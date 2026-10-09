' files.bas -- FILE TRANSFER page, laid out like club.py's SDImportPage:
' browse the board's drives -- A: (flash), B: (SD card), C: (USB stick) --
' pick a file, then use the top menu bar:
'   FILE   IMPORT (copy it to the Import to folder, or blank: where the club
'          keeps that kind of file; a
'          .pak is unpacked -- every page/game in it installed),
'          EDIT (text files only), DELETE (press twice)
'   VIEW   EDIT (text files), REFRESH, SD CARD / USB STICK / BOARD FLASH A:
'   BACK   back to ADMIN (Esc does the same)
' Click a folder to open it ("[..]" goes up), click a file to pick it.
' The mouse wheel, or click and drag, scrolls the list.
' Or the keyboard: Up/Down, PgUp/PgDn, Enter opens/picks, Backspace goes
' up a folder, Delete deletes, Esc goes back.
' The status line under the path always says what just happened.
'
' EDIT hands the file to edit.bas through edit.tmp in the club folder (the file's
' full path on the first line), and edit.bas comes back here.
'
' Build with: python mmbasic/build.py  (writes ../files.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXF = 300, ROWS = 13
' where IMPORT puts each kind of file (club.py routed the same way)
Const PHOTO_DIR$ = "B:/cars", MUSIC_DIR$ = "B:/music", IMPORT_DIR$ = "B:/import"
' the only files EDIT will open; biggest it will try
Const TEXT_EXT$ = ".BAS.DAT.INC.TXT.CSV.LOG.INI.MD.PY.CFG.", MAX_EDIT = 60000

Dim string fn$(MAXF - 1), path$
Dim integer isdir(MAXF - 1), count, top, sel, j, v, delArmed, impArmed
Dim integer lx, ly, lw, rh, bPrev, bNext, sy
' IMPORT's folder: blank = the usual place for that kind of file
Dim string tgt$
Dim integer tgX, tgY, tgW
Dim string cmd$, k$

CoreInit
v = AddMenu("FILE", "IMPORT|DELETE")
v = AddMenu("VIEW", "EDIT|REFRESH|SD CARD|USB STICK|BOARD FLASH A:")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "FILE TRANSFER"
Layout
DrawAllBtns
StartCursor
path$ = LastPath$()
LoadDir

Do
  ' the keyboard drives the list (PollInput only moves between buttons)
  k$ = Inkey$
  If k$ <> "" Then KeyNav Asc(k$)
  j = PollInput()
  ' mouse wheel, or click and drag the list
  v = ListDelta(lx, ly, lw, ROWS * rh + 6, rh)
  If v <> 0 And count > ROWS Then
    v = Max(0, Min(count - ROWS, top + v))
    If v <> top Then
      top = v
      DrawList
    EndIf
  EndIf
  If j = -2 Then GoPage "admin.bas"
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
  If cmd$ = "HELP" Then HelpFor "files", "files.bas"
  Select Case cmd$
    Case "BACK"
      GoPage "admin.bas"
    Case "SD CARD", "USB STICK", "BOARD FLASH A:"
      path$ = Choice(cmd$ = "SD CARD", "B:/", Choice(cmd$ = "USB STICK", "C:/", "A:/"))
      LoadDir
    Case "REFRESH"
      LoadDir
    Case "IMPORT"
      ImportFile
    Case "EDIT"
      EditFile
    Case "DELETE"
      DeleteFile
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  If cmd$ <> "IMPORT" And j <> -1 Then impArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, yb
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W - 2 * m
  ' path line, then the status line, then the list
  sy = H * 13 \ 100 + rh
  ly = sy + rh + 4
  bh2 = H \ 14
  bw2 = W \ 5
  yb = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, yb, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, yb, bw2, bh2, 0)
  ' club.py's "Folder (blank=auto)" box, right of PREV/NEXT
  tgX = lx + 2 * bw2 + 3 * m + PWidth("Import to:", 0) + 8
  tgY = yb + (bh2 - fh(0) - 6) \ 2
  tgW = lx + lw - tgX
  PText tgX - 6, tgY + (fh(0) + 6) \ 2, "Import to:", "R", 0, C_INK
  TextBox tgX, tgY, tgW, "(blank = automatic)", 0
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

