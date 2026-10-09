Dim integer tmMain = 3, tmShade = 4
Dim integer drvOff
Dim integer mechMain = 12, mechShade = 13
Dim integer cMain = 5, cShade = 4, psMX, psMY, psDX, psDY, nextBlink
Dim integer psMMX, psMMY, psDMX, psDMY
Dim integer sceneDismissed
Sub DrawBay(title$)
  Local integer i, backL, backR, backTop, backBottom, midY, floorTop
  Local integer px(4), py(4)
  Box 0, CT, W, CB - CT, 0, 0, MAP(10)
  floorTop = CT + (CB - CT) * 35 \ 100
  backL = W * 3 \ 10
  backR = W * 7 \ 10
  backTop = CT + (floorTop - CT) * 15 \ 100
  backBottom = floorTop - (floorTop - CT) * 30 \ 100
  px(0) = 0 : py(0) = CT : px(1) = W : py(1) = CT
  px(2) = backR : py(2) = backTop : px(3) = backL : py(3) = backTop
  px(4) = 0 : py(4) = CT
  Polygon 5, px(), py(), MAP(6), MAP(6)
  px(0) = 0 : py(0) = CT : px(1) = backL : py(1) = backTop
  px(2) = backL : py(2) = backBottom : px(3) = 0 : py(3) = floorTop
  px(4) = 0 : py(4) = CT
  Polygon 5, px(), py(), MAP(13), MAP(13)
  px(0) = W : py(0) = CT : px(1) = backR : py(1) = backTop
  px(2) = backR : py(2) = backBottom : px(3) = W : py(3) = floorTop
  px(4) = W : py(4) = CT
  Polygon 5, px(), py(), MAP(13), MAP(13)
  px(0) = 0 : py(0) = CB : px(1) = W : py(1) = CB
  px(2) = backR : py(2) = backBottom : px(3) = backL : py(3) = backBottom
  px(4) = 0 : py(4) = CB
  Polygon 5, px(), py(), MAP(10), MAP(10)
  Box backL, backTop, backR - backL, backBottom - backTop, 0, 0, MAP(13)
  midY = backTop + (backBottom - backTop) * 55 \ 100
  Box backL, midY - 2, backR - backL, 3, 0, 0, C_AMBER
  Box backL + 10, backTop + 10, backR - backL - 20, midY - backTop - 16, 1, C_BLACK, MAP(10)
  For i = backTop + 16 To midY - 10 Step 8
    Line backL + 12, i, backR - 12, i, 1, MAP(13)
  Next
End Sub
Sub Scene(pl As integer, c As integer, mc$, dc$)
  qN$ = pn$(pl)
  qC$ = carName$(c)
  qD$ = Str$(Int(dmg(c)))
  PitScene pl, c, Quote$(mc$), Quote$(dc$)
End Sub
FemaleNames:
Data "ABBEY", "ABBIE", "ABIGAIL", "ALEX", "ALEXA", "ALEXIS", "ALICE", "ALICIA"
Data "ALYSSA", "AMBER", "AMELIA", "AMY", "ANGELA", "ANGIE", "ANNA", "ANNIE"
Data "ASHLEY", "AVA", "BEC", "BECKY", "BELLA", "BETH", "BEV", "BEVERLEY"
Data "BREE", "BRIANNA", "BRIDGET", "BROOKE", "CAITLIN", "CARLY", "CAROL"
Data "CAROLINE", "CASEY", "CASSIE", "CATHY", "CHARLOTTE", "CHELSEA", "CHLOE"
Data "CLAIRE", "COURTNEY", "DAISY", "DANIELLE", "DEB", "DEBBIE", "DIANE"
Data "DONNA", "EDEN", "ELLA", "ELLE", "ELLIE", "ELIZABETH", "EMILY", "EMMA"
Data "ERIN", "EVA", "EVE", "EVIE", "FAITH", "FIONA", "FRAN", "FRANCESCA"
Data "GABBY", "GAIL", "GEORGIA", "GINA", "GRACE", "HALEY", "HANNAH", "HAYLEY"
Data "HEATHER", "HEIDI", "HELEN", "HOLLY", "IMOGEN", "INDIA", "ISABEL"
Data "ISABELLA", "ISLA", "IVY", "JACKIE", "JACQUI", "JADE", "JAN", "JANE"
Data "JANET", "JASMINE", "JAYDA", "JEN", "JENNA", "JENNIFER", "JESS"
Data "JESSICA", "JILL", "JO", "JOAN", "JODIE", "JOSIE", "JULIA", "JULIE"
Data "KAITLYN", "KAREN", "KATE", "KATH", "KATHY", "KATIE", "KATRINA", "KAYLA"
Data "KAYLEE", "KELLY", "KERRY", "KIM", "KIRA", "KIRSTY", "KYLIE", "LARA"
Data "LAUREN", "LAURA", "LEAH", "LEANNE", "LEXI", "LILY", "LINDA", "LISA"
Data "LIZ", "LOLA", "LORNA", "LOTTIE", "LUCY", "LUCIA", "LYDIA", "LYNN"
Data "MADDIE", "MADDISON", "MADISON", "MAEVE", "MAGGIE", "MANDY", "MARGARET"
Data "MARIA", "MARIE", "MARY", "MAYA", "MEG", "MEGAN", "MEL", "MELANIE"
Data "MELISSA", "MIA", "MICHELLE", "MILLIE", "MOLLY", "NAOMI", "NATALIE"
Data "NATASHA", "NICOLE", "NINA", "OLIVIA", "PAIGE", "PAM", "PAMELA", "PATRICIA"
Data "PENNY", "PHOEBE", "POPPY", "PRIYA", "RACHEL", "REBECCA", "RENEE", "RHIANNON"
Data "RIA", "ROSE", "ROSIE", "RUBY", "RUTH", "SALLY", "SAM", "SAMANTHA"
Data "SANDRA", "SARA", "SARAH", "SASHA", "SHANNON", "SHARON", "SHEILA"
Data "SIENNA", "SKYE", "SOPHIA", "SOPHIE", "STACEY", "STELLA", "STEPH"
Data "STEPHANIE", "SUE", "SUSAN", "SUZIE", "TAHLIA", "TAMARA", "TAMMY"
Data "TANYA", "TARA", "TAYLA", "TAYLOR", "TESS", "TIA", "TINA", "TONI"
Data "TRACY", "TRISH", "VAL", "VICKY", "VICTORIA", "VIOLET", "WENDY", "WILLOW"
Data "YVONNE", "ZARA", "ZOE", ""
Function IsFemaleName(nm$) As integer
  Local string w$, n$
  w$ = UCase$(Field$(Trim$(nm$), 1, " "))
  Restore FemaleNames
  Do
    Read n$
    If n$ = w$ Then
      IsFemaleName = 1
      Exit Function
    EndIf
  Loop Until n$ = ""
End Function
TeamColours:
Data "RED", 3, 4, "GREEN", 1, 2, "BLUE", 12, 13, "PURPLE", 9, 13
Data "YELLOW", 5, 4, "SILVER", 14, 13, "BLACK", 13, 10
Function TeamNames$()
  Local string n$, t$
  Local integer i, a, b
  Restore TeamColours
  For i = 0 To NTEAM - 1
    Read n$, a, b
    t$ = t$ + n$ + Choice(i < NTEAM - 1, "|", "")
  Next
  TeamNames$ = t$
End Function
Function ColourSlot(i As integer) As integer
  Local string n$
  Local integer k, a, b
  Restore TeamColours
  For k = 0 To i
    Read n$, a, b
  Next
  ColourSlot = a
End Function
CarColours:
Data 5, 4, 12, 13, 3, 4, 1, 2, 9, 13, 15, 13, 2, 1, 4, 3
Data 5, 4, 12, 13, 3, 4, 1, 2, 9, 13, 15, 13, 2, 1, 4, 3
Data 5, 4, 12, 13, 3, 4, 1, 2
Data 9, 13, 15, 13, 2, 1, 4, 3, 5, 4, 12, 13, 3, 4, 1, 2, 9, 13, 15, 13
Sub PitSceneSetup(pl As integer, c As integer)
  Local integer i, mw, mh, dw, dh, cw, chh, cnx, cny, cx, cy
  tmMain = pMain(pl)
  tmShade = pShade(pl)
  drvOff = Choice(IsFemaleName(pn$(pl)), 8, 0)
  Restore CarColours
  For i = 0 To c
    Read cMain, cShade
  Next
  Restore ArtInfo
  Read mw, mh, psMMX, psMMY, dw, dh, psDMX, psDMY, cw, chh, cnx, cny
  CurHide
  DrawBay "PIT GARAGE"
  cx = (W - cw) \ 2
  cy = CB - chh - 16
  ArtAt 10, cx, cy
  PText cx + cnx, cy + cny, Str$(c + 1), "C", 0, C_BLACK
  PText W \ 2, CB - 8, carName$(c), "C", 0, C_INK
  psDX = 14
  psDY = CB - dh - 6
  psMX = W - mw - 10
  psMY = CB - mh - 6
  ArtAt 5 + drvOff, psDX, psDY
  ArtAt 0, psMX, psMY
  PText psDX + dw \ 2, psDY - 10, pn$(pl), "C", 0, C_AMBER
  CurShow
  BLIT FRAMEBUFFER N, 2, 0, CT, 0, CT, W, CB - CT
End Sub
Sub PitSceneWait
  Local integer t0
  nextBlink = Timer + 1500
  t0 = Timer
  Do
    TickerTick
    Blink
    If Inkey$ <> "" Then Exit Do
    Pause 10
  Loop Until ClickAt() Or Timer - t0 > 8000
  sceneDismissed = Choice(Timer - t0 < 8000, 1, 0)
End Sub
Sub PitScene(pl As integer, c As integer, m$, r$)
  PitSceneSetup pl, c
  Talk m$, psMX + psMMX, psMY + psMMY, 0, 0
  If r$ <> "" Then Talk r$, psDX + psDMX, psDY + psDMY, 1, 0
  PitSceneWait
  If Not sceneChaining Then ShowTrack
End Sub
Sub WelcomeScene(pl As integer, c As integer)
  Local integer i
  PitSceneSetup pl, c
  For i = 1 To 3
    qN$ = pn$(pl)
    qC$ = carName$(c)
    qD$ = Str$(Int(dmg(c)))
    CurHide
    BLIT FRAMEBUFFER 2, N, 0, CT, 0, CT, W, CB - CT
    CurShow
    Talk Quote$("WELCOME"), psMX + psMMX, psMY + psMMY, 0, 0
    Talk Quote$("WELCOMER"), psDX + psDMX, psDY + psDMY, 1, 0
    PitSceneWait
    If sceneDismissed Then Exit Sub
  Next
  ShowTrack
