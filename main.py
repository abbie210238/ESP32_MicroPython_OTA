
import network
import time
import machine
import os
import json
import gc
import requests

# =========================
# 設定
# =========================
SSID = "a@iPhone"
PASSWORD = "199808300"

CURRENT_VERSION = "0.0.3"

VERSION_URL = (
    "https://raw.githubusercontent.com/"
    "abbie210238/ESP32_MicroPython_OTA/"
    "main/version.json"
)

CHECK_INTERVAL = 60

led = machine.Pin(2, machine.Pin.OUT)
led.value(1)


def get_version():
    try:
        with open("version.txt", "r") as f:
            return f.read().strip()
    except Exception:
        return CURRENT_VERSION


def version_tuple(v):
    try:
        parts = v.split(".")
        if len(parts) != 3:
            return None
        nums = tuple(int(x) for x in parts)
        if any(x < 0 for x in nums):
            return None
        return nums
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
            return

        if not firmware_url.startswith("https://"):
            print("Invalid firmware URL")
            return

        if remote <= current:
            print("Already latest:", get_version())
            return

        print("New version:", remote_version)

        code = download_text(firmware_url)

        if len(code) < 10:
            print("Downloaded file too small")
            return

        compile(code, "main.py", "exec")

        # 寫入暫存檔，保留原程式
        with open("main.new", "w") as f:
            f.write(code)

        try:
            os.remove("main.bak")
        except OSError:
            pass

        try:
            os.rename("main.py", "main.bak")
        except OSError:
            pass

        try:
            os.rename("main.new", "main.py")

            with open("version.txt", "w") as f:
                f.write(remote_version)

        except Exception:
            try:
                os.remove("main.py")
            except OSError:
                pass

            try:
                os.rename("main.bak", "main.py")
            except OSError:
                pass

            raise

        print("Update installed:", remote_version)
        time.sleep(2)
        machine.reset()

    except Exception as e:
        print("Update failed:", e)

        try:
            os.remove("main.new")
        except OSError:
            pass


# =========================
# 主程式
# =========================
wlan = connect_wifi()

check_update()
last_check = time.time()

while True:
    try:
        if not wlan.isconnected():
            wlan = connect_wifi()

        if time.time() - last_check >= CHECK_INTERVAL:
            last_check = time.time()
            if wlan.isconnected():
                check_update()

        time.sleep(1)
        gc.collect()

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
