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
Const NTABS = 6
Const TAB_WIFI = 0, TAB_EMAIL = 1, TAB_SMS = 2, TAB_UNIT = 3, TAB_USERS = 4, TAB_FILES = 5
Const MAXFIELDS = 5
Dim string tabName$(NTABS - 1)
Dim string caption$(MAXFIELDS - 1), value$(MAXFIELDS - 1)
Dim integer isSecret(MAXFIELDS - 1)
Dim integer fieldCount, openTab, sms
Dim integer tabY, tabH, tabW, tabX0, panelY, panelBottom
Dim integer fieldX, fieldW, fieldPitch, statusY
Dim string cmd$, townName$, weatherFor$, err$
Dim float la, lo
Dim integer j, v, i
CoreInit
v = AddMenu("APPLY", "")
v = AddMenu("TEST", "")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "SETTINGS"
Restore TabNames
For i = 0 To NTABS - 1
  Read tabName$(i)
Next
tabX0 = W \ 40
tabW = (W - W \ 20) \ NTABS
tabH = fh(0) + 14
tabY = H * 18 \ 100
panelY = tabY + tabH
fieldX = W \ 4
fieldW = W \ 2
fieldPitch = fh(0) * 2 + 16
panelBottom = panelY + fh(0) + 24 + MAXFIELDS * fieldPitch
statusY = panelBottom + 10
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
DrawAllBtns
StartCursor
ShowTab TAB_WIFI
Do
  j = PollInput()
  If j = -2 Then GoPage "admin.bas"
  If j = -3 Then Clicked clickX, clickY
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "settings", "settings.bas"
  Select Case cmd$
    Case "BACK"
      GoPage "admin.bas"
    Case "APPLY"
      Apply
    Case "TEST"
      TestMessage
  End Select
  Pause 10
Loop
TabNames:
Data "WIFI", "EMAIL", "SMS", "UNIT", "USERS", "FILES"
Sub ShowTab(t As integer)
  If t = TAB_USERS Then GoPage "users.bas"
  If t = TAB_FILES Then GoPage "files.bas"
  openTab = t
  LoadTab
  DrawTabs
  DrawFields
  Select Case openTab
    Case TAB_WIFI
      Say WifiLine$()
      TickerMsg "Type the network and its password, then APPLY (the board restarts)"
    Case TAB_EMAIL, TAB_SMS
      TickerMsg "Fill in the boxes, APPLY to save, TEST to check it works"
    Case TAB_UNIT
      TickerMsg "Click a box to type, then APPLY"
  End Select
End Sub
Sub DrawTabs
  Local integer i, x, y, h
  CurHide
  Box 0, tabY - 4, W, panelBottom - tabY + 8, 1, C_PAGE, C_PAGE
  RBox tabX0, panelY, W - W \ 20, panelBottom - panelY, 4, C_DIM, C_PAGE
  For i = 0 To NTABS - 1
    x = tabX0 + i * tabW
    If i = openTab Then
      RBox x, tabY, tabW - 4, tabH + 4, 6, C_INK, C_GRN_BASE
      PText x + tabW \ 2 - 2, tabY + tabH \ 2 + 2, tabName$(i), "C", 0, C_INK
    Else
      RBox x, tabY + 5, tabW - 4, tabH - 5, 6, C_DIM, C_BAR
      PText x + tabW \ 2 - 2, tabY + tabH \ 2 + 4, tabName$(i), "C", 0, C_DIM
    EndIf
  Next
  CurShow
End Sub
Sub LoadTab
  Local string l$
  Local integer i
  fieldCount = 0
  For i = 0 To MAXFIELDS - 1
    caption$(i) = ""
    value$(i) = ""
    isSecret(i) = 0
  Next
  Select Case openTab
    Case TAB_WIFI
      fieldCount = 2
      caption$(0) = "Network name"
      caption$(1) = "Password"
      isSecret(1) = 1
    Case TAB_EMAIL, TAB_SMS
      sms = (openTab = TAB_SMS)
      fieldCount = 5
      If sms Then
        Restore SmsLabels
        l$ = NetLine$(HOME_DIR$ + "/sms.dat")
      Else
        Restore MailLabels
        l$ = NetLine$(HOME_DIR$ + "/mail.dat")
      EndIf
      For i = 0 To 4
        Read caption$(i)
        value$(i) = Fld$(l$, i + 1)
      Next
      value$(3) = UnB64$(value$(3))
      isSecret(3) = 1
      If value$(1) = "" Then value$(1) = Choice(sms, "8080", "465")
    Case TAB_UNIT
      fieldCount = 2
      caption$(0) = "Club name (blank = CAR CLUB)"
      caption$(1) = "Town (for the weather)"
      value$(0) = NetLine$(HOME_DIR$ + "/clubname.txt")
      value$(1) = Fld$(NetLine$(HOME_DIR$ + "/home.dat"), 4)
      weatherFor$ = Fld$(NetLine$(HOME_DIR$ + "/home.dat"), 3)
  End Select