End Sub
Sub Talk(t$, mx As integer, my As integer, who As integer, instant As integer)
  Local string ln$(7) LENGTH 32
  Local string r$, wd$
  Local integer n, i, j, p, lh, bw, bh, bx, by, skip, shut, k, hid
  lh = fh(0) + 4
  r$ = t$
  Do While r$ <> "" And n < 8
    p = Instr(r$, "|")
    If p = 0 Then p = Len(r$) + 1
    wd$ = Left$(r$, p - 1)
    r$ = Mid$(r$, p + 1)
    Do While Len(wd$) > 30 And n < 8
      i = 30
      Do While i > 1 And Mid$(wd$, i, 1) <> " "
        i = i - 1
      Loop
      If i = 1 Then i = 30
      ln$(n) = Left$(wd$, i)
      wd$ = Mid$(wd$, i + 1)
      n = n + 1
    Loop
    If n < 8 And wd$ <> "" Then
      ln$(n) = wd$
      n = n + 1
    EndIf
  Loop
  For i = 0 To n - 1
    bw = Max(bw, PWidth(ln$(i), 0))
  Next
  bw = bw + 24
  bh = n * lh + 16
  If who = 0 Then
    bx = Max(4, mx - 40 - bw)
  Else
    bx = Min(W - bw - 4, mx + 40)
  EndIf
  If instant Then
    by = Max(CT + 4, my - bh - 14)
  Else
    by = CT + 8 + who * (bh + 14)
  EndIf
  CurHide
  Triangle Choice(who, bx + 20, bx + bw - 34), by + bh - 2, Choice(who, bx + 40, bx + bw - 14), by + bh - 2, mx, my - 6, C_BLACK, C_INK
  RBox bx, by, bw, bh, 10, C_BLACK, C_INK
  Line Choice(who, bx + 21, bx + bw - 33), by + bh - 1, Choice(who, bx + 39, bx + bw - 15), by + bh - 1, 2, C_INK
  CurShow
  If instant Then
    For i = 0 To n - 1
      PText bx + 12, by + 8 + i * lh + lh \ 2, ln$(i), "L", 0, C_BLACK
    Next
    Exit Sub
  EndIf
  For i = 0 To n - 1
    For j = 1 To Len(ln$(i))
      If Not skip Then
        If Inkey$ <> "" Or ClickAt() Then skip = 1
      EndIf
      If Not skip Then
        hid = CurOver(bx, by, bw, bh) Or CurOver(Choice(who, psDX, psMX) - 20, Choice(who, psDY, psMY) - 20, 180, 220)
        If hid Then CurHide
        PText bx + 12, by + 8 + i * lh + lh \ 2, Left$(ln$(i), j), "L", 0, C_BLACK
        k = k + 1
        If k Mod 3 = 0 Then
          shut = 1 - shut
          ArtAt Choice(who, 6 + drvOff, 1) + shut, Choice(who, psDX, psMX), Choice(who, psDY, psMY)
        EndIf
        If hid Then CurShow
        Blink
        Pause 20
      EndIf
    Next
    hid = CurOver(bx, by, bw, bh)
    If hid Then CurHide
    PText bx + 12, by + 8 + i * lh + lh \ 2, ln$(i), "L", 0, C_BLACK
    If hid Then CurShow
  Next
  hid = CurOver(Choice(who, psDX, psMX) - 20, Choice(who, psDY, psMY) - 20, 180, 220)
  If hid Then CurHide
  ArtAt Choice(who, 6 + drvOff, 1), Choice(who, psDX, psMX), Choice(who, psDY, psMY)
  If hid Then CurShow
End Sub
Sub Blink
  If Timer < nextBlink Then Exit Sub
  CurHide
  ArtAt 4, psMX, psMY
  ArtAt 9 + drvOff, psDX, psDY
  CurShow
  Pause 110
  CurHide
  ArtAt 3, psMX, psMY
  ArtAt 8 + drvOff, psDX, psDY
  CurShow
  nextBlink = Timer + 2000 + Int(Rnd * 2500)
End Sub
Sub ArtAt(k As integer, x As integer, y As integer)
  Local integer aw, ah, dx, dy, r, i, cx, n, col, artMain, artShade
  Local string row$, c$
  artMain = Choice(k < 5 Or k = 11 Or k = 12, mechMain, tmMain)
  artShade = Choice(k < 5 Or k = 11 Or k = 12, mechShade, tmShade)
  Select Case k
    Case 0
      Restore MechArt
    Case 1
      Restore MechMouthOpen
    Case 2
      Restore MechMouthShut
    Case 3
      Restore MechEyesOpen
    Case 4
      Restore MechEyesShut
    Case 5
      Restore DrvArt
    Case 6
      Restore DrvMouthOpen
    Case 7
      Restore DrvMouthShut
    Case 8
      Restore DrvEyesOpen
    Case 9
      Restore DrvEyesShut
    Case 11
      Restore MechArt2
    Case 12
      Restore MechArt3
    Case 13
      Restore DrvArtF
    Case 14
      Restore DrvMouthOpenF
    Case 15
      Restore DrvMouthShutF
    Case 16
      Restore DrvEyesOpenF
    Case 17
      Restore DrvEyesShutF
    Case Else
      Restore CarArt
  End Select
  Read aw, ah, dx, dy
  For r = 0 To ah - 1
    Read row$
    cx = x + dx
    For i = 1 To Len(row$) Step 2
      c$ = Mid$(row$, i, 1)
      n = Asc(Mid$(row$, i + 1, 1)) - 34
      If c$ <> "." Then
        Select Case c$
          Case "T"
            col = artMain
          Case "U"
            col = artShade
          Case "C"
            col = cMain
          Case "D"
            col = cShade
          Case Else
            col = Val("&H" + c$)
        End Select
        Line cx, y + dy + r, cx + n - 1, y + dy + r, 1, MAP(col)
      EndIf
      cx = cx + n
    Next
  Next
