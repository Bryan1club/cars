Option EXPLICIT
Option DEFAULT NONE
Const USE_MAP = 1
Const F_TEXT = 9, F_TITLE = 10
Const NBMAX = 16
Const BG_FILE$ = "page_bg_640.bmp"
Const CURSOR_FILE$ = "arrow.spr"
Const HOME_DIR$ = "B:/club"
Dim integer C_BLACK, C_GRN_TOP, C_GRN_BASE, C_RED_TOP, C_RED_BASE
Dim integer C_BAR, C_PAGE, C_INK, C_DIM, C_AMBER, C_FACE
Dim string lbl$(NBMAX - 1)
Dim integer bx(NBMAX - 1), by(NBMAX - 1), bw(NBMAX - 1), bh(NBMAX - 1)
Dim integer colA(NBMAX - 1), colB(NBMAX - 1)
Dim integer bstyle(NBMAX - 1)
Const MAXLA = 8
Dim string laN$(MAXLA - 1)
Dim integer laX(MAXLA - 1), laY(MAXLA - 1), laW(MAXLA - 1), laH(MAXLA - 1), nla
Dim integer nb, focus, W, H
Dim integer clickX, clickY
Dim string mitem$(NBMAX - 1)
Dim integer hasBar, barX
Const TICK_MS = 150
Dim integer tkx, tky, tkw, tkh, tkPos, lastTick
Dim integer tickerRaceMode
Dim string ip$, tkMsg$, tkWx$
Dim string tkSeg$(4)
Dim integer hasTouch, hasMouse, gmx, gmy, gml, prevML, curX, curY
Dim integer lastWheel, dragY
Dim integer kbRow, lsKey, lsOn
Dim integer pendClick
Dim integer nm, ach, mch(3), px(4), py(4), pl(4)
Dim integer adv(1, 94), fh(1)
Dim integer fText, fTitle
Dim integer forceBuiltinFont
Dim string cname$, cmd$, town$, where$
Dim float la, lo
Dim integer j, v, fx, fy, fw
CoreInit
v = AddMenu("SAVE", "")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "UNIT NAME"
fx = W \ 4
fw = W \ 2
fy = H * 35 \ 100
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
DrawAllBtns
StartCursor
cname$ = NetLine$(HOME_DIR$ + "/clubname.txt")
PText fx, fy - fh(0) - 20, "Shown on the menu. Blank = CAR CLUB.", "L", 0, C_DIM
PText fx, fy - fh(0) \ 2 - 4, "Name", "L", 0, C_INK
TextBox fx, fy, fw, cname$, 0
town$ = Fld$(NetLine$(HOME_DIR$ + "/home.dat"), 4)
where$ = Fld$(NetLine$(HOME_DIR$ + "/home.dat"), 3)
PText fx, fy + 3 * fh(0) - fh(0) \ 2 - 4, "Town (for the weather)", "L", 0, C_INK
TextBox fx, fy + 3 * fh(0), fw, town$, 0
If where$ <> "" Then PField fx, fy + 5 * fh(0), fw, "Weather is for " + where$, 0
TickerMsg "Click a box to type, then SAVE"
Do
  j = PollInput()
  If j = -2 Then GoPage "admin.bas"
  If j = -3 Then
    If clickX >= fx And clickX < fx + fw And clickY >= fy And clickY < fy + fh(0) + 6 Then cname$ = Trim$(EditText$(fx, fy, fw, cname$))
    If clickX >= fx And clickX < fx + fw And clickY >= fy + 3 * fh(0) And clickY < fy + 4 * fh(0) + 6 Then town$ = Trim$(EditText$(fx, fy + 3 * fh(0), fw, town$))
  EndIf
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "unitname", "unitname.bas"
  If cmd$ = "BACK" Then GoPage "admin.bas"
  If cmd$ = "SAVE" Then
    Open HOME_DIR$ + "/clubname.txt" For Output As #1
    If cname$ <> "" Then Print #1, cname$
    Close #1
    TickerMsg "Saved - " + Choice(cname$ = "", "CAR CLUB", cname$) + " shows on the menu"
    If town$ <> "" Then
      PField fx, fy + 5 * fh(0), fw, "Looking up " + town$ + " ...", 0
      If TownLookup(town$, la, lo, where$) Then
        Open HOME_DIR$ + "/home.dat" For Output As #1
        Print #1, Str$(la, 0, 4) + "|" + Str$(lo, 0, 4) + "|" + where$ + "|" + town$
        Close #1
        On Error Skip
        Kill HOME_DIR$ + "/weather.txt"
        PField fx, fy + 5 * fh(0), fw, "Weather is for " + where$ + " (" + Str$(la, 0, 3) + ", " + Str$(lo, 0, 3) + ")", 0
        TickerMsg "Saved - weather is now for " + where$
      Else
        PField fx, fy + 5 * fh(0), fw, "Couldn't find " + town$ + " - check the spelling (or WiFi)", 0
      EndIf
    EndIf
  EndIf
  Pause 10
