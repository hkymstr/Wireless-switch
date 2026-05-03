"""
Wireless Switch – TRANSMITTER firmware
Raspberry Pi Pico 2 W  |  Hardware v2

Behaviour
---------
* Creates a WiFi Access Point that the RX connects to.
* Reads 5 toggle-switch inputs (GPIO 1-5, active-low).
* Broadcasts switch states over UDP at 20 Hz.
* GPIO 0 (CONNECTED LED) – solid ON when at least one RX is connected.
* GPIO 7 (SEARCHING LED) – flashes at 2 Hz while waiting for RX, OFF when linked.
* Packet format: [0xAA, sw1, sw2, sw3, sw4, sw5, checksum]
  where checksum = (sw1+sw2+sw3+sw4+sw5) & 0xFF
"""

import network
import socket
import time
from machine import Pin
import config


# ─── Hardware setup ─────────────────────────────────────────
connected_led = Pin(config.GPIO_CONNECTED,  Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING,  Pin.OUT, value=0)
switches      = [Pin(gp, Pin.IN, Pin.PULL_UP) for gp in config.TX_SWITCH_GPIOS]


def read_switches():
    """Return list of 0/1 per channel; active-low so invert pin value."""
    return [1 - sw.value() for sw in switches]


def build_packet(states):
    chk = sum(states) & 0xFF
    return bytes([0xAA] + states + [chk])


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(False)          # reset so config takes effect
    ap.config(
        ssid=config.WIFI_SSID,
        password=config.WIFI_PASSWORD,
        authmode=3,            # WPA2-PSK
    )
    ap.active(True)
    deadline = time.ticks_add(time.ticks_ms(), 10_000)
    while not ap.active():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            raise RuntimeError("AP failed to start")
        time.sleep_ms(100)
    print("[TX] AP up –", ap.ifconfig())
    return ap


def main():
    ap = start_ap()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.setblocking(False)

    rx_addr          = None
    last_rx_time     = time.ticks_ms()
    search_flash_t   = time.ticks_ms()
    search_led_state = False

    print("[TX] Waiting for receiver…")

    while True:
        now = time.ticks_ms()

        # ── Receive heartbeat / registration from RX ────────
        try:
            data, addr = sock.recvfrom(32)
            if data[:6] == b"RXHERE":
                if addr != rx_addr:
                    print("[TX] RX registered from", addr)
                rx_addr      = addr
                last_rx_time = now
        except OSError:
            pass

        # ── Link status ──────────────────────────────────────
        link_ok = (rx_addr is not None and
                   time.ticks_diff(now, last_rx_time) < config.LINK_TIMEOUT_MS)

        if link_ok:
            connected_led.value(1)
            searching_led.value(0)
            search_led_state = False
        else:
            connected_led.value(0)
            if time.ticks_diff(now, search_flash_t) >= config.SEARCH_FLASH_MS:
                search_led_state = not search_led_state
                searching_led.value(search_led_state)
                search_flash_t = now

        # ── Broadcast switch states to RX ────────────────────
        if rx_addr:
            pkt = build_packet(read_switches())
            try:
                sock.sendto(pkt, rx_addr)
            except OSError:
                pass

        time.sleep_ms(config.HEARTBEAT_MS)


main()
