# Wireless Race Car Switch System — Hardware v2

A fully wireless switch panel for a race car using two **Raspberry Pi Pico 2 W** boards.  
One board acts as the **Transmitter** (switch panel), the other as the **Receiver** (12 V output driver).  
Both boards use identical PCBs; firmware determines the role.

---

## System Overview

```
 ┌──────────────────────────┐      WiFi (AP/STA)      ┌─────────────────────────────┐
 │      TRANSMITTER         │ ◄──── UDP 20 Hz ──────► │        RECEIVER             │
 │    Raspberry Pi Pico 2W  │                          │    Raspberry Pi Pico 2W     │
 │                          │                          │                             │
 │  GPIO 1-5 ← 5 switches   │                          │  GPIO 8-11 → 4× MOSFET     │
 │  GPIO 0  → Connected LED │                          │  GPIO 12   → Relay K2      │
 │  GPIO 7  → Searching LED │                          │  GPIO 0    → Connected LED  │
 │  Powered from 12 V via   │                          │  GPIO 7    → Searching LED  │
 │  on-board 5 V regulator  │                          │  Takes 12 V from car        │
 └──────────────────────────┘                          └─────────────────────────────┘
```

---

## GPIO Pin Mapping — Hardware v2

### Status LEDs (identical on both boards)

| GPIO | Function          | Behaviour                        |
|------|-------------------|----------------------------------|
|  0   | CONNECTED LED     | Solid ON when wireless link is up |
|  7   | SEARCHING LED     | Flashes 2 Hz while searching; OFF when linked |

### Transmitter — Switch Inputs

Switches are **active-low** (connect switch between GPIO pin and GND).  
Internal pull-ups enabled in firmware.

| GPIO | Channel | Description   |
|------|---------|---------------|
|  1   | SW1     | Switch 1 input |
|  2   | SW2     | Switch 2 input |
|  3   | SW3     | Switch 3 input |
|  4   | SW4     | Switch 4 input |
|  5   | SW5     | Switch 5 input |

### Receiver — Output Channels

Outputs are **active-high** (GPIO HIGH = output energised).  
All outputs are forced **OFF** if the wireless link is lost.

| GPIO | Channel | Type         | Max Load        |
|------|---------|--------------|-----------------|
|  8   | CH1     | N-ch MOSFET  | 5 A @ 12 V      |
|  9   | CH2     | N-ch MOSFET  | 5 A @ 12 V      |
| 10   | CH3     | N-ch MOSFET  | 5 A @ 12 V      |
| 11   | CH4     | N-ch MOSFET  | 5 A @ 12 V      |
| 12   | CH5     | Relay K2 (SPDT) | Per relay rating |

---

## Repository Structure

