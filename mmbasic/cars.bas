' cars.bas -- CARS page (MEMBERS > LINKS > CARS), ported from club.py's
' cars_page.py: the club's cars on the left (member, name, rego), the
' picked car on the right. Opened from MEMBERS it shows that member's
' cars only (member number handed over in cars.tmp); SHOW ALL lists all.
' Top menu bar: RECORD (NEW/SAVE/DELETE), VIEW (SHOW PIC/SHOW ALL), BACK.
'
' Data: cars.dat, one car per line: id|member number|photo|rego|logbook.
' Photos are in B:/cars; SHOW PIC hands the photo to photos.bas.
'
' Build with: python mmbasic/build.py  (writes ../cars.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXC = 200, NF = 5, ROWS = 13, MAXM2 = 200

Dim string c$(MAXC - 1, NF - 1), f$(NF - 1), who$(MAXC - 1)
Dim string flab$(3), only$, cmd$
' a photo from PHOTOS > USE FOR CAR, waiting for a car to be clicked
Dim string attach$
Dim integer vis(MAXC - 1), count, nvis, top, sel, j, i, v, delArmed
Dim integer lx, ly, lw, rh, fx, fy, fw, fp, bPrev, bNext

CoreInit
v = AddMenu("RECORD", "NEW|SAVE|DELETE")
v = AddMenu("VIEW", "SHOW PIC|SHOW ALL")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "CARS"
Layout
DrawAllBtns
StartCursor
only$ = NetLine$(HOME_DIR$ + "/cars.tmp")
On Error Skip
Kill HOME_DIR$ + "/cars.tmp"
attach$ = NetLine$(HOME_DIR$ + "/carphoto.tmp")
On Error Skip
Kill HOME_DIR$ + "/carphoto.tmp"
LoadData
Filter
sel = -1
If nvis > 0 Then sel = vis(0)
DrawList
If sel >= 0 Then
  ShowRecord sel
Else
  ClearForm
  f$(1) = only$
  DrawForm
EndIf
TickerMsg Str$(nvis) + " car(s)" + Choice(only$ = "", "", " for member " + only$)
If attach$ <> "" Then TickerMsg "Click the car " + attach$ + " is for (or RECORD > NEW, then SAVE)"

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
  If j = -2 Then GoPage "members.bas"
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
  If cmd$ = "HELP" Then HelpFor "cars", "cars.bas"
  Select Case cmd$
    Case "BACK"
      GoPage "members.bas"
    Case "NEW"
      NewRecord
    Case "SAVE"
      SaveRecord
    Case "DELETE"
      DeleteRecord
    Case "SHOW ALL"
      only$ = ""
      top = 0
      Filter
      DrawList
      TickerMsg Str$(nvis) + " cars"
    Case "SHOW PIC"
      If f$(2) = "" Then
        TickerMsg "This car has no photo"
      Else
        Open HOME_DIR$ + "/photo.tmp" For Output As #1
        Print #1, f$(2) + "|cars.bas"
        Close #1
        GoPage "photos.bas"
      EndIf
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, y
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W * 42 \ 100
  ly = H * 17 \ 100
  fx = lx + lw + m * 2 + 80
  fw = W - fx - m
  fy = ly
  fp = fh(0) + 14
  bh2 = H \ 14
  bw2 = (lw - m) \ 2
  y = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, y, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, y, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
  Restore FormLabels
  CurHide
  For i = 0 To 3
    Read flab$(i)
    PText fx - 8, fy + i * fp + (fh(0) + 6) \ 2, flab$(i), "R", 0, C_INK
  Next
  CurShow
End Sub

FormLabels:
Data "Member", "Photo", "Rego", "Logbook"

