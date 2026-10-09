' gps.bas -- GPS page for the car club (MMBasic), ported from
' club.py's gps_page.py: big KM/H speed, course, lat/lon, altitude and
' satellites, UTC time, and the top menu bar: GET FIX and MENU, with the
' ticker along the bottom. (The weather is in every page's ticker now --
' club.bas fetches it -- so it isn't on this page any more.)
'
' The GPS is an NMEA module on COM1 (RX GP1, TX GP0) at 9600, the same
' wiring club.py used. Like club.py, this page reads the sentences itself
' ($..RMC for position/speed/course/time, $..GGA for satellites/altitude)
' instead of MMBasic's built-in GPS reader, so it can show what's going
' on while it searches: "Reading GPS: 240 sentences, 3 satellites, no fix
' yet". The last fix is kept in lastfix.dat and shown when the page opens.
' lastfix.dat is also where the weather (net.inc) finds its location.
'
' Build with: python mmbasic/build.py  (writes ../gps.bas)

Option EXPLICIT
Option DEFAULT NONE

Const Q$ = Chr$(34)
Const FIX_FILE$ = "lastfix.dat"

Dim integer j, v, gpsOpen, lx, lw
Dim string cmd$
' what the ticker last said about the GPS
Dim string gpsMsg$
Dim integer sx, sy
Dim float lat, lon
Dim string lastT$
' what the sentences have said: fix, speed (knots), course, altitude,
' satellites, UTC time, how many sentences so far, and the part-line
Dim integer fixOK, sats, nSent, opened
' from $..GSV: satellites in view, and the strongest signal (dB, 0 = none)
Dim integer inView, bestSnr, gsvSnr
Dim float spdKn, trk, alt
Dim string utc$, part$

CoreInit
v = AddMenu("GET FIX", "")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "GPS"
Layout
DrawAllBtns
StartCursor
LoadFix
OpenGps
opened = Timer
ShowFix

Do
  j = PollInput()
  If j = -2 Then GoPage "club.bas"
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "gps", "gps.bas"
  If cmd$ = "MENU" Then GoPage "club.bas"
  If cmd$ = "GET FIX" Then
    ' always say something, even if nothing has changed
    gpsMsg$ = ""
    ShowFix
  EndIf
  ReadGps
  If Time$ <> lastT$ Then
    lastT$ = Time$
    ShowFix
  EndIf
  Pause 5
Loop

Sub Layout
  Local integer m
  m = W \ 40
  lx = W \ 4
  lw = W \ 2
  sx = W \ 2
  sy = H * 23 \ 100
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

Sub OpenGps
  gpsOpen = 0
  On Error Skip
  SetPin GP1, GP0, COM1
  On Error Skip
  Open "COM1:9600" As #5
  If MM.Errno = 0 Then gpsOpen = 1
End Sub

