Public FECHIX As String
Public REPORT As String
Public THISDAY As Date
Public MONTO As Double
Public MONTO_CONT As Double

Sub MODELO_INVERSIONES()



Dim WorkbookName As String
Dim RUTA As String
Dim MacroName1 As String
Dim MacroName2 As String

SP = 15
EP = 4
P = 10
Sheets("PANEL").Select
ActiveSheet.Shapes("TBL_M_INVERSIONES").Select '######## CAMBIAR ##########
Selection.Interior.ColorIndex = EP
Range("B1").Select


'Sheets("PANEL").Select
'With ActiveSheet.Shapes("TBL_MLA_NMD")
'    .Fill.ForeColor.RGB = RGB(208, 206, 206)
'End With

Call PROCESO_CART_BKN

RUTA = "Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones\"
WorkbookName = "Maestro Modelo de Inversiones.xlsm"
MacroName1 = "ActualizaModeloInversiones"


Workbooks.Open Filename:=RUTA & WorkbookName, WriteResPassword:="RFF" 'APERTURA DEL EXCEL CON CLAVE

Run ("'" & RUTA & WorkbookName & "'!" & MacroName1)
'Run ("'" & RUTA & WorkbookName & "'!" & MacroName2)


Workbooks("Modelo de Inversiones.xlsx").Activate
Workbooks("Modelo de Inversiones.xlsx").Close SaveChanges:=True

Workbooks("RF_Generador_Modelos.xlsm").Activate
Sheets("PANEL").Select

Sheets("PANEL").Select
ActiveSheet.Shapes("TBL_M_INVERSIONES").Select
Selection.Interior.ColorIndex = P
Range("B1").Select

'''kk = CreateObject("WScript.Shell").Popup("La cuenta " & tblVencidas.Rows(c).Item(0).ToString & " de este cliente presenta recargo...", 1)
'''Dim kk As Integer
'''Dim wShell As Variant
'''Set wShell = CreateObject("WScript.Shell")
'''kk = wShell.Popup("NO SE EMITE EL ALBARAN.", 1, "REPARTO EXTERNO TIENDA", vbInformation)
''
''Application.EnableEvents = False
''Application.DisplayAlerts = False
''
''SP = 15
''EP = 4
''P = 10
''
''Sheets("PANEL").Select
''ActiveSheet.Shapes("TBL_M_INVERSIONES").Select
''Selection.Interior.ColorIndex = EP
''Range("B1").Select
''
''
''
''Call PROCESO_CART_BKN
''Call ACTUALIZA
''Call DIAPROCESO
''
'''MsgBox ("Modelo_Inversiones_" & FECHIX)
'''Private Sub Workbook_Open()
'''kk = CreateObject("wscript.shell").Popup("Este aviso desaparecerá en 2 segundos...", 0, "Mensaje temporal") ', 0
'''End Sub
'''Modelo de Inversiones 13062018
''Workbooks(REPORT).Activate
''
''Application.EnableEvents = False
''Application.DisplayAlerts = False
''
''RUTA = "Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones"
''Archivo = "Modelo de Inversiones"
''
''ActiveWorkbook.SaveAS RUTA & "\" & Archivo & "_" & FECHIX & "" & ".xlsx"
''
''Application.EnableEvents = True
''Application.DisplayAlerts = True
''ActiveWorkbook.Close SaveChanges:=1
''ActiveWorkbook.Close SaveChanges:=1
'''MsgBox (MONTO)
'''SendKeys "{ENTER}", Trueno,
''Workbooks.Add
''
''MONTO_CONTABLE = ActiveWorkbook.Name
''
''
''Range("a1").Select
''
''    Range("a1").Select
''    ActiveCell.FormulaR1C1 = "Inversion Financiera Privado"
''    Range("a2").Select
''    ActiveCell.FormulaR1C1 = "Inversion Financiera Publico"
''    Range("a3").Select
''    ActiveCell.FormulaR1C1 = "INVERSIONES FINANCIERAS FONDOS MUTUOS"
''     Range("B1").Select
''    ActiveCell.FormulaR1C1 = _
''        "=VLOOKUP(RC[-1],'Z:\RF_PROCESOS\RF_Balance\[RF_Generador_Balance_Carteras.xlsm]Cuadratura'!C3:C4,2,0)"
''    Range("B2").Select
''    ActiveCell.FormulaR1C1 = _
''        "=VLOOKUP(RC[-1],'Z:\RF_PROCESOS\RF_Balance\[RF_Generador_Balance_Carteras.xlsm]Cuadratura'!C3:C4,2,0)"
''    Range("B3").Select
''    ActiveCell.FormulaR1C1 = _
''        "=VLOOKUP(RC[-1],'Z:\RF_PROCESOS\RF_Balance\[RF_Generador_Balance_Carteras.xlsm]Cuadratura'!C3:C4,2,0)"
''    Range("B4").Select
''    ActiveCell.FormulaR1C1 = "=SUM(R[-3]C:R[-1]C)"
''
''    MONTO_CONT = ActiveCell.Value
''
''Workbooks(MONTO_CONTABLE).Close SaveChanges:=False
''
''If MONTO > 1000000 Then
'''    Call CORREO_MODELO
''    Call hola
''End If
''
''Workbooks("RF_Generador_Modelos.xlsm").Activate
''Sheets("PANEL").Select
''ActiveSheet.Shapes("TBL_M_INVERSIONES").Select
''Selection.Interior.ColorIndex = P
''Range("B1").Select
''
''ActiveWorkbook.Save
'''ActiveWorkbook.Close SaveChanges:=1

