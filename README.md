# Wireless Race Car Switch System — Hardware v2 (WiFi)

A fully wireless switch panel for a race car using two **Raspberry Pi Pico 2 W** boards.  
One board acts as the **Transmitter** (switch panel), the other as the **Receiver** (12 V output driver).

> **Bluetooth version:** see the `bluetooth` branch.

---

## System Overview

```
 ┌──────────────────────────┐      WiFi (AP/STA)      ┌─────────────────────────────┐
 │      TRANSMITTER         │ ◄──── UDP 20 Hz ──────► │        RECEIVER             │
 │    Raspberry Pi Pico 2W  │                          │    Raspberry Pi Pico 2W     │
 │                          │  Web UI: 192.168.4.1     │  Web UI: <RX-IP>            │
 │  GPIO 1-5 ← 5 switches   │                          │  GPIO 8-11 → 4× MOSFET     │
 │  GPIO 0  → Connected LED │                          │  GPIO 12   → Relay K2      │
 │  GPIO 7  → Searching LED │                          │  GPIO 0    → Connected LED  │
 │  Powered from 12 V via   │                          │  GPIO 7    → Searching LED  │
 │  on-board 5 V regulator  │                          │  Takes 12 V from car        │
 └──────────────────────────┘                          └─────────────────────────────┘
```

TX creates an **open WiFi access point** (`WirelessSwitch-1` by default). RX connects as a station.  
Both boards host a **web settings page** — join the WiFi network and open a browser to configure.

---

## Web Interface

| Board | URL | What you can change |
|-------|-----|---------------------|
| TX | `http://192.168.4.1` | Pair ID |
| RX | `http://<RX-IP>` (linked from TX page) | Pair ID, hold time, channel modes |

Connect any phone or laptop to the `WirelessSwitch-N` WiFi network (no password), then open the URL above. Settings are saved to flash and survive power cycles.

---

## GPIO Pin Mapping — Hardware v2

### Status LEDs (identical on both boards)

| GPIO | Function      | Behaviour                                     |
|------|---------------|-----------------------------------------------|
|  0   | CONNECTED LED | Solid ON when wireless link is up             |
|  7   | SEARCHING LED | Flashes 2 Hz while searching; OFF when linked |

### Transmitter — Switch Inputs

Switches are **active-low** (connect switch between GPIO pin and GND).  
Internal pull-ups enabled in firmware.

| GPIO | Channel | Description    |
|------|---------|----------------|
|  1   | SW1     | Switch 1 input |
|  2   | SW2     | Switch 2 input |
|  3   | SW3     | Switch 3 input |
|  4   | SW4     | Switch 4 input |
|  5   | SW5     | Switch 5 input |

### Receiver — Output Channels

Outputs are **active-high** (GPIO HIGH = output energised).

| GPIO | Channel | Type            | Max Load         |
|------|---------|-----------------|------------------|
|  8   | CH1     | N-ch MOSFET     | 5 A @ 12 V       |
|  9   | CH2     | N-ch MOSFET     | 5 A @ 12 V       |
| 10   | CH3     | N-ch MOSFET     | 5 A @ 12 V       |
| 11   | CH4     | N-ch MOSFET     | 5 A @ 12 V       |
| 12   | CH5     | Relay K2 (SPDT) | Per relay rating |

---

## Repository Structure

```
├── kicad/
│   ├── wireless_switch.kicad_pro   KiCad project file
│   ├── wireless_switch.kicad_sch   Top-level schematic
│   ├── Pico_interface.kicad_sch    Pico 2 W GPIO interface sub-sheet
│   ├── analog_in.kicad_sch         Output channel sub-sheet (MOSFET + relay)
│   ├── input_power.kicad_sch       12 V → 5 V power supply sub-sheet
│   ├── wireless_switch.kicad_pcb   PCB layout
│   └── sym-lib-table               KiCad symbol library table
│
├── firmware/
│   ├── config.py        Shared configuration (defaults – overridden by web UI)
│   ├── tx_main.py       Transmitter MicroPython firmware
│   ├── rx_main.py       Receiver MicroPython firmware
│   ├── install_tx.bat   Windows transmitter installer  (default COM3)
│   ├── install_rx.bat   Windows receiver installer     (default COM5)
│   ├── install_tx.sh    Linux / macOS transmitter installer
│   ├── install_rx.sh    Linux / macOS receiver installer
│   ├── verify.bat       18-point verification script (Windows)
│   ├── led_test.bat     LED blink test (Windows)
│   └── polarity_test.bat  LED polarity / GPIO finder (Windows)
│
└── docs/
    └── wireless_switch.pdf   Full schematic PDF
```

---

## Hardware Requirements

### Per Board (× 2)
- Raspberry Pi Pico 2 W
- PCB from `kicad/wireless_switch.kicad_pcb`

### Transmitter PCB BOM additions
- 5× panel-mount toggle switches (SPDT or SPST)
- 2× LEDs with 330 Ω series resistors for GPIO 0 & 7
- 12 V → 5 V onboard regulator + capacitors (see `input_power.kicad_sch`)

