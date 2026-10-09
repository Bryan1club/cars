' bench.bas - identical benchmark for comparing PicoMite firmware builds
' (e.g. BT-only V7b7 on board 4 vs BT+WiFi build on board 2).
' Each test prints its time in milliseconds; lower is faster.
' Run it with nothing else active (no music, no network traffic) for a fair baseline.
OPTION EXPLICIT
OPTION DEFAULT NONE

DIM INTEGER t0, i, j, n
DIM FLOAT f
DIM STRING s$
DIM INTEGER arr%(9999)

PRINT "MM.VER = "; MM.VER
PRINT "Heap before tests (bytes free): "; MM.INFO(HEAP)

' 1. Integer maths: tight loop, shows raw interpreter speed
t0 = TIMER
n = 0
FOR i = 1 TO 300000
  n = n + (i AND 7) * 3
NEXT i
PRINT "1 integer loop 300k   : "; TIMER - t0; " ms"

' 2. Floating point maths: SQR and SIN stress the FPU/library
t0 = TIMER
f = 0
FOR i = 1 TO 50000
  f = f + SQR(i) * SIN(i / 100)
NEXT i
PRINT "2 float sqr/sin 50k    : "; TIMER - t0; " ms"

' 3. Array fill and sum: memory access speed
t0 = TIMER
FOR j = 1 TO 10
  FOR i = 0 TO 9999
    arr%(i) = i * j
  NEXT i
NEXT j
PRINT "3 array fill 10x10k    : "; TIMER - t0; " ms"

' 4. String building: heap allocation churn
t0 = TIMER
FOR j = 1 TO 20
  s$ = ""
  FOR i = 1 TO 200
    s$ = LEFT$(s$ + "x", 250)
  NEXT i
NEXT j
PRINT "4 string ops 4000      : "; TIMER - t0; " ms"

' 5. Display fill: the HDMI work shares the CPU, so this is a useful tell
t0 = TIMER
FOR i = 1 TO 20
  BOX 0, 0, MM.HRES, MM.VRES, 0, RGB(BLACK), RGB(BLUE)
  BOX 0, 0, MM.HRES, MM.VRES, 0, RGB(BLACK), RGB(RED)
NEXT i
CLS
PRINT "5 fullscreen fills 40  : "; TIMER - t0; " ms"

' 6. Text drawing: many small draws, like a dashboard redraw
t0 = TIMER
FOR i = 1 TO 300
  TEXT (i * 7) MOD 600, (i * 13) MOD 400, "Bench " + STR$(i), "LT", 1, 1, RGB(WHITE), RGB(BLACK)
NEXT i
PRINT "6 text draws 300       : "; TIMER - t0; " ms"
CLS

PRINT "Heap after tests (bytes free): "; MM.INFO(HEAP)
PRINT "Done. Program memory report:"
MEMORY
