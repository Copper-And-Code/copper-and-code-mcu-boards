# Handover: scheda STM32H7_CORE V1.3 + pannello IPS 1024x600 (MicroPython + LVGL)

Per chi sviluppa strumenti (per esempio un IDE LVGL) che parlano con la scheda sul
banco. Stato verificato il 2026-11-03 sul firmware della commit `ab3235d` del branch
`stm32h743` (repo `mpy-lvgl-boards`); dettagli tecnici in `docs/stm32h743.md`.

## 1. Hardware

| | |
|---|---|
| MCU | STM32H743, Cortex-M7 a 480 MHz, FPU in doppia precisione |
| RAM | SDRAM 32 MB su bus a 16 bit (FMC, 120 MHz): 28 MB di heap MicroPython, 4 MB riservati ai framebuffer |
| Flash | 2 MB interna (firmware, 1,13 MB usati) + QSPI W25Q128 da 16 MB montata come `/flash` (FAT, ~16 MB liberi) |
| Display | IPS 7" **1024x600 RGB565**, controller LTDC, ~58,3 Hz, due framebuffer (nessun tearing) |
| Touch | GT911 capacitivo, I2C software (SCL B12, SDA B13, reset B14, INT H7), indirizzo 0x5D, coordinate già in pixel del pannello, nessuna rotazione |
| Retroilluminazione | GPIO on/off (nessun dimmer: qualsiasi valore > 0 = accesa) |
| Buzzer | nessuno (`buzzer.AVAILABLE` è `False`, le chiamate non fanno nulla) |
| SD | lo slot c'è nel firmware, ma non c'è una scheda inserita (`/sd` assente) |

## 2. Collegamento al PC

- **Una sola via**: la UART1 della scheda (PA9/PA10, la REPL) tramite un convertitore
  CH340, **`/dev/ttyUSB0`, 115200 8N1**. La USB nativa della scheda non è collegata.
- **`/dev/ttyACM0` è un'altra scheda (emulatore C64): non aprirla mai.**
- Cablaggio particolare: **DTR → BOOT0, RTS → NRST**.
  - Per far girare la scheda: **DTR = 1 (BOOT0 basso), RTS = 0 (reset rilasciato)**.
  - RTS = 1 tiene la scheda in reset; DTR = 0 + impulso su RTS = bootloader ST.
- **Ogni apertura della porta resetta la scheda** (Linux muove DTR/RTS all'apertura,
  prima che si possano impostare). Conseguenze per un IDE:
  - aprire la porta **una volta** e tenerla aperta per tutta la sessione;
  - dopo l'apertura aspettare **~3 s** che la scheda finisca il boot;
  - lo stato in RAM (variabili, schermata LVGL) non sopravvive a una riapertura.
- Una sola applicazione alla volta può usare la porta.
- **`mpremote` non va bene** su questo collegamento (lascia RTS alto → scheda in reset).
  Terminale manuale: `picocom -b 115200 --lower-rts /dev/ttyUSB0` (uscita `Ctrl-A Ctrl-X`).

Apertura corretta con pyserial (impostare DTR/RTS **prima** di `open()`):

```python
import serial, time
s = serial.Serial()
s.port, s.baudrate, s.timeout = "/dev/ttyUSB0", 115200, 0.1
s.dtr, s.rts = True, False      # BOOT0 basso, NRST rilasciato
s.open()
time.sleep(3)                   # l'apertura ha resettato la scheda: attendere il boot
```

## 3. Protocollo: REPL standard di MicroPython

È la REPL normale (stessi byte di `mpremote`):

| Byte | Effetto |
|---|---|
| `Ctrl-C` (0x03) | interrompe il programma in corso |
| `Ctrl-A` (0x01) | entra nella raw REPL (risponde `raw REPL; CTRL-B to exit\r\n>`) |
| `Ctrl-B` (0x02) | torna alla REPL normale |
| `Ctrl-D` (0x04) | in raw REPL esegue il codice inviato; a prompt vuoto fa un **soft reset** |
| `Ctrl-E` (0x05) | modalità paste (REPL normale) |

