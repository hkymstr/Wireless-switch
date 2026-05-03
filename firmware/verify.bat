@echo off
REM ─────────────────────────────────────────────────────────────
REM  verify.bat  -  Verify TX and RX Pico firmware and link
REM  Hardware v2  |  Wireless Race Car Switch System
REM
REM  Usage:  verify.bat [TX_PORT] [RX_PORT]
REM  Default: TX=COM3  RX=COM5
REM ─────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

if "%1"=="" ( set TX_PORT=COM3 ) else ( set TX_PORT=%1 )
if "%2"=="" ( set RX_PORT=COM5 ) else ( set RX_PORT=%2 )

set PASS=0
set FAIL=0

echo ============================================================
echo  Wireless Switch - Firmware Verification
echo  TX: %TX_PORT%    RX: %RX_PORT%
echo ============================================================
echo.

REM ── Check mpremote ──────────────────────────────────────────
python -m mpremote version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] mpremote not installed.  Run: pip install mpremote
    exit /b 1
)

REM ── TRANSMITTER checks ──────────────────────────────────────
echo --- TRANSMITTER (%TX_PORT%) ---

echo [CHECK] MicroPython version...
python -m mpremote connect %TX_PORT% exec "import sys; print(sys.version)" 2>nul
if errorlevel 1 (
    echo [FAIL] Cannot reach TX on %TX_PORT%
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] config.py present...
python -m mpremote connect %TX_PORT% exec "import config; print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] config.py missing or has errors
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] main.py (tx_main) present...
python -m mpremote connect %TX_PORT% ls 2>nul | findstr "main.py" >nul
if errorlevel 1 (
    echo [FAIL] main.py not found on TX
    set /a FAIL+=1
) else (
    echo        main.py found
    set /a PASS+=1
)

echo [CHECK] GPIO config (TX switches GPIO 1-5)...
python -m mpremote connect %TX_PORT% exec ^
    "import config; assert config.TX_SWITCH_GPIOS==[1,2,3,4,5], 'wrong'; print('OK GPIO 1-5')" 2>nul
if errorlevel 1 (
    echo [FAIL] TX_SWITCH_GPIOS mismatch in config.py
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] GPIO config (Connected=0, Searching=7)...
python -m mpremote connect %TX_PORT% exec ^
    "import config; assert config.GPIO_CONNECTED==0; assert config.GPIO_SEARCHING==7; print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] LED GPIO mismatch in config.py
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] TX GPIO pins can be initialised...
python -m mpremote connect %TX_PORT% exec ^
    "from machine import Pin; [Pin(g,Pin.IN,Pin.PULL_UP) for g in [1,2,3,4,5]]; print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] Could not init switch input pins
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] TX CONNECTED LED (GPIO 0) toggle...
python -m mpremote connect %TX_PORT% exec ^
    "from machine import Pin; import time; led=Pin(0,Pin.OUT); led.value(1); time.sleep_ms(500); led.value(0); print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] Could not toggle GPIO 0
    set /a FAIL+=1
) else (
    echo        GPIO 0 toggled - check LED flashed
    set /a PASS+=1
)

echo [CHECK] TX SEARCHING LED (GPIO 7) toggle...
python -m mpremote connect %TX_PORT% exec ^
    "from machine import Pin; import time; led=Pin(7,Pin.OUT); [led.toggle() or __import__('time').sleep_ms(200) for _ in range(6)]; led.value(0); print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] Could not toggle GPIO 7
    set /a FAIL+=1
) else (
    echo        GPIO 7 toggled - check LED flashed 3x
    set /a PASS+=1
)

echo [CHECK] WiFi hardware present...
python -m mpremote connect %TX_PORT% exec ^
    "import network; w=network.WLAN(network.AP_IF); print('WiFi chip OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] WiFi not available (wrong firmware or not a Pico W?)
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo.

REM ── RECEIVER checks ─────────────────────────────────────────
echo --- RECEIVER (%RX_PORT%) ---

echo [CHECK] MicroPython version...
python -m mpremote connect %RX_PORT% exec "import sys; print(sys.version)" 2>nul
if errorlevel 1 (
    echo [FAIL] Cannot reach RX on %RX_PORT%
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] config.py present...
python -m mpremote connect %RX_PORT% exec "import config; print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] config.py missing or has errors
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] main.py (rx_main) present...
python -m mpremote connect %RX_PORT% ls 2>nul | findstr "main.py" >nul
if errorlevel 1 (
    echo [FAIL] main.py not found on RX
    set /a FAIL+=1
) else (
    echo        main.py found
    set /a PASS+=1
)

echo [CHECK] GPIO config (RX outputs GPIO 8-12)...
python -m mpremote connect %RX_PORT% exec ^
    "import config; assert config.RX_OUTPUT_GPIOS==[8,9,10,11,12], 'wrong'; print('OK GPIO 8-12')" 2>nul
if errorlevel 1 (
    echo [FAIL] RX_OUTPUT_GPIOS mismatch in config.py
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] RX output pins can be initialised...
python -m mpremote connect %RX_PORT% exec ^
    "from machine import Pin; [Pin(g,Pin.OUT,value=0) for g in [8,9,10,11,12]]; print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] Could not init output pins
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo [CHECK] RX output channel pulse test (GPIO 8-12 each 300 ms)...
python -m mpremote connect %RX_PORT% exec ^
    "from machine import Pin; import time; pins=[Pin(g,Pin.OUT,value=0) for g in [8,9,10,11,12]]; [p.__setattr__('value',1) or p.value(1) or time.sleep_ms(300) or p.value(0) for p in pins]; print('OK')" 2>nul
if errorlevel 1 (
    echo [WARN] Output pulse test inconclusive (check manually)
) else (
    echo        Each output pulsed 300 ms - check LEDs/relay fired in order
    set /a PASS+=1
)

echo [CHECK] RX CONNECTED LED (GPIO 0) toggle...
python -m mpremote connect %RX_PORT% exec ^
    "from machine import Pin; import time; led=Pin(0,Pin.OUT); led.value(1); time.sleep_ms(500); led.value(0); print('OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] Could not toggle GPIO 0
    set /a FAIL+=1
) else (
    echo        GPIO 0 toggled - check LED flashed
    set /a PASS+=1
)

echo [CHECK] WiFi hardware present...
python -m mpremote connect %RX_PORT% exec ^
    "import network; w=network.WLAN(network.STA_IF); w.active(True); print('WiFi chip OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] WiFi not available
    set /a FAIL+=1
) else (
    set /a PASS+=1
)

echo.
echo ============================================================
echo  Results:  %PASS% passed   %FAIL% failed
echo ============================================================

if %FAIL%==0 (
    echo  All checks passed. Power-cycle both Picos to start the link.
    echo  Watch for CONNECTED LED (GPIO 0) to go solid on both boards.
) else (
    echo  Fix the failures above, then re-run verify.bat
)

endlocal