Loop
Sub MapGreys
  MAP 6 = RGB(17,18,19)
  MAP 7 = RGB(20,22,24)
  MAP 8 = RGB(23,25,27)
  MAP 9 = RGB(26,28,31)
  MAP 10 = RGB(30,32,35)
  MAP 11 = RGB(33,36,39)
  MAP 12 = RGB(42,44,47)
  MAP 13 = RGB(66,70,74)
  MAP 14 = RGB(117,121,125)
End Sub
FontWidths:
Data 18
Data 4,3,5,10,8,10,8,5,4,4,6,6,3,5,3,6,7,5,7,7,7,7,7,7
Data 7,7,4,4,5,6,5,6,11,9,8,7,9,8,7,8,9,7,8,7,7,11,10,10
Data 6,11,8,8,8,9,8,12,9,8,8,5,7,5,7,8,7,6,7,6,7,7,6,6
Data 7,3,5,6,3,9,6,6,6,6,6,6,6,6,6,8,7,6,6,4,5,4,7
Data 32
Data 5,4,8,15,12,15,12,7,7,7,10,9,5,8,4,9,11,8,11,11,11,11,11,11
Data 11,11,5,5,7,9,7,9,17,13,11,11,13,11,11,12,14,10,12,11,10,16,14,14
Data 9,16,11,12,12,13,12,19,13,11,12,7,10,7,10,11,10,9,11,9,11,10,9,10
Data 10,5,7,10,5,14,9,9,10,9,9,9,8,9,9,12,11,9,10,7,8,7,11
Sub CoreInit
  On Error Skip
  Option Web Messages Off
  On Error Skip
  Drive "B:"
  On Error Skip
  Chdir HOME_DIR$
  MODE 3
  CLS
  W = MM.HRES
  H = MM.VRES
  SetPalette
  ReadWidths
  ProbeInputs
  nb = 0
  focus = 0
  hasBar = 0
  kbRow = -1
  barX = W \ 40
End Sub
Sub SetPalette
  MAP 0 = RGB(0,0,0)
  MAP 1 = RGB(67,160,71)
  MAP 2 = RGB(46,125,50)
  MAP 3 = RGB(226,75,74)
  MAP 4 = RGB(168,40,40)
  MAP 5 = RGB(255,176,0)
  MAP 15 = RGB(232,234,237)
  MapGreys
  MAP SET
  C_BLACK = MAP(0)
  C_GRN_TOP = MAP(1)
  C_GRN_BASE = MAP(2)
  C_RED_TOP = MAP(3)
  C_RED_BASE = MAP(4)
  C_AMBER = MAP(5)
  C_BAR = MAP(6)
  C_PAGE = MAP(10)
  C_FACE = MAP(14)
  C_DIM = MAP(13)
  C_INK = MAP(15)
End Sub
Sub ReadWidths
  Local integer f, i
  Restore FontWidths
  For f = 0 To 1
    Read fh(f)
    For i = 0 To 94
      Read adv(f, i)
    Next
  Next
  fText = F_TEXT
  fTitle = F_TITLE
  If forceBuiltinFont = 0 Then
    On Error Skip
    Font F_TEXT
    If MM.Errno = 0 Then
      On Error Skip
      Font F_TITLE
    EndIf
  EndIf
  If forceBuiltinFont Or MM.Errno Then
    fText = 1
    fTitle = 1
    Font 1
    fh(0) = MM.Info(FONTHEIGHT)
    fh(1) = MM.Info(FONTHEIGHT)
    For f = 0 To 1
      For i = 0 To 94
        adv(f, i) = MM.Info(FONTWIDTH)
      Next
    Next
  EndIf
  Font 1
End Sub
Sub ProbeInputs
  Local integer v
  hasTouch = 0
  hasMouse = 0
  On Error Skip
  v = Touch(X)
  If MM.Errno = 0 Then hasTouch = 1
  nm = 0
  For v = 1 To 4
    If MM.Info(USB v) = 2 And nm < 4 Then
      mch(nm) = v
      px(v) = Device(MOUSE v, X)
      py(v) = Device(MOUSE v, Y)
      pl(v) = Device(MOUSE v, L)
      nm = nm + 1
    EndIf
  Next
  If nm > 0 Then
    hasMouse = 1
    ach = mch(0)
  EndIf
