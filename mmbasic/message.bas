' message.bas -- EMAIL/TXT page (main menu), ported from club.py's
' mass_message_page.py: send one message to members by email and/or text.
' Left: who (ALL members or the ones TICKED in the list), PAID ONLY,
' EMAIL on/off, SMS on/off, Subject and a 4-line Message. Right: the
' member list, click a name to tick/untick it.
' Top menu bar: SEND, CLEAR, MENU. Click a box to type or toggle it.
'
' Sends with MAIL SETUP's settings (net.inc). Members come from
' members.dat (number|name|email|phone|status|financial|...).
'
' Build with: python mmbasic/build.py  (writes ../message.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXM = 200, ROWS = 15, NLINES = 4

Dim string mn$(MAXM - 1), me$(MAXM - 1), mp$(MAXM - 1), mf$(MAXM - 1), mnum$(MAXM - 1)
Dim integer tick(MAXM - 1)
Dim string subj$, ln$(NLINES - 1), cmd$
Dim integer count, top, j, v, i, sendArmed
Dim integer toAll, paidOnly, useMail, useSms
Dim integer lx, ly, lw, rh, fx, fy, fw, fp, bPrev, bNext

CoreInit
v = AddMenu("SEND", "")
v = AddMenu("CLEAR", "")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "EMAIL/TXT"
rh = fh(0) + 5
fx = W \ 40
fw = W * 48 \ 100
fy = H * 16 \ 100
fp = fh(0) + 12
lx = fx + fw + W \ 30
lw = W - lx - W \ 40
ly = fy
bPrev = AddBtn("PREV", lx, ly + ROWS * rh + 10, (lw - 8) \ 2, H \ 16, 0)
bNext = AddBtn("NEXT", lx + (lw + 8) \ 2, ly + ROWS * rh + 10, (lw - 8) \ 2, H \ 16, 0)
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
DrawAllBtns
StartCursor
LoadMembers
toAll = 1
useMail = 1
useSms = 1
FromEvent
DrawForm
DrawList
If Not toAll Then
  TickerMsg "Everyone who came is ticked - type the message, then SEND"
Else
  TickerMsg Str$(count) + " members - fill in the message, then SEND"
EndIf

Do
  j = PollInput()
  ' wheel, drag and keys on the list (core ListNav): the arrows pick a row
  ' as a click would, Enter clicks it again
  v = ListNav(lx, ly, lw, rh, ROWS, count, top)
  If v = 1 Then DrawList
  ' here a click ticks/unticks, so the arrows only move an amber frame and
  ' Enter does the ticking
  If v >= 2 Then DrawList
  If v = 3 Then Clicked lx + 8, ly + 3 + (kbRow - top) * rh + rh \ 2
  If v >= 2 And kbRow >= top And kbRow < top + ROWS Then
    CurHide
    Box lx + 2, ly + 3 + (kbRow - top) * rh, lw - 4, rh, 1, C_AMBER
    CurShow
  EndIf
  If j = -2 Then GoPage "club.bas"
  If j = -3 Then Clicked clickX, clickY
  If j = bPrev And top > 0 Then
    top = Max(0, top - ROWS)
    DrawList
  EndIf
  If j = bNext And top + ROWS < count Then
    top = top + ROWS
    DrawList
  EndIf
  cmd$ = ""
  If j >= 0 And j <> bPrev And j <> bNext Then cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "message", "message.bas"
  Select Case cmd$
    Case "MENU"
      GoPage "club.bas"
    Case "CLEAR"
      subj$ = ""
      For i = 0 To NLINES - 1
        ln$(i) = ""
      Next
      For i = 0 To count - 1
        tick(i) = 0
      Next
      DrawForm
      DrawList
    Case "SEND"
      SendAll
  End Select
  If cmd$ <> "SEND" And j <> -1 Then sendArmed = 0
  Pause 10
Loop

Sub LoadMembers
  Local string l$
  count = 0
  On Error Skip
  Open "members.dat" For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And count < MAXM
    Line Input #1, l$
    If l$ <> "" Then
      mnum$(count) = Fld$(l$, 1)
      mn$(count) = Fld$(l$, 2)
      me$(count) = Fld$(l$, 3)
      mp$(count) = Fld$(l$, 4)
      mf$(count) = Fld$(l$, 6)
      count = count + 1
    EndIf
  Loop
  Close #1
End Sub

' form rows: 0 who, 1 paid only, 2 email, 3 sms, 4 subject, 5.. message
Sub DrawForm
  Local integer y
  y = fy
  TextBox fx, y, fw, "Send to: " + Choice(toAll, "ALL MEMBERS", "TICKED ONLY"), 0
  TextBox fx, y + fp, fw, "Paid only: " + Choice(paidOnly, "YES", "NO"), 0
  TextBox fx, y + 2 * fp, fw \ 2 - 4, "EMAIL " + Choice(useMail, "ON", "OFF"), 0
  TextBox fx + fw \ 2 + 4, y + 2 * fp, fw \ 2 - 4, "SMS " + Choice(useSms, "ON", "OFF"), 0
  PText fx, y + 3 * fp + fh(0) \ 2, "Subject", "L", 0, C_INK
  TextBox fx, y + 3 * fp + fh(0) + 2, fw, subj$, 0
  PText fx, y + 4 * fp + fh(0) + 2 + fh(0) \ 2, "Message", "L", 0, C_INK
  For i = 0 To NLINES - 1
    TextBox fx, MsgY(i), fw, ln$(i), 0
  Next
