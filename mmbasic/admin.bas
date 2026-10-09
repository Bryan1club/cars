' admin.bas -- ADMIN page for the car club (MMBasic), ported from club.py's
' admin_page.py: a grid of admin buttons. FILES (club.py's FILE TRANSFER,
' with the text editor) works; the others say so until they're ported.
' Bluetooth is left out -- the MMBasic boards don't use BLE.
'
' Build with: python mmbasic/build.py  (writes ../admin.bas)

Option EXPLICIT
Option DEFAULT NONE

Dim integer j, v, i, m, bwid, bht, gx, gy
Dim string cmd$

CoreInit
DrawPage "ADMIN"
m = W \ 40
bwid = (W - 4 * m) \ 3
bht = H \ 9
gx = m
gy = H * 16 \ 100
Restore AdminButtons
For i = 0 To 5
  Read cmd$
  v = AddBtn(cmd$, gx + (i Mod 3) * (bwid + m), gy + (i \ 3) * (bht + m * 2), bwid, bht, 0)
Next
v = AddBtn("MENU", (W - bwid) \ 2, gy + 2 * (bht + m * 2) + m, bwid, bht, 0)
v = AddBtn("HELP", W - bwid \ 2 - W \ 40, gy + 2 * (bht + m * 2) + m, bwid \ 2, bht, 0)
DrawAllBtns
TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
StartCursor
TickerMsg "Admin"

Do
  j = PollInput()
  If j = -2 Then GoPage "club.bas"
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "admin", "admin.bas"
  Select Case cmd$
    Case "MENU"
      GoPage "club.bas"
    Case "FILES"
      GoPage "files.bas"
    Case "USERS"
      GoPage "users.bas"
    Case "MAIL SETUP"
      GoPage "mailsetup.bas"
    Case "UNIT NAME"
      GoPage "unitname.bas"
    Case "WIFI"
      GoPage "wifi.bas"
    Case "SETTINGS"
      GoPage "settings.bas"
    Case ""
    Case Else
      TickerMsg cmd$ + " - not ported yet"
  End Select
  Pause 10
Loop

AdminButtons:
Data "FILES", "USERS", "MAIL SETUP", "WIFI", "UNIT NAME", "SETTINGS"