End Sub
MailLabels:
Data "Server (e.g. smtp.gmail.com)", "Port (465)", "Email address", "Password", "TEST sends to (blank = same address)"
SmsLabels:
Data "Phone IP (shown in the SMS Gateway app)", "Port (8080)", "Username", "Password", "Phone number for TEST"
Function FieldTop(i As integer) As integer
  FieldTop = panelY + fh(0) + 24 + i * fieldPitch
End Function
Sub DrawFields
  Local integer i
  CurHide
  Box tabX0 + 4, panelY + 4, W - W \ 20 - 8, panelBottom - panelY - 8, 1, C_PAGE, C_PAGE
  CurShow
  For i = 0 To fieldCount - 1
    DrawField i
  Next
End Sub
Sub DrawField(i As integer)
  PText fieldX, FieldTop(i) - fh(0) \ 2 - 4, caption$(i), "L", 0, C_INK
  If isSecret(i) Then
    TextBox fieldX, FieldTop(i), fieldW, String$(Len(value$(i)), "*"), 0
  Else
    TextBox fieldX, FieldTop(i), fieldW, value$(i), 0
  EndIf
End Sub
Sub Say(s$)
  CurHide
  Box 0, statusY, W, fh(0) + 8, 1, C_PAGE, C_PAGE
  CurShow
  PText W \ 2, statusY + fh(0) \ 2 + 4, Fit$(s$, W - 20), "C", 0, C_AMBER
End Sub
Sub Clicked(x As integer, y As integer)
  Local integer i, top
  If y >= tabY And y < panelY Then
    i = (x - tabX0) \ tabW
    If x >= tabX0 And i >= 0 And i < NTABS And i <> openTab Then ShowTab i
    Exit Sub
  EndIf
  If x < fieldX Or x >= fieldX + fieldW Then Exit Sub
  For i = 0 To fieldCount - 1
    top = FieldTop(i)
    If y >= top And y < top + fh(0) + 6 Then
      If isSecret(i) Then
        value$(i) = EditPass$(fieldX, top, fieldW, value$(i))
      Else
        value$(i) = Trim$(EditText$(fieldX, top, fieldW, value$(i)))
      EndIf
      Exit Sub
    EndIf
  Next
End Sub
Sub Apply
  Select Case openTab
    Case TAB_WIFI
      Connect
    Case TAB_EMAIL, TAB_SMS
      SaveMail
    Case TAB_UNIT
      SaveUnit
  End Select
End Sub
Function WifiLine$() As string
  Local string a$
  Local integer st
  On Error Skip
  st = MM.Info(WIFI STATUS)
  On Error Skip
  a$ = MM.Info$(IP ADDRESS)
  If a$ <> "" And a$ <> "0.0.0.0" Then
    WifiLine$ = "Connected - this board is " + a$
  Else
    WifiLine$ = "Not connected (status " + Str$(st) + ")"
  EndIf
End Function
Sub Connect
  If value$(0) = "" Then
    Say "Type the network name first"
    Exit Sub
  EndIf
  Say "Switching to " + value$(0) + " - the board restarts"
  Pause 500
  On Error Skip
  Option WIFI value$(0), value$(1)
  TickerMsg "Firmware won't switch here: press Ctrl-C, then at > type  OPTION WIFI " + Chr$(34) + value$(0) + Chr$(34) + ", " + Chr$(34) + "password" + Chr$(34)
  Say "The firmware wouldn't switch from here - see the line below"
