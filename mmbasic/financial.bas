' financial.bas -- FINANCIAL page for the car club (MMBasic), ported from
' club.py's financial_page.py: entries on the left, the selected entry's
' details on the right with the income/expense/net totals under them, and
' the top menu bar: RECORD (NEW/SAVE/CLEAR/DELETE), EXPORT (EXPORT CSV),
' MENU. Click Type to flip it between Income and Expense.
'
' Data: finance.dat on A:, "|"-separated like members.dat:
'   id|date|descr|category|kind|amount|notes
'
' Build with: python mmbasic/build.py  (writes ../financial.bas)

Option EXPLICIT
Option DEFAULT NONE

Const DATA_FILE$ = "finance.dat", CSV_FILE$ = "finance.csv"
Const MAXF = 300, NF = 7, ROWS = 13, KIND_BOX = 4

Dim string flab$(6)
Dim integer fcol(6)
Dim string d$(MAXF - 1, NF - 1)
Dim string f$(NF - 1)
Dim integer count, top, sel, j, i, v, delArmed
Dim integer lx, ly, lw, rh, fx, fy, fw, fp, ty, bPrev, bNext
Dim string cmd$

CoreInit
v = AddMenu("RECORD", "NEW|SAVE|CLEAR|DELETE")
v = AddMenu("EXPORT", "EXPORT CSV")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "FINANCIAL"
Layout
DrawAllBtns
StartCursor
LoadData
sel = -1
If count > 0 Then sel = 0
DrawList
If sel >= 0 Then
  ShowRecord sel
Else
  ClearForm
EndIf
DrawTotals
TickerMsg Str$(count) + " entries"

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
  If cmd$ = "HELP" Then HelpFor "financial", "financial.bas"
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
    Case "EXPORT CSV"
      ExportCsv
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, y
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W * 44 \ 100
  ly = H * 13 \ 100
  fx = lx + lw + m * 2 + 78
  fw = W - fx - m
  fy = H * 13 \ 100
  fp = fh(0) + 12
  bh2 = H \ 14
  bw2 = (lw - m) \ 2
  y = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, y, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, y, bw2, bh2, 0)
  ty = fy + 7 * fp + 10
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
  Restore FormFields
  For i = 0 To 6
    Read flab$(i), fcol(i)
  Next
  CurHide
  For i = 0 To 6
    PText fx - 8, fy + i * fp + (fh(0) + 6) \ 2, flab$(i), "R", 0, C_INK
  Next
  CurShow
End Sub

FormFields:
Data "Record #", 0, "Date", 1, "Description", 2, "Category", 3
Data "Type", 4, "Amount $", 5, "Notes", 6

Sub LoadData
  Local string l$
  count = 0
  On Error Skip
  Open DATA_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And count < MAXF
    Line Input #1, l$
    If l$ <> "" Then
      For i = 0 To NF - 1
        d$(count, i) = Fld$(l$, i + 1)
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
    l$ = d$(r, 0)
    For c = 1 To NF - 1
      l$ = l$ + "|" + d$(r, c)
    Next
    Print #1, l$
  Next
  Close #1
End Sub

Function Money$(a As float)
  If a < 0 Then
    Money$ = "-$" + Str$(-a, 0, 2)
  Else
    Money$ = "$" + Str$(a, 0, 2)
  EndIf
End Function

Sub DrawList
  Local integer r, y
  Local float a
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      a = Val(d$(top + r, 5))
      If d$(top + r, 4) = "Expense" Then a = -a
      PText lx + lw - 8, y + rh \ 2, Money$(a), "R", 0, C_INK
      PText lx + 8, y + rh \ 2, Fit$(DDate$(d$(top + r, 1)) + "  " + d$(top + r, 2), lw - 100), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub DrawTotals
  Local float incm, exps
  For i = 0 To count - 1
    If d$(i, 4) = "Expense" Then
      exps = exps + Val(d$(i, 5))
    Else
      incm = incm + Val(d$(i, 5))
    EndIf
  Next
  CurHide
  Box fx - 90, ty - 2, W - fx + 90, 3 * (fh(0) + 4) + 4, 1, C_PAGE, C_PAGE
  PText fx, ty + fh(0) \ 2, "Income:  " + Money$(incm), "L", 0, C_INK
  PText fx, ty + fh(0) + 4 + fh(0) \ 2, "Expenses:  " + Money$(exps), "L", 0, C_INK
  PText fx, ty + 2 * (fh(0) + 4) + fh(0) \ 2, "Net:  " + Money$(incm - exps), "L", 0, Choice(incm < exps, C_RED_TOP, C_GRN_TOP)
  CurShow
