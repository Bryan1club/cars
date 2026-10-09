' settings.bas -- SETTINGS page (ADMIN > SETTINGS): the club's setup on ONE
' page with a row of tabs along the top, like a Windows or Linux settings
' window. Click a tab and its options are laid out right on the page -- no
' list boxes. Click a box to type in it, then APPLY.
'
'   WIFI   the network + password to switch to      (was wifi.bas)
'   EMAIL  the club's mail account                  (was mailsetup.bas)
'   SMS    the phone running "SMS Gateway"          (was mailsetup.bas)
'   UNIT   the club's name and its town             (was unitname.bas)
'   USERS  opens the USERS page   } these two are still pages of their own,
'   FILES  opens the FILES page   } so their tab just jumps to them
'
' Top menu bar: APPLY (saves / connects, whatever the open tab does), TEST
' (EMAIL and SMS tabs: sends a test message), BACK, HELP.
'
' The old WIFI, MAIL SETUP and UNIT NAME pages are untouched and still
' work; this page uses the same data files (mail.dat, sms.dat,
' clubname.txt, home.dat), so either can be used.
'
' Build with: python mmbasic/build.py  (writes ../settings.bas)

Option EXPLICIT
Option DEFAULT NONE

Const NTABS = 6
Const TAB_WIFI = 0, TAB_EMAIL = 1, TAB_SMS = 2, TAB_UNIT = 3, TAB_USERS = 4, TAB_FILES = 5
' the most boxes any tab shows (EMAIL and SMS have five)
Const MAXFIELDS = 5

Dim string tabName$(NTABS - 1)
' the boxes of the open tab: caption, text, and whether it's a password
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
' layout: tab row, then the panel the boxes sit in, then a status line
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

' --- tabs -----------------------------------------------------------

' open a tab: USERS and FILES jump to their own pages, the rest fill the
' panel with their boxes
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

' the tab row and the panel under it. The open tab is lit and joined to
' the panel; the others sit back, a little shorter.
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

' --- the open tab's boxes ------------------------------------------

' fill caption$/value$ for the open tab from its data file
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
      ' the password is kept base64'd in the file
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

' where box i sits
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

' one line of news under the panel
Sub Say(s$)
  CurHide
  Box 0, statusY, W, fh(0) + 8, 1, C_PAGE, C_PAGE
  CurShow
  PText W \ 2, statusY + fh(0) \ 2 + 4, Fit$(s$, W - 20), "C", 0, C_AMBER
End Sub

' --- clicks ---------------------------------------------------------

' a click that missed every menu button: a tab, or one of the boxes
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

' --- APPLY: what each tab does -------------------------------------

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

' what the board is connected to now
Function WifiLine$() As string
  Local string a$
  Local integer st
  On Error Skip
  st = MM.Info(WIFI STATUS)
  On Error Skip
  a$ = MM.Info$(IP ADDRESS)
  ' a real IP is the test: WIFI STATUS reads 1 (joined), not 3, when up
  If a$ <> "" And a$ <> "0.0.0.0" Then
    WifiLine$ = "Connected - this board is " + a$
  Else
    WifiLine$ = "Not connected (status " + Str$(st) + ")"
  EndIf
End Function

' OPTION WIFI saves the network and restarts the board. The stock firmware
' only allows that at the > prompt, not from a running program; if it
' refuses, say so and show the command (same as the WIFI page).
Sub Connect
  If value$(0) = "" Then
    Say "Type the network name first"
    Exit Sub
  EndIf
  Say "Switching to " + value$(0) + " - the board restarts"
  Pause 500
  On Error Skip
  Option WIFI value$(0), value$(1)
  ' only reached if the firmware refused (it restarts the board otherwise)
  TickerMsg "Firmware won't switch here: press Ctrl-C, then at > type  OPTION WIFI " + Chr$(34) + value$(0) + Chr$(34) + ", " + Chr$(34) + "password" + Chr$(34)
  Say "The firmware wouldn't switch from here - see the line below"
End Sub

Sub SaveMail
  If value$(0) = "" Or value$(2) = "" Then
    Say Choice(sms, "Enter at least the phone's IP and username", "Enter at least a server and email address")
    Exit Sub
  EndIf
  If Val(value$(1)) = 0 Then value$(1) = Choice(sms, "8080", "465")
  ' port 587 (STARTTLS) isn't supported, only 465 (SSL)
  If Not sms And Val(value$(1)) = 587 Then value$(1) = "465"
  Open HOME_DIR$ + Choice(sms, "/sms.dat", "/mail.dat") For Output As #1
  Print #1, value$(0) + "|" + value$(1) + "|" + value$(2) + "|" + B64$(value$(3)) + "|" + value$(4)
  Close #1
  DrawFields
  Say "Saved - TEST to check it works"
End Sub

' TEST sends with what's on screen, so it saves first
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
    ' the old weather (from the internet guess) goes; the menu fetches anew
    On Error Skip
    Kill HOME_DIR$ + "/weather.txt"
    Say "Saved - weather is now for " + weatherFor$
  Else
    Say "Couldn't find " + townName$ + " - check the spelling (or WiFi)"
  EndIf
End Sub