```
├── kicad/
│   ├── wireless_switch.kicad_pro   KiCad project file
│   ├── wireless_switch.kicad_sch   Top-level schematic (with GPIO mapping notes)
│   ├── Pico_interface.kicad_sch    Pico 2 W GPIO interface sub-sheet
│   ├── analog_in.kicad_sch         Output channel sub-sheet (MOSFET + relay)
│   ├── input_power.kicad_sch       12 V → 5 V power supply sub-sheet
│   ├── wireless_switch.kicad_pcb   PCB layout
│   └── sym-lib-table               KiCad symbol library table
│
├── firmware/
│   ├── config.py       Shared configuration (WiFi SSID, GPIO assignments)
│   ├── tx_main.py      Transmitter MicroPython firmware
│   ├── rx_main.py      Receiver MicroPython firmware
│   ├── install_tx.sh   Automated transmitter installer (Linux/macOS)
│   ├── install_rx.sh   Automated receiver installer (Linux/macOS)
│   ├── install_tx.bat  Automated transmitter installer (Windows)
│   ├── install_rx.bat  Automated receiver installer (Windows)
│   ├── verify.bat      Post-install verification (Windows)
│   └── led_test.bat    LED test script (Windows)
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
- 2× LEDs (3 mm or PCB-mount) with 330 Ω series resistors for GPIO 0 & 7
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
2. Hold **BOOTSEL** button, plug USB → Pico appears as `RPI-RP2` mass storage drive
3. Drag the `.uf2` file onto the drive — Pico reboots automatically

### Step 2 — Install `mpremote`

```bash
pip install mpremote
```

### Step 3 — Install Transmitter firmware

Connect the **transmitter** Pico via USB, then:

**Linux / macOS:**
```bash
cd firmware
chmod +x install_tx.sh
./install_tx.sh                  # auto-detect USB port
# or specify port explicitly:
./install_tx.sh /dev/ttyACM0     # Linux
./install_tx.sh /dev/tty.usbmodem* # macOS
```

**Windows:**
```bat
cd firmware
install_tx.bat COM3              # replace COM3 with your actual port
```

### Step 4 — Install Receiver firmware

Connect the **receiver** Pico via USB, then:

**Linux / macOS:**
```bash
./install_rx.sh
```

**Windows:**
```bat
install_rx.bat COM5              # replace COM5 with your actual port
```

### Step 5 — Verify installation (optional)

**Windows:**
```bat
verify.bat COM3 COM5
```

Run the LED test to confirm both boards' indicator LEDs are wired correctly:

**Windows:**
```bat
led_test.bat COM3 COM5
```

### Step 6 — Configure WiFi SSID (optional)

The network is **open (no password)**. The default SSID is `WirelessSwitch`.  
To change it, edit `firmware/config.py` before installation:

```python
WIFI_SSID = "WirelessSwitch"
```

The transmitter creates the access point; the receiver connects to it automatically.

---

## Operation

1. **Power on both boards** — on startup, both boards blink the **SEARCHING LED 3× quickly**  
   to confirm firmware is running.
2. The transmitter creates an open WiFi access point (SSID: `WirelessSwitch`, no password).  
   The **SEARCHING LED (GPIO 7)** flashes on both boards until the link is established.
3. Once connected, the **CONNECTED LED (GPIO 0)** lights solid on both boards and  
   the SEARCHING LED turns off.
4. Pressing any switch on the transmitter immediately activates the corresponding  
   output channel on the receiver.
5. If the link drops, all receiver outputs are immediately forced **OFF** (safety interlock)  
   and both SEARCHING LEDs resume flashing.

### Link Parameters

| Parameter             | Value  |
|-----------------------|--------|
| Update rate           | 20 Hz  |
| Link timeout          | 2 s    |
| Protocol              | UDP    |
| WiFi mode             | TX=AP, RX=Station |
| Frequency band        | 2.4 GHz (802.11n) |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| SEARCHING LED never stops flashing | RX cannot find the TX access point | Confirm TX is powered and its SEARCHING LED is also blinking; check `config.py` SSID matches |
| SEARCHING LED does not blink 3× on boot | Firmware not installed | Re-run the install script; verify MicroPython UF2 was flashed first |
| SEARCHING LED never stops flashing (TX side) | TX AP failed to start due to stale security settings | Firmware deactivates the AP before reconfiguring to clear old settings — power-cycle the TX board |
| Output stays on after switch released | Link lost before switch released | Check antenna placement; reduce distance |
| `mpremote` cannot find device | Driver missing or wrong port | Try `mpremote` with no arguments to list ports |
| Pico not detected as storage drive | Not holding BOOTSEL | Hold BOOTSEL before plugging USB |
| Output channel too dim / not switching | MOSFET gate not reaching threshold | Verify 3.3 V GPIO level compatible with MOSFET (use logic-level type) |

---

## Protocol Reference

UDP packet format (7 bytes, transmitter → receiver, port 4210):

```
Byte 0   : 0xAA  (start marker)
Byte 1   : Switch 1 state  (0 = open, 1 = pressed)
Byte 2   : Switch 2 state
Byte 3   : Switch 3 state
Byte 4   : Switch 4 state
Byte 5   : Switch 5 state
Byte 6   : Checksum  = (SW1+SW2+SW3+SW4+SW5) & 0xFF
```

Receiver → transmitter heartbeat: `b"RXHERE"` (6 bytes, every 50 ms)
