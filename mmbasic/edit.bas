' edit.bas -- the text editor for the FILES page (club.py's FILE TRANSFER >
' EDIT): opens the file named on the first line of edit.tmp in the club
' folder.
'
' Keys: arrows, Home/End, PgUp/PgDn, typing, Enter, Backspace, Delete,
' Tab (2 spaces), Ctrl-S saves, Esc quits (twice if there are unsaved
' changes). A click in the text moves the cursor. Top menu bar: FILE
' (SAVE / SAVE & QUIT / QUIT). Uses the board's fixed-width font 1 so
' columns line up.
'
' Build with: python mmbasic/build.py  (writes ../edit.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXL = 1000, CW = 8, CH = 13

Dim string tl$(MAXL - 1), file$
Dim integer nl, cr, cc, vtop, vleft, rows, cols, tx0, ty0, dirty, quitArmed, j, v
' set when the file had a line over 255 chars or more than MAXL lines:
' what's in the editor isn't the whole file, so SAVE would damage it
Dim integer partial
Dim string k$, cmd$

CoreInit
v = AddMenu("FILE", "SAVE|SAVE & QUIT|QUIT")
DrawPage "EDIT"
StartCursor
tx0 = 8
' just under the menu bar
ty0 = by(0) + bh(0) + 10
rows = (H - ty0 - CH - 8) \ CH
cols = (W - 2 * tx0) \ CW
DrawAllBtns
LoadFile
DrawAll
If partial Then
  StatusMsg "Long lines or too big to show whole - view only, SAVE is off"
Else
  Status
EndIf

Do
  k$ = Inkey$
  If k$ <> "" Then
    KeyPress Asc(k$), k$
  Else
    j = PollInput()
    If j = -3 Then ClickText clickX, clickY
    cmd$ = Command$(j)
    If cmd$ = "SAVE" Then SaveFile
    If cmd$ = "SAVE & QUIT" Then
      SaveFile
      GoPage "files.bas"
    EndIf
    If cmd$ = "QUIT" Then TryQuit
  EndIf
  Pause 5
Loop