End Sub
Sub SaveMail
  If value$(0) = "" Or value$(2) = "" Then
    Say Choice(sms, "Enter at least the phone's IP and username", "Enter at least a server and email address")
    Exit Sub
  EndIf
  If Val(value$(1)) = 0 Then value$(1) = Choice(sms, "8080", "465")
  If Not sms And Val(value$(1)) = 587 Then value$(1) = "465"
  Open HOME_DIR$ + Choice(sms, "/sms.dat", "/mail.dat") For Output As #1
  Print #1, value$(0) + "|" + value$(1) + "|" + value$(2) + "|" + B64$(value$(3)) + "|" + value$(4)
  Close #1
  DrawFields
  Say "Saved - TEST to check it works"
End Sub
Sub TestMessage
  If openTab <> TAB_EMAIL And openTab <> TAB_SMS Then
    Say "TEST is for the EMAIL and SMS tabs"
    Exit Sub
  EndIf
  SaveMail
  If value$(0) = "" Or value$(2) = "" Then Exit Sub
  If sms Then
    If value$(4) = "" Then
      Say "Enter a phone number for TEST first"
      Exit Sub
    EndIf
    Say "Sending a test text to " + value$(4) + " ..."
    err$ = SendSms$(value$(4), "Test from the car club board")
  Else
    Say "Sending a test email ..."
    err$ = SendMail$(Choice(value$(4) = "", value$(2), value$(4)), "Car club test", "This is a test from the car club board.")
  EndIf
  If err$ = "" Then
    Say "Sent - check " + Choice(sms, "the phone", "the inbox")
  Else
    Say "Failed: " + err$
  EndIf
End Sub
Sub SaveUnit
  Open HOME_DIR$ + "/clubname.txt" For Output As #1
  If value$(0) <> "" Then Print #1, value$(0)
  Close #1
  townName$ = value$(1)
  If townName$ = "" Then
    Say "Saved - " + Choice(value$(0) = "", "CAR CLUB", value$(0)) + " shows on the menu"
    Exit Sub
  EndIf
  Say "Looking up " + townName$ + " ..."
  If TownLookup(townName$, la, lo, weatherFor$) Then
    Open HOME_DIR$ + "/home.dat" For Output As #1
    Print #1, Str$(la, 0, 4) + "|" + Str$(lo, 0, 4) + "|" + weatherFor$ + "|" + townName$
    Close #1
    On Error Skip
    Kill HOME_DIR$ + "/weather.txt"
    Say "Saved - weather is now for " + weatherFor$
  Else
    Say "Couldn't find " + townName$ + " - check the spelling (or WiFi)"
  EndIf
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
Function EditPass$(x As integer, y As integer, w As integer, s$)
  Local string t$, k$
  t$ = s$
  TextBox x, y, w, String$(Len(t$), "*") + "_", 1
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
          If Len(t$) < 40 And k$ <> "|" Then t$ = t$ + k$
      End Select
      TextBox x, y, w, String$(Len(t$), "*") + "_", 1
    EndIf
    If ClickAt() Then Exit Do
    Pause 10
  Loop
  TextBox x, y, w, String$(Len(t$), "*"), 0
  EditPass$ = t$