' the last fix this board had, so the page isn't blank while it searches
Sub LoadFix
  Local string l$
  On Error Skip
  Open FIX_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  If Not Eof(#1) Then Line Input #1, l$
  Close #1
  lat = Val(Fld$(l$, 1))
  lon = Val(Fld$(l$, 2))
End Sub

Sub SaveFix
  On Error Skip
  Open FIX_FILE$ For Output As #1
  If MM.Errno Then Exit Sub
  Print #1, Str$(lat, 0, 6) + "|" + Str$(lon, 0, 6) + "|" + utc$
  Close #1
End Sub

' whatever has arrived on COM1, split into lines, each $..RMC / $..GGA read
Sub ReadGps
  Local integer n, p
  Local string l$
  If Not gpsOpen Then Exit Sub
  n = Loc(#5)
  If n = 0 Then Exit Sub
  part$ = part$ + Input$(Min(n, 255 - Len(part$)), #5)
  Do
    p = Instr(part$, Chr$(10))
    If p = 0 Then Exit Do
    l$ = Left$(part$, p - 1)
    part$ = Mid$(part$, p + 1)
    If Right$(l$, 1) = Chr$(13) Then l$ = Left$(l$, Len(l$) - 1)
    If Left$(l$, 1) = "$" Then Sentence l$
  Loop
  ' a runaway line with no end (noise) is dropped
  If Len(part$) >= 250 Then part$ = ""
End Sub

' field n (0 = the $GPRMC name) of a comma sentence, "" if it's empty
Function NF$(l$, n As integer)
  Local integer i, p, q
  p = 1
  For i = 1 To n
    q = Instr(p, l$, ",")
    If q = 0 Then Exit Function
    p = q + 1
  Next
  q = Instr(p, l$, ",")
  If q = 0 Then q = Instr(p, l$, "*")
  If q = 0 Then q = Len(l$) + 1
  NF$ = Mid$(l$, p, q - p)
End Function

' ddmm.mmmm (or dddmm.mmmm) and N/S/E/W -> signed degrees
Function GeoDeg(v$, h$) As float
  Local integer p
  Local float d
  p = Instr(v$, ".")
  If p < 4 Then Exit Function
  d = Val(Left$(v$, p - 3)) + Val(Mid$(v$, p - 2)) / 60
  If h$ = "S" Or h$ = "W" Then d = -d
  GeoDeg = d
End Function

Sub Sentence(l$)
  Local string t$
  Local integer i
  nSent = nSent + 1
  t$ = Mid$(l$, 4, 3)
  If t$ = "RMC" Then
    fixOK = (NF$(l$, 2) = "A")
    t$ = NF$(l$, 1)
    If Len(t$) >= 6 Then utc$ = Mid$(t$, 1, 2) + ":" + Mid$(t$, 3, 2) + ":" + Mid$(t$, 5, 2)
    If fixOK Then
      lat = GeoDeg(NF$(l$, 3), NF$(l$, 4))
      lon = GeoDeg(NF$(l$, 5), NF$(l$, 6))
      spdKn = Val(NF$(l$, 7))
      trk = Val(NF$(l$, 8))
    EndIf
  ElseIf t$ = "GGA" Then
    sats = Val(NF$(l$, 7))
    If NF$(l$, 9) <> "" Then alt = Val(NF$(l$, 9))
  ElseIf t$ = "GSV" Then
    ' $GPGSV,msgs,msg,inview, then (id,elev,azim,snr) x up to 4
    inView = Val(NF$(l$, 3))
    If Val(NF$(l$, 2)) = 1 Then gsvSnr = 0
    For i = 0 To 3
      gsvSnr = Max(gsvSnr, Val(NF$(l$, 7 + 4 * i)))
    Next
    ' the last of the set: that's the strongest this time round
    If NF$(l$, 1) = NF$(l$, 2) Then bestSnr = gsvSnr
  EndIf
End Sub

Sub ShowFix
  Local integer y, dy, spd
  Local string t$, k$
  Static integer saved
  dy = fh(0) + 6
  y = H * 40 \ 100
  If fixOK Then
    spd = Int(spdKn * 1.852)
    ' the big speed readout, in the firmware's large number font
    CurHide
    Box sx - 120, sy - 30, 240, 60, 1, C_PAGE, C_PAGE
    Text sx - 30, sy, Str$(spd), "RM", 6, 1, C_INK, C_PAGE
    CurShow
    PText sx - 20, sy + 10, "KM/H", "L", 0, C_INK
    PField lx, y, lw, "Course: " + Str$(Int(trk)) + " deg", 0
    PField lx, y + dy, lw, "Lat: " + Str$(lat, 0, 5), 0
    PField lx, y + 2 * dy, lw, "Lon: " + Str$(lon, 0, 5), 0
    PField lx, y + 3 * dy, lw, "Alt: " + Str$(Int(alt)) + " m   Sats: " + Str$(sats), 0
    PField lx, y + 4 * dy, lw, "UTC: " + utc$, 0
    t$ = "GPS fix: " + Str$(lat, 0, 5) + ", " + Str$(lon, 0, 5) + "  " + Str$(sats) + " satellites  " + Str$(spd) + " km/h"
    ' the ticker gets the position to ~100 m, so it isn't restarting
    ' every second while the car moves
    k$ = "GPS fix: " + Str$(lat, 0, 3) + ", " + Str$(lon, 0, 3) + "  " + Str$(sats) + " satellites"
    ' keep it for next time, once a minute at most
    If Timer - saved > 60000 Or saved = 0 Then
      SaveFix
      saved = Timer
    EndIf
  Else
    If Not gpsOpen Then
      t$ = "GPS: can't open COM1 (GP1/GP0)"
      k$ = t$
    ElseIf nSent = 0 Then
      t$ = "GPS: nothing received in " + Str$((Timer - opened) \ 1000) + "s - is the module wired to GP1/GP0?"
      k$ = "GPS: nothing received - is the module wired to GP1/GP0?"
    Else
      t$ = "Reading GPS: " + Str$(nSent) + " sentences, " + Str$(inView) + " in view, best " + Str$(bestSnr) + " dB"
      If inView = 0 Then
        k$ = "GPS: working, but it can't see ANY satellites - the aerial needs open sky above it"
      ElseIf bestSnr < 25 Then
        k$ = "GPS: " + Str$(inView) + " satellites in view but too weak (best " + Str$(bestSnr) + " dB) - move it nearer the sky"
      Else
        k$ = "GPS: " + Str$(inView) + " satellites in view (best " + Str$(bestSnr) + " dB) - working towards a fix"
      EndIf
    EndIf
    CurHide
    Box sx - 120, sy - 30, 240, 60, 1, C_PAGE, C_PAGE
    CurShow
    PText sx, sy, "--  KM/H", "C", 1, C_INK
    PField lx, y, lw, Fit$(t$, lw - 10), 0
    If lat <> 0 Or lon <> 0 Then
      PField lx, y + dy, lw, "Lat: " + Str$(lat, 0, 5) + " (last)", 0
      PField lx, y + 2 * dy, lw, "Lon: " + Str$(lon, 0, 5) + " (last)", 0
    Else
      PField lx, y + dy, lw, "Lat: --", 0
      PField lx, y + 2 * dy, lw, "Lon: --", 0
    EndIf
    PField lx, y + 3 * dy, lw, "In view: " + Str$(inView) + "   Best signal: " + Str$(bestSnr) + " dB", 0
    PField lx, y + 4 * dy, lw, "UTC: " + Choice(utc$ = "", "--", utc$), 0
  EndIf
  ' into the ticker only when it changes (not the ever-rising sentence
  ' count, or the ticker would restart every second)
  If k$ <> gpsMsg$ Then
    gpsMsg$ = k$
    TickerMsg k$
  EndIf
End Sub