Esecuzione in raw REPL: si invia il codice, poi `0x04`; la scheda risponde
`OK<stdout>\x04<stderr>\x04>`. Stderr non vuoto = eccezione (traceback in chiaro).
Il codice va mandato a blocchi (256 B con 10 ms di pausa funziona; la UART non ha
controllo di flusso). La modalità raw-paste (`\x05A\x01`) non è stata provata.

Esempio provato (scrive un file su `/flash`, ~2 KB/s utili):

```python
import binascii

def rd(marker, t=10):
    b, end = b"", time.time() + t
    while time.time() < end:
        b += s.read(4096)
        if marker in b:
            return b
    raise TimeoutError(b)

s.write(b"\r\x03\x03"); time.sleep(0.2); s.reset_input_buffer()
s.write(b"\r\x01"); rd(b"raw REPL; CTRL-B to exit\r\n>")

def exec_(code, t=10):
    s.write(code.encode() + b"\x04")
    out, err = rd(b"\x04>", t).split(b"OK", 1)[1].split(b"\x04")[:2]
    if err.strip():
        raise RuntimeError(err.decode())
    return out.decode()

def put(data, remote):
    exec_("import binascii\nf=open(%r,'wb')" % remote)
    for i in range(0, len(data), 512):
        chunk = binascii.b2a_base64(data[i:i + 512], newline=False).decode()
        exec_("f.write(binascii.a2b_base64(%r))" % chunk)
    exec_("f.close()")
```

Script pronti nel repo (`mpy-lvgl-boards/scripts/`):

- `uart_run.py a.py [b.py ...] [--timeout N] [--soft-reset]`: esegue script in raw REPL
  in un'unica sessione (come `mpremote run`); exit 1 su eccezione, 2 su timeout.
- `stm32_uart_flash.py flash <firmware>.hex --verify`: aggiorna il firmware via
  bootloader ST su UART (gestisce da solo DTR/RTS), ~2,5 min; `probe`, `reset`.

## 4. Software sulla scheda

- MicroPython **1.29.0** + **LVGL 9.5.0** (binding PyDevices `lvgl-micropython`, API
  `import lvgl as lv`, nomi in stile LVGL 9: `lv.obj`, `lv.button`, `lv.label`,
  `lv.screen_load`, `lv.ALIGN.CENTER`, `lv.EVENT.CLICKED`...).
- Font compilati: **`lv.font_montserrat_14`, `_16`, `_24`, `_32`, `_40`** (nessun altro).
- Colore 16 bit (RGB565).
- Moduli congelati utili: `display_driver`, `ui`, `buzzer`, `st_ltdc`, `panels`,
  `stm32_board`, `gt911`, `fs_driver`, `asyncio`, `framebuf`, `json`.
- `/flash` contiene ancora file di un vecchio progetto dell'utente (terminale, tetris,
  editor...); `boot.py` e `main.py` sono solo commenti, quindi all'avvio non parte nulla
  e la scheda va al prompt. Non cancellare quei file senza chiedere.
- Pannello scelto da `/flash/display_config.py` (`PANEL = "IPS1024x600"`); il file non
  c'è e il default è già quello giusto.

### Avviare LVGL

```python
import lvgl as lv
import display_driver          # pannello, LVGL, touch e timer_handler periodico

scr = lv.obj()
lv.label(scr).set_text("Ciao")
lv.screen_load(scr)
# nessun loop: lv.timer_handler() gira da solo ogni 5 ms
```

- `display_driver.WIDTH, .HEIGHT` (1024, 600), `.disp`, `.touch` (GT911 o `None`),
  `.indev`, `.stop()` / `.start()` (ferma/riprende il `timer_handler` automatico),
  `.backlight(pct)`.
- Reimportarlo è sicuro. Stessa interfaccia della scheda RP2350 (240x240):
  lo stesso codice gira su entrambe.
