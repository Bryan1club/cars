# main.py -- runs automatically at boot.
# Starts the board as its own access point (pico1), also tries to
# connect to a known wifi network to sync the clock via NTP, then
# launches the car club system.

import network
import time
from pcshell import run


def connect_wifi(ssid, password, timeout=10, static_ip=None):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if static_ip:
        # fixed IP for this board (subnet, gateway, dns) -- so other
        # boards can reach it reliably for upload forwarding (see
        # forward.txt / FORWARD_FILE in club.py) instead of chasing
        # whatever address DHCP handed out this time
        sta.ifconfig((static_ip, STATIC_SUBNET, STATIC_GATEWAY, STATIC_DNS))
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
        return
    # also write the NTP time back to the DS3231 hardware RTC, so it
    # stays correct across a power loss even if a future boot can't
    # reach wifi -- boards without a DS3231 (or a dead backup battery)
    # just fail this silently, same as before
    try:
        import ds3231
        ds3231.settime(t[0], t[1], t[2], t[3], t[4], t[5])
    except Exception:
        pass


# start the access point so a phone/laptop can connect directly
# -- fill in your own AP name/password before deploying
AP_SSID = "pico1"
AP_PASSWORD = "PUT_YOUR_AP_PASSWORD_HERE"

# also try to join a known network, and sync the clock if it works
# -- fill in your own home/venue network before deploying
HOME_SSID = "PUT_YOUR_WIFI_SSID_HERE"
HOME_PASSWORD = "PUT_YOUR_WIFI_PASSWORD_HERE"

# optional fixed IP on that network -- leave STATIC_IP as None to keep
# using DHCP. Set it per-board so other boards can reliably reach this
# one for upload forwarding (see forward.txt / FORWARD_FILE in club.py)
# instead of the address changing every time DHCP reassigns it.
STATIC_IP = None
STATIC_SUBNET = "255.255.255.0"
STATIC_GATEWAY = "10.108.72.181"
STATIC_DNS = "10.108.72.181"

ap = network.WLAN(network.AP_IF)
ap.config(essid=AP_SSID, password=AP_PASSWORD)
ap.active(True)

sta = connect_wifi(HOME_SSID, HOME_PASSWORD, static_ip=STATIC_IP)
if sta:
    sync_clock()

run('/sd/club.py')