@echo off
REM polarity_test.bat
REM Determines whether LEDs are active-high or active-low, and finds
REM which GPIO each LED is actually wired to.
REM
REM Usage: polarity_test.bat [PORT]
REM Default port: COM3  (run once for TX, once for RX)

setlocal
if "%1"=="" ( set PORT=COM3 ) else ( set PORT=%1 )

echo.
echo ============================================================
echo  LED Polarity + GPIO Finder  -  Port: %PORT%
echo  Answer Y/N at each prompt. Keep your eyes on the board.
echo ============================================================

python -m mpremote connect %PORT% exec "print('Connected OK')" 2>nul || (echo [ERROR] Cannot reach device on %PORT% & exit /b 1)

REM ── Test GPIO 0, active-high ─────────────────────────────────
echo.
echo TEST 1: GPIO 0 held HIGH for 3 seconds...
python -m mpremote connect %PORT% exec "from machine import Pin; import time; p=Pin(0,Pin.OUT); p.value(1); time.sleep_ms(3000); p.value(0)"
set /p A1=Did an LED light up? [Y/N]:
if /i "%A1%"=="Y" ( echo [RESULT] GPIO 0 is CONNECTED LED - wired ACTIVE HIGH & goto :gpio7 )

REM ── Test GPIO 0, active-low ──────────────────────────────────
echo TEST 2: GPIO 0 held LOW for 3 seconds (other LED may turn off)...
python -m mpremote connect %PORT% exec "from machine import Pin; import time; p=Pin(0,Pin.OUT); p.value(0); time.sleep_ms(3000)"
set /p A2=Did an LED light up? [Y/N]:
if /i "%A2%"=="Y" ( echo [RESULT] GPIO 0 is CONNECTED LED - wired ACTIVE LOW & goto :gpio7 )

echo [NOTE] GPIO 0 LED not confirmed. Trying nearby pins...
for %%G in (1 2 3 4 5 6) do (
    echo Testing GPIO %%G HIGH for 2 seconds...
    python -m mpremote connect %PORT% exec "from machine import Pin; import time; p=Pin(%%G,Pin.OUT); p.value(1); time.sleep_ms(2000); p.value(0)"
    set /p AX=Did an LED light up on GPIO %%G? [Y/N]:
    if /i "!AX!"=="Y" echo [RESULT] CONNECTED LED appears to be on GPIO %%G
)

:gpio7
echo.
echo ── Now testing GPIO 7 (SEARCHING LED) ──────────────────────
echo TEST: GPIO 7 held HIGH for 3 seconds...
python -m mpremote connect %PORT% exec "from machine import Pin; import time; p=Pin(7,Pin.OUT); p.value(1); time.sleep_ms(3000); p.value(0)"
set /p B1=Did an LED light up? [Y/N]:
if /i "%B1%"=="Y" ( echo [RESULT] GPIO 7 is SEARCHING LED - wired ACTIVE HIGH & goto :done )

echo TEST: GPIO 7 held LOW for 3 seconds...
python -m mpremote connect %PORT% exec "from machine import Pin; import time; p=Pin(7,Pin.OUT); p.value(0); time.sleep_ms(3000)"
set /p B2=Did an LED light up? [Y/N]:
if /i "%B2%"=="Y" ( echo [RESULT] GPIO 7 is SEARCHING LED - wired ACTIVE LOW & goto :done )

echo [NOTE] GPIO 7 LED not confirmed. Trying nearby pins...
for %%G in (6 8 9 10) do (
    echo Testing GPIO %%G HIGH for 2 seconds...
    python -m mpremote connect %PORT% exec "from machine import Pin; import time; p=Pin(%%G,Pin.OUT); p.value(1); time.sleep_ms(2000); p.value(0)"
    set /p BX=Did an LED light up on GPIO %%G? [Y/N]:
    if /i "!BX!"=="Y" echo [RESULT] SEARCHING LED appears to be on GPIO %%G
)

:done
echo.
echo ============================================================
echo  Polarity test complete. Report the [RESULT] lines above
echo  so firmware config.py can be updated if needed.
echo ============================================================
endlocal
