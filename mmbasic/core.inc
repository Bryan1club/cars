' --- core.inc: shared by every page ---------------------------------
' Joined onto each page by mmbasic/build.py. A page calls CoreInit,
' adds its buttons with AddBtn, draws with DrawPage/PText, and loops on
' PollInput(), which returns the button pressed (-1 none, -2 Esc).
'
' Colours: the 16 MODE 3 slots are set with MAP (fixed in board 2's
' firmware 2026-09-24): club colours in 0-5 and 15, the backgrounds'
' panel greys in 6-14 (see SetPalette and generated.inc's MapGreys).
Const USE_MAP = 1
Const F_TEXT = 9, F_TITLE = 10
Const NBMAX = 16
Const BG_FILE$ = "page_bg_640.bmp"
Const CURSOR_FILE$ = "arrow.spr"
' every page, data file and the pointer live here on the SD card
Const HOME_DIR$ = "B:/club"

Dim integer C_BLACK, C_GRN_TOP, C_GRN_BASE, C_RED_TOP, C_RED_BASE
Dim integer C_BAR, C_PAGE, C_INK, C_DIM, C_AMBER, C_FACE
Dim string lbl$(NBMAX - 1)
Dim integer bx(NBMAX - 1), by(NBMAX - 1), bw(NBMAX - 1), bh(NBMAX - 1)
Dim integer colA(NBMAX - 1), colB(NBMAX - 1)
' 0 = a drawn button; 1/2 = a plate already in the background art, nub
' on the left/right (plate buttons keep a copy of their patch of screen,
' BLIT buffer 10 + number)
Dim integer bstyle(NBMAX - 1)
' the named AREAs of a draw.bas layout: TICKER, CLOCK, ...
Const MAXLA = 8
Dim string laN$(MAXLA - 1)
Dim integer laX(MAXLA - 1), laY(MAXLA - 1), laW(MAXLA - 1), laH(MAXLA - 1), nla
Dim integer nb, focus, W, H
' where the last click/touch that missed every button landed (PollInput -3)
Dim integer clickX, clickY
' top menu bar: each bar heading is a button whose mitem$ lists its
' dropdown commands ("A|B|C"); "" for ordinary buttons. hasBar moves the
' page title to the top right, out of the bar's way.
Dim string mitem$(NBMAX - 1)
Dim integer hasBar, barX
' the scrolling ticker (TickerAt places it; PollInput keeps it moving)
Const TICK_MS = 150
Dim integer tkx, tky, tkw, tkh, tkPos, lastTick
' set by a page/game, never by core.inc itself: when true, DrawTicker
' drops the date/time/weather/wifi it normally opens with
Dim integer tickerRaceMode
Dim string ip$, tkMsg$, tkWx$
' extra live segments (TickerSeg) alongside the one plain TickerMsg --
' each a page's own slot, refreshed independently, so a live screen (the
' racing garage: entrants, event, running order...) can keep them all
' flowing through the one ticker instead of overwriting each other
Dim string tkSeg$(4)
Dim integer hasTouch, hasMouse, gmx, gmy, gml, prevML, curX, curY
' list scrolling: the wheel's last count, and where a drag started (-1 none)
Dim integer lastWheel, dragY
' keyboard on a list: the row the arrows are on (-1 none yet), a list key
' waiting for ListNav, and whether this page has a list
Dim integer kbRow, lsKey, lsOn
' a click that finished typing in a text box, still to be acted on
Dim integer pendClick
' every USB channel that reports a mouse, and each one's last reading
Dim integer nm, ach, mch(3), px(4), py(4), pl(4)
' per-character advance widths for fonts #9 (0) and #10 (1)
Dim integer adv(1, 94), fh(1)
' the fonts PText uses: the club's #9 / #10 from the library, or the
' built-in font 1 on a board without them (a game run on its own)
Dim integer fText, fTitle
' set by a caller BEFORE calling CoreInit to skip the club's #9/#10
' entirely and always use the built-in font 1 -- for a page/game that's
' decided the custom fonts aren't right for it (racing.bas: members found
' the italic font hard to read on the race/garage screens)
Dim integer forceBuiltinFont

Sub CoreInit
  ' no "tcp address ... / Connecting to ... / Connected" lines printed over
  ' the page whenever a page talks to the internet (weather, email). The
  ' firmware turns them back on at every RUN, so every page says it.
  On Error Skip
  Option Web Messages Off
  ' work in the club folder, so data files can be named without a path
  ' (a game run on a board without the club carries on where it is)
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
  ' slot 0 black and 15 near-white are also the mouse pointer's colours
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
    ' no club fonts in the library: the built-in font 1, every letter the
    ' same width. Both custom fonts must load, or PText later crashes
    ' with "Invalid font #n" on whichever one is missing -- probe both,
    ' not just F_TEXT (a board can have one loaded without the other)
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
  ' small arrow from arrow.spr; keeps the built-in one if it's missing
  On Error Skip
  GUI Cursor Load CURSOR_FILE$
End Sub

' reads every mouse; whichever one changed last becomes the active one
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

' true when the pointer is over (or next to) the box x,y,w,h. Things that
' redraw on a timer (ticker, clock) hide the pointer only then: hiding and
' showing it on every redraw made it flicker all over the screen.
Function CurOver(x As integer, y As integer, w As integer, h As integer) As integer
  If hasMouse = 0 Then Exit Function
  CurOver = (curX + 20 >= x And curX <= x + w And curY + 20 >= y And curY <= y + h)
End Function

' rows to scroll a list in the box x,y,w,h (rows rh high): the mouse wheel
' (3 rows a notch), or holding the button down on the list and dragging it
' up or down, like a phone. Call after PollInput, which reads the mouse.
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

' a page's list, driven by the wheel, dragging, and the keyboard. The
' list is rows rows of rh at x,y (w wide), n items, top = first shown
' (changed here). Returns 0 nothing, 1 scrolled (redraw it), 2 the arrow
' keys moved to row kbRow (redraw, then act as if it was clicked), 3 Enter
' on row kbRow (act as if it was clicked again). Call after PollInput.
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

' the firmware's pointer saves what's under it, so hide it while drawing
Sub CurHide
  If hasMouse Then GUI Cursor Hide
End Sub

Sub CurShow
  If hasMouse Then GUI Cursor Show
End Sub

' the HELP page for topic$ (a [section] of help.txt); BACK there comes back
' to back$
Sub HelpFor(topic$, back$)
  Open HOME_DIR$ + "/help.tmp" For Output As #4
  Print #4, topic$ + "|" + back$
  Close #4
  GoPage "help.bas"
End Sub

' hand over to another page's program; the pointer is switched off
' first because a new program can't see the old one's cursor state
Sub GoPage(f$)
  If hasMouse Then GUI Cursor Off
  ' pages live in HOME_DIR$; a game run from B:/Games mustn't look
  ' for "club.bas" in the Games folder
  If Instr(f$, ":") = 0 Then
    Run HOME_DIR$ + "/" + f$
  Else
    Run f$
  EndIf
End Sub

' --- text -----------------------------------------------------------
Function PWidth(s$, f As integer) As integer
  Local integer i, t, c
  For i = 1 To Len(s$)
    c = Asc(Mid$(Choice(f = 1, UCase$(s$), s$), i, 1)) - 32
    If c >= 0 And c <= 94 Then t = t + adv(f, c)
  Next
  PWidth = t
End Function

' proportional text: al$ is "L", "C" or "R" around x, y is the middle
' of the line, f is 0 for font #9 or 1 for font #10. Transparent, so
' whatever is behind shows between the letters.
Sub PText(x As integer, y As integer, s$, al$, f As integer, c As integer)
  Local integer i, p, fn, a
  Local string t$
  ' font #10 (f = 1, titles) only has capitals: lowercase would draw as
  ' solid blocks, so titles are always shown in capitals
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

' a line of text in a box that's cleared first, for values that change
Sub PField(x As integer, y As integer, w As integer, s$, f As integer)
  CurHide
  Box x, y - fh(f) \ 2, w, fh(f), 1, C_PAGE, C_PAGE
  PText x, y, s$, "L", f, C_INK
  CurShow
End Sub

' --- page frame -----------------------------------------------------
Sub DrawPage(title$)
  DrawPageOn title$, BG_FILE$
End Sub

' a page on a given background picture (the menu has its own dash)
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

' --- buttons --------------------------------------------------------
' red = 1 for QUIT-style buttons. Returns the button's number.
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

' a button on a switch plate that's already in the background: keeps a
' copy of the plate so it can be put back under a new label or highlight.
' Call after the background is drawn. nub is the side the plate's toggle
' nub is on (-1 left, 1 right), so the label centres beside it.
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

' st: 0 = normal, 1 = selected, 2 = pressed
Sub DrawBtn(i As integer, st As integer)
  Local integer x, y, w, h, r, top, bot, edge, nudge
  ' bstyle 4: this button's own look is drawn elsewhere (e.g. racing.bas's
  ' garage drawers via DrawDrawer) -- the generic hover/press redraw here
  ' would just paint a plain green box over that custom art
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
  ' deeper shade for the whole body, lighter shade for the top band
  RBox x, y, w, h, r, edge, bot
  RBox x + 3, y + 3, w - 6, h \ 2 - 2, r - 2, top, top
  If st <> 0 Then RBox x + 1, y + 1, w - 2, h - 2, r, edge
  ' drop shadow keeps the label readable across both shades
  PText x + w \ 2 + 1 + nudge, y + h \ 2 + 1 + nudge, lbl$(i), "C", 0, C_BLACK
  PText x + w \ 2 + nudge, y + h \ 2 + nudge, lbl$(i), "C", 0, C_INK
  CurShow
End Sub

' a plate button: the plate from the background, its label, and for the
' selected one an amber frame; pressed lights the plate's face green
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
  ' centred in the part of the plate beside its nub
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


' the nearest button in the arrow's direction gets the highlight
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

' the press animation every activated button gets
Sub PressBtn(i As integer)
  DrawBtn i, 2
  Pause 150
  DrawBtn i, 1
End Sub

' true when a click or tap has just happened, at clickX, clickY. Also
' keeps the pointer following the mouse. Everything that waits for a
' click (buttons, dropdowns, text boxes) goes through this.
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

' one pass over the keyboard, touch and mouse: the button pressed (after
' its press animation), -2 for Esc, -3 for a click that missed every
' button (at clickX, clickY), or -1 for nothing. Enter presses the
' highlighted button; the mouse highlights whatever it's over.
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
  ' on a page with a list, Up/Down/PgUp/PgDn (and Enter once the arrows
  ' have been used) are the list's -- ListNav picks them up
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
  ' arrow keys move the highlight to the nearest button that way
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

' --- text boxes -----------------------------------------------------
' a one-line box, text left-aligned; shows the end of s$ if it's too long
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

' edit s$ in the box at x,y with the keyboard. Enter or a click keeps the
' new text, Esc puts the old text back.
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
      ' the click that ends the typing also counts for what was clicked
      ' (SAVE straight after typing, the next box...): PollInput acts on it
      pendClick = 1
      Exit Do
    EndIf
    Pause 10
  Loop
  TextBox x, y, w, t$, 0
  EditText$ = t$
End Function

' one "|"-separated field (1-based) of a data file record
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

' s$ cut short (with "..") so it fits in w pixels of font #9
Function Fit$(s$, w As integer)
  Local string t$
  t$ = s$
  If PWidth(t$, 0) <= w Then
    Fit$ = t$
    Exit Function
  EndIf
  Do While Len(t$) > 0 And PWidth(t$ + "..", 0) > w
    t$ = Left$(t$, Len(t$) - 1)
  Loop
  Fit$ = t$ + ".."
End Function

' --- top menu bar ---------------------------------------------------
' adds a heading to the bar along the top; items$ is its dropdown
' ("NEW|SAVE|DELETE") or "" for a heading that is a command itself
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

' what a PollInput result means as a command: a dropdown heading opens
' its list and gives the item picked ("" if closed), anything else gives
' the button's own label
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
  ' opens under the button's left edge, but a list wider than its button
  ' (SELL CAR, CAR LIST...) is nudged back onto the screen instead of
  ' running off the right edge -- that's what looked like a stray, broken
  ' box sitting off to one side
  x = Max(4, Min(bx(j), W - lw - 4))
  y = by(j) + bh(j) + 2
  If y + lh > H - 4 Then y = H - lh - 4
  ' keep what's under the list so closing it puts the page back
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
    ' the row under the pointer is highlighted
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

' --- ticker ---------------------------------------------------------
' a scrolling line like club.py's footer: date, time, IP and the page's
' latest message (TickerMsg)
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

' a ticker in a bar that's already in the background art (no frame)
Sub TickerIn(x As integer, y As integer, w As integer, h As integer)
  tkx = x - 3
  tky = y - 2
  tkw = w + 6
  tkh = h + 4
  WifiCheck
  WeatherLoad
  lastTick = Timer
End Sub

' the weather part of the ticker, from weather.txt (the menu fetches it
' with net.inc): "epoch|Clear sky, 21 C, wind 12 km/h|near X".
' Dropped once it's over 3 hours old.
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

' the WiFi part of the ticker: connected (with this board's IP) or down.
' Checked again every time the ticker text comes round.
Sub WifiCheck
  Local string a$
  ' connected = it has a real IP (MM.INFO(WIFI STATUS) reads 1, not 3,
  ' when joined, so it isn't a safe test on its own)
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

' one of 5 extra live segments (0-4) that flow through the ticker
' alongside TickerMsg's, each updated on its own without resetting the
' scroll -- for a page with several live things to show at once.
' Capped per-segment: MMBasic strings max out at 255 chars, and with
' up to 5 segments plus the date/time/wifi/msg all sharing that budget
' in DrawTicker, one long segment (e.g. a full entrants list) could
' blow the limit and crash with "String too long"
Sub TickerSeg(slot As integer, s$)
  tkSeg$(slot) = Left$(s$, 60)
End Sub

Sub TickerTick
  If tkw = 0 Or Timer - lastTick < TICK_MS Then Exit Sub
  lastTick = Timer
  DrawTicker
End Sub

' appends add$ to base$ but never lets the result pass maxlen chars --
' trimming add$ itself if it would overrun. Used to build the ticker line
' piece by piece: MMBasic's "String too long" crash fires the instant any
' ONE concatenation exceeds 255 chars, so the cap has to apply as each
' piece goes on, not just once at the very end (that's already too late)
Function TickAppend$(base$, add$, maxlen As integer) As string
  If Len(base$) >= maxlen Then
    TickAppend$ = base$
  ElseIf Len(base$) + Len(add$) <= maxlen Then
    TickAppend$ = base$ + add$
  Else
    TickAppend$ = base$ + Left$(add$, maxlen - Len(base$))
  EndIf
