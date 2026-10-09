' members.bas -- MEMBERS page for the car club (MMBasic), ported from
' club.py's members_page.py: member list with Find on the left, the
' selected member's details on the right, and club.py's top menu bar:
' RECORD (NEW/SAVE/CLEAR/DELETE), LIST (SEARCH/SHOW ALL), LINKS, MENU.
'
' Data: members.dat on A:, one member per line, fields separated by "|"
' in the club.py column order: number|name|email|phone|status|financial|
' role|notes|visited|logbook|address. Made from the club workbook by
' mmbasic/export_workbook.py.
'
' Click a name to show it, click a box on the right to type into it
' (Enter or a click keeps it, Esc undoes), SAVE writes the file.
'
' Build with: python mmbasic/build.py  (writes ../members.bas)

Option EXPLICIT
Option DEFAULT NONE

Const DATA_FILE$ = "members.dat"
Const MAXM = 200, NF = 11, ROWS = 13

' the form's boxes: label and which data column each one edits
Dim string flab$(9)
Dim integer fcol(9)
Dim string m$(MAXM - 1, NF - 1)
Dim string f$(NF - 1)
Dim integer vis(MAXM - 1)
Dim integer count, nvis, top, sel, j, i, delArmed
Dim integer lx, ly, lw, rh, fx, fy, fw, fp
Dim integer bPrev, bNext, v
Dim string cmd$
Dim string find$

CoreInit
v = AddMenu("RECORD", "NEW|SAVE|CLEAR|DELETE")
v = AddMenu("LIST", "SEARCH|SHOW ALL|REFRESH|CHECK IN")
v = AddMenu("LINKS", "CARS|PHOTO|EMAIL")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "MEMBERS"
Layout
DrawAllBtns
StartCursor
LoadData
Filter
DrawList
If nvis > 0 Then
  sel = vis(0)
  ShowRecord sel
Else
  ClearForm
EndIf
TickerMsg Str$(count) + " members"

Do
  j = PollInput()
  ' wheel, drag and keys on the list (core ListNav): the arrows pick a row
  ' as a click would, Enter clicks it again
  v = ListNav(lx, ly, lw, rh, ROWS, nvis, top)
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
  If j = bNext And top + ROWS < nvis Then
    top = top + ROWS
    DrawList
  EndIf
  cmd$ = ""
  If j >= 0 And j <> bPrev And j <> bNext Then cmd$ = Command$(j)
  If cmd$ = "HELP" Then HelpFor "members", "members.bas"
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
    Case "SEARCH"
      Clicked lx + 50, ly - rh - 6
    Case "SHOW ALL"
      find$ = ""
      TextBox lx + 44, ly - rh - 6 - (fh(0) + 6) \ 2, lw - 44, "", 0
      top = 0
      Filter
      DrawList
      TickerMsg Str$(nvis) + " members"
    Case "REFRESH"
      LoadData
      Filter
      DrawList
      TickerMsg Str$(count) + " members"
    Case "CHECK IN"
      CheckIn
    Case "CARS"
      ' CARS shows this member's cars
      Open HOME_DIR$ + "/cars.tmp" For Output As #1
      Print #1, f$(0)
      Close #1
      GoPage "cars.bas"
    Case "PHOTO"
      GoPage "photos.bas"
    Case "EMAIL"
      GoPage "message.bas"
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  Pause 10
Loop
Sub Layout
  Local integer m, bw2, bh2, y
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W * 34 \ 100
  ly = H * 17 \ 100
  fx = lx + lw + m * 2 + 70
  fw = W - fx - m
  fy = H * 11 \ 100
  fp = fh(0) + 11
  bh2 = H \ 14
  bw2 = (lw - m) \ 2
  y = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, y, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, y, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
  Restore FormFields
  For i = 0 To 9
    Read flab$(i), fcol(i)
  Next
  CurHide
  PText lx, ly - rh - 6, "Find", "L", 0, C_INK
  For i = 0 To 9
    PText fx - 8, fy + i * fp + (fh(0) + 6) \ 2, flab$(i), "R", 0, C_INK
  Next
  CurShow
  TextBox lx + 44, ly - rh - 6 - (fh(0) + 6) \ 2, lw - 44, "", 0
End Sub

FormFields:
Data "No", 0, "Name", 1, "Email", 2, "Phone", 3, "Status", 4
Data "Paid", 5, "Role", 6, "Logbook", 9, "Address", 10, "Notes", 7

Sub LoadData
  Local string l$
  count = 0
  On Error Skip
  Open DATA_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And count < MAXM
    Line Input #1, l$
    If l$ <> "" Then
      For i = 0 To NF - 1
        m$(count, i) = Fld$(l$, i + 1)
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
    l$ = m$(r, 0)
    For c = 1 To NF - 1
      l$ = l$ + "|" + m$(r, c)
    Next
    Print #1, l$
  Next
  Close #1
End Sub