- `ui.px(n)` scala misure pensate per 240 px (`ui.px(10)` = 25 px qui),
  `ui.font(size)` sceglie il Montserrat compilato più vicino, `ui.W`, `ui.H`.
- Esempi pronti in `mpy-lvgl-boards/examples/` (hello, button, animation, backlight,
  breakout, pong, simon, snake, tictactoe, c64_keyboard).

### Comportamenti da conoscere

- **Ctrl-C mentre gira un'app LVGL**: il primo Ctrl-C di solito cade dentro il
  `timer_handler` e ferma solo il timer (messaggio
  `display_driver: stopped by Ctrl-C`); il secondo interrompe il programma. Un IDE
  dovrebbe mandare Ctrl-C due o tre volte prima di entrare in raw REPL.
- **Soft reset (Ctrl-D)**: LVGL viene deinizializzato e la RAM liberata, ma il pannello
  continua a mostrare l'ultima immagine finché un nuovo `import display_driver` non
  ridisegna. È il modo più rapido per ripartire pulito senza riaprire la porta.
- **Hard reset** = riaprire la porta (o impulso su RTS): ~3 s.
- Non c'è un modo veloce per leggere lo schermo dal PC: il framebuffer è 1,2 MB e la
  UART fa ~11 KB/s (circa 2 minuti). Per un'anteprima conviene renderizzare
  sul PC (LVGL per simulatore) o leggere un'immagine ridotta.
- Prestazioni misurate: ridisegno completo di una schermata con 48 pulsanti 56–66 ms,
  animazioni ~35 aggiornamenti/s, 0 underrun del pannello. Il limite è la banda della
  SDRAM a 16 bit.
- Touch: errore I2C occasionale (~1 lettura su 9000), assorbito dal driver
  (`display_driver.touch.errors` lo conta).

## 5. Verifica rapida che la scheda risponda

```
cd mpy-lvgl-boards
printf 'import os,gc\nprint(os.uname().machine, gc.mem_free())\n' > /tmp/ping.py
python3 scripts/uart_run.py /tmp/ping.py --timeout 20
# STM32H7_CORE V1.3 with STM32H743 28686000
```

## Script dei layout del maintainer sulla V1.0 (10 novembre 2026)
Script del maintainer (PR #6), adattato: `hold()` = `display_driver.stop()/start()`. Copia, helper e risultati in `_private/pool-layouts-V10/` (bench.sh fa reset hardware prima di ogni giro: soft reset non basta, l'heap restava sporco).
Due build dallo stesso albero 60e4cc2-dirty, V1.0, lvgl-micropython 3e287e7 con la nostra patch, 1024x600, heap 28 MB in SDRAM, due giri identici:
- nopool: refresh mediana 68.6 / 359.3 / 360.0 ms (fresh / one hole / many holes), worst 68.8 / 359.8 / 370.7; 50 label 15.6 / 31.6 / 93.5 ms; collect 31.7 / 81 / 77 ms.
- pools: refresh 68.6 in tutti e tre (worst <= 68.7); 50 label 14.5 / 14.5 / 17.9 ms; collect 37.6 / 87.0 / 82.9 ms.
- bytearray(100): 101-130 / 66-79 / ~865 us in entrambe (nessun buco "one hole" lento da noi).
Sulla scheda resta la build pools 60e4cc2-dirty (hash flash verificato). Modifica non committata: `LVMP_POOLS=none` in `boards/stm32/lvgl_pool.mk` e `scripts/build.sh` (suffisso -nopool).
DFU: `machine.bootloader()` NON entra nella DFU ROM su questa scheda (reset normale); servono BOOT0+RESET. Uscita senza tasti: `dfu-util -a 0 -d 0483:df11 -s 0x08000000:4:leave -U <file>`.
Risposta al maintainer: pubblicata dall'utente il 10 novembre (tabella completa + chiarimento che i run S3 su #10 non sono ancora fatti). Prossimi: ESP32 tre firmware con questo script (#10), poi H7 su omnipython-lvgl, poi heap piccolo AXI SRAM.
