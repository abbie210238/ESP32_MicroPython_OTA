
import network
import socket
import time
import machine
import os
import json
import gc
import requests

# ===== Wi-Fi 設定：請填入實際熱點資訊 =====
SSID = "labor"
PASSWORD = "98668800"

CURRENT_VERSION = "0.0.5"
VERSION_URL = (
    "https://raw.githubusercontent.com/"
    "abbie210238/ESP32_MicroPython_OTA/"
    "main/version.json"
)
CHECK_INTERVAL = 60

led = machine.Pin(2, machine.Pin.OUT)
led.value(0)


def get_version():
    try:
        with open("version.txt", "r") as f:
            return f.read().strip()
    except Exception:
        return CURRENT_VERSION


def version_tuple(v):
    try:
        parts = tuple(int(x) for x in v.split("."))
        return parts if len(parts) == 3 and min(parts) >= 0 else None
    except Exception:
        return None


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        start = time.time()

        while not wlan.isconnected():
            if time.time() - start > 30:
                print("WiFi connection timeout")
                return wlan
            time.sleep(1)

    if wlan.isconnected():
        print("WiFi connected:", wlan.ifconfig()[0])

    return wlan


def download_text(url):
    response = requests.get(url)
    try:
        if response.status_code != 200:
            raise OSError("HTTP {}".format(response.status_code))
        return response.text
    finally:
        response.close()


def check_update():
    print("Checking GitHub...")
    try:
        data = json.loads(download_text(VERSION_URL))
        remote_version = data.get("version", "")
        firmware_url = data.get("firmware_url", "")

        remote = version_tuple(remote_version)
        current = version_tuple(get_version())

        if remote is None or current is None:
            print("Invalid version")
            return False

        if not firmware_url.startswith("https://"):
            print("Invalid firmware URL")
            return False

        if remote <= current:
            print("Already latest:", get_version())
            return False

        code = download_text(firmware_url)
        if len(code) < 10:
            print("Downloaded file too small")
            return False

        compile(code, "main.py", "exec")

        with open("main.new", "w") as f:
            f.write(code)

        try:
            os.remove("main.bak")
        except OSError:
            pass

        os.rename("main.py", "main.bak")
        try:
            os.rename("main.new", "main.py")
            with open("version.txt", "w") as f:
                f.write(remote_version)
        except Exception:
            try:
                os.rename("main.bak", "main.py")
            except OSError:
                pass
            raise

        print("Update installed:", remote_version)
        time.sleep(2)
        machine.reset()
        return True

    except Exception as e:
        print("Update failed:", e)
        try:
            os.remove("main.new")
        except OSError:
            pass
        return False


def make_page():
    state = "開啟" if led.value() else "關閉"
    color = "#34d399" if led.value() else "#64748b"
    return """<!doctype html>
<html lang="zh-TW">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESP32 LED 控制</title>
<style>
body{font-family:system-ui;background:#0b1020;color:#eef3ff;
text-align:center;padding:24px}
main{max-width:420px;margin:30px auto;background:#131b2e;
padding:24px;border-radius:18px}
button{font-size:18px;padding:14px 22px;margin:8px;
border:0;border-radius:10px}
.on{background:#a7f3d0}.off{background:#fecdd3}
</style>
<main>
<h1>ESP32 Remote Dashboard</h1>
<p>裝置 IP：""" + wlan.ifconfig()[0] + """</p>
<p>GPIO 2 燈光：<strong style="color:""" + color + """">""" + state + """</strong></p>
<form action="/on" method="get"><button class="on">開燈</button></form>
<form action="/off" method="get"><button class="off">關燈</button></form>
<form action="/" method="get"><button>更新狀態</button></form>
</main></html>"""


def handle_client(client):
    try:
        client.settimeout(2)
        request = client.recv(1024).decode()
        first_line = request.split("\r\n")[0]
        path = first_line.split(" ")[1] if len(first_line.split(" ")) > 1 else "/"

        if path.startswith("/on"):
            led.value(1)
        elif path.startswith("/off"):
            led.value(0)

        body = make_page()
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Connection: close\r\n"
            "Cache-Control: no-store\r\n\r\n" + body
        )
        client.send(response.encode())

    except Exception as e:
        print("HTTP error:", e)
    finally:
        client.close()


wlan = connect_wifi()
if wlan.isconnected():
    check_update()

addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(addr)
server.listen(2)
server.settimeout(1)

print("Web server ready")
if wlan.isconnected():
    print("Open http://{}".format(wlan.ifconfig()[0]))

last_check = time.time()

while True:
    try:
        if not wlan.isconnected():
            wlan = connect_wifi()

        try:
            client, remote = server.accept()
            handle_client(client)
        except OSError:
            pass

        if time.time() - last_check >= CHECK_INTERVAL:
            last_check = time.time()
            if wlan.isconnected():
                # 暫停監聽，避免 OTA 下載期間持續接收連線
                server.close()
                check_update()
                server = socket.socket()
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(addr)
                server.listen(2)
                server.settimeout(1)

        gc.collect()

    except Exception as e:
        print("Main loop error:", e)
        time.sleep(2)

