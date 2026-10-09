' events.bas -- EVENTS page for the car club (MMBasic), ported from
' club.py's events_page.py: event list on the left, the selected event's
' details on the right, and the top menu bar: EVENT (NEW/SAVE/CLEAR/
' DELETE), ACTIONS (START/STOP/WHO CAME/GET GPS/PHOTO/MESSAGE), MENU.
'
' Data on A:, "|"-separated like members.dat:
'   events.dat  key|name|date|time|place|notes|photo|lat|lon (key is the
'               date, as club.py used it; photo/lat/lon added 2026-09-25,
'               older lines just read them as blank)
'   attend.dat  eventkey|member number|time      (who checked in)
'   active.dat  the key of the event that's running, if any
'
' Build with: python mmbasic/build.py  (writes ../events.bas)

Option EXPLICIT
Option DEFAULT NONE

Const DATA_FILE$ = "events.dat", ATTEND_FILE$ = "attend.dat", ACTIVE_FILE$ = "active.dat"
Const MAXE = 100, NF = 9, ROWS = 13

Dim string flab$(4)
Dim integer fcol(4)
Dim string e$(MAXE - 1, NF - 1)
Dim string f$(NF - 1)
Dim integer count, top, sel, j, i, v, delArmed
Dim integer lx, ly, lw, rh, fx, fy, fw, fp, bPrev, bNext
Dim string cmd$, active$

CoreInit
v = AddMenu("EVENT", "NEW|SAVE|CLEAR|DELETE")
v = AddMenu("ACTIONS", "START|STOP|WHO CAME|GET GPS|SHOW PHOTO|SET PHOTO|MESSAGE")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "EVENTS"
Layout
DrawAllBtns
StartCursor
LoadData
active$ = ReadActive$()
sel = -1
If count > 0 Then sel = 0
DrawList
If sel >= 0 Then
  ShowRecord sel
Else
  ClearForm
EndIf
TickerMsg Str$(count) + " events"

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
  If cmd$ = "HELP" Then HelpFor "events", "events.bas"
  Select Case cmd$
    Case "MENU"
      GoPage "club.bas"
    Case "NEW"
      NewRecord
    Case "SAVE"
      SaveRecord
    Case "CLEAR"
      ClearForm
    Case "DELETE"
      DeleteRecord
    Case "START"
      StartEvent
    Case "STOP"
      StopEvent
    Case "WHO CAME"
      WhoCame
    Case "GET GPS"
      EventGps
    Case "SHOW PHOTO"
      ShowPhoto
    Case "SET PHOTO"
      SetPhoto
    Case "MESSAGE"
      MessageCame
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, y
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W * 38 \ 100
  ly = H * 13 \ 100
  fx = lx + lw + m * 2 + 50
  fw = W - fx - m
  fy = H * 13 \ 100
  fp = fh(0) + 14
  bh2 = H \ 14
  bw2 = (lw - m) \ 2
  y = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, y, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, y, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
  Restore FormFields
  For i = 0 To 4
    Read flab$(i), fcol(i)
  Next
  CurHide
  For i = 0 To 4
    PText fx - 8, fy + i * fp + (fh(0) + 6) \ 2, flab$(i), "R", 0, C_INK
  Next
  CurShow
End Sub

FormFields:
Data "Name", 1, "Date", 2, "Time", 3, "Place", 4, "Notes", 5

Sub LoadData
  Local string l$
  count = 0
  On Error Skip
  Open DATA_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And count < MAXE
    Line Input #1, l$
    If l$ <> "" Then
      For i = 0 To NF - 1
        e$(count, i) = Fld$(l$, i + 1)
      Next
      count = count + 1
    EndIf
  Loop
  Close #1
End Sub

Sub SaveData
  Local string l$
  Local integer r, c
  Open DATA_FILE$ For Output As #1
  For r = 0 To count - 1
    l$ = e$(r, 0)
    For c = 1 To NF - 1
      l$ = l$ + "|" + e$(r, c)
    Next
    Print #1, l$
  Next
  Close #1
End Sub

