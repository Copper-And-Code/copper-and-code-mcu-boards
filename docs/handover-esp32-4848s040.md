# Handover: scheda ESP32-4848S040 (MicroPython + LVGL)

Per chi sviluppa strumenti (per esempio un IDE LVGL) che parlano con questa scheda. Stato
verificato il 2026-11-05 sul firmware del branch `esp32-speed` di `mpy-lvgl-boards`. Dettagli tecnici e
misure in `docs/esp32-4848s040.md`. La V1.3 ha un handover a parte:
`docs/handover-stm32h7-core-v13.md`; **le differenze contano**, vedi la sezione 2.

## 1. Hardware

| | |
|---|---|
| MCU | ESP32-S3, 240 MHz, doppio core, WiFi e BLE |
| RAM | 8 MB PSRAM ottale: circa 5,7 MB di heap MicroPython (il resto: firmware eseguito da PSRAM e framebuffer) |
| Flash | 16 MB: 3 MB firmware, circa 12 MB filesystem `/` (LittleFS, formattato al primo avvio) |
| Display | IPS 4" **480x480 RGB565**, ST7701, bus RGB 16 bit, **42 Hz** (pixel clock 12 MHz), due framebuffer (nessun tearing) |
| Touch | GT911 capacitivo, I2C software (SCL 45, SDA 19), indirizzo 0x5D, coordinate in pixel del pannello, nessuna rotazione; RST e INT non collegati |
| Retroilluminazione | GPIO 38, on/off (nessun dimmer) |
| Altro | Buzzer no; relè, altoparlante e SD non gestiti dal firmware |

## 2. Collegamento al PC: cosa cambia rispetto alla V1.3

- **Una sola via**: il CH340 della scheda, **`/dev/ttyUSB0`, 115200 8N1**, REPL su UART0.
  La USB nativa è **spenta nel firmware**, perché i suoi pin servono al touch e al pannello:
  non comparirà nessuna `/dev/ttyACM*` e non c'è disco USB.
- **Stesso convertitore della V1.3**: il nome della porta non dice quale scheda c'è. Con
  `esptool.py flash_id` risponde un ESP32-S3; `scripts/stm32_uart_flash.py probe` riconosce la V1.3.
- **DTR e RTS vanno aperti entrambi a 0** (DTR alto tiene basso IO0, e al reset la scheda
  andrebbe in bootloader). Sulla V1.3 serve invece DTR = 1, RTS = 0.
- **Ogni apertura della porta resetta la scheda**, come sulla V1.3: aprire una volta, tenere
  aperto, aspettare circa **5 s**.
- **`mpremote`** non è stato provato qui.

```python
import serial, time
s = serial.Serial()
s.port, s.baudrate, s.timeout = "/dev/ttyUSB0", 115200, 0.1
s.dtr, s.rts = False, False
s.open()
time.sleep(5)
```

Con lo script del repository:

```
python3 scripts/uart_run.py a.py b.py --dtr 0 --boot-wait 5 --soft-reset --timeout 60
```

**Aggiornare il firmware** (immagine completa, offset 0; serve ESP-IDF v5.5.2 attivo o `pip install esptool`):

```
esptool.py --chip esp32s3 -p /dev/ttyUSB0 -b 460800 write_flash 0x0 ESP32_4848S040-<commit>.bin
```

Su una scheda con un altro firmware fare prima `esptool.py --chip esp32s3 -p /dev/ttyUSB0 erase_flash`
(cancella tutto): altrimenti può fermarsi all'avvio con "The filesystem appears to be corrupted".

Il protocollo REPL e il caricamento file sono gli stessi della V1.3 (sezione 3 del suo
handover), con `/` al posto di `/flash`:

```python
exec_("import binascii\nf=open('/app.py','wb')")
```

## 3. Software

- MicroPython **1.29.0**, **LVGL 9.5.0**, binding `PyDevices/omnipython-lvgl` `92f8c0a`
  (`import lvgl as lv`): non il vecchio `lvgl-micropython` della V1.3.
- Font: la lista non è stata controllata su questa scheda (verificare con `dir(lv)`):
  `ui.font()` sceglie comunque tra quelli presenti.
- Moduli congelati: `display_driver`, `ui`, `buzzer`, `esp_rgb`, `panels`, `gt911`.
- La flash è stata cancellata: sul filesystem c'è solo il `boot.py` standard creato da
  MicroPython al primo avvio. `/main.py` parte all'avvio, se lo scrivi.

```python
import lvgl as lv
import display_driver      # pannello, LVGL, touch e timer_handler periodico

scr = lv.obj()
lv.label(scr).set_text("Ciao")
lv.screen_load(scr)
```

