' photos.bas -- PHOTOS page for the car club (MMBasic), ported from
' club.py's photos_page.py: the car photos on the SD card (B:/cars, which
' club.py called /sd/cars) in a list, and the top menu bar: PHOTO (SHOW
' PIC / RENAME / DELETE), VIEW (REFRESH), MENU.
'
' SHOW PIC switches to the full-colour screen mode (MODE 4, 320x240 --
' the 640x480 mode only has 16 colours), fits the photo with LOAD JPG's
' 1/2 1/4 1/8 scaling, and any key or click comes back to the list.
' A click on a name that's already picked shows it too.
'
' Build with: python mmbasic/build.py  (writes ../photos.bas)

Option EXPLICIT
Option DEFAULT NONE

' where the photos are shown from: the SD card's B:/cars, or the USB stick (VIEW)
Dim string photoDir$
Const MAXP = 300, ROWS = 14

Dim string pn$(MAXP - 1)
Dim integer count, top, sel, j, v, delArmed, jw, jh
Dim integer lx, ly, lw, rh, bPrev, bNext
Dim string cmd$, back$

CoreInit
photoDir$ = "B:/cars"
v = AddMenu("PHOTO", "SHOW PIC|RENAME|DELETE|USE FOR CAR|COPY TO SD")
v = AddMenu("VIEW", "REFRESH|SD CARD PHOTOS|USB STICK PHOTOS")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "PHOTOS"
Layout
DrawAllBtns
StartCursor
LoadList
sel = -1
If count > 0 Then sel = 0
DrawList
TickerMsg Str$(count) + " photos in " + photoDir$
' another page (CARS) can hand over a photo to show: photo.tmp holds
' "file name|page to go back to"
back$ = NetLine$(HOME_DIR$ + "/photo.tmp")
If back$ <> "" Then
  On Error Skip
  Kill HOME_DIR$ + "/photo.tmp"
  For j = 0 To count - 1
    If LCase$(pn$(j)) = LCase$(Fld$(back$, 1)) Then sel = j
  Next
  If LCase$(pn$(Max(sel, 0))) = LCase$(Fld$(back$, 1)) Then
    ShowPic
  Else
    TickerMsg Fld$(back$, 1) + " isn't in " + photoDir$
    Pause 1500
  EndIf
  GoPage Fld$(back$, 2)
EndIf

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
  If cmd$ = "HELP" Then HelpFor "photos", "photos.bas"
  Select Case cmd$
    Case "MENU"
      GoPage "club.bas"
    Case "SHOW PIC"
      ShowPic
    Case "RENAME"
      RenamePic
    Case "DELETE"
      DeletePic
    Case "SD CARD PHOTOS", "USB STICK PHOTOS"
      photoDir$ = Choice(cmd$ = "SD CARD PHOTOS", "B:/cars", "C:")
      LoadList
      top = 0
      sel = Choice(count > 0, 0, -1)
      DrawList
      TickerMsg Str$(count) + " photos in " + photoDir$ + Choice(count = 0 And photoDir$ = "C:", " - is the USB stick in?", "")
    Case "USE FOR CAR"
      UseForCar
    Case "COPY TO SD"
      If CopyToSD() Then TickerMsg pn$(sel) + " copied to B:/cars"
    Case "REFRESH"
      LoadList
      top = 0
      sel = Choice(count > 0, 0, -1)
      DrawList
      TickerMsg Str$(count) + " photos"
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, y
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W - 2 * m
  ly = H * 13 \ 100
  bh2 = H \ 14
  bw2 = W \ 5
  y = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, y, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, y, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

' every .jpg/.jpeg/.bmp in photoDir$
Sub LoadList
  Local string f$, u$
  count = 0
  On Error Skip
  f$ = Dir$(photoDir$ + "/*", FILE)
  If MM.Errno Then
    TickerMsg "No SD card photos folder (" + photoDir$ + ")"
    Exit Sub
  EndIf
  Do While f$ <> "" And count < MAXP
    u$ = UCase$(f$)
    If Right$(u$, 4) = ".JPG" Or Right$(u$, 5) = ".JPEG" Or Right$(u$, 4) = ".BMP" Then
      pn$(count) = f$
      count = count + 1
    EndIf
    f$ = Dir$()
  Loop
  ' case-insensitive A-Z
  If count > 1 Then Sort pn$(), , 2, 0, count
End Sub

Sub DrawList
  Local integer r, y
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(pn$(top + r), lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      If r = sel Then
        ShowPic
      Else
        sel = r
        DrawList
        TickerMsg pn$(sel) + " - click again to show it"
      EndIf
    EndIf
  EndIf
End Sub

' width and height from a JPEG's start-of-frame marker (FFC0/FFC2)
Sub JpgSize(f$)
  Local string b$
  Local integer p, n
  jw = 0
  jh = 0
  Open f$ For Input As #3
  Do While Not Eof(#3) And n < 64
    b$ = b$ + Input$(255, #3)
    n = n + 1
    p = Instr(b$, Chr$(255) + Chr$(192))
    If p = 0 Then p = Instr(b$, Chr$(255) + Chr$(194))
    If p > 0 And Len(b$) >= p + 8 Then
      jh = Asc(Mid$(b$, p + 5, 1)) * 256 + Asc(Mid$(b$, p + 6, 1))
      jw = Asc(Mid$(b$, p + 7, 1)) * 256 + Asc(Mid$(b$, p + 8, 1))
      Exit Do
    EndIf
    ' keep only the tail so a marker split across reads is still found
    b$ = Right$(b$, 8)
  Loop
  Close #3
End Sub

Sub ShowPic
  Local string f$, k$
  Local integer sc, sw, sh, ok
  If sel < 0 Then
    TickerMsg "Pick a photo first"
    Exit Sub
  EndIf
  f$ = photoDir$ + "/" + pn$(sel)
  If hasMouse Then GUI Cursor Off
  ' full colour at 320x240 on this firmware; MODE 5 (256 colours) where
  ' there's no MODE 4
  On Error Skip
  MODE 4
  If MM.Errno Then MODE 5
  CLS
  sw = MM.HRES
  sh = MM.VRES
  On Error Skip
  If UCase$(Right$(f$, 4)) = ".BMP" Then
    Load Bmp f$, 0, 0
  Else
    JpgSize f$
    sc = 1
    Do While sc < 8 And (jw \ sc > sw Or jh \ sc > sh)
      sc = sc * 2
    Loop
    Load Jpg f$, Max(0, (sw - jw \ sc) \ 2), Max(0, (sh - jh \ sc) \ 2), , , , sc
  EndIf
  ok = (MM.Errno = 0)
  If Not ok Then Text sw \ 2, sh \ 2, "Can't show " + pn$(sel), "CM", 1, 1, RGB(255,255,255)
  ' wait for a key, a click or a touch
  Do
    k$ = Inkey$
    If k$ <> "" Then Exit Do
    If hasMouse Then
      ReadMouse
      If gml <> 0 And prevML = 0 Then
        prevML = gml
        Exit Do
      EndIf
      prevML = gml
    EndIf
    If hasTouch Then
      If Touch(X) >= 0 Then Exit Do
    EndIf
    Pause 20
  Loop
  ' back to this page as it was
  GoPage "photos.bas"
End Sub

Sub RenamePic
  Local string n$
  If sel < 0 Then
    TickerMsg "Pick a photo first"
    Exit Sub
  EndIf
  TickerMsg "Type the new name, Enter to keep"
  n$ = EditText$(lx, ly + ROWS * rh + 6 + W \ 80 + H \ 14 + 6, lw, pn$(sel))
  DrawList
  If n$ = "" Or n$ = pn$(sel) Then Exit Sub
  If Instr(n$, ".") = 0 Then n$ = n$ + ".jpg"
  On Error Skip
  Rename photoDir$ + "/" + pn$(sel) As photoDir$ + "/" + n$
  If MM.Errno Then
    TickerMsg "Couldn't rename: " + MM.ErrMsg$
  Else
    TickerMsg "Renamed to " + n$
    pn$(sel) = n$
  EndIf
  DrawList
End Sub

Sub DeletePic
  Local integer r
  If sel < 0 Then
    TickerMsg "Pick a photo first"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE again to delete " + pn$(sel)
    Exit Sub
  EndIf
  delArmed = 0
  On Error Skip
  Kill photoDir$ + "/" + pn$(sel)
  If MM.Errno Then
    TickerMsg "Couldn't delete: " + MM.ErrMsg$
    Exit Sub
  EndIf
  TickerMsg "Deleted " + pn$(sel)
  For r = sel To count - 2
    pn$(r) = pn$(r + 1)
  Next
  count = count - 1
  sel = Choice(count > 0, Min(sel, count - 1), -1)
  DrawList
End Sub

' a photo from the stick into B:/cars (where cars/events/members use them);
' 1 when it's there
Function CopyToSD() As integer
  If sel < 0 Then
    TickerMsg "Pick a photo first"
    Exit Function
  EndIf
  If photoDir$ = "B:/cars" Then
    CopyToSD = 1
    Exit Function
  EndIf
  If MM.Info(FILESIZE "B:/cars") <> -2 Then
    Drive "B:"
    Chdir "/"
    On Error Skip
    MkDir "cars"
    Chdir HOME_DIR$
  EndIf
  On Error Skip
  Copy photoDir$ + "/" + pn$(sel) To "B:/cars/" + pn$(sel)
  If MM.Errno Then
    TickerMsg "Couldn't copy: " + MM.ErrMsg$
    Exit Function
  EndIf
  CopyToSD = 1
End Function

' CARS with this photo waiting: the car clicked there gets it
Sub UseForCar
  If Not CopyToSD() Then Exit Sub
  Open HOME_DIR$ + "/carphoto.tmp" For Output As #1
  Print #1, pn$(sel)
  Close #1
  GoPage "cars.bas"
End Sub