End Sub
Sub StartCursor
  If hasMouse = 0 Then Exit Sub
  ReadMouse
  curX = gmx
  curY = gmy
  GUI Cursor On 0, curX, curY, C_INK
  dragY = -1
  On Error Skip
  lastWheel = Device(MOUSE ach, W)
  On Error Skip
  GUI Cursor Load CURSOR_FILE$
End Sub
Sub ReadMouse
  Local integer i, c, x, y, l
  For i = 0 To nm - 1
    c = mch(i)
    x = Device(MOUSE c, X)
    y = Device(MOUSE c, Y)
    l = Device(MOUSE c, L)
    If x <> px(c) Or y <> py(c) Or l <> pl(c) Then
      ach = c
      px(c) = x
      py(c) = y
      pl(c) = l
    EndIf
  Next
  gmx = px(ach)
  gmy = py(ach)
  gml = pl(ach)
End Sub
Function CurOver(x As integer, y As integer, w As integer, h As integer) As integer
  If hasMouse = 0 Then Exit Function
  CurOver = (curX + 20 >= x And curX <= x + w And curY + 20 >= y And curY <= y + h)
End Function
Function ListDelta(x As integer, y As integer, wd As integer, ht As integer, rh As integer) As integer
  Local integer wv, d, n
  If hasMouse = 0 Then Exit Function
  wv = lastWheel
  On Error Skip
  wv = Device(MOUSE ach, W)
  If wv <> lastWheel Then
    d = (lastWheel - wv) * 3
    lastWheel = wv
  EndIf
  If gml <> 0 And gmx >= x And gmx < x + wd And gmy >= y And gmy < y + ht Then
    If dragY < 0 Then
      dragY = gmy
    Else
      n = (dragY - gmy) \ rh
      If n <> 0 Then
        d = d + n
        dragY = dragY - n * rh
      EndIf
    EndIf
  Else
    dragY = -1
  EndIf
  ListDelta = d
End Function
Function ListNav(x As integer, y As integer, w As integer, rh As integer, rows As integer, n As integer, top As integer) As integer
  Local integer d, r, k
  lsOn = 1
  d = ListDelta(x, y, w, rows * rh + 6, rh)
  If d <> 0 And n > rows Then
    r = Max(0, Min(n - rows, top + d))
    If r <> top Then
      top = r
      ListNav = 1
    EndIf
  EndIf
  k = lsKey
  lsKey = 0
  If k = 0 Or n = 0 Then Exit Function
  If k = 13 Then
    If kbRow >= 0 And kbRow < n Then ListNav = 3
    Exit Function
  EndIf
  r = kbRow
  If r < 0 Then r = top - Choice(k = 129, 1, 0)
  Select Case k
    Case 128
      r = r - 1
    Case 129
      r = r + 1
    Case 136
      r = r - rows
    Case 137
      r = r + rows
  End Select
  kbRow = Max(0, Min(n - 1, r))
  If kbRow < top Then top = kbRow
  If kbRow >= top + rows Then top = kbRow - rows + 1
  ListNav = 2
End Function
Sub CurHide
  If hasMouse Then GUI Cursor Hide
End Sub
Sub CurShow
  If hasMouse Then GUI Cursor Show
End Sub
Sub HelpFor(topic$, back$)
  Open HOME_DIR$ + "/help.tmp" For Output As #4
  Print #4, topic$ + "|" + back$
  Close #4
  GoPage "help.bas"
End Sub
Sub GoPage(f$)
  If hasMouse Then GUI Cursor Off
  If Instr(f$, ":") = 0 Then
    Run HOME_DIR$ + "/" + f$
  Else
    Run f$
  EndIf
End Sub
Function PWidth(s$, f As integer) As integer
  Local integer i, t, c
  For i = 1 To Len(s$)
    c = Asc(Mid$(Choice(f = 1, UCase$(s$), s$), i, 1)) - 32
    If c >= 0 And c <= 94 Then t = t + adv(f, c)
  Next
  PWidth = t
