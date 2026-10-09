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
Const MENU_BG$ = "menu_bg.bmp"
Const LAY_MENU$ = "B:/draw/menu"
Const WX_EVERY = 180000
Const PLATE_W = 110, PLATE_H = 20, PLATE_GAP = 3, PLATE_Y0 = 216
Const LEFT_X = 190, RIGHT_X = 340
Const BOT_W = 90, BOT_H = 20, BOT_GAP = 10, BOT_X0 = 175, BOT_Y0 = 398
Dim integer clkX = 230, clkY = 150, dtX = 410, dtY = 150, fR = 39
Dim integer mtX = 182, mtY = 334, mtW = 276, mtH = 34, useLay, a
Dim integer j, i, v, dateDrawn
Dim string lastT$, clubName$, label$, wwhere$
Dim integer lastWx
Dim float wla, wlo
CoreInit
clubName$ = ClubNameFromFile$()
If MM.Info(FILESIZE LAY_MENU$ + ".lay") > 0 And MM.Info(FILESIZE LAY_MENU$ + ".bmp") > 0 Then
  DrawPageOn "", LAY_MENU$ + ".bmp"
  useLay = (LayButtons(LAY_MENU$ + ".lay") > 0)
  If Not useLay Then DrawPageOn "", MENU_BG$
Else
  DrawPageOn "", MENU_BG$
EndIf
If useLay Then
  LayPlaces
Else
  CurHide
  PText W \ 2 + 1, 27, clubName$, "C", 1, C_BLACK
  PText W \ 2, 26, clubName$, "C", 1, C_INK
  CurShow
  PlatesFromArt
EndIf
DrawAllBtns
TickerIn mtX + 4, mtY + 4, mtW - 8, mtH - 8
StartCursor
TickerMsg "Welcome to " + clubName$
lastWx = Timer - WX_EVERY
Do
  j = PollInput()
  If j >= 0 Then Activate j
  If Timer - lastWx >= WX_EVERY Then GetWx
  If Time$ <> lastT$ Then
    lastT$ = Time$
    DrawClock
    If Right$(lastT$, 5) = "00:00" Or dateDrawn = 0 Then DrawDate
  EndIf
  Pause 10
Loop
Sub PlatesFromArt
Restore MenuPlates
For i = 0 To 3
  Read label$
  v = AddPlate(label$, LEFT_X, PLATE_Y0 + i * (PLATE_H + PLATE_GAP), PLATE_W, PLATE_H, -1)
Next
For i = 0 To 3
  Read label$
  v = AddPlate(label$, RIGHT_X, PLATE_Y0 + i * (PLATE_H + PLATE_GAP), PLATE_W, PLATE_H, 1)
Next
For i = 0 To 2
  Read label$
  v = AddPlate(label$, BOT_X0 + i * (BOT_W + BOT_GAP), BOT_Y0, BOT_W, BOT_H, -1)
Next
End Sub
Sub LayPlaces
  a = LayArea("TICKER")
  If a >= 0 Then
    mtX = laX(a) : mtY = laY(a) : mtW = laW(a) : mtH = laH(a)
  Else
    mtX = 0 : mtY = H - 34 : mtW = W : mtH = 34
  EndIf
  a = LayArea("CLOCK")
  clkX = -1
  If a >= 0 Then
    clkX = laX(a) + laW(a) \ 2 : clkY = laY(a) + laH(a) \ 2
    fR = Max(20, Min(laW(a), laH(a)) \ 2 - 1)
  EndIf
  a = LayArea("DATE")
  dtX = -1
  If a >= 0 Then
    dtX = laX(a) + laW(a) \ 2 : dtY = laY(a) + laH(a) \ 2
    fR = Max(20, Min(fR, Min(laW(a), laH(a)) \ 2 - 1))
  EndIf
  a = LayArea("TITLE")
  If a >= 0 Then
    CurHide
    PText laX(a) + laW(a) \ 2 + 1, laY(a) + laH(a) \ 2 + 1, clubName$, "C", 1, C_BLACK
    PText laX(a) + laW(a) \ 2, laY(a) + laH(a) \ 2, clubName$, "C", 1, C_INK
    CurShow
  EndIf
