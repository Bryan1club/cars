' draw.bas -- standalone page painter for the club boards (MMBasic).
' Draw a page's background art and mark where its buttons and boxes go.
' Needs nothing else: no library, no club files, built-in fonts only.
' Tools borrowed from the 3D Model Editor: SELECT/move/DELETE, CTR LINE,
' ARC, MULTI LINE, MIRROR, MEASURE, COLOUR, plus a duplicate.
'
' Every shape is kept as an object, so anything can be picked (SEL) and
' moved, recoloured, resized, filled, mirrored, copied or deleted later.
' Screen: MODE 3 (640x480, 16 colours) if the firmware has it, else
' MODE 2 (320x240). The finished art is kept in framebuffer F; the screen
' shows F plus the tool bar, selection and previews.
'
' Top menu bar and left icon panel -- with VIEW > Auto-hide (on at the
' start) they tuck away while the pointer is out in the picture, leaving
' the whole screen to draw on, and drop back when the pointer touches the
' top or left edge. Tab hides/shows them by hand:
'   FILE  New, Load, Save, Quit
'   EDIT  Undo, Duplicate, Mirror, Delete, Clear all, Shrink / grow, Flip
'   DRAW  the tools: Select, Pen, Line, Centre line, Box, Rounded box, Circle,
'         Arc, Multi line, Text, Eraser, Pick colour, Measure, Button, Area
'   STYLE Colour mixer, Fill, Size 1/2/4/8 (these also change the selection)
'   VIEW  Grid snap, Hide menu
'   HELP  how to use the current tool
' Side panel down the left: an icon for every tool, then DELETE (bin) and
' UNDO. Select a shape and square handles show on its points (line ends,
' box corners, circle/arc points, every Multi line corner, a text's
' spot): drag one to move just that point. With a Multi line corner
' picked, DELETE removes that corner; otherwise it deletes the shape.
' The status bar along the bottom, ticker style: the command in use,
' messages (scrolling when they're long), FILL and GRID (click to
' toggle), the colour swatch with the size in it (click: colour mixer),
' and the pointer's X,Y. Prompts to type take the whole bar.
' ARC  press at the centre, drag out to the start, release, click the end.
' MLIN click the corners; click the first one again (or Enter) to close.
' BTN  drag a rectangle, type a label: a club-style button, in the layout.
' AREA drag a rectangle, type a name (LIST, TICKER...): layout only.
' SAVE name -> name.pic (the shapes, to edit again), name.bmp (the art),
'      name.lay (BUTTON/AREA,name,x,y,w,h per line, for the pages).
' LOAD name -> name.pic, or just name.bmp as a background to draw over.
' Right-click GRID (bottom bar) or VIEW > Grid size sets the grid; the
' snap, the dots and arrow-key nudges all use it.
' RADIUS: click two lines that meet at a corner and give a radius: both
' are cut back and joined by an arc (as in the 3D Model Editor).
' EDIT > Shrink / grow (or the - and + keys, 10% a press): the selected
' shape, or the whole picture when nothing is selected.
' Keys: Tab bar, X shows/hides the X,Y readout, Ctrl-Z undo (up to 100 steps back), Delete removes the selection, arrows nudge
' it, Enter closes a MULTI LINE, Esc cancels, Esc twice quits.

Option EXPLICIT
Option DEFAULT NONE

Const MAXS = 400, MAXP = 3000, MAXPOLY = 64, NT = 16
Const K_PEN = 1, K_LINE = 2, K_CTR = 3, K_BOX = 4, K_RBOX = 5, K_CIRC = 6
Const K_ARC = 7, K_MLIN = 8, K_TEXT = 9, K_BTN = 10, K_AREA = 11

Dim integer W, H, TB, RH, fnt, fw, fhh, uf, ufw, ufh, hasFB, showBar
' the side icon panel: width, each icon's height; the picked handle of
' the selection (-1 none) and the one being dragged
Dim integer PW, icoH, selH, dragH, radA
' ShapeBox's answer: how far a shape reaches
Dim integer bx0, by0, bx1, by1
' the patch the drag preview has drawn on (pvX1 < pvX0 = none yet)
Dim integer pvX0, pvY0, pvX1, pvY1
' shrink / grow: the shapes in the group (sm(i) = 1), how many
Dim integer sm(MAXS - 1), gN
' the icon the pointer is resting on (-1 none, 99 the colour swatch)
Dim integer hoverI
' where the name pop-up is drawn (tipW 0 = none), to take it off again
Dim integer tipX, tipY, tipW, tipH
' click-click shapes: the first click set sx,sy, waiting for the end click;
' and how many reads in a row the mouse button has been up (a blip isn't
' a let-go)
Dim integer twoClick, upReads
' the X,Y readout (VIEW > Show X,Y) and the position it last showed
Dim integer showXY, xyX, xyY
' the status bar: its top, the cells' x positions and widths, the message
' and where its scroll is, and whether a prompt has the whole bar
Dim integer sbY, sbTw, sbMx, sbMw, sbFx, sbGx, sbSx, sbXx, sbXw, sayPos, sayLast, sayWide
Dim string sayMsg$
' auto-hide: the menu and icon panel tuck away while drawing, and come
' back when the pointer touches the top or left edge
Dim integer autoHide
' grid size in pixels (snap and dots); the right mouse button now and before
Dim integer gsz, rdown, wasR, mpr(4)
Dim integer tool, col, size, fil, grd, sel, mx, my, down, wasDown, dragging
Dim integer sx, sy, lastX, lastY, ox, oy, nm, ach, hasMouse, hasTouch, escArmed
Dim integer mch(3), mpx(4), mpy(4), mpl(4), pal(15), hi(15), cur(15), hasMap
Dim string tn$(NT - 1), tl$(NT - 1), kn$(11), mt$(5), k$, fname$, bg$
' the menu titles along the bar, and where the colour swatch is
Dim integer mtx(5), mtw(5), swx
' the shapes: kind (negative = deleted), a-e numbers, fill, colour, size
Dim integer sk(MAXS - 1), sa(MAXS - 1), sb(MAXS - 1), sc(MAXS - 1), sd(MAXS - 1), se(MAXS - 1)
Dim integer sf(MAXS - 1), scl(MAXS - 1), ssz(MAXS - 1), ns
Dim string st$(MAXS - 1) Length 40
' points for PEN strokes and MULTI LINE shapes (sa = first, sb = count)
Dim integer qx(MAXP - 1), qy(MAXP - 1), np, tx(MAXPOLY), ty(MAXPOLY)
' ARC and MULTI LINE in progress
Dim integer arcStage, acx, acy, ar, aa1, mlN
' the change just made: what, which shape, and what to put back
Dim integer uT, uI, uA, uB, uC, uNs, uNp
' the undo history: each change's record (above) pushed here, newest last
Const MAXU = 100
Dim integer usT(MAXU - 1), usI(MAXU - 1), usA(MAXU - 1), usB(MAXU - 1), usC(MAXU - 1)
Dim integer usNs(MAXU - 1), usNp(MAXU - 1), nu, clearGen
' the background picture each Clear all took away, by clear number
Dim string clBg$(MAXU)

Setup
Do
  ReadInput
  k$ = Inkey$
  If k$ <> "" Then KeyPress k$
  If down And Not wasDown Then
    PressAt mx, my
  ElseIf down And dragging Then
    If mx <> lastX Or my <> lastY Then DragTo mx, my
  ElseIf Not down And wasDown And dragging Then
    ReleaseAt mx, my
  ElseIf Not down And (arcStage = 1 Or mlN > 0 Or twoClick) Then
    If mx <> lastX Or my <> lastY Then Rubber mx, my
  ElseIf Not down Then
    Hover
  EndIf
  If rdown And Not wasR And Not down Then RightClick mx, my
  wasR = rdown
  If showXY And (mx <> xyX Or my <> xyY) Then DrawXY
  ScrollSay
  wasDown = down
  Pause 5
Loop

Sub Setup
  Local integer i
  On Error Skip
  MODE 3
  If MM.Errno Then
    On Error Skip
    MODE 2
  EndIf
  W = MM.HRES
  H = MM.VRES
  ' fnt: text drawn into the art; uf: the menus and messages, bigger
  fnt = Choice(W >= 640, 1, 7)
  Font fnt
  fw = MM.Info(FONTWIDTH)
  fhh = MM.Info(FONTHEIGHT)
  uf = Choice(W >= 640, 2, 1)
  Font uf
  ufw = MM.Info(FONTWIDTH)
  ufh = MM.Info(FONTHEIGHT)
  Font fnt
  RH = ufh + 8
  TB = RH
  PW = Choice(W >= 640, 40, 22)
  ' status bar cells, left to right: tool | message | FILL GRID | swatch | X,Y
  sbY = H - RH
  sbTw = 11 * ufw + 12
  sbXw = 13 * ufw + 8
  sbXx = W - sbXw
  sbSx = sbXx - 2 * RH - 4
  sbGx = sbSx - 4 * ufw - 16
  sbFx = sbGx - 4 * ufw - 14
  sbMx = sbTw + 4
  sbMw = sbFx - sbMx - 6
  icoH = (H - TB - RH - 2) \ (NT + 2)
  SetPalette
  Restore Names
  For i = 0 To NT - 1
    Read tn$(i)
  Next
  For i = 0 To NT - 1
    Read tl$(i)
  Next
  For i = 0 To 5
    Read mt$(i)
  Next
  For i = 1 To 11
    Read kn$(i)
  Next
  CLS RGB(BLACK)
  On Error Skip
  FRAMEBUFFER CREATE
  hasFB = (MM.Errno = 0)
  ProbeInputs
  If hasMouse Then
    On Error Skip
    GUI Cursor On 0, W \ 2, H \ 2, RGB(WHITE)
    On Error Skip
    GUI Cursor Load "arrow.spr"
  EndIf
  tool = 1
  col = 7
  size = 1
  sel = -1
  selH = -1
  dragH = -1
  radA = -1
  hoverI = -1
  showXY = 1
  ' auto-hide starts OFF (VIEW > Auto-hide menu turns it on)
  autoHide = 0
  gsz = 8
  xyX = -1
  showBar = 1
  fname$ = "page1"
  PicFolder
  RedrawPic
  Say "Pick a tool from DRAW, a colour from STYLE. Tab hides the menu." + Choice(hasFB, "", " (no framebuffer: slower)")
End Sub

' the 16 colour slots, in the firmware's slot order. With MAP (board 2's
' firmware) each slot can be mixed to any colour: cur() holds what each
' slot shows. hi() is a lighter slot for button highlights.
Sub SetPalette
  Local integer i
  Restore DefaultColours
  For i = 0 To 15
    Read cur(i)
  Next
  On Error Skip
  MAP 0 = cur(0)
  hasMap = (MM.Errno = 0)
  ApplyPal
End Sub

DefaultColours:
Data RGB(BLACK), RGB(BLUE), RGB(MYRTLE), RGB(COBALT), RGB(MIDGREEN), RGB(CERULEAN), RGB(GREEN), RGB(CYAN)
Data RGB(RED), RGB(MAGENTA), RGB(RUST), RGB(FUCHSIA), RGB(BROWN), RGB(LILAC), RGB(YELLOW), RGB(WHITE)

Sub ApplyPal
  Local integer i
  If hasMap Then
    For i = 0 To 15
      MAP i = cur(i)
    Next
    MAP SET
    For i = 0 To 15
      pal(i) = MAP(i)
    Next
  Else
    For i = 0 To 15
      pal(i) = cur(i)
    Next
  EndIf
  For i = 0 To 15
    hi(i) = pal(Nearest(Mix(cur(i), &HFFFFFF, 40), i))
  Next
End Sub

' c1 moved p% of the way to c2
Function Mix(c1 As integer, c2 As integer, p As integer) As integer
  Local integer r, g, b
  r = ((c1 >> 16) And 255) + (((c2 >> 16) And 255) - ((c1 >> 16) And 255)) * p \ 100
  g = ((c1 >> 8) And 255) + (((c2 >> 8) And 255) - ((c1 >> 8) And 255)) * p \ 100
  b = (c1 And 255) + ((c2 And 255) - (c1 And 255)) * p \ 100
  Mix = RGB(r, g, b)
End Function

' the slot (other than skip) whose colour is closest to c
Function Nearest(c As integer, skip As integer) As integer
  Local integer i, d, best
  best = 999999
  Nearest = skip
  For i = 0 To 15
    d = Abs(((c >> 16) And 255) - ((cur(i) >> 16) And 255)) + Abs(((c >> 8) And 255) - ((cur(i) >> 8) And 255)) + Abs((c And 255) - (cur(i) And 255))
    If d < best And i <> skip Then
      best = d
      Nearest = i
    EndIf
  Next
End Function

Names:
Data "SEL", "PEN", "LINE", "CTR", "BOX", "RBOX", "CIRC", "ARC", "MLIN", "TEXT", "ERAS", "PICK", "MEAS", "BTN", "AREA", "RAD"
Data "Select", "Pen", "Line", "Centre line", "Box", "Rounded box", "Circle", "Arc", "Multi line"
Data "Text", "Eraser", "Pick colour", "Measure", "Button", "Area", "Radius"
Data "FILE", "EDIT", "DRAW", "STYLE", "VIEW", "HELP"
Data "PEN", "LINE", "CTR", "BOX", "RBOX", "CIRC", "ARC", "MLIN", "TEXT", "BTN", "AREA"

' --- input ------------------------------------------------------------
Sub ProbeInputs
  Local integer v
  On Error Skip
  v = Touch(X)
  hasTouch = (MM.Errno = 0)
  nm = 0
  For v = 1 To 4
    On Error Skip
    If MM.Info(USB v) = 2 And nm < 4 Then
      mch(nm) = v
      mpx(v) = Device(MOUSE v, X)
      mpy(v) = Device(MOUSE v, Y)
      mpl(v) = Device(MOUSE v, L)
      nm = nm + 1
    EndIf
  Next
  If nm > 0 Then
    hasMouse = 1
    ach = mch(0)
  EndIf
End Sub

' mouse (whichever one moved last) or touch -> mx, my, down
Sub ReadInput
  Local integer i, c, x, y, l, t
  If hasTouch Then
    t = Touch(X)
    If t >= 0 Then
      mx = t
      my = Touch(Y)
      down = 1
      Exit Sub
    EndIf
  EndIf
  down = 0
  If Not hasMouse Then Exit Sub
  For i = 0 To nm - 1
    c = mch(i)
    x = Device(MOUSE c, X)
    y = Device(MOUSE c, Y)
    l = Device(MOUSE c, L)
    If x <> mpx(c) Or y <> mpy(c) Or l <> mpl(c) Then
      ach = c
      mpx(c) = x
      mpy(c) = y
      mpl(c) = l
    EndIf
    On Error Skip
    mpr(c) = Device(MOUSE c, R)
  Next
  rdown = (mpr(ach) <> 0)
  x = Max(0, Min(W - 1, mpx(ach)))
  y = Max(0, Min(H - 1, mpy(ach)))
  If x <> mx Or y <> my Then GUI Cursor x, y
  mx = x
  my = y
  ' the button counts as let go only after 3 reads up in a row, so a blip
  ' in the middle of a drag doesn't end the line and start another
  If mpl(ach) <> 0 Then
    upReads = 0
    down = 1
  Else
    upReads = upReads + 1
    down = (upReads < 3 And wasDown)
  EndIf
End Sub

Sub CurHide
  If hasMouse Then GUI Cursor Hide
End Sub

Sub CurShow
  If hasMouse Then GUI Cursor Show
End Sub

Function Snap(v As integer) As integer
  Snap = Choice(grd, ((v + gsz \ 2) \ gsz) * gsz, v)
End Function

' --- screen -----------------------------------------------------------
' every shape (except AREAs, which aren't art) into the current target
Sub PaintArt
  Local integer i
  CLS RGB(BLACK)
  If bg$ <> "" Then
    On Error Skip
    Load Bmp bg$, 0, 0
  EndIf
  For i = 0 To ns - 1
    If sk(i) > 0 And sk(i) <> K_AREA Then DrawShape i, 0
  Next
End Sub

' rebuild the art after a change, then the screen
Sub RedrawPic
  CurHide
  If hasFB Then
    FRAMEBUFFER WRITE F
    PaintArt
    FRAMEBUFFER WRITE N
  EndIf
  Refresh
End Sub

' the art, AREA frames, grid, selection and tool bar
Sub Refresh
  Local integer i, j
  tipW = 0
  PvNone
  CurHide
  If hasFB Then
    FRAMEBUFFER COPY F, N
  Else
    PaintArt
  EndIf
  For i = 0 To ns - 1
    If sk(i) = K_AREA Then DrawShape i, 0
  Next
  If grd Then
    ' a dot every grid step (every other one for tiny grids)
    For j = 0 To H - 1 Step Choice(gsz < 8, 2 * gsz, gsz)
      For i = 0 To W - 1 Step Choice(gsz < 8, 2 * gsz, gsz)
        Pixel i, j, RGB(GRAY)
      Next
    Next
  EndIf
  If sel >= 0 Then
    DrawShape sel, 1
    DrawHandles sel
  EndIf
  ' the side panel is always there; only the top menu hides
  DrawPanel
  If showBar Then
    DrawBar
  Else
    ' where the menu is: a thin line along the top (touch it with the
    ' pointer, or click the corner, to get it back)
    Line 0, 0, W - 1, 0, 2, RGB(GRAY)
    Box 0, 0, 10, 10, 1, RGB(WHITE), RGB(GRAY)
  EndIf
  DrawStatus
  Tip
  CurShow
End Sub




' the menu bar: titles on the left, what's in use on the right
Sub DrawBar
  Local integer i, x
  Box 0, 0, W, TB, 1, RGB(GRAY), RGB(MYRTLE)
  x = 6
  For i = 0 To 5
    mtx(i) = x
    mtw(i) = Len(mt$(i)) * ufw + 16
    Text x + 8, TB \ 2, mt$(i), "LM", uf, 1, RGB(WHITE), -1
    x = x + mtw(i)
  Next
  ' (the tool, colour and X,Y are on the status bar at the bottom now)
  swx = W + 1
End Sub

' what each menu holds; "*" marks what's on / in use
Function MenuItems$(m As integer)
  Local integer i
  Local string t$
  Select Case m
    Case 0
      t$ = "New|Open...|Save...|Quit"
    Case 1
      t$ = "Undo   Ctrl-Z|Duplicate|Mirror left-right|Delete   Del|Clear all|Shrink / grow...   - +|Flip upside down"
    Case 2
      For i = 0 To NT - 1
        t$ = t$ + Choice(i = tool, "* ", "  ") + tl$(i) + Choice(i < NT - 1, "|", "")
      Next
    Case 3
      t$ = "Colour mixer...|" + Choice(fil, "* ", "  ") + "Fill shapes|"
      For i = 0 To 3
        t$ = t$ + Choice(size = 2 ^ i, "* ", "  ") + "Size " + Str$(2 ^ i) + Choice(i < 3, "|", "")
      Next
    Case 4
      t$ = Choice(grd, "* ", "  ") + "Snap to grid|Grid size (" + Str$(gsz) + ")...|" + Choice(showXY, "* ", "  ") + "Show X,Y   (X key)|" + Choice(autoHide, "* ", "  ") + "Auto-hide menu|Hide menu   Tab"
    Case 5
      t$ = "How to use " + tl$(tool) + "|Keys"
  End Select
  MenuItems$ = t$
End Function

' open menu m under its title; returns the item picked (0 up), or -1
Function Dropdown(m As integer) As integer
  Local string it$(15), t$
  Local integer n, i, x, y, wd, ht, hov, old, p
  t$ = MenuItems$(m)
  Do While t$ <> "" And n < 16
    p = Instr(t$, "|")
    If p = 0 Then p = Len(t$) + 1
    it$(n) = Left$(t$, p - 1)
    t$ = Mid$(t$, p + 1)
    wd = Max(wd, Len(it$(n)))
    n = n + 1
  Loop
  wd = wd * ufw + 24
  x = Min(mtx(m), W - wd - 2)
  y = TB
  ht = n * RH + 4
  CurHide
  Box mtx(m), 0, mtw(m), TB, 1, RGB(WHITE), RGB(MIDGREEN)
  Text mtx(m) + 8, TB \ 2, mt$(m), "LM", uf, 1, RGB(WHITE), -1
  Box x, y, wd, ht, 2, RGB(WHITE), RGB(BLACK)
  For i = 0 To n - 1
    Text x + 10, y + 2 + i * RH + RH \ 2, it$(i), "LM", uf, 1, RGB(WHITE), -1
  Next
  CurShow
  hov = -1
  wasDown = 1
  Dropdown = -1
  Do
    ReadInput
    old = hov
    hov = -1
    If mx >= x And mx < x + wd And my >= y + 2 And my < y + 2 + n * RH Then hov = (my - y - 2) \ RH
    If hov <> old Then
      CurHide
      If old >= 0 Then
        Box x + 2, y + 2 + old * RH, wd - 4, RH, 1, RGB(BLACK), RGB(BLACK)
        Text x + 10, y + 2 + old * RH + RH \ 2, it$(old), "LM", uf, 1, RGB(WHITE), -1
      EndIf
      If hov >= 0 Then
        Box x + 2, y + 2 + hov * RH, wd - 4, RH, 1, RGB(MIDGREEN), RGB(MIDGREEN)
        Text x + 10, y + 2 + hov * RH + RH \ 2, it$(hov), "LM", uf, 1, RGB(WHITE), -1
      EndIf
      CurShow
    EndIf
    If down And Not wasDown Then
      Dropdown = hov
      Exit Do
    EndIf
    wasDown = down
    k$ = Inkey$
    If k$ = Chr$(27) Then Exit Do
    Pause 10
  Loop
  ' wait for the button to come up so the click doesn't also draw
  Do
    ReadInput
    Pause 10
  Loop While down
  wasDown = 0
  Refresh
End Function

Sub MenuPick(m As integer, i As integer)
  If i < 0 Then Exit Sub
  Select Case m
    Case 0
      Select Case i
        Case 0
          ClearAll "Start a new picture? (can not be undone)", 1
        Case 1
          LoadPage
        Case 2
          SavePage
        Case 3
          Quit
      End Select
    Case 1
      Select Case i
        Case 0
          Undo
        Case 1
          DupSel
        Case 2
          If sel < 0 Then
            Say "Pick something with Select first"
          Else
            MirrorShape sel
            uT = 4
            uI = sel
            PushUndo
            RedrawPic
          EndIf
        Case 3
          DelSel
        Case 4
          ClearAll "Clear everything?", 0
        Case 5
          AskScale
        Case 6
          If sel < 0 Then
            Say "Pick something with Select first"
          Else
            FlipShape sel
            uT = 14
            uI = sel
            PushUndo
            RedrawPic
          EndIf
      End Select
    Case 2
      PickTool i
      Refresh
      ToolHelp
    Case 3
      Select Case i
        Case 0
          ColourPicker
        Case 1
          fil = Not fil
          If sel >= 0 Then
            SetProps scl(sel), ssz(sel), fil
          Else
            Refresh
          EndIf
          Say "Fill " + Choice(fil, "on", "off")
        Case Else
          size = 2 ^ (i - 2)
          If sel >= 0 Then
            SetProps scl(sel), size, sf(sel)
          Else
            Refresh
          EndIf
          Say "Size " + Str$(size)
      End Select
    Case 4
      If i = 0 Then
        grd = Not grd
        Refresh
        Say "Snap to a " + Str$(gsz) + " pixel grid " + Choice(grd, "on", "off")
      ElseIf i = 1 Then
        GridSize
      ElseIf i = 2 Then
        ToggleXY
      ElseIf i = 3 Then
        autoHide = Not autoHide
        showBar = 1
        Refresh
        Say "Auto-hide menu " + Choice(autoHide, "on - move into the picture to hide it, touch the top edge to get it back", "off - Tab hides and shows it")
      Else
        showBar = 0
        Refresh
      EndIf
    Case 5
      If i = 0 Then
        ToolHelp
      Else
        Say "Tab menu  Ctrl-Z undo  Del delete  arrows nudge  Enter close shape  Esc cancel"
      EndIf
  End Select
End Sub

Sub ToolHelp
  Select Case tn$(tool)
    Case "SEL"
      Say "Select: click a shape, drag to move, arrows nudge, Del deletes"
    Case "PEN", "ERAS"
      Say tl$(tool) + ": hold the button and draw"
    Case "ARC"
      Say "Arc: press at the centre, drag to the start, release, click the end"
    Case "MLIN"
      Say "Multi line: click each corner, click the first one (or Enter) to close"
    Case "TEXT"
      Say "Text: click where it goes, type, Enter"
    Case "PICK"
      Say "Pick colour: click a shape to use its colour"
    Case "MEAS"
      Say "Measure: drag between two points"
    Case "RAD"
      Say "Radius: click a line, then the line it meets at the corner, then type the radius"
    Case "BTN"
      Say "Button: drag a rectangle, then type its label"
    Case "AREA"
      Say "Area: drag a rectangle, then name it (LIST, TICKER...)"
    Case Else
      Say tl$(tool) + ": drag from one corner (or the centre) to the other"
  End Select
End Sub

' Clear all (undoable): every shape is hidden, not forgotten --
' -(kind + 100 * clear number) -- so UNDO brings back just that clear's
' shapes, even after more drawing. hard = 1 (FILE > New) really starts a
' new picture: everything, and the undo history, goes.
Sub ClearAll(q$, hard As integer)
  Local integer i
  If Not Confirm(q$) Then
    Refresh
    Exit Sub
  EndIf
  MarkNone
  sel = -1
  If hard Then
    ns = 0
    np = 0
    nu = 0
    clearGen = 0
    bg$ = ""
    RedrawPic
    Say "New picture"
    Exit Sub
  EndIf
  If clearGen >= MAXU Then
    Say "Too many clears to undo - use FILE > New"
    Exit Sub
  EndIf
  clearGen = clearGen + 1
  For i = 0 To ns - 1
    If sk(i) > 0 Then sk(i) = -(sk(i) + 100 * clearGen)
  Next
  clBg$(clearGen) = bg$
  uT = 6
  uB = clearGen
  PushUndo
  bg$ = ""
  RedrawPic
  Say "Cleared - UNDO brings it back"
End Sub

' a message along the bottom (shown until the next Refresh)

' the next key; a mouse click or touch counts as Esc (cancel), so a
' prompt never waits invisibly for a keyboard
Function GetKey$()
  Do
    ReadInput
  Loop While down
  Do
    GetKey$ = Inkey$
    ReadInput
    If down Then GetKey$ = Chr$(27)
    Pause 5
  Loop Until GetKey$ <> ""
  Do
    ReadInput
  Loop While down
  wasDown = 0
End Function

' a question in a box with YES and NO buttons to click (or Y / N / Esc
' keys): 1 = yes
Function Confirm(q$) As integer
  Local integer wd, ht, x, y, bw, yx, nx, by
  Local string k$
  wd = Max(Len(q$) * ufw + 40, 300)
  ht = 3 * RH + 30
  x = (W - wd) \ 2
  y = (H - ht) \ 2
  bw = 90
  yx = x + wd \ 2 - bw - 15
  nx = x + wd \ 2 + 15
  by = y + ht - RH - 16
  CurHide
  Box x, y, wd, ht, 2, RGB(WHITE), RGB(BLACK)
  Text x + wd \ 2, y + RH, q$, "CM", uf, 1, RGB(YELLOW), -1
  RBox yx, by, bw, RH + 6, 6, RGB(WHITE), RGB(MIDGREEN)
  Text yx + bw \ 2, by + (RH + 6) \ 2, "YES", "CM", uf, 1, RGB(WHITE), -1
  RBox nx, by, bw, RH + 6, 6, RGB(WHITE), RGB(RED)
  Text nx + bw \ 2, by + (RH + 6) \ 2, "NO", "CM", uf, 1, RGB(WHITE), -1
  CurShow
  Do
    ReadInput
  Loop While down
  wasDown = 0
  Do
    ReadInput
    k$ = UCase$(Inkey$)
    If k$ = "Y" Then
      Confirm = 1
      Exit Do
    EndIf
    If k$ = "N" Or k$ = Chr$(27) Then Exit Do
    If down And Not wasDown Then
      If my >= by And my < by + RH + 6 Then
        If mx >= yx And mx < yx + bw Then
          Confirm = 1
          Exit Do
        EndIf
        If mx >= nx And mx < nx + bw Then Exit Do
      EndIf
    EndIf
    wasDown = down
    Pause 5
  Loop
  Do
    ReadInput
  Loop While down
  wasDown = 0
End Function

' typed input on the bottom line; Esc or a click gives back ""
Function Ask$(p$, d$)
  Local string t$, c$
  t$ = d$
  Do
    sayWide = 1
    sayMsg$ = p$ + " " + t$ + "_   (Enter = OK, click = cancel)"
    DrawSay
    c$ = GetKey$()
    Select Case Asc(c$)
      Case 13
        Exit Do
      Case 27
        t$ = ""
        Exit Do
      Case 8, 127
        If Len(t$) Then t$ = Left$(t$, Len(t$) - 1)
      Case 32 To 126
        If Len(t$) < 40 And c$ <> "," Then t$ = t$ + c$
    End Select
  Loop
  sayWide = 0
  DrawStatus
  Ask$ = t$
End Function

' --- shapes -----------------------------------------------------------
' draw shape i; hl = 1 draws it as a red outline (the selection), moved
' by ox, oy
Sub DrawShape(i As integer, hl As integer)
  Local integer k, c, f, w, j, n, x, y
  k = sk(i)
  If k <= 0 Then Exit Sub
  c = Choice(hl, RGB(RED), pal(scl(i)))
  f = sf(i) And Not hl
  w = Choice(hl, 1, ssz(i))
  x = sa(i) + Choice(hl, ox, 0)
  y = sb(i) + Choice(hl, oy, 0)
  Select Case k
    Case K_PEN
      For j = sa(i) + 1 To sa(i) + sb(i) - 1
        Line qx(j - 1) + ox * hl, qy(j - 1) + oy * hl, qx(j) + ox * hl, qy(j) + oy * hl, w, c
      Next
      If sb(i) = 1 Then Circle qx(sa(i)), qy(sa(i)), Max(1, w \ 2), 1, 1, c, c
    Case K_LINE
      Line x, y, sc(i) + ox * hl, sd(i) + oy * hl, w, c
    Case K_CTR
      DashLine x, y, sc(i) + ox * hl, sd(i) + oy * hl, w, c
    Case K_BOX
      If f Then
        Box x, y, sc(i), sd(i), 1, c, c
      Else
        Box x, y, sc(i), sd(i), w, c
      EndIf
    Case K_RBOX
      If f Then
        RBox x, y, sc(i), sd(i), Max(3, Min(sc(i), sd(i)) \ 5), c, c
      Else
        RBox x, y, sc(i), sd(i), Max(3, Min(sc(i), sd(i)) \ 5), c
      EndIf
    Case K_CIRC
      If f Then
        Circle x, y, sc(i), 1, 1, c, c
      Else
        Circle x, y, sc(i), w, 1, c
      EndIf
    Case K_ARC
      DrawArc x, y, Choice(f, 0, Max(0, sc(i) - w + 1)), sc(i), sd(i), se(i), c
    Case K_MLIN
      n = sb(i)
      For j = 0 To n - 1
        tx(j) = qx(sa(i) + j) + ox * hl
        ty(j) = qy(sa(i) + j) + oy * hl
      Next
      tx(n) = tx(0)
      ty(n) = ty(0)
      If f Then
        Polygon n + 1, tx(), ty(), c, c
      Else
        For j = 1 To n
          Line tx(j - 1), ty(j - 1), tx(j), ty(j), w, c
        Next
      EndIf
    Case K_TEXT
      If hl Then
        Box x - 1, y - 1, Len(st$(i)) * fw * ssz(i) + 2, fhh * ssz(i) + 2, 1, c
      Else
        Text x, y, st$(i), "LT", fnt, ssz(i), c, -1
      EndIf
    Case K_BTN
      If hl Then
        Box x - 1, y - 1, sc(i) + 2, sd(i) + 2, 1, c
      Else
        DrawButton x, y, sc(i), sd(i), st$(i), scl(i)
      EndIf
    Case K_AREA
      Box x, y, sc(i), sd(i), 1, Choice(hl, c, RGB(YELLOW))
      Text x + 2, y + 2, st$(i), "LT", fnt, 1, RGB(YELLOW), -1
  End Select
End Sub

' a centre line: 8 on, 4 off
Sub DashLine(x1 As integer, y1 As integer, x2 As integer, y2 As integer, w As integer, c As integer)
  Local float d, t, t2
  d = Sqr((x2 - x1) ^ 2 + (y2 - y1) ^ 2)
  If d < 1 Then Exit Sub
  For t = 0 To d Step 12
    t2 = Min(d, t + 8)
    Line x1 + (x2 - x1) * t / d, y1 + (y2 - y1) * t / d, x1 + (x2 - x1) * t2 / d, y1 + (y2 - y1) * t2 / d, w, c
  Next
End Sub

' an arc clockwise from a1 to a2 degrees (0 = up); split if it wraps past 0
Sub DrawArc(x As integer, y As integer, r1 As integer, r2 As integer, a1 As integer, a2 As integer, c As integer)
  If r2 < 1 Then Exit Sub
  If a2 > a1 Then
    Arc x, y, r1, r2, a1, a2, c
  Else
    If a1 < 360 Then Arc x, y, r1, r2, a1, 360, c
    If a2 > 0 Then Arc x, y, r1, r2, 0, a2, c
  EndIf
End Sub

' a club-style button: dark edge, lighter top band, label with a shadow
Sub DrawButton(x As integer, y As integer, w As integer, h As integer, t$, ci As integer)
  Local integer r
  If w < 12 Or h < 12 Then Exit Sub
  r = Max(2, h \ 4)
  RBox x, y, w, h, r, RGB(BLACK), pal(ci)
  RBox x + 3, y + 3, w - 6, h \ 2 - 2, Max(1, r - 2), hi(ci), hi(ci)
  If t$ <> "" Then
    Text x + w \ 2 + 1, y + h \ 2 + 1, t$, "CM", fnt, 1, RGB(BLACK), -1
    Text x + w \ 2, y + h \ 2, t$, "CM", fnt, 1, RGB(WHITE), -1
  EndIf
End Sub

' compass angle of (dx, dy) in degrees: 0 up, 90 right
Function Ang(dx As float, dy As float) As integer
  Local float a
  If dy = 0 Then
    a = Choice(dx >= 0, 90, 270)
  Else
    a = Atn(dx / -dy) * 180 / Pi
    If dy > 0 Then a = a + 180
  EndIf
  If a < 0 Then a = a + 360
  Ang = Int(a) Mod 360
End Function

' a new shape with the current colour, size and fill; returns its number
Function NewShape(k As integer, a As integer, b As integer, c As integer, d As integer, t$) As integer
  NewShape = -1
  If ns >= MAXS Then
    Say "Too many shapes (" + Str$(MAXS) + ")"
    Exit Function
  EndIf
  uT = 1
  uNs = ns
  uNp = np
  PushUndo
  sk(ns) = k
  sa(ns) = a
  sb(ns) = b
  sc(ns) = c
  sd(ns) = d
  se(ns) = 0
  sf(ns) = fil
  scl(ns) = col
  ssz(ns) = size
  st$(ns) = t$
  NewShape = ns
  ns = ns + 1
End Function

Function AddPoint(x As integer, y As integer) As integer
  If np >= MAXP Then Exit Function
  qx(np) = x
  qy(np) = y
  np = np + 1
  AddPoint = 1
End Function

' --- hit testing --------------------------------------------------------
Function SegD(x As float, y As float, x1 As float, y1 As float, x2 As float, y2 As float) As float
  Local float dx, dy, t, l2
  dx = x2 - x1
  dy = y2 - y1
  l2 = dx * dx + dy * dy
  If l2 = 0 Then
    SegD = Sqr((x - x1) ^ 2 + (y - y1) ^ 2)
    Exit Function
  EndIf
  t = Max(0, Min(1, ((x - x1) * dx + (y - y1) * dy) / l2))
  SegD = Sqr((x - x1 - t * dx) ^ 2 + (y - y1 - t * dy) ^ 2)
End Function

Function InRect(x As integer, y As integer, i As integer, m As integer) As integer
  InRect = (x >= sa(i) - m And x <= sa(i) + sc(i) + m And y >= sb(i) - m And y <= sb(i) + sd(i) + m)
End Function

' the top shape under x, y (-1 if none)
Function Hit(x As integer, y As integer) As integer
  Local integer i, j, k, tol, n
  Local float d
  Hit = -1
  For i = ns - 1 To 0 Step -1
    k = sk(i)
    tol = 4 + ssz(i) \ 2
    d = 999
    Select Case k
      Case K_PEN, K_MLIN
        n = sb(i)
        For j = 1 To n - 1
          d = Min(d, SegD(x, y, qx(sa(i) + j - 1), qy(sa(i) + j - 1), qx(sa(i) + j), qy(sa(i) + j)))
        Next
        If k = K_MLIN Then d = Min(d, SegD(x, y, qx(sa(i) + n - 1), qy(sa(i) + n - 1), qx(sa(i)), qy(sa(i))))
        If n = 1 Then d = SegD(x, y, qx(sa(i)), qy(sa(i)), qx(sa(i)), qy(sa(i)))
      Case K_LINE, K_CTR
        d = SegD(x, y, sa(i), sb(i), sc(i), sd(i))
      Case K_BOX, K_RBOX
        If InRect(x, y, i, tol) And (sf(i) Or Not InRect(x, y, i, -tol)) Then d = 0
      Case K_BTN, K_AREA
        If InRect(x, y, i, 2) Then d = 0
      Case K_CIRC, K_ARC
        d = Sqr((x - sa(i)) ^ 2 + (y - sb(i)) ^ 2)
        d = Choice(sf(i) And d <= sc(i), 0, Abs(d - sc(i)))
      Case K_TEXT
        If x >= sa(i) And x <= sa(i) + Len(st$(i)) * fw * ssz(i) And y >= sb(i) And y <= sb(i) + fhh * ssz(i) Then d = 0
    End Select
    If k > 0 And d <= tol Then
      Hit = i
      Exit Function
    EndIf
  Next
End Function

' --- changing shapes ----------------------------------------------------
' upside down, about the shape's own middle (MirrorShape's partner)
Sub FlipShape(i As integer)
  Local integer j, lo, hh, t
  Select Case sk(i)
    Case K_PEN, K_MLIN
      lo = 99999
      hh = -99999
      For j = sa(i) To sa(i) + sb(i) - 1
        lo = Min(lo, qy(j))
        hh = Max(hh, qy(j))
      Next
      For j = sa(i) To sa(i) + sb(i) - 1
        qy(j) = lo + hh - qy(j)
      Next
    Case K_LINE, K_CTR
      t = sb(i)
      sb(i) = sd(i)
      sd(i) = t
    Case K_ARC
      ' angles run clockwise from the top: upside down, a -> 180 - a
      t = sd(i)
      sd(i) = (540 - se(i)) Mod 360
      se(i) = (540 - t) Mod 360
  End Select
End Sub

Sub MoveShape(i As integer, dx As integer, dy As integer)
  Local integer j
  Select Case sk(i)
    Case K_PEN, K_MLIN
      For j = sa(i) To sa(i) + sb(i) - 1
        qx(j) = qx(j) + dx
        qy(j) = qy(j) + dy
      Next
    Case K_LINE, K_CTR
      sa(i) = sa(i) + dx
      sb(i) = sb(i) + dy
      sc(i) = sc(i) + dx
      sd(i) = sd(i) + dy
    Case Else
      sa(i) = sa(i) + dx
      sb(i) = sb(i) + dy
  End Select
End Sub

' flip left-right about its own middle
Sub MirrorShape(i As integer)
  Local integer j, lo, hh, t
  Select Case sk(i)
    Case K_PEN, K_MLIN
      lo = 99999
      hh = -99999
      For j = sa(i) To sa(i) + sb(i) - 1
        lo = Min(lo, qx(j))
        hh = Max(hh, qx(j))
      Next
      For j = sa(i) To sa(i) + sb(i) - 1
        qx(j) = lo + hh - qx(j)
      Next
    Case K_LINE, K_CTR
      t = sa(i)
      sa(i) = sc(i)
      sc(i) = t
    Case K_ARC
      t = sd(i)
      sd(i) = (360 - se(i)) Mod 360
      se(i) = (360 - t) Mod 360
  End Select
End Sub

' push the change just recorded in uT..uNp onto the history (the oldest
' drops off once it's full)
Sub PushUndo
  Local integer i
  If nu >= MAXU Then
    For i = 1 To MAXU - 1
      usT(i - 1) = usT(i)
      usI(i - 1) = usI(i)
      usA(i - 1) = usA(i)
      usB(i - 1) = usB(i)
      usC(i - 1) = usC(i)
      usNs(i - 1) = usNs(i)
      usNp(i - 1) = usNp(i)
    Next
    nu = MAXU - 1
  EndIf
  usT(nu) = uT
  usI(nu) = uI
  usA(nu) = uA
  usB(nu) = uB
  usC(nu) = uC
  usNs(nu) = uNs
  usNp(nu) = uNp
  nu = nu + 1
End Sub

' take back the newest change; press again for the one before, and so on
Sub Undo
  Local integer t, i
  If nu = 0 Then
    Say "Nothing (more) to undo"
    Exit Sub
  EndIf
  ' a group resize/move is one record per shape: types 12 and 13 say
  ' "the one below is part of this too", so one Ctrl-Z takes all of it
  Do
  nu = nu - 1
  uI = usI(nu)
  uA = usA(nu)
  uB = usB(nu)
  uC = usC(nu)
  t = usT(nu)
  Select Case t
    Case 1
      ' an added shape (and its points) goes
      ns = usNs(nu)
      np = usNp(nu)
      If sel >= ns Then sel = -1
    Case 2
      sk(uI) = -sk(uI)
    Case 3, 13
      MoveShape uI, -uA, -uB
    Case 4
      MirrorShape uI
    Case 14
      FlipShape uI
    Case 5
      scl(uI) = uA
      ssz(uI) = uB
      sf(uI) = uC
    Case 7
      ' a moved point: the shape's numbers as they were
      sa(uI) = uA
      sb(uI) = uB
      sc(uI) = uC
      sd(uI) = usNs(nu)
      se(uI) = usNp(nu)
    Case 8
      ' a moved Multi line corner
      qx(sa(uI) + uC) = uA
      qy(sa(uI) + uC) = uB
    Case 9
      ' a deleted Multi line corner: back to the old points
      sa(uI) = uA
      sb(uI) = uB
    Case 10, 12
      ' a shrink/grow: the opposite size change about the same middle
      ScaleShape uI, 100 / uA, uB, uC
    Case 6
      ' only the shapes this clear hid (clear number uB)
      For i = 0 To ns - 1
        If sk(i) <= -100 * uB And sk(i) > -100 * (uB + 1) Then sk(i) = -sk(i) - 100 * uB
      Next
      bg$ = clBg$(uB)
      clearGen = uB - 1
  End Select
  Loop While (t = 12 Or t = 13) And nu > 0
  RedrawPic
  Say "Undone - " + Str$(nu) + " more step" + Choice(nu = 1, "", "s") + " to undo"
End Sub

' colour / size / fill of the selection, with undo
Sub SetProps(c As integer, z As integer, f As integer)
  uT = 5
  uI = sel
  uA = scl(sel)
  uB = ssz(sel)
  uC = sf(sel)
  PushUndo
  scl(sel) = c
  ssz(sel) = z
  sf(sel) = f
  RedrawPic
End Sub

' --- tools ----------------------------------------------------------------
Sub PressAt(px As integer, py As integer)
  Local integer i, x, y, h
  x = px
  y = py
  If Not showBar And x < 12 And y < 12 Then
    showBar = 1
    Refresh
    Exit Sub
  EndIf
  If showBar And y < TB Then
    For i = 0 To 5
      If x >= mtx(i) And x < mtx(i) + mtw(i) Then MenuPick i, Dropdown(i)
    Next
    If x >= swx Then ColourPicker
    Exit Sub
  EndIf
  If y >= sbY Then
    StatusClick x
    Exit Sub
  EndIf
  If x < PW And y >= TB And y < TB + (NT + 2) * icoH Then
    PanelClick (y - TB) \ icoH
    Exit Sub
  EndIf
  escArmed = 0
  ' the end click of a click-click line, box, circle...
  If twoClick = 1 Then
    ' 2 = this is the finishing click: ReleaseAt mustn't wait for another
    twoClick = 2
    ReleaseAt x, y
    twoClick = 0
    Exit Sub
  EndIf
  sx = Snap(x)
  sy = Snap(y)
  lastX = x
  lastY = y
  ox = 0
  oy = 0
  Select Case tn$(tool)
    Case "SEL"
      If sel >= 0 Then
        h = HandleAt(sel, x, y)
        If h >= 0 Then
          StartHandle h
          Exit Sub
        EndIf
      EndIf
      h = Hit(x, y)
      If h <> sel Then
        sel = h
        selH = -1
        Refresh
        If sel >= 0 Then Say "Selected " + kn$(sk(sel)) + " - drag it, or drag a square to move that point"
      EndIf
      dragging = (sel >= 0)
    Case "PICK"
      PickAt x, y
    Case "RAD"
      RadClick x, y
    Case "TEXT"
      TextAt sx, sy
    Case "ARC"
      If arcStage = 1 Then
        ArcFinish x, y
      Else
        dragging = 1
      EndIf
    Case "MLIN"
      MlinClick sx, sy
    Case "PEN", "ERAS"
      If np >= MAXP - 2 Then
        Say "No room for more pen strokes"
        Exit Sub
      EndIf
      i = NewShape(K_PEN, np, 1, 0, 0, "")
      If i < 0 Then Exit Sub
      If tn$(tool) = "ERAS" Then
        scl(i) = 0
        ssz(i) = Max(6, size * 3)
      EndIf
      i = AddPoint(sx, sy)
      CurHide
      If hasFB Then
        FRAMEBUFFER WRITE F
        DrawShape ns - 1, 0
        FRAMEBUFFER WRITE N
      EndIf
      DrawShape ns - 1, 0
      CurShow
      dragging = 1
    Case Else
      dragging = 1
  End Select
End Sub


Sub DupSel
  Local integer i, j, a
  If sel < 0 Then
    Say "Pick something with SEL first"
    Exit Sub
  EndIf
  a = sa(sel)
  If sk(sel) = K_PEN Or sk(sel) = K_MLIN Then
    If np + sb(sel) > MAXP Then
      Say "No room for more points"
      Exit Sub
    EndIf
    a = np
  EndIf
  i = NewShape(sk(sel), a, sb(sel), sc(sel), sd(sel), st$(sel))
  If i < 0 Then Exit Sub
  se(i) = se(sel)
  sf(i) = sf(sel)
  scl(i) = scl(sel)
  ssz(i) = ssz(sel)
  If a = np Then
    For j = sa(sel) To sa(sel) + sb(sel) - 1
      a = AddPoint(qx(j), qy(j))
    Next
  EndIf
  MoveShape i, 16, 16
  sel = i
  RedrawPic
  Say "Copied - drag it where you want it"
End Sub

Sub DelSel
  Local integer j, a
  If sel < 0 Then
    Say "Pick something with Select first"
    Exit Sub
  EndIf
  ' a picked Multi line corner goes on its own (a copy of the shape's other
  ' corners is made at the end of the points; UNDO points back at the old)
  If sk(sel) = K_MLIN And selH >= 0 And sb(sel) > 3 Then
    If np + sb(sel) > MAXP Then
      Say "No room to change that shape"
      Exit Sub
    EndIf
    uT = 9
    uI = sel
    uA = sa(sel)
    uB = sb(sel)
    PushUndo
    a = np
    For j = 0 To sb(sel) - 1
      If j <> selH Then a = AddPoint(qx(sa(sel) + j), qy(sa(sel) + j))
    Next
    sa(sel) = np - (sb(sel) - 1)
    sb(sel) = sb(sel) - 1
    selH = -1
    RedrawPic
    Say "Corner deleted (UNDO brings it back)"
    Exit Sub
  EndIf
  uT = 2
  uI = sel
  PushUndo
  sk(sel) = -sk(sel)
  sel = -1
  selH = -1
  RedrawPic
  Say "Deleted (UNDO brings it back)"
End Sub

Sub DragTo(px As integer, py As integer)
  Local integer x, y, i
  Local float d
  lastX = px
  lastY = py
  x = Snap(px)
  y = Snap(py)
  Select Case tn$(tool)
    Case "PEN", "ERAS"
      i = ns - 1
      If x = qx(np - 1) And y = qy(np - 1) Then Exit Sub
      If Not AddPoint(x, y) Then Exit Sub
      sb(i) = sb(i) + 1
      CurHide
      If hasFB Then
        FRAMEBUFFER WRITE F
        Line qx(np - 2), qy(np - 2), x, y, ssz(i), pal(scl(i))
        FRAMEBUFFER WRITE N
      EndIf
      Line qx(np - 2), qy(np - 2), x, y, ssz(i), pal(scl(i))
      CurShow
    Case "SEL"
      If dragH >= 0 Then
        PvShape sel
        SetHandle sel, dragH, x, y
        Preview
        CurHide
        DrawShape sel, 0
        DrawShape sel, 1
        DrawHandles sel
        CurShow
        PvShape sel
        Exit Sub
      EndIf
      PvShape sel
      ox = x - sx
      oy = y - sy
      Preview
    Case Else
      Preview
      CurHide
      Shape sx, sy, x, y
      CurShow
      PvRubber sx, sy, x, y
      If tn$(tool) = "MEAS" Then
        d = Sqr((x - sx) ^ 2 + (y - sy) ^ 2)
        Say "Length " + Str$(d, 0, 1) + "  across " + Str$(Abs(x - sx) + 1) + "  down " + Str$(Abs(y - sy) + 1) + "  from " + Str$(sx) + "," + Str$(sy)
      EndIf
  End Select
End Sub

' the screen as it is, ready for a preview on top. With the framebuffer
' only the patch the last preview drew on is put back (the whole screen
' every mouse move flashed and lagged)
Sub Preview
  Local integer b
  If Not hasFB Then
    b = showBar
    showBar = 0
    Refresh
    showBar = b
    Exit Sub
  EndIf
  If pvX1 >= pvX0 Then PutBack pvX0, pvY0, pvX1, pvY1
  PvNone
  If sel >= 0 Then
    CurHide
    DrawShape sel, 1
    DrawHandles sel
    CurShow
    PvShape sel
  EndIf
End Sub

Sub PvNone
  pvX0 = 99999
  pvY0 = 99999
  pvX1 = -99999
  pvY1 = -99999
End Sub

' the preview is about to draw between these corners (any order)
Sub PvAdd(x1 As integer, y1 As integer, x2 As integer, y2 As integer)
  Local integer m
  m = Max(size, 4) + 6
  pvX0 = Min(pvX0, Min(x1, x2) - m)
  pvY0 = Min(pvY0, Min(y1, y2) - m)
  pvX1 = Max(pvX1, Max(x1, x2) + m)
  pvY1 = Max(pvY1, Max(y1, y2) + m)
End Sub

' shape i as the selection draws it (moved by ox, oy), and its handles
Sub PvShape(i As integer)
  ShapeBox i
  PvAdd bx0 + ox, by0 + oy, bx1 + ox, by1 + oy
  PvAdd bx0, by0, bx1, by1
End Sub

' the rubber-band shape from (x1,y1) to (x2,y2), as Shape draws it
Sub PvRubber(x1 As integer, y1 As integer, x2 As integer, y2 As integer)
  Local integer r
  If tn$(tool) = "CIRC" Or tn$(tool) = "ARC" Then
    r = Int(Sqr((x2 - x1) ^ 2 + (y2 - y1) ^ 2)) + 1
    PvAdd x1 - r, y1 - r, x1 + r, y1 + r
  Else
    PvAdd x1, y1, x2, y2
  EndIf
End Sub

' the finished picture back over one patch of screen, and whatever sits
' on top of it there (grid dots, AREA frames, panel, bars)
Sub PutBack(x0 As integer, y0 As integer, x1 As integer, y1 As integer)
  Local integer i, j, st
  x0 = Max(0, x0)
  y0 = Max(0, y0)
  x1 = Min(W - 1, x1)
  y1 = Min(H - 1, y1)
  If x1 < x0 Or y1 < y0 Then Exit Sub
  CurHide
  BLIT FRAMEBUFFER F, N, x0, y0, x0, y0, x1 - x0 + 1, y1 - y0 + 1
  If grd Then
    st = Choice(gsz < 8, 2 * gsz, gsz)
    For j = (y0 + st - 1) \ st * st To y1 Step st
      For i = (x0 + st - 1) \ st * st To x1 Step st
        Pixel i, j, RGB(GRAY)
      Next
    Next
  EndIf
  For i = 0 To ns - 1
    If sk(i) = K_AREA Then DrawShape i, 0
  Next
  If x0 < PW And y1 >= TB And y0 < TB + (NT + 2) * icoH Then DrawPanel
  If y0 < TB Then
    If showBar Then
      DrawBar
    Else
      Line 0, 0, W - 1, 0, 2, RGB(GRAY)
      Box 0, 0, 10, 10, 1, RGB(WHITE), RGB(GRAY)
    EndIf
  EndIf
  If y1 >= sbY Then DrawStatus
  If tipW Then
    If x0 < tipX + tipW And x1 >= tipX And y0 < tipY + tipH And y1 >= tipY Then
      tipW = 0
      hoverI = -1
    EndIf
  EndIf
  CurShow
End Sub

' the rubber-band shape while dragging, from (x1,y1) to (x2,y2)
Sub Shape(x1 As integer, y1 As integer, x2 As integer, y2 As integer)
  Local integer x, y, w, h, r, c
  x = Min(x1, x2)
  y = Min(y1, y2)
  w = Abs(x2 - x1) + 1
  h = Abs(y2 - y1) + 1
  r = Int(Sqr((x2 - x1) ^ 2 + (y2 - y1) ^ 2))
  c = pal(col)
  Select Case tn$(tool)
    Case "LINE"
      Line x1, y1, x2, y2, size, c
    Case "CTR"
      DashLine x1, y1, x2, y2, size, c
    Case "BOX"
      Box x, y, w, h, Choice(fil, 1, size), c, Choice(fil, c, -1)
    Case "RBOX"
      If w > 8 And h > 8 Then RBox x, y, w, h, Max(3, Min(w, h) \ 5), c, Choice(fil, c, -1)
    Case "CIRC", "ARC"
      If r > 0 Then Circle x1, y1, r, 1, 1, c
      If tn$(tool) = "ARC" Then Line x1, y1, x2, y2, 1, RGB(GRAY)
    Case "BTN"
      DrawButton x, y, w, h, "", col
    Case "AREA", "MEAS"
      Box x, y, w, h, 1, RGB(YELLOW)
      If tn$(tool) = "MEAS" Then Line x1, y1, x2, y2, 1, RGB(YELLOW)
  End Select
End Sub

Sub ReleaseAt(px As integer, py As integer)
  Local integer x, y, i
  Local string t$
  dragging = 0
  x = Snap(px)
  y = Snap(py)
  ' let go where it started: a click, not a drag -- the end comes with the
  ' next click, and the shape follows the pointer until then
  If Abs(x - sx) < 4 And Abs(y - sy) < 4 And twoClick = 0 Then
    Select Case tn$(tool)
      Case "LINE", "CTR", "BOX", "RBOX", "CIRC", "MEAS", "BTN", "AREA"
        twoClick = 1
        Say "Now click where it ends (Esc cancels)"
        Exit Sub
    End Select
  EndIf
  Select Case tn$(tool)
    Case "PEN", "ERAS"
      Refresh
      Exit Sub
    Case "SEL"
      If dragH >= 0 Then
        dragH = -1
        RedrawPic
        Exit Sub
      EndIf
      If ox <> 0 Or oy <> 0 Then
        MoveShape sel, ox, oy
        uT = 3
        uI = sel
        uA = ox
        uB = oy
        PushUndo
        ox = 0
        oy = 0
        RedrawPic
      EndIf
      Exit Sub
    Case "MEAS"
      Refresh
      Say "Length " + Str$(Sqr((x - sx) ^ 2 + (y - sy) ^ 2), 0, 1) + "  across " + Str$(Abs(x - sx) + 1) + "  down " + Str$(Abs(y - sy) + 1)
      Exit Sub
    Case "ARC"
      ar = Int(Sqr((x - sx) ^ 2 + (y - sy) ^ 2))
      If ar < 3 Then
        Refresh
        Exit Sub
      EndIf
      acx = sx
      acy = sy
      aa1 = Ang(x - sx, y - sy)
      arcStage = 1
      Say "Now click where the arc ends (it goes clockwise)"
      Exit Sub
    Case "LINE", "CTR"
      i = NewShape(Choice(tn$(tool) = "LINE", K_LINE, K_CTR), sx, sy, x, y, "")
    Case "CIRC"
      i = NewShape(K_CIRC, sx, sy, Int(Sqr((x - sx) ^ 2 + (y - sy) ^ 2)), 0, "")
    Case "BOX", "RBOX", "BTN", "AREA"
      If Abs(x - sx) < 6 Or Abs(y - sy) < 6 Then
        Refresh
        Say "Drag out a bigger rectangle"
        Exit Sub
      EndIf
      If tn$(tool) = "BTN" Or tn$(tool) = "AREA" Then
        t$ = UCase$(Ask$(Choice(tn$(tool) = "BTN", "Button label:", "Area name (LIST, TICKER...):"), ""))
        If t$ = "" Then
          Refresh
          Exit Sub
        EndIf
      EndIf
      Select Case tn$(tool)
        Case "BOX"
          i = K_BOX
        Case "RBOX"
          i = K_RBOX
        Case "BTN"
          i = K_BTN
        Case Else
          i = K_AREA
      End Select
      i = NewShape(i, Min(sx, x), Min(sy, y), Abs(x - sx) + 1, Abs(y - sy) + 1, t$)
  End Select
  RedrawPic
End Sub

Sub Rubber(px As integer, py As integer)
  Local integer j, x, y
  lastX = px
  lastY = py
  x = Snap(px)
  y = Snap(py)
  Preview
  CurHide
  If twoClick Then
    Shape sx, sy, x, y
    PvRubber sx, sy, x, y
  ElseIf arcStage = 1 Then
    PvAdd acx - ar, acy - ar, acx + ar, acy + ar
    Circle acx, acy, ar, 1, 1, RGB(GRAY)
    DrawArc acx, acy, Max(0, ar - size + 1), ar, aa1, Ang(x - acx, y - acy), pal(col)
  Else
    For j = 1 To mlN - 1
      Line tx(j - 1), ty(j - 1), tx(j), ty(j), size, pal(col)
      PvAdd tx(j - 1), ty(j - 1), tx(j), ty(j)
    Next
    Line tx(mlN - 1), ty(mlN - 1), x, y, 1, pal(col)
    PvAdd tx(mlN - 1), ty(mlN - 1), x, y
    Circle tx(0), ty(0), 6, 1, 1, RGB(YELLOW)
    PvAdd tx(0) - 8, ty(0) - 8, tx(0) + 8, ty(0) + 8
  EndIf
  CurShow
End Sub

Sub ArcFinish(x As integer, y As integer)
  Local integer i
  arcStage = 0
  i = NewShape(K_ARC, acx, acy, ar, aa1, "")
  If i >= 0 Then se(i) = Ang(x - acx, y - acy)
  RedrawPic
End Sub

' MULTI LINE: collect corners in tx/ty; closing makes the shape
Sub MlinClick(x As integer, y As integer)
  If mlN >= 3 And Abs(x - tx(0)) < 8 And Abs(y - ty(0)) < 8 Then
    MlinClose
    Exit Sub
  EndIf
  If mlN >= MAXPOLY - 1 Then
    MlinClose
    Exit Sub
  EndIf
  tx(mlN) = x
  ty(mlN) = y
  mlN = mlN + 1
  Say "Corner " + Str$(mlN) + Choice(mlN >= 3, " - click the first corner or Enter to close", "")
End Sub

Sub MlinClose
  Local integer i, j, a
  If mlN < 3 Then
    Say "A MULTI LINE needs 3 corners or more"
    Exit Sub
  EndIf
  If np + mlN > MAXP Then
    mlN = 0
    Say "No room for more points"
    Exit Sub
  EndIf
  i = NewShape(K_MLIN, np, mlN, 0, 0, "")
  If i >= 0 Then
    For j = 0 To mlN - 1
      a = AddPoint(tx(j), ty(j))
    Next
  EndIf
  mlN = 0
  RedrawPic
End Sub

' type straight onto the picture; Enter keeps it, Esc drops it
Sub TextAt(x As integer, y As integer)
  Local string t$, c$
  Local integer sc2, i
  sc2 = Max(1, Min(4, size))
  Do
    Refresh
    CurHide
    Text x, y, t$ + "_", "LT", fnt, sc2, pal(col), -1
    CurShow
    Say "Type the text, Enter to keep it, Esc or click to drop it"
    c$ = GetKey$()
    Select Case Asc(c$)
      Case 13
        Exit Do
      Case 27
        t$ = ""
        Exit Do
      Case 8, 127
        If Len(t$) Then t$ = Left$(t$, Len(t$) - 1)
      Case 32 To 126
        If Len(t$) < 40 Then t$ = t$ + c$
    End Select
  Loop
  If t$ <> "" Then
    i = NewShape(K_TEXT, x, y, 0, 0, t$)
    If i >= 0 Then ssz(i) = sc2
  EndIf
  RedrawPic
End Sub

Sub PickAt(x As integer, y As integer)
  Local integer c, i, h
  h = Hit(x, y)
  If h >= 0 Then
    col = scl(h)
  Else
    CurHide
    If hasFB Then FRAMEBUFFER WRITE F
    c = Pixel(x, y)
    If hasFB Then FRAMEBUFFER WRITE N
    For i = 0 To 15
      If pal(i) = c Then col = i
    Next
  EndIf
  Refresh
  Say "Colour " + Str$(col)
End Sub

' --- shrink / grow ---------------------------------------------------------
' EDIT > Shrink / grow. With a shape selected: that shape. Otherwise drag
' a box round the part to resize (Enter = the whole picture), type a
' percent (50 = half, 200 = double), then click where it goes. E.g. draw a
' button big for the detail, then shrink it onto the background.
' After that the - and + keys resize the same shapes 10% a press.
Sub AskScale
  Local string p$
  Local integer r
  If sel >= 0 Then
    MarkSel
  Else
    r = PickBox()
    If r = 0 Then
      Refresh
      Exit Sub
    EndIf
    If r = 2 Then
      MarkAll
    Else
      MarkBox
    EndIf
    If gN = 0 Then
      Refresh
      Say "Nothing drawn fully inside that box"
      Exit Sub
    EndIf
  EndIf
  Refresh
  p$ = Ask$(Str$(gN) + Choice(gN = 1, " shape", " shapes") + " - size in % (50 = half, 200 = double):", "50")
  If Val(p$) <= 0 Then
    Refresh
    Exit Sub
  EndIf
  If Not ScaleBy(Val(p$)) Then Exit Sub
  If r = 1 Then PlaceGroup
End Sub

' - and + keys: the selected shape, else the last group, else everything
Sub ScaleKey(p As integer)
  If sel >= 0 Then
    MarkSel
  ElseIf gN = 0 Then
    MarkAll
  EndIf
  If ScaleBy(p) Then Say Str$(gN) + Choice(gN = 1, " shape", " shapes") + " to " + Str$(p) + "%  (- smaller, + bigger, Ctrl-Z undoes)"
End Sub

Sub MarkNone
  Local integer i
  For i = 0 To MAXS - 1
    sm(i) = 0
  Next
  gN = 0
End Sub

Sub MarkSel
  MarkNone
  sm(sel) = 1
  gN = 1
End Sub

Sub MarkAll
  Local integer i
  MarkNone
  For i = 0 To ns - 1
    If sk(i) > 0 Then
      sm(i) = 1
      gN = gN + 1
    EndIf
  Next
End Sub

' every shape wholly inside the box PickBox left in bx0..by1
Sub MarkBox
  Local integer i, x0, y0, x1, y1
  x0 = bx0 : y0 = by0 : x1 = bx1 : y1 = by1
  MarkNone
  For i = 0 To ns - 1
    If sk(i) > 0 Then
      ShapeBox i
      If bx0 >= x0 And by0 >= y0 And bx1 <= x1 And by1 <= y1 Then
        sm(i) = 1
        gN = gN + 1
      EndIf
    EndIf
  Next
End Sub

' drag a box: 1 = got one (bx0,by0 to bx1,by1), 2 = Enter (the whole
' picture), 0 = cancelled
Function PickBox() As integer
  Local integer x0, y0, lx, ly
  Local string c$
  Say "Drag a box round what to resize  (Enter = whole picture, Esc = cancel)"
  Do
    ReadInput
  Loop While down
  wasDown = 0
  Do
    ReadInput
    c$ = Inkey$
    If c$ = Chr$(13) Then
      PickBox = 2
      Exit Function
    EndIf
    If c$ = Chr$(27) Then Exit Function
    If showXY And (mx <> xyX Or my <> xyY) Then DrawXY
    Pause 5
  Loop Until down
  x0 = mx
  y0 = my
  lx = -1
  Do
    ReadInput
    If mx <> lx Or my <> ly Then
      Preview
      CurHide
      Box Min(x0, mx), Min(y0, my), Abs(mx - x0) + 1, Abs(my - y0) + 1, 1, RGB(YELLOW)
      CurShow
      PvAdd x0, y0, mx, my
      lx = mx
      ly = my
    EndIf
    wasDown = down
    Pause 5
  Loop While down
  wasDown = 0
  bx0 = Min(x0, mx) : by0 = Min(y0, my) : bx1 = Max(x0, mx) : by1 = Max(y0, my)
  If bx1 - bx0 < 4 Or by1 - by0 < 4 Then Exit Function
  PickBox = 1
End Function

' resize the marked shapes about the middle of them all; one Ctrl-Z
' puts them all back
Function ScaleBy(p As integer) As integer
  Local integer i, x0, y0, x1, y1, cx, cy, first
  If p < 5 Or p > 1000 Then
    Say "Pick a size from 5% to 1000%"
    Exit Function
  EndIf
  If gN = 0 Then
    Say "Nothing drawn yet to resize"
    Exit Function
  EndIf
  x0 = 99999 : y0 = 99999 : x1 = -99999 : y1 = -99999
  For i = 0 To ns - 1
    If sm(i) And sk(i) > 0 Then
      ShapeBox i
      x0 = Min(x0, bx0) : y0 = Min(y0, by0) : x1 = Max(x1, bx1) : y1 = Max(y1, by1)
    EndIf
  Next
  cx = (x0 + x1) \ 2
  cy = (y0 + y1) \ 2
  first = 1
  For i = 0 To ns - 1
    If sm(i) And sk(i) > 0 Then
      ScaleShape i, p / 100, cx, cy
      ' the first one ends the chain Ctrl-Z follows (see Undo)
      uT = Choice(first, 10, 12)
      uI = i
      uA = p
      uB = cx
      uC = cy
      PushUndo
      first = 0
    EndIf
  Next
  RedrawPic
  ScaleBy = 1
End Function

' click where the resized group goes (its middle lands on the click)
Sub PlaceGroup
  Local integer i, x0, y0, x1, y1, dx, dy, first
  Local string c$
  Say "Click where it goes  (Esc = leave it here)"
  Do
    ReadInput
  Loop While down
  wasDown = 0
  Do
    ReadInput
    c$ = Inkey$
    If c$ = Chr$(27) Then
      Say "Resized - - and + keys resize it again"
      Exit Sub
    EndIf
    If showXY And (mx <> xyX Or my <> xyY) Then DrawXY
    Pause 5
  Loop Until down
  Do
    ReadInput
  Loop While down
  wasDown = 0
  x0 = 99999 : y0 = 99999 : x1 = -99999 : y1 = -99999
  For i = 0 To ns - 1
    If sm(i) And sk(i) > 0 Then
      ShapeBox i
      x0 = Min(x0, bx0) : y0 = Min(y0, by0) : x1 = Max(x1, bx1) : y1 = Max(y1, by1)
    EndIf
  Next
  dx = Snap(mx) - (x0 + x1) \ 2
  dy = Snap(my) - (y0 + y1) \ 2
  first = 1
  For i = 0 To ns - 1
    If sm(i) And sk(i) > 0 Then
      MoveShape i, dx, dy
      uT = Choice(first, 3, 13)
      uI = i
      uA = dx
      uB = dy
      PushUndo
      first = 0
    EndIf
  Next
  RedrawPic
  Say "Placed - - and + keys resize it again, Ctrl-Z undoes the move"
End Sub

' how far shape i reaches: bx0,by0 to bx1,by1
Sub ShapeBox(i As integer)
  Local integer j
  Select Case sk(i)
    Case K_PEN, K_MLIN
      bx0 = 99999 : by0 = 99999 : bx1 = -99999 : by1 = -99999
      For j = sa(i) To sa(i) + sb(i) - 1
        bx0 = Min(bx0, qx(j)) : by0 = Min(by0, qy(j))
        bx1 = Max(bx1, qx(j)) : by1 = Max(by1, qy(j))
      Next
    Case K_LINE, K_CTR
      bx0 = Min(sa(i), sc(i)) : bx1 = Max(sa(i), sc(i))
      by0 = Min(sb(i), sd(i)) : by1 = Max(sb(i), sd(i))
    Case K_CIRC, K_ARC
      bx0 = sa(i) - sc(i) : bx1 = sa(i) + sc(i)
      by0 = sb(i) - sc(i) : by1 = sb(i) + sc(i)
    Case K_TEXT
      bx0 = sa(i) : by0 = sb(i)
      bx1 = sa(i) + Len(st$(i)) * fw * ssz(i) : by1 = sb(i) + fhh * ssz(i)
    Case Else
      ' boxes, buttons, areas: x, y, width, height
      bx0 = sa(i) : by0 = sb(i) : bx1 = sa(i) + sc(i) : by1 = sb(i) + sd(i)
  End Select
End Sub

' shape i f times the size, about (cx, cy); line widths and text size stay
Sub ScaleShape(i As integer, f As float, cx As integer, cy As integer)
  Local integer j
  Select Case sk(i)
    Case K_PEN, K_MLIN
      For j = sa(i) To sa(i) + sb(i) - 1
        qx(j) = cx + Cint((qx(j) - cx) * f)
        qy(j) = cy + Cint((qy(j) - cy) * f)
      Next
    Case K_LINE, K_CTR
      sa(i) = cx + Cint((sa(i) - cx) * f)
      sb(i) = cy + Cint((sb(i) - cy) * f)
      sc(i) = cx + Cint((sc(i) - cx) * f)
      sd(i) = cy + Cint((sd(i) - cy) * f)
    Case K_CIRC, K_ARC
      sa(i) = cx + Cint((sa(i) - cx) * f)
      sb(i) = cy + Cint((sb(i) - cy) * f)
      sc(i) = Max(1, Cint(sc(i) * f))
    Case K_TEXT
      sa(i) = cx + Cint((sa(i) - cx) * f)
      sb(i) = cy + Cint((sb(i) - cy) * f)
      ssz(i) = Max(1, Cint(ssz(i) * f))
    Case Else
      sa(i) = cx + Cint((sa(i) - cx) * f)
      sb(i) = cy + Cint((sb(i) - cy) * f)
      sc(i) = Max(1, Cint(sc(i) * f))
      sd(i) = Max(1, Cint(sd(i) * f))
  End Select
End Sub

' --- files --------------------------------------------------------------
Sub SavePage
  Local string n$, l$
  Local integer i, j
  n$ = Ask$("Save as (no extension):", fname$)
  If n$ = "" Then
    Refresh
    Exit Sub
  EndIf
  fname$ = n$
  On Error Skip
  Open n$ + ".pic" For Output As #1
  If MM.Errno Then
    Refresh
    Say "Couldn't save: " + MM.ErrMsg$
    Exit Sub
  EndIf
  If bg$ <> "" Then Print #1, "BG,0,0,0,0,0,0,0,0," + bg$
  ' the mixed colours, so the picture comes back looking the same
  If hasMap Then
    l$ = "PAL"
    For i = 0 To 15
      l$ = l$ + "," + Hex$(cur(i), 6)
    Next
    Print #1, l$
  EndIf
  For i = 0 To ns - 1
    If sk(i) > 0 Then
      ' in two halves: one line of MMBasic can be at most 255 characters
      Print #1, kn$(sk(i)) + "," + Choice(sk(i) = K_PEN Or sk(i) = K_MLIN, Str$(sb(i)), Str$(sa(i))) + "," + Str$(sb(i)) + "," + Str$(sc(i)) + ",";
      Print #1, Str$(sd(i)) + "," + Str$(se(i)) + "," + Str$(sf(i)) + "," + Str$(scl(i)) + "," + Str$(ssz(i)) + "," + st$(i)
      If sk(i) = K_PEN Or sk(i) = K_MLIN Then
        For j = sa(i) To sa(i) + sb(i) - 1
          Print #1, Str$(qx(j)) + "," + Str$(qy(j))
        Next
      EndIf
    EndIf
  Next
  Close #1
  Open n$ + ".lay" For Output As #1
  For i = 0 To ns - 1
    If sk(i) = K_BTN Or sk(i) = K_AREA Then
      Print #1, Choice(sk(i) = K_BTN, "BUTTON", "AREA") + "," + st$(i) + "," + Str$(sa(i)) + "," + Str$(sb(i)) + "," + Str$(sc(i)) + "," + Str$(sd(i))
    EndIf
  Next
  Close #1
  ' the art alone: no bar, frames, selection or pointer
  CurHide
  If hasFB Then
    FRAMEBUFFER COPY F, N
  Else
    PaintArt
  EndIf
  On Error Skip
  Save Image n$ + ".bmp"
  i = MM.Errno
  Refresh
  If i Then
    Say "Saved " + n$ + ".pic and .lay, but not the .bmp: " + MM.ErrMsg$
  Else
    Say "Saved " + n$ + ".pic, .bmp and .lay in " + Cwd$
  EndIf
End Sub

Sub LoadPage
  Local string n$, l$
  Local integer i, j, k, p, c
  MarkNone
  n$ = FilePick$()
  If n$ = "" Then
    Refresh
    Exit Sub
  EndIf
  On Error Skip
  Open n$ + ".pic" For Input As #1
  If MM.Errno Then
    ' no shapes file: use the picture as a background to draw over
    If BmpSize(n$) < 0 Then
      Refresh
      Say "No " + n$ + ".pic or " + n$ + ".bmp"
      Exit Sub
    EndIf
    ns = 0
    np = 0
    bg$ = n$ + ".bmp"
  Else
    ns = 0
    np = 0
    bg$ = ""
    Do While Not Eof(#1) And ns < MAXS
      Line Input #1, l$
      If Field$(l$, 1, ",") = "PAL" Then
        For i = 0 To 15
          cur(i) = Val("&H" + Field$(l$, i + 2, ","))
        Next
        If hasMap Then ApplyPal
      ElseIf Field$(l$, 1, ",") = "BG" Then
        bg$ = Mid$(l$, Instr(l$, ",0,0,0,0,0,0,0,0,") + 17)
      ElseIf l$ <> "" Then
        k = 0
        For i = 1 To 11
          If kn$(i) = Field$(l$, 1, ",") Then k = i
        Next
        If k > 0 Then
          ' the text is everything after the 9th comma (it may hold commas)
          p = 0
          For i = 1 To 9
            p = Instr(p + 1, l$, ",")
          Next
          sk(ns) = k
          sa(ns) = Val(Field$(l$, 2, ","))
          sb(ns) = Val(Field$(l$, 3, ","))
          sc(ns) = Val(Field$(l$, 4, ","))
          sd(ns) = Val(Field$(l$, 5, ","))
          se(ns) = Val(Field$(l$, 6, ","))
          sf(ns) = Val(Field$(l$, 7, ","))
          scl(ns) = Val(Field$(l$, 8, ","))
          ssz(ns) = Val(Field$(l$, 9, ","))
          st$(ns) = Choice(p > 0, Mid$(l$, p + 1), "")
          If k = K_PEN Or k = K_MLIN Then
            c = sa(ns)
            sa(ns) = np
            sb(ns) = 0
            For j = 1 To c
              If Not Eof(#1) Then
                Line Input #1, l$
                If AddPoint(Val(Field$(l$, 1, ",")), Val(Field$(l$, 2, ","))) Then sb(ns) = sb(ns) + 1
              EndIf
            Next
          EndIf
          ns = ns + 1
        EndIf
      EndIf
    Loop
    Close #1
  EndIf
  fname$ = Mid$(n$, Choice(Instr(n$, "/club/"), Instr(n$, "/club/") + 6, 1))
  sel = -1
  uT = 0
  nu = 0
  clearGen = 0
  RedrawPic
  Say "Loaded " + n$ + " (" + Str$(ns) + " shapes)" + Choice(bg$ = "", "", " on " + bg$)
End Sub

Sub KeyPress(c$)
  Local integer d
  d = Choice(grd, gsz, 1)
  Select Case Asc(c$)
    Case 9
      showBar = Not showBar
      Refresh
    Case 26
      Undo
    Case 88, 120
      ToggleXY
    Case 13
      If mlN > 0 Then MlinClose
    Case 127
      DelSel
    Case 128 To 131
      If sel >= 0 Then
        Select Case Asc(c$)
          Case 128
            MoveShape sel, 0, -d
            uB = -d
            uA = 0
          Case 129
            MoveShape sel, 0, d
            uB = d
            uA = 0
          Case 130
            MoveShape sel, -d, 0
            uA = -d
            uB = 0
          Case 131
            MoveShape sel, d, 0
            uA = d
            uB = 0
        End Select
        uT = 3
        uI = sel
        PushUndo
        RedrawPic
      EndIf
    Case 45
      ScaleKey 90
    Case 43, 61
      ScaleKey 110
    Case 27
      If arcStage Or mlN Or twoClick Then
        arcStage = 0
        mlN = 0
        twoClick = 0
        Refresh
        Say "Cancelled"
      ElseIf sel >= 0 Then
        sel = -1
        Refresh
      ElseIf escArmed Then
        Quit
      Else
        escArmed = 1
        Say "Esc again to quit (unsaved work is lost)"
      EndIf
  End Select
End Sub

' B:/draw, made if it isn't there; the SD card's own folder if no B:
Sub PicFolder
  On Error Skip
  Drive "B:"
  If MM.Errno Then Exit Sub
  On Error Skip
  Chdir "/"
  If Dir$("draw", DIR) = "" Then
    On Error Skip
    MkDir "draw"
  EndIf
  On Error Skip
  Chdir "/draw"
End Sub

Sub Quit
  If Not Confirm("Quit draw? Anything not saved is lost.") Then
    escArmed = 0
    Refresh
    Exit Sub
  EndIf
  If hasMouse Then GUI Cursor Off
  If hasFB Then
    FRAMEBUFFER WRITE N
    FRAMEBUFFER CLOSE
  EndIf
  CLS
  ' back to the club's folder, where the pages expect to be
  On Error Skip
  Chdir "/club"
  End
End Sub

' --- colour mixer ---------------------------------------------------------
Function Bright(c As integer) As integer
  Bright = (((c >> 16) And 255) * 3 + ((c >> 8) And 255) * 6 + (c And 255)) > 1280
End Function

' COL: a big panel. Left, the 16 colours as large swatches. Right, the
' picked one shown big with its numbers, and three sliders (red, green,
' blue) that mix it -- the big swatch, and everything drawn in that
' colour, change as the slider moves (MAP). OK keeps it and makes it the
' drawing colour (and the selection's), DEFAULT puts that colour back,
' CANCEL (or Esc) undoes all the mixing.
Sub ColourPicker
  Local integer px0, py0, pw, ph, cs, gx, gy, sx0, sw, sy0, bw0, bh0, by0
  Local integer i, pick, old(15), x, y, drag, v, done
  For i = 0 To 15
    old(i) = cur(i)
  Next
  pick = col
  pw = W * 7 \ 8
  ph = H * 3 \ 4
  px0 = (W - pw) \ 2
  py0 = (H - ph) \ 2
  bh0 = RH + 4
  cs = (ph - RH - bh0 - 24) \ 4
  gx = px0 + 8
  gy = py0 + RH + 6
  sx0 = gx + 4 * cs + 16
  sw = px0 + pw - sx0 - 12
  sy0 = gy + cs + RH + 8
  bw0 = (pw - 32) \ 3
  by0 = py0 + ph - bh0 - 8
  drag = -1
  CurHide
  Box px0, py0, pw, ph, 2, RGB(WHITE), RGB(BLACK)
  Text px0 + pw \ 2, py0 + RH \ 2 + 2, "COLOUR MIXER", "CM", uf, 1, RGB(WHITE), -1
  For i = 0 To 2
    RBox px0 + 8 + i * (bw0 + 8), by0, bw0, bh0, 4, RGB(GRAY), RGB(MYRTLE)
    Text px0 + 8 + i * (bw0 + 8) + bw0 \ 2, by0 + bh0 \ 2, Choice(i = 0, "OK", Choice(i = 1, "DEFAULT", "CANCEL")), "CM", uf, 1, RGB(WHITE), -1
  Next
  CurShow
  PickerDraw pick, gx, gy, cs, sx0, sy0, sw
  wasDown = 1
  Do
    ReadInput
    x = mx
    y = my
    If down And Not wasDown Then
      drag = -1
      ' a swatch
      If x >= gx And x < gx + 4 * cs And y >= gy And y < gy + 4 * cs Then
        pick = ((y - gy) \ cs) * 4 + (x - gx) \ cs
        PickerDraw pick, gx, gy, cs, sx0, sy0, sw
      EndIf
      ' a slider
      If hasMap And x >= sx0 - 6 And x < sx0 + sw + 6 Then
        For i = 0 To 2
          If y >= sy0 + i * 2 * RH - 4 And y < sy0 + i * 2 * RH + RH + 8 Then drag = i
        Next
      EndIf
      ' OK / DEFAULT / CANCEL
      If y >= by0 And y < by0 + bh0 Then
        For i = 0 To 2
          If x >= px0 + 8 + i * (bw0 + 8) And x < px0 + 8 + i * (bw0 + 8) + bw0 Then done = i + 1
        Next
      EndIf
    EndIf
    If down And drag >= 0 Then
      v = Max(0, Min(255, (x - sx0) * 255 \ (sw - 1)))
      If v <> ((cur(pick) >> (16 - 8 * drag)) And 255) Then
        ' keep the other two channels: the mask is built with XOR, because
        ' MMBasic's NOT is true/false, not a bit flip (it wiped them to 0)
        cur(pick) = (cur(pick) And (&HFFFFFF Xor (255 << (16 - 8 * drag)))) Or (v << (16 - 8 * drag))
        ApplyPal
        PickerDraw pick, gx, gy, cs, sx0, sy0, sw
      EndIf
    EndIf
    If Not down Then drag = -1
    wasDown = down
    If Inkey$ = Chr$(27) Then done = 3
    Select Case done
      Case 1
        Exit Do
      Case 2
        Restore DefaultColours
        For i = 0 To 15
          Read v
          If i = pick Then cur(i) = v
        Next
        ApplyPal
        PickerDraw pick, gx, gy, cs, sx0, sy0, sw
        done = 0
      Case 3
        For i = 0 To 15
          cur(i) = old(i)
        Next
        ApplyPal
        Exit Do
    End Select
    Pause 10
  Loop
  If done = 1 Then
    col = pick
    If sel >= 0 Then
      SetProps col, ssz(sel), sf(sel)
      Exit Sub
    EndIf
  EndIf
  RedrawPic
End Sub

Sub PickerDraw(pick As integer, gx As integer, gy As integer, cs As integer, sx0 As integer, sy0 As integer, sw As integer)
  Local integer i, v, y
  CurHide
  For i = 0 To 15
    Box gx + (i Mod 4) * cs + 2, gy + (i \ 4) * cs + 2, cs - 4, cs - 4, 3, Choice(i = pick, RGB(WHITE), RGB(BLACK)), pal(i)
  Next
  ' the colour being mixed, large, with its numbers
  Box sx0, gy, sw, cs, 2, RGB(WHITE), pal(pick)
  Box sx0, gy + cs + 2, sw, RH, 1, RGB(BLACK), RGB(BLACK)
  Text sx0, gy + cs + 4, "R" + Str$((cur(pick) >> 16) And 255) + " G" + Str$((cur(pick) >> 8) And 255) + " B" + Str$(cur(pick) And 255) + "  #" + Hex$(cur(pick), 6), "LT", fnt, 1, RGB(WHITE), -1
  If hasMap Then
    For i = 0 To 2
      y = sy0 + i * 2 * RH
      v = (cur(pick) >> (16 - 8 * i)) And 255
      Box sx0 - 6, y, sw + 12, RH + 8, 1, RGB(BLACK), RGB(BLACK)
      Text sx0, y, Mid$("RGB", i + 1, 1) + " " + Str$(v), "LT", fnt, 1, RGB(WHITE), -1
      Box sx0, y + fhh + 4, sw, 4, 1, RGB(GRAY), Choice(i = 0, RGB(RED), Choice(i = 1, RGB(GREEN), RGB(BLUE)))
      Box sx0 + v * (sw - 8) \ 255, y + fhh, 8, 12, 1, RGB(WHITE), RGB(WHITE)
    Next
  Else
    Text sx0, sy0, "This firmware can't mix", "LT", fnt, 1, RGB(GRAY), -1
    Text sx0, sy0 + RH, "colours (no MAP): pick one", "LT", fnt, 1, RGB(GRAY), -1
  EndIf
  CurShow
End Sub

Function BmpSize(n$) As integer
  BmpSize = -1
  On Error Skip
  BmpSize = MM.Info(FILESIZE n$ + ".bmp")
  If MM.Errno Then BmpSize = -1
End Function

' --- file list ------------------------------------------------------------
' the pictures in this folder (name.pic, or a plain name.bmp) as a list to
' click; returns the name without its extension, or "" for cancel
Function FilePick$()
  Local string fl$(79), d$, e$, t$
  Local integer n, nd, i, j, rows, top, x, y, wd, ht, r, dup
  ' this folder (B:/draw): .pic pictures, and .bmp without a .pic
  d$ = Dir$("*.pic", FILE)
  Do While d$ <> "" And n < 60
    fl$(n) = d$
    n = n + 1
    d$ = Dir$()
  Loop
  e$ = Dir$("*.bmp", FILE)
  Do While e$ <> "" And n < 60
    ' a .bmp with a .pic of the same name is already in the list
    dup = 0
    For i = 0 To n - 1
      If LCase$(Left$(fl$(i), Len(fl$(i)) - 4)) = LCase$(Left$(e$, Len(e$) - 4)) Then dup = 1
    Next
    If Not dup Then
      fl$(n) = e$
      n = n + 1
    EndIf
    e$ = Dir$()
  Loop
  If n > 1 Then Sort fl$(), , 1, 0, n
  nd = n
  ' then the club's own art in B:/club, to open as a background
  On Error Skip
  Chdir "/club"
  If MM.Errno = 0 Then
    e$ = Dir$("*.bmp", FILE)
    Do While e$ <> "" And n < 80
      fl$(n) = "B:/club/" + e$
      n = n + 1
      e$ = Dir$()
    Loop
    On Error Skip
    Chdir "/draw"
  EndIf
  If n - nd > 1 Then Sort fl$(), , 1, nd, n - nd
  rows = (H - TB - 3 * RH) \ RH - 1
  wd = W * 2 \ 3
  x = (W - wd) \ 2
  y = TB + RH
  Do
    ht = (Max(1, Min(rows, n - top)) + 2) * RH + 8
    CurHide
    Box x, y, wd, ht, 2, RGB(WHITE), RGB(BLACK)
    Text x + wd \ 2, y + RH \ 2 + 2, "OPEN - click a picture", "CM", uf, 1, RGB(YELLOW), -1
    If n = 0 Then Text x + 12, y + 4 + RH + RH \ 2, "Nothing saved yet - FILE > Save... first", "LM", uf, 1, RGB(WHITE), -1
    For i = 0 To Min(rows, n - top) - 1
      t$ = fl$(top + i)
      If top + i >= nd Then
        t$ = Mid$(t$, 9) + "  (club art, as a background)"
      ElseIf LCase$(Right$(t$, 4)) = ".bmp" Then
        t$ = t$ + "  (background)"
      EndIf
      Text x + 12, y + 4 + (i + 1) * RH + RH \ 2, t$, "LM", uf, 1, Choice(top + i >= nd, RGB(CYAN), RGB(WHITE)), -1
    Next
    j = Max(1, Min(rows, n - top)) + 1
    Text x + 12, y + 4 + j * RH + RH \ 2, Choice(top + rows < n, "More...", ""), "LM", uf, 1, RGB(CYAN), -1
    Text x + wd - 12, y + 4 + j * RH + RH \ 2, "Cancel", "RM", uf, 1, RGB(CYAN), -1
    CurShow
    ' wait for a click
    Do
      ReadInput
    Loop While down
    Do
      ReadInput
      If Inkey$ = Chr$(27) Then
        Refresh
        Exit Function
      EndIf
      Pause 5
    Loop Until down
    Do
      ReadInput
    Loop While down
    wasDown = 0
    If mx < x Or mx >= x + wd Or my < y + 4 + RH Or my >= y + ht Then
      Refresh
      Exit Function
    EndIf
    r = (my - y - 4) \ RH - 1
    If r >= 0 And r < Min(rows, n - top) Then
      FilePick$ = Left$(fl$(top + r), Len(fl$(top + r)) - 4)
      Exit Function
    EndIf
    If r = j - 1 Then
      If mx >= x + wd \ 2 Then
        Refresh
        Exit Function
      EndIf
      If top + rows < n Then
        top = top + rows
      Else
        top = 0
      EndIf
    EndIf
  Loop
End Function

' --- side panel ---------------------------------------------------------------
' an icon per tool, then DELETE and UNDO, down the left edge
Sub DrawPanel
  Local integer i, y
  Box 0, TB, PW, (NT + 2) * icoH, 1, RGB(GRAY), RGB(BLACK)
  For i = 0 To NT + 1
    y = TB + i * icoH
    If i = tool Then Box 2, y + 1, PW - 4, icoH - 2, 1, RGB(WHITE), RGB(MIDGREEN)
    If i = NT Then Line 2, y, PW - 3, y, 1, RGB(GRAY)
    Icon Choice(i < NT, i, 100 + i - NT), PW \ 2, y + icoH \ 2, Min(PW, icoH) * 3 \ 8
  Next
End Sub

Sub PanelClick(i As integer)
  If i < NT Then
    PickTool i
  ElseIf i = NT Then
    DelSel
  Else
    Undo
  EndIf
End Sub

Sub PickTool(i As integer)
  tool = i
  radA = -1
  arcStage = 0
  mlN = 0
  twoClick = 0
  If i <> 0 Then
    sel = -1
    selH = -1
  EndIf
  Refresh
  ToolHelp
End Sub

' a little picture of tool i (or DELETE, UNDO), centred on x,y, s across
Sub Icon(i As integer, x As integer, y As integer, s As integer)
  Local integer c, j, ax(3), ay(3)
  c = RGB(WHITE)
  Select Case i
    Case 0
      ' select: an arrow pointer
      ax(0) = x - s \ 2
      ay(0) = y - s
      ax(1) = x - s \ 2
      ay(1) = y + s \ 2
      ax(2) = x + s \ 2
      ay(2) = y + s \ 6
      ax(3) = ax(0)
      ay(3) = ay(0)
      Polygon 4, ax(), ay(), c, c
      Line x, y, x + s \ 2, y + s, 2, c
    Case 1
      ' pen: a squiggle
      For j = -s To s - 2 Step 2
        Line x + j, y + Int(Sin(j / 2) * s / 2), x + j + 2, y + Int(Sin((j + 2) / 2) * s / 2), 1, c
      Next
    Case 2
      Line x - s, y + s, x + s, y - s, 1, c
    Case 3
      For j = 0 To 2
        Line x - s + j * s * 2 \ 3, y + s - j * s * 2 \ 3, x - s + j * s * 2 \ 3 + s \ 2, y + s - j * s * 2 \ 3 - s \ 2, 1, c
      Next
    Case 4
      Box x - s, y - s * 3 \ 4, 2 * s, s * 3 \ 2, 1, c
    Case 5
      RBox x - s, y - s * 3 \ 4, 2 * s, s * 3 \ 2, Max(2, s \ 3), c
    Case 6
      Circle x, y, s, 1, 1, c
    Case 7
      Arc x, y, s - 1, s, 270, 90, c
    Case 8
      ' multi line: a star-ish outline
      Line x, y - s, x + s, y + s, 1, c
      Line x + s, y + s, x - s, y, 1, c
      Line x - s, y, x + s, y, 1, c
      Line x + s, y, x - s, y + s, 1, c
      Line x - s, y + s, x, y - s, 1, c
    Case 9
      Text x, y, "T", "CM", Choice(PW >= 40, 2, 1), 1, c, -1
    Case 10
      ' eraser: a pink block
      Box x - s, y - s \ 2, 2 * s, s, 1, c, RGB(LILAC)
    Case 11
      ' pick colour: a dropper
      Line x - s, y + s, x + s \ 2, y - s \ 2, 2, c
      Circle x + s \ 2, y - s \ 2, s \ 3 + 1, 1, 1, c, c
    Case 12
      ' measure: a ruler
      Box x - s, y - s \ 3, 2 * s, s * 2 \ 3 + 1, 1, c
      For j = -s + 2 To s - 2 Step 3
        Line x + j, y - s \ 3, x + j, y, 1, c
      Next
    Case 13
      ' button: a little green club button
      RBox x - s, y - s \ 2, 2 * s, s, 2, RGB(BLACK), RGB(MIDGREEN)
      Box x - s + 2, y - s \ 2 + 2, 2 * s - 4, s \ 3, 1, RGB(GREEN), RGB(GREEN)
    Case 14
      ' area: a dotted yellow frame
      For j = -s To s Step 3
        Pixel x + j, y - s * 3 \ 4, RGB(YELLOW)
        Pixel x + j, y + s * 3 \ 4, RGB(YELLOW)
      Next
      For j = -s * 3 \ 4 To s * 3 \ 4 Step 3
        Pixel x - s, y + j, RGB(YELLOW)
        Pixel x + s, y + j, RGB(YELLOW)
      Next
    Case 15
      ' radius: two lines joined by a rounded corner
      Line x - s, y + s, x - s, y - s \ 3, 1, c
      Line x - s \ 3, y - s, x + s, y - s, 1, c
      Arc x - s \ 3, y - s \ 3, s * 2 \ 3 - 1, s * 2 \ 3, 270, 360, RGB(YELLOW)
    Case 100
      ' delete: a bin
      c = RGB(RED)
      Box x - s * 2 \ 3, y - s \ 2, s * 4 \ 3, s * 3 \ 2, 1, c
      Line x - s, y - s \ 2 - 2, x + s, y - s \ 2 - 2, 1, c
      Line x - s \ 3, y - s + 1, x + s \ 3, y - s + 1, 1, c
    Case 101
      ' undo: a curling arrow
      c = RGB(YELLOW)
      Arc x, y, s - 2, s, 0, 270, c
      Line x - s, y, x - s - s \ 3, y - s \ 3, 2, c
      Line x - s, y, x - s + s \ 3, y - s \ 3, 2, c
  End Select
End Sub

' --- handles: the points of the selected shape ------------------------------------
Function NHandles(i As integer) As integer
  Select Case sk(i)
    Case K_LINE, K_CTR, K_CIRC
      NHandles = 2
    Case K_BOX, K_RBOX, K_BTN, K_AREA
      NHandles = 4
    Case K_ARC
      NHandles = 3
    Case K_MLIN
      NHandles = sb(i)
    Case K_TEXT
      NHandles = 1
  End Select
End Function

' where handle h of shape i is
Sub HandleXY(i As integer, h As integer, x As integer, y As integer)
  Select Case sk(i)
    Case K_LINE, K_CTR
      x = Choice(h = 0, sa(i), sc(i))
      y = Choice(h = 0, sb(i), sd(i))
    Case K_BOX, K_RBOX, K_BTN, K_AREA
      x = sa(i) + Choice(h = 1 Or h = 2, sc(i) - 1, 0)
      y = sb(i) + Choice(h >= 2, sd(i) - 1, 0)
    Case K_CIRC
      x = sa(i) + Choice(h = 1, sc(i), 0)
      y = sb(i)
    Case K_ARC
      If h = 0 Then
        x = sa(i)
        y = sb(i)
      Else
        x = sa(i) + sc(i) * Sin(Rad(Choice(h = 1, sd(i), se(i))))
        y = sb(i) - sc(i) * Cos(Rad(Choice(h = 1, sd(i), se(i))))
      EndIf
    Case K_MLIN
      x = qx(sa(i) + h)
      y = qy(sa(i) + h)
    Case K_TEXT
      x = sa(i)
      y = sb(i)
  End Select
End Sub

' move handle h of shape i to x, y
Sub SetHandle(i As integer, h As integer, x As integer, y As integer)
  Local integer x0, y0, x1, y1
  Select Case sk(i)
    Case K_LINE, K_CTR
      If h = 0 Then
        sa(i) = x
        sb(i) = y
      Else
        sc(i) = x
        sd(i) = y
      EndIf
    Case K_BOX, K_RBOX, K_BTN, K_AREA
      ' the corner moves, the opposite one stays put
      x0 = sa(i)
      y0 = sb(i)
      x1 = sa(i) + sc(i) - 1
      y1 = sb(i) + sd(i) - 1
      If h = 0 Or h = 3 Then x0 = x Else x1 = x
      If h <= 1 Then y0 = y Else y1 = y
      sa(i) = Min(x0, x1)
      sb(i) = Min(y0, y1)
      sc(i) = Max(4, Abs(x1 - x0) + 1)
      sd(i) = Max(4, Abs(y1 - y0) + 1)
    Case K_CIRC
      If h = 0 Then
        sa(i) = x
        sb(i) = y
      Else
        sc(i) = Max(2, Int(Sqr((x - sa(i)) ^ 2 + (y - sb(i)) ^ 2)))
      EndIf
    Case K_ARC
      If h = 0 Then
        sa(i) = x
        sb(i) = y
      Else
        sc(i) = Max(3, Int(Sqr((x - sa(i)) ^ 2 + (y - sb(i)) ^ 2)))
        If h = 1 Then sd(i) = Ang(x - sa(i), y - sb(i)) Else se(i) = Ang(x - sa(i), y - sb(i))
      EndIf
    Case K_MLIN
      qx(sa(i) + h) = x
      qy(sa(i) + h) = y
    Case K_TEXT
      sa(i) = x
      sb(i) = y
  End Select
End Sub

Sub DrawHandles(i As integer)
  Local integer h, x, y
  For h = 0 To NHandles(i) - 1
    HandleXY i, h, x, y
    Box x - 3, y - 3, 7, 7, 1, RGB(WHITE), Choice(h = selH, RGB(YELLOW), RGB(RED))
  Next
End Sub

' the handle of shape i under x, y (-1 if none)
Function HandleAt(i As integer, px As integer, py As integer) As integer
  Local integer h, x, y
  HandleAt = -1
  For h = 0 To NHandles(i) - 1
    HandleXY i, h, x, y
    If Abs(px - x) <= 5 And Abs(py - y) <= 5 Then
      HandleAt = h
      Exit Function
    EndIf
  Next
End Function

' begin dragging handle h: note how the shape was (for UNDO), and take the
' shape out of the art so the old copy doesn't show while it moves
Sub StartHandle(h As integer)
  selH = h
  dragH = h
  dragging = 1
  If sk(sel) = K_MLIN Then
    uT = 8
    uI = sel
    uC = h
    uA = qx(sa(sel) + h)
    uB = qy(sa(sel) + h)
  Else
    uT = 7
    uI = sel
    uA = sa(sel)
    uB = sb(sel)
    uC = sc(sel)
    uNs = sd(sel)
    uNp = se(sel)
  EndIf
  PushUndo
  sk(sel) = -sk(sel)
  RedrawPic
  sk(sel) = -sk(sel)
  Refresh
  Say "Moving a point - let go where it belongs" + Choice(sk(sel) = K_MLIN, " (DELETE removes this corner)", "")
End Sub

' --- names on mouse-over ------------------------------------------------------
' which icon (or the colour swatch) the pointer is on; redraw only when that
' changes, so the name pops up and goes without flicker
Sub Hover
  Local integer h
  ' auto-hide: out into the picture hides them, the top or left edge
  ' brings them back
  If autoHide And my < sbY Then
    If showBar Then
      If my > TB + 6 Then
        showBar = 0
        hoverI = -1
        Refresh
        Exit Sub
      EndIf
    ElseIf my <= 2 Then
      showBar = 1
      Refresh
      Exit Sub
    EndIf
  EndIf
  h = -1
  If mx < PW And my >= TB And my < TB + (NT + 2) * icoH Then h = (my - TB) \ icoH
  ' the swatch is on the status bar, which is always there
  If my >= sbY And mx >= sbSx And mx < sbXx Then h = 99
  ' only the pop-up changes: take the old one off, put the new one on --
  ' no whole-screen redraw (that flashed as the pointer crossed the icons)
  If h <> hoverI Then
    ClearTip
    hoverI = h
    CurHide
    Tip
    CurShow
  EndIf
End Sub

' the patch of picture under the name pop-up, back as it was
Sub ClearTip
  If tipW = 0 Then Exit Sub
  CurHide
  If hasFB Then
    BLIT FRAMEBUFFER F, N, tipX, tipY, tipX, tipY, tipW, tipH
    tipW = 0
    CurShow
  Else
    tipW = 0
    CurShow
    Refresh
  EndIf
End Sub

' the name of the icon under the pointer, in a box beside it
Sub Tip
  Local string t$
  Local integer x, y, wd
  If hoverI < 0 Then Exit Sub
  If hoverI = 99 Then
    t$ = "Colour mixer"
    y = sbY - RH - 2
  Else
    If hoverI < NT Then
      t$ = tl$(hoverI)
    ElseIf hoverI = NT Then
      t$ = "Delete" + Choice(sel >= 0, "", " (select something first)")
    Else
      t$ = "Undo  (Ctrl-Z)"
    EndIf
    y = TB + hoverI * icoH + (icoH - RH) \ 2
  EndIf
  wd = Len(t$) * ufw + 12
  x = Choice(hoverI = 99, Min(sbSx, W - wd - 4), PW + 4)
  tipX = x
  tipY = y
  tipW = wd
  tipH = RH
  Box x, y, wd, RH, 1, RGB(WHITE), RGB(BLACK)
  Text x + 6, y + RH \ 2, t$, "LM", uf, 1, RGB(YELLOW), -1
End Sub

' --- the status bar ------------------------------------------------------------
' a message: shown in the message cell, scrolling if it doesn't fit
Sub Say(s$)
  sayMsg$ = s$
  sayPos = 1
  sayLast = Timer
  DrawSay
End Sub

' the whole bar
Sub DrawStatus
  Local integer hid, c
  hid = (my + 20 >= sbY)
  If hid Then CurHide
  Box 0, sbY, W, RH, 1, RGB(GRAY), RGB(BLACK)
  ' the command in use
  RBox 2, sbY + 2, sbTw - 4, RH - 4, 4, RGB(GRAY), RGB(MYRTLE)
  Text sbTw \ 2, sbY + RH \ 2, UCase$(tl$(tool)), "CM", uf, 1, RGB(YELLOW), -1
  ' FILL and GRID switches, lit when on
  RBox sbFx, sbY + 2, 4 * ufw + 10, RH - 4, 4, RGB(GRAY), Choice(fil, RGB(MIDGREEN), RGB(BLACK))
  Text sbFx + 2 * ufw + 5, sbY + RH \ 2, "FILL", "CM", uf, 1, Choice(fil, RGB(WHITE), RGB(GRAY)), -1
  RBox sbGx, sbY + 2, 4 * ufw + 10, RH - 4, 4, RGB(GRAY), Choice(grd, RGB(MIDGREEN), RGB(BLACK))
  Text sbGx + 2 * ufw + 5, sbY + RH \ 2, "G" + Str$(gsz), "CM", uf, 1, Choice(grd, RGB(WHITE), RGB(GRAY)), -1
  ' the colour swatch, with the size in it
  Box sbSx, sbY + 3, 2 * RH, RH - 6, 1, RGB(WHITE), pal(col)
  c = Choice(Bright(cur(col)), RGB(BLACK), RGB(WHITE))
  Text sbSx + RH, sbY + RH \ 2, Str$(size), "CM", fnt, 1, c, -1
  If hid Then CurShow
  sayWide = 0
  DrawSay
  xyX = -1
  If showXY Then DrawXY
End Sub

' the message cell (or the whole bar, for a prompt): the part that fits,
' from the scroll position; a prompt shows its end, where the typing is
Sub DrawSay
  Local integer x, wd, n, hid
  Local string t$
  x = Choice(sayWide, 0, sbMx)
  wd = Choice(sayWide, W, sbMw)
  n = wd \ ufw - 1
  If sayWide Then
    t$ = Right$(sayMsg$, n)
  ElseIf Len(sayMsg$) <= n Then
    t$ = sayMsg$
  Else
    ' round and round, with a gap between the end and the start
    t$ = Mid$(sayMsg$ + "      " + sayMsg$, sayPos, n)
  EndIf
  hid = (my + 20 >= sbY And mx + 20 >= x And mx <= x + wd)
  If hid Then CurHide
  Box x, sbY + 1, wd, RH - 2, 1, RGB(BLACK), RGB(BLACK)
  Text x + 4, sbY + RH \ 2, t$, "LM", uf, 1, RGB(YELLOW), -1
  If hid Then CurShow
End Sub

' move a long message along one letter (called from the main loop)
Sub ScrollSay
  If sayWide Or Len(sayMsg$) <= sbMw \ ufw - 1 Then Exit Sub
  If Timer - sayLast < 200 Then Exit Sub
  sayLast = Timer
  sayPos = sayPos + 1
  If sayPos > Len(sayMsg$) + 6 Then sayPos = 1
  DrawSay
End Sub

' the pointer's position (snapped, if the grid is on), right of the bar
Sub DrawXY
  Local integer hid
  xyX = mx
  xyY = my
  hid = (my + 20 >= sbY And mx + 20 >= sbXx)
  If hid Then CurHide
  Box sbXx, sbY + 1, sbXw - 2, RH - 2, 1, RGB(BLACK), RGB(BLACK)
  If showXY Then Text sbXx + sbXw \ 2, sbY + RH \ 2, "X" + Str$(Snap(mx)) + " Y" + Str$(Snap(my)), "CM", uf, 1, RGB(CYAN), -1
  If hid Then CurShow
End Sub

' a click on the status bar: FILL, GRID, the swatch
Sub StatusClick(x As integer)
  If x >= sbFx And x < sbGx - 4 Then
    MenuPick 3, 1
  ElseIf x >= sbGx And x < sbSx - 4 Then
    MenuPick 4, 0
  ElseIf x >= sbSx And x < sbXx Then
    ColourPicker
  EndIf
End Sub

' --- the X,Y readout ----------------------------------------------------------
Sub ToggleXY
  showXY = Not showXY
  Refresh
  Say "X,Y readout " + Choice(showXY, "on", "off") + " (X key or VIEW menu)"
End Sub

' the pointer's position (snapped, if the grid is on) in the bottom-right
' corner; the pointer is only hidden if it's over the readout itself

' --- right click and grid size ------------------------------------------------
' the right button: on GRID (bottom bar) it picks the grid size
Sub RightClick(x As integer, y As integer)
  If y >= sbY And x >= sbGx And x < sbSx - 4 Then
    GridSize
  Else
    Say "Right-click GRID (bottom bar) to set the grid size"
  EndIf
  ' wait for the button to come up -- but never for more than a second, in
  ' case this mouse reports the right button as always held
  Local integer t0
  t0 = Timer
  Do
    ReadInput
    Pause 10
  Loop While rdown And Timer - t0 < 1000
  wasR = rdown
End Sub

' a list of sizes above the GRID switch; the pick turns snapping on
Sub GridSize
  Local integer n, i, x, y, wd, r, sz(6), c, t0
  Restore GridSizes
  For i = 0 To 6
    Read sz(i)
  Next
  n = 7
  wd = 10 * ufw
  x = Min(sbGx, W - wd - 2)
  y = sbY - n * RH - 6
  CurHide
  Box x, y, wd, n * RH + 4, 2, RGB(WHITE), RGB(BLACK)
  For i = 0 To n - 1
    Text x + 10, y + 2 + i * RH + RH \ 2, Choice(sz(i) = gsz, "* ", "  ") + Str$(sz(i)) + " px", "LM", uf, 1, RGB(WHITE), -1
  Next
  CurShow
  ' wait for a click (either button up first)
  t0 = Timer
  Do
    ReadInput
    Pause 10
  Loop While (down Or rdown) And Timer - t0 < 1000
  r = -1
  Do
    ReadInput
    c = Asc(Inkey$ + Chr$(0))
    If c = 27 Then Exit Do
    If down Then
      If mx >= x And mx < x + wd And my >= y + 2 And my < y + 2 + n * RH Then r = (my - y - 2) \ RH
      Exit Do
    EndIf
    Pause 10
  Loop
  Do
    ReadInput
    Pause 10
  Loop While down
  wasDown = 0
  If r >= 0 Then
    gsz = sz(r)
    grd = 1
  EndIf
  Refresh
  Say "Grid " + Str$(gsz) + " px, snap " + Choice(grd, "on", "off") + " (click GRID to switch it)"
End Sub

GridSizes:
Data 4, 8, 10, 16, 20, 25, 32

' --- RADIUS (the 3D Model Editor's): round the corner where two lines meet --
Sub RadClick(x As integer, y As integer)
  Local integer h
  h = Hit(x, y)
  If h < 0 Then
    Say "Click right on a line"
    Exit Sub
  EndIf
  If sk(h) <> K_LINE And sk(h) <> K_CTR Then
    Say "Radius works on two straight lines that meet at a corner"
    Exit Sub
  EndIf
  If radA < 0 Or radA = h Then
    radA = h
    sel = h
    Refresh
    Say "Now click the other line at that corner"
    Exit Sub
  EndIf
  Fillet radA, h
  radA = -1
End Sub

' trim lines a and b back from their shared corner and join them with an arc
Sub Fillet(a As integer, b As integer)
  Local integer ea, eb, i, j, ci
  Local float px, py, ux, uy, vx, vy, la, lb, d, best, th, t, r, cx, cy, bx, by, bl
  Local float ax2(1), ay2(1), bx2(1), by2(1)
  Local string r$
  ax2(0) = sa(a) : ay2(0) = sb(a) : ax2(1) = sc(a) : ay2(1) = sd(a)
  bx2(0) = sa(b) : by2(0) = sb(b) : bx2(1) = sc(b) : by2(1) = sd(b)
  ' the pair of ends that meet (the corner)
  best = 999999
  For i = 0 To 1
    For j = 0 To 1
      d = Sqr((ax2(i) - bx2(j)) ^ 2 + (ay2(i) - by2(j)) ^ 2)
      If d < best Then
        best = d
        ea = i
        eb = j
      EndIf
    Next
  Next
  If best > 8 Then
    sel = -1
    Refresh
    Say "Those lines don't meet at a corner (ends " + Str$(Int(best)) + " px apart)"
    Exit Sub
  EndIf
  px = (ax2(ea) + bx2(eb)) / 2
  py = (ay2(ea) + by2(eb)) / 2
  ' along each line, away from the corner
  ux = ax2(1 - ea) - px : uy = ay2(1 - ea) - py
  vx = bx2(1 - eb) - px : vy = by2(1 - eb) - py
  la = Sqr(ux * ux + uy * uy) : lb = Sqr(vx * vx + vy * vy)
  If la < 2 Or lb < 2 Then Exit Sub
  ux = ux / la : uy = uy / la : vx = vx / lb : vy = vy / lb
  d = ux * vx + uy * vy
  If d > 0.998 Or d < -0.998 Then
    sel = -1
    Refresh
    Say "Those lines are in a straight line - there's no corner to round"
    Exit Sub
  EndIf
  th = Acos(Max(-1, Min(1, d)))
  r$ = Ask$("Radius (pixels):", Str$(Max(8, size * 4)))
  r = Val(r$)
  sel = -1
  If r <= 0 Then
    Refresh
    Exit Sub
  EndIf
  ' how far back from the corner each line is cut
  t = r / Tan(th / 2)
  If t >= la Or t >= lb Then
    Refresh
    Say "Too big for those lines - the most is about " + Str$(Int(Min(la, lb) * Tan(th / 2))) + " px"
    Exit Sub
  EndIf
  ' the arc's centre is along the line halfway between them
  bx = ux + vx : by = uy + vy
  bl = Sqr(bx * bx + by * by)
  cx = px + bx / bl * r / Sin(th / 2)
  cy = py + by / bl * r / Sin(th / 2)
  ' cut the lines back (each recorded for UNDO)
  For i = 0 To 1
    ci = Choice(i = 0, a, b)
    uT = 7 : uI = ci : uA = sa(ci) : uB = sb(ci) : uC = sc(ci) : uNs = sd(ci) : uNp = se(ci)
    PushUndo
  Next
  If ea = 0 Then
    sa(a) = px + ux * t : sb(a) = py + uy * t
  Else
    sc(a) = px + ux * t : sd(a) = py + uy * t
  EndIf
  If eb = 0 Then
    sa(b) = px + vx * t : sb(b) = py + vy * t
  Else
    sc(b) = px + vx * t : sd(b) = py + vy * t
  EndIf
  ' the arc: from one cut point round to the other, the short way
  i = NewShape(K_ARC, Int(cx), Int(cy), Int(r), 0, "")
  If i < 0 Then Exit Sub
  scl(i) = scl(a)
  ssz(i) = ssz(a)
  sf(i) = 0
  sd(i) = Ang(px + ux * t - cx, py + uy * t - cy)
  se(i) = Ang(px + vx * t - cx, py + vy * t - cy)
  If (se(i) - sd(i) + 360) Mod 360 > 180 Then
    j = sd(i)
    sd(i) = se(i)
    se(i) = j
  EndIf
  RedrawPic
  Say "Corner rounded, radius " + Str$(r) + " - UNDO three times takes it back"
End Sub
