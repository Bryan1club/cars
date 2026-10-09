' wifi.bas -- WIFI page (ADMIN > WIFI), ported from club.py's wifi_page.py:
' what the board is connected to, a SCAN of the networks it can see, and
' a network + password to switch to (e.g. a phone hotspot at a car run).
' Top menu bar: SCAN, CONNECT, BACK. Click a network to pick it, click
' Password to type it.
'
' CONNECT uses OPTION WIFI, which saves the network and restarts the
' board. The stock firmware only allows that at the > prompt, not from a
' running program; if it refuses, the page says so and shows the command.
'
' Build with: python mmbasic/build.py  (writes ../wifi.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXN = 20, ROWS = 11

Dim string ss$(MAXN - 1), pw$, pick$, cmd$
Dim integer rssi(MAXN - 1), count, sel, j, v, i, top
Dim integer lx, ly, lw, rh, fx, fy, fw, sy

CoreInit
v = AddMenu("SCAN", "")
v = AddMenu("CONNECT", "")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "WIFI"
rh = fh(0) + 5
lx = W \ 40
lw = W * 50 \ 100
ly = H * 22 \ 100
fx = lx + lw + W \ 20
fw = W - fx - W \ 40
fy = ly + 2 * rh + 10
sy = H * 14 \ 100
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
DrawAllBtns
StartCursor
sel = -1
ShowStatus
DrawList
DrawForm
TickerMsg "SCAN to look for networks"

Do
  j = PollInput()
  ' wheel, drag and keys on the list (core ListNav): the arrows pick a row
  ' as a click would, Enter clicks it again
  v = ListNav(lx, ly, lw, rh, ROWS, count, top)
  If v = 1 Then DrawList
  If v >= 2 Then
    DrawList
    Clicked lx + 8, ly + 3 + (kbRow - top) * rh + rh \ 2
  EndIf
  If j = -2 Then GoPage "admin.bas"
  If j = -3 Then Clicked clickX, clickY
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "wifi", "wifi.bas"
  Select Case cmd$
    Case "BACK"
      GoPage "admin.bas"
    Case "SCAN"
      DoScan
    Case "CONNECT"
      DoConnect
  End Select
  Pause 10
Loop

Sub ShowStatus
  Local string s$
  Local integer st
  Local string a$
  On Error Skip
  st = MM.Info(WIFI STATUS)
  On Error Skip
  a$ = MM.Info$(IP ADDRESS)
  ' a real IP is the test: WIFI STATUS reads 1 (joined), not 3, when up
  If a$ <> "" And a$ <> "0.0.0.0" Then
    s$ = "Connected - this board is " + a$
  Else
    s$ = "Not connected (status " + Str$(st) + ")"
  EndIf
  CurHide
  Box lx, sy - rh \ 2, W - 2 * lx, rh, 1, C_BAR, C_BAR
  CurShow
  PText lx + 6, sy, s$, "L", 0, C_INK
End Sub

Sub DrawList
  Local integer r, y
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(ss$(top + r), lw - 70), "L", 0, C_INK
      PText lx + lw - 8, y + rh \ 2, Bars$(rssi(top + r)), "R", 0, C_DIM
    EndIf
  Next
  CurShow
End Sub

' signal strength as 1-4 bars
Function Bars$(r As integer)
  Bars$ = String$(Choice(r > -55, 4, Choice(r > -67, 3, Choice(r > -78, 2, 1))), "|")
End Function

Sub DrawForm
  PText fx, fy - rh - fh(0) \ 2, "Network", "L", 0, C_INK
  TextBox fx, fy - rh + fh(0) \ 2, fw, pick$, 0
  PText fx, fy + rh + fh(0) \ 2, "Password", "L", 0, C_INK
  TextBox fx, fy + 2 * rh + fh(0), fw, String$(Len(pw$), "*"), 0
End Sub

Sub DoScan
  Local buf%(600)
  Local string l$, t$
  Local integer p, q, n
  TickerMsg "Scanning..."
  On Error Skip
  WEB SCAN buf%()
  If MM.Errno Then
    TickerMsg "Scan failed: " + MM.ErrMsg$
    Exit Sub
  EndIf
  count = 0
  sel = -1
  top = 0
  n = LLen(buf%())
  p = 1
  Do While p <= n And count < MAXN
    q = LInStr(buf%(), Chr$(10), p)
    If q = 0 Then q = n + 1
    l$ = LGetStr$(buf%(), p, Min(255, q - p))
    p = q + 1
    If Left$(l$, 5) = "ssid:" Then
      t$ = Trim$(Mid$(l$, 7, 32))
      If t$ <> "" Then
        ss$(count) = t$
        rssi(count) = Val(Mid$(l$, Instr(l$, "rssi:") + 5, 5))
        count = count + 1
      EndIf
    EndIf
  Loop
  DrawList
  ShowStatus
  TickerMsg Str$(count) + " networks - click one, type its password, CONNECT"
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      sel = r
      pick$ = ss$(r)
      pw$ = ""
      DrawList
      DrawForm
    EndIf
    Exit Sub
  EndIf
  If x < fx Or x >= fx + fw Then Exit Sub
  If y >= fy - rh + fh(0) \ 2 And y < fy - rh + fh(0) \ 2 + fh(0) + 6 Then
    pick$ = Trim$(EditText$(fx, fy - rh + fh(0) \ 2, fw, pick$))
  ElseIf y >= fy + 2 * rh + fh(0) And y < fy + 2 * rh + 2 * fh(0) + 6 Then
    pw$ = EditPass$(fx, fy + 2 * rh + fh(0), fw, pw$)
  EndIf
End Sub

Sub DoConnect
  If pick$ = "" Then
    TickerMsg "Pick a network first"
    Exit Sub
  EndIf
  TickerMsg "Switching to " + pick$ + " - the board restarts"
  Pause 500
  On Error Skip
  Option WIFI pick$, pw$
  ' only reached if the firmware refused (it restarts the board otherwise)
  TickerMsg "Firmware won't switch here: press Ctrl-C, then at > type  OPTION WIFI " + Chr$(34) + pick$ + Chr$(34) + ", " + Chr$(34) + "password" + Chr$(34)
End Sub
