# Audio out of the STM32F769I-DISCO: beeps and WAV files, in the background. The same calls as
# python/esp32/audio.py, so buzzer.py and the apps use either.
#
#   import audio
#   audio.beep()                     # 880 Hz, 100 ms
#   audio.beep(440, 500, atten=2)    # atten: quieter by 6 dB a step
#   audio.tone(660)                  # until audio.finish()
#   audio.play("/sd/sound.wav")      # returns at once; PCM, 16 bit, mono or stereo
#   audio.playing()
#   audio.finish()                   # stop feeding: what is queued still plays
#   audio.stop()                     # silence once the queue has played (up to about 0.1 s)
#   audio.volume(70)                 # headphone volume, 0 (mute) to 100
#
# The WM8994 codec on I2C4 (0x1A), its headphone output (the line output jack CN7, UM2033 6.9),
# fed by SAI1 through st_audio (modules/st_audio). The codec's set-up is ST's (wm8994.c of the
# BSP, BSD-3, see docs/CREDITS.md) for the headphone with no input, as register writes here.
#
# A machine.Timer every FEED_MS tops the queue up to QUEUE_BYTES; if Python is held up longer
# than the ring (st_audio.RING_BYTES) the codec gets silence, not the old sound again.
import math
import struct

import micropython
import st_audio
from machine import I2C, Timer

ADDR = 0x1A
RATE = 22050             # for beeps and tones
FEED_MS = 20
QUEUE_BYTES = 8192       # about 93 ms at 22.05 kHz stereo
BLOCK = 4096
VOLUME = 70

# AIF1 rate register (0x210): sample rate code, 256 x fs for the master clock.
_RATE_CODE = {8000: 0x03, 11025: 0x13, 16000: 0x33, 22050: 0x43, 32000: 0x63, 44100: 0x73,
              48000: 0x83}

_i2c = None
_rate = None
_timer = None
_file = None
_buf = None
_view = None
_left = 0
_off = 0                 # where a tone's block goes on from
_mono = True
_atten = 0
_volume = VOLUME


def _w(reg, value):
    _i2c.writeto_mem(ADDR, reg, struct.pack(">H", value), addrsize=16)


def _codec_init(rate):
    # ST's WM8994_Init for OUT_HEADPHONE, IN_NONE, 16 bit, I2S, cold start-up.
    global _i2c
    import time

    _i2c = I2C(4, freq=400_000)
    if _i2c.readfrom_mem(ADDR, 0x0000, 2, addrsize=16) != b"\x89\x94":
        raise OSError("WM8994 not found on I2C4")
    for reg, value in ((0x102, 0x0003), (0x817, 0x0000), (0x102, 0x0000),
                       (0x039, 0x006C),   # ANTIPOP2: VMID soft start
                       (0x001, 0x0003)):  # PWR_MANAGEMENT_1: bias, VMID
        _w(reg, value)
    time.sleep_ms(50)
    for reg, value in ((0x005, 0x0303),   # PWR_MANAGEMENT_5: AIF1 DAC1 left and right on
                       (0x601, 0x0001), (0x602, 0x0001),   # AIF1 timeslot 0 to DAC1
                       (0x604, 0x0000), (0x605, 0x0000),
                       (0x210, _RATE_CODE[rate]),           # AIF1_RATE
                       (0x300, 0x4010),   # AIF1_CONTROL1: I2S, 16 bit (ADCR source)
                       (0x302, 0x0000),   # AIF1 slave: the SAI is the master
                       (0x208, 0x000A),   # CLOCKING1: DSP clocks from AIF1CLK
                       (0x200, 0x0001),   # AIF1_CLOCKING1: AIF1CLK from MCLK1, on
                       (0x02D, 0x0100), (0x02E, 0x0100),   # DAC1 to the headphone mixers
                       (0x110, 0x8100)):  # WRITE_SEQ_CTRL1: headphone cold start-up sequence
        _w(reg, value)
    time.sleep_ms(325)
    for reg, value in ((0x420, 0x0000),
                       (0x610, 0x00C0), (0x611, 0x00C0),   # DAC1 volume 0 dB, update
                       (0x420, 0x0010),                    # AIF1 DAC1 unmute, soft mute ramp
                       (0x612, 0x00C0), (0x613, 0x00C0),
                       (0x422, 0x0010)):
        _w(reg, value)
    volume(_volume)