End Sub

Sub PROCESO_CART_BKN()

Dim appaccess As Object
Dim FECHA As Date

Call ModoOptimizado(True)

Set appaccess = CreateObject("Access.Application")
appaccess.OpenCurrentDatabase "Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones\RF_Gener_Modelo_Inversiones.accdb", False

appaccess.Visible = True

 appaccess.DoCmd.RunMacro "Modelo_Inversiones_Completo"
'appaccess.DoCmd.RunMacro "Modelo_Inversiones_Completo_S/BBC"

appaccess.CloseCurrentDatabase
appaccess.Application.Quit

Call ModoOptimizado(False)
End Sub

Sub ACTUALIZA()
'
' ACTUALIZA Macro
Dim FECHA As Date

RUTA = "Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones"
Archivo = "Modelo de Inversiones"
EXT = ".xlsx"

Workbooks.Open Filename:=RUTA & "\" & Archivo & EXT

Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Range("A1").Select
Selection.ListObject.QueryTable.Refresh BackgroundQuery:=False

Sheets("MODELO_INVERSIONES").Select
Range("A1").Select
Selection.ListObject.QueryTable.Refresh BackgroundQuery:=False
FECHA = Range("A2").Value
'#######################################################################################################
'#######################   ACÁ INTRODUCIR MACRO DE MODIFICACIÓN LCHR    ################################
ini = Now
Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Range("H2").Select
While ActiveCell.Offset() <> ""
  
    If Right(ActiveCell.Value, 4) = "LCHR" Or Right(ActiveCell.Value, 3) = "Gob" Or Right(ActiveCell.Value, 3) = "BBC" Then
        ActiveCell.Value = "ML_C46_Inversiones_Financieras"
        ActiveCell.Offset(0, 14).Value = "INVERSIONES TASAS"
        ActiveCell.Offset(0, 16).Value = "INVERSIONES TASAS"
        ActiveCell.Offset(0, 17).Value = "HTM"
    End If
     ActiveCell.Offset(1, 0).Select
