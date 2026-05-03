"""
Wireless Switch – RECEIVER firmware
Raspberry Pi Pico 2 W  |  Hardware v2

Behaviour
---------
* Connects to the TX's WiFi Access Point.
* Receives switch states over UDP and drives 5 output channels.
* GPIO  0 (CONNECTED LED) – solid ON when link is up.
* GPIO  7 (SEARCHING LED) – flashes at 2 Hz while searching, OFF when linked.
* GPIO  8 – Channel 1  N-channel MOSFET (up to 5 A switched 12 V)
* GPIO  9 – Channel 2  N-channel MOSFET
* GPIO 10 – Channel 3  N-channel MOSFET
* GPIO 11 – Channel 4  N-channel MOSFET
* GPIO 12 – Channel 5  Relay K2 (SPDT)
* Safety: all outputs forced OFF if link is lost.
"""

import network
import socket
import time
from machine import Pin
import config


# ─── Hardware setup ─────────────────────────────────────────
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
outputs       = [Pin(gp, Pin.OUT, value=0) for gp in config.RX_OUTPUT_GPIOS]


def all_outputs_off():
    for out in outputs:
        out.value(0)


def set_outputs(states):
    for out, state in zip(outputs, states):
        out.value(int(state))


def parse_packet(data):
    """Return list of 5 switch states, or None if packet is invalid."""
    if len(data) < 7 or data[0] != 0xAA:
        return None
    states = list(data[1:6])
    if sum(states) & 0xFF != data[6]:
        return None           # checksum mismatch
    return states


def connect_wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    search_led_state = False
    search_t         = time.ticks_ms()

    print("[RX] Connecting to", config.WIFI_SSID)
    while not sta.isconnected():
        now = time.ticks_ms()
        if time.ticks_diff(now, search_t) >= config.SEARCH_FLASH_MS:
            search_led_state = not search_led_state
            searching_led.value(search_led_state)
            search_t = now
        try:
            sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        except OSError:
            pass
        time.sleep_ms(500)

    searching_led.value(0)
    print("[RX] Connected –", sta.ifconfig())
    return sta


def main():
    sta         = connect_wifi()
    tx_addr     = (config.TX_HOST, config.UDP_PORT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.settimeout(0.1)

    # Start link as timed-out so searching LED flashes until first real packet
    last_rx_time   = time.ticks_add(time.ticks_ms(), -(config.LINK_TIMEOUT_MS + 1))
    search_flash_t = time.ticks_ms()

    print("[RX] Listening for TX packets…")

    while True:
        now = time.ticks_ms()

        # ── Send heartbeat so TX knows our IP / port ─────────
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
            all_outputs_off()           # safety interlock
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


main()
