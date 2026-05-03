@echo off
REM ─────────────────────────────────────────────────────────────
REM  install_rx.bat  -  Flash RECEIVER firmware to Pico 2 W
REM  Hardware v2  |  Wireless Race Car Switch System
REM
REM  Usage:
REM    install_rx.bat           (uses default COM5)
REM    install_rx.bat COM5      (specify port)
REM ─────────────────────────────────────────────────────────────

setlocal

if "%1"=="" (
    set PORT=COM5
) else (
    set PORT=%1
)

echo [RX INSTALL] Using port: %PORT%

REM Check mpremote is installed
python -m mpremote version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] mpremote not installed. Run:  pip install mpremote
    exit /b 1
)

REM Test connection
echo [RX INSTALL] Testing connection to Pico on %PORT%...
python -m mpremote connect %PORT% exec "import sys; print('MicroPython', sys.version)" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot connect to Pico on %PORT%.
    echo         Check USB cable and that MicroPython is flashed.
    echo         Flash MicroPython: hold BOOTSEL, plug USB, copy .uf2 to RPI-RP2 drive.
    exit /b 1
)

echo.
echo [WARNING] This will install RECEIVER firmware on Pico at %PORT%
echo           GPIO 8-12 will be outputs.  GPIO 0 and 7 are status LEDs.
set /p CONFIRM=Continue? [y/N]:
if /i not "%CONFIRM%"=="y" (
    echo Aborted.
    exit /b 0
)

REM Get script directory
set SCRIPT_DIR=%~dp0

echo [RX INSTALL] Uploading config.py...
python -m mpremote connect %PORT% cp "%SCRIPT_DIR%config.py" :config.py
if errorlevel 1 ( echo [ERROR] Failed to upload config.py & exit /b 1 )

echo [RX INSTALL] Uploading rx_main.py as main.py...
python -m mpremote connect %PORT% cp "%SCRIPT_DIR%rx_main.py" :main.py
if errorlevel 1 ( echo [ERROR] Failed to upload main.py & exit /b 1 )

echo [RX INSTALL] Files on device:
python -m mpremote connect %PORT% ls

echo.
echo [RX INSTALL] SUCCESS - Receiver firmware installed.
echo             Power-cycle the Pico to start the receiver.
echo.
echo   GPIO assignments:
echo     GPIO  0  - CONNECTED LED  (solid when TX linked)
echo     GPIO  7  - SEARCHING LED  (flashes until TX connects)
echo     GPIO  8  - Channel 1 output (MOSFET, up to 5A)
echo     GPIO  9  - Channel 2 output (MOSFET, up to 5A)
echo     GPIO 10  - Channel 3 output (MOSFET, up to 5A)
echo     GPIO 11  - Channel 4 output (MOSFET, up to 5A)
echo     GPIO 12  - Channel 5 output (Relay K2, SPDT)

endlocal