' the members whose name, number or phone contains find$
Sub Filter
  Local string u$
  nvis = 0
  u$ = UCase$(find$)
  For i = 0 To count - 1
    If u$ = "" Or Instr(UCase$(m$(i, 1)), u$) Or Instr(m$(i, 0), u$) Or Instr(m$(i, 3), u$) Then
      vis(nvis) = i
      nvis = nvis + 1
    EndIf
  Next
  If top >= nvis Then top = 0
End Sub

Sub DrawList
  Local integer r, y
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < nvis Then
      y = ly + 3 + r * rh
      If vis(top + r) = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(m$(vis(top + r), 0) + "  " + m$(vis(top + r), 1), lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub ShowRecord(r As integer)
  For i = 0 To NF - 1
    f$(i) = m$(r, i)
  Next
  DrawForm
End Sub

Sub ClearForm
  For i = 0 To NF - 1
    f$(i) = ""
  Next
  DrawForm
End Sub

Sub DrawForm
  For i = 0 To 9
    TextBox fx, fy + i * fp, fw, f$(fcol(i)), 0
  Next
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  ' a name in the list
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < nvis Then
      sel = vis(r)
      DrawList
      ShowRecord sel
      TickerMsg m$(sel, 1)
    EndIf
    Exit Sub
  EndIf
  ' the Find box
  If x >= lx + 44 And y >= ly - rh - 6 - (fh(0) + 6) \ 2 And y < ly - rh - 6 + (fh(0) + 6) \ 2 Then
    find$ = EditText$(lx + 44, ly - rh - 6 - (fh(0) + 6) \ 2, lw - 44, find$)
    top = 0
    Filter
    DrawList
    TickerMsg Str$(nvis) + " found"
    Exit Sub
  EndIf
  ' a box on the form
  If x >= fx And x < fx + fw And y >= fy Then
    r = (y - fy) \ fp
    If r <= 9 And y < fy + r * fp + fh(0) + 6 Then
      f$(fcol(r)) = EditText$(fx, fy + r * fp, fw, f$(fcol(r)))
    EndIf
  EndIf
End Sub

Sub NewRecord
  Local integer hi
  For i = 0 To count - 1
    hi = Max(hi, Val(m$(i, 0)))
  Next
  ClearForm
  f$(0) = Str$(hi + 1)
  f$(4) = "Active"
  f$(5) = "No"
  sel = -1
  DrawForm
  DrawList
  TickerMsg "New member - fill in, then SAVE"
End Sub

' writes the form back over the member with the same number, or adds it
Sub SaveRecord
  Local integer r
  If f$(1) = "" Then
    TickerMsg "Needs a name first"
    Exit Sub
  EndIf
  r = -1
  For i = 0 To count - 1
    If m$(i, 0) = f$(0) Then r = i
  Next
  If r < 0 Then
    If count >= MAXM Then
      TickerMsg "Member list is full"
      Exit Sub
    EndIf
    r = count
    count = count + 1
  EndIf
  For i = 0 To NF - 1
    m$(r, i) = f$(i)
  Next
  SaveData
  sel = r
  Filter
  DrawList
  TickerMsg "Saved " + f$(1)
End Sub

' needs two presses, so one stray click can't delete a member
Sub DeleteRecord
  Local integer r
  If sel < 0 Then
    TickerMsg "Pick a member first"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE again to remove " + m$(sel, 1)
    Exit Sub
  EndIf
  delArmed = 0
  TickerMsg "Deleted " + m$(sel, 1)
  For r = sel To count - 2
    For i = 0 To NF - 1
      m$(r, i) = m$(r + 1, i)
    Next
  Next
  count = count - 1
  SaveData
  sel = -1
  Filter
  DrawList
  ClearForm
End Sub

' check the member shown in to the event that's running (EVENTS > START):
' a line "eventkey|member|HH:MM" in attend.dat, once per member per event
Sub CheckIn
  Local string a$, l$, t$
  Local integer c, already
  If f$(0) = "" Or f$(1) = "" Then
    TickerMsg "Pick a member first"
    Exit Sub
  EndIf
  a$ = NetLine$(HOME_DIR$ + "/active.dat")
  If a$ = "" Then
    TickerMsg "No event is running - EVENTS > ACTIONS > START first"
    Exit Sub
  EndIf
  On Error Skip
  Open "attend.dat" For Input As #1
  If MM.Errno = 0 Then
    Do While Not Eof(#1)
      Line Input #1, l$
      If Fld$(l$, 1) = a$ Then
        c = c + 1
        If Fld$(l$, 2) = f$(0) Then
          already = 1
          t$ = Fld$(l$, 3)
        EndIf
      EndIf
    Loop
    Close #1
  EndIf
  If already Then
    TickerMsg f$(1) + " is already checked in (at " + t$ + ")"
    Exit Sub
  EndIf
  t$ = Left$(Time$, 5)
  Open "attend.dat" For Append As #1
  Print #1, a$ + "|" + f$(0) + "|" + t$
  Close #1
  TickerMsg "Checked in " + f$(1) + " at " + t$ + "  (" + Str$(c + 1) + " here)"
End Sub
