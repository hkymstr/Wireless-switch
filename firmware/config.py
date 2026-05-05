# Hardware v2 Configuration
# Wireless Race Car Switch System - Raspberry Pi Pico 2 W
# Branch: bluetooth

# ── Bluetooth ────────────────────────────────────────────────
# Set PAIR_ID to the same number on both the TX and RX that belong together.
# Every pair in use must have a unique PAIR_ID so units don't cross-connect
# when multiple pairs are operating nearby.  Valid values: 1, 2, 3, ...
PAIR_ID        = 1
BT_DEVICE_NAME = "WirelessSwitch-{}".format(PAIR_ID)

# 128-bit UUIDs for the switch-state GATT service / characteristic
BT_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BT_CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"

# ── Timing ───────────────────────────────────────────────────
HEARTBEAT_MS          = 50    # 20 Hz switch-state notify
LINK_TIMEOUT_MS       = 2000  # loss-of-link if no packet for 2 s
SEARCH_FLASH_MS       = 250   # searching LED half-period
HOLD_ON_DISCONNECT_MS = 10_000  # hold last output states for 10 s on link loss

# ── GPIO – shared by both boards ────────────────────────────
GPIO_CONNECTED  = 0   # solid ON when link is up
GPIO_SEARCHING  = 7   # flashes while searching, OFF when linked

# TRANSMITTER – switch inputs (active-low, internal pull-up)
TX_SWITCH_GPIOS = [1, 2, 3, 4, 5]

# RECEIVER – output channels
#   GPIO  8-11 : N-channel MOSFET low-side switches (up to 5 A each)
#   GPIO 12    : Relay driver (K2, SPDT)
RX_OUTPUT_GPIOS = [8, 9, 10, 11, 12]

CHANNEL_NAMES = ["CH1_MOSFET", "CH2_MOSFET", "CH3_MOSFET",
                 "CH4_MOSFET", "CH5_RELAY"]

# ── Channel modes ────────────────────────────────────────────
# MODE_MOMENTARY : output follows switch (ON while held, OFF when released)
# MODE_LATCH     : each press toggles output ON/OFF
MODE_MOMENTARY = 0
MODE_LATCH     = 1

CHANNEL_MODES = [
    MODE_MOMENTARY,   # CH1 MOSFET  GPIO 8
    MODE_MOMENTARY,   # CH2 MOSFET  GPIO 9
    MODE_MOMENTARY,   # CH3 MOSFET  GPIO 10
    MODE_MOMENTARY,   # CH4 MOSFET  GPIO 11
    MODE_MOMENTARY,   # CH5 RELAY   GPIO 12
]
