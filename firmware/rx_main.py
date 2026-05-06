"""
Wireless Switch – RECEIVER firmware
Raspberry Pi Pico 2 W  |  Hardware v2  |  WiFi branch

GPIO  0  CONNECTED LED  – solid ON when link is up
GPIO  7  SEARCHING LED  – flashes while searching, OFF when linked
GPIO  8-11  MOSFET outputs CH1-CH4 (up to 5 A each)
GPIO 12     Relay K2 output CH5

Link-loss behaviour:
  - Outputs hold their last state for HOLD_MS (default 10 s)
  - After hold period, all outputs turn off

Channel modes (configurable via web interface):
  - MODE_MOMENTARY: output follows switch state
  - MODE_LATCH:     each press toggles output ON/OFF

Web interface: http://<RX-IP>
  RX IP is shown as a clickable link on the TX settings page (http://192.168.4.1).
"""

import network
import socket
import time
import ujson
from machine import Pin, reset
import config

# -- Flash config (loaded before hardware init) ---------------
PAIR_ID       = config.PAIR_ID
WIFI_SSID     = config.WIFI_SSID
HOLD_MS       = config.HOLD_ON_DISCONNECT_MS
CHANNEL_MODES = list(config.CHANNEL_MODES)   # mutable local copy

try:
    with open("user_config.json") as _f:
        _cfg = ujson.load(_f)
    PAIR_ID   = int(_cfg.get("pair_id", PAIR_ID))
    WIFI_SSID = "WirelessSwitch-{}".format(PAIR_ID)
    HOLD_MS   = int(_cfg.get("hold_time_s", HOLD_MS // 1000)) * 1000
    _m = _cfg.get("channel_modes")
    if isinstance(_m, list) and len(_m) == len(CHANNEL_MODES):
        for _i in range(len(CHANNEL_MODES)):
            CHANNEL_MODES[_i] = int(_m[_i])
except Exception:
    pass

# -- Hardware -------------------------------------------------
connected_led = Pin(config.GPIO_CONNECTED, Pin.OUT, value=0)
searching_led = Pin(config.GPIO_SEARCHING, Pin.OUT, value=0)
outputs       = [Pin(gp, Pin.OUT, value=0) for gp in config.RX_OUTPUT_GPIOS]

# -- Channel state --------------------------------------------
_prev_raw  = [0] * len(config.RX_OUTPUT_GPIOS)
_latch_out = [0] * len(config.RX_OUTPUT_GPIOS)


def blink_error():
    while True:
        connected_led.toggle()
        searching_led.toggle()
        time.sleep_ms(100)


def all_outputs_off():
    for out in outputs:
        out.value(0)
    for i in range(len(_latch_out)):
        _latch_out[i] = 0


def apply_states(raw):
    """Apply received switch states honouring per-channel mode."""
    for i in range(len(outputs)):
        if CHANNEL_MODES[i] == config.MODE_MOMENTARY:
            outputs[i].value(raw[i])
        else:                                        # MODE_LATCH
            if raw[i] == 1 and _prev_raw[i] == 0:   # rising edge → toggle
                _latch_out[i] ^= 1
            outputs[i].value(_latch_out[i])
        _prev_raw[i] = raw[i]


def parse_packet(data):
    if len(data) < 7 or data[0] != 0xAA:
        return None
    states = list(data[1:6])
    if sum(states) & 0xFF != data[6]:
        return None
    return states


def save_config():
    with open("user_config.json", "w") as f:
        ujson.dump({
            "pair_id":       PAIR_ID,
            "hold_time_s":   HOLD_MS // 1000,
            "channel_modes": CHANNEL_MODES,
        }, f)


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
    b"input,select{width:100%;padding:8px;border:1px solid #ced4da;border-radius:4px;"
    b"box-sizing:border-box;font-size:1em}"
    b"button{width:100%;padding:11px;background:#0d6efd;color:#fff;border:none;"
    b"border-radius:4px;margin-top:10px;font-size:1em;cursor:pointer}"
    b".warn{background:#fff3cd;border:1px solid #ffc107;border-radius:4px;"
    b"padding:8px;font-size:.85em;margin:8px 0}"
)

_HEAD = (
    b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n"
    b"<!DOCTYPE html><html><head>"
    b"<meta name=viewport content='width=device-width,initial-scale=1'>"
    b"<title>RX Settings</title>"
    b"<style>"
)

_MODE_LABELS = [b"Momentary", b"Latch"]


def _parse_form(body):
    params = {}
    for part in body.split(b"&"):
        if b"=" in part:
            k, v = part.split(b"=", 1)
            params[k.strip()] = v.strip()
    return params


def _current_out_state(i):
    if CHANNEL_MODES[i] == config.MODE_LATCH:
        return _latch_out[i]
    return outputs[i].value()


def _serve_rx(cl, link_ok):
    w = cl.write
    w(_HEAD + _CSS + b"</style></head><body>")
    w(b"<h2>RX &ndash; " + WIFI_SSID.encode() + b"</h2>")
    w(b"<p><a href='http://192.168.4.1/'>&#8592; TX Settings</a></p>")
    w(b"<div class=ok>&#10003; Linked to TX</div>" if link_ok
      else b"<div class=srch>&#9679; Searching for TX&hellip;</div>")

    # Output states table
    w(b"<h3>Output States</h3>")
    w(b"<table><tr><th>Channel</th><th>GPIO</th><th>Mode</th><th>State</th></tr>")
    for i, (name, gp) in enumerate(zip(config.CHANNEL_NAMES, config.RX_OUTPUT_GPIOS)):
        state = _current_out_state(i)
        w(b"<tr><td>" + name.encode() + b"</td><td>" + str(gp).encode() +
          b"</td><td>" + _MODE_LABELS[CHANNEL_MODES[i]] +
          b"</td><td>" + (b"<b>ON</b>" if state else b"off") + b"</td></tr>")
    w(b"</table>")

    # Settings form
    w(b"<form method=post action=/save>")

    w(b"<h3>Settings</h3>")
    w(b"<label>Pair ID (1&ndash;99):</label>")
    w(b"<input type=number name=pair_id value=" + str(PAIR_ID).encode() +
      b" min=1 max=99>")
    w(b"<div class=warn>&#9888; Changing Pair ID connects this board to a different TX."
      b" Update TX Pair ID first, then save here.</div>")

    w(b"<label>Hold time on disconnect (0&ndash;60 seconds):</label>")
    w(b"<input type=number name=hold_time_s value=" + str(HOLD_MS // 1000).encode() +
      b" min=0 max=60>")

    # Channel mode selects
    w(b"<h3>Channel Modes</h3>")
    w(b"<table><tr><th>Channel</th><th>Mode</th></tr>")
    for i, name in enumerate(config.CHANNEL_NAMES):
        key = ("ch%d_mode" % i).encode()
        sel_m = b" selected" if CHANNEL_MODES[i] == 0 else b""
        sel_l = b" selected" if CHANNEL_MODES[i] == 1 else b""
        w(b"<tr><td>" + name.encode() + b"</td><td>"
          b"<select name=" + key + b">"
          b"<option value=0" + sel_m + b">Momentary (ON while held)</option>"
          b"<option value=1" + sel_l + b">Latch (toggle ON/OFF)</option>"
          b"</select></td></tr>")
    w(b"</table>")

    w(b"<button>Save Settings</button>")
    w(b"</form>")
    w(b"<p style='color:#6c757d;font-size:.8em;margin-top:20px'>Firmware v" +
      config.FIRMWARE_VERSION.encode() + b" &ndash; RX</p>")
    w(b"</body></html>")


def handle_web_rx(web_sock, link_ok):
    global PAIR_ID, WIFI_SSID, HOLD_MS, CHANNEL_MODES
    try:
        cl, _ = web_sock.accept()
    except OSError:
        return
    try:
        cl.settimeout(0.5)
        req = cl.recv(1024)
        # Body often arrives in a second TCP packet — read it if missing
        if req.startswith(b"POST") and b"\r\n\r\n" in req:
            body = req.split(b"\r\n\r\n", 1)[1]
            if not body:
                try:
                    body = cl.recv(512)
                except OSError:
                    body = b""
        elif req.startswith(b"POST"):
            body = b""

        if req.startswith(b"POST"):
            params = _parse_form(body)
            need_reset = False

            if b"pair_id" in params:
                try:
                    new_id = int(params[b"pair_id"])
                    if 1 <= new_id <= 99 and new_id != PAIR_ID:
                        PAIR_ID   = new_id
                        WIFI_SSID = "WirelessSwitch-{}".format(PAIR_ID)
                        need_reset = True
                except Exception:
                    pass

            if b"hold_time_s" in params:
                try:
                    new_hold = int(params[b"hold_time_s"])
                    HOLD_MS = max(0, min(60, new_hold)) * 1000
                except Exception:
                    pass

            for i in range(len(CHANNEL_MODES)):
                key = ("ch%d_mode" % i).encode()
                if key in params:
                    try:
                        CHANNEL_MODES[i] = int(params[key])
                    except Exception:
                        pass

            save_config()
            cl.write(b"HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n")
            cl.close()
            if need_reset:
                time.sleep_ms(300)
                reset()
        else:
            _serve_rx(cl, link_ok)
    except Exception as e:
        print("[WEB]", e)
    finally:
        try:
            cl.close()
        except Exception:
            pass


# -- WiFi STA -------------------------------------------------
def connect_wifi():
    for _ in range(3):
        searching_led.value(1)
        time.sleep_ms(150)
        searching_led.value(0)
        time.sleep_ms(150)

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    print("[RX] Connecting to", WIFI_SSID)

    deadline     = time.ticks_add(time.ticks_ms(), 60_000)
    last_attempt = time.ticks_add(time.ticks_ms(), -10_000)

    while not sta.isconnected():
        now = time.ticks_ms()
        if time.ticks_diff(now, last_attempt) >= 5_000:
            print("[RX] Trying connect…")
            try:
                sta.connect(WIFI_SSID)
            except OSError:
                pass
            last_attempt = now
        searching_led.toggle()
        if time.ticks_diff(deadline, now) <= 0:
            return None
        time.sleep_ms(250)

    searching_led.value(0)
    ip = sta.ifconfig()[0]
    print("[RX] Connected –", sta.ifconfig())
    print("[RX] Web interface: http://{}/".format(ip))
    return sta


def main():
    sta = connect_wifi()
    if sta is None:
        print("[RX] WiFi connect timed out")
        blink_error()

    tx_addr = (config.TX_HOST, config.UDP_PORT)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("0.0.0.0", config.UDP_PORT))
    udp.settimeout(0.1)

    web = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    web.bind(("0.0.0.0", config.WEB_PORT))
    web.listen(1)
    web.setblocking(False)

    # Start past the hold window so outputs are OFF at boot
    last_rx_time      = time.ticks_add(time.ticks_ms(), -(config.LINK_TIMEOUT_MS + 1))
    last_link_ok_t    = time.ticks_add(time.ticks_ms(), -(HOLD_MS + 1))
    search_flash_t    = time.ticks_ms()
    last_reconnect_t  = time.ticks_add(time.ticks_ms(), -10_000)
    link_ok           = False

    print("[RX] Listening for TX packets…")

    while True:
        now = time.ticks_ms()

        # Web request (non-blocking)
        handle_web_rx(web, link_ok)

        # Heartbeat to TX
        try:
            udp.sendto(b"RXHERE", tx_addr)
        except OSError:
            pass

        # Receive switch-state packet
        try:
            data, _ = udp.recvfrom(32)
            states  = parse_packet(data)
            if states is not None:
                apply_states(states)
                last_rx_time = now
        except OSError:
            pass

        # Link status
        link_ok = time.ticks_diff(now, last_rx_time) < config.LINK_TIMEOUT_MS

        if link_ok:
            connected_led.value(1)
            searching_led.value(0)
            last_link_ok_t = now
        else:
            connected_led.value(0)
            # Hold outputs for HOLD_MS after link loss, then release
            if time.ticks_diff(now, last_link_ok_t) >= HOLD_MS:
                all_outputs_off()
            if time.ticks_diff(now, search_flash_t) >= config.SEARCH_FLASH_MS:
                searching_led.toggle()
                search_flash_t = now
            if not sta.isconnected():
                if time.ticks_diff(now, last_reconnect_t) >= 5_000:
                    print("[RX] WiFi lost – reconnecting…")
                    try:
                        sta.active(False)
                        time.sleep_ms(100)
                        sta.active(True)
                        sta.connect(WIFI_SSID)
                    except OSError:
                        pass
                    last_reconnect_t = now

        time.sleep_ms(config.HEARTBEAT_MS)


try:
    main()
except Exception as e:
    print("[RX] CRASH:", e)
    blink_error()