### Receiver PCB BOM additions
- 4× N-channel logic-level MOSFETs (e.g. IRLZ44N) with gate resistors
- 1× 12 V SPDT relay K2 (Omron G5V-1 or equivalent)
- Relay driver transistor + flyback diodes
- Fusing on each output channel

---

## Software Installation

### Step 1 — Flash MicroPython to each Pico 2 W

1. Download the **Pico 2 W** MicroPython UF2 from  
   `https://micropython.org/download/RPI_PICO2_W/`
2. Hold **BOOTSEL**, plug USB → Pico appears as `RPI-RP2` mass storage
3. Drag the `.uf2` onto the drive — Pico reboots automatically

### Step 2 — Install `mpremote`

```bash
pip install mpremote
```

### Step 3 — Install Transmitter firmware

**Windows** (default COM3):
```bat
cd firmware
install_tx.bat
install_tx.bat COM4    ← specify a different port if needed
```

**Linux / macOS:**
```bash
cd firmware
chmod +x install_tx.sh && ./install_tx.sh
```

Confirm: board blinks SEARCHING LED **3× quickly** then flashes slowly.

### Step 4 — Install Receiver firmware

**Windows** (default COM5):
```bat
install_rx.bat
```

**Linux / macOS:**
```bash
./install_rx.sh
```

### Step 5 — Verify (optional, Windows)

```bat
verify.bat COM3 COM5
led_test.bat COM3 COM5
```

---

## Operation

1. **Power on both boards.** Both blink the SEARCHING LED **3× quickly** to confirm firmware is running.
2. TX creates an open WiFi access point. Both boards flash their SEARCHING LED while waiting for a link.
3. Once linked, **CONNECTED LED turns solid** on both boards; SEARCHING LED turns off.
4. Pressing a switch on TX activates the corresponding output on RX according to that channel's mode.
5. **On link loss:** RX holds its last output states for the configured hold time (default 10 s), then turns all outputs off. Both boards resume searching.

### Link Parameters

| Parameter           | Value                  |
|---------------------|------------------------|
| Update rate         | 20 Hz (every 50 ms)    |
| Link timeout        | 2 s                    |
| Hold on disconnect  | 10 s (configurable)    |
| Protocol            | UDP port 4210          |
| WiFi mode           | TX = AP, RX = Station  |
| Network             | Open (no password)     |

---

## Channel Modes

Each output channel can be set independently via the RX web interface:

| Mode      | Behaviour                                            |
|-----------|------------------------------------------------------|
| Momentary | Output ON while switch is held; OFF when released    |
| Latch     | First press turns output ON; next press turns it OFF |

Latch state is preserved through brief disconnects (within hold window).  
A disconnection longer than the hold time resets all latch states to OFF.

---

## Multiple Pairs

If two TX/RX pairs operate at the same time, each pair needs a unique **Pair ID** so they don't cross-connect.

Set the same Pair ID on both boards in a pair via the web interface:

| Pair | TX SSID         | RX connects to  |
|------|-----------------|-----------------|
|  1   | WirelessSwitch-1 | WirelessSwitch-1 |
|  2   | WirelessSwitch-2 | WirelessSwitch-2 |

**Procedure for changing Pair ID:**
1. Connect to the current WiFi network
2. Open RX settings → change Pair ID → Save (RX reboots, now looks for new SSID)
3. Open TX settings (192.168.4.1) → change Pair ID → Save (TX reboots with new SSID)
4. RX reconnects automatically

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No 3× startup blink | Firmware not installed | Re-run the installer; verify MicroPython UF2 was flashed first |
| SEARCHING LED never stops flashing | Wrong Pair ID or TX not powered | Check both boards have the same Pair ID; confirm TX SEARCHING LED is also flashing |
| TX AP has stale WPA2 password | Old security settings cached in chip | Firmware resets the AP before configuring — power-cycle TX |
| Can't open web interface | Not connected to WirelessSwitch-N WiFi | Join the WiFi network first (no password), then open the URL |
| RX web page not reachable | RX IP unknown | Open TX page (192.168.4.1) first — it shows a clickable link to the RX page |
| Outputs don't activate | Wrong firmware on board | Confirm TX has `tx_main.py` installed as `main.py` |
| Latch output stuck after reboot | Expected — latch state is in RAM only | Press the switch once to toggle off |
| `mpremote` cannot find device | Driver missing or wrong port | Run `python -m mpremote connect list` |
| Pico not detected as storage | Not holding BOOTSEL | Hold BOOTSEL before plugging USB |

---

## Protocol Reference

UDP packet format (7 bytes, TX → RX, port 4210):

```
Byte 0   : 0xAA  (start marker)
Byte 1   : Switch 1 state  (0 = open, 1 = pressed)
Byte 2   : Switch 2 state
Byte 3   : Switch 3 state
Byte 4   : Switch 4 state
Byte 5   : Switch 5 state
Byte 6   : Checksum  = (SW1+SW2+SW3+SW4+SW5) & 0xFF
```

RX → TX heartbeat: `b"RXHERE"` (6 bytes, every 50 ms) — tells TX the RX's IP address.