End Function
Sub PText(x As integer, y As integer, s$, al$, f As integer, c As integer)
  Local integer i, p, fn, a
  Local string t$
  t$ = Choice(f = 1, UCase$(s$), s$)
  fn = Choice(f = 1, fTitle, fText)
  p = x
  If al$ = "C" Then p = x - PWidth(t$, f) \ 2
  If al$ = "R" Then p = x - PWidth(t$, f)
  For i = 1 To Len(t$)
    a = Asc(Mid$(t$, i, 1)) - 32
    If a >= 0 And a <= 94 Then
      Text p, y - fh(f) \ 2, Mid$(t$, i, 1), "LT", fn, 1, c, -1
      p = p + adv(f, a)
    EndIf
  Next
End Sub
Sub PField(x As integer, y As integer, w As integer, s$, f As integer)
  CurHide
  Box x, y - fh(f) \ 2, w, fh(f), 1, C_PAGE, C_PAGE
  PText x, y, s$, "L", f, C_INK
  CurShow
End Sub
Sub DrawPage(title$)
  DrawPageOn title$, BG_FILE$
End Sub
Sub DrawPageOn(title$, bg$)
  CurHide
  Box 0, 0, W, H, 1, C_PAGE, C_PAGE
  On Error Skip
  Load Bmp bg$, 0, 0
  If title$ <> "" Then
    If hasBar Then
      PText W - W \ 40 + 1, H \ 16 + 1, title$, "R", 1, C_BLACK
      PText W - W \ 40, H \ 16, title$, "R", 1, C_INK
    Else
      PText W \ 2 + 1, H \ 16 + 1, title$, "C", 1, C_BLACK
      PText W \ 2, H \ 16, title$, "C", 1, C_INK
    EndIf
  EndIf
  CurShow
End Sub
Function AddBtn(t$, x As integer, y As integer, w As integer, h As integer, red As integer) As integer
  lbl$(nb) = t$
  mitem$(nb) = ""
  bstyle(nb) = 0
  bx(nb) = x
  by(nb) = y
  bw(nb) = w
  bh(nb) = h
  If red Then
    colA(nb) = C_RED_TOP
    colB(nb) = C_RED_BASE
  Else
    colA(nb) = C_GRN_TOP
    colB(nb) = C_GRN_BASE
  EndIf
  AddBtn = nb
  nb = nb + 1
End Function
Sub DrawAllBtns
  Local integer i
  For i = 0 To nb - 1
    DrawBtn i, (i = focus)
  Next
End Sub
Sub DrawBtn(i As integer, st As integer)
  Local integer x, y, w, h, r, top, bot, edge, nudge
  If bstyle(i) = 4 Then Exit Sub
  If bstyle(i) = 3 Then
    DrawArt i, st
    Exit Sub
  EndIf
  If bstyle(i) > 0 Then
    DrawPlate i, st
    Exit Sub
  EndIf
  x = bx(i)
  y = by(i)
  w = bw(i)
  h = bh(i)
  r = h \ 4
  If st = 2 Then
    top = colB(i)
    bot = colA(i)
    nudge = 1
  Else
    top = colA(i)
    bot = colB(i)
    nudge = 0
  EndIf
  If st = 0 Then
    edge = C_BLACK
  Else
    edge = C_INK
  EndIf
  CurHide
  RBox x, y, w, h, r, edge, bot
  RBox x + 3, y + 3, w - 6, h \ 2 - 2, r - 2, top, top
  If st <> 0 Then RBox x + 1, y + 1, w - 2, h - 2, r, edge
  PText x + w \ 2 + 1 + nudge, y + h \ 2 + 1 + nudge, lbl$(i), "C", 0, C_BLACK
  PText x + w \ 2 + nudge, y + h \ 2 + nudge, lbl$(i), "C", 0, C_INK
  CurShow
End Sub
Sub DrawPlate(i As integer, st As integer)
  Local integer x, y, w, h, cx
  x = bx(i)
  y = by(i)
  w = bw(i)
  h = bh(i)
  CurHide
  Blit Write 10 + i, x - 2, y - 2
  If st = 2 Then RBox x + 2, y + 2, w - 4, h - 4, 3, C_GRN_TOP, C_GRN_BASE
  If st <> 0 Then
    RBox x - 2, y - 2, w + 4, h + 4, 5, C_AMBER
    RBox x - 1, y - 1, w + 2, h + 2, 4, C_AMBER
  EndIf
  cx = x + w \ 2 + Choice(bstyle(i) = 1, 6, -6)
  PText cx + 1, y + h \ 2 + 1, lbl$(i), "C", 0, C_BLACK
  PText cx, y + h \ 2, lbl$(i), "C", 0, C_INK
  CurShow