End Sub
MenuPlates:
Data "MEMBERS", "EVENTS", "PHOTOS", "EXPORT/IMPORT"
Data "EMAIL/TXT", "FINANCIAL", "GAMES", "GPS"
Data "ADMIN", "QUIT", "MUSIC"
Function ClubNameFromFile$()
  Local string l$
  ClubNameFromFile$ = "CAR CLUB"
  On Error Skip
  Open "clubname.txt" For Input As #1
  If MM.Errno Then Exit Function
  If Not Eof(#1) Then Line Input #1, l$
  Close #1
  If l$ <> "" Then ClubNameFromFile$ = l$
End Function
Sub DrawClock
  Local integer hh, mm, ss, k, r1, hid
  Local float a
  If clkX < 0 Then Exit Sub
  hh = Val(Left$(lastT$, 2))
  mm = Val(Mid$(lastT$, 4, 2))
  ss = Val(Right$(lastT$, 2))
  hid = CurOver(clkX - fR, clkY - fR, 2 * fR, 2 * fR)
  If hid Then CurHide
  Circle clkX, clkY, fR, 1, 1, C_FACE, C_FACE
  For k = 0 To 11
    a = Rad(k * 30)
    r1 = Choice(k Mod 3 = 0, fR - 7, fR - 4)
    Line clkX + r1 * Sin(a), clkY - r1 * Cos(a), clkX + (fR - 1) * Sin(a), clkY - (fR - 1) * Cos(a), 1, C_BAR
  Next
  PText clkX, clkY - fR + 14, "XII", "C", 0, C_BAR
  PText clkX + fR - 13, clkY, "III", "C", 0, C_BAR
  PText clkX, clkY + fR - 13, "VI", "C", 0, C_BAR
  PText clkX - fR + 13, clkY, "IX", "C", 0, C_BAR
  a = ((hh Mod 12) + mm / 60) * 30
  Hand a, fR - 20, 3, C_BAR
  a = (mm + ss / 60) * 6
  Hand a, fR - 10, 2, C_BAR
  a = ss * 6
  Hand a, fR - 6, 1, C_RED_TOP
  Circle clkX, clkY, 3, 1, 1, C_BAR, C_BAR
  If hid Then CurShow
End Sub
Sub Hand(deg As float, length As integer, thick As integer, c As integer)
  Local float a
  a = Rad(deg)
  Line clkX, clkY, clkX + length * Sin(a), clkY - length * Cos(a), thick, c
End Sub
Sub DrawDate
  Local string dn$
  On Error Skip
  dn$ = UCase$(Left$(Day$(Date$), 3))
  dateDrawn = 1
  If dtX < 0 Then Exit Sub
  CurHide
  Circle dtX, dtY, fR, 1, 1, C_FACE, C_FACE
  CurShow
  PText dtX, dtY - 18, dn$, "C", 0, C_BAR
  PText dtX, dtY + 2, Str$(Val(Left$(Date$, 2))) + "-" + Str$(Val(Mid$(Date$, 4, 2))), "C", 1, C_BAR
  PText dtX, dtY + 22, Right$(Date$, 4), "C", 0, C_BAR
  dateDrawn = 1
End Sub
Sub GetWx
  Local string w$
  lastWx = Timer
  wla = 0
  wlo = 0
  wwhere$ = ""
  w$ = WeatherNow$(wla, wlo, wwhere$)
  If w$ <> "" Then
    WeatherLoad
  EndIf
End Sub
Sub Activate(i As integer)
  Select Case lbl$(i)
    Case "QUIT"
      If hasMouse Then GUI Cursor Off
      MAP RESET
      MODE 1
      Font 1
      CLS
      Print "Menu closed. Type RUN "; Chr$(34); "B:/club/club.bas"; Chr$(34); " to start it again."
      End
    Case "MEMBERS"
      GoPage "members.bas"
    Case "EVENTS"
      GoPage "events.bas"
    Case "FINANCIAL"
      GoPage "financial.bas"
    Case "PHOTOS"
      GoPage "photos.bas"
    Case "MUSIC"
      GoPage "music.bas"
    Case "GAMES"
      GoPage "games.bas"
    Case "ADMIN"
      GoPage "admin.bas"
    Case "EXPORT/IMPORT"
      GoPage "export.bas"
    Case "EMAIL/TXT"
      GoPage "message.bas"
    Case "GPS"
      GoPage "gps.bas"
    Case Else
      TickerMsg lbl$(i) + " - page not ported yet"
  End Select
End Sub
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
Function AddPlate(t$, x As integer, y As integer, w As integer, h As integer, nub As integer) As integer
  Local integer i
  i = AddBtn(t$, x, y, w, h, 0)
  bstyle(i) = Choice(nub > 0, 2, 1)
  CurHide
  Blit Read 10 + i, x - 2, y - 2, w + 4, h + 4
  CurShow
  AddPlate = i
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
Sub TickerIn(x As integer, y As integer, w As integer, h As integer)
  tkx = x - 3
  tky = y - 2
  tkw = w + 6
  tkh = h + 4
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
Function LayButtons(f$) As integer
  Local string l$, k$
  Local integer x, y, wd, ht, n
  nla = 0
  On Error Skip
  Open f$ For Input As #1
  If MM.Errno Then Exit Function
  Do While Not Eof(#1)
    Line Input #1, l$
    k$ = UCase$(Field$(l$, 1, ","))
    x = Val(Field$(l$, 3, ","))
    y = Val(Field$(l$, 4, ","))
    wd = Val(Field$(l$, 5, ","))
    ht = Val(Field$(l$, 6, ","))
    If k$ = "BUTTON" And nb < NBMAX And wd > 4 And ht > 4 Then
      x = AddArt(UCase$(Field$(l$, 2, ",")), x, y, wd, ht)
      n = n + 1
    ElseIf k$ = "AREA" And nla < MAXLA Then
      laN$(nla) = UCase$(Field$(l$, 2, ","))
      laX(nla) = x
      laY(nla) = y
      laW(nla) = wd
      laH(nla) = ht
      nla = nla + 1
    EndIf
  Loop
  Close #1
  LayButtons = n
End Function
Function LayArea(n$) As integer
  Local integer i
  LayArea = -1
  For i = 0 To nla - 1
    If laN$(i) = n$ Then LayArea = i
  Next
End Function
Function AddArt(t$, x As integer, y As integer, wd As integer, ht As integer) As integer
  Local integer i
  i = AddBtn(t$, Max(2, x), Max(2, y), Min(wd, W - 3 - Max(2, x)), Min(ht, H - 3 - Max(2, y)), 0)
  bstyle(i) = 3
  CurHide
  Blit Read 10 + i, bx(i) - 2, by(i) - 2, bw(i) + 4, bh(i) + 4
  CurShow
  AddArt = i
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
Function WeatherNow$(la As float, lo As float, where$)
  Local integer wb(1024), p, code
  Local float temp, wind
  Local string req$, l$, d$
  If la = 0 And lo = 0 Then
    l$ = NetLine$(HOME_DIR$ + "/lastfix.dat")
    la = Val(Fld$(l$, 1))
    lo = Val(Fld$(l$, 2))
    If la <> 0 Or lo <> 0 Then where$ = "last GPS fix"
  EndIf
  If la = 0 And lo = 0 Then
    l$ = NetLine$(HOME_DIR$ + "/home.dat")
    la = Val(Fld$(l$, 1))
    lo = Val(Fld$(l$, 2))
    If la <> 0 Or lo <> 0 Then where$ = Fld$(l$, 3)
  EndIf
  If la = 0 And lo = 0 Then IpLocate la, lo, where$
  If la = 0 And lo = 0 Then Exit Function
  req$ = "GET /v1/forecast?latitude=" + Str$(la, 0, 4) + "&longitude=" + Str$(lo, 0, 4)
  req$ = req$ + "&current_weather=true HTTP/1.0" + Chr$(13) + Chr$(10)
  req$ = req$ + "Host: api.open-meteo.com" + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB Open TCP Client "api.open-meteo.com", 80
  If MM.Errno Then Exit Function
  On Error Skip
  WEB TCP Client Request req$, wb(), 8000
  On Error Skip
  WEB Close TCP Client
  p = LInStr(wb(), Chr$(34) + "current_weather" + Chr$(34) + ":{")
  If p = 0 Then Exit Function
  temp = JsonNum(wb(), "temperature", p)
  wind = JsonNum(wb(), "windspeed", p)
  code = JsonNum(wb(), "weathercode", p)
  d$ = WeatherText$(code) + ", " + Str$(temp, 0, 1) + " C, wind " + Str$(wind, 0, 0) + " km/h"
  On Error Skip
  Open HOME_DIR$ + "/weather.txt" For Output As #3
  If MM.Errno = 0 Then
    Print #3, Str$(Epoch(Now)) + "|" + d$ + "|" + where$
    Close #3
  EndIf
  WeatherNow$ = d$
End Function
Sub IpLocate(la As float, lo As float, where$)
  Local integer b(512), p, q
  Local string req$, city$
  req$ = "GET /json/?fields=status,city,lat,lon HTTP/1.0" + Chr$(13) + Chr$(10)
  req$ = req$ + "Host: ip-api.com" + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB Open TCP Client "ip-api.com", 80
  If MM.Errno Then Exit Sub
  On Error Skip
  WEB TCP Client Request req$, b(), 8000
  On Error Skip
  WEB Close TCP Client
  If LInStr(b(), Chr$(34) + "success" + Chr$(34)) = 0 Then Exit Sub
  la = JsonNum(b(), "lat", 1)
  lo = JsonNum(b(), "lon", 1)
  p = LInStr(b(), Chr$(34) + "city" + Chr$(34) + ":" + Chr$(34))
  If p Then
    q = LInStr(b(), Chr$(34), p + 8)
    If q > p + 8 Then city$ = LGetStr$(b(), p + 8, Min(40, q - p - 8))
  EndIf
  where$ = "near " + Choice(city$ = "", "here", city$)
End Sub
Function JsonNum(b() As integer, k$, from As integer) As float
  Local integer p
  p = LInStr(b(), Chr$(34) + k$ + Chr$(34) + ":", from)
  If p = 0 Then Exit Function
  JsonNum = Val(LGetStr$(b(), p + Len(k$) + 3, 12))
End Function
Function WeatherText$(c As integer)
  Select Case c
    Case 0
      WeatherText$ = "Clear sky"
    Case 1
      WeatherText$ = "Mainly clear"
    Case 2
      WeatherText$ = "Partly cloudy"
    Case 3
      WeatherText$ = "Overcast"
    Case 45, 48
      WeatherText$ = "Fog"
    Case 51, 53, 55
      WeatherText$ = "Drizzle"
    Case 61
      WeatherText$ = "Slight rain"
    Case 63
      WeatherText$ = "Rain"
    Case 65
      WeatherText$ = "Heavy rain"
    Case 71, 73, 75, 77
      WeatherText$ = "Snow"
    Case 80, 81
      WeatherText$ = "Rain showers"
    Case 82
      WeatherText$ = "Violent showers"
    Case 85, 86
      WeatherText$ = "Snow showers"
    Case 95, 96, 99
      WeatherText$ = "Thunderstorm"
    Case Else
      WeatherText$ = "Weather code " + Str$(c)
  End Select
End Function
