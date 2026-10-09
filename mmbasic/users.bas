' users.bas -- USERS page (ADMIN > USERS), ported from club.py's
' users_page.py: the board's login accounts on the left, the picked one
' on the right. Top menu bar like club.py: SAVE, DELETE, CLEAR, BACK.
'
' Data: users.dat in the club folder, one account per line:
' username|password hash|role (role is "admin" or "operator"). Passwords
' are never stored as typed, only as PassHash$() of username + password.
'
' Click a name to edit it, click Username/Password to type, click Role to
' swap admin/operator. Picking an account leaves Password blank: type one
' only to change it. SAVE writes the file.
'
' Build with: python mmbasic/build.py  (writes ../users.bas)

Option EXPLICIT
Option DEFAULT NONE

Const DATA_FILE$ = "users.dat"
Const MAXU = 40, ROWS = 13

Dim string u$(MAXU - 1), ph$(MAXU - 1), ur$(MAXU - 1)
Dim string fu$, pw$, fr$
Dim integer count, top, sel, j, i, v, delArmed
Dim integer lx, ly, lw, rh, fx, fy, fw, fp
Dim integer bPrev, bNext
Dim string cmd$

CoreInit
v = AddMenu("SAVE", "")
v = AddMenu("DELETE", "")
v = AddMenu("CLEAR", "")
v = AddMenu("BACK", "")
v = AddMenu("HELP", "")
DrawPage "USERS"
Layout
DrawAllBtns
StartCursor
LoadData
DrawList
ClearForm
TickerMsg Str$(count) + " account(s) on file"

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
  If cmd$ = "HELP" Then HelpFor "users", "users.bas"
  Select Case cmd$
    Case "BACK"
      GoPage "admin.bas"
    Case "SAVE"
      SaveUser
    Case "DELETE"
      DeleteUser
    Case "CLEAR"
      sel = -1
      DrawList
      ClearForm
      TickerMsg "New account - fill in, then SAVE"
  End Select
  If cmd$ <> "DELETE" And j <> -1 Then delArmed = 0
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2, y
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  lw = W * 40 \ 100
  ly = H * 17 \ 100
  fx = lx + lw + m * 2 + 90
  fw = W - fx - m
  fy = ly
  fp = fh(0) + 14
  bh2 = H \ 14
  bw2 = (lw - m) \ 2
  y = ly + ROWS * rh + 6 + m \ 2
  bPrev = AddBtn("PREV", lx, y, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, y, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
  CurHide
  PText fx - 8, fy + (fh(0) + 6) \ 2, "Username", "R", 0, C_INK
  PText fx - 8, fy + fp + (fh(0) + 6) \ 2, "Password", "R", 0, C_INK
  PText fx - 8, fy + 2 * fp + (fh(0) + 6) \ 2, "Role", "R", 0, C_INK
  PText fx, fy + 3 * fp + (fh(0) + 6) \ 2, "Click Role to swap admin/operator", "L", 0, C_DIM
  CurShow
End Sub

Sub LoadData
  Local string l$
  count = 0
  On Error Skip
  Open DATA_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And count < MAXU
    Line Input #1, l$
    If l$ <> "" Then
      u$(count) = Fld$(l$, 1)
      ph$(count) = Fld$(l$, 2)
      ur$(count) = Fld$(l$, 3)
      If ur$(count) <> "admin" Then ur$(count) = "operator"
      count = count + 1
    EndIf
  Loop
  Close #1
End Sub

Sub SaveData
  Open DATA_FILE$ For Output As #1
  For i = 0 To count - 1
    Print #1, u$(i) + "|" + ph$(i) + "|" + ur$(i)
  Next
  Close #1
End Sub

' FNV-1a of the username and password together, as 8 hex digits
Function PassHash$(n$, p$)
  Local integer h, k
  Local string s$
  s$ = LCase$(n$) + ":" + p$
  h = &H811C9DC5
  For k = 1 To Len(s$)
    h = ((h Xor Asc(Mid$(s$, k, 1))) * 16777619) And &HFFFFFFFF
  Next
  PassHash$ = Hex$(h, 8)
End Function

Sub DrawList
  Local integer r, y
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      PText lx + 8, y + rh \ 2, Fit$(u$(top + r) + "  (" + ur$(top + r) + ")", lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub ClearForm
  fu$ = ""
  pw$ = ""
  fr$ = "operator"
  DrawForm
End Sub

Sub DrawForm
  TextBox fx, fy, fw, fu$, 0
  TextBox fx, fy + fp, fw, String$(Len(pw$), "*"), 0
  TextBox fx, fy + 2 * fp, fw \ 2, fr$, 0
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  ' an account in the list
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      sel = r
      delArmed = 0
      fu$ = u$(r)
      pw$ = ""
      fr$ = ur$(r)
      DrawList
      DrawForm
      TickerMsg "Editing " + fu$ + " - type a password only to change it"
    EndIf
    Exit Sub
  EndIf
  If x < fx Or x >= fx + fw Or y < fy Then Exit Sub
  r = (y - fy) \ fp
  If y >= fy + r * fp + fh(0) + 6 Then Exit Sub
  Select Case r
    Case 0
      fu$ = EditText$(fx, fy, fw, fu$)
    Case 1
      pw$ = EditPass$(fx, fy + fp, fw, pw$)
    Case 2
      If x < fx + fw \ 2 Then
        fr$ = Choice(fr$ = "admin", "operator", "admin")
        DrawForm
      EndIf
  End Select
End Sub

Function Find(n$) As integer
  Find = -1
  For i = 0 To count - 1
    If LCase$(u$(i)) = LCase$(n$) Then Find = i
  Next
End Function

Function Admins() As integer
  For i = 0 To count - 1
    If ur$(i) = "admin" Then Admins = Admins + 1
  Next
End Function

Sub SaveUser
  Local integer r
  fu$ = Trim$(fu$)
  If fu$ = "" Then
    TickerMsg "Enter a username"
    Exit Sub
  EndIf
  r = Find(fu$)
  If r < 0 Then
    If pw$ = "" Then
      TickerMsg "Enter a password for this new user"
      Exit Sub
    EndIf
    If count >= MAXU Then
      TickerMsg "Account list is full"
      Exit Sub
    EndIf
    r = count
    count = count + 1
    u$(r) = fu$
  ElseIf ur$(r) = "admin" And fr$ <> "admin" And Admins() <= 1 Then
    TickerMsg "Can't take admin off the only admin account"
    Exit Sub
  EndIf
  If pw$ <> "" Then ph$(r) = PassHash$(fu$, pw$)
  ur$(r) = fr$
  SaveData
  sel = r
  pw$ = ""
  DrawList
  DrawForm
  TickerMsg "Saved " + fu$
End Sub

' needs two presses, and never removes the last account or last admin
Sub DeleteUser
  Local integer r
  If sel < 0 Then
    TickerMsg "Pick a user from the list first"
    Exit Sub
  EndIf
  If count <= 1 Then
    TickerMsg "Can't delete the only account left"
    Exit Sub
  EndIf
  If ur$(sel) = "admin" And Admins() <= 1 Then
    TickerMsg "Can't delete the only admin"
    Exit Sub
  EndIf
  If Not delArmed Then
    delArmed = 1
    TickerMsg "Press DELETE again to remove " + u$(sel)
    Exit Sub
  EndIf
  delArmed = 0
  TickerMsg "Deleted " + u$(sel)
  For r = sel To count - 2
    u$(r) = u$(r + 1)
    ph$(r) = ph$(r + 1)
    ur$(r) = ur$(r + 1)
  Next
  count = count - 1
  SaveData
  sel = -1
  DrawList
  ClearForm
End Sub