def volume(percent=None):
    """Headphone volume 0..100 (0 mutes); with no argument, the current one."""
    global _volume
    if percent is None:
        return _volume
    _volume = max(0, min(100, int(percent)))
    if _i2c is None:
        return
    if _volume == 0:
        _w(0x420, 0x0200)  # AIF1 DAC1 mute
        return
    _w(0x420, 0x0010)
    level = (_volume * 63 // 100) | 0x140  # HPOUT1 volume, update, unmuted
    _w(0x01C, level)
    _w(0x01D, level)


def _start(rate, mono, atten):
    global _rate, _timer, _mono, _atten
    if rate not in _RATE_CODE:
        raise ValueError("rate 8000, 11025, 16000, 22050, 32000, 44100 or 48000")
    _stop_feed()
    if _rate is None:
        st_audio.init(rate)  # the master clock runs before the codec is set up
        _codec_init(rate)
    elif rate != _rate:
        st_audio.init(rate)
        _w(0x210, _RATE_CODE[rate])
    _rate = rate
    _mono = mono
    _atten = atten
    _timer = Timer(-1, period=FEED_MS, mode=Timer.PERIODIC, callback=_tick)


def _tick(_):
    try:
        micropython.schedule(_feed, None)
    except RuntimeError:
        pass  # schedule queue full: the next tick feeds


def _feed(_=None):
    global _left, _off
    if _timer is None:
        return
    while _left > 0 and st_audio.queued() < QUEUE_BYTES:
        if _file:
            n = _file.readinto(_view[:min(_left, len(_buf))])
            if not n:
                _left = 0
                break
            taken = st_audio.write(_view[:n], mono=_mono, shift=_atten)
            if taken < n:
                _file.seek(taken - n, 1)  # give back what did not fit
        else:
            # A tone: the block of whole periods goes on where it stopped, with no phase jump.
            n = min(_left, len(_buf) - _off)
            taken = st_audio.write(_view[_off:_off + n], mono=_mono, shift=_atten)
            _off = (_off + taken) % len(_buf)
        _left -= taken
        if taken < n:
            break
    if _left <= 0 and st_audio.queued() == 0:
        _stop_feed()


def _stop_feed():
    global _timer, _file
    t, f = _timer, _file
    _timer = _file = None
    if t:
        t.deinit()
    if f:
        f.close()


def stop():
    """Stop feeding and close the file: silence once the queue has played (up to ~0.1 s)."""
    global _left
    _left = 0
    _stop_feed()


def playing():
    return _timer is not None


def finish():
    global _left
    _left = 0


def _tone(freq, nbytes, atten):
    global _buf, _view, _left, _off
    _start(RATE, True, 0)
    period = max(2, round(RATE / freq))
    amplitude = 16000 >> atten
    one = bytearray(2 * period)
    for i in range(period):
        struct.pack_into("<h", one, 2 * i, int(amplitude * math.sin(2 * math.pi * i / period)))
    # A block of whole periods, written again and again.
    _buf = bytearray(bytes(one) * max(1, BLOCK // len(one)))
    _view = memoryview(_buf)
    _off = 0
    _left = nbytes - nbytes % len(one)
    _feed()


def beep(freq=880, ms=100, atten=1):
    _tone(freq, RATE * ms // 1000 * 2, atten)


def tone(freq=880, atten=1):
    _tone(freq, 1 << 30, atten)


def _wav_data(f):
    """Leave f at the samples; returns (rate, channels, bytes of samples)."""
    head = f.read(12)
    if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
        raise ValueError("not a WAV file")
    channels = rate = None
    while True:
        h = f.read(8)
        if len(h) < 8:
            raise ValueError("no data in the WAV file")
        tag, size = h[:4], struct.unpack("<I", h[4:])[0]
        if tag == b"data":
            if channels is None:
                raise ValueError("no format in the WAV file")
            return rate, channels, size
        if tag == b"fmt ":
            fmt = f.read(size + (size & 1))
            code, channels, rate, _, _, bits = struct.unpack("<HHIIHH", fmt[:16])
            if code != 1 or bits != 16 or channels > 2:
                raise ValueError("only PCM, 16 bit, mono or stereo")
        else:
            f.seek(size + (size & 1), 1)


def play(path, atten=0):
    global _file, _left, _buf, _view
    f = open(path, "rb")
    try:
        rate, channels, size = _wav_data(f)
        _start(rate, channels == 1, atten)
    except Exception:
        f.close()
        raise
    _buf = bytearray(BLOCK)
    _view = memoryview(_buf)
    _file, _left = f, size
    _feed()