End Function

' scrolls one character per tick. The live tkSeg$ segments go in before
' tkMsg$ -- they're what a page is actively showing right now (e.g. the
' race's live running order), so if the budget runs out it's the one-off
' message that gets trimmed, not the thing changing every couple of seconds
Sub DrawTicker
  Local string s$, c$
  Local integer p, i, a, hid, sg
  Const TICKER_MAX = 200
  ' tickerRaceMode (set by a page/game that's busy showing something more
  ' urgent, e.g. racing.bas mid-race): drop the date/time/weather/wifi
  ' that every ticker normally opens with, so the segments below -- the
  ' live, changing-every-couple-of-seconds stuff -- get the full budget
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
  ' each letter is drawn over its own background and only the space left
  ' at the end is cleared, so the bar is never blank (no flashing)
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

' --- dates ----------------------------------------------------------
' shown the club.py way, day-month-year without leading zeros (20-6-2026);
' stored as YYYY-MM-DD so the data files sort by date. DDate$ takes either
' YYYY-MM-DD or the board's DD-MM-YYYY (Date$).
Function DDate$(d$)
  If Mid$(d$, 5, 1) = "-" Then
    DDate$ = Str$(Val(Mid$(d$, 9, 2))) + "-" + Str$(Val(Mid$(d$, 6, 2))) + "-" + Left$(d$, 4)
  ElseIf Mid$(d$, 3, 1) = "-" And Len(d$) = 10 Then
    DDate$ = Str$(Val(Left$(d$, 2))) + "-" + Str$(Val(Mid$(d$, 4, 2))) + "-" + Right$(d$, 4)
  Else
    DDate$ = d$
  EndIf
