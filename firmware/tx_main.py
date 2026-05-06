"""
Wireless Switch – TRANSMITTER firmware
Raspberry Pi Pico 2 W  |  Hardware v2  |  WiFi branch

GPIO 0  CONNECTED LED  – solid ON when RX is linked
GPIO 7  SEARCHING LED  – flashes while waiting for RX, OFF when linked
GPIO 1-5  Switch inputs (active-low, internal pull-up)

Web interface: http://192.168.4.1
  Connect phone/laptop to the WirelessSwitch-N WiFi network, then open that URL.
"""

import network
import socket
import time
import ujson
from machine import Pin, reset
import config

# -- Flash config (loaded before hardware init) ---------------
# Overrides config.py defaults with values saved via the web UI.
PAIR_ID   = config.PAIR_ID
WIFI_SSID = config.WIFI_SSID

try:
    with open("user_config.json") as _f:
        _cfg = ujson.load(_f)
    PAIR_ID   = int(_cfg.get("pair_id", PAIR_ID))
    WIFI_SSID = "WirelessSwitch-{}".format(PAIR_ID)
except Exception:
    pass

# -- Hardware -------------------------------------------------
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
switches      = [Pin(gp, Pin.IN, Pin.PULL_UP) for gp in config.TX_SWITCH_GPIOS]


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


def save_config():
    with open("user_config.json", "w") as f:
        ujson.dump({"pair_id": PAIR_ID}, f)


# -- Web interface --------------------------------------------
_CSS = (
    b"body{font-family:system-ui,sans-serif;padding:16px;max-width:500px;margin:0 auto}"
    b"h2{margin:0 0 10px}h3{margin:14px 0 6px}"
    b".ok{background:#d4edda;color:#155724;padding:8px;border-radius:6px;margin:8px 0}"
    b".srch{background:#fff3cd;color:#856404;padding:8px;border-radius:6px;margin:8px 0}"
    b"table{width:100%;border-collapse:collapse;margin:6px 0}"
    b"td,th{padding:7px 10px;border:1px solid #dee2e6;font-size:.9em}"
    b"th{background:#f1f3f5;font-weight:600}"
    b"label{display:block;font-weight:500;margin:10px 0 3px}"
    b"input{width:100%;padding:8px;border:1px solid #ced4da;border-radius:4px;"
    b"box-sizing:border-box;font-size:1em}"
    b"button{width:100%;padding:11px;background:#0d6efd;color:#fff;border:none;"
    b"border-radius:4px;margin-top:10px;font-size:1em;cursor:pointer}"
    b".warn{background:#fff3cd;border:1px solid #ffc107;border-radius:4px;"
    b"padding:8px;font-size:.85em;margin:8px 0}"
    b"a{color:#0d6efd}"
)

_HEAD = (
    b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n"
    b"<!DOCTYPE html><html><head>"
    b"<meta name=viewport content='width=device-width,initial-scale=1'>"
    b"<title>TX Settings</title>"
    b"<style>"
)


def _parse_form(body):
    params = {}
    for part in body.split(b"&"):
        if b"=" in part:
            k, v = part.split(b"=", 1)
            params[k.strip()] = v.strip()
    return params


def _serve_tx(cl, link_ok, rx_addr, sw_states):
    w = cl.write
    w(_HEAD + _CSS + b"</style></head><body>")
    w(b"<h2>TX &ndash; " + WIFI_SSID.encode() + b"</h2>")

    if link_ok and rx_addr:
        rx_ip = rx_addr[0].encode()
        w(b"<div class=ok>&#10003; Linked &ndash; RX at " + rx_ip + b"</div>")
        w(b"<p><a href='http://" + rx_ip + b"/'>Open RX settings &rarr;</a></p>")
    else:
        w(b"<div class=srch>&#9679; Searching for RX&hellip;</div>")

    w(b"<h3>Switch States</h3>")
    w(b"<table><tr>")
    for i in range(len(config.TX_SWITCH_GPIOS)):
        w(b"<th>SW" + str(i + 1).encode() + b"</th>")
    w(b"</tr><tr>")
    for s in sw_states:
        w(b"<td><b>ON</b></td>" if s else b"<td>off</td>")
    w(b"</tr></table>")

    w(b"<h3>Settings</h3>")
    w(b"<form method=post action=/save>")
    w(b"<label>Pair ID (1&ndash;99):</label>")
    w(b"<input type=number name=pair_id value=" + str(PAIR_ID).encode() +
      b" min=1 max=99>")
    w(b"<div class=warn>&#9888; Changing Pair ID renames the WiFi network and reboots"
      b" this board. Update the RX Pair ID first, then save here.</div>")
    w(b"<button>Save &amp; Reboot TX</button>")
    w(b"</form>")
    w(b"<p style='color:#6c757d;font-size:.8em;margin-top:20px'>Firmware v" +
      config.FIRMWARE_VERSION.encode() + b" &ndash; TX</p>")
    w(b"</body></html>")