End Sub
ArtInfo:
Data 137, 182, 54, 53, 108, 181, 50, 46, 298, 82, 203, 38
MechArt:
Data 137, 182, 0, 0
Data ".a0&.h"
Data ".^0,.-4$.X"
Data ".Y06.)4%.V"
Data ".W0)3,0*.&4&.U"
Data ".U0'350'.%4&.T"
Data ".S0&3:0&.$4'.S"
Data ".Q0&3>0&.#4'.R"
Data ".P0%3-0-3,0%4'.R"
Data ".O0%3-0/3,0%4'.Q"
Data ".N0%3-0$5,0$3.0#4'.Q"
Data ".M0%3.0$5%3&5%0$3/0#4&.Q"
Data ".L0%3/0$5%3'5$0$304'.P"
Data ".K0%300$5%3'5$0$314&.P"
Data ".K0$310$5%3&5%0$314&.P"
Data ".J0$320$5&3$5&0$324%.P"
Data ".J0$3200324&.O"
Data ".I0$340.344%.O"
Data ".I0$3R4%.O"
Data ".40E3G4$.O"
Data ".30F3G4$.O"
Data ".40$4$3>4#0%3F0#4#.O"
Data ".40$4$3>4$0I4#.O"
Data ".50$4A0J.O"
Data ".50$4B0I.O"
Data ".60$4>0-B*0/B#0(.R"
Data ".60$4.0;B.0-B#0(.R"
Data ".70<B$0&B:0&B$0(.R"
Data ".70+.,0)BF0).Q"
Data ".J0)B'0&B40&B'0).Q"
Data ".J0)B%0*B00*B%0).Q"
Data ".J0)B$0%F&0%B.0%F&0%B$0*.P"
Data ".J0)B$F#0%F&0$B.F#0%F&0$B$0*.P"
Data ".I0*B#0#F#0%F'0$B,0#F#0%F'0$B$0).P"
Data ".G0,B#0(F&0$B,0(F&0$B$0+.N"
Data ".F0-B#0'F&0%B,0'F&0%B$0,.M"
Data ".E0%B#0*B#0'F&0$B(E#B&0'F&0$B%0)B#0%.L"
Data ".E0$B$0*B$0+B)E$B&0+B&0)B$0$.L"
Data ".E0$B$0*B&0(B+E#B(0(B'0)B%0$.K"
Data ".D0$B%0*B5E$B20)B%0$.K"
Data ".D0$B%0*B6E#B20)B%0$.K"
Data ".D0$B%0*B6E$B10)B%0$.:0$.*0$.'"
Data ".D0$B%0*B7E#B10)B%0$.;0$.)0$.'"
Data ".D0$B&0(B8E$B00)B%0$.;0$.)0$.'"
Data ".(0&.:0$B&0(B+0$B*E'B%0$B'E&0)B%0$.:0%.(0%.'"
Data ".'0(.90%B%0$B$0$B*0(B$E&B&0(B%E(0#B$0%B%0$.90&.(0&.&"
Data ".&0%B$0%.90$B$E#0$B,0.B%0-B#E(B%0$E$B#0$.90'.(0'.%"
Data ".&0$B&0$.90%B$0$B*0@E)B#0$B%0$.80%E#0%.'0$E#0%.$"
Data ".&0#E(0#.:0)B(0CB$E%0).90$E%0$.'0$E$0%.#"
Data ".&0$B&0$.;0(B&0FB&0(.90$E&0$.&0%E%0$.#"
Data ".&0$B&0$.@0$B%0.F(E#F'0.B&0$.=0$E&0$.&0$E'0$"
Data ".&0$B&0$.@0$B(0'F,E#F+0'B(0$.=0$E'0*E'0$"
Data ".&0$B&0$.@0%B$E$B%0$4$F+E#F+4#0$B%E$B%0$.=0$E#F$E$0*E'0$"
Data ".&0$B&0$.A0$B$E%B$0%470$B%E$B$0$.>0$E#F$E10$"
Data ".&0$B&0$.B0$B$E$B%0$460$B%E$B$0%.>0$E#F$E10$"
Data ".&0$B&0$.B0%B#E%B$0%450$B$E%B$0$.?0$E#F$E10$"
Data ".&0$B&0$.C0$B$E%B$0$440%B$E$B$0$.@0$E#F%E00$"
Data ".&0$B&0$.D0$B$E%B#0%430$B#E%B$0%.A0$E#F$E00$"
Data ".&0$B&0$.E0$B$E$B$07B#E$B$0%.B0$E#F%E.0$.#"
Data ".&0$B&0$.E0%B$E%06B#E%B#0%.C0%E#F%E-0$.#"
Data ".&0$B&0$.F0%B$E%B4E%B$0%.E0%E#F$E,0$.$"
Data ".&0$B&0$.H0%B#E'B.E'B#0&.G0%E-0$.%"
Data ".&0$B&0(.E0%B#E'B&E$B&E'B#0%.J0%E*0%.&"
Data ".$0'B%0*.D0'E2B#0&.L0..'"
Data ".#0%B#0(B'0%.E0(E-0'.OE#0*.)"
Data ".#0$B%0&B)0%.D08.OE#F$E&.+"
Data "0$B20$.D0$B%0.B%0$.OE#F$E&.+"
Data "0$B20$.D0$B40$.OE#F$E&.+"
Data "0$B20$.D0$B40$.OE#F$E&.+"
Data "0$B20$.D0$B40$.OF$E'.+"
Data "03B#0$.D0$B40$.OF$E'.+"
Data "0$B20$.B0&B40'.KE#F$E'.+"
Data "0$B20$.<0,B40,.FE#F$E&.,"
Data "0$B20$.60.T$0$B40%U#0/.?E#F$E&.,"
Data "0$B20$.60'T+0$B40$U+0(.?E#F$E&.,"
Data "0$B20$.60&T,0%B30$U,0&.@E#F$E&.,"
Data "03B#0$.80%T,06U,0%.BE#F$E&.,"
Data "0$B20$.*05T*06U*06.3F$E'.,"
Data "0$B20$.(09T)0$F00%U)03U$0%.2F$E'.,"
Data "0$B20$.(0'T20%T(0$F00$U(0&T$U10&.0E#F$E'.,"
Data "0$B20$.'0$T$0$T30&T'0$F/0$U'0%U50'./E#F$E&.-"
Data "0$B20$.&0$T%5#0$T40%T&0$F.0$U&0&U60$U#0%..E#F$E&.-"
Data "03B#0$.%0$T%5%0$T40&T$0%F-0$U%0%T#U70$5%0$.-E#F$E&.-"
Data "0$B20$.$0%T%5%0%T50%T$0$F,0%U#0&T%U60$5%0%.,E#F$E&.-"
Data ".#0$B10$.#0%T%5%T$0%T50(F,0(T'U60$U#5%0%.+E#F$E&.-"
Data ".#0%B/0$.#0%T%5%T&0%T604T)U60$U#5%U#0%.*F$E'.-"
Data ".$02.#0%T%5%T(0$T702T*U60$U$5%U#0%.)F$E'.-"
Data ".%04T&5$T*0$T80$T$0#T#U#T%0$T,U60$U$5%U$0%.(F$E'.-"
Data ".'0%B*0&T&5%T+0$T;0#T#U#T1U60$U%5%U$0%.&E#F$E'.-"
Data ".(0$B*0%T&5%T,0%T:0#T#U#T2U50$U%5%U%0%.%E#F$E&.."
Data ".(0$B*0$T&5%T.0$T:0#T#U#T-E$T%U50$U&5%U%0$.%E#F$E&.."
Data ".(0$B+0$T$5%T.0$T;0#T#U#T-E$T%U50$U&5%U&0$.$E#F$E&.."
Data ".(0$B+0$T$5%T-0$T<0#T#U#T+0$E$0*U00$U'5%U%0$.$E#F$E&.."
Data ".(0$B+0$T#5%T-0$T=0#T#U#T*5#0$E$0+U/0$U'5%U%0$.$F$E'.."
Data ".(0$B$E&B%0$5%T-08T*0#T#U#T*5%E$5+U/0$U(5$U%0%.#F$E'.."
Data ".(0$B#E(B$0$5$T-0:T)0#T#U#T*0$U#E$U)0$U/0$U(5%U%0$.#F$E'.."
Data ".(0$B#E(B$0$5#T-0'F40$T)0#T#U#T*0$U#E$U)0$U/0$U(5%U%0$E#F$E'.."
Data ".(0$B$E&B%0$5#T,0%T#0$F40$T)0#T#U#T*0$U#E$U)0$U/0%U(5%U$0$E#F$E'.."
Data ".(0$B+0$T,0%T$0$F'4&F+0$T)0#T#U#T*0$U#E$U)0$U00$U(5%U%0$F$E&./"
Data ".(0$B+0$T,0$T%0$F$4'F$4#F&4$F$0$T)0#T#U#T*0$U,0$U00$U)5%U$0$F$E&./"
Data ".(0$B+0$T+0$T&0$F$4$F(4#F$4$F%0$T)0#T#U#T*0$U,0$U10$U(5%U$0$F$E&./"
Data ".(0$B+0$T*0$T'0$F-4%F&0$T)0#T#U#T*0$U,0$U10$U)5%U$0$E'./"
Data ".'0%B+0$T)0$T(0$F.4#F'0$T)0#T#U#T*00U10%U(5%U$0$E'./"
Data ".'0&B*0$T(0%T(0$F40$T)0#T#U#T+0/U20$U)5%U#0$E'./"
Data ".)0%B*0$T&0%T)0$F40$T)0#T#U#T4U60$U)5%U#0%E&./"
Data ".*0&B(0$T%0%T*08T)0#T#U#T4U70$U)5%U#0$E&./"
Data ".+0&B'0)T,06T*0#T#U#T4U70$U)5%U#0$E%.0"
Data ".-0%B&0(TI0#T#U#T4U70%U)5$U#0$E%.0"
Data "..0&B$0$F#0%TI0#T#U#T5U70$U)5#U%0$E$.0"
Data "./0&B#0(TI0#T#U#T5U70$U-0$E$.0"
Data ".00*.#0$TH0#T#U#T5U80$U,0$E$.0"
Data ".20'.$0$TH0#T#U#T5U80$U,0%E#.0"
Data ".30&.$0$TH0#T#U#T5U80%U,0%.0"
Data ".40$.%0$TH0#T#U#T5U70&U'0*.0"
Data ".90$TH0#T#U#T5U70#.#0.F#0%./"
Data ".90$TH0#T#U#T6U60#.#0(F*0$./"
Data ".90$TH0#T#U#T6U60#.#0$F.0$./"
Data ".90$TH0#T#U#T6U60#.#02./"
Data ".90$TH0#T#U#T6U60#.#04.-"
Data ".:0$TG0#T#U#T6U60#.#0$B00%.,"
Data ".:0$TC0.T1U60%B20$.,"
Data ".:0wB20$.,"
Data ".:0F5,0F.#0$B20$.,"
Data ".:0$AB0$5,0$AB0$.#06.,"
Data ".:0$AB0$5$A(5$0$AB0$.#0$B20$.,"
Data ".:0$AB0$5$A(5$0$AB0$.#0$B20$.,"
Data ".:0$A.0#A50$5$A(5$0$AB0$.#0$B20$.,"
Data ".:01A50$5$A(5$0$AB0$.#0$B20$.,"
Data ".:0-E$0%A40$5$A(5$0$AB0$.#06.,"
Data ".:0%E-0$A40$5,0$AB0$.#0$B20$.,"
Data ".:0$E.085,0F.$0$B00%.,"
Data ".:0$E.0f.$04.-"
Data ".:0$E&D#E)0e.&02.."
Data ".90%E$D%E&8#E$0%T-U+0$.&0$T0U,0$.20&E&0&.0"
Data ".90$E$D&E&8#E%0$T-U+0$.&0$T0U,0$.30,.1"
Data ".90$E$D'E%8#E%0$T-U+0$.&0$T0U,0$.50).2"
Data ".90$E$D'E%8#E%0$T-U+0$.&0$T0U,0$.L"
Data ".80%E$D'E%8#E%0$T-U+0$.&0$T0U,0$.L"
Data ".80$E&D&E%8$E$0$T-U+0$.&0$T0U,0$.L"
Data ".80$E)D#E%8$E$0$T.U*0$.&0$T0U,0$.L"
Data ".80$E)D#E%8$E$0$T.U*0$.&0$T0U,0$.L"
Data ".80$E)D#E%8$E#0$T/U*0$.&0$T0U,0$.L"
Data ".90$E(D$E$8$E#0$T/U*0$.&0$T0U,0$.L"
Data ".90$E(D$E%8#E#0$T/U*0$.&0$T0U,0$.L"
Data ".90$E'0#D$E&0%T/U*0$.'0$T/U,0$.L"
Data ".90$E&0$D$E&0$T0U*0$.'0$T/U,0$.L"
Data ".90$E&0$.#0$E%0$T0U*0$.'0$T0U+0#.M"
Data ".90$E%0$.$0$E%0$T-U-0$.'0$T&U(T&U+0#.M"
Data ".90$E$0%.%0$E#0$T'U+T#U*0$.'0$T*U00$.M"
Data ".90$E$0$.&0'T&U%T*U*0$.'0$T/U+0$.M"
Data ".:0'.'0&T1U*0$.'0$T0U*0$.M"
Data ".:0&.)0%T1U*0$.'0$T0U*0$.M"
Data ".:0%.*0%T1U*0$.'0$T0U*0$.M"
Data ".:0%.+0$T1U*0$.'0$T0U*0$.M"
Data ".;0#.,0$T1U*0$.'0$T0U*0$.M"
Data ".F0$T1U*0$.'0$T0U*0$.M"
Data ".F0$T1U*0$.'0$T0U*0$.M"
Data ".G0$T0U*0$.'0$T0U*0$.M"
Data ".G0$T1U)0$.'0$T0U*0$.M"
Data ".G0$T1U)0$.'0$T0U*0$.M"
Data ".G0<.'0<.M"
Data ".G0#590$.'0#590$.M"
Data ".G0#590$.'0#590$.M"
Data ".G0#590$.'0#590$.M"
Data ".G0#590#.(0#590$.M"
Data ".G0$T1U)0#.(0$T0U*0$.M"
Data ".G0$T1U)0#.(0$T0U)0%.M"
Data ".G0$T1U)0#.(0$T0U)0$.N"
Data ".G0$T1U)0#.(0$T0U)0$.N"
Data ".G0<.'0<.M"
Data ".D0?.&0?.K"
Data ".A0B.&0B.H"
Data ".@0D.%0D.F"
Data ".>0F.%0E.E"
Data ".<0#D*0?.%0>D*0#.C"
Data ".;0#D,0>.%0=D,0$.A"
Data ".:0$D,0>.%0=D,0$.A"
Data ".:0%D*0?.%0>D*0&.@"
Data ".:0'D&0A.%0@D&0(.@"
Data ".:0J.%0J.@"
Data ".90K.%0J.@"
Data ".90K.%0J.@"
Data ".90K.%0J.@"
MechMouthOpen:
Data 26, 11, 52, 48
Data "0<"
Data "0)F(E#F'0)"
Data "0%F,E#F+0%"
Data "0$4$F+E#F+4#0$"
Data "0%470$"
Data "B#0$460$B#"
Data "B#0%450$B#"
Data "B$0$440%B#"
Data "E#B#0%430$B#E#"
Data "E#B$07B#E#"
Data "E%06B#E$"
MechMouthShut:
Data 26, 11, 52, 48
Data "0.B$0."
Data "0)B.0)"
Data "0%B$0%B,0&B#0%"
Data "B(00B("
Data "B*0,B*"
Data "B$E$B4E$B$"
Data "B$E$B4E$B$"
Data "B<"
Data "E#B:E#"
Data "E#B:E#"
Data "E%B7E$"
MechEyesOpen:
Data 34, 10, 48, 28
Data "B&0&B40&B&"
Data "B$0*B00*B$"
Data "B#0%F&0%B.0%F&0%B#"
Data "B#F#0%F&0$B.F#0%F&0$B#"
Data "0#F#0%F'0$B,0#F#0%F'0$"
Data "0(F&0$B,0(F&0$"
Data "0'F&0%B,0'F&0%"
Data "0'F&0$B(E#B&0'F&0$B#"
Data "B#0+B)E$B&0+B$"
Data "B%0(B+E#B(0(B%"
MechEyesShut:
Data 34, 10, 48, 28
Data "BD"
Data "BD"
Data "BD"
Data "BD"
Data "BD"
Data "B#0-B-0-"
Data "B#0-B-0-"
Data "B3E#B2"
Data "B3E$B1"
Data "B4E#B1"
DrvArt:
Data 108, 181, 0, 0
Data ".K0,.["
Data ".G04.W"
Data ".E09.T"
Data ".C0=.R"
Data ".A0@.Q"
Data ".@0C.O"
Data ".>0F.N"
Data ".=0H.M"
Data ".<0J.L"
Data ".<0K.K"
Data ".;0L.K"
Data ".:0N.J"
Data ".:0N.J"
Data ".90P.I"
Data ".90P.I"
Data ".90Q.H"
Data ".80R.H"
Data ".80R.H"
Data ".80R.H"
Data ".80R.H"
Data ".:0+B#0*B+0)B(0(.H"
Data ".:02B.0*B'0'.H"
Data ".:0(B$0%B80%B'0'.H"
Data ".:0(BE0'.H"
Data ".;0'B'0&B00&B*0&.I"
Data ".90)B&0)B-0)B(0'.H"
Data ".70+B%0$F$0$F$B,0$F$0$F$B(0(.G"
Data ".70$B#0(B%0$F$0$F$0#B+0$F$0$F$0#B(0(.F"
Data ".60$B$0'B&0$F$0'B+0$F$0'B(0(.F"
Data ".60$B$0%B(0$F$0&B,0$F$0&B)0$B$0$.F"
Data ".60$B$0$B)0*B(E#B%0*B)0$B%0$.E"
Data ".60$B$0$B*0(B)E$B%0(B*0$B%0$.E"
Data ".60$B$0$B7E$B30$B%0$.E"
Data ".60$B$0$B8E$B20$B%0$.E"
Data ".60$B$0$B8E$B20$B$0%.E"
Data ".60$B%0$B8E#B20$B$0$.F"
Data ".70$B$0$B8E$B10$B$0$.F"
Data ".70(B4E(B00(.G"
Data ".80'B$E'BA0'.H"
Data ".;0%B#E'BA0$.K"
Data ".<0$B$E$BB0$.L"
Data ".<0$B*07B)0$.L"
Data ".=0$B(0%F20%B(0%.L"
Data ".=0$B)0$4#F04#0%B(0$.M"
Data ".>0$B(0$4$F/4#0$B(0%.M"
Data ".>0%B(0$400%B(0$.N"
Data ".?0$B(0$400$B(0$.O"
Data ".@0$B(0$4.0%B'0%.O"
Data ".@0%B'0$4.0$B'0%.P"
Data ".A0%B'01B&0%.Q"
Data ".B0%B&00B&0%.R"
Data ".C0&B50%.S"
Data ".E0%B20&.T"
Data ".F0'B,0'.V"
Data ".H02.X"
Data ".G04.W"
Data ".F0%B00%.V"
Data ".F0$B20$.V"
Data ".F0$B20$.V"
Data ".F0$B20$.V"
Data ".F0$B20$.V"
Data ".F0$B20$.V"
Data ".F0$B20$.V"
Data ".E0&B10%.U"
Data ".D0:.T"
Data ".D0$T$02T$0$.T"
Data ".D0$T60$.T"
Data ".008T609.?"
Data "./09F605U%0#.?"
Data "./0$T50$T60$T'U20#.>"
Data "./0&T30$T60$U10%U%0#.>"
Data "./0'T20%T50$U10&U$0#.>"
Data "..0$T$0&T108T#U10$T#0$U#0#.>"
Data "..0$T&0&T006T$U10$T$0%.>"
Data "..0$T'0&T90#T-U10$T#F$0%.="
Data ".-0%T)0&T70#T.U/0$T$F$T#0%.<"
Data ".-F$T,0$T70#T.U/0$T$F$T%0$.;"
Data ".-F$T,0$T70#T.U/0$T$F$T&0%.9"
Data ".-F$T,0$T70#T.U/0$T%F$T&0$.9"
Data ".,F%T+0$T80#T.U/0$T%F$T'0$.8"
Data ".,F$T,0$T80#T.U/0$T%F$T'0$.8"
Data ".,F$T,0$T80#T.U/0$T%F%T&0$.8"
Data ".,F$T+0%T80#T&04U%0$T&F$T&0$.8"
Data ".,F$T+0$T90#T%06U$0$T&F$T&0%.7"
Data ".+F%T+0$T90#T%0$520$U#0$T'F$T'0*.1"
Data ".+F$T,0$T90#T%0$520$U#0$T(F$T&0-.."
Data ".+F$T+0$T:0#T%0$520$U#0$T(F$T&0$U'0(.,"
Data ".*0#F$T+0$T:0#T%0$5$4.5$0$U#0$T(F$T&0$U+0&.*"
Data ".*0#F$T+0$T:0#T%0$520$U#0$T)F$T&0$U,0%.)"
Data ".*0#F$T*0%T:0#T%0$520$U$0$T(F$T&0$U-0&.'"
Data ".*F$T+0$F$T90#T%06U$0$T(F$T&0$U/0%.&"
Data ".)0#F$T+0$F$T90#T&05U$0%T'F%T%0$U00$.&"
Data ".)0#F$T+0$F$T90#T/U-04U00$.%"
Data ".)0#F$T*0%F%T80#T/U,07U/0$.$"
Data ".)0#F$T*0$T#F%T80#T/U,0$U#05U.0$.$"
Data ".(0#F$T+0$T#F%T80#T/U+09F/0$F#"
Data ".(0#F$T+0$T#F&T70#T/U+0$F#06F/0$F#"
Data ".(0#F$T*0$T%F%T70#T/U+0$F#06F/0%"
Data ".'0$F$T*0$T%F&T60#T/U*0$T$0&D.0&T00$"
Data ".'0$F$T*0$T&F%T60#T/U*0$T$06T00$"
Data ".'0#F$T*0%T&F%T60#T0U)0$T$06T00$"
Data ".'0#F$T*0$T'F&T50#T0U)0$T$06T00$"
Data ".&0$F$T*0$T'0.T-0#T0U)0$T$0CT#0$"
Data ".&0$F$T*0$T&00T,0#T0U)0$T%0E"
Data ".&0$F$T)0$T'0$F,0$T,0#T0U)0$T%04E#A/0%"
Data ".&0#F$T*0$T'0$F,0$T,0#T0U)0$T&02E*A*0$"
Data ".%0,T$0$T'0$F,0$T,0#T0U*0$T+0$A:0$"
Data ".$01T'0$F,0$T,0#T0U*0$T+0$A90%"
Data ".#01T(00T,0#T0U*0%T*0$A90%"
Data "02T)0/T,0#T0U+0$T*0$A80&"
Data "02T-F%T20#T0U+0%T)0$A80&"
Data "02T-F%T20#T0U,0$T*0$A60'"
Data "0$D.0$T-F&T10#T1U,0$T)0<.#"
Data "02T.F%T10#T1U-0$T)0:.$"
Data "02T.F%T10#T1U-0%T90&.'"
Data "02T.F&T00#T1U/0%T60&.("
Data "02TPU00&T20&.*"
Data "03TOU10(T-0'.+"
Data "03TOU00$.#04.-"
Data "0o.'0..0"
Data "0o.A"
Data ".#01.%0$F%T.U*0#.$0$T1U'F%0$.D"
Data ".#00.&0$F%T.U*0#.$0$T1U'F%0$.D"
Data ".$0..'0$F%T.U*0#.$0$T1U'F%0$.D"
Data ".50$F%T.U*0#.$0$T1U'F%U#0#.D"
Data ".50$F%T.U*0#.$0$T2U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T2U&F$U#0#.D"
Data ".50$F%T/U)0#.%0$T2U&F$U#0#.D"
Data ".50$F%T/U).&0$T2U&F$U#0#.D"
Data ".50$F%T/U).&0$T2U&F$U#0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0$.C"
Data ".50$F%T/U(0#.&0$T2U&F%0$.C"
Data ".50$F%T/U(0#.&0$T2U&F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U%F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U%F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U%F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F%0#.C"
Data ".50$F%T/U'0#.(0$T3U%F%0#.C"
Data ".50$T2U'0#.(0$T3U(0#.C"
Data ".40%T2U'0#.(0$T3U(0#.C"
Data ".30<.(0=.B"
Data ".20>.'0>.A"
Data ".20>.'0?.@"
Data ".20>.'0A.>"
Data ".10?.'0B.="
Data ".10?.'0C.<"
Data ".10?.'0=D'0$.;"
Data ".00A.&0;D*0%.9"
Data ".00A.&0;D*0%.9"
Data ".00A.&0<D(0&.9"
Data "./0B.&0F.9"
Data "./0B.&0F.9"
Data "./0B.&0F.9"
DrvMouthOpen:
Data 22, 10, 35, 41
Data "B#07"
Data "0%F20%"
Data "B#0$4#F04#0%"
Data "B#0$4$F/4#0$B#"
Data "B$0$400%B#"
Data "B$0$400$B$"
Data "B%0$4.0%B$"
Data "B%0$4.0$B%"
Data "B&01B%"
Data "B&00B&"
DrvMouthShut:
Data 22, 10, 35, 41
Data "B8"
Data "B%0$B/0#B%"
Data "B%0%B,0%B%"
Data "B&00B&"
Data "B(0,B("
Data "B8"
Data "B8"
Data "B8"
Data "B8"
Data "B8"
DrvEyesOpen:
Data 27, 8, 33, 24
Data "B$0&B00&B%"
Data "B#0)B-0)B#"
Data "0$F$0$F$B,0$F$0$F$B#"
Data "0$F$0$F$0#B+0$F$0$F$0#"
Data "0$F$0'B+0$F$0'"
Data "0$F$0&B,0$F$0&B#"
Data "0*B(E#B%0*B#"
Data "B#0(B)E$B%0(B$"
DrvEyesShut:
Data 27, 8, 33, 24
Data "B="
Data "B="
Data "B="
Data "B="
Data "0+B+0+"
Data "0+B+0+"
Data "B0E#B."
Data "B0E$B-"
DrvArtF:
Data 108, 181, 0, 0
Data ".K0,.["
Data ".G04.W"
Data ".E09.T"
Data ".C0=.R"
Data ".A0@.Q"
Data ".@0C.O"
Data ".>0F.N"
Data ".=0H.M"
Data ".<0J.L"
Data ".<0K.K"
Data ".;0L.K"
Data ".:0N.J"
Data ".:0N.J"
Data ".90P.I"
Data ".90P.I"
Data ".90Q.H"
Data ".80R.H"
Data ".80R.H"
Data ".80R.H"
Data ".80R.H"
Data ".;0*B#0*B+0)B%0+.H"
Data ".;01B.0*B#0+.H"
Data ".90*B#0%B80%B#0+.H"
Data ".80+B@0+.H"
Data ".70-B%0&B00&B&0,.G"
Data ".70-B$0)B-0)B$0,.G"
Data ".60.B#0$F$0$F$B,0$F$0$F$B$0-.F"
Data ".60.B#0$F$0$F$0#B+0$F$0$F$0#B#0-.F"
Data ".60.B#0$F$0'B+0$F$0'B#0-.F"
Data ".50/B#0$F$0&B,0$F$0&B$0..E"
Data ".50/B#0*B(E#B%0*B$0..E"
Data ".50/B$0(B)E$B%0(B%0..E"
Data ".400B1E$B.0/.D"
Data ".400B2E$B-0/.D"
Data ".400B2E$B-0/.D"
Data ".400B3E#B-0/.D"
Data ".301B3E$B,00.C"
Data ".300E#B/E(B,00.C"
Data ".30.E'B=00.C"
Data ".20/E'B=01.B"
Data ".200E$B?01.B"
Data ".202B&07B&01.B"
Data ".103B%0%F20%B&02.A"
Data ".103B&0$4#F04#0%B&02.A"
Data ".103B&0$4$F/4#0$B'02.A"
Data ".103B'0$400%B'02.A"
Data ".103B'0$400$B'03.A"
Data ".103B(0$4.0%B'03.A"
Data ".104B'0$4.0$B'04.A"
Data ".105B'01B&05.A"
Data ".106B&00B&06.A"
Data ".103.#0&B50%.#03.A"
Data ".202.%0%B20&.$03.A"
Data ".202.&0'B,0'.&03.A"
Data ".203.'02.(03.A"
Data ".203.&04.'03.A"
Data ".203.%0%B00%.&02.B"
Data ".203.%0$B20$.&02.B"
Data ".203.%0$B20$.&02.B"
Data ".203.%0$B20$.&02.B"
Data ".203.%0$B20$.&02.B"
Data ".203.%0$B20$.&02.B"
Data ".203.%0$B20$.&02.B"
Data ".203.$0&B10%.%02.B"
Data ".203.#0:.$02.B"
Data ".203.#0$T$02T$0$.$02.B"
Data ".203.#0$T60$.$02.B"
Data ".008T609.?"
Data "./09F606U$0#.?"
Data "./0$T#03T#0$T60$T#03U%0#.>"
Data "./06T#0$T60$U$02U%0#.>"
Data "./06T#0%T50$U$03U$0#.>"
Data "..0$T$03T$08T#U$04U#0#.>"
Data "..0$T%02T%06T$U$02T#0%.>"
Data "..0$T%02T/0#T-U$02F$0%.="
Data ".-0%T%02T/0#T.U#02F$T#0%.<"
Data ".-F$T&02T/0#T.02T#F$T%0$.;"
Data ".-F$T&02T/0#T.02T#F$T&0%.9"
Data ".-F$T&02T/0#T.02T$F$T&0$.9"
Data ".,F%T&02T/0#T.02T$F$T'0$.8"
Data ".,F$T'02T/0#T.02T$F$T'0$.8"
Data ".,F$T'0/T20#T.U$00T$F%T&0$.8"
Data ".,F$T'0,T50#T&0:T%F$T&0$.8"
Data ".,F$T'0)T80#T%0;T%F$T&0%.7"
Data ".+F%T'0%T#0$T90#T%0$520$U#0&T%F$T'0*.1"
Data ".+F$T,0$T90#T%0$520$U#0$T(F$T&0-.."
Data ".+F$T+0$T:0#T%0$520$U#0$T(F$T&0$U'0(.,"
Data ".*0#F$T+0$T:0#T%0$5$4.5$0$U#0$T(F$T&0$U+0&.*"
Data ".*0#F$T+0$T:0#T%0$520$U#0$T)F$T&0$U,0%.)"
Data ".*0#F$T*0%T:0#T%0$520$U$0$T(F$T&0$U-0&.'"
Data ".*F$T+0$F$T90#T%06U$0$T(F$T&0$U/0%.&"
Data ".)0#F$T+0$F$T90#T&05U$0%T'F%T%0$U00$.&"
Data ".)0#F$T+0$F$T90#T/U-04U00$.%"
Data ".)0#F$T*0%F%T80#T/U,07U/0$.$"
Data ".)0#F$T*0$T#F%T80#T/U,0$U#05U.0$.$"
Data ".(0#F$T+0$T#F%T80#T/U+09F/0$F#"
Data ".(0#F$T+0$T#F&T70#T/U+0$F#06F/0$F#"
Data ".(0#F$T*0$T%F%T70#T/U+0$F#06F/0%"
Data ".'0$F$T*0$T%F&T60#T/U*0$T$0&D.0&T00$"
Data ".'0$F$T*0$T&F%T60#T/U*0$T$06T00$"
Data ".'0#F$T*0%T&F%T60#T0U)0$T$06T00$"
Data ".'0#F$T*0$T'F&T50#T0U)0$T$06T00$"
Data ".&0$F$T*0$T'0.T-0#T0U)0$T$0CT#0$"
Data ".&0$F$T*0$T&00T,0#T0U)0$T%0E"
Data ".&0$F$T)0$T'0$F,0$T,0#T0U)0$T%04E#A/0%"
Data ".&0#F$T*0$T'0$F,0$T,0#T0U)0$T&02E*A*0$"
Data ".%0,T$0$T'0$F,0$T,0#T0U*0$T+0$A:0$"
Data ".$01T'0$F,0$T,0#T0U*0$T+0$A90%"
Data ".#01T(00T,0#T0U*0%T*0$A90%"
Data "02T)0/T,0#T0U+0$T*0$A80&"
Data "02T-F%T20#T0U+0%T)0$A80&"
Data "02T-F%T20#T0U,0$T*0$A60'"
Data "0$D.0$T-F&T10#T1U,0$T)0<.#"
Data "02T.F%T10#T1U-0$T)0:.$"
Data "02T.F%T10#T1U-0%T90&.'"
Data "02T.F&T00#T1U/0%T60&.("
Data "02TPU00&T20&.*"
Data "03TOU10(T-0'.+"
Data "03TOU00$.#04.-"
Data "0o.'0..0"
Data "0o.A"
Data ".#01.%0$F%T.U*0#.$0$T1U'F%0$.D"
Data ".#00.&0$F%T.U*0#.$0$T1U'F%0$.D"
Data ".$0..'0$F%T.U*0#.$0$T1U'F%0$.D"
Data ".50$F%T.U*0#.$0$T1U'F%U#0#.D"
Data ".50$F%T.U*0#.$0$T2U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U&F%U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T1U'F$U#0#.D"
Data ".50$F%T.U*0#.%0$T2U&F$U#0#.D"
Data ".50$F%T/U)0#.%0$T2U&F$U#0#.D"
Data ".50$F%T/U).&0$T2U&F$U#0#.D"
Data ".50$F%T/U).&0$T2U&F$U#0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0#.D"
Data ".50$F%T/U(0#.&0$T2U&F%0$.C"
Data ".50$F%T/U(0#.&0$T2U&F%0$.C"
Data ".50$F%T/U(0#.&0$T2U&F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U%F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U%F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U%F%U#0#.C"
Data ".50$F%T/U(0#.&0$T3U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T2U&F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F$U#0#.C"
Data ".50$F%T/U(0#.'0$T3U%F%0#.C"
Data ".50$F%T/U'0#.(0$T3U%F%0#.C"
Data ".50$T2U'0#.(0$T3U(0#.C"
Data ".40%T2U'0#.(0$T3U(0#.C"
Data ".30<.(0=.B"
Data ".20>.'0>.A"
Data ".20>.'0?.@"
Data ".20>.'0A.>"
Data ".10?.'0B.="
Data ".10?.'0C.<"
Data ".10?.'0=D'0$.;"
Data ".00A.&0;D*0%.9"
Data ".00A.&0;D*0%.9"
Data ".00A.&0<D(0&.9"
Data "./0B.&0F.9"
Data "./0B.&0F.9"
Data "./0B.&0F.9"
DrvMouthOpenF:
Data 22, 10, 35, 41
Data "B#07"
Data "0%F20%"
Data "B#0$4#F04#0%"
Data "B#0$4$F/4#0$B#"
Data "B$0$400%B#"
Data "B$0$400$B$"
Data "B%0$4.0%B$"
Data "B%0$4.0$B%"
Data "B&01B%"
Data "B&00B&"
DrvMouthShutF:
Data 22, 10, 35, 41
Data "B8"
Data "B%0$B/0#B%"
Data "B%0%B,0%B%"
Data "B&00B&"
Data "B(0,B("
Data "B8"
Data "B8"
Data "B8"
Data "B8"
Data "B8"
DrvEyesOpenF:
Data 27, 8, 33, 24
Data "B$0&B00&B%"
Data "B#0)B-0)B#"
Data "0$F$0$F$B,0$F$0$F$B#"
Data "0$F$0$F$0#B+0$F$0$F$0#"
Data "0$F$0'B+0$F$0'"
Data "0$F$0&B,0$F$0&B#"
Data "0*B(E#B%0*B#"
Data "B#0(B)E$B%0(B$"
DrvEyesShutF:
Data 27, 8, 33, 24
Data "B="
Data "B="
Data "B="
Data "B="
Data "0+B+0+"
Data "0+B+0+"
Data "B0E#B."
Data "B0E$B-"
MechArt2:
Data 96, 182, 0, 0
Data ".P0&.P"
Data ".M0,.-4$.@"
Data ".H06.)4%.>"
Data ".F0)3,0*.&4&.="
Data ".D0'350'.%4&.<"
Data ".B0&3:0&.$4'.;"
Data ".@0&3>0&.#4'.:"
Data ".?0%3-0-3,0%4'.:"
Data ".>0%3-0/3,0%4'.9"
Data ".=0%3-0$5,0$3.0#4'.9"
Data ".<0%3.0$5%3&5%0$3/0#4&.9"
Data ".;0%3/0$5%3'5$0$304'.8"
Data ".:0%300$5%3'5$0$314&.8"
Data ".:0$310$5%3&5%0$314&.8"
Data ".90$320$5&3$5&0$324%.8"
Data ".90$3200324&.7"
Data ".80$340.344%.7"
Data ".80$3R4%.7"
Data ".#0E3G4$.7"
Data "0F3G4$.7"
Data ".#0$4$3>4#0%3F0#4#.7"
Data ".#0$4$3>4$0I4#.7"
Data ".$0$4A0J.7"
Data ".$0$4B0I.7"
Data ".%0$4>0-B*0/B#0(.:"
Data ".%0$4.0;B.0-B#0(.:"
Data ".&0<B$0&B:0&B$0(.:"
Data ".&0+.,0)BF0).9"
Data ".90)B'0&B40&B'0).9"
Data ".90)B%0*B00*B%0).9"
Data ".90)B$0%F&0%B.0%F&0%B$0*.8"
Data ".90)B$F#0%F&0$B.F#0%F&0$B$0*.8"
Data ".80*B#0#F#0%F'0$B,0#F#0%F'0$B$0).8"
Data ".60,B#0(F&0$B,0(F&0$B$0+.6"
Data ".50-B#0'F&0%B,0'F&0%B$0,.5"
Data ".40%B#0*B#0'F&0$B(E#B&0'F&0$B%0)B#0%.4"
Data ".40$B$0*B$0+B)E$B&0+B&0)B$0$.4"
Data ".40$B$0*B&0(B+E#B(0(B'0)B%0$.3"
Data ".30$B%0*B5E$B20)B%0$.3"
Data ".30$B%0*B6E#B20)B%0$.3"
Data ".30$B%0*B6E$B10)B%0$.3"
Data ".30$B%0*B7E#B10)B%0$.3"
Data ".30$B&0(B8E$B00)B%0$.3"
Data ".30$B&0(B+0$B*E'B%0$B'E&0)B%0$.3"
Data ".30%B%0$B$0$B*0(B$E&B&0(B%E(0#B$0%B%0$.3"
Data ".40$B$E#0$B,0.B%0-B#E(B%0$E$B#0$.4"
Data ".40%B$0$B*0@E)B#0$B%0$.4"
Data ".50)B(0CB$E%0).5"
Data ".60(B&0FB&0(.6"
Data ".;0$B%0.F(E#F'0.B&0$.:"
Data ".;0$B(0'F,E#F+0'B(0$.;"
Data ".;0%B$E$B%0$4$F+E#F+4#0$B%E$B%0$.;"
Data ".<0$B$E%B$0%470$B%E$B$0$.<"
Data ".=0$B$E$B%0$460$B%E$B$0%.<"
Data ".=0%B#E%B$0%450$B$E%B$0$.="
Data ".>0$B$E%B$0$440%B$E$B$0$.>"
Data ".?0$B$E%B#0%430$B#E%B$0%.>"
Data ".@0$B$E$B$07B#E$B$0%.?"
Data ".@0%B$E%06B#E%B#0%.@"
Data ".A0%B$E%B4E%B$0%.A"
Data ".C0%B#E'B.E'B#0&.B"
Data ".D0%B#E'B&E$B&E'B#0%.D"
Data ".E0'E2B#0&.E"
Data ".G0(E-0'.G"
Data ".G08.G"
Data ".G0$B%0.B%0$.G"
Data ".G0$B40$.G"
Data ".G0$B40$.G"
Data ".G0$B40$.G"
Data ".G0$B40$.G"
Data ".E0&B40'.D"
Data ".?0,B40,.?"
Data ".90.T$0$B40%U#0/.8"
Data ".90'T+0$B40$U+0(.8"
Data ".90&T,0%B30$U,0&.9"
Data ".;0%T,06U,0%.;"
Data ".-05T*06U*06.,"
Data ".+09T)0$F00%U)08.+"
Data ".*0%T#0&T00%T(0$F00$U(0&T$U.0&U#0$.*"
Data ".)0%T&0%T00&T'0$F/0$U'0%U00&U&0%.("
Data ".(0$T)0&T00%T&0$F.0$U&0&U00%U)0%.'"
Data ".&0%T,0&T/0&T$0%F-0$U%0%T#U/0%U,0%.&"
Data ".%0%T/0%T00%T$0$F,0%U#0&T%U,0&U/0$.%"
Data ".$0%T20%T/0(F,0(T'U*0&U20%.#"
Data ".#0$T50&T/04T)U(0&U50%"
Data "0%T70%T/02T*U'0%U70%"
Data ".$0%T60%T00$T$0#T#U#T%0$T,U'0$U70%.#"
Data ".%0%T70$T30#T#U#T1U&0$U70%.$"
Data ".'0%T60%T10#T#U#T2U$0$U70%.%"
Data ".(0%T60%T00#T#U#T-E$T%U#0$U70%.&"
Data ".(0&T60%T/0#T#U#T-E$T%0%U60%.'"
Data ".(0$T#0%T60$T.0#T#U#T+0$E$0'U60&.'"
Data ".'0$T%0%T60%T,0#T#U#T*5#0$E$0&U50%U$0#.'"
Data ".'0$T'0%T50&T*0#T#U#T*5%E$0%U50%U%0#.'"
Data ".'0$T(0%T50&T)0#T#U#T*0$U#E#0%U50%U&0$.&"
Data ".&0%T*0%T50$T)0#T#U#T*0$U#0%U50%U(0#.&"
Data ".&0$T,0%T50%T'0#T#U#T*0'U50%U)0#.&"
Data ".&0$T-0%T50%T&0#T#U#T*0&U50%U*0#.&"
Data ".&0$T-0'T40%T%0#T#U#T*0%U50%U+0#.&"
Data ".&0$T-0$F#0%T50$T$0#T#U#T*0$U50$U-0#.&"
Data ".&0$T-0$F%0$T50&T#U#T)0$U40%U.0#.&"
Data ".'0$T,0$F&0%T40%T#U#T(0%U30%U/0#.&"
Data ".'0$T,0$F'0%T20&T#U#T'0%U30%U00#.&"
Data ".'0$T,0$F(0%T'00T#U#T&0%U30%U10#.&"
Data ".'0$T,0/T#02U$T%0%U30%U10#.'"
Data ".'0$T-01B.0%U#T$0%U30%U20#.'"
Data ".'0$T80%B00%T$0$U30%U30#.'"
Data ".'0$T604B$0$T#0%U20$U50#.'"
Data ".'0$T400B*0$T$0%U/0%U60#.'"
Data ".(0$T20%B,0%B)0$T%0$U.0%U70#.'"
Data ".(0$T20$B.0%B(0$T&0$U,0%U80#.'"
Data ".(0$T10$B$0,B$0$B(0$T'0$U*0%T#U80#.'"
Data ".(0$T10$B00$B(0$T'0%U(0%T$U70$.'"
Data ".(0$T10$B00$B(0$T(0%U&0%T%U70#.("
Data ".(0$T10$B00$B(0$T)0$U%0%T'U60#.("
Data ".(0$T10$B00$B(0$T*0$U#0$T)U60#.("
Data ".(0$T10$B00$B'0$U#T+0%T*U60#.("
Data ".(0$T20$B/0*U$T+0$T+U60#.("
Data ".)0$T10%B-0+T#U#T6U60#.("
Data ".)0$T200T%0.T1U60#.("
Data ".)0u.("
Data ".)0F5,0F.)"
Data ".)0$AB0$5,0$AB0$.)"
Data ".)0$AB0$5$A(5$0$AB0$.)"
Data ".)0$AB0$5$A(5$0$AB0$.)"
Data ".)0$A.0#A50$5$A(5$0$AB0$.)"
Data ".)01A50$5$A(5$0$AB0$.)"
Data ".)0-E$0%A40$5$A(5$0$AB0$.)"
Data ".)0%E-0$A40$5,0$AB0$.)"
Data ".)0$E.085,0F.)"
Data ".)0$E.0f.)"
Data ".)0$E&D#E)0e.*"
Data ".(0%E$D%E&8#E$0%T-U+0$.&0$T0U,0$.4"
Data ".(0$E$D&E&8#E%0$T-U+0$.&0$T0U,0$.4"
Data ".(0$E$D'E%8#E%0$T-U+0$.&0$T0U,0$.4"
Data ".(0$E$D'E%8#E%0$T-U+0$.&0$T0U,0$.4"
Data ".'0%E$D'E%8#E%0$T-U+0$.&0$T0U,0$.4"
Data ".'0$E&D&E%8$E$0$T-U+0$.&0$T0U,0$.4"
Data ".'0$E)D#E%8$E$0$T.U*0$.&0$T0U,0$.4"
Data ".'0$E)D#E%8$E$0$T.U*0$.&0$T0U,0$.4"
Data ".'0$E)D#E%8$E#0$T/U*0$.&0$T0U,0$.4"
Data ".(0$E(D$E$8$E#0$T/U*0$.&0$T0U,0$.4"
Data ".(0$E(D$E%8#E#0$T/U*0$.&0$T0U,0$.4"
Data ".(0$E'0#D$E&0%T/U*0$.'0$T/U,0$.4"
Data ".(0$E&0$D$E&0$T0U*0$.'0$T/U,0$.4"
Data ".(0$E&0$.#0$E%0$T0U*0$.'0$T0U+0#.5"
Data ".(0$E%0$.$0$E%0$T-U-0$.'0$T&U(T&U+0#.5"
Data ".(0$E$0%.%0$E#0$T'U+T#U*0$.'0$T*U00$.5"
Data ".(0$E$0$.&0'T&U%T*U*0$.'0$T/U+0$.5"
Data ".)0'.'0&T1U*0$.'0$T0U*0$.5"
Data ".)0&.)0%T1U*0$.'0$T0U*0$.5"
Data ".)0%.*0%T1U*0$.'0$T0U*0$.5"
Data ".)0%.+0$T1U*0$.'0$T0U*0$.5"
Data ".*0#.,0$T1U*0$.'0$T0U*0$.5"
Data ".50$T1U*0$.'0$T0U*0$.5"
Data ".50$T1U*0$.'0$T0U*0$.5"
Data ".60$T0U*0$.'0$T0U*0$.5"
Data ".60$T1U)0$.'0$T0U*0$.5"
Data ".60$T1U)0$.'0$T0U*0$.5"
Data ".60<.'0<.5"
Data ".60#590$.'0#590$.5"
Data ".60#590$.'0#590$.5"
Data ".60#590$.'0#590$.5"
Data ".60#590#.(0#590$.5"
Data ".60$T1U)0#.(0$T0U*0$.5"
Data ".60$T1U)0#.(0$T0U)0%.5"
Data ".60$T1U)0#.(0$T0U)0$.6"
Data ".60$T1U)0#.(0$T0U)0$.6"
Data ".60<.'0<.5"
Data ".30?.&0?.3"
Data ".00B.&0B.0"
Data "./0D.%0D.."
Data ".-0F.%0E.-"
Data ".+0#D*0?.%0>D*0#.+"
Data ".*0#D,0>.%0=D,0$.)"
Data ".)0$D,0>.%0=D,0$.)"
Data ".)0%D*0?.%0>D*0&.("
Data ".)0'D&0A.%0@D&0(.("
Data ".)0J.%0J.("
Data ".(0K.%0J.("
Data ".(0K.%0J.("
Data ".(0K.%0J.("
MechArt3:
Data 101, 182, 0, 0
Data ".S0&.R"
Data ".P0,.-4$.B"
Data ".K06.)4%.@"
Data ".I0)3,0*.&4&.?"
Data ".G0'350'.%4&.>"
Data ".E0&3:0&.$4'.="
Data ".C0&3>0&.#4'.<"
Data ".B0%3-0-3,0%4'.<"
Data ".A0%3-0/3,0%4'.;"
Data ".@0%3-0$5,0$3.0#4'.;"
Data ".?0%3.0$5%3&5%0$3/0#4&.;"
Data ".>0%3/0$5%3'5$0$304'.:"
Data ".=0%300$5%3'5$0$314&.:"
Data ".=0$310$5%3&5%0$314&.:"
Data ".<0$320$5&3$5&0$324%.:"
Data ".<0$3200324&.9"
Data ".;0$340.344%.9"
Data ".;0$3R4%.9"
Data ".&0E3G4$.9"
Data ".%0F3G4$.9"
Data ".&0$4$3>4#0%3F0#4#.9"
Data ".&0$4$3>4$0I4#.9"
Data ".'0$4A0J.9"
Data ".'0$4B0I.9"
Data ".(0$4>0-B*0/B#0(.<"
Data ".(0$4.0;B.0-B#0(.<"
Data ".)0<B$0&B:0&B$0(.<"
Data ".)0+.,0)BF0).;"
Data ".<0)B'0&B40&B'0).;"
Data ".<0)B%0*B00*B%0).;"
Data ".<0)B$0%F&0%B.0%F&0%B$0*.:"
Data ".<0)B$F#0%F&0$B.F#0%F&0$B$0*.:"
Data ".;0*B#0#F#0%F'0$B,0#F#0%F'0$B$0).:"
Data ".90,B#0(F&0$B,0(F&0$B$0+.8"
Data ".80-B#0'F&0%B,0'F&0%B$0,.7"
Data ".70%B#0*B#0'F&0$B(E#B&0'F&0$B%0)B#0%.6"
Data ".70$B$0*B$0+B)E$B&0+B&0)B$0$.6"
Data ".70$B$0*B&0(B+E#B(0(B'0)B%0$.5"
Data ".60$B%0*B5E$B20)B%0$.5"
Data ".60$B%0*B6E#B20)B%0$.5"
Data ".60$B%0*B6E$B10)B%0$.5"
Data ".60$B%0*B7E#B10)B%0$.5"
Data ".60$B&0(B8E$B00)B%0$.5"
Data ".60$B&0(B+0$B*E'B%0$B'E&0)B%0$.5"
Data ".60%B%0$B$0$B*0(B$E&B&0(B%E(0#B$0%B%0$.5"
Data ".70$B$E#0$B,0.B%0-B#E(B%0$E$B#0$.6"
Data ".70%B$0$B*0@E)B#0$B%0$.6"
Data ".80)B(0CB$E%0).7"
Data ".90(B&0FB&0(.8"
Data ".>0$B%0.F(E#F'0.B&0$.<"
Data ".>0$B(0'F,E#F+0'B(0$.="
Data ".>0%B$E$B%0$4$F+E#F+4#0$B%E$B%0$.="
Data ".?0$B$E%B$0%470$B%E$B$0$.>"
Data ".@0$B$E$B%0$460$B%E$B$0%.>"
Data ".@0%B#E%B$0%450$B$E%B$0$.?"
Data ".A0$B$E%B$0$440%B$E$B$0$.@"
Data ".B0$B$E%B#0%430$B#E%B$0%.@"
Data ".C0$B$E$B$07B#E$B$0%.A"
Data ".C0%B$E%06B#E%B#0%.B"
Data ".D0%B$E%B4E%B$0%.C"
Data ".F0%B#E'B.E'B#0&.D"
Data ".G0%B#E'B&E$B&E'B#0%.F"
Data ".H0'E2B#0&.G"
Data ".J0(E-0'.I"
Data ".J08.I"
Data ".J0$B%0.B%0$.I"
Data ".J0$B40$.I"
Data ".J0$B40$.I"
Data ".J0$B40$.I"
Data ".J0$B40$.I"
Data ".H0&B40'.F"
Data ".B0,B40,.A"
Data ".<0.T$0$B40%U#0/.:"
Data ".<0'T+0$B40$U+0(.:"
Data ".<0&T,0%B30$U,0&.;"
Data ".>0%T,06U,0%.="
Data ".005T*06U*06.."
Data "./08T)0$F00%U)03U#0&.-"
Data "..0&T30%T(0$F00$U(0&T$U00'.,"
Data ".-0'T40&T'0$F/0$U'0%U40$U#0%.+"
Data ".,0%T#0$T60%T&0$F.0$U&0&U40%U%0%.)"
Data ".+0%T$0%T60&T$0%F-0$U%0%T#U50$U'0%.("
Data ".*0%T&0$T80%T$0$F,0%U#0&T%U30%U(0%.'"
Data ".)0%T'0$T90(F,0(T'U30$U*0%.&"
Data ".)0$T(0%T:04T)U20%U+0%.%"
Data ".(0$T*0$T;02T*U20$U.0%.#"
Data ".'0$T+0$T=0$T$0#T#U#T%0$T,U20$U/0%"
Data ".&0%T+0%T@0#T#U#T1U20$U00$"
Data ".%0%T-0$T@0#T#U#T2U10$U00$"
Data ".$0%T.0$T@0#T#U#T-E$T%U10$U00$"
Data ".$0$T/0$T@0#T#U#T-E$T%U10$U00$"
Data ".#0$T00$T@0#T#U#T+0$E$0*U,0$U00$"
Data ".$0$T/0$T@0#T#U#T*5#0$E$0+U+0$U00$"
Data ".$0$T00$T$05T*0#T#U#T*5%E$5+U+0$U00$"
Data ".$0$T00$T#07T)0#T#U#T*0$U#E$U)0$U+0$U00$"
Data ".$0$T00&F40$T)0#T#U#T*0$U#E$U)0$U+0$U00$"
Data ".$0%T/0&F40$T)0#T#U#T*0$U#E$U)0$U+0$U00$"
Data ".%0$T/0&F'4&F+0$T)0#T#U#T*0$U#E$U)0$U+0$U00$"
Data ".%0$T/0&F$4'F$4#F&4$F$0$T)0#T#U#T*0$U,0$U+0$U00$"
Data ".%0$T/0&F$4$F(4#F$4$F%0$T)0#T#U#T*0$U,0$U+0$U00$"
Data ".%0$T/0&F-4%F&0$T)0#T#U#T*0$U,0$U+0$U00$"
Data ".&0$T.0&F.4#F'0$T)0#T#U#T*00U+0$U00$"
Data ".&0$T/0%F40$T)0#T#U#T+0/U+0$U/0$.#"
Data ".&0$T/0%F40$T)0#T#U#T4U/0$U/0$.#"
Data ".&0$T/09T)0#T#U#T4U/0$U/0$.#"
Data ".&0.T%08T*0#T#U#T4U/0$U/0$.#"
Data ".$02T#0$T>0#T#U#T4U/0$U/0$.#"
Data ".#0%B.0'T>0#T#U#T5U.0$U/0$.#"
Data ".#0$B00%T?0#T#U#T5U.0$U/0$.#"
Data "0$B$0.B$0$T?0#T#U#T5U.0$U/0$.#"
Data "0$B20$T?0#T#U#T5U.0$U/0$.#"
Data "0$B20$T?0#T#U#T5U.0$U/0$.#"
Data "0$B20$T?0#T#U#T5U.0$U/0$.#"
Data "0$B20$T?0#T#U#T5U.0$U/0$.#"
Data "0$B20$T?0#T#U#T6U-0$U/0$.#"
Data ".#0$B10$T?0#T#U#T6U-0$U/0$.#"
Data ".#0%B/0$T@0#T#U#T6U-0$U/0$.#"
Data ".$02TA0#T#U#T6U-0$U/0$.#"
Data ".%00TB0#T#U#T6U-0$U/0$.#"
Data ".+0%TC0.T1U,0.U%0$.$"
Data ".,0{.$"
Data ".,0F5,0<B.0'.$"
Data ".,0$AB0$5,0$A60%B00%.%"
Data ".,0$AB0$5$A(5$0$A60$B20$.%"
Data ".,0$AB0$5$A(5$0$A60$B20$.%"
Data ".,0$A.0#A50$5$A(5$0$A60$B$0.B$0$.%"
Data ".,01A50$5$A(5$0$A60$B20$.%"
Data ".,0-E$0%A40$5$A(5$0$A60$B20$.%"
Data ".,0%E-0$A40$5,0$A60$B20$.%"
Data ".,0$E.085,0:B20$.%"
Data ".,0$E.0ZB20$.%"
Data ".,0$E&D#E)0[B10$.%"
Data ".+0%E$D%E&8#E$0%T-U+0$.&0$T0U,0%B/0$.&"
Data ".+0$E$D&E&8#E%0$T-U+0$.&0$T0U,03.'"
Data ".+0$E$D'E%8#E%0$T-U+0$.&0$T0U,02.("
Data ".+0$E$D'E%8#E%0$T-U+0$.&0$T0U,0$.6"
Data ".*0%E$D'E%8#E%0$T-U+0$.&0$T0U,0$.6"
Data ".*0$E&D&E%8$E$0$T-U+0$.&0$T0U,0$.6"
Data ".*0$E)D#E%8$E$0$T.U*0$.&0$T0U,0$.6"
Data ".*0$E)D#E%8$E$0$T.U*0$.&0$T0U,0$.6"
Data ".*0$E)D#E%8$E#0$T/U*0$.&0$T0U,0$.6"
Data ".+0$E(D$E$8$E#0$T/U*0$.&0$T0U,0$.6"
Data ".+0$E(D$E%8#E#0$T/U*0$.&0$T0U,0$.6"
Data ".+0$E'0#D$E&0%T/U*0$.'0$T/U,0$.6"
Data ".+0$E&0$D$E&0$T0U*0$.'0$T/U,0$.6"
Data ".+0$E&0$.#0$E%0$T0U*0$.'0$T0U+0#.7"
Data ".+0$E%0$.$0$E%0$T-U-0$.'0$T&U(T&U+0#.7"
Data ".+0$E$0%.%0$E#0$T'U+T#U*0$.'0$T*U00$.7"
Data ".+0$E$0$.&0'T&U%T*U*0$.'0$T/U+0$.7"
Data ".,0'.'0&T1U*0$.'0$T0U*0$.7"
Data ".,0&.)0%T1U*0$.'0$T0U*0$.7"
Data ".,0%.*0%T1U*0$.'0$T0U*0$.7"
Data ".,0%.+0$T1U*0$.'0$T0U*0$.7"
Data ".-0#.,0$T1U*0$.'0$T0U*0$.7"
Data ".80$T1U*0$.'0$T0U*0$.7"
Data ".80$T1U*0$.'0$T0U*0$.7"
Data ".90$T0U*0$.'0$T0U*0$.7"
Data ".90$T1U)0$.'0$T0U*0$.7"
Data ".90$T1U)0$.'0$T0U*0$.7"
Data ".90<.'0<.7"
Data ".90#590$.'0#590$.7"
Data ".90#590$.'0#590$.7"
Data ".90#590$.'0#590$.7"
Data ".90#590#.(0#590$.7"
Data ".90$T1U)0#.(0$T0U*0$.7"
Data ".90$T1U)0#.(0$T0U)0%.7"
Data ".90$T1U)0#.(0$T0U)0$.8"
Data ".90$T1U)0#.(0$T0U)0$.8"
Data ".90<.'0<.7"
Data ".60?.&0?.5"
Data ".30B.&0B.2"
Data ".20D.%0D.0"
Data ".00F.%0E./"
Data "..0#D*0?.%0>D*0#.-"
Data ".-0#D,0>.%0=D,0$.+"
Data ".,0$D,0>.%0=D,0$.+"
Data ".,0%D*0?.%0>D*0&.*"
Data ".,0'D&0A.%0@D&0(.*"
Data ".,0J.%0J.*"
Data ".+0K.%0J.*"
Data ".+0K.%0J.*"
Data ".+0K.%0J.*"
CarArt:
Data 298, 82, 0, 0
Data ".|.KA0.|.a"
Data ".|.KA0.|.a"
Data ".|.KA0.30(.|.J"
Data ".|.KA0.00..|.G"
Data ".|.OA'.40&F(0&.|.F"
Data ".|.PA&.30%F,0%.20#.|.4"
Data ".|.PA&.20%F/05.|.3"
Data ".|.PA&.*0,F101C#0$.|.3"
Data ".-0].dA&.)0,F(0<E$0#.|.2"
Data ".,0_.cA&.'0.F'06A'0#E&0#.|.1"
Data ".+0$D\0$.cA&.%0&C#0*F'0$A.0$A,0$E&0#.|.0"
Data ".+0$D\0$.cA&.#0&C%0$A&0$F'0$A.0$A-0$E&0#.|./"
Data ".+0$D$FXD$0$.cA&0%C&0$A'0$F'0$A.0$A-0%E%0#.|./"
Data ".+0$D\0$.cA&0#C(0$A'0$F'0$A.0$A.0$E&0#.|.."
Data ".+0$D\0$.cA&C)0$A'0$F'02A.0%E&0#.|.-"
Data ".+0$D\0$.a0$A&C)0$A(0$F'00A00$C#E&0#.|.,"
Data ".+0$D\0$._0&A'C'0$A)0$F20$A10%C#E%0#.|.,"
Data ".+0$D\0$.^0%C%A&C'0$A*0$F00%A20$C#E&0#.|.+"
Data ".+0`.\0%C'A&C'0$A+0$F.0%A30%C#E&0#.|.*"
Data ".,0^.[0&C(A&C'0$A,0%F*0&A50$C$E&0#.|.)"
Data ".>0&.40%.j0&C*A&C&0$A.0.A70%C$E%0$.|.("
Data ".?0%.40%.h0&C,A&C&0$A00*A:0$C$E&0#.|.("
Data ".?0%.40%.g0%C.A&C&0$AP0%C$E&0#.|.'"
Data ".?0%.50%.d0&C/A&C&0$AK0*C%E%0$.|.&"
Data ".?0%.50%.b0&C1A&C%0$A30CC&E#C#0*.z"
Data ".@0%.40%.`0&C3A&C%0HC90,.u"
Data ".@0%.40%.I0;C<0/CW0-.o"
Data ".@0%.40%.10LC|C10-.i"
Data ".@0%.40FC|C90(C20-.c"
Data ".A0%.)0:C|CL0.C50-.]"
Data ".=0:C|CY0&F(0&C:0,.X"
Data "./0:C|Cf0%F,0%C>0-.R"
Data "..0-Cp0?Cb0%F/0$CC0-.L"
Data "..0$Cx0AC`0%F10$CH0-.F"
Data ".-0%Cw0$A&D#A)D#A)D#A)0$C`0$F20%CM0).D"
Data ".-0$Cx0$A&D#A)D#A)D#A)0$C_0%F30$CR0'.A"
Data ".-0$CX0+C90$A&D#A)D#A)D#A)0$C_0$F40$C30+C:0'.?"
Data ".-0$CT02C60$A&D#A)D#A)D#A)0$C_0$F40$C/02C90(.<"
Data ".-0$CR06C40$A&D#A)D#A)D#A)0$C_0$F40$C-06C:0'.:"
Data ".,0%CP0:C20$A&D#A)D#A)D#A)0$C_0$F40$C+0:C:0(.7"
Data ".,0$CP0<C10$A&D#A)D#A)D#A)0$C_0$F40$C*0<C<0'.5"
Data ".,0$C)FEC%0)D#07C/0$A&D#A)D#A)D#A)0$C`0$F20%C)0)D#07C<0'.3"
Data ".,0$C)FG0(D&07F.0BC`0$F20$C)0(D&07C>0'.0"
Data ".,0$C)FF0(D%0:F.0@F^C%F#0$F00%C(0(D%0:C?0'.."
Data ".#0/CJ0'D&0<F|F20$F.0%F(0'D&0<F'C;0'.,"
Data "01CH0'D%0>CSF\0%F*0&F(0'D%0>FH.)"
Data "0&E+0$CG0'D%0@C|C30/F(0'D%0@FG0%.&"
Data "0&E+0$CG0'D$0(D#0$E(0$D#00C|C40*C+0'D$0(D#0$E(0$D#00C5F30'.$"
Data "01CF0'D$0)D#E,D#00C|CD0'D$0)D#E,D#00CH0%.$"
Data ".#00CF0&D%0(E#D$E*D$E#00C|CC0&D%0(E#D$E*D$E#00CH0$.$"
Data ".*0$CJ0'D$0(E%D$E)D#E%0/C|CB0'D$0(E%D$E)D#E%0/CH0$.$"
Data ".*0$CJ0&D$0(E&D$E(D$E&0.C|CB0&D$0(E&D$E(D$E&0.CH0$.$"
Data ".*0$C#DI0.E'D#E(D#E(0.D|DA0.E'D#E(D#E(0.DH0#.$"
Data ".)0%DJ0-E*0&E*0.D|DA0-E*0&E*0.DH0#.$"
Data ".)0$C#DI0.E)0)E)0-D|D@0.E)0)E)0-DH0#.$"
Data ".)0$DJ0-E)0$D&0%E(0-D|D@0-E)0$D&0%E(0-DH0%"
Data ".)0$DJ0-E(0$D(0$E(0-D|D@0-E(0$D(0$E(0-D805"
Data ".)0#DK0,D(E#0$D(0$E(D#0,D|D@0,D(E#0$D(0$E(D#0,D&0AD&0$"
Data ".(0$DK0,D(E#0$D(0$E#D(0,D|D@0,D(E#0$D(0$E#D(0,D%00D80$"
Data ".(0#DL0-E(0$D(0$E(0-D|D@0-E(0$D(0$E(0-D%0$DD0$"
Data ".)0&DH0-E)0$D&0%E(0-D|D@0-E)0$D&0%E(0-D&0$DC0$"
Data ".00,D;0.E(0*E)0-D|D@0.E(0*E)0-D&0$DC0$"
Data ".=0,D.0.E)0(E)0.D|D@0.E)0(E)04DC0$"
Data ".J07E(D$E'D#E(0.D|DA0-E(D$E'D#E(0..&0$D?0("
Data ".T0.E'D#E(D$E&0|0ZE'D#E(D$E&0..(0$D-09"
Data ".T0/E%D$E)D$E%0..|.B0/E%D$E)D$E%0..(0<.,"
Data ".U0/E#D$E*D$E$0/.|.C0/E#D$E*D$E$0/.(0+.="
Data ".U00D$E+D$0/.|.D00D$E+D$0/.M"
Data ".V0/D#0#E*02.|.E0/D#0#E*02.M"
Data ".V0H.|.F0H.N"
Data ".W0G.,A|A*.50F.O"
Data ".W0FA|AI0E.O"
Data ".GA30DA|AJ0DA+.G"
Data ".9AB0BA|AL0BA:.9"
Data ".0AL0@A|AN0@AD.0"
Data ".,AQ0>A|AP0>AI.,"
Data ".+AT0:A|AT0:AL.+"
Data "..AR08A|AV08AJ.."
Data ".5AM04A|AZ04AF.4"
Data ".@AE0.A|A`0.A=.@"
Data ".RA|A|A8.R"
Data ".oA|AX.o"
Sub ReadMouse
  Local integer i, c, x, y, l
  For i = 0 To nm - 1
    c = mch(i)
    x = Device(MOUSE c, X)
    y = Device(MOUSE c, Y)
    l = Device(MOUSE c, L)
    If x <> px(c) Or y <> py(c) Or l <> pl(c) Then
      ach = c
      px(c) = x
      py(c) = y
      pl(c) = l
    EndIf
  Next
  gmx = px(ach)
  gmy = py(ach)
  gml = pl(ach)
