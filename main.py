# main.py -- runs automatically at boot.
# Starts the board as its own access point (pico1), also tries to
# connect to a known wifi network to sync the clock via NTP, then
# launches the car club system.

import network
import time
from pcshell import run


def connect_wifi(ssid, password, timeout=10):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)
    for i in range(timeout):
        if sta.isconnected():
            print('connected:', sta.ifconfig())
            return sta
        time.sleep(1)
    print('failed to connect')
    return None


def sync_clock():
    try:
        import ntptime
        import machine
        ntptime.settime()
        t = time.localtime(time.time() + 9 * 3600 + 30 * 60)
        rtc = machine.RTC()
        rtc.datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
        print('clock synced')
    except Exception as e:
        print('clock sync failed:', e)


# start the access point so a phone/laptop can connect directly
# -- fill in your own AP name/password before deploying
AP_SSID = "pico1"
AP_PASSWORD = "PUT_YOUR_AP_PASSWORD_HERE"

# also try to join a known network, and sync the clock if it works
# -- fill in your own home/venue network before deploying
HOME_SSID = "PUT_YOUR_WIFI_SSID_HERE"
HOME_PASSWORD = "PUT_YOUR_WIFI_PASSWORD_HERE"

ap = network.WLAN(network.AP_IF)
ap.config(essid=AP_SSID, password=AP_PASSWORD)
ap.active(True)

sta = connect_wifi(HOME_SSID, HOME_PASSWORD)
if sta:
    sync_clock()

run('/sd/club.py')