Function ReadActive$()
  Local string l$
  On Error Skip
  Open ACTIVE_FILE$ For Input As #1
  If MM.Errno Then Exit Function
  If Not Eof(#1) Then Line Input #1, l$
  Close #1
  ReadActive$ = l$
End Function

Sub DrawList
  Local integer r, y
  Local string t$
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      t$ = DDate$(e$(top + r, 2)) + "  " + e$(top + r, 1)
      If e$(top + r, 0) = active$ And active$ <> "" Then t$ = "* " + t$
      PText lx + 8, y + rh \ 2, Fit$(t$, lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub ShowRecord(r As integer)
  For i = 0 To NF - 1
    f$(i) = e$(r, i)
  Next
  f$(2) = DDate$(f$(2))
  DrawForm
End Sub

Sub ClearForm
  For i = 0 To NF - 1
    f$(i) = ""
  Next
  DrawForm
End Sub

Sub DrawForm
  For i = 0 To 4
    TextBox fx, fy + i * fp, fw, f$(fcol(i)), 0
  Next
  CurHide
  Box fx, fy + 5 * fp + 4, fw, fh(0), 1, C_PAGE, C_PAGE
  If f$(0) <> "" And f$(0) = active$ Then PText fx, fy + 5 * fp + 4 + fh(0) \ 2, "RUNNING NOW", "L", 0, C_GRN_TOP
  CurShow
  PField fx, fy + 6 * fp, fw, Fit$(Choice(f$(6) = "", "No photo", "Photo: " + f$(6)) + Choice(f$(7) = "", "", "   GPS " + f$(7) + ", " + f$(8)), fw - 8), 0
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      sel = r
      DrawList
      ShowRecord sel
      TickerMsg e$(sel, 1)
    EndIf
    Exit Sub
  EndIf
  If x >= fx And x < fx + fw And y >= fy Then
    r = (y - fy) \ fp
    If r <= 4 And y < fy + r * fp + fh(0) + 6 Then
      f$(fcol(r)) = EditText$(fx, fy + r * fp, fw, f$(fcol(r)))
    EndIf
  EndIf
End Sub

Sub NewRecord
  ClearForm
  f$(2) = DDate$(Date$)
  f$(3) = Left$(Time$, 5)
  sel = -1
  DrawForm
  DrawList
  TickerMsg "New event - fill in, then SAVE"
End Sub

' the key is the date, as in club.py; a second event on the same date
' gets "-2", "-3" ... on its key so both keep their own check-ins
Sub SaveRecord
  Local integer r, n
  Local string k$
  If f$(1) = "" Or f$(2) = "" Then
    TickerMsg "Needs a name and a date"
    Exit Sub
  EndIf
  f$(2) = IsoDate$(f$(2))
  r = sel
  If r < 0 Then
    If count >= MAXE Then
      TickerMsg "Event list is full"
      Exit Sub
    EndIf
    k$ = f$(2)
    n = 1
    Do
      v = 0
      For i = 0 To count - 1
        If e$(i, 0) = k$ Then v = 1
      Next
      If v = 0 Then Exit Do
      n = n + 1
      k$ = f$(2) + "-" + Str$(n)
    Loop
    f$(0) = k$
    r = count
    count = count + 1
  EndIf
  For i = 0 To NF - 1
    e$(r, i) = f$(i)
  Next
  SaveData
  sel = r
  DrawList
  f$(2) = DDate$(f$(2))
  DrawForm
  TickerMsg "Saved " + f$(1)
End Sub

Sub DeleteRecord
  Local integer r
  If sel < 0 Then
    TickerMsg "Pick an event first"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE again to remove " + e$(sel, 1)
    Exit Sub
  EndIf
  delArmed = 0
  TickerMsg "Deleted " + e$(sel, 1)
  For r = sel To count - 2
    For i = 0 To NF - 1
      e$(r, i) = e$(r + 1, i)
    Next
  Next
  count = count - 1
  SaveData
  sel = -1
  DrawList
  ClearForm
End Sub

' the running event is the one MEMBERS' CHECK IN records against
Sub StartEvent
  If sel < 0 Then
    TickerMsg "Pick an event first"
    Exit Sub
  EndIf
  Open ACTIVE_FILE$ For Output As #1
  Print #1, e$(sel, 0)
  Close #1
  active$ = e$(sel, 0)
  DrawList
  DrawForm
  TickerMsg e$(sel, 1) + " is running"
End Sub

Sub StopEvent
  Open ACTIVE_FILE$ For Output As #1
  Close #1
  active$ = ""
  DrawList
  DrawForm
  TickerMsg "No event running"
End Sub

' names of the members checked in to the selected event, in the ticker
Sub WhoCame
  Local string l$, who$, n$
  Local integer c
  If sel < 0 Then
    TickerMsg "Pick an event first"
    Exit Sub
  EndIf
  On Error Skip
  Open ATTEND_FILE$ For Input As #1
  If MM.Errno = 0 Then
    Do While Not Eof(#1)
      Line Input #1, l$
      If Fld$(l$, 1) = e$(sel, 0) Then
        c = c + 1
        n$ = MemberName$(Fld$(l$, 2))
        If Len(who$) + Len(n$) < 200 Then who$ = who$ + ", " + n$
      EndIf
    Loop
    Close #1
  EndIf
  If c = 0 Then
    TickerMsg "Nobody checked in to " + e$(sel, 1) + " yet"
  Else
    TickerMsg Str$(c) + " came: " + Mid$(who$, 3)
  EndIf
End Sub

Function MemberName$(num$)
  Local string l$
  MemberName$ = "#" + num$
  On Error Skip
  Open "members.dat" For Input As #2
  If MM.Errno Then Exit Function
  Do While Not Eof(#2)
    Line Input #2, l$
    If Fld$(l$, 1) = num$ Then
      MemberName$ = Fld$(l$, 2)
      Exit Do
    EndIf
  Loop
  Close #2
End Function

' --- GPS, photo, message (club.py's events_page.py) ----------------------
Function NeedEvent() As integer
  If sel < 0 Then
    TickerMsg "Pick an event first"
    Exit Function
  EndIf
  NeedEvent = 1
End Function

' where the event is: this board's last GPS fix (the GPS page keeps it)
Sub EventGps
  Local string l$
  If Not NeedEvent() Then Exit Sub
  l$ = NetLine$(HOME_DIR$ + "/lastfix.dat")
  If l$ = "" Then
    TickerMsg "No GPS fix on this board yet - open GPS first (it needs open sky)"
    Exit Sub
  EndIf
  e$(sel, 7) = Fld$(l$, 1)
  e$(sel, 8) = Fld$(l$, 2)
  f$(7) = e$(sel, 7)
  f$(8) = e$(sel, 8)
  SaveData
  DrawForm
  TickerMsg e$(sel, 1) + " is at " + e$(sel, 7) + ", " + e$(sel, 8)
End Sub

Sub ShowPhoto
  If Not NeedEvent() Then Exit Sub
  If e$(sel, 6) = "" Then
    TickerMsg "No photo for this event yet - ACTIONS > SET PHOTO"
    Exit Sub
  EndIf
  Open HOME_DIR$ + "/photo.tmp" For Output As #1
  Print #1, e$(sel, 6) + "|events.bas"
  Close #1
  GoPage "photos.bas"
End Sub

Sub SetPhoto
  Local string p$
  If Not NeedEvent() Then Exit Sub
  p$ = PickPhoto$()
  DrawList
  DrawForm
  If p$ = "" Then Exit Sub
  e$(sel, 6) = p$
  f$(6) = p$
  SaveData
  DrawForm
  TickerMsg e$(sel, 1) + " - photo " + p$
End Sub

' a list of the pictures in B:/cars to click (Esc or a click outside cancels)
Function PickPhoto$()
  Local string pn$(99), d$, t$
  Local integer n, i, top2, rows2, x, y, wd, rh2, r
  d$ = Dir$("B:/cars/*", FILE)
  Do While d$ <> "" And n < 100
    t$ = UCase$(Right$(d$, 4))
    If t$ = ".JPG" Or t$ = "JPEG" Or t$ = ".BMP" Then
      pn$(n) = d$
      n = n + 1
    EndIf
    d$ = Dir$()
  Loop
  If n = 0 Then
    TickerMsg "No photos in B:/cars - add some with FILE TRANSFER > IMPORT"
    Exit Function
  EndIf
  If n > 1 Then Sort pn$(), , 1, 0, n
  rh2 = fh(0) + 8
  rows2 = 10
  wd = W * 3 \ 5
  x = (W - wd) \ 2
  y = H * 15 \ 100
  Do
    CurHide
    RBox x, y, wd, (rows2 + 2) * rh2 + 10, 6, C_INK, C_BAR
    CurShow
    PText x + wd \ 2, y + rh2 \ 2 + 4, "Pick the event's photo", "C", 0, C_AMBER
    For i = 0 To rows2 - 1
      If top2 + i < n Then PText x + 14, y + 6 + (i + 1) * rh2 + rh2 \ 2, Fit$(pn$(top2 + i), wd - 28), "L", 0, C_INK
    Next
    PText x + 14, y + 6 + (rows2 + 1) * rh2 + rh2 \ 2, Choice(top2 + rows2 < n, "More...", ""), "L", 0, C_AMBER
    PText x + wd - 14, y + 6 + (rows2 + 1) * rh2 + rh2 \ 2, "Cancel", "R", 0, C_AMBER
    Do
      If Inkey$ = Chr$(27) Then Exit Function
      TickerTick
      Pause 10
    Loop Until ClickAt()
    If clickX < x Or clickX >= x + wd Or clickY < y + 6 + rh2 Then Exit Function
    r = (clickY - y - 6) \ rh2 - 1
    If r >= 0 And r < rows2 Then
      If top2 + r < n Then
        PickPhoto$ = pn$(top2 + r)
        Exit Function
      EndIf
    ElseIf r = rows2 Then
      If clickX >= x + wd \ 2 Then Exit Function
      top2 = Choice(top2 + rows2 < n, top2 + rows2, 0)
    Else
      Exit Function
    EndIf
  Loop
End Function

' EMAIL/TXT with everyone who checked in to this event ticked, and the
' event's name as the subject (handed over in message.tmp)
Sub MessageCame
  Local string l$, nums$
  Local integer c
  If Not NeedEvent() Then Exit Sub
  On Error Skip
  Open ATTEND_FILE$ For Input As #1
  If MM.Errno = 0 Then
    Do While Not Eof(#1)
      Line Input #1, l$
      If Fld$(l$, 1) = e$(sel, 0) And Len(nums$) < 240 Then
        nums$ = nums$ + Fld$(l$, 2) + ","
        c = c + 1
      EndIf
    Loop
    Close #1
  EndIf
  If c = 0 Then
    TickerMsg "Nobody checked in to " + e$(sel, 1) + " yet - check members in from MEMBERS"
    Exit Sub
  EndIf
  Open HOME_DIR$ + "/message.tmp" For Output As #1
  Print #1, e$(sel, 1)
  Print #1, nums$
  Close #1
  GoPage "message.bas"
End Sub