End Sub

Function MsgY(n As integer) As integer
  MsgY = fy + 4 * fp + 2 * fh(0) + 6 + n * (fh(0) + 8)
End Function

Sub DrawList
  Local integer r, y
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If tick(top + r) Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(Choice(tick(top + r), "[x] ", "[ ] ") + mn$(top + r), lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      tick(r) = Not tick(r)
      If tick(r) Then toAll = 0
      DrawList
      DrawForm
    EndIf
    Exit Sub
  EndIf
  If x < fx Or x >= fx + fw Then Exit Sub
  If y >= fy And y < fy + fh(0) + 6 Then
    toAll = Not toAll
  ElseIf y >= fy + fp And y < fy + fp + fh(0) + 6 Then
    paidOnly = Not paidOnly
  ElseIf y >= fy + 2 * fp And y < fy + 2 * fp + fh(0) + 6 Then
    If x < fx + fw \ 2 Then
      useMail = Not useMail
    Else
      useSms = Not useSms
    EndIf
  ElseIf y >= fy + 3 * fp + fh(0) + 2 And y < fy + 3 * fp + 2 * fh(0) + 8 Then
    subj$ = EditText$(fx, fy + 3 * fp + fh(0) + 2, fw, subj$)
  Else
    For r = 0 To NLINES - 1
      If y >= MsgY(r) And y < MsgY(r) + fh(0) + 6 Then ln$(r) = EditText$(fx, MsgY(r), fw, ln$(r))
    Next
  EndIf
  DrawForm
End Sub

Function Wanted(n As integer) As integer
  If Not toAll And Not tick(n) Then Exit Function
  If paidOnly And LCase$(Left$(mf$(n), 1)) <> "y" Then Exit Function
  Wanted = 1
End Function

' the message lines joined with "~" (net.inc's line break)
Function Body$()
  Local integer last
  last = -1
  For i = 0 To NLINES - 1
    If ln$(i) <> "" Then last = i
  Next
  For i = 0 To last
    Body$ = Body$ + ln$(i) + Choice(i < last, "~", "")
  Next
End Function

' two presses: the first says how many will get it
Sub SendAll
  Local integer n, okM, okS, bad
  Local string b$, e$
  b$ = Body$()
  If b$ = "" Then
    TickerMsg "Type a message first"
    Exit Sub
  EndIf
  If Not useMail And Not useSms Then
    TickerMsg "Turn EMAIL or SMS on"
    Exit Sub
  EndIf
  For i = 0 To count - 1
    If Wanted(i) Then n = n + 1
  Next
  If n = 0 Then
    TickerMsg "Nobody to send to - tick members or choose ALL"
    Exit Sub
  EndIf
  If Not sendArmed Then
    sendArmed = 1
    TickerMsg "Press SEND again to send to " + Str$(n) + " member(s)"
    Exit Sub
  EndIf
  sendArmed = 0
  For i = 0 To count - 1
    If Wanted(i) Then
      If useMail And Instr(me$(i), "@") Then
        TickerMsg "Emailing " + mn$(i) + " ..."
        e$ = SendMail$(me$(i), Choice(subj$ = "", "Car club", subj$), b$)
        If e$ = "" Then
          okM = okM + 1
        Else
          bad = bad + 1
        EndIf
      EndIf
      If useSms And mp$(i) <> "" Then
        TickerMsg "Texting " + mn$(i) + " ..."
        e$ = SendSms$(mp$(i), Choice(subj$ = "", "", subj$ + ": ") + b$)
        If e$ = "" Then
          okS = okS + 1
        Else
          bad = bad + 1
        EndIf
      EndIf
    EndIf
  Next
  TickerMsg "Sent " + Str$(okM) + " email(s), " + Str$(okS) + " text(s)" + Choice(bad, ", " + Str$(bad) + " failed (last: " + e$ + ")", "")
End Sub

' EVENTS > MESSAGE hands over the event's name and who checked in, in
' message.tmp: tick them, and use the name as the subject
Sub FromEvent
  Local string t$, nums$
  Local integer i
  t$ = NetLine$(HOME_DIR$ + "/message.tmp")
  If t$ = "" Then Exit Sub
  Open HOME_DIR$ + "/message.tmp" For Input As #1
  Line Input #1, t$
  If Not Eof(#1) Then Line Input #1, nums$
  Close #1
  On Error Skip
  Kill HOME_DIR$ + "/message.tmp"
  subj$ = Left$(t$, 60)
  For i = 0 To count - 1
    If Instr("," + nums$, "," + mnum$(i) + ",") Then tick(i) = 1
  Next
  toAll = 0
End Sub
