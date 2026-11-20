// SPDX-License-Identifier: MIT
// st_audio: 16-bit stereo audio out through an STM32F7 SAI and a DMA ring, for a codec that
// takes I2S with a master clock of 256 x the sample rate (the STM32F769I-DISCO's WM8994 on
// SAI1 block A). The codec itself is set up from Python over I2C (python/stm32/audio.py).
//
//   st_audio.init(rate)        # PLLI2S, SAI1 block A, DMA2 stream 1 in circular mode: silence
//   st_audio.write(buf, mono=False, shift=0)  # copies what fits now, returns bytes taken
//   st_audio.queued()          # bytes written and not yet played
//   st_audio.deinit()
//
// No interrupt: the DMA loops over a ring in RAM and Python feeds it. What the DMA has played is
// zeroed when the ring is next looked at (write, queued), so if Python is late the codec gets
// silence, not the old sound again. mono=True doubles each sample to both channels; shift > 0
// divides the samples by 2^shift (quieter by 6 dB a step).
//
// Pins and frame as ST's BSP for the board (stm32f769i_discovery_audio.c): MCLK PG7, SCK PE5,
// FS PE4, SD PE6 (AF6); frame of 64 bits, four 16-bit slots, slots 0 and 2 active (left,
// right), FS on the channel, one bit before the first.

#include <string.h>

#include "py/runtime.h"
#include "py/mphal.h"
#include "dma.h"
#include "pin.h"

#if defined(MICROPY_HW_AUDIO_SAI1)

#define RING_BYTES (32 * 1024)   // 186 ms at 44.1 kHz stereo
#define GUARD_BYTES (64)         // the writer stays this far behind the DMA

static uint8_t ring[RING_BYTES] __attribute__((aligned(32)));
static uint32_t ring_w;          // next byte to write
static uint32_t ring_r;          // where the DMA was when last looked at
static uint32_t ring_queued;     // bytes written and not played
static uint32_t rate_hz;
static bool running;

#define DMA_STREAM DMA2_Stream1  // channel 0: SAI1_A

// PLLI2S Q / DIVQ as the SAI1 clock (1 MHz in, HSE / PLLM): 256 x 44.1 kHz or a multiple of
// 256 x 48 kHz, then the SAI's MCKDIV for the rate. As ST's BSP.
static void clock_set(uint32_t rate) {
    uint32_t n, q, divq, mckdiv;
    switch (rate) {
        case 44100: n = 429; q = 2; divq = 19; mckdiv = 0; break;   // 11.2895 MHz
        case 22050: n = 429; q = 2; divq = 19; mckdiv = 1; break;
        case 11025: n = 429; q = 2; divq = 19; mckdiv = 2; break;
        case 48000: n = 344; q = 7; divq = 1; mckdiv = 2; break;    // 49.1429 MHz / 4
        case 32000: n = 344; q = 7; divq = 1; mckdiv = 3; break;
        case 16000: n = 344; q = 7; divq = 1; mckdiv = 6; break;
        case 8000: n = 344; q = 7; divq = 1; mckdiv = 12; break;
        default:
            mp_raise_ValueError(MP_ERROR_TEXT("st_audio: rate 8000, 11025, 16000, 22050, 32000, 44100 or 48000"));
    }
    RCC->CR &= ~RCC_CR_PLLI2SON;
    while (RCC->CR & RCC_CR_PLLI2SRDY) {
    }
    RCC->PLLI2SCFGR = (n << RCC_PLLI2SCFGR_PLLI2SN_Pos) | (q << RCC_PLLI2SCFGR_PLLI2SQ_Pos)
        | (2 << RCC_PLLI2SCFGR_PLLI2SR_Pos);
    // PLLI2SDIVQ is divq - 1; SAI1SEL 01 is PLLI2S. The rest of DCKCFGR1 (PLLSAIDIVR for the
    // LTDC, TIMPRE) stays.
    RCC->DCKCFGR1 = (RCC->DCKCFGR1 & ~(RCC_DCKCFGR1_PLLI2SDIVQ | RCC_DCKCFGR1_SAI1SEL))
        | ((divq - 1) << RCC_DCKCFGR1_PLLI2SDIVQ_Pos) | (1 << RCC_DCKCFGR1_SAI1SEL_Pos);
    RCC->CR |= RCC_CR_PLLI2SON;
    uint32_t t0 = mp_hal_ticks_ms();
    while (!(RCC->CR & RCC_CR_PLLI2SRDY)) {
        if (mp_hal_ticks_ms() - t0 > 100) {
            mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("st_audio: PLLI2S did not lock"));
        }
    }
    SAI1_Block_A->CR1 = (SAI1_Block_A->CR1 & ~SAI_xCR1_MCKDIV) | (mckdiv << SAI_xCR1_MCKDIV_Pos);
}

