' snake.bas -- the club's snake game, ported from club.py's
' assets/games/snake.py: a 30x18 board of 20px cells, the snake moves every
' 220ms, eat the red food to grow, hitting a wall or yourself ends it.
' Arrow keys or the LEFT/UP/DOWN/RIGHT buttons steer; after a game over any
' direction starts again. QUIT (or Esc) goes back to the GAMES page.
'
' Build with: python mmbasic/build.py  (writes ../games/snake.bas,
' which goes in the SD card's Games folder)

Option EXPLICIT
Option DEFAULT NONE

Const CELL = 20, COLS = 30, RWS = 18, MOVE_MS = 220
Const MAXLEN = COLS * RWS

Dim integer bx0, by0, sxs(MAXLEN - 1), sys(MAXLEN - 1)
Dim integer hd, ln, dx, dy, ndx, ndy, fx, fy, score, over, last, j
Dim integer bL, bU, bD, bR, bQ
Dim string k$

CoreInit
DrawPage "SNAKE"
bx0 = (W - COLS * CELL) \ 2
by0 = H * 11 \ 100
Buttons
DrawAllBtns
StartCursor
NewGame

Do
  ' arrow keys first, so PollInput doesn't use them to move between buttons
  k$ = Inkey$
  If k$ <> "" Then
    Select Case Asc(k$)
      Case 128
        Steer 0, -1
      Case 129
        Steer 0, 1
      Case 130
        Steer -1, 0
      Case 131
        Steer 1, 0
      Case 27
        GoPage "games.bas"
    End Select
  EndIf
  j = PollInput()
  If j = bL Then Steer -1, 0
  If j = bU Then Steer 0, -1
  If j = bD Then Steer 0, 1
  If j = bR Then Steer 1, 0
  If j = bQ Or j = -2 Then GoPage "games.bas"
  If Not over And Timer - last >= MOVE_MS Then
    last = Timer
    Advance
  EndIf
  Pause 5
Loop

Sub Buttons
  ' not w/h: MMBasic ignores case, so they'd be the screen's W and H
  Local integer yb, bwid, bht, m
  m = W \ 40
  bht = H \ 12
  bwid = (W - 6 * m) \ 5
  yb = H - bht - m
  bL = AddBtn("LEFT", m, yb, bwid, bht, 0)
  bU = AddBtn("UP", m * 2 + bwid, yb, bwid, bht, 0)
  bD = AddBtn("DOWN", m * 3 + bwid * 2, yb, bwid, bht, 0)
  bR = AddBtn("RIGHT", m * 4 + bwid * 3, yb, bwid, bht, 0)
  bQ = AddBtn("QUIT", m * 5 + bwid * 4, yb, bwid, bht, 1)
End Sub

Sub NewGame
  Local integer i
  CurHide
  Box bx0 - 2, by0 - 2, COLS * CELL + 4, RWS * CELL + 4, 2, C_DIM, C_PAGE
  CurShow
  ln = 3
  hd = ln - 1
  For i = 0 To ln - 1
    sxs(i) = COLS \ 2 - (ln - 1 - i)
    sys(i) = RWS \ 2
    PaintCell sxs(i), sys(i), C_GRN_TOP
  Next
  dx = 1
  dy = 0
  ndx = 1
  ndy = 0
  score = 0
  over = 0
  ShowScore
  PlaceFood
  last = Timer
End Sub

Sub PaintCell(c As integer, r As integer, col As integer)
  CurHide
  Box bx0 + c * CELL + 1, by0 + r * CELL + 1, CELL - 2, CELL - 2, 1, col, col
  CurShow
End Sub

Sub ShowScore
  CurHide
  Box W \ 40, H \ 16 - fh(1) \ 2, W \ 3, fh(1), 1, C_PAGE, C_PAGE
  CurShow
  PText W \ 40, H \ 16, "Score: " + Str$(score), "L", 1, C_INK
End Sub

' a free cell for the food, not on the snake
Sub PlaceFood
  Local integer i, ok
  Do
    fx = Int(Rnd * COLS)
    fy = Int(Rnd * RWS)
    ok = 1
    For i = 0 To ln - 1
      If sxs((hd - i + MAXLEN) Mod MAXLEN) = fx And sys((hd - i + MAXLEN) Mod MAXLEN) = fy Then ok = 0
    Next
  Loop Until ok
  PaintCell fx, fy, C_RED_TOP
End Sub

' no turning straight back on yourself; after a game over it restarts
Sub Steer(x As integer, y As integer)
  If over Then
    NewGame
    Exit Sub
  EndIf
  If x = -dx And y = -dy Then Exit Sub
  ndx = x
  ndy = y
End Sub

Sub Advance
  Local integer nx, ny, i, tl
  dx = ndx
  dy = ndy
  nx = sxs(hd) + dx
  ny = sys(hd) + dy
  If nx < 0 Or nx >= COLS Or ny < 0 Or ny >= RWS Then
    GameOver
    Exit Sub
  EndIf
  For i = 0 To ln - 1
    If sxs((hd - i + MAXLEN) Mod MAXLEN) = nx And sys((hd - i + MAXLEN) Mod MAXLEN) = ny Then
      GameOver
      Exit Sub
    EndIf
  Next
  hd = (hd + 1) Mod MAXLEN
  sxs(hd) = nx
  sys(hd) = ny
  PaintCell nx, ny, C_GRN_TOP
  If nx = fx And ny = fy Then
    ln = ln + 1
    score = score + 10
    ShowScore
    PlaceFood
  Else
    tl = (hd - ln + MAXLEN) Mod MAXLEN
    PaintCell sxs(tl), sys(tl), C_PAGE
  EndIf
End Sub

Sub GameOver
  over = 1
  CurHide
  RBox W \ 2 - 160, by0 + RWS * CELL \ 2 - 40, 320, 80, 10, C_INK, C_BAR
  CurShow
  PText W \ 2, by0 + RWS * CELL \ 2 - 14, "GAME OVER  -  " + Str$(score), "C", 1, C_INK
  PText W \ 2, by0 + RWS * CELL \ 2 + 20, "press a direction to play again", "C", 0, C_INK
End Sub
