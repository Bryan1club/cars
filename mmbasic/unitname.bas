' unitname.bas -- UNIT NAME page (ADMIN > UNIT NAME), ported from club.py's
' unit_name_page.py: the club's name, shown on the menu (clubname.txt,
' blank = "CAR CLUB"), and its town: SAVE looks the town up and keeps
' its position in home.dat, which the weather uses when there's no GPS
' fix (instead of guessing from the internet connection -- Telstra's
' guess is Melbourne). Top menu bar: SAVE, BACK. Click a box to type.
'
' Build with: python mmbasic/build.py  (writes ../unitname.bas)

Option EXPLICIT
Option DEFAULT NONE

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
        ' the old weather (from the internet guess) goes; the menu fetches anew
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
