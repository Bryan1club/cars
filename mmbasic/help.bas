' help.bas -- the HELP page: shows the help.txt section for the page it was
' opened from (help.tmp in the club folder holds "topic|page to go back
' to", written by core's HelpFor). Paragraphs are wrapped to the screen;
' PREV/NEXT (or PgUp/PgDn) page through long ones. BACK (Esc) goes back.
'
' Build with: python mmbasic/build.py  (writes ../help.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXHL = 120
Dim string hl$(MAXHL - 1), topic$, back$, title$, cmd$
Dim integer nhl, top, rowsH, lx, ly, lw, rh, bPrev, bNext, j, v

CoreInit
v = AddMenu("BACK", "")
DrawPage ""
Layout
DrawAllBtns
StartCursor
topic$ = Fld$(NetLine$(HOME_DIR$ + "/help.tmp"), 1)
back$ = Fld$(NetLine$(HOME_DIR$ + "/help.tmp"), 2)
If back$ = "" Then back$ = "club.bas"
LoadHelp
ShowHelp
TickerMsg "Help - " + title$

Do
  j = PollInput()
  v = ListNav(lx, ly, lw, rh, rowsH, nhl, top)
  If v >= 1 Then ShowHelp
  If j = -2 Then GoPage back$
  If j = bPrev And top > 0 Then
    top = Max(0, top - rowsH)
    ShowHelp
  EndIf
  If j = bNext And top + rowsH < nhl Then
    top = top + rowsH
    ShowHelp
  EndIf
  cmd$ = ""
  If j >= 0 And j <> bPrev And j <> bNext Then cmd$ = Command$(j)
  If cmd$ = "BACK" Then GoPage back$
  Pause 10
Loop

Sub Layout
  Local integer m, bw2, bh2
  m = W \ 40
  rh = fh(0) + 6
  lx = m * 2
  lw = W - 4 * m
  ly = H * 15 \ 100
  bh2 = H \ 14
  bw2 = W \ 5
  rowsH = (H - ly - bh2 - fh(0) - 40) \ rh
  bPrev = AddBtn("PREV", lx, ly + rowsH * rh + 8, bw2, bh2, 0)
  bNext = AddBtn("NEXT", lx + bw2 + m, ly + rowsH * rh + 8, bw2, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

' the [topic] section of help.txt, each paragraph wrapped to lw
Sub LoadHelp
  Local string l$
  Local integer inSec
  nhl = 0
  title$ = "Help"
  On Error Skip
  Open HOME_DIR$ + "/help.txt" For Input As #1
  If MM.Errno Then
    hl$(0) = "No help.txt in " + HOME_DIR$ + " yet."
    nhl = 1
    Exit Sub
  EndIf
  Do While Not Eof(#1) And nhl < MAXHL
    Line Input #1, l$
    If Left$(l$, 1) = "[" Then
      If inSec Then Exit Do
      inSec = (LCase$(l$) = "[" + LCase$(topic$) + "]")
      If inSec And Not Eof(#1) Then Line Input #1, title$
    ElseIf inSec And Left$(l$, 1) <> "'" Then
      ' a paragraph can run over several lines (each under 255 characters,
      ' Line Input's limit); a blank line ends it
      If l$ = "" Then
        If nhl > 0 And nhl < MAXHL Then
          hl$(nhl) = ""
          nhl = nhl + 1
        EndIf
      Else
        Wrap l$
      EndIf
    EndIf
  Loop
  Close #1
  If nhl = 0 Then
    hl$(0) = "There's no help for this page yet."
    nhl = 1
  EndIf
End Sub

' a paragraph into lines that fit lw (font 0), broken at spaces
Sub Wrap(p$)
  Local string t$, w$
  Local integer i
  t$ = ""
  p$ = p$ + " "
  Do While p$ <> "" And nhl < MAXHL
    i = Instr(p$, " ")
    w$ = Left$(p$, i - 1)
    p$ = Mid$(p$, i + 1)
    If t$ <> "" And PWidth(t$ + " " + w$, 0) > lw - 10 Then
      hl$(nhl) = t$
      nhl = nhl + 1
      t$ = w$
    Else
      t$ = t$ + Choice(t$ = "", "", " ") + w$
    EndIf
  Loop
  If t$ <> "" And nhl < MAXHL Then
    hl$(nhl) = t$
    nhl = nhl + 1
  EndIf
End Sub

Sub ShowHelp
  Local integer r
  CurHide
  Box lx - 6, ly - rh - 10, lw + 12, (rowsH + 1) * rh + 16, 1, C_DIM, C_PAGE
  CurShow
  PText lx, ly - rh \ 2 - 4, title$ + Choice(nhl > rowsH, "   (" + Str$(top \ rowsH + 1) + "/" + Str$((nhl - 1) \ rowsH + 1) + ")", ""), "L", 1, C_AMBER
  For r = 0 To rowsH - 1
    If top + r < nhl Then PText lx, ly + r * rh + rh \ 2, hl$(top + r), "L", 0, C_INK
  Next
End Sub