def handle_web_tx(web_sock, link_ok, rx_addr, sw_states):
    global PAIR_ID, WIFI_SSID
    try:
        cl, _ = web_sock.accept()
    except OSError:
        return
    try:
        cl.settimeout(0.5)
        req = cl.recv(1024)

        if req.startswith(b"POST"):
            body = req.split(b"\r\n\r\n", 1)[-1] if b"\r\n\r\n" in req else b""
            params = _parse_form(body)
            if b"pair_id" in params:
                try:
                    new_id = int(params[b"pair_id"])
                    if 1 <= new_id <= 99:
                        PAIR_ID   = new_id
                        WIFI_SSID = "WirelessSwitch-{}".format(PAIR_ID)
                        save_config()
                        cl.write(b"HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n")
                        cl.close()
                        time.sleep_ms(300)
                        reset()
                except Exception:
                    pass
            cl.write(b"HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n")
        else:
            _serve_tx(cl, link_ok, rx_addr, sw_states)
    except Exception as e:
        print("[WEB]", e)
    finally:
        try:
            cl.close()
        except Exception:
            pass


# -- WiFi AP --------------------------------------------------
def start_ap():
    for _ in range(3):
        searching_led.value(1)
        time.sleep_ms(150)
        searching_led.value(0)
        time.sleep_ms(150)

    ap = network.WLAN(network.AP_IF)
    try:
        ap.active(False)
        time.sleep_ms(500)
    except OSError:
        pass
    ap.config(ssid=WIFI_SSID, security=0, password="")
    ap.active(True)

    deadline = time.ticks_add(time.ticks_ms(), 15_000)
    while not ap.active():
        searching_led.toggle()
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return None
        time.sleep_ms(200)

    searching_led.value(0)
    print("[TX] AP:", WIFI_SSID, " IP:", ap.ifconfig()[0])
    print("[TX] Web interface: http://192.168.4.1/")
    return ap


def main():
    ap = start_ap()
    if ap is None:
        print("[TX] AP failed to start")
        blink_error()

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("0.0.0.0", config.UDP_PORT))
    udp.setblocking(False)

    web = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    web.bind(("0.0.0.0", config.WEB_PORT))
    web.listen(1)
    web.setblocking(False)

    rx_addr        = None
    last_rx_time   = time.ticks_ms()
    search_flash_t = time.ticks_ms()
    sw_states      = [0] * 5
    link_ok        = False

    print("[TX] Waiting for receiver…")

    while True:
        now = time.ticks_ms()

        # Web request (non-blocking)
        handle_web_tx(web, link_ok, rx_addr if link_ok else None, sw_states)

        # Receive RXHERE heartbeat
        try:
            data, addr = udp.recvfrom(32)
            if data[:6] == b"RXHERE":
                if addr != rx_addr:
                    print("[TX] RX registered from", addr)
                rx_addr      = addr
                last_rx_time = now
        except OSError:
            pass

        # Link status
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

        # Read switches and broadcast
        sw_states = read_switches()
        if rx_addr:
            try:
                udp.sendto(build_packet(sw_states), rx_addr)
            except OSError:
                pass

        time.sleep_ms(config.HEARTBEAT_MS)


try:
    main()
except Exception as e:
    print("[TX] CRASH:", e)
    blink_error()
