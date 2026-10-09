# Session report 2026-10-08: Peter's PicoMite V7.0.00b7 Bluetooth on board 2

## What works
- b7 `PicoMiteHDMIBTH` flashed to board 2 (BOOTSEL drive E: on Computer B). `MM.VER` = 7.000007.
- **JBL Flip 6**: `BLUETOOTH SCAN`, `BLUETOOTH CONNECT`, MP3 playback from the file manager. Needs `OPTION AUDIO BLUETOOTH` (currently `OPTION AUDIO BLUETOOTH 60`; I2S GP10,GP22 was replaced). The board remembers the speaker and reconnects after a reset.

## What does not
- **K250 (Logitech BLE keyboard)**: pairs with the passkey, bond stored, `BLUETOOTH STATUS` says connected, but **no key is received**. Reproduced 3 times, also with the USB keyboard and mouse unplugged (so not a channel clash).
  - A stale bond on the board makes re-pairing fail (`Last pairing: failed, status 0x05 reason 0x0A`, a new passkey each try). Fix: `BLUETOOTH FORGET`, then pair and type the passkey on the K250.
- **M196 (BLE mouse)**: putting it in pairing mode makes the K250 disconnect/reconnect over and over (9 pairs in the last log), no mouse message. Possible cause: one HID slot that the two devices keep taking from each other (unconfirmed).
- **No WiFi/telnet**: BTH and WEB are separate builds in Peter's CMake (`HDMIBTH` vs `HDMIWEB`).
- **Board 1 GPS** never fixed on the drive with the dashcam. Not investigated further; see the questions in the chat (LED, sentences, satellites, windscreen).

## Facts learned from Peter's source (tag `PicoMite-V7.0.00b7`, fetched into `C:\build\picomite`)
- The manual says BLE only (Classic keyboards/mice do not connect), pairing is automatic, and keyboard + mouse + speaker are supposed to work together.
- Peter's release notes ask for feedback from a passkey keyboard: the K250 is one.
- In `bluetooth/BTKeyboard.c`, `bth_raw_notification_handler` treats only **8-byte** notifications as keyboard reports. Other lengths are dropped silently unless `BTH_DEBUG_LOG` is defined, and the main `GATTSERVICE_SUBEVENT_HID_REPORT` decode is commented out. If the K250 sends e.g. 9 bytes (report-ID prefix) it would connect and type nothing. This is a hypothesis.

## Debug build for the morning
- `PicoMiteHDMIBTH_V7.0.00b7_BTHDEBUG.uf2` (this folder): stock b7 with `BTH_DEBUG_LOG` switched on. Source is the clean worktree `C:\build\pm7` (tag b7, one-line change in `BTKeyboard.c`). Build logs: `C:\build\b7dbg_configure.log`, `b7dbg_build.log`.
- Plan: flash it to board 2 (BOOTSEL, E: on B), `BLUETOOTH FORGET`, pair the K250, press keys, and read the `[BT] raw notify handle=... len=...` lines in Tera Term. That shows the K250's real report length, and whether the fix is a one-line change or something for Peter.
- The flash may reset options, so expect to redo `OPTION AUDIO BLUETOOTH` and the Flip 6 connect.

## Setup notes
- Board 2 console: `OPTION SERIAL CONSOLE COM2,GP8,GP9` via a CH340 on Computer B (COM3 now; COM9 earlier). Tera Term portable at `C:\Users\Public\teraterm\teraterm-5.7.0-x64`, desktop shortcut on B. Log: Desktop `8-10 Debugging.txt` (stops after a reboot; reopen COM3 and restart the log).
- Do not paste console output back into the console: it runs as commands.
- The forum post draft is `forum_post_draft.md` (the owner posts it himself).
