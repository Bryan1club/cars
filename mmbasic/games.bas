' games.bas -- GAMES page for the car club (MMBasic), ported from club.py's
' games_page.py: a launcher for the games in the SD card's Games folder
' (B:/Games, club.py's /sd/Games). Each game is its own .bas program; PLAY
' (or clicking a picked game again) RUNs it, and the game RUNs this page
' again when it ends. Top menu bar: GAME (PLAY / REFRESH), MENU.
'
' Build with: python mmbasic/build.py  (writes ../games.bas)

Option EXPLICIT
Option DEFAULT NONE

Const GAMES_DIR$ = "B:/Games"
Const MAXG = 60, ROWS = 14

Dim string gn$(MAXG - 1)
Dim integer count, top, sel, j, v
Dim integer lx, ly, lw, rh
Dim string cmd$

CoreInit
v = AddMenu("GAME", "PLAY|REFRESH")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "GAMES"
Layout
DrawAllBtns
StartCursor
LoadList
DrawList
If count = 0 Then
  TickerMsg "No games in " + GAMES_DIR$
Else
  TickerMsg Str$(count) + " games - click one, click again to play"
EndIf

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
  If j = -2 Then GoPage "club.bas"
  If j = -3 Then Clicked clickX, clickY
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "games", "games.bas"
  If cmd$ = "MENU" Then GoPage "club.bas"
  If cmd$ = "PLAY" Then PlayGame
  If cmd$ = "REFRESH" Then
    LoadList
    DrawList
    TickerMsg Str$(count) + " games"
  EndIf
  Pause 10
Loop

Sub Layout
  Local integer m
  m = W \ 40
  rh = fh(1) + 6
  lx = W \ 5
  lw = W - 2 * lx
  ly = H * 15 \ 100
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

Sub LoadList
  Local string f$
  count = 0
  On Error Skip
  f$ = Dir$(GAMES_DIR$ + "/*.bas", FILE)
  Do While f$ <> "" And count < MAXG And MM.Errno = 0
    gn$(count) = f$
    count = count + 1
    f$ = Dir$()
  Loop
  If count > 1 Then Sort gn$(), , 2, 0, count
  sel = Choice(count > 0, 0, -1)
End Sub

' the game names, big, without ".bas"
Sub DrawList
  Local integer r, y, n
  n = Min(ROWS, (H * 70 \ 100) \ rh)
  CurHide
  RBox lx, ly, lw, n * rh + 6, 6, C_DIM, C_BAR
  For r = 0 To n - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + lw \ 2, y + rh \ 2, UCase$(Left$(gn$(top + r), Len(gn$(top + r)) - 4)), "C", 1, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      If r = sel Then
        PlayGame
      Else
        sel = r
        DrawList
        TickerMsg gn$(sel) + " - click again to play"
      EndIf
    EndIf
  EndIf
End Sub

Sub PlayGame
  If sel < 0 Then Exit Sub
  GoPage GAMES_DIR$ + "/" + gn$(sel)
End Sub
