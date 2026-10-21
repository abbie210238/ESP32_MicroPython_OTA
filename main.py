import network
import time
import machine

SSID = "labor"
PASSWORD = "98668800"

CURRENT_VERSION = "0.0.1"

led = machine.Pin(2, machine.Pin.OUT)
led.value(1)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

print("Connecting to WiFi...")

if not wlan.isconnected():
    wlan.connect(SSID, PASSWORD)

    timeout = 30
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1

if wlan.isconnected():
    print("\nWiFi connected")
    print("IP address:", wlan.ifconfig()[0])
    print("MicroPython version:", CURRENT_VERSION)
else:
    print("WiFi connection failed")

while True:
    time.sleep(1)