' the page's own status line -- club.py found ticker-only messages too easy
' to miss on this page
Sub Say(s$)
  CurHide
  Box lx, sy - rh \ 2, lw, rh, 1, C_BAR, C_BAR
  CurShow
  PText lx + 6, sy, Fit$(s$, lw - 12), "L", 0, C_INK
End Sub

' the folder the editor came back from, or the club folder
Function LastPath$()
  Local string l$
  LastPath$ = "B:/"
  On Error Skip
  Open "edit.tmp" For Input As #1
  If MM.Errno Then Exit Function
  If Not Eof(#1) Then Line Input #1, l$
  Close #1
  If Instr(l$, "/") Then LastPath$ = Left$(l$, RInstr(l$, "/"))
  ' only for coming straight back from the editor, never again after
  On Error Skip
  Kill "edit.tmp"
End Function

Function RInstr(s$, c$) As integer
  Local integer i
  For i = Len(s$) To 1 Step -1
    If Mid$(s$, i, 1) = c$ Then
      RInstr = i
      Exit Function
    EndIf
  Next
End Function

' folders first (with ".." unless at a drive's top), then files, A-Z
Sub LoadDir
  Local string f$
  Local integer nd
  Local string e$
  ' each drive keeps its own current folder (MUSIC leaves the stick's at
  ' /music), and Dir$ lists that one, so go into path$ itself to list it
  If Not GoInto(path$) Then
    ' said on the page's status line below, not left in the ticker
    e$ = "Can't read " + path$ + Choice(Left$(path$, 1) = "C", " - is the USB stick in?", "") + " - showing " + HOME_DIR$
    path$ = HOME_DIR$ + "/"
    If GoInto(path$) Then e$ = e$ + ""
  EndIf
  On Error Skip
  f$ = Dir$("*", DIR)
  count = 0
  If Len(path$) > 3 Then
    ' ".." first; the folders found above follow it
    count = 1
  EndIf
  Do While f$ <> "" And count < MAXF
    If f$ <> "." And f$ <> ".." Then
      fn$(count) = f$
      isdir(count) = 1
      count = count + 1
    EndIf
    f$ = Dir$()
  Loop
  If Len(path$) > 3 Then
    fn$(0) = ".."
    isdir(0) = 1
  EndIf
  nd = count
  On Error Skip
  f$ = Dir$("*", FILE)
  Do While f$ <> "" And count < MAXF And MM.Errno = 0
    fn$(count) = f$
    isdir(count) = 0
    count = count + 1
    f$ = Dir$()
  Loop
  If count - nd > 1 Then Sort fn$(), , 2, nd, count - nd
  ' back to the club folder, where the pages' own files are
  Drive "B:"
  Chdir HOME_DIR$
  top = 0
  sel = -1
  DrawList
  If e$ <> "" Then
    Say e$
  Else
    Say Str$(count) + " items - click a file to pick it"
  EndIf
  ' an old complaint doesn't hang about in the ticker
  TickerMsg "File transfer - " + path$
End Sub

Sub DrawList
  Local integer r, y
  Local string t$
  CurHide
  Box lx, sy - rh - rh \ 2, lw, rh, 1, C_PAGE, C_PAGE
  CurShow
  PText lx, sy - rh, Fit$(path$, lw), "L", 0, C_INK
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      t$ = fn$(top + r)
      If isdir(top + r) Then t$ = "[" + t$ + "]"
      PText lx + 8, y + rh \ 2, Fit$(t$, lw - 120), "L", 0, Choice(isdir(top + r), C_DIM, C_INK)
      ' sizes on the SD card and flash; on the USB stick each lookup is slow,
      ' so there the size shows when a file is picked
      If Not isdir(top + r) And Left$(path$, 1) <> "C" Then PText lx + lw - 10, y + rh \ 2, SizeText$(path$ + fn$(top + r)), "R", 0, C_DIM
    EndIf
  Next
  CurShow
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= tgX And x < tgX + tgW And y >= tgY And y < tgY + fh(0) + 6 Then
    tgt$ = Trim$(EditText$(tgX, tgY, tgW, tgt$))
    If tgt$ = "" Then TextBox tgX, tgY, tgW, "(blank = automatic)", 0
    Say Choice(tgt$ = "", "IMPORT puts each file in its usual place", "IMPORT will put files in " + TgtDir$())
    Exit Sub
  EndIf
  If x < lx Or x >= lx + lw Or y < ly + 3 Or y >= ly + 3 + ROWS * rh Then Exit Sub
  r = top + (y - ly - 3) \ rh
  If r >= count Then Exit Sub
  OpenRow r
