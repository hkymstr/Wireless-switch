"""
Wireless Switch – RECEIVER firmware
Raspberry Pi Pico 2 W  |  Hardware v2

GPIO  0  CONNECTED LED  – solid ON when link is up
GPIO  7  SEARCHING LED  – flashes while searching, OFF when linked
GPIO  8-11  MOSFET outputs CH1-CH4 (up to 5 A each)
GPIO 12     Relay K2 output CH5
Safety: all outputs forced OFF if link is lost.
"""

import network
import socket
import time
from machine import Pin
import config


# ─── Hardware ────────────────────────────────────────────────
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
outputs       = [Pin(gp, Pin.OUT, value=0) for gp in config.RX_OUTPUT_GPIOS]


def blink_error():
    """Fast-blink both LEDs forever to signal a fatal error."""
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


def connect_wifi():
    # Confirm firmware alive – three quick searching LED blinks
    for _ in range(3):
        searching_led.value(1)
        time.sleep_ms(150)
        searching_led.value(0)
        time.sleep_ms(150)

    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    print("[RX] Connecting to", config.WIFI_SSID)
    sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)  # call once only

    deadline = time.ticks_add(time.ticks_ms(), 30_000)   # 30 s timeout
    while not sta.isconnected():
        searching_led.toggle()
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return None                                   # caller signals error
        time.sleep_ms(250)

    searching_led.value(0)
    print("[RX] Connected –", sta.ifconfig())
    return sta


def main():
    sta = connect_wifi()
    if sta is None:
        print("[RX] WiFi connect timed out")
        blink_error()

    tx_addr = (config.TX_HOST, config.UDP_PORT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.settimeout(0.1)

    # Start link as timed-out so searching LED flashes until first real packet
    last_rx_time   = time.ticks_add(time.ticks_ms(), -(config.LINK_TIMEOUT_MS + 1))
    search_flash_t = time.ticks_ms()

    print("[RX] Listening for TX packets…")

    while True:
        now = time.ticks_ms()

        # ── Heartbeat to TX ──────────────────────────────────
        try:
            sock.sendto(b"RXHERE", tx_addr)
        except OSError:
            pass

        # ── Receive switch-state packet ───────────────────────
        try:
            data, _ = sock.recvfrom(32)
            states  = parse_packet(data)
            if states is not None:
                set_outputs(states)
                last_rx_time = now
        except OSError:
            pass

        # ── Link status ───────────────────────────────────────
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

            # Re-connect WiFi if dropped
            if not sta.isconnected():
                print("[RX] WiFi lost – reconnecting…")
                try:
                    sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
                except OSError:
                    pass

        time.sleep_ms(config.HEARTBEAT_MS)


try:
    main()
except Exception as e:
    print("[RX] CRASH:", e)
    blink_error()