Wend
fin = Now
MsgBox (Format(fin - ini, "hh:mm:ss"))
'#######################################################################################################
'    Range("Tabla_RF_Gener_Modelo_Inversiones.accdb[[#Headers],[Fec_Pro]]").Select
'    Selection.ListObject.QueryTable.Refresh BackgroundQuery:=False


Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Call CarteraAdicional
Sheets("MODELO_INVERSIONES").Select
Workbooks.Add
REPORT = ActiveWorkbook.Name
Workbooks(Archivo & EXT).Activate

    Range("Tabla_RF_Gener_Modelo_Inversiones.accdb[#Headers]").Select
    Range(Selection, Selection.End(xlDown)).Select
    Selection.Copy
    Workbooks(REPORT).Activate
    Range("A1").Select
'    ActiveSheet.Paste
'    Application.CutCopyMode = False
'    Sheets.Add After:=ActiveSheet
'    Windows("Modelo de Inversiones.xlsm").Activate
'    Selection.Copy
''    Windows("Libro13").Activate
    Selection.PasteSpecial Paste:=xlPasteValues, Operation:=xlNone, SkipBlanks _
        :=False, Transpose:=False
    Application.CutCopyMode = False
    Range("A1:N1").Select
    Selection.Font.Bold = True
    With Selection.Interior
        .Pattern = xlSolid
        .PatternColorIndex = xlAutomatic
        .ThemeColor = xlThemeColorDark2
        .TintAndShade = -0.249977111117893
        .PatternTintAndShade = 0
    End With

    Columns("I:N").Select
    Selection.Style = "Comma"
    Selection.NumberFormat = "_(* #,##0.0_);_(* (#,##0.0);_(* ""-""??_);_(@_)"
    Selection.NumberFormat = "_(* #,##0_);_(* (#,##0);_(* ""-""??_);_(@_)"
    Range("A:A,G:G").Select
    Selection.NumberFormat = "m/d/yyyy"
    Range("A1").Select
    
    
i = 1
MONTO = 0
While ActiveCell.Offset(i, 13).Value <> ""
MONTO = MONTO + (ActiveCell.Offset(i, 10).Value + ActiveCell.Offset(i, 11).Value) * ActiveCell.Offset(i, 12).Value
i = i + 1
Wend


End Sub

Sub CarteraAdicional()
'
' Macro1 Macro CarteraAdicional
'
Dim PROCESO As Date
Dim DIAPROCESO As String

'
Sheets("CartAdcnl").Select
Range("A3:BZ10000").Select
Selection.ClearContents

Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Range("a2").Select
Selection.End(xlDown).Select
FILA = ActiveCell.Row
Sheets("CartAdcnl").Select
Range("A2:BZ2").Select
Selection.Copy
ActiveCell.Offset(FILA - 2, 0).Select
Range(Selection, Selection.End(xlUp)).Select
ActiveSheet.Paste
Calculate
    
Sheets("CartAdcnl").Select
PROCESO = Range("A2").Value


DIA = Day(PROCESO)
MES = Month(PROCESO)
AÑO = Year(PROCESO)
  
  'Carteras de RealAis 31-10-17
    If DIA < 10 Then
        DIA = "0" & DIA
    End If
    If MES < 10 Then
        MES = "0" & MES
    End If
    
DIA_PROCESO = AÑO & MES & DIA

    Sheets("CartAdcnl").Copy
    Cells.Select
    Selection.Copy
    Selection.PasteSpecial Paste:=xlPasteValues, Operation:=xlNone, SkipBlanks _
        :=False, Transpose:=False
    Application.CutCopyMode = False
    'ChDir _
     '   "\\172.20.1.117\Riesgo Financiero2\RF_PROCESOS\RF_Modelos\RF_Modelo_Saldos_sin_Vencimiento\Cartera_Adicional"
 
rutaArchivo = "Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones\Cartera_Adicional\" & DIA_PROCESO & "_Modelo_Inversiones_CarteraAdicional.CSV"
ActiveWorkbook.SaveAS Filename:=rutaArchivo, FileFormat:=xlCSV, CreateBackup:=False, local:=True
 
