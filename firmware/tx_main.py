"""
Wireless Switch – TRANSMITTER firmware  (Bluetooth branch)
Raspberry Pi Pico 2 W  |  Hardware v2

GPIO 0  CONNECTED LED  – solid ON when RX is linked
GPIO 7  SEARCHING LED  – flashes while waiting for RX, OFF when linked
GPIO 1-5  Switch inputs (active-low, internal pull-up)

BLE role: PERIPHERAL / GATT server
  - Advertises by name (flags + complete local name, 21 bytes)
  - Sends notifications every HEARTBEAT_MS once connected
  - 1-second settle delay after connect before first notify
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
_FLAG_NOTIFY            = const(0x0010)
_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)


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


def make_adv_payload(name):
    name_b = name.encode()
    return bytes([2, 0x01, 0x06, 1 + len(name_b), 0x09]) + name_b


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

    adv_payload    = make_adv_payload(config.BT_DEVICE_NAME)
    char_handle    = register_gatt(ble, config.BT_SERVICE_UUID, config.BT_CHAR_UUID)
    search_flash_t = time.ticks_ms()

    conn_handle  = None
    connect_time = None
    do_advertise = False

    def ble_irq(event, data):
        nonlocal conn_handle, connect_time, do_advertise
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            connect_time = time.ticks_ms()
            print("[TX] RX connected, handle:", conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle  = None
            connect_time = None
            do_advertise = True
            print("[TX] RX disconnected")

    ble.irq(ble_irq)
    ble.gap_advertise(100_000, adv_payload)
    print("[TX] Advertising as:", config.BT_DEVICE_NAME, " payload:", len(adv_payload), "B")

    while True:
        now = time.ticks_ms()

        if do_advertise:
            do_advertise = False
            ble.gap_advertise(100_000, adv_payload)
            print("[TX] Advertising resumed")

        if conn_handle is not None:
            connected_led.value(1)
            searching_led.value(0)
            # 1-second settle delay lets RX finish any GATT discovery before notifications start
            settled = connect_time and time.ticks_diff(now, connect_time) > 1000
            if settled:
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
