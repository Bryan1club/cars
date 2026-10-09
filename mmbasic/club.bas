' club.bas -- the car club's main menu (MMBasic): club.py's dashboard.
' Target: MMBasic 6.04 on the Pico Computer 3 (RP2350), MODE 3 640x480
' with the club palette (needs board 2's MAP-fixed firmware).
'
' The weather is fetched when the menu starts and every 3 minutes after
' (net.inc WeatherNow$), saved to weather.txt, and every page's ticker
' shows it.
' The background is club.py's dash art (menu_bg.bmp, made from
' assets/dash_bg.bmp by assets/gen_club_bas_assets.py): a brushed panel,
' the console with two gauge housings, eight switch plates, the ticker
' bar and three more plates underneath. The buttons ARE those plates --
' the positions below match the art exactly (see gen_dash_bg.py's
' switch grid). Left gauge: an analog clock. Right gauge: day and date.
'
' Each page is its own program (members.bas, gps.bas, ...) run from the
' club folder; this menu RUNs it and the page RUNs club.bas to come back.
' Mouse, touch and keyboard (arrows + Enter) all work.
'
' A menu drawn in draw.bas replaces all that: save it there as "menu"
' (B:/draw/menu.bmp + menu.lay) and the menu uses that picture, its
' BUTTONs as the buttons (named MEMBERS, EVENTS... like the plates) and
' its AREAs TICKER, CLOCK, DATE and TITLE for those (any left out aren't
' shown). Delete or rename B:/draw/menu.lay to get the dash back.
'
' Build with: python mmbasic/build.py  (writes ../club.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MENU_BG$ = "menu_bg.bmp"
Const LAY_MENU$ = "B:/draw/menu"
Const WX_EVERY = 180000   ' ms between weather updates (3 minutes)
' the switch plates in the dash art (club.py Menu / gen_dash_bg.py)
Const PLATE_W = 110, PLATE_H = 20, PLATE_GAP = 3, PLATE_Y0 = 216
Const LEFT_X = 190, RIGHT_X = 340
Const BOT_W = 90, BOT_H = 20, BOT_GAP = 10, BOT_X0 = 175, BOT_Y0 = 398
' the two gauge faces and the ticker bar (a draw.bas layout can move
' them; clkX / dtX -1 = not shown)
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
' the weather for every page's ticker: now, then every WX_EVERY ms
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

' the menu's own dash art: the buttons are its switch plates
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

' a draw.bas menu: the ticker, clock, date and club name go in its AREAs
Sub LayPlaces
  a = LayArea("TICKER")
  If a >= 0 Then
    mtX = laX(a) : mtY = laY(a) : mtW = laW(a) : mtH = laH(a)
  Else
    ' none drawn: a strip along the bottom
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

' the club's name from clubname.txt in the club folder, if it's there
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

' the left gauge: a clock face with Roman numerals at 12, 3, 6, 9, and
' hour, minute and (red) second hands, redrawn every second
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
  ' angles into variables first: "Hand (a) * 30, ..." would read the
  ' bracket as Hand's own argument list and draw nothing
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

' the right gauge: day of the week, day-month, and the year
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

' fetch the weather (net.inc) into weather.txt, and show it straight away
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
      ' leave the prompt the way the board normally has it
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