End Function

' what was typed (20-6-2026, 20.6.2026, 20/6/2026) back to YYYY-MM-DD;
' anything else is kept as typed
Function IsoDate$(d$)
  Local string t$, p$(2)
  Local integer i, n
  If Mid$(d$, 5, 1) = "-" Then
    IsoDate$ = d$
    Exit Function
  EndIf
  For i = 1 To Len(d$)
    t$ = Mid$(d$, i, 1)
    If t$ = "-" Or t$ = "." Or t$ = "/" Then
      n = n + 1
      If n > 2 Then Exit For
    Else
      p$(n) = p$(n) + t$
    EndIf
  Next
  If n <> 2 Or Len(p$(2)) <> 4 Then
    IsoDate$ = d$
    Exit Function
  EndIf
  IsoDate$ = p$(2) + "-" + Right$("0" + p$(1), 2) + "-" + Right$("0" + p$(0), 2)
End Function

' --- draw.bas layouts ---------------------------------------------------
' draw.bas saves name.bmp (the art) and name.lay, a line per button or
' area: BUTTON,MEMBERS,x,y,w,h or AREA,TICKER,x,y,w,h. The buttons are in
' the art already, so here they're just places to click: hovering or
' pressing outlines them. A button's name is what the page acts on (the
' same as its label would be). Call after the .bmp is on screen.
' Returns how many buttons it added (0 = no layout file).
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

' the layout's AREA called n$ (-1 if it hasn't one)
Function LayArea(n$) As integer
  Local integer i
  LayArea = -1
  For i = 0 To nla - 1
    If laN$(i) = n$ Then LayArea = i
  Next
End Function

' a button that's part of the background picture: keeps a copy of the art
' under it (and a 2 pixel edge) so a highlight can be taken off again
Function AddArt(t$, x As integer, y As integer, wd As integer, ht As integer) As integer
  Local integer i
  i = AddBtn(t$, Max(2, x), Max(2, y), Min(wd, W - 3 - Max(2, x)), Min(ht, H - 3 - Max(2, y)), 0)
  bstyle(i) = 3
  CurHide
  Blit Read 10 + i, bx(i) - 2, by(i) - 2, bw(i) + 4, bh(i) + 4
  CurShow
  AddArt = i
End Function

' st: 0 = the art as drawn, 1 = amber outline, 2 = pressed (thicker)
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
