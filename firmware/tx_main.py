"""
Wireless Switch – TRANSMITTER firmware
Raspberry Pi Pico 2 W  |  Hardware v2

GPIO 0  CONNECTED LED  – solid ON when RX is linked
GPIO 7  SEARCHING LED  – flashes while waiting for RX, OFF when linked
GPIO 1-5  Switch inputs (active-low, internal pull-up)
"""

import network
import socket
import time
from machine import Pin
import config


# ─── Hardware ────────────────────────────────────────────────
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
switches      = [Pin(gp, Pin.IN, Pin.PULL_UP) for gp in config.TX_SWITCH_GPIOS]


def blink_error():
    """Fast-blink both LEDs forever to signal a fatal error."""
    while True:
        connected_led.toggle()
        searching_led.toggle()
        time.sleep_ms(100)


def read_switches():
    return [1 - sw.value() for sw in switches]


def build_packet(states):
    chk = sum(states) & 0xFF
    return bytes([0xAA] + states + [chk])


def start_ap():
    # Confirm firmware is alive – three quick searching LED blinks
    for _ in range(3):
        searching_led.value(1)
        time.sleep_ms(150)
        searching_led.value(0)
        time.sleep_ms(150)

    ap = network.WLAN(network.AP_IF)
    ap.config(ssid=config.WIFI_SSID)   # open network
    ap.active(True)

    deadline = time.ticks_add(time.ticks_ms(), 15_000)
    while not ap.active():
        searching_led.toggle()             # flash while waiting for AP
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return None                    # caller will signal error
        time.sleep_ms(200)

    searching_led.value(0)
    print("[TX] AP up  SSID:", ap.config('ssid'), " IP:", ap.ifconfig()[0])
    return ap


def main():
    ap = start_ap()
    if ap is None:
        print("[TX] AP failed to start")
        blink_error()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.setblocking(False)

    rx_addr        = None
    last_rx_time   = time.ticks_ms()
    search_flash_t = time.ticks_ms()

    print("[TX] Waiting for receiver…")

    while True:
        now = time.ticks_ms()

        # ── Receive heartbeat from RX ────────────────────────
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
        else:
            connected_led.value(0)
            if time.ticks_diff(now, search_flash_t) >= config.SEARCH_FLASH_MS:
                searching_led.toggle()
                search_flash_t = now

        # ── Broadcast switch states ──────────────────────────
        if rx_addr:
            try:
                sock.sendto(build_packet(read_switches()), rx_addr)
            except OSError:
                pass

        time.sleep_ms(config.HEARTBEAT_MS)


try:
    main()
except Exception as e:
    print("[TX] CRASH:", e)
    blink_error()