End Sub
Function HitTest(x As integer, y As integer) As integer
  Local integer i
  HitTest = -1
  For i = 0 To nb - 1
    If x >= bx(i) And x < bx(i) + bw(i) And y >= by(i) And y < by(i) + bh(i) Then
      HitTest = i
      Exit Function
    EndIf
  Next
End Function
Sub SetFocus(n As integer)
  Local integer old
  old = focus
  focus = n
  If old <> n Then DrawBtn old, 0
  DrawBtn n, 1
End Sub
Sub MoveFocus(dx As integer, dy As integer)
  Local integer i, best, bestScore, ddx, ddy, along, across, score
  best = -1
  bestScore = 999999
  For i = 0 To nb - 1
    If i <> focus Then
      ddx = (bx(i) + bw(i) \ 2) - (bx(focus) + bw(focus) \ 2)
      ddy = (by(i) + bh(i) \ 2) - (by(focus) + bh(focus) \ 2)
      along = ddx * dx + ddy * dy
      across = Abs(ddx * dy) + Abs(ddy * dx)
      If along > 0 Then
        score = along + across * 2
        If score < bestScore Then
          best = i
          bestScore = score
        EndIf
      EndIf
    EndIf
  Next
  If best >= 0 Then SetFocus best
End Sub
Sub PressBtn(i As integer)
  DrawBtn i, 2
  Pause 150
  DrawBtn i, 1
End Sub
Function ClickAt() As integer
  Local integer tx
  If hasTouch Then
    tx = Touch(X)
    If tx >= 0 Then
      clickX = tx
      clickY = Touch(Y)
      Do While Touch(X) >= 0
        Pause 10
      Loop
      ClickAt = 1
      Exit Function
    EndIf
  EndIf
  If hasMouse Then
    ReadMouse
    If gmx <> curX Or gmy <> curY Then
      curX = gmx
      curY = gmy
      GUI Cursor curX, curY
    EndIf
    If gml <> 0 And prevML = 0 Then
      clickX = gmx
      clickY = gmy
      ClickAt = 1
    EndIf
    prevML = gml
  EndIf
End Function
Function PollInput() As integer
  Local string k$
  Local integer j
  PollInput = -1
  TickerTick
  k$ = Inkey$
  If k$ = Chr$(27) Then
    PollInput = -2
    Exit Function
  EndIf
  If lsOn And k$ <> "" Then
    Select Case Asc(k$)
      Case 128, 129, 136, 137
        lsKey = Asc(k$)
        Exit Function
      Case 13
        If kbRow >= 0 Then
          lsKey = 13
          Exit Function
        EndIf
    End Select
  EndIf
  If k$ <> "" And nb > 0 Then
    Select Case Asc(k$)
      Case 128
        MoveFocus 0, -1
      Case 129
        MoveFocus 0, 1
      Case 130
        MoveFocus -1, 0
      Case 131
        MoveFocus 1, 0
    End Select
  EndIf
  If (k$ = Chr$(13) Or k$ = " ") And nb > 0 Then
    PressBtn focus
    PollInput = focus
    Exit Function
  EndIf
  If pendClick Or ClickAt() Then
    pendClick = 0
    j = HitTest(clickX, clickY)
    If j >= 0 Then
      SetFocus j
      PressBtn j
      PollInput = j
    Else
      PollInput = -3
    EndIf
    Exit Function
  EndIf
  If hasMouse Then
    j = HitTest(gmx, gmy)
    If j >= 0 And j <> focus Then SetFocus j
  EndIf
End Function
Sub TextBox(x As integer, y As integer, w As integer, s$, active As integer)
  Local string t$
  Local integer h
  h = fh(0) + 6
  t$ = s$
  Do While PWidth(t$, 0) > w - 10 And Len(t$) > 0
    t$ = Mid$(t$, 2)
  Loop
  CurHide
  If active Then
    RBox x, y, w, h, 4, C_INK, C_GRN_BASE
  Else
    RBox x, y, w, h, 4, C_DIM, C_BAR
  EndIf
  PText x + 5, y + h \ 2, t$, "L", 0, C_INK
  CurShow
End Sub
Function EditText$(x As integer, y As integer, w As integer, s$)
  Local string t$, k$
  t$ = s$
  TextBox x, y, w, t$ + "_", 1
  Do
    k$ = Inkey$
    If k$ <> "" Then
      Select Case Asc(k$)
        Case 13
          Exit Do
        Case 27
          t$ = s$
          Exit Do
        Case 8, 127
          If Len(t$) > 0 Then t$ = Left$(t$, Len(t$) - 1)
        Case 32 To 126
          If Len(t$) < 79 And k$ <> "|" Then t$ = t$ + k$
      End Select
      TextBox x, y, w, t$ + "_", 1
    EndIf
    If ClickAt() Then
      pendClick = 1
      Exit Do
    EndIf
    Pause 10
  Loop
  TextBox x, y, w, t$, 0
  EditText$ = t$