End Sub

' Up/Down move through the list, PgUp/PgDn a page, Enter opens a folder or
' picks a file, Backspace goes up a folder, Delete deletes, Esc goes back
Sub KeyNav(c As integer)
  Local integer r
  r = sel
  Select Case c
    Case 27
      GoPage "admin.bas"
    Case 128
      r = Max(0, sel - 1)
    Case 129
      r = Min(count - 1, sel + 1)
    Case 136
      r = Max(0, sel - ROWS)
    Case 137
      r = Min(count - 1, Max(0, sel) + ROWS)
    Case 13
      If sel >= 0 Then OpenRow sel
      Exit Sub
    Case 8
      If Len(path$) > 3 Then
        path$ = Left$(path$, RInstr(Left$(path$, Len(path$) - 1), "/"))
        LoadDir
      EndIf
      Exit Sub
    Case 127
      DeleteFile
      Exit Sub
    Case Else
      Exit Sub
  End Select
  If r < 0 Or r = sel Then Exit Sub
  sel = r
  ' keep the highlighted row on screen
  If sel < top Then top = (sel \ ROWS) * ROWS
  If sel >= top + ROWS Then top = (sel \ ROWS) * ROWS
  DrawList
  Say Choice(isdir(sel), "[" + fn$(sel) + "] - Enter opens it", fn$(sel) + " - Enter picks it, then FILE: IMPORT, EDIT or DELETE")
End Sub

' open a folder row, or pick a file row
Sub OpenRow(r As integer)
  If isdir(r) Then
    If fn$(r) = ".." Then
      path$ = Left$(path$, RInstr(Left$(path$, Len(path$) - 1), "/"))
    Else
      path$ = path$ + fn$(r) + "/"
    EndIf
    LoadDir
  Else
    sel = r
    DrawList
    Say fn$(sel) + "  " + SizeText$(path$ + fn$(sel)) + " - FILE: IMPORT or DELETE, VIEW: EDIT"
  EndIf
End Sub

Function Picked() As integer
  If sel < 0 Or sel >= count Then
    Say "Pick a file from the list first"
    Exit Function
  EndIf
  If isdir(sel) Then
    Say "That's a folder - click it to open it"
    Exit Function
  EndIf
  Picked = 1
End Function

Sub EditFile
  If Not Picked() Then Exit Sub
  ' pictures, music etc. aren't text - the editor can't show them
  If Instr(TEXT_EXT$, "." + UCase$(Ext$(fn$(sel))) + ".") = 0 Then
    Say "Only text files (.bas .dat .txt .csv ...) can be edited"
    Exit Sub
  EndIf
  If FSize(path$ + fn$(sel)) > MAX_EDIT Then
    Say fn$(sel) + " is too big to edit here"
    Exit Sub
  EndIf
  Open HOME_DIR$ + "/edit.tmp" For Output As #1
  Print #1, path$ + fn$(sel)
  Close #1
  GoPage "edit.bas"
End Sub