End Sub

Sub ShowRecord(r As integer)
  For i = 0 To NF - 1
    f$(i) = d$(r, i)
  Next
  f$(1) = DDate$(f$(1))
  DrawForm
End Sub

Sub ClearForm
  For i = 0 To NF - 1
    f$(i) = ""
  Next
  DrawForm
End Sub

Sub DrawForm
  For i = 0 To 6
    TextBox fx, fy + i * fp, fw, f$(fcol(i)), 0
  Next
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      sel = r
      DrawList
      ShowRecord sel
      TickerMsg d$(sel, 2)
    EndIf
    Exit Sub
  EndIf
  If x >= fx And x < fx + fw And y >= fy Then
    r = (y - fy) \ fp
    If r > 6 Or y >= fy + r * fp + fh(0) + 6 Then Exit Sub
    If r = 0 Then Exit Sub
    If r = KIND_BOX Then
      If f$(4) = "Income" Then
        f$(4) = "Expense"
      Else
        f$(4) = "Income"
      EndIf
      TextBox fx, fy + r * fp, fw, f$(4), 0
    Else
      f$(fcol(r)) = EditText$(fx, fy + r * fp, fw, f$(fcol(r)))
    EndIf
  EndIf
End Sub

Sub NewRecord
  Local integer hi
  For i = 0 To count - 1
    hi = Max(hi, Val(d$(i, 0)))
  Next
  ClearForm
  f$(0) = Str$(hi + 1)
  f$(1) = DDate$(Date$)
  f$(4) = "Income"
  sel = -1
  DrawForm
  DrawList
  TickerMsg "New entry - fill in, then SAVE"
End Sub

Sub SaveRecord
  Local integer r
  If f$(2) = "" Or f$(5) = "" Then
    TickerMsg "Needs a description and an amount"
    Exit Sub
  EndIf
  f$(5) = Str$(Val(f$(5)))
  f$(1) = IsoDate$(f$(1))
  r = -1
  For i = 0 To count - 1
    If d$(i, 0) = f$(0) Then r = i
  Next
  If r < 0 Then
    If count >= MAXF Then
      TickerMsg "Too many entries"
      Exit Sub
    EndIf
    r = count
    count = count + 1
  EndIf
  For i = 0 To NF - 1
    d$(r, i) = f$(i)
  Next
  SaveData
  sel = r
  DrawList
  f$(1) = DDate$(f$(1))
  DrawForm
  DrawTotals
  TickerMsg "Saved " + f$(2)
End Sub

Sub DeleteRecord
  Local integer r
  If sel < 0 Then
    TickerMsg "Pick an entry first"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE again to remove " + d$(sel, 2)
    Exit Sub
  EndIf
  delArmed = 0
  TickerMsg "Deleted " + d$(sel, 2)
  For r = sel To count - 2
    For i = 0 To NF - 1
      d$(r, i) = d$(r + 1, i)
    Next
  Next
  count = count - 1
  SaveData
  sel = -1
  DrawList
  ClearForm
  DrawTotals
End Sub

' a spreadsheet-ready copy on A:, same columns with a header row
Sub ExportCsv
  Local integer r
  Open CSV_FILE$ For Output As #1
  Print #1, "id,date,description,category,type,amount,notes"
  For r = 0 To count - 1
    Print #1, d$(r, 0); ","; d$(r, 1); ","; Chr$(34); d$(r, 2); Chr$(34); ","; d$(r, 3); ","; d$(r, 4); ","; d$(r, 5); ","; Chr$(34); d$(r, 6); Chr$(34)
  Next
  Close #1
  TickerMsg "Exported " + Str$(count) + " entries to " + CSV_FILE$
End Sub