Stessa interfaccia delle altre schede: `display_driver.WIDTH, .HEIGHT` (480, 480), `.disp`,
`.touch`, `.indev`, `.stop()`, `.start()`, `.backlight(pct)`. `ui.px(n)` qui è `2 * n`.

## 4. Comportamenti da conoscere

- **Ridisegno lento**: una schermata piena di pulsanti richiede circa **90 ms**, contro 55 ms sulla V1.3.
  Le piccole modifiche vanno bene: 3 ms, animazioni al passo del pannello. Evitare effetti a schermo intero.
- **`gc.collect()` dura 120 ms** (5 frame) e nelle animazioni si vede come un'esitazione.
  Nelle app conviene allocare poco; se proprio serve, chiamarlo a schermo fermo.
- **Ctrl-C** con un'app LVGL: come sulla V1.3, mandarne due o tre prima della raw REPL.
- **Soft reset (Ctrl-D)**: sicuro anche con LVGL attivo (provato 3 su 3). Il pannello mantiene
  l'ultima immagine finché non riparte `display_driver`.
- **Crash**: un errore grave stampa `Guru Meditation` sulla seriale e la scheda si riavvia da
  sola. Un IDE può riconoscere quel testo e mostrarlo.
- **Memoria**: con LVGL attivo e una scena semplice restano circa 4,7 MB. Il firmware non ha i
  pool di memoria di LVGL della V1.3.
- **`flush_cb` in Python** con Ctrl-C blocca la scheda: usare `display_driver`, che ha la flush
  in C. Se capita, serve un reset hardware; riaprire la porta lo fa.
- **Leggere lo schermo dal PC**: 460 KB a circa 11 KB/s, oltre 40 secondi.

## 5. Verifica rapida

```
printf 'import os,gc\nprint(os.uname().machine, gc.mem_free())\n' > /tmp/ping.py
python3 scripts/uart_run.py /tmp/ping.py --dtr 0 --boot-wait 5 --timeout 20
# ESP32-4848S040 with ESP32-S3 5695728
```

## Stato al 7 novembre 2026

Pubblicato: `main` a `60e4cc2` (`examples/shell/`: shell, ansiterm, ansifont con OFL, vi, edit). Release ancora v0.1.4: gli esempi non cambiano il firmware.

Scheda banco (seconda 4848S040, MAC `dc:b4:d9:04:87:c0`, senza relè): firmware v0.1.4, `/main.py` avvia la shell, meteo in `/bin/weather.py`, SD montata su `/sd`. Ctrl-C su riga vuota esce dalla shell: uno se non è stato digitato nulla, due entro 3 s dopo.

PR upstream #6 mergiata (`3ea92c1bb`, release v9.5.53). Il maintainer ha aperto la issue #10 (pool mai attivi su ESP32). Le 3 issue in bozza vanno ricontrollate: #7 e #8 upstream sembrano coprirne una parte.

### Lavoro in corso, NON nel commit
Quattro modifiche nel worktree, copia in `_private/esp32-pools-wip.patch`:
- `scripts/build_esp32.sh`: `OPL_SHA` a v9.5.53 (`0886d385c`); `.work/esp32/omnipython-lvgl` è già lì.
- `boards/esp32/ESP32_4848S040/mpconfigboard.h`: `LVMP_POOL_TLSF (1)`.
- `modules/esp32_usermods.cmake`: variante pool; `ESP_PLATFORM=1` per multi_heap, `LVMP_POOLS=tlsf` per TLSF.
- `modules/esp32_lvmp_tlsf.c` (nuovo): wrapper, senza toccare upstream.

Attenzione: con queste modifiche la build predefinita esce con multi_heap. Dopo aver aggiunto il define solo nell'header va forzata la rigenerazione del root pointer (`touch` su `lvgl_micropython_build.c`, cancellare `genhdr/qstr.i.last` e `genhdr/root_pointers.*`).

Firmware pronti in `dist/` (ignorata da git), con copia in `_private/firmware-opl9553/`, mai provati su scheda, hash in `ESP32_4848S040-opl9553.sha256`: `-opl9553-nopool.bin`, `-opl9553-multiheap.bin`, `-opl9553-tlsf.bin`.

### Prossimi passi, quando la scheda torna collegata
1. Identificare la scheda, poi provare nopool, multiheap, tlsf, con le stesse prove: soak, fps, audio, WiFi, e refresh con molti dati vivi nell'heap.
2. Con i numeri, l'utente decide cosa scrivere nella #10 (ha procurato l'hardware: il suo commento nella PR diceva di non averlo) e quale variante tenere. Nessun messaggio upstream senza il suo via libera.
3. Da fare a parte: bridge Bluetooth <-> USB host dell'utente verso la seriale, per il mini PC portatile (sequenze VT100, 115200, niente flow control, DTR/RTS fermi).