static uint32_t dma_pos(void) {
    return RING_BYTES - DMA_STREAM->NDTR * 2;
}

static void clean(uint32_t from, uint32_t len) {
    uint32_t a = (uint32_t)ring + from;
    uint32_t start = a & ~31u;
    SCB_CleanDCache_by_Addr((uint32_t *)start, (a + len - start + 31) & ~31u);
}

// Zero what the DMA played since the last look, and count it out of the queue.
static void advance(void) {
    uint32_t r = dma_pos();
    uint32_t played = (r + RING_BYTES - ring_r) % RING_BYTES;
    if (played >= ring_queued) {
        // Underrun (or nothing queued): the writer starts again where the DMA is.
        ring_queued = 0;
        ring_w = r;
    } else {
        ring_queued -= played;
    }
    uint32_t a = ring_r;
    while (played) {
        uint32_t n = played;
        if (a + n > RING_BYTES) {
            n = RING_BYTES - a;
        }
        memset(ring + a, 0, n);
        clean(a, n);
        a = (a + n) % RING_BYTES;
        played -= n;
    }
    ring_r = r;
}

static void stop(void) {
    if (!running) {
        return;
    }
    SAI1_Block_A->CR1 &= ~(SAI_xCR1_SAIEN | SAI_xCR1_DMAEN);
    DMA_STREAM->CR &= ~DMA_SxCR_EN;
    while (DMA_STREAM->CR & DMA_SxCR_EN) {
    }
    dma_external_release(1, 1);
    running = false;
}