' ActiveWorkbook.SaveAs Filename:="\\172.20.1.117\Riesgo Financiero2\RF_PROCESOS\RF_Modelos\RF_Modelo_Saldos_sin_Vencimiento\Cartera_Adicional\CarteraAdicional.xlsx"
'ActiveWorkbook.SaveAs Filename:="\\172.20.1.117\Riesgo Financiero2\RF_PROCESOS\RF_Modelos\RF_Modelo_Saldos_sin_Vencimiento\Cartera_Adicional\" & DIAPROCESO & "_CarteraAdicional.CSV"
 'ActiveWorkbook.Close
 ActiveWorkbook.Close SaveChanges = True
 Sheets("INTERFAZ_MODELO_INVERSIONES").Select
 End Sub

Sub DIAPROCESO()

Dim fase As Integer
Dim restric As Date
restric = "18:00:00"
fase = 1


'###########################################
'###########################################

If Now - Date > restric Then
    fase = 0
End If


THISDAY = Date - fase


'###########################################
'###########################################

DIASEM = Weekday(THISDAY)

If Weekday(THISDAY) = 7 Then
    THISDAY = THISDAY - 1
End If
If Weekday(THISDAY) = 1 Then
    THISDAY = THISDAY - 2
End If

''######################################################
''########## PROVISORIO POR FIESTAS PATRIAS ############
'
'If Weekday(THISDAY) = 4 Then
'    THISDAY = THISDAY - 5
'End If
'
''########## PROVISORIO POR FIESTAS PATRIAS ############
''######################################################


DIA = Day(THISDAY)
MES = Month(THISDAY)
AÑO = Year(THISDAY)


MES_TEX = MonthName(MES, False)
MAYUS_MES = UCase(MES_TEX)
MINUS_MES = LCase(MES_TEX)
NOMP_MES = UCase(Left(MES_TEX, 1)) & LCase(Mid(MES_TEX, 2, Len(MES_TEX) - 1))
  
  'Carteras de RealAis 31-10-17
    If DIA < 10 Then
        DIA = "0" & DIA
    End If
    If MES < 10 Then
        MES = "0" & MES
    End If
'AÑO = Mid(AÑO, 3, 2)
FECHIX = AÑO & MES & DIA


End Sub



Sub CORREO_MODELO()
'***Macro Para enviar correos
'Por.Dam
Dim MOTOMM As String

    MONTOMM = FormatNumber(MONTO, 2)
    'MsgBox (MONTOMM)
    Set dam1 = CreateObject("outlook.application")
    Set Dam2 = dam1.CreateItem(olMailItem)
    Dam2.To = "aparrar@bancofalabella.cl;jromanm@bancofalabella.cl" '"Riesgo Financiero" 'Range("B2") 'Destinatarios
    Dam2.CC = "lgiordanoc@bancofalabella.cl"
    Dam2.Subject = "Modelo Inversiones al " & THISDAY & " con un monto total de $" & MONTOMM
    Dam2.Body = "Modelo Inversiones al " & THISDAY & " con un monto total de $" & MONTOMM
'    Dam2.Display  'El correo se muestra
'        SendKeys "^{END}"
'        SendKeys "^v"
'    DoEvents
'    Dam2.Display
    Dam2.send
    
End Sub

Sub hola()
'vbCr SE DEBE AGREGAR REF: SCRIPTINGRUNTIME
MONTOMM = FormatNumber(MONTO, 0)
MONTO_CONTM = FormatNumber(MONTO_CONT, 0)
DIFERMM = FormatNumber(MONTO - MONTO_CONT, 0)
'MsgBox ("PRUEBA")
  
  CreateObject("wscript.shell").PopUp "Modelo e inversiones:   " & MONTOMM & vbCr & "Cuadratura Contable:    " & MONTO_CONTM & vbCr & "Monto diferencia total:  " & DIFERMM, 6, "Modelo Inversiones ", 64
 


End Sub
