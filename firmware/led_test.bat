@echo off
REM led_test.bat - Blink both status LEDs visibly on TX and RX simultaneously
REM Usage: led_test.bat [TX_PORT] [RX_PORT]
REM Default: TX=COM3  RX=COM5

setlocal
if "%1"=="" ( set TX=COM3 ) else ( set TX=%1 )
if "%2"=="" ( set RX=COM5 ) else ( set RX=%2 )

echo.
echo ============================================================
echo  LED Blink Test  -  TX: %TX%   RX: %RX%
echo  Watch BOTH boards for blinking LEDs
echo ============================================================
echo.

REM ── Step 1: confirm boards reachable ────────────────────────
echo [1/4] Checking TX on %TX%...
python -m mpremote connect %TX% exec "print('TX OK')" 2>nul || (echo [ERROR] Cannot reach TX on %TX% & exit /b 1)

echo [2/4] Checking RX on %RX%...
python -m mpremote connect %RX% exec "print('RX OK')" 2>nul || (echo [ERROR] Cannot reach RX on %RX% & exit /b 1)

REM ── Step 2: blink GPIO 0 (CONNECTED LED) ────────────────────
echo.
echo [3/4] Blinking GPIO 0 (CONNECTED LED) on BOTH boards - watch for slow blink...
echo       TX blinking now...
start "" python -m mpremote connect %TX% exec "from machine import Pin; import time; p=Pin(0,Pin.OUT); [p.toggle() or time.sleep_ms(500) for _ in range(10)]; p.value(0)"
echo       RX blinking now...
python -m mpremote connect %RX% exec "from machine import Pin; import time; p=Pin(0,Pin.OUT); [p.toggle() or time.sleep_ms(500) for _ in range(10)]; p.value(0)"
echo       Done. Did you see GPIO 0 blink on both boards? (5 flashes x 500ms each)

REM ── Step 3: blink GPIO 7 (SEARCHING LED) ────────────────────
echo.
echo [4/4] Blinking GPIO 7 (SEARCHING LED) on BOTH boards - watch for slow blink...
echo       TX blinking now...
start "" python -m mpremote connect %TX% exec "from machine import Pin; import time; p=Pin(7,Pin.OUT); [p.toggle() or time.sleep_ms(500) for _ in range(10)]; p.value(0)"
echo       RX blinking now...
python -m mpremote connect %RX% exec "from machine import Pin; import time; p=Pin(7,Pin.OUT); [p.toggle() or time.sleep_ms(500) for _ in range(10)]; p.value(0)"
echo       Done. Did you see GPIO 7 blink on both boards?

echo.
echo ============================================================
echo  If LEDs did NOT blink, run polarity_test.bat to check
echo  whether your LEDs are wired active-low instead of active-high
echo ============================================================
endlocal
