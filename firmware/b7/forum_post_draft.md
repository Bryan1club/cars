**V7.0.00b7 HDMIBTH on Pico Computer 3: Bluetooth keyboard and mouse results**

First, thank you for adding Bluetooth. The JBL Flip 6 works perfectly:
`BLUETOOTH SCAN`, `BLUETOOTH CONNECT`, then MP3 playback through the speaker.

Two problems with standard retail Bluetooth devices (Logitech K250 keyboard
and M196 mouse, both Bluetooth LE, both bought at JB Hi-Fi), on the same
board:

1. **K250 keyboard:** pairs and bonds fine, but no keystrokes reach the
   console, even at the `>` prompt. `BLUETOOTH STATUS` after `BLUETOOTH
   FORGET` and a re-pair:
```
Bluetooth: on
Keyboard:  connected
Speaker:   not connected
Bond store: 2 writes, longest 165 ms, total 328 ms
Keyboard security: 1 pairings, 1 re-encryptions, 0 interrupted since boot
Keyboard bonds held: 1
Last pairing: D1:13:CB:14:D1:05 (random), bond stored
```
The same K250 pairs and types fine on a MicroPython/btstack build.

2. **M196 mouse:** each time I put the M196 into pairing mode, the K250 drops
   and reconnects (the repeats below are my pairing attempts), and every
   key press on the K250 then shows a new 6-digit passkey. The M196 itself
   never connects (`BLUETOOTH SCAN` lists only Classic audio devices, so I
   know it won't appear there):
```
> bluetooth scan
90:F2:60:76:BE:F0  -44 dBm  Audio  "Ruddy's JBL Flip 6"
1 device found
> Bluetooth Keyboard Disconnected
> Bluetooth Keyboard Connected
(repeats, one pair per attempt)
```

More detail on the K250:
- After `BLUETOOTH FORGET` and a re-pair, with a stale bond on the board the
  pairing failed over and over (`Last pairing: failed, status 0x05 reason
  0x0A`, a new passkey each try). With the bond cleared and the passkey typed
  on the K250 it paired first time (`150597`, `Bluetooth Keyboard Connected`,
  `bond stored`).
- Once connected, **no key is received**, even with the USB keyboard and USB
  mouse unplugged (so it is not a channel clash) and after a reboot.
- It happens every time I have tried it (3 fresh pairings).

With the USB keyboard and mouse removed and the K250 connected, putting the
M196 into pairing mode gave nine `Bluetooth Keyboard Disconnected` /
`Bluetooth Keyboard Connected` pairs in a row and nothing else (no mouse
message). It looks as if the two devices keep taking the same HID slot from
each other. Does the BTH build support a BLE keyboard and a BLE mouse at the
same time?

I had a look at `bluetooth/BTKeyboard.c` in the b7 tag. In
`bth_raw_notification_handler` only an **8-byte** notification is passed to
`process_kbd_report`; any other length is dropped silently unless
`BTH_DEBUG_LOG` is defined, and the `GATTSERVICE_SUBEVENT_HID_REPORT` decode
is commented out. If the Logitech K250 sends its key reports with a report-ID
prefix (9 bytes), or in another size, it would connect, bond and then deliver
nothing, which is exactly what I see. I have not yet captured the K250's
actual report length. Could you check what a K250 sends, or tell me the
easiest way to print the raw report length on the release build?

Both devices work on a MicroPython/btstack build on the same hardware (the
K250 pairs with its passkey, the M196 auto-connects), so they are good BLE
devices. Your beta 7 notes ask for feedback from a passkey keyboard, so this
is one: it shows the passkey, pairs and bonds, but sends no keys. Is there a
way to see whether HID reports are arriving? Is a keyboard + mouse + speaker
combination meant to work together? Finally, a WiFi/telnet build that also has
Bluetooth (HDMIWEB + BTH) would be great: is that possible?

Setup: PicoMiteHDMIBTH V7.0.00b7, OPTION AUDIO BLUETOOTH 60, PLATFORM PICO
COMPUTER 3.