Sub LoadFile
  Local string l$, b$
  Local integer p
  On Error Skip
  Open HOME_DIR$ + "/edit.tmp" For Input As #1
  If MM.Errno = 0 Then
    If Not Eof(#1) Then Line Input #1, file$
    Close #1
  EndIf
  nl = 0
  partial = 0
  On Error Skip
  Open file$ For Input As #1
  If MM.Errno = 0 Then
    ' not Line Input: it stops the program on a line over 255 chars
    ' (MMBasic's string limit), so read in chunks and split on LF
    l$ = ""
    Do While Not Eof(#1) And nl < MAXL
      b$ = Input$(128, #1)
      Do While b$ <> "" And nl < MAXL
        p = Instr(b$, Chr$(10))
        If p = 0 Then
          AddText l$, b$
          b$ = ""
        Else
          AddText l$, Left$(b$, p - 1)
          b$ = Mid$(b$, p + 1)
          PushLine l$
        EndIf
      Loop
    Loop
    If l$ <> "" And nl < MAXL Then PushLine l$
    If Not Eof(#1) Or b$ <> "" Then partial = 1
    Close #1
  EndIf
  If nl = 0 Then nl = 1
End Sub

' add s$ to the line being read; a line too long for a string is split
Sub AddText(l$, s$)
  Local integer room
  room = 255 - Len(l$)
  If Len(s$) <= room Then
    l$ = l$ + s$
    Exit Sub
  EndIf
  partial = 1
  l$ = l$ + Left$(s$, room)
  If nl < MAXL Then PushLine l$
  If nl < MAXL Then AddText l$, Mid$(s$, room + 1)
End Sub

Sub PushLine(l$)
  If Right$(l$, 1) = Chr$(13) Then l$ = Left$(l$, Len(l$) - 1)
  tl$(nl) = l$
  nl = nl + 1
  l$ = ""
End Sub

Sub SaveFile
  Local integer i
  If partial Then
    StatusMsg "Can't save - long lines or too big, only part of it is shown"
    Exit Sub
  EndIf
  On Error Skip
  Open file$ For Output As #1
  If MM.Errno Then
    StatusMsg "Couldn't save: " + MM.ErrMsg$
    Exit Sub
  EndIf
  For i = 0 To nl - 1
    Print #1, tl$(i)
  Next
  Close #1
  dirty = 0
  StatusMsg "Saved " + file$
End Sub

Sub TryQuit
  If dirty And Not quitArmed Then
    quitArmed = 1
    StatusMsg "Unsaved changes - Esc or QUIT again to throw them away"
    Exit Sub
  EndIf
  GoPage "files.bas"
End Sub

' one screen row: the part of the line in view, padded so it clears
Sub DrawRow(r As integer)
  Local string s$
  Local integer ln
  ln = vtop + r
  If ln < nl Then s$ = Mid$(tl$(ln), vleft + 1, cols)
  s$ = s$ + Space$(cols - Len(s$))
  CurHide
  Text tx0, ty0 + r * CH, s$, "LT", 1, 1, C_INK, C_BAR
  If ln = cr Then
    ' the cursor: the character under it drawn inverted
    s$ = Mid$(tl$(cr) + " ", cc + 1, 1)
    Text tx0 + (cc - vleft) * CW, ty0 + r * CH, s$, "LT", 1, 1, C_BAR, C_INK
  EndIf
  CurShow
End Sub

Sub DrawAll
  Local integer r
  CurHide
  Box tx0 - 4, ty0 - 4, cols * CW + 8, rows * CH + 8, 1, C_DIM, C_BAR
  CurShow
  For r = 0 To rows - 1
    DrawRow r
  Next
End Sub

Sub Status
  StatusMsg Fit$(file$, W \ 2) + "   line " + Str$(cr + 1) + "/" + Str$(nl) + "  col " + Str$(cc + 1) + Choice(dirty, "   (changed)", "")
End Sub

Sub StatusMsg(s$)
  CurHide
  Box 0, H - CH - 4, W, CH + 4, 1, C_PAGE, C_PAGE
  Text tx0, H - CH - 2, Left$(s$, W \ CW - 2), "LT", 1, 1, C_INK, C_PAGE
  CurShow
End Sub

' keep the cursor on screen; redraw everything if the view had to move
Sub Follow(oldRow As integer)
  Local integer moved
  cr = Max(0, Min(nl - 1, cr))
  cc = Max(0, Min(Len(tl$(cr)), cc))
  If cr < vtop Then
    vtop = cr
    moved = 1
  EndIf
  If cr >= vtop + rows Then
    vtop = cr - rows + 1
    moved = 1
  EndIf
  If cc < vleft Then
    vleft = Max(0, cc - cols \ 2)
    moved = 1
  EndIf
  If cc >= vleft + cols Then
    vleft = cc - cols \ 2
    moved = 1
  EndIf
  If moved Then
    DrawAll
  Else
    If oldRow <> cr And oldRow - vtop >= 0 And oldRow - vtop < rows Then DrawRow oldRow - vtop
    DrawRow cr - vtop
  EndIf
  Status
End Sub

Sub KeyPress(a As integer, k$)
  Local integer old, i
  Local string l$
  old = cr
  If a <> 27 Then quitArmed = 0
  l$ = tl$(cr)
  Select Case a
    Case 128
      cr = cr - 1
    Case 129
      cr = cr + 1
    Case 130
      If cc > 0 Then
        cc = cc - 1
      ElseIf cr > 0 Then
        cr = cr - 1
        cc = Len(tl$(cr))
      EndIf
    Case 131
      If cc < Len(l$) Then
        cc = cc + 1
      ElseIf cr < nl - 1 Then
        cr = cr + 1
        cc = 0
      EndIf
    Case 134
      cc = 0
    Case 135
      cc = Len(l$)
    Case 136
      cr = cr - rows
    Case 137
      cr = cr + rows
    Case 19
      SaveFile
    Case 27
      TryQuit
      Exit Sub
    Case 13
      If nl >= MAXL Then Exit Sub
      For i = nl To cr + 2 Step -1
        tl$(i) = tl$(i - 1)
      Next
      tl$(cr + 1) = Mid$(l$, cc + 1)
      tl$(cr) = Left$(l$, cc)
      nl = nl + 1
      cr = cr + 1
      cc = 0
      dirty = 1
      DrawAll
    Case 8
      If cc > 0 Then
        tl$(cr) = Left$(l$, cc - 1) + Mid$(l$, cc + 1)
        cc = cc - 1
        dirty = 1
      ElseIf cr > 0 Then
        cc = Len(tl$(cr - 1))
        JoinLine cr - 1
        cr = cr - 1
        DrawAll
      EndIf
    Case 127
      If cc < Len(l$) Then
        tl$(cr) = Left$(l$, cc) + Mid$(l$, cc + 2)
        dirty = 1
      ElseIf cr < nl - 1 Then
        JoinLine cr
        DrawAll
      EndIf
    Case 9
      InsertText "  "
    Case 32 To 126
      InsertText k$
  End Select
  Follow old
End Sub

Sub InsertText(s$)
  If Len(tl$(cr)) + Len(s$) > 250 Then Exit Sub
  tl$(cr) = Left$(tl$(cr), cc) + s$ + Mid$(tl$(cr), cc + 1)
  cc = cc + Len(s$)
  dirty = 1
End Sub

' line n and the one after it become one line
Sub JoinLine(n As integer)
  Local integer i
  If Len(tl$(n)) + Len(tl$(n + 1)) > 250 Then Exit Sub
  tl$(n) = tl$(n) + tl$(n + 1)
  For i = n + 1 To nl - 2
    tl$(i) = tl$(i + 1)
  Next
  nl = nl - 1
  dirty = 1
End Sub

Sub ClickText(x As integer, y As integer)
  Local integer old
  If x < tx0 Or y < ty0 Or y >= ty0 + rows * CH Then Exit Sub
  old = cr
  cr = vtop + (y - ty0) \ CH
  cc = vleft + (x - tx0) \ CW
  Follow old
End Sub
