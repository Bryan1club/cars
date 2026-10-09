' clicker.bas -- the club's sample game, ported from club.py's
' assets/games/clicker.py: click the button, the count goes up. QUIT (or
' Esc) goes back to the GAMES page.
'
' Build with: python mmbasic/build.py  (writes ../games/clicker.bas,
' which goes in the SD card's Games folder)

Option EXPLICIT
Option DEFAULT NONE

Dim integer j, n, bClick, bQuit

CoreInit
DrawPage "CLICKER"
bClick = AddBtn("CLICK ME", W \ 2 - W \ 6, H * 55 \ 100, W \ 3, H \ 8, 0)
bQuit = AddBtn("QUIT", W \ 2 - W \ 10, H * 75 \ 100, W \ 5, H \ 12, 1)
DrawAllBtns
StartCursor
ShowCount

Do
  j = PollInput()
  If j = bClick Then
    n = n + 1
    ShowCount
  EndIf
  If j = bQuit Or j = -2 Then GoPage "games.bas"
  Pause 10
Loop

Sub ShowCount
  CurHide
  Box W \ 4, H * 30 \ 100, W \ 2, H \ 6, 1, C_PAGE, C_PAGE
  Text W \ 2, H * 38 \ 100, Str$(n), "CM", 6, 1, C_INK, C_PAGE
  CurShow
End Sub
