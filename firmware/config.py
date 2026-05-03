# Hardware v2 Configuration
# Wireless Race Car Switch System - Raspberry Pi Pico 2 W
# Branch: bluetooth

# ─── Bluetooth ───────────────────────────────────────────────
BT_DEVICE_NAME  = "WirelessSwitch-TX"
# 128-bit UUIDs for the switch-state GATT service / characteristic
BT_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BT_CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"

# ─── Timing ─────────────────────────────────────────────────
HEARTBEAT_MS     = 50    # 20 Hz switch-state notify
LINK_TIMEOUT_MS  = 2000  # Loss-of-link if no notify for 2 s
SEARCH_FLASH_MS  = 250   # Searching LED half-period

# ─── GPIO – shared by both boards ───────────────────────────
GPIO_CONNECTED  = 0   # Solid ON when link is up
GPIO_SEARCHING  = 7   # Flashes while searching, OFF when linked

# TRANSMITTER – switch inputs (active-low, internal pull-up)
TX_SWITCH_GPIOS = [1, 2, 3, 4, 5]

# RECEIVER – output channels
#   GPIO  8-11 : N-channel MOSFET low-side switches (up to 5 A each)
#   GPIO 12    : Relay driver (K2, SPDT)
RX_OUTPUT_GPIOS = [8, 9, 10, 11, 12]

CHANNEL_NAMES = ["CH1_MOSFET", "CH2_MOSFET", "CH3_MOSFET",
                 "CH4_MOSFET", "CH5_RELAY"]