static mp_obj_t st_audio_init(mp_obj_t rate_in) {
    uint32_t rate = mp_obj_get_int(rate_in);
    stop();

    // Pins: MCLK PG7, SCK PE5, FS PE4, SD PE6, AF6.
    const machine_pin_obj_t *pins[] = { pin_G7, pin_E5, pin_E4, pin_E6 };
    for (size_t i = 0; i < MP_ARRAY_SIZE(pins); ++i) {
        mp_hal_pin_config(pins[i], MP_HAL_PIN_MODE_ALT, MP_HAL_PIN_PULL_NONE, 6);
        mp_hal_pin_config_speed(pins[i], MP_HAL_PIN_SPEED_VERY_HIGH);
    }

    __HAL_RCC_SAI1_CLK_ENABLE();
    __HAL_RCC_SAI1_FORCE_RESET();
    __HAL_RCC_SAI1_RELEASE_RESET();
    SAI1_Block_A->CR1 = 0;
    clock_set(rate);
    rate_hz = rate;

    // Master transmitter, free protocol, 16-bit data, signals change on SCK's rising edge
    // (CKSTR 0 for a transmitter: ST's "rising edge"), master clock out (NODIV 0).
    SAI1_Block_A->CR1 = (SAI1_Block_A->CR1 & SAI_xCR1_MCKDIV) | (4 << SAI_xCR1_DS_Pos);
    SAI1_Block_A->CR2 = (1 << SAI_xCR2_FTH_Pos) | SAI_xCR2_FFLUSH;
    SAI1_Block_A->FRCR = (63 << SAI_xFRCR_FRL_Pos) | (31 << SAI_xFRCR_FSALL_Pos)
        | SAI_xFRCR_FSDEF | SAI_xFRCR_FSOFF;  // FS active low: left channel
    SAI1_Block_A->SLOTR = (3 << SAI_xSLOTR_NBSLOT_Pos) | (0x0005u << SAI_xSLOTR_SLOTEN_Pos);

    memset(ring, 0, sizeof(ring));
    SCB_CleanDCache_by_Addr((uint32_t *)ring, sizeof(ring));
    ring_w = ring_r = ring_queued = 0;

    dma_external_acquire(1, 1);  // DMA2's clock stays on while MicroPython's DMA is idle
    DMA_STREAM->CR = 0;
    while (DMA_STREAM->CR & DMA_SxCR_EN) {
    }
    DMA2->LIFCR = DMA_LIFCR_CTCIF1 | DMA_LIFCR_CHTIF1 | DMA_LIFCR_CTEIF1 | DMA_LIFCR_CDMEIF1 | DMA_LIFCR_CFEIF1;
    DMA_STREAM->PAR = (uint32_t)&SAI1_Block_A->DR;
    DMA_STREAM->M0AR = (uint32_t)ring;
    DMA_STREAM->NDTR = RING_BYTES / 2;
    DMA_STREAM->FCR = 0;  // direct mode
    DMA_STREAM->CR = (0 << DMA_SxCR_CHSEL_Pos) | (2 << DMA_SxCR_PL_Pos)
        | (1 << DMA_SxCR_MSIZE_Pos) | (1 << DMA_SxCR_PSIZE_Pos) | DMA_SxCR_MINC
        | DMA_SxCR_CIRC | (1 << DMA_SxCR_DIR_Pos);
    DMA_STREAM->CR |= DMA_SxCR_EN;

    SAI1_Block_A->CR1 |= SAI_xCR1_DMAEN;
    SAI1_Block_A->CR1 |= SAI_xCR1_SAIEN;
    running = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(st_audio_init_obj, st_audio_init);

static mp_obj_t st_audio_deinit(void) {
    stop();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(st_audio_deinit_obj, st_audio_deinit);

static mp_obj_t st_audio_write(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_buf, ARG_mono, ARG_shift };
    static const mp_arg_t allowed[] = {
        { MP_QSTR_buf, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_mono, MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_shift, MP_ARG_INT, {.u_int = 0} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed), allowed, args);
    if (!running) {
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("st_audio: not started"));
    }
    mp_buffer_info_t bi;
    mp_get_buffer_raise(args[ARG_buf].u_obj, &bi, MP_BUFFER_READ);
    bool mono = args[ARG_mono].u_bool;
    int shift = args[ARG_shift].u_int;
    advance();
    uint32_t room = RING_BYTES - GUARD_BYTES - ring_queued;
    // Bytes taken from buf: whole frames (4 bytes stereo, 2 bytes mono written as 4).
    uint32_t take = mono ? (room / 4) * 2 : room & ~3u;
    if (take > (bi.len & ~(mono ? 1u : 3u))) {
        take = bi.len & ~(mono ? 1u : 3u);
    }
    const int16_t *src = bi.buf;
    uint32_t samples = take / 2;
    uint32_t a = ring_w;
    uint32_t out = mono ? samples * 4 : take;
    for (uint32_t i = 0; i < samples; ++i) {
        int16_t v = src[i] >> shift;
        *(int16_t *)(ring + a) = v;
        a = (a + 2) % RING_BYTES;
        if (mono) {
            *(int16_t *)(ring + a) = v;
            a = (a + 2) % RING_BYTES;
        }
    }
    // Clean what was written, in up to two pieces around the end of the ring.
    if (ring_w + out <= RING_BYTES) {
        clean(ring_w, out);
    } else {
        clean(ring_w, RING_BYTES - ring_w);
        clean(0, ring_w + out - RING_BYTES);
    }
    __DSB();
    ring_w = a;
    ring_queued += out;
    return mp_obj_new_int_from_uint(take);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(st_audio_write_obj, 1, st_audio_write);

static mp_obj_t st_audio_queued(void) {
    if (!running) {
        return MP_OBJ_NEW_SMALL_INT(0);
    }
    advance();
    return mp_obj_new_int_from_uint(ring_queued);
}
static MP_DEFINE_CONST_FUN_OBJ_0(st_audio_queued_obj, st_audio_queued);

static mp_obj_t st_audio_info(void) {
    mp_obj_t d = mp_obj_new_dict(0);
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_running), mp_obj_new_bool(running));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_rate), mp_obj_new_int_from_uint(rate_hz));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_ring_bytes), MP_OBJ_NEW_SMALL_INT(RING_BYTES));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_dma_pos), mp_obj_new_int_from_uint(running ? dma_pos() : 0));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_sai_sr), mp_obj_new_int_from_uint(SAI1_Block_A->SR));
    return d;
}
static MP_DEFINE_CONST_FUN_OBJ_0(st_audio_info_obj, st_audio_info);

static const mp_rom_map_elem_t st_audio_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_st_audio) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&st_audio_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&st_audio_deinit_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&st_audio_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_queued), MP_ROM_PTR(&st_audio_queued_obj) },
    { MP_ROM_QSTR(MP_QSTR_info), MP_ROM_PTR(&st_audio_info_obj) },
    { MP_ROM_QSTR(MP_QSTR_RING_BYTES), MP_ROM_INT(RING_BYTES) },
};
static MP_DEFINE_CONST_DICT(st_audio_globals, st_audio_globals_table);

const mp_obj_module_t st_audio_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&st_audio_globals,
};

MP_REGISTER_MODULE(MP_QSTR_st_audio, st_audio_user_cmodule);

#endif // MICROPY_HW_AUDIO_SAI1
