# Wireless Race Car Switch System — Hardware v2 (Bluetooth)

A fully wireless switch panel for a race car using two **Raspberry Pi Pico 2 W** boards.  
One board acts as the **Transmitter** (switch panel), the other as the **Receiver** (12 V output driver).  
This branch uses **Bluetooth Low Energy (BLE)** instead of WiFi — lower TX power, point-to-point
link, and faster reconnect.

> **WiFi version:** see the `hardware-v2` branch.

---

## System Overview

```
 ┌──────────────────────────┐     Bluetooth BLE      ┌─────────────────────────────┐
 │      TRANSMITTER         │ ──── GATT notify ────► │        RECEIVER             │
 │    Raspberry Pi Pico 2W  │       20 Hz            │    Raspberry Pi Pico 2W     │
 │                          │                        │                             │
 │  GPIO 1-5 ← 5 switches   │  Peripheral/Server     │  GPIO 8-11 → 4× MOSFET     │
 │  GPIO 0  → Connected LED │  Advertises by name    │  GPIO 12   → Relay K2      │
 │  GPIO 7  → Searching LED │                        │  GPIO 0    → Connected LED  │
 │  Powered from 12 V via   │  Central/Client        │  GPIO 7    → Searching LED  │
 │  on-board 5 V regulator  │  Scans → connects      │  Takes 12 V from car        │
 └──────────────────────────┘                        └─────────────────────────────┘
```

**TX** advertises as `WirelessSwitch-TX`. **RX** scans, connects, and receives switch-state
notifications. No pairing or password required.

---

## GPIO Pin Mapping — Hardware v2

### Status LEDs (identical on both boards)

| GPIO | Function      | Behaviour                                    |
|------|---------------|----------------------------------------------|
|  0   | CONNECTED LED | Solid ON when BLE link is up                 |
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
│   ├── config.py        Shared configuration (BLE settings, GPIO, channel modes)
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

### Noise reduction (recommended for race car)
- 100 µF electrolytic + 100 nF ceramic capacitor on each board's power input (VSYS to GND)
- Mount boards in a grounded metal enclosure
- A small drop of hot glue on the inductor next to the Pico's USB connector reduces coil whine

---

## Software Installation

### Step 1 — Flash MicroPython to each Pico 2 W

1. Download the **Pico 2 W** MicroPython UF2 from  
   `https://micropython.org/download/RPI_PICO2_W/`
2. Hold **BOOTSEL**, plug USB — Pico appears as `RPI-RP2` mass storage
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
./install_tx.sh /dev/ttyACM0    # specify port if needed
```

Confirm success: the board should blink its SEARCHING LED **3× quickly**, then start flashing slowly.

### Step 4 — Install Receiver firmware

**Windows** (default COM5):
```bat
install_rx.bat
install_rx.bat COM4    ← specify a different port if needed
```

**Linux / macOS:**
```bash
./install_rx.sh
```

### Step 5 — Verify installation (optional, Windows)

With both boards connected:
```bat
verify.bat COM3 COM5
led_test.bat COM3 COM5
```

### Step 6 — Configure channel modes (optional)

Edit `firmware/config.py` before installing the receiver to set each channel's behaviour:

```python
CHANNEL_MODES = [
    MODE_MOMENTARY,   # CH1 – output ON while switch held, OFF when released
    MODE_LATCH,       # CH2 – each press toggles output ON / OFF
    MODE_MOMENTARY,   # CH3
    MODE_MOMENTARY,   # CH4
    MODE_LATCH,       # CH5 relay
]
```

Re-run `install_rx.bat` after any config change.

---

## Operation

1. **Power on the Transmitter.** The SEARCHING LED blinks **3× quickly** to confirm firmware
   is running, then flashes slowly while advertising `WirelessSwitch-TX` over BLE.
2. **Power on the Receiver.** Same 3× startup blink, then SEARCHING LED flashes while scanning.
3. Once connected, both boards show **CONNECTED LED solid ON** and SEARCHING LED turns off.
4. Pressing a switch on the transmitter activates the corresponding output on the receiver
   according to that channel's configured mode (momentary or latch).
5. **On link loss:** the receiver holds its last output states for **10 seconds**
   while it searches for the transmitter. If reconnected within 10 s, outputs resume
   with no interruption. If disconnected for more than 10 s, all outputs turn off.

### Link Parameters

| Parameter           | Value                          |
|---------------------|--------------------------------|
| Update rate         | 20 Hz (every 50 ms)            |
| Link timeout        | 2 s                            |
| Hold on disconnect  | 10 s before outputs release    |
| Transport           | Bluetooth Low Energy (BLE 5.2) |
| TX role             | Peripheral / GATT server       |
| RX role             | Central / GATT client          |
| BLE device name     | `WirelessSwitch-TX`            |

---

## Channel Modes

Each of the five output channels can be independently set in `config.py`:

| Mode            | Constant        | Behaviour                                        |
|-----------------|-----------------|--------------------------------------------------|
| Momentary       | `MODE_MOMENTARY`| Output follows the switch — ON while held, OFF when released |
| Latch (toggle)  | `MODE_LATCH`    | First press turns output ON; next press turns it OFF |

Latch state is preserved through brief disconnects (within the 10 s hold window).
A disconnection longer than 10 s resets all latch states to OFF.

---

## Monitoring with a Phone

Install **nRF Connect** (Nordic Semiconductor, free) or **LightBlue** (Punch Through) on
an iPhone or Android phone. Both apps can scan and see `WirelessSwitch-TX` in the device
list, showing signal strength (RSSI) and advertisement data. This is useful for confirming
the TX is powered and advertising before the RX is connected.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No 3× startup blink on TX or RX | Firmware not installed | Re-run the installer; confirm `main.py` and `config.py` appear with `mpremote connect COMx ls` |
| SEARCHING LED flashes indefinitely on RX | TX not in range or not powered | Confirm TX shows SEARCHING LED flashing (advertising); bring boards within 2 m for initial pairing |
| Connected LED goes solid then drops back to searching | BLE link unstable | Move boards closer; check for 2.4 GHz interference from other devices |
| TX CONNECTED LED stays green but RX searches | TX disconnect IRQ delayed | Power-cycle both boards; they will re-establish the link automatically |
| Outputs don't activate | Wrong firmware on board | Confirm TX has `tx_main.py` installed as `main.py` and RX has `rx_main.py` |
| Latch output stuck ON after power cycle | Expected — latch state is not saved across reboots | Press the switch once to toggle off, or power-cycle with switch released |
| Coil whine from board | RT6150 switching regulator | Add 100 µF cap on VSYS; apply hot glue to inductor near USB connector |
| `mpremote` cannot find device | Driver missing or wrong port | Run `python -m mpremote connect list` to list available ports |
| Pico not detected as storage drive | Not holding BOOTSEL | Hold BOOTSEL before plugging USB |

---

## Protocol Reference

BLE GATT notification payload (7 bytes, TX → RX, 20 Hz):

```
Byte 0   : 0xAA  (start marker)
Byte 1   : Switch 1 state  (0 = open, 1 = pressed)
Byte 2   : Switch 2 state
Byte 3   : Switch 3 state
Byte 4   : Switch 4 state
Byte 5   : Switch 5 state
Byte 6   : Checksum  = (SW1+SW2+SW3+SW4+SW5) & 0xFF
```

BLE service UUID:       `12345678-1234-5678-1234-56789abcdef0`  
Characteristic UUID:    `12345678-1234-5678-1234-56789abcdef1`  
Characteristic flags:   NOTIFY
