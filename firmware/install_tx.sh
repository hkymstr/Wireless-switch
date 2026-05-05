#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  install_tx.sh  –  Flash TRANSMITTER firmware to Pico 2 W
#  Hardware v2  |  Wireless Race Car Switch System
#
#  Prerequisites
#  -------------
#  1. Python 3.7+ installed
#  2. mpremote  : pip install mpremote
#  3. MicroPython flashed on the Pico 2 W
#     Download from: https://micropython.org/download/RPI_PICO2_W/
#     Flash with: hold BOOTSEL, plug USB, copy .uf2 to RPI-RP2 drive
#
#  Usage
#  -----
#    ./install_tx.sh              # auto-detect port
#    ./install_tx.sh /dev/ttyACM1 # specify port
# ─────────────────────────────────────────────────────────────

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()  { echo -e "${GREEN}[TX INSTALL]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARNING]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Dependency checks ────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || error "python3 not found"
python3 -m mpremote version >/dev/null 2>&1 \
    || error "mpremote not installed. Run: pip install mpremote"

# ── Port selection ───────────────────────────────────────────
if [[ $# -ge 1 ]]; then
    PORT="connect $1"
else
    PORT="auto"
fi

info "Using port: ${PORT}"
info "Testing connection to Pico…"
python3 -m mpremote "${PORT}" exec "import sys; print(sys.version)" \
    || error "Cannot connect to Pico. Check USB cable and MicroPython installation."

# ── Confirm role ─────────────────────────────────────────────
echo ""
warn "This will install TRANSMITTER firmware on the connected Pico 2 W."
warn "GPIO 1-5 will be switch inputs.  GPIO 0 & 7 are status LEDs."
read -r -p "Continue? [y/N] " confirm
[[ "${confirm,,}" == "y" ]] || { info "Aborted."; exit 0; }

# ── Upload files ─────────────────────────────────────────────
info "Uploading config.py…"
python3 -m mpremote "${PORT}" cp "${SCRIPT_DIR}/config.py" :config.py

info "Uploading tx_main.py as main.py (auto-runs on boot)…"
python3 -m mpremote "${PORT}" cp "${SCRIPT_DIR}/tx_main.py" :main.py

# ── Verify ───────────────────────────────────────────────────
info "Files on device:"
python3 -m mpremote "${PORT}" ls

echo ""
info "✓ Transmitter firmware installed successfully."
info "  Power-cycle the Pico to start the transmitter."
info ""
info "  GPIO assignments:"
info "    GPIO 0  – CONNECTED LED (solid when RX linked)"
info "    GPIO 7  – SEARCHING LED (flashes until RX connects)"
info "    GPIO 1  – Switch 1 input"
info "    GPIO 2  – Switch 2 input"
info "    GPIO 3  – Switch 3 input"
info "    GPIO 4  – Switch 4 input"
info "    GPIO 5  – Switch 5 input"