End Sub
Function CurOver(x As integer, y As integer, w As integer, h As integer) As integer
  If hasMouse = 0 Then Exit Function
  CurOver = (curX + 20 >= x And curX <= x + w And curY + 20 >= y And curY <= y + h)
End Function
Sub CurHide
  If hasMouse Then GUI Cursor Hide
End Sub
Sub CurShow
  If hasMouse Then GUI Cursor Show
End Sub
Function PWidth(s$, f As integer) As integer
  Local integer i, t, c
  For i = 1 To Len(s$)
    c = Asc(Mid$(Choice(f = 1, UCase$(s$), s$), i, 1)) - 32
    If c >= 0 And c <= 94 Then t = t + adv(f, c)
  Next
  PWidth = t
End Function
Sub PText(x As integer, y As integer, s$, al$, f As integer, c As integer)
  Local integer i, p, fn, a
  Local string t$
  t$ = Choice(f = 1, UCase$(s$), s$)
  fn = Choice(f = 1, fTitle, fText)
  p = x
  If al$ = "C" Then p = x - PWidth(t$, f) \ 2
  If al$ = "R" Then p = x - PWidth(t$, f)
  For i = 1 To Len(t$)
    a = Asc(Mid$(t$, i, 1)) - 32
    If a >= 0 And a <= 94 Then
      Text p, y - fh(f) \ 2, Mid$(t$, i, 1), "LT", fn, 1, c, -1
      p = p + adv(f, a)
    EndIf
  Next
