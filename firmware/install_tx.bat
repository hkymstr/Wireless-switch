@echo off
REM ─────────────────────────────────────────────────────────────
REM  install_tx.bat  -  Flash TRANSMITTER firmware to Pico 2 W
REM  Hardware v2  |  Wireless Race Car Switch System
REM
REM  Usage:
REM    install_tx.bat           (uses default COM3)
REM    install_tx.bat COM3      (specify port)
REM ─────────────────────────────────────────────────────────────

setlocal

if "%1"=="" (
    set PORT=COM3
) else (
    set PORT=%1
)

echo [TX INSTALL] Using port: %PORT%

REM Check mpremote is installed
python -m mpremote version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] mpremote not installed. Run:  pip install mpremote
    exit /b 1
)

REM Test connection
echo [TX INSTALL] Testing connection to Pico on %PORT%...
python -m mpremote connect %PORT% exec "import sys; print('MicroPython', sys.version)" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot connect to Pico on %PORT%.
    echo         Check USB cable and that MicroPython is flashed.
    echo         Flash MicroPython: hold BOOTSEL, plug USB, copy .uf2 to RPI-RP2 drive.
    exit /b 1
)

echo.
echo [WARNING] This will install TRANSMITTER firmware on Pico at %PORT%
echo           GPIO 1-5 will be switch inputs.  GPIO 0 and 7 are status LEDs.
set /p CONFIRM=Continue? [y/N]:
if /i not "%CONFIRM%"=="y" (
    echo Aborted.
    exit /b 0
)

REM Get script directory
set SCRIPT_DIR=%~dp0

echo [TX INSTALL] Uploading config.py...
python -m mpremote connect %PORT% cp "%SCRIPT_DIR%config.py" :config.py
if errorlevel 1 ( echo [ERROR] Failed to upload config.py & exit /b 1 )

echo [TX INSTALL] Uploading tx_main.py as main.py...
python -m mpremote connect %PORT% cp "%SCRIPT_DIR%tx_main.py" :main.py
if errorlevel 1 ( echo [ERROR] Failed to upload main.py & exit /b 1 )

echo [TX INSTALL] Files on device:
python -m mpremote connect %PORT% ls

echo.
echo [TX INSTALL] SUCCESS - Transmitter firmware installed.
echo             Power-cycle the Pico to start the transmitter.
echo.
echo   GPIO assignments:
echo     GPIO 0  - CONNECTED LED  (solid when RX linked)
echo     GPIO 7  - SEARCHING LED  (flashes until RX connects)
echo     GPIO 1  - Switch 1 input
echo     GPIO 2  - Switch 2 input
echo     GPIO 3  - Switch 3 input
echo     GPIO 4  - Switch 4 input
echo     GPIO 5  - Switch 5 input

endlocal
