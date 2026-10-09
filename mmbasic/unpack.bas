' unpack.bas -- installs a club.pak: every page, game and picture the club
' boards need, shipped as one file (made by mmbasic/build.py).
'
' Put club.pak (pages and games) and/or clubart.pak (pictures) on the USB
' stick (C:), the SD card (B:) or A:, then either RUN "unpack.bas" at the
' prompt (it looks for club.pak, and installs clubart.pak too if it's in
' the same place), or pick a .pak in FILE TRANSFER and
' IMPORT it (that page hands the path over in B:/club/unpack.tmp).
'
' A .pak is: a line "@@PACK <name> <date> <count>", then for every file a
' line "@@FILE <path> <size>" followed by exactly <size> bytes, then
' "@@END". Each file is written to a temporary name in its folder, its size
' checked, and only then swapped in for the old one -- a bad copy never
' replaces a working page. Folders are made if they're missing.
'
' Needs nothing else on the board (no library, no club files), so it can
' set up a fresh board too.

Option EXPLICIT
Option DEFAULT NONE

Dim string pak$, l$, fpath$, fdir$, nm$, c$
Dim integer size, done, bad, total, remain, n, i

MODE 1
CLS
Font 1
Print "CLUB UNPACK"
Print

' where the pak is: handed over by FILE TRANSFER, else the usual places
pak$ = ""
On Error Skip
Open "B:/club/unpack.tmp" For Input As #1
If MM.Errno = 0 Then
  If Not Eof(#1) Then Line Input #1, pak$
  Close #1
  On Error Skip
  Kill "B:/club/unpack.tmp"
EndIf
If pak$ = "" Then
  For i = 1 To 5
    c$ = Choice(i = 1, "C:/club.pak", Choice(i = 2, "B:/club.pak", Choice(i = 3, "A:/club.pak", Choice(i = 4, "B:/import/club.pak", "B:/club/club.pak"))))
    On Error Skip
    n = MM.Info(FILESIZE c$)
    If MM.Errno = 0 And n > 0 And pak$ = "" Then pak$ = c$
  Next
EndIf
If pak$ = "" Then
  Print "No club.pak found on C:/, B:/, A:/, B:/import or B:/club"
  End
EndIf
DoPack pak$
' the pictures come in their own pack: install it too if it's alongside
c$ = Left$(pak$, RInstr(pak$, "/")) + "clubart.pak"
If c$ <> pak$ And MM.Info(FILESIZE c$) > 0 Then DoPack c$

Print
Print done; " of"; total; " files installed"; Choice(bad, ","  + Str$(bad) + " FAILED (old copies kept)", "")
If bad = 0 Then
  Print "Starting the club menu..."
  Pause 1500
  Run "B:/club/club.bas"
EndIf
End

' every file in one pack
Sub DoPack(p$)
  Local integer n2
  Print "Unpacking "; p$; " ("; MM.Info(FILESIZE p$); " bytes)"
  Open p$ For Input As #1
  Line Input #1, l$
  If Left$(l$, 6) <> "@@PACK" Then
    Print "Not a club pack: "; p$
    Close #1
    Exit Sub
  EndIf
  Print Mid$(l$, 8)
  n2 = Val(Field$(l$, 4, " "))
  total = total + n2
  Do While Not Eof(#1)
    Line Input #1, l$
    If Left$(l$, 6) = "@@END" Then Exit Do
    If Left$(l$, 6) = "@@FILE" Then
      fpath$ = Field$(l$, 2, " ")
      size = Val(Field$(l$, 3, " "))
      Unpack1
    EndIf
  Loop
  Close #1
  Print
End Sub

' one file: size bytes from #1 into fpath$
Sub Unpack1
  Local string tmp$, s$
  Local integer p, got
  p = RInstr(fpath$, "/")
  fdir$ = Left$(fpath$, p - 1)
  nm$ = Mid$(fpath$, p + 1)
  Print "  "; fpath$; Space$(Max(1, 30 - Len(fpath$))); size;
  MakeDirs fdir$
  Drive Left$(fdir$, 2)
  Chdir Choice(Len(fdir$) = 2, "/", Mid$(fdir$, 3))
  tmp$ = "unpack.new"
  On Error Skip
  Kill tmp$
  Open tmp$ For Output As #2
  remain = size
  Do While remain > 0
    s$ = Input$(Min(255, remain), #1)
    If Len(s$) = 0 Then Exit Do
    Print #2, s$;
    remain = remain - Len(s$)
  Loop
  Close #2
  got = MM.Info(FILESIZE tmp$)
  If got <> size Then
    Print "  BAD ("; got; ")"
    bad = bad + 1
    ' skip whatever of this file is left in the pack
    Do While remain > 0
      s$ = Input$(Min(255, remain), #1)
      If Len(s$) = 0 Then Exit Do
      remain = remain - Len(s$)
    Loop
    On Error Skip
    Kill tmp$
    Exit Sub
  EndIf
  On Error Skip
  Kill nm$
  Rename tmp$ As nm$
  Print "  ok"
  done = done + 1
End Sub

' make every folder along d$ ("B:/club/x") that doesn't exist yet
Sub MakeDirs(d$)
  Local integer p
  Local string part$
  Drive Left$(d$, 2)
  Chdir "/"
  p = 4
  Do While p <= Len(d$)
    p = Instr(p, d$ + "/", "/")
    part$ = Mid$(d$, 3, p - 3)
    If MM.Info(FILESIZE Left$(d$, 2) + part$) <> -2 Then
      On Error Skip
      Mkdir Mid$(part$, 2)
    EndIf
    p = p + 1
  Loop
End Sub

Function RInstr(s$, f$) As integer
  Local integer i
  For i = Len(s$) To 1 Step -1
    If Mid$(s$, i, 1) = f$ Then
      RInstr = i
      Exit Function
    EndIf
  Next
End Function