End Sub
Function ClickAt() As integer
  Local integer tx
  If hasTouch Then
    tx = Touch(X)
    If tx >= 0 Then
      clickX = tx
      clickY = Touch(Y)
      Do While Touch(X) >= 0
        Pause 10
      Loop
      ClickAt = 1
      Exit Function
    EndIf
  EndIf
  If hasMouse Then
    ReadMouse
    If gmx <> curX Or gmy <> curY Then
      curX = gmx
      curY = gmy
      GUI Cursor curX, curY
    EndIf
    If gml <> 0 And prevML = 0 Then
      clickX = gmx
      clickY = gmy
      ClickAt = 1
    EndIf
    prevML = gml
  EndIf
End Function
Sub WeatherLoad
  Local string l$
  Local integer p, q
  tkWx$ = ""
  On Error Skip
  Open HOME_DIR$ + "/weather.txt" For Input As #4
  If MM.Errno Then Exit Sub
  If Not Eof(#4) Then Line Input #4, l$
  Close #4
  p = Instr(l$, "|")
  If p = 0 Then Exit Sub
  q = Instr(p + 1, l$, "|")
  If q = 0 Then q = Len(l$) + 1
  On Error Skip
  If Epoch(Now) - Val(Left$(l$, p - 1)) > 10800 Then Exit Sub
  tkWx$ = Mid$(l$, p + 1, q - p - 1) + Choice(q <= Len(l$), " (" + Mid$(l$, q + 1) + ")", "")
End Sub
Sub WifiCheck
  Local string a$
  a$ = ""
  On Error Skip
  a$ = MM.Info(IP ADDRESS)
  If a$ <> "" And a$ <> "0.0.0.0" Then
    ip$ = "WiFi OK  " + a$
  Else
    ip$ = "WiFi DOWN"
  EndIf
End Sub
Sub TickerTick
  If tkw = 0 Or Timer - lastTick < TICK_MS Then Exit Sub
  lastTick = Timer
  DrawTicker
End Sub
Function TickAppend$(base$, add$, maxlen As integer) As string
  If Len(base$) >= maxlen Then
    TickAppend$ = base$
  ElseIf Len(base$) + Len(add$) <= maxlen Then
    TickAppend$ = base$ + add$
  Else
    TickAppend$ = base$ + Left$(add$, maxlen - Len(base$))
  EndIf
End Function
Sub DrawTicker
  Local string s$, c$
  Local integer p, i, a, hid, sg
  Const TICKER_MAX = 200
  s$ = ""
  If Not tickerRaceMode Then
    s$ = DDate$(Date$) + " " + Time$
    If tkWx$ <> "" Then s$ = TickAppend$(s$, "   |   " + tkWx$, TICKER_MAX)
    If ip$ <> "" Then s$ = TickAppend$(s$, "   |   " + ip$, TICKER_MAX)
  EndIf
  For sg = 0 To 4
    If tkSeg$(sg) <> "" Then s$ = TickAppend$(s$, Choice(s$ = "", tkSeg$(sg), "   |   " + tkSeg$(sg)), TICKER_MAX)
  Next
  If tkMsg$ <> "" Then s$ = TickAppend$(s$, Choice(s$ = "", tkMsg$, "   |   " + tkMsg$), TICKER_MAX)
  If Len(s$) < TICKER_MAX Then s$ = s$ + "   |   "
  tkPos = tkPos + 1
  If tkPos > Len(s$) Then
    tkPos = 1
    WifiCheck
    WeatherLoad
  EndIf
  hid = CurOver(tkx, tky, tkw, tkh)
  If hid Then CurHide
  p = tkx + 8
  i = tkPos
  Do
    c$ = Mid$(s$, i, 1)
    a = adv(0, Asc(c$) - 32)
    If p + a > tkx + tkw - 8 Then Exit Do
    Text p, tky + (tkh - fh(0)) \ 2, c$, "LT", fText, 1, C_INK, C_BAR
    p = p + a
    i = i + 1
    If i > Len(s$) Then i = 1
  Loop
  Box p, tky + 2, tkx + tkw - 3 - p, tkh - 4, 1, C_BAR, C_BAR
  If hid Then CurShow
End Sub
Function DDate$(d$)
  If Mid$(d$, 5, 1) = "-" Then
    DDate$ = Str$(Val(Mid$(d$, 9, 2))) + "-" + Str$(Val(Mid$(d$, 6, 2))) + "-" + Left$(d$, 4)
  ElseIf Mid$(d$, 3, 1) = "-" And Len(d$) = 10 Then
    DDate$ = Str$(Val(Left$(d$, 2))) + "-" + Str$(Val(Mid$(d$, 4, 2))) + "-" + Right$(d$, 4)
  Else
    DDate$ = d$
  EndIf
End Function
