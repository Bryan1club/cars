## PicoMite V7.0.00b7: BT + WiFi together - speed, memory and audio results

Peter, you said BT and WiFi will never run together in MMBasic because
there's not enough room left for large programs. I wanted numbers, so I
benchmarked two Pico Computer 3 boards (RP2350, HDMI, 640x480) with the same
program and the same Bluetooth speaker (JBL Flip 6). Short version: speed is
unaffected, the memory cost is small, and the one real problem (dropped
audio with WiFi up) has a workaround and looks fixable.

**Board A:** your release `PicoMiteHDMIBTHV7.0.00b7.uf2` (BT, no WEB).
**Board B:** my own build, one image with BT and WEB together (`HDMIBTHWEB`,
1.62 MB, gcc 13). It is built from the public git tag PicoMite-V7.0.00b7
(commit b40e71f) plus my CMake changes to add the combined variant. A plain
BT-only build from that same tag does not contain the Bluetooth status
counters your release has (send errors, stream starts, bitpool lowered), so
the release is newer than the tag.

Both report `MM.VER = 7.000007`. Timing program: `bench.bas` (about 50
lines, attached), using `TIMER` around each loop. Times are in milliseconds,
so lower is faster. Idle results are the mean of 5 runs; the figure in
brackets is half the min-to-max spread.

### 1. Speed and memory, idle (no music, no network traffic)

| Test | A: release BT | B: BT + WiFi | B vs A |
|---|---|---|---|
| Integer loop, 300k | 3852 (±3) | 3708 (±2) | -3.7% |
| Float SQR/SIN, 50k | 1250 (±1) | 1110 (±1) | -11.1% |
| Array fill, 10 x 10k | 1309 (±1) | 1264 (±2) | -3.5% |
| String ops, 4000 | 82 (±1) | 80 (±1) | -2.3% |
| Full-screen fills, 40 | 60 (±1) | 60 (±0) | +1.4% |
| Text draws, 300 | 70 (±1) | 73 (±1) | +5.7% |

| | A: release BT | B: BT + WiFi | Difference |
|---|---|---|---|
| Free RAM (heap) | 6437 KB | 6392 KB | -45 KB |
| Free program space | 179 KB | 155 KB | -24 KB |
| Firmware image | 1.42 MB | 1.62 MB | +216 KB |

- Having WiFi compiled in costs no measurable speed. I would not read the
  11% float gain as a feature: the two builds also differ in toolchain.
- The memory difference is partly my own choice. I set the combined build's
  heap to 184 KB and program size to 156 KB as provisional values (the BT
  build uses 228 KB and 180 KB). Treat 24 KB / 45 KB as an upper bound until
  those are tuned against what the linker allows.

### 2. Streaming music while running the benchmark

Same speaker and MP3 (Stairway to Heaven, SBC 44100 Hz), benchmark run over
the console while it plays. These runs used the speaker's default bitpool 40.

| Test | A idle | A streaming | B idle | B streaming |
|---|---|---|---|---|
| Integer loop, 300k | 3852 | 4582 | 3708 | 4235 |
| Float SQR/SIN, 50k | 1250 | 1412 | 1110 | 1299 |
| Array fill, 10 x 10k | 1309 | 1559 | 1264 | 1443 |
| String ops, 4000 | 82 | 97 | 80 | 93 |
| Full-screen fills, 40 | 60 | 71 | 60 | 69 |
| Text draws, 300 | 70 | 83 | 73 | 87 |

A: mean of 3 runs while streaming. B: mean of 7. Streaming slows both boards
by 14-21%, and the audio encoder uses 7-11% of the CPU.

### 3. Audio quality: dropped samples with WiFi up

The dropped-sample count comes from `BLUETOOTH STATUS` (it resets each time
it is printed). Board B was flashed with two images in turn, so those two
columns are the same board, speaker and MP3 with only the firmware changed.

| | A: release (BT) | B: tag, BT only | B: tag + WiFi |
|---|---|---|---|
| Samples dropped | 0 | 0 | about 3,700-3,900 per second |
| Underruns | 0 | 0 | 0 |
| Longest send wait | 13-48 ms | 15 ms | 114-172 ms |
| Audible static | none | none | yes |

What I found:

- Bluetooth audio from the b7 source is clean on its own, on both boards.
- With WiFi connected (even idle), each audio packet sometimes waits
  100-170 ms for the radio. The encoder falls more than 250 ms behind and
  discards audio, which is the static.
- It is not the CPU: the encoder's timer is never late by more than 23-28 ms,
  and the drop rate is the same with or without the benchmark running.
- Not the heartbeat LED either. I made the WiFi heartbeat leave the LED alone
  while a speaker streams (as `bt_keyboard_poll` already does) and tried
  `OPTION HEARTBEAT OFF`; the drops remained.
- Capping the SBC bitpool at 28 instead of the speaker's 40 gives 0 dropped
  samples over 36 s with WiFi connected, and it sounds fine. So it looks like
  a throughput limit on the shared CYW43 radio, and a lower bitrate fits.

My guess, not checked: your release's "bitpool lowered" counter suggests it
already backs off the bitrate when sending falls behind, which would fix this
properly (full quality when the radio is quiet, lower only when needed).
Peter, is that right, and which commit is the b7 BTH release built from?

### 4. File transfer while streaming

On board B (bitpool 28, WiFi connected, song playing from USB):

- TFTP PUT of a 1.7 MB file to the SD card: about 65 KB/s, 0 dropped samples,
  0 underruns, longest send wait about 100 ms.
- I could not verify the file bytes (the TFTP read-back failed with
  "Connect request failed"), only that TFTP reported success and the size
  matched.
- Playback stopped during or after the transfer. The Bluetooth link stayed up
  and its counters were clean, so I suspect the MP3 player stopped, not
  Bluetooth. Not yet understood.
- Separately, listing and running files on the SD card while a song played
  caused a 593 ms send wait and about 120,000 dropped samples once, and later
  the board hung until a hard reset. I have not reproduced that yet, so
  treat it as a lead, not a conclusion.

### Method

Flashed over SWD with OpenOCD. Programs were loaded over telnet (B) and
serial (A). Results were read from the console. Nothing else was running
apart from the music where stated.
