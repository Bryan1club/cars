' export.bas -- EXPORT/IMPORT page for the car club (MMBasic), ported from
' club.py's export_page.py.
'   EXPORT writes spreadsheet CSVs of the club data (members_, cars_,
'     events_, finance_ + date-time .csv) into the SD card's exports folder
'     (B:/exports, club.py's /sd/exports).
'   IMPORT merges a picked CSV back in: which data file it goes to comes
'     from the start of its name; a row whose first column (member number,
'     car id, event key, entry id) is already there replaces that record,
'     anything else is added.
' Top menu bar: EXPORT (MEMBERS/CARS/EVENTS/FINANCE/ALL), IMPORT (IMPORT/
' DELETE CSV), MENU. The list shows the CSVs in the exports folder.
'
' Build with: python mmbasic/build.py  (writes ../export.bas)

Option EXPLICIT
Option DEFAULT NONE

Const EXPORT_DIR$ = "B:/exports"
Const MAXF = 100, ROWS = 14, MAXR = 400
Const Q$ = Chr$(34)

Dim string cn$(MAXF - 1)
Dim integer count, top, sel, j, v, delArmed
Dim integer lx, ly, lw, rh, bPrev, bNext
Dim string cmd$

CoreInit
v = AddMenu("EXPORT", "MEMBERS|CARS|EVENTS|FINANCE|ALL")
v = AddMenu("IMPORT", "IMPORT|DELETE CSV")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "EXPORT/IMPORT"
Layout
DrawAllBtns
StartCursor
LoadList
DrawList
TickerMsg Str$(count) + " CSV files in " + EXPORT_DIR$

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
  If cmd$ = "HELP" Then HelpFor "export", "export.bas"
  Select Case cmd$
    Case "MENU"
      GoPage "club.bas"
    Case "MEMBERS"
      ExportOne "members"
    Case "CARS"
      ExportOne "cars"
    Case "EVENTS"
      ExportOne "events"
    Case "FINANCE"
      ExportOne "finance"
    Case "ALL"
      ExportOne "members"
      ExportOne "cars"
      ExportOne "events"
      ExportOne "finance"
      TickerMsg "Exported all four to " + EXPORT_DIR$
    Case "IMPORT"
      ImportCsv
    Case "DELETE CSV"
      DeleteCsv
  End Select
  If cmd$ <> "DELETE CSV" And j <> -1 Then delArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, yb
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W - 2 * m
  ly = H * 13 \ 100
  bh2 = H \ 14
  bw2 = W \ 5
  yb = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, yb, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, yb, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

Sub LoadList
  Local string f$
  count = 0
  On Error Skip
  MkDir EXPORT_DIR$
  On Error Skip
  f$ = Dir$(EXPORT_DIR$ + "/*.csv", FILE)
  Do While f$ <> "" And count < MAXF And MM.Errno = 0
    cn$(count) = f$
    count = count + 1
    f$ = Dir$()
  Loop
  If count > 1 Then Sort cn$(), , 3, 0, count
  top = 0
  sel = Choice(count > 0, 0, -1)
End Sub