End Function
Function Fld$(l$, n As integer)
  Local integer i, p, q
  p = 1
  For i = 1 To n - 1
    q = Instr(p, l$, "|")
    If q = 0 Then Exit Function
    p = q + 1
  Next
  q = Instr(p, l$, "|")
  If q = 0 Then q = Len(l$) + 1
  Fld$ = Mid$(l$, p, q - p)
End Function
Function AddMenu(t$, items$) As integer
  Local integer w, h, i
  h = fh(0) + 10
  w = PWidth(t$, 0) + 28
  i = AddBtn(t$, barX, 10, w, h, 0)
  mitem$(i) = items$
  barX = barX + w + 6
  hasBar = 1
  AddMenu = i
End Function
Function Command$(j As integer)
  If j < 0 Then Exit Function
  If mitem$(j) = "" Then
    Command$ = lbl$(j)
  Else
    Command$ = Dropdown$(j)
  EndIf
End Function
Function Dropdown$(j As integer)
  Local string item$(15), k$
  Local integer n, i, x, y, lw, lh, rowH, hover, old, hit
  Do While n < 16
    item$(n) = Fld$(mitem$(j), n + 1)
    If item$(n) = "" Then Exit Do
    n = n + 1
  Loop
  rowH = fh(0) + 8
  For i = 0 To n - 1
    lw = Max(lw, PWidth(item$(i), 0))
  Next
  lw = Max(lw + 30, bw(j))
  lh = n * rowH + 8
  x = Max(4, Min(bx(j), W - lw - 4))
  y = by(j) + bh(j) + 2
  If y + lh > H - 4 Then y = H - lh - 4
  CurHide
  Blit Read 1, x, y, lw, lh
  RBox x, y, lw, lh, 5, C_INK, C_BAR
  For i = 0 To n - 1
    PText x + 12, y + 4 + i * rowH + rowH \ 2, item$(i), "L", 0, C_INK
  Next
  CurShow
  hover = -1
  hit = -1
  Do
    k$ = Inkey$
    If k$ = Chr$(27) Then Exit Do
    If ClickAt() Then
      If clickX >= x And clickX < x + lw And clickY >= y + 4 And clickY < y + 4 + n * rowH Then hit = (clickY - y - 4) \ rowH
      Exit Do
    EndIf
    old = hover
    hover = -1
    If gmx >= x And gmx < x + lw And gmy >= y + 4 And gmy < y + 4 + n * rowH Then hover = (gmy - y - 4) \ rowH
    If hover <> old Then
      CurHide
      If old >= 0 Then
        Box x + 3, y + 4 + old * rowH, lw - 6, rowH, 1, C_BAR, C_BAR
        PText x + 12, y + 4 + old * rowH + rowH \ 2, item$(old), "L", 0, C_INK
      EndIf
      If hover >= 0 Then
        Box x + 3, y + 4 + hover * rowH, lw - 6, rowH, 1, C_GRN_BASE, C_GRN_BASE
        PText x + 12, y + 4 + hover * rowH + rowH \ 2, item$(hover), "L", 0, C_INK
      EndIf
      CurShow
    EndIf
    Pause 10
  Loop
  CurHide
  Blit Write 1, x, y
  Blit Close 1
  CurShow
  If hit >= 0 Then Dropdown$ = item$(hit)
End Function
Sub TickerAt(x As integer, y As integer, w As integer)
  tkx = x
  tky = y
  tkw = w
  tkh = fh(0) + 10
  CurHide
  RBox tkx, tky, tkw, tkh, 5, C_INK, C_BAR
  CurShow
  WifiCheck
  WeatherLoad
  lastTick = Timer
