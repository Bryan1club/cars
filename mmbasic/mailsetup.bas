' mailsetup.bas -- MAIL SETUP page (ADMIN > MAIL SETUP), ported from
' club.py's email_settings_page.py. Two modes, swapped with MODE:
'   EMAIL  the club's mail account (server, port, address, password,
'          where TEST sends to) -> mail.dat
'   SMS    the phone running "SMS Gateway for Android" (IP, port,
'          username, password, a phone number for TEST) -> sms.dat
' Top menu bar like club.py: MODE, SAVE, TEST, BACK. Click a box to type.
' Passwords are shown as stars and kept base64'd in the file.
'
' Build with: python mmbasic/build.py  (writes ../mailsetup.bas)

Option EXPLICIT
Option DEFAULT NONE

Dim string lab$(4), f$(4), cmd$, e$
Dim integer sms, j, v, i, fx, fy, fw, fp, sy

CoreInit
v = AddMenu("MODE", "EMAIL|SMS")
v = AddMenu("SAVE", "")
v = AddMenu("TEST", "")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "MAIL SETUP"
fx = W \ 4
fw = W \ 2
fy = H * 20 \ 100
fp = fh(0) * 2 + 16
sy = fy + 5 * fp + 4
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
DrawAllBtns
StartCursor
ShowMode

Do
  j = PollInput()
  If j = -2 Then GoPage "admin.bas"
  If j = -3 Then Clicked clickX, clickY
  cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "mailsetup", "mailsetup.bas"
  Select Case cmd$
    Case "BACK"
      GoPage "admin.bas"
    Case "EMAIL", "SMS"
      sms = (cmd$ = "SMS")
      ShowMode
    Case "SAVE"
      SaveMode
    Case "TEST"
      TestMode
  End Select
  Pause 10
Loop

Sub ShowMode
  Local string l$
  If sms Then
    Restore SmsLabels
    l$ = NetLine$(HOME_DIR$ + "/sms.dat")
  Else
    Restore MailLabels
    l$ = NetLine$(HOME_DIR$ + "/mail.dat")
  EndIf
  For i = 0 To 4
    Read lab$(i)
    f$(i) = Fld$(l$, i + 1)
  Next
  f$(3) = UnB64$(f$(3))
  If f$(1) = "" Then f$(1) = Choice(sms, "8080", "465")
  CurHide
  Box fx - 4, fy - fh(0) - 8, fw + 8, 5 * fp + fh(0) + 8, 1, C_PAGE, C_PAGE
  CurShow
  For i = 0 To 4
    PText fx, fy + i * fp - fh(0) \ 2 - 4, lab$(i), "L", 0, C_INK
  Next
  DrawForm
  If l$ = "" Then
    Say "Not set up yet - fill in, then SAVE"
  Else
    Say Choice(sms, "Phone gateway set up", "Email set up") + " - TEST to check it works"
  EndIf
End Sub

MailLabels:
Data "Server (e.g. smtp.gmail.com)", "Port (465)", "Email address", "Password", "TEST sends to (blank = same address)"
SmsLabels:
Data "Phone IP (shown in the SMS Gateway app)", "Port (8080)", "Username", "Password", "Phone number for TEST"

Sub DrawForm
  For i = 0 To 4
    If i = 3 Then
      TextBox fx, fy + i * fp, fw, String$(Len(f$(3)), "*"), 0
    Else
      TextBox fx, fy + i * fp, fw, f$(i), 0
    EndIf
  Next
End Sub

Sub Say(s$)
  CurHide
  Box 0, sy, W, fh(0) + 8, 1, C_PAGE, C_PAGE
  CurShow
  PText W \ 2, sy + fh(0) \ 2 + 4, Fit$(s$, W - 20), "C", 0, C_AMBER
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x < fx Or x >= fx + fw Or y < fy Then Exit Sub
  r = (y - fy) \ fp
  If r > 4 Or y >= fy + r * fp + fh(0) + 6 Then Exit Sub
  If r = 3 Then
    f$(3) = EditPass$(fx, fy + r * fp, fw, f$(3))
  Else
    f$(r) = Trim$(EditText$(fx, fy + r * fp, fw, f$(r)))
  EndIf
End Sub

Sub SaveMode
  If f$(0) = "" Or f$(2) = "" Then
    Say Choice(sms, "Enter at least the phone's IP and username", "Enter at least a server and email address")
    Exit Sub
  EndIf
  If Val(f$(1)) = 0 Then f$(1) = Choice(sms, "8080", "465")
  If Not sms And Val(f$(1)) = 587 Then f$(1) = "465"
  Open HOME_DIR$ + Choice(sms, "/sms.dat", "/mail.dat") For Output As #1
  Print #1, f$(0) + "|" + f$(1) + "|" + f$(2) + "|" + B64$(f$(3)) + "|" + f$(4)
  Close #1
  DrawForm
  Say "Saved - TEST to check it works"
End Sub

' TEST sends with what's on screen, so it saves first
Sub TestMode
  SaveMode
  If f$(0) = "" Or f$(2) = "" Then Exit Sub
  If sms Then
    If f$(4) = "" Then
      Say "Enter a phone number for TEST first"
      Exit Sub
    EndIf
    Say "Sending a test text to " + f$(4) + " ..."
    e$ = SendSms$(f$(4), "Test from the car club board")
  Else
    Say "Sending a test email ..."
    e$ = SendMail$(Choice(f$(4) = "", f$(2), f$(4)), "Car club test", "This is a test from the car club board.")
  EndIf
  If e$ = "" Then
    Say "Sent - check " + Choice(sms, "the phone", "the inbox")
  Else
    Say "Failed: " + e$
  EndIf
End Sub