Sub DrawList
  Local integer r, y
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(cn$(top + r), lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      sel = r
      DrawList
      TickerMsg cn$(sel)
    EndIf
  EndIf
End Sub

' the header row each CSV gets (same columns as the .dat file)
Function Header$(t$)
  Select Case t$
    Case "members"
      Header$ = "number,name,email,phone,status,financial,role,notes,visited,logbook,address"
    Case "cars"
      Header$ = "id,member,descr,rego,logbook"
    Case "events"
      Header$ = "key,name,date,time,place,notes"
    Case "finance"
      Header$ = "id,date,descr,category,kind,amount,notes"
  End Select
End Function

' YYYYMMDD_HHMM for file names
Function Stamp$()
  Local string d$
  d$ = Date$
  Stamp$ = Right$(d$, 4) + Mid$(d$, 4, 2) + Left$(d$, 2) + "_" + Left$(Time$, 2) + Mid$(Time$, 4, 2)
End Function

' every field quoted, so commas in addresses and notes are safe
Sub ExportOne(t$)
  Local string l$, o$, f$
  Local integer n, i
  f$ = EXPORT_DIR$ + "/" + t$ + "_" + Stamp$() + ".csv"
  On Error Skip
  Open t$ + ".dat" For Input As #1
  If MM.Errno Then
    TickerMsg "No " + t$ + " data to export"
    Exit Sub
  EndIf
  Open f$ For Output As #2
  Print #2, Header$(t$)
  Do While Not Eof(#1)
    Line Input #1, l$
    If l$ <> "" Then
      o$ = Q$ + Fld$(l$, 1) + Q$
      For i = 2 To FieldCount(Header$(t$))
        o$ = o$ + "," + Q$ + Fld$(l$, i) + Q$
      Next
      Print #2, o$
      n = n + 1
    EndIf
  Loop
  Close #2
  Close #1
  LoadList
  DrawList
  TickerMsg "Exported " + Str$(n) + " " + t$ + " to " + f$
End Sub

Function FieldCount(h$) As integer
  Local integer i
  FieldCount = 1
  For i = 1 To Len(h$)
    If Mid$(h$, i, 1) = "," Then FieldCount = FieldCount + 1
  Next
End Function

' one CSV line into "|"-separated fields (quotes allow commas inside)
Function CsvToDat$(c$)
  Local string o$, ch$
  Local integer i, q
  For i = 1 To Len(c$)
    ch$ = Mid$(c$, i, 1)
    If ch$ = Q$ Then
      q = Not q
    ElseIf ch$ = "," And Not q Then
      o$ = o$ + "|"
    ElseIf ch$ = "|" Then
      o$ = o$ + "/"
    Else
      o$ = o$ + ch$
    EndIf
  Next
  CsvToDat$ = o$
End Function

Sub ImportCsv
  Local string t$, l$, k$, d$(MAXR - 1)
  Local integer n, i, added, changed, found, first
  If sel < 0 Then
    TickerMsg "Pick a CSV first"
    Exit Sub
  EndIf
  t$ = LCase$(Left$(cn$(sel), Instr(cn$(sel) + "_", "_") - 1))
  If Header$(t$) = "" Then
    TickerMsg "Don't know what " + cn$(sel) + " holds (name must start members_, cars_, events_ or finance_)"
    Exit Sub
  EndIf
  ' what's there now
  On Error Skip
  Open t$ + ".dat" For Input As #1
  If MM.Errno = 0 Then
    Do While Not Eof(#1) And n < MAXR
      Line Input #1, l$
      If l$ <> "" Then
        d$(n) = l$
        n = n + 1
      EndIf
    Loop
    Close #1
  EndIf
  ' merge the CSV in, skipping its header row
  Open EXPORT_DIR$ + "/" + cn$(sel) For Input As #1
  first = 1
  Do While Not Eof(#1)
    Line Input #1, l$
    ' the header row isn't a record
    If first And LCase$(Left$(l$, 3)) = Left$(Header$(t$), 3) Then l$ = ""
    first = 0
    l$ = CsvToDat$(l$)
    k$ = Fld$(l$, 1)
    If k$ <> "" Then
      found = 0
      For i = 0 To n - 1
        If Fld$(d$(i), 1) = k$ Then
          d$(i) = l$
          found = 1
          changed = changed + 1
        EndIf
      Next
      If Not found And n < MAXR Then
        d$(n) = l$
        n = n + 1
        added = added + 1
      EndIf
    EndIf
  Loop
  Close #1
  Open t$ + ".dat" For Output As #1
  For i = 0 To n - 1
    Print #1, d$(i)
  Next
  Close #1
  TickerMsg "Imported " + cn$(sel) + ": " + Str$(added) + " added, " + Str$(changed) + " updated"
End Sub

Sub DeleteCsv
  If sel < 0 Then
    TickerMsg "Pick a CSV first"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE CSV again to delete " + cn$(sel)
    Exit Sub
  EndIf
  delArmed = 0
  On Error Skip
  Kill EXPORT_DIR$ + "/" + cn$(sel)
  TickerMsg "Deleted " + cn$(sel)
  LoadList
  DrawList
End Sub
