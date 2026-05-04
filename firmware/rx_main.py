"""
Wireless Switch – RECEIVER firmware  (Bluetooth branch)
Raspberry Pi Pico 2 W  |  Hardware v2

GPIO  0  CONNECTED LED  – solid ON when link is up
GPIO  7  SEARCHING LED  – flashes while searching, OFF when linked
GPIO  8-11  MOSFET outputs CH1-CH4 (up to 5 A each)
GPIO 12     Relay K2 output CH5
Safety: all outputs forced OFF if link is lost.

BLE role: CENTRAL / GATT client
  - Scans indefinitely for BT_DEVICE_NAME
  - Connects, discovers service + characteristic, writes CCCD to enable notify
  - Applies received switch states to outputs
"""

import bluetooth
import time
from machine import Pin
from micropython import const
import config

# ─── Hardware ────────────────────────────────────────────────
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
outputs       = [Pin(gp, Pin.OUT, value=0) for gp in config.RX_OUTPUT_GPIOS]

# ─── BLE constants ───────────────────────────────────────────
_IRQ_SCAN_RESULT                 = const(5)
_IRQ_SCAN_DONE                   = const(6)
_IRQ_PERIPHERAL_CONNECT          = const(7)
_IRQ_PERIPHERAL_DISCONNECT       = const(8)
_IRQ_GATTC_SERVICE_RESULT        = const(9)
_IRQ_GATTC_SERVICE_DONE          = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE   = const(12)
_IRQ_GATTC_NOTIFY                = const(18)

_ADV_TYPE_NAME       = const(0x09)
_ADV_TYPE_SHORT_NAME = const(0x08)


def blink_error():
    while True:
        connected_led.toggle()
        searching_led.toggle()
        time.sleep_ms(100)


def all_outputs_off():
    for out in outputs:
        out.value(0)


def set_outputs(states):
    for out, state in zip(outputs, states):
        out.value(int(state))


def parse_packet(data):
    if len(data) < 7 or data[0] != 0xAA:
        return None
    states = list(data[1:6])
    if sum(states) & 0xFF != data[6]:
        return None
    return states


def adv_contains_name(payload, target_name):
    i = 0
    while i < len(payload):
        length = payload[i]
        if length == 0:
            break
        if i + length >= len(payload):
            break
        ad_type = payload[i + 1]
        if ad_type in (_ADV_TYPE_NAME, _ADV_TYPE_SHORT_NAME):
            name = payload[i + 2: i + 1 + length].decode('utf-8', 'ignore')
            if name == target_name:
                return True
        i += 1 + length
    return False


def start_scan(ble):
    # interval_us=30000, window_us=30000 = 100% duty cycle, active scan
    ble.gap_scan(0, 30_000, 30_000, True)
    print("[RX] Scanning for", config.BT_DEVICE_NAME)


def startup_blinks():
    for _ in range(3):
        searching_led.value(1)
        time.sleep_ms(150)
        searching_led.value(0)
        time.sleep_ms(150)


def main():
    startup_blinks()

    ble = bluetooth.BLE()
    ble.active(True)

    conn_handle    = None
    char_handle    = None
    last_rx_time   = time.ticks_add(time.ticks_ms(), -(config.LINK_TIMEOUT_MS + 1))
    search_flash_t = time.ticks_ms()

    svc_uuid  = bluetooth.UUID(config.BT_SERVICE_UUID)
    char_uuid = bluetooth.UUID(config.BT_CHAR_UUID)

    def ble_irq(event, data):
        nonlocal conn_handle, char_handle, last_rx_time

        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            if adv_contains_name(bytes(adv_data), config.BT_DEVICE_NAME):
                print("[RX] Found TX (RSSI", rssi, ") – connecting")
                ble.gap_scan(None)                        # stop scan
                ble.gap_connect(addr_type, bytes(addr))

        elif event == _IRQ_SCAN_DONE:
            if conn_handle is None:
                print("[RX] Scan ended without finding TX – restarting")
                start_scan(ble)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            conn_handle, _, _ = data
            print("[RX] Connected – discovering services")
            ble.gattc_discover_services(conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            conn_handle = None
            char_handle = None
            print("[RX] Disconnected – scanning again")
            all_outputs_off()
            start_scan(ble)

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            conn_h, start_h, end_h, uuid = data
            if uuid == svc_uuid:
                print("[RX] Service found – discovering characteristics")
                ble.gattc_discover_characteristics(conn_h, start_h, end_h)

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn_h, def_h, value_h, properties, uuid = data
            if uuid == char_uuid:
                char_handle = value_h
                # Write 0x0001 to CCCD (value_handle + 1) to enable notifications
                ble.gattc_write(conn_h, value_h + 1, b'\x01\x00', 1)
                print("[RX] Subscribed to TX notifications")

        elif event == _IRQ_GATTC_NOTIFY:
            conn_h, value_h, notify_data = data
            states = parse_packet(bytes(notify_data))
            if states is not None:
                set_outputs(states)
                last_rx_time = time.ticks_ms()

    ble.irq(ble_irq)
    start_scan(ble)

    while True:
        now     = time.ticks_ms()
        link_ok = time.ticks_diff(now, last_rx_time) < config.LINK_TIMEOUT_MS

        if link_ok:
            connected_led.value(1)
            searching_led.value(0)
        else:
            connected_led.value(0)
            all_outputs_off()
            if time.ticks_diff(now, search_flash_t) >= config.SEARCH_FLASH_MS:
                searching_led.toggle()
                search_flash_t = now

        time.sleep_ms(config.HEARTBEAT_MS)


try:
    main()
except Exception as e:
    print("[RX] CRASH:", e)
    blink_error()