' the cars, and each one's owner's name from members.dat
Sub LoadData
  Local string l$, mnum$(MAXM2), mnam$(MAXM2)
  Local integer nm2, k
  On Error Skip
  Open "members.dat" For Input As #1
  If MM.Errno = 0 Then
    Do While Not Eof(#1) And nm2 < MAXM2
      Line Input #1, l$
      If l$ <> "" Then
        mnum$(nm2) = Fld$(l$, 1)
        mnam$(nm2) = Fld$(l$, 2)
        nm2 = nm2 + 1
      EndIf
    Loop
    Close #1
  EndIf
  count = 0
  On Error Skip
  Open "cars.dat" For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And count < MAXC
    Line Input #1, l$
    If l$ <> "" Then
      For i = 0 To NF - 1
        c$(count, i) = Fld$(l$, i + 1)
      Next
      who$(count) = ""
      For k = 0 To nm2 - 1
        If mnum$(k) = c$(count, 1) Then who$(count) = mnam$(k)
      Next
      count = count + 1
    EndIf
  Loop
  Close #1
End Sub


Sub SaveData
  Local string l$
  Local integer r, k
  Open "cars.dat" For Output As #1
  For r = 0 To count - 1
    l$ = c$(r, 0)
    For k = 1 To NF - 1
      l$ = l$ + "|" + c$(r, k)
    Next
    Print #1, l$
  Next
  Close #1
End Sub

Sub Filter
  nvis = 0
  For i = 0 To count - 1
    If only$ = "" Or c$(i, 1) = only$ Then
      vis(nvis) = i
      nvis = nvis + 1
    EndIf
  Next
  If top >= nvis Then top = 0
End Sub

Sub DrawList
  Local integer r, y, n
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < nvis Then
      n = vis(top + r)
      y = ly + 3 + r * rh
      If n = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(c$(n, 3) + "  " + c$(n, 1) + " " + who$(n), lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub ShowRecord(r As integer)
  For i = 0 To NF - 1
    f$(i) = c$(r, i)
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
  For i = 0 To 3
    TextBox fx, fy + i * fp, Choice(i = 0, fw \ 3, fw), f$(i + 1), 0
  Next
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < nvis Then
      sel = vis(r)
      DrawList
      If attach$ <> "" Then
        ' PHOTOS > USE FOR CAR: this car gets the photo
        c$(sel, 2) = attach$
        SaveData
        TickerMsg c$(sel, 3) + " now has the photo " + attach$
        attach$ = ""
      EndIf
      ShowRecord sel
      TickerMsg c$(sel, 3) + Choice(who$(sel) = "", "", " - " + who$(sel))
    EndIf
    Exit Sub
  EndIf
  If x >= fx And x < fx + fw And y >= fy Then
    r = (y - fy) \ fp
    If r <= 3 And y < fy + r * fp + fh(0) + 6 Then
      f$(r + 1) = Trim$(EditText$(fx, fy + r * fp, Choice(r = 0, fw \ 3, fw), f$(r + 1)))
    EndIf
  EndIf
End Sub

Sub NewRecord
  Local integer hi
  For i = 0 To count - 1
    hi = Max(hi, Val(c$(i, 0)))
  Next
  ClearForm
  f$(0) = Str$(hi + 1)
  f$(1) = only$
  sel = -1
  DrawForm
  DrawList
  TickerMsg "New car - fill in, then SAVE"
End Sub

Sub SaveRecord
  Local integer r
  If attach$ <> "" And f$(2) = "" Then
    f$(2) = attach$
    attach$ = ""
  EndIf
  If f$(3) = "" And f$(1) = "" Then
    TickerMsg "Needs a member number or a rego"
    Exit Sub
  EndIf
  If f$(0) = "" Then NewId
  r = -1
  For i = 0 To count - 1
    If c$(i, 0) = f$(0) Then r = i
  Next
  If r < 0 Then
    If count >= MAXC Then
      TickerMsg "Car list is full"
      Exit Sub
    EndIf
    r = count
    count = count + 1
  EndIf
  For i = 0 To NF - 1
    c$(r, i) = f$(i)
  Next
  SaveData
  LoadData
  sel = r
  Filter
  DrawList
  TickerMsg "Saved " + f$(3)
End Sub

Sub NewId
  Local integer hi
  For i = 0 To count - 1
    hi = Max(hi, Val(c$(i, 0)))
  Next
  f$(0) = Str$(hi + 1)
End Sub

Sub DeleteRecord
  Local integer r, k
  If sel < 0 Then
    TickerMsg "Pick a car first"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE again to remove " + c$(sel, 3)
    Exit Sub
  EndIf
  delArmed = 0
  TickerMsg "Deleted " + c$(sel, 3)
  For r = sel To count - 2
    For k = 0 To NF - 1
      c$(r, k) = c$(r + 1, k)
    Next
    who$(r) = who$(r + 1)
  Next
  count = count - 1
  SaveData
  sel = -1
  Filter
  DrawList
  ClearForm
End Sub