Caricamento file: `_private/hil-helpers/mkput.py`. Upload grossi: prima un soft reset (`uart_run.py corto.py grande.py --soft-reset`), e controllare il file sulla scheda. Gli altri script di prova della sessione (tasti per vi ed edit, backend vero di Thonny) stavano nella cartella temporanea e sono andati persi: per Thonny si esegue `bare_metal_backend.py` con `/usr/bin/python3`, passando gli argomenti come dict e i comandi con `serialize_message`.

### Promesse fatte upstream (risposta nella PR #6, 8 novembre)
L'utente ha scritto al maintainer che faremo:
1. **ESP32 (#10):** i risultati dei tre firmware (nopool, multiheap, tlsf) "soon". Insieme ai numeri va la scoperta sul secondo build senza `ESP_PLATFORM` e il rimedio.
2. **H7 su omnipython-lvgl:** rifare le misure dei pool (finora 575 -> 50-51 ms, ma su lvgl-micropython con la nostra patch) dopo aver portato le schede STM32 su omnipython-lvgl.
3. **H7 con heap piccolo in AXI SRAM:** il caso che il maintainer non ha misurato.
Gli abbiamo anche chiesto se sul GIGA c'era un blocco libero sotto i bytearray: aspettiamo la risposta.

### Test dei tre firmware opl9553 (10 novembre 2026, 06:12-07:10)
Runner e log in `_private/pool-esp32/` (run_all.sh, nopool.log, multiheap.log, tlsf.log). Tutte le prove RESULT: ok su tutte e tre le varianti. main.py rinominato durante i test e poi ripristinato. Sulla scheda resta **opl9553-tlsf** (non più v0.1.4).
Script layout del maintainer (480x480, due giri identici), fresh / one hole / many holes:
- nopool: refresh med 70.9 / 471.0 / 496.0 ms (max 72.1 / 471.6 / 506.2); 50 label 30.8 / 70 / 240.6 ms; collect 3.0 / 127.6 / 112.6 ms; bytearray 174 / 161 / 2885 us; free 4.76 MB.
- multiheap: refresh 70.9 / 70.9 / 70.9 (max 71.1 / 71.3 / 79.9); label 26.9 / 27 / 36.7; collect 15.7 / 121.6 / 122.5; bytearray 81 / 131 / 4187 us; free 4.51 MB.
- tlsf: refresh 70.9 / 70.8 / 70.8 (max 81.3 / 71.5 / 81.5); label 27.8 / 27.4 / 37.5; collect 15.8 / 121.8 / 122.4; bytearray 80 / 131 / 4180 us; free 4.51 MB.
t05_perf full refresh avg 96.5 / 93.3 / 93.1 ms (nopool/multiheap/tlsf), animazione 54.3-54.5 rps, 42.3 fps. Soak 15 min, 0 errori, memoria piatta: **nopool 47.7 rps, multiheap e tlsf 43.3 rps** (pool -9% nel soak, heap non frammentato). Audio ok (longest gap 22-25 ms), WiFi ok, throughput rumoroso 2-4.6 Mbit/s su tutte.
Risposta su #10: da preparare, nulla pubblicato.
**Aggiornamento 10 novembre, dopo i test:** commit locali dd01e02 (stm32 LVMP_POOLS=none) e 3cc2cbb (esp32 omnipython-lvgl v9.5.53, pool multi_heap predefiniti, LVMP_POOLS=tlsf|none), pushati su main il 10 novembre (60e4cc2..3cc2cbb). Il define LVMP_POOL_TLSF in mpconfigboard.h serve davvero (senza, i pool restano spenti per MICROPY_MALLOC_USES_ALLOCATED_SIZE=0). Sulla scheda ora c'è ESP32_4848S040-dd01e02-dirty (predefinito multi_heap); shell, meteo e raw REPL provati. Non rifatti i 10 esempi sul binding nuovo.
**Dopo la #15 upstream (10 novembre, 08:00-08:40):** omnipython-lvgl a c34fbee, pool TLSF crescenti opt-in con LVMP_POOL_TLSF (già nel nostro mpconfigboard.h). Commit a42cb13 pushato su main. Misure: pool costano 25 KB e +3.7 ms collect, soak 48.9 vs 47.6 rps; refresh 70.9 piatto vs 449-471 senza. Log `docs/log/esp32-pools-c34fbee-4848S040.txt`, grezzi in `_private/pool-esp32/c34-*.log`. Heap libero -128 KB rispetto a v9.5.53 anche senza pool (firmware +55 KB per l'assert handler #13, XIP da PSRAM: ipotesi). Sulla scheda: build con pool c34fbee, shell in autostart. Commento su #10 da pubblicare (issue chiusa da #15).
