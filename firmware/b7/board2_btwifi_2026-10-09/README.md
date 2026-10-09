# Board 2: Bluetooth + WiFi together (2026-10-09)

Working state: Flip 6 audio over Bluetooth with WiFi/telnet/TFTP at the same
time, no static. Flashed on board 2.

## Files
- `PicoMite_HDMIBTHWEB_bitpool28_ledfix.bin` - the image on board 2 now.
- `PicoMite_HDMIBTHWEB_before_ledfix.bin` - the earlier combined build (static
  with WiFi up). Kept for comparison only.
- `pm7_changes_vs_b7_tag.patch` - every local change in C:\build\pm7 on top of
  Peter's b7 tag (base commit in `base_commit.txt`): the HDMIBTHWEB CMake
  variant, boot banner "PicoMiteHDMIBTHWEB", heartbeat LED fix in net/WiFi.c,
  and the bitpool cap.

## What is temporary
The bitpool cap in bluetooth/BTAudio.c (`if (bitpool > 28) bitpool = 28;`) is
an EXPERIMENT. It lowers the bitrate so the shared radio keeps up with WiFi on.
Real fix: adaptive bitpool (lower only when sends fall behind).
`HEAP_MEMORY_SIZE` 184 KB / `MAX_PROG_SIZE` 156 KB in configuration.h for
this variant are provisional guesses, not tuned.

## Build and flash
Build: `cmake --build buildweb` in C:\build\pm7 (gcc 13.3, pico-sdk 2.3.1).
The ninja run ends with a picotool segfault on the UF2 step; harmless, the
.bin is fine. Flash the .bin with OpenOCD on Computer B (2040W probe on the
target board): `adapter speed 500`, `flash write_image erase X.bin
0x10000000`, `verify_image`, `reset run` (about 65 s).
Same-layout reflash keeps options and the Bluetooth bond; switching between
BTH and BTHWEB images resets options (re-enter OPTION WIFI, OPTION TELNET
CONSOLE ON, OPTION AUDIO DISABLE then BLUETOOTH, and re-pair the speaker).
