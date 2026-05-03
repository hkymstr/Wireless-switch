"""
Wireless Switch – TRANSMITTER firmware  (Bluetooth branch)
Raspberry Pi Pico 2 W  |  Hardware v2

GPIO 0  CONNECTED LED  – solid ON when RX is linked
GPIO 7  SEARCHING LED  – flashes while waiting for RX, OFF when linked
GPIO 1-5  Switch inputs (active-low, internal pull-up)

BLE role: PERIPHERAL / GATT server
  - Advertises as BT_DEVICE_NAME
  - Exposes one notify characteristic with the 7-byte switch packet
  - Notifies the connected central (RX) at HEARTBEAT_MS rate
"""

import bluetooth
import time
from machine import Pin
from micropython import const
import config

# ─── Hardware ────────────────────────────────────────────────
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
switches      = [Pin(gp, Pin.IN, Pin.PULL_UP) for gp in config.TX_SWITCH_GPIOS]

# ─── BLE constants ───────────────────────────────────────────
_ADV_TYPE_FLAGS              = const(0x01)
_ADV_TYPE_NAME               = const(0x09)
_ADV_TYPE_UUID128_INCOMPLETE = const(0x06)
_FLAG_NOTIFY                 = const(0x0010)
_IRQ_CENTRAL_CONNECT         = const(1)
_IRQ_CENTRAL_DISCONNECT      = const(2)


def blink_error():
    while True:
        connected_led.toggle()
        searching_led.toggle()
        time.sleep_ms(100)


def read_switches():
    return [1 - sw.value() for sw in switches]


def build_packet(states):
    chk = sum(states) & 0xFF
    return bytes([0xAA] + states + [chk])


def uuid128_to_bytes(uuid_str):
    """'xxxxxxxx-xxxx-...' → little-endian bytes for BLE advertisement."""
    hex_str = uuid_str.replace('-', '')
    b = bytes(int(hex_str[i:i+2], 16) for i in range(0, 32, 2))
    return bytes(reversed(b))


def make_adv_payload(name, service_uuid):
    payload = bytearray()
    payload += bytes([2, _ADV_TYPE_FLAGS, 0x06])          # general discoverable, BLE only
    name_b = name.encode()
    payload += bytes([1 + len(name_b), _ADV_TYPE_NAME]) + name_b
    uuid_b = uuid128_to_bytes(service_uuid)
    payload += bytes([1 + len(uuid_b), _ADV_TYPE_UUID128_INCOMPLETE]) + uuid_b
    return bytes(payload)


def register_gatt(ble, service_uuid, char_uuid):
    svc  = bluetooth.UUID(service_uuid)
    char = bluetooth.UUID(char_uuid)
    ((char_handle,),) = ble.gatts_register_services(((svc, ((char, _FLAG_NOTIFY),)),))
    return char_handle


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
    adv_payload    = make_adv_payload(config.BT_DEVICE_NAME, config.BT_SERVICE_UUID)
    char_handle    = register_gatt(ble, config.BT_SERVICE_UUID, config.BT_CHAR_UUID)
    search_flash_t = time.ticks_ms()

    def ble_irq(event, data):
        nonlocal conn_handle
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("[TX] RX connected, handle:", conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle = None
            print("[TX] RX disconnected – resuming advertising")
            ble.gap_advertise(100_000, adv_payload)

    ble.irq(ble_irq)
    ble.gap_advertise(100_000, adv_payload)   # 100 ms advertising interval
    print("[TX] Advertising as", config.BT_DEVICE_NAME)

    while True:
        now = time.ticks_ms()

        if conn_handle is not None:
            connected_led.value(1)
            searching_led.value(0)
            try:
                ble.gatts_notify(conn_handle, char_handle, build_packet(read_switches()))
            except OSError:
                pass
        else:
            connected_led.value(0)
            if time.ticks_diff(now, search_flash_t) >= config.SEARCH_FLASH_MS:
                searching_led.toggle()
                search_flash_t = now

        time.sleep_ms(config.HEARTBEAT_MS)


try:
    main()
except Exception as e:
    print("[TX] CRASH:", e)
    blink_error()