End Sub
Sub WeatherLoad
  Local string l$
  Local integer p, q
  tkWx$ = ""
  On Error Skip
  Open HOME_DIR$ + "/weather.txt" For Input As #4
  If MM.Errno Then Exit Sub
  If Not Eof(#4) Then Line Input #4, l$
  Close #4
  p = Instr(l$, "|")
  If p = 0 Then Exit Sub
  q = Instr(p + 1, l$, "|")
  If q = 0 Then q = Len(l$) + 1
  On Error Skip
  If Epoch(Now) - Val(Left$(l$, p - 1)) > 10800 Then Exit Sub
  tkWx$ = Mid$(l$, p + 1, q - p - 1) + Choice(q <= Len(l$), " (" + Mid$(l$, q + 1) + ")", "")
End Sub
Sub WifiCheck
  Local string a$
  a$ = ""
  On Error Skip
  a$ = MM.Info(IP ADDRESS)
  If a$ <> "" And a$ <> "0.0.0.0" Then
    ip$ = "WiFi OK  " + a$
  Else
    ip$ = "WiFi DOWN"
  EndIf
End Sub
Sub TickerMsg(s$)
  tkMsg$ = Left$(s$, 100)
  tkPos = 0
End Sub
Sub TickerSeg(slot As integer, s$)
  tkSeg$(slot) = Left$(s$, 60)
End Sub
Sub TickerTick
  If tkw = 0 Or Timer - lastTick < TICK_MS Then Exit Sub
  lastTick = Timer
  DrawTicker
End Sub
Function TickAppend$(base$, add$, maxlen As integer) As string
  If Len(base$) >= maxlen Then
    TickAppend$ = base$
  ElseIf Len(base$) + Len(add$) <= maxlen Then
    TickAppend$ = base$ + add$
  Else
    TickAppend$ = base$ + Left$(add$, maxlen - Len(base$))
  EndIf
End Function
Sub DrawTicker
  Local string s$, c$
  Local integer p, i, a, hid, sg
  Const TICKER_MAX = 200
  s$ = ""
  If Not tickerRaceMode Then
    s$ = DDate$(Date$) + " " + Time$
    If tkWx$ <> "" Then s$ = TickAppend$(s$, "   |   " + tkWx$, TICKER_MAX)
    If ip$ <> "" Then s$ = TickAppend$(s$, "   |   " + ip$, TICKER_MAX)
  EndIf
  For sg = 0 To 4
    If tkSeg$(sg) <> "" Then s$ = TickAppend$(s$, Choice(s$ = "", tkSeg$(sg), "   |   " + tkSeg$(sg)), TICKER_MAX)
  Next
  If tkMsg$ <> "" Then s$ = TickAppend$(s$, Choice(s$ = "", tkMsg$, "   |   " + tkMsg$), TICKER_MAX)
  If Len(s$) < TICKER_MAX Then s$ = s$ + "   |   "
  tkPos = tkPos + 1
  If tkPos > Len(s$) Then
    tkPos = 1
    WifiCheck
    WeatherLoad
  EndIf
  hid = CurOver(tkx, tky, tkw, tkh)
  If hid Then CurHide
  p = tkx + 8
  i = tkPos
  Do
    c$ = Mid$(s$, i, 1)
    a = adv(0, Asc(c$) - 32)
    If p + a > tkx + tkw - 8 Then Exit Do
    Text p, tky + (tkh - fh(0)) \ 2, c$, "LT", fText, 1, C_INK, C_BAR
    p = p + a
    i = i + 1
    If i > Len(s$) Then i = 1
  Loop
  Box p, tky + 2, tkx + tkw - 3 - p, tkh - 4, 1, C_BAR, C_BAR
  If hid Then CurShow
End Sub
Function DDate$(d$)
  If Mid$(d$, 5, 1) = "-" Then
    DDate$ = Str$(Val(Mid$(d$, 9, 2))) + "-" + Str$(Val(Mid$(d$, 6, 2))) + "-" + Left$(d$, 4)
  ElseIf Mid$(d$, 3, 1) = "-" And Len(d$) = 10 Then
    DDate$ = Str$(Val(Left$(d$, 2))) + "-" + Str$(Val(Mid$(d$, 4, 2))) + "-" + Right$(d$, 4)
  Else
    DDate$ = d$
  EndIf
End Function
Sub DrawArt(i As integer, st As integer)
  CurHide
  Blit Write 10 + i, bx(i) - 2, by(i) - 2
  If st <> 0 Then
    RBox bx(i) - 2, by(i) - 2, bw(i) + 4, bh(i) + 4, 5, C_AMBER
    RBox bx(i) - 1, by(i) - 1, bw(i) + 2, bh(i) + 2, 4, C_AMBER
  EndIf
  If st = 2 Then RBox bx(i), by(i), bw(i), bh(i), 4, C_AMBER
  CurShow
End Sub
Function NetLine$(f$)
  NetLine$ = ""
  On Error Skip
  Open f$ For Input As #3
  If MM.Errno Then Exit Function
  If Not Eof(#3) Then Line Input #3, NetLine$
  Close #3
End Function
Function JsonNum(b() As integer, k$, from As integer) As float
  Local integer p
  p = LInStr(b(), Chr$(34) + k$ + Chr$(34) + ":", from)
  If p = 0 Then Exit Function
  JsonNum = Val(LGetStr$(b(), p + Len(k$) + 3, 12))
End Function
Function TownLookup(t$, la As float, lo As float, where$) As integer
  Local string nm$, st$, w$
  Local integer i, tries
  nm$ = " " + Trim$(t$) + " "
  For i = 1 To 8
    w$ = StateName$(i)
    If UCase$(Right$(nm$, Len(Fld$(w$, 1)) + 1)) = UCase$(Fld$(w$, 1) + " ") Then
      st$ = Fld$(w$, 1)
      nm$ = Left$(nm$, Len(nm$) - Len(Fld$(w$, 1)) - 1)
      Exit For
    ElseIf UCase$(Right$(nm$, Len(Fld$(w$, 2)) + 2)) = UCase$(" " + Fld$(w$, 2) + " ") Then
      st$ = Fld$(w$, 1)
      nm$ = Left$(nm$, Len(nm$) - Len(Fld$(w$, 2)) - 1)
      Exit For
    EndIf
  Next
  If UCase$(Left$(nm$, 4)) = " MT " Or UCase$(Left$(nm$, 4)) = " MT." Then nm$ = " Mount " + Mid$(nm$, 5)
  If UCase$(Left$(nm$, 4)) = " PT " Or UCase$(Left$(nm$, 4)) = " PT." Then nm$ = " Port " + Mid$(nm$, 5)
  nm$ = Trim$(nm$)
  For tries = 1 To 3
    If nm$ = "" Then Exit Function
    If TownAsk(nm$, st$, la, lo, where$) Then
      TownLookup = 1
      Exit Function
    EndIf
    i = Instr(nm$ + " ", " ")
    If Instr(nm$, " ") = 0 Then Exit Function
    Do While Instr(i + 1, nm$, " ")
      i = Instr(i + 1, nm$, " ")
    Loop
    nm$ = Left$(nm$, i - 1)
  Next
End Function
Function StateName$(i As integer)
  Select Case i
    Case 1
      StateName$ = "South Australia|SA"
    Case 2
      StateName$ = "Victoria|Vic"
    Case 3
      StateName$ = "New South Wales|NSW"
    Case 4
      StateName$ = "Queensland|Qld"
    Case 5
      StateName$ = "Western Australia|WA"
    Case 6
      StateName$ = "Tasmania|Tas"
    Case 7
      StateName$ = "Northern Territory|NT"
    Case 8
      StateName$ = "Australian Capital Territory|ACT"
  End Select
End Function
Function TownAsk(nm$, st$, la As float, lo As float, where$) As integer
  Local integer b(1024), p, i
  Local string req$, u$, a$
  For i = 1 To Len(nm$)
    u$ = u$ + Choice(Mid$(nm$, i, 1) = " ", "%20", Mid$(nm$, i, 1))
  Next
  req$ = "GET /v1/search?name=" + u$ + "&count=10&country=AU HTTP/1.0" + Chr$(13) + Chr$(10)
  req$ = req$ + "Host: geocoding-api.open-meteo.com" + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB Open TCP Client "geocoding-api.open-meteo.com", 80
  If MM.Errno Then Exit Function
  On Error Skip
  WEB TCP Client Request req$, b(), 8000
  On Error Skip
  WEB Close TCP Client
  p = 1
  Do
    p = LInStr(b(), Chr$(34) + "latitude" + Chr$(34), p)
    If p = 0 Then Exit Function
    a$ = JsonText$(b(), "admin1", p)
    If st$ = "" Or UCase$(a$) = UCase$(st$) Then
      la = JsonNum(b(), "latitude", p)
      lo = JsonNum(b(), "longitude", p)
      where$ = nm$ + Choice(a$ = "", "", ", " + a$)
      TownAsk = 1
      Exit Function
    EndIf
    p = p + 10
  Loop
End Function
Function JsonText$(b() As integer, k$, from As integer)
  Local integer p, q
  p = LInStr(b(), Chr$(34) + k$ + Chr$(34) + ":" + Chr$(34), from)
  If p = 0 Then Exit Function
  p = p + Len(k$) + 4
  q = LInStr(b(), Chr$(34), p)
  If q > p Then JsonText$ = LGetStr$(b(), p, Min(60, q - p))
End Function