' copy the picked file to where the club keeps that kind of file:
' programs and data to the club folder, pictures to the car photos,
' music to the music folder, anything else to B:/import
Sub ImportFile
  Local string e$, d$, src$
  Local integer sz
  If Not Picked() Then Exit Sub
  e$ = "." + UCase$(Ext$(fn$(sel))) + "."
  ' a club pack (club.pak, clubart.pak): unpack.bas installs everything in it
  If e$ = ".PAK." Then
    If FSize(HOME_DIR$ + "/unpack.bas") < 0 Then
      Say "unpack.bas isn't in " + HOME_DIR$ + " yet - copy it there once first"
      Exit Sub
    EndIf
    Open HOME_DIR$ + "/unpack.tmp" For Output As #1
    Print #1, path$ + fn$(sel)
    Close #1
    GoPage "unpack.bas"
  EndIf
  If Instr(".BAS.DAT.INC.SPR.", e$) Then
    d$ = HOME_DIR$
  ElseIf Instr(".BMP.JPG.JPEG.PNG.GIF.", e$) Then
    d$ = PHOTO_DIR$
  ElseIf Instr(".MP3.WAV.FLAC.MOD.", e$) Then
    d$ = MUSIC_DIR$
  Else
    d$ = IMPORT_DIR$
  EndIf
  If tgt$ <> "" Then d$ = TgtDir$()
  src$ = path$ + fn$(sel)
  If UCase$(path$) = UCase$(d$ + "/") Then
    Say fn$(sel) + " is already in " + d$
    Exit Sub
  EndIf
  If FSize(d$ + "/" + fn$(sel)) >= 0 And Not impArmed Then
    impArmed = 1
    Say fn$(sel) + " is already in " + d$ + " - IMPORT again to replace it"
    Exit Sub
  EndIf
  impArmed = 0
  If FSize(d$) <> -2 Then
    On Error Skip
    MkDir d$
  EndIf
  Say "Copying " + fn$(sel) + " to " + d$ + " ..."
  sz = FSize(src$)
  On Error Skip
  Copy src$ To d$ + "/" + fn$(sel)
  If MM.Errno Then
    Say "Couldn't copy: " + MM.ErrMsg$
  ElseIf FSize(d$ + "/" + fn$(sel)) <> sz Then
    Say "Copy came out the wrong size - try IMPORT again"
  Else
    Say "Imported " + fn$(sel) + " to " + d$
  EndIf
End Sub

Function SizeText$(f$)
  Local integer n
  n = FSize(f$)
  If n < 0 Then Exit Function
  If n < 10000 Then
    SizeText$ = Str$(n)
  ElseIf n < 10000000 Then
    SizeText$ = Str$(n \ 1024) + "K"
  Else
    SizeText$ = Str$(n \ 1048576) + "M"
  EndIf
End Function

Function Ext$(f$)
  Local integer i
  i = RInstr(f$, ".")
  If i Then Ext$ = Mid$(f$, i + 1)
End Function

' needs two presses, so one stray click can't delete a file
Sub DeleteFile
  If Not Picked() Then Exit Sub
  If Not delArmed Then
    delArmed = 1
    Say "Press DELETE again to delete " + fn$(sel)
    Exit Sub
  EndIf
  delArmed = 0
  On Error Skip
  Kill path$ + fn$(sel)
  If MM.Errno Then
    Say "Couldn't delete: " + MM.ErrMsg$
  Else
    LoadDir
    Say "Deleted " + fn$(sel)
  EndIf
End Sub

' the "Import to" folder as a full path: "photos" -> B:/photos
Function TgtDir$()
  Local string t$
  t$ = tgt$
  If Mid$(t$, 2, 1) <> ":" Then t$ = "B:/" + t$
  If Right$(t$, 1) = "/" Then t$ = Left$(t$, Len(t$) - 1)
  TgtDir$ = t$
End Function

' a file's size, -2 for a folder, -1 if it isn't there -- or if the drive
' gives an error (board 2's USB stick does), instead of stopping the page
Function FSize(f$) As integer
  FSize = -1
  On Error Skip
  FSize = MM.Info(FILESIZE f$)
End Function

' make p$ ("C:/", "B:/cars/") the current drive and folder; 0 if it can't
Function GoInto(p$) As integer
  Local string d$
  d$ = Mid$(p$, 3)
  If Len(d$) > 1 And Right$(d$, 1) = "/" Then d$ = Left$(d$, Len(d$) - 1)
  On Error Skip
  Drive Left$(p$, 2)
  If MM.Errno Then Exit Function
  On Error Skip
  Chdir d$
  If MM.Errno Then
    Drive "B:"
    Chdir HOME_DIR$
    Exit Function
  EndIf
  GoInto = 1
End Function