End Function
Function NetLine$(f$)
  NetLine$ = ""
  On Error Skip
  Open f$ For Input As #3
  If MM.Errno Then Exit Function
  If Not Eof(#3) Then Line Input #3, NetLine$
  Close #3
End Function
Function B64$(s$)
  Local string t$, a$
  Local integer i, n, v
  a$ = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  For i = 1 To Len(s$) Step 3
    n = Len(s$) - i + 1
    v = Asc(Mid$(s$, i, 1)) << 16
    If n > 1 Then v = v Or (Asc(Mid$(s$, i + 1, 1)) << 8)
    If n > 2 Then v = v Or Asc(Mid$(s$, i + 2, 1))
    t$ = t$ + Mid$(a$, ((v >> 18) And 63) + 1, 1) + Mid$(a$, ((v >> 12) And 63) + 1, 1)
    t$ = t$ + Choice(n > 1, Mid$(a$, ((v >> 6) And 63) + 1, 1), "=")
    t$ = t$ + Choice(n > 2, Mid$(a$, (v And 63) + 1, 1), "=")
  Next
  B64$ = t$
End Function
Function UnB64$(s$)
  Local string t$, a$
  Local integer i, k, v, c, bits
  a$ = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  For i = 1 To Len(s$)
    c = Instr(a$, Mid$(s$, i, 1))
    If c > 0 Then
      v = ((v << 6) Or (c - 1)) And &HFFFFFF
      bits = bits + 6
      If bits >= 8 Then
        bits = bits - 8
        t$ = t$ + Chr$((v >> bits) And 255)
      EndIf
    EndIf
  Next
  UnB64$ = t$
End Function
Function SmtpCmd$(c$, want$, buf%())
  If c$ = "" Then
    On Error Skip
    WEB TCP CLIENT READ buf%(), 15000
  Else
    On Error Skip
    WEB TCP CLIENT REQUEST c$ + Chr$(13) + Chr$(10), buf%(), 15000
  EndIf
  If MM.Errno Then
    SmtpCmd$ = MM.ErrMsg$
  ElseIf LGetStr$(buf%(), 1, 3) <> want$ Then
    SmtpCmd$ = LGetStr$(buf%(), 1, Min(60, LLen(buf%())))
  EndIf
End Function
Function MailDate$()
  Local string d$
  d$ = Date$
  MailDate$ = Left$(Day$(Now), 3) + ", " + Left$(d$, 2) + " " + Mid$("JanFebMarAprMayJunJulAugSepOctNovDec", Val(Mid$(d$, 4, 2)) * 3 - 2, 3) + " " + Right$(d$, 4) + " " + Time$ + " +1000"
End Function
Function SendMail$(to$, subj$, mailText$)
  Local buf%(256), msg%(512)
  Local string cfg$, srv$, usr$, pw$, e$, l$, b$
  Local integer port, p
  cfg$ = NetLine$(HOME_DIR$ + "/mail.dat")
  srv$ = Fld$(cfg$, 1)
  port = Val(Fld$(cfg$, 2))
  usr$ = Fld$(cfg$, 3)
  pw$ = UnB64$(Fld$(cfg$, 4))
  If srv$ = "" Or usr$ = "" Then
    SendMail$ = "MAIL SETUP isn't filled in"
    Exit Function
  EndIf
  If port = 0 Or port = 587 Then port = 465
  On Error Skip
  WEB OPEN TLS CLIENT srv$, port, 15000
  If MM.Errno Then
    SendMail$ = "Can't reach " + srv$ + ": " + MM.ErrMsg$
    Exit Function
  EndIf
  e$ = SmtpCmd$("", "220", buf%())
  If e$ = "" Then e$ = SmtpCmd$("EHLO carclub", "250", buf%())
  If e$ = "" Then e$ = SmtpCmd$("AUTH LOGIN", "334", buf%())
  If e$ = "" Then e$ = SmtpCmd$(B64$(usr$), "334", buf%())
  If e$ = "" Then
    e$ = SmtpCmd$(B64$(pw$), "235", buf%())
    If e$ <> "" Then e$ = "login refused - check the email address and password"
  EndIf
  If e$ = "" Then e$ = SmtpCmd$("MAIL FROM:<" + usr$ + ">", "250", buf%())
  If e$ = "" Then e$ = SmtpCmd$("RCPT TO:<" + to$ + ">", "250", buf%())
  If e$ = "" Then e$ = SmtpCmd$("DATA", "354", buf%())
  If e$ = "" Then
    LongString Clear msg%()
    MailLine msg%(), "From: " + usr$
    MailLine msg%(), "To: " + to$
    MailLine msg%(), "Subject: " + subj$
    MailLine msg%(), "Date: " + MailDate$()
    MailLine msg%(), "Content-Type: text/plain; charset=us-ascii"
    MailLine msg%(), ""
    b$ = mailText$
    Do
      p = Instr(b$, "~")
      If p = 0 Then
        l$ = b$
        b$ = ""
      Else
        l$ = Left$(b$, p - 1)
        b$ = Mid$(b$, p + 1)
      EndIf
      If Left$(l$, 1) = "." Then l$ = "." + l$
      MailLine msg%(), l$
    Loop Until b$ = ""
    On Error Skip
    WEB TCP CLIENT WRITE msg%()
    If MM.Errno Then e$ = MM.ErrMsg$
  EndIf
  If e$ = "" Then e$ = SmtpCmd$(".", "250", buf%())
  On Error Skip
  WEB TCP CLIENT REQUEST "QUIT" + Chr$(13) + Chr$(10), buf%(), 3000
  On Error Skip
  WEB CLOSE TCP CLIENT
  SendMail$ = e$
End Function
Sub MailLine(m%(), s$)
  LongString Append m%(), s$ + Chr$(13) + Chr$(10)
End Sub
Function E164$(ph$)
  Local string d$, c$
  Local integer i
  For i = 1 To Len(ph$)
    c$ = Mid$(ph$, i, 1)
    If c$ >= "0" And c$ <= "9" Then d$ = d$ + c$
  Next
  If d$ = "" Then Exit Function
  If Left$(d$, 2) = "61" Then
    E164$ = "+" + d$
  ElseIf Left$(d$, 1) = "0" Then
    E164$ = "+61" + Mid$(d$, 2)
  Else
    E164$ = "+" + d$
  EndIf
End Function
Function JsonStr$(s$)
  Local string t$, c$
  Local integer i
  For i = 1 To Len(s$)
    c$ = Mid$(s$, i, 1)
    If c$ = Chr$(34) Or c$ = "\" Then
      t$ = t$ + "\" + c$
    ElseIf c$ = "~" Then
      t$ = t$ + "\n"
    ElseIf c$ >= " " Then
      t$ = t$ + c$
    EndIf
  Next
  JsonStr$ = t$
End Function
Function SendSms$(phone$, text$)
  Local buf%(128), req%(128)
  Local string cfg$, ip$, usr$, pw$, to$, j$, r$
  Local integer port
  cfg$ = NetLine$(HOME_DIR$ + "/sms.dat")
  ip$ = Fld$(cfg$, 1)
  port = Val(Fld$(cfg$, 2))
  usr$ = Fld$(cfg$, 3)
  pw$ = UnB64$(Fld$(cfg$, 4))
  If ip$ = "" Or usr$ = "" Then
    SendSms$ = "SMS SETUP isn't filled in"
    Exit Function
  EndIf
  If port = 0 Then port = 8080
  to$ = E164$(phone$)
  If to$ = "" Then
    SendSms$ = "no phone number"
    Exit Function
  EndIf
  j$ = "{" + Chr$(34) + "textMessage" + Chr$(34) + ":{" + Chr$(34) + "text" + Chr$(34) + ":" + Chr$(34)
  LongString Clear req%()
  LongString Append req%(), j$
  LongString Append req%(), JsonStr$(text$)
  LongString Append req%(), Chr$(34) + "}," + Chr$(34) + "phoneNumbers" + Chr$(34) + ":[" + Chr$(34) + to$ + Chr$(34) + "]}"
  r$ = "POST /message HTTP/1.1" + Chr$(13) + Chr$(10) + "Host: " + ip$ + Chr$(13) + Chr$(10)
  r$ = r$ + "Authorization: Basic " + B64$(usr$ + ":" + pw$) + Chr$(13) + Chr$(10)
  r$ = r$ + "Content-Type: application/json" + Chr$(13) + Chr$(10) + "Connection: close" + Chr$(13) + Chr$(10)
  r$ = r$ + "Content-Length: " + Str$(LLen(req%())) + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB OPEN TCP CLIENT ip$, port, 10000
  If MM.Errno Then
    SendSms$ = "Can't reach the phone at " + ip$ + " - same WiFi?"
    Exit Function
  EndIf
  LongString Clear buf%()
  LongString Append buf%(), r$
  On Error Skip
  WEB TCP CLIENT WRITE buf%()
  If MM.Errno = 0 Then
    On Error Skip
    WEB TCP CLIENT WRITE req%()
  EndIf
  If MM.Errno = 0 Then
    On Error Skip
    WEB TCP CLIENT READ buf%(), 10000
  EndIf
  If MM.Errno Then
    SendSms$ = MM.ErrMsg$
  ElseIf Instr(LGetStr$(buf%(), 1, Min(20, LLen(buf%()))), " 20") = 0 Then
    SendSms$ = "phone said: " + LGetStr$(buf%(), 1, Min(40, LLen(buf%())))
  EndIf
  On Error Skip
  WEB CLOSE TCP CLIENT
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
