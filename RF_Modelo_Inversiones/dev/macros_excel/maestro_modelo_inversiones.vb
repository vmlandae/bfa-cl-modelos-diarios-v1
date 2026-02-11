Public FLUJO_CLP_AMORT_INT As Double
Public MONTO_CONT As Double
Public VP_AMORT_INT As Double

Public Sub OptimizedMode(ByVal enable As Boolean)
     Application.EnableEvents = Not enable
     Application.Calculation = IIf(enable, xlCalculationManual, xlCalculationAutomatic)
     Application.ScreenUpdating = Not enable
     Application.EnableAnimations = Not enable
     Application.DisplayStatusBar = Not enable
     Application.PrintCommunication = Not enable
End Sub
Sub ActualizaModeloInversiones()

Call OptimizedMode(True)

Workbooks("Maestro Modelo de Inversiones.xlsm").Activate

Call ActualizaDinamicas
Call CarteraAdicional
Call CopiarTablaDesarrollo
Call RepasaCodigoSubProducto

Calculate

Call SumarFlujoCLP
Call SumarMontoContable
ActiveWorkbook.Save
Call MensajeDiferenciaModeloContraBalance

With ActiveWorkbook
        .SaveAs Filename:="Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones\Modelo de Inversiones.xlsx", FileFormat:=51
End With




Call OptimizedMode(False)
End Sub

Sub ActualizaDinamicas()

Sheets("MODELO_INVERSIONES").Select
Range("A1").Select
Selection.ListObject.QueryTable.Refresh BackgroundQuery:=False

Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Range("A1").Select
Selection.ListObject.QueryTable.Refresh BackgroundQuery:=False

End Sub

Sub RepasaCodigoSubProducto()


Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Range("I2").Select

While ActiveCell.Offset() <> ""

    If Right(ActiveCell.Value, 4) = "LCHR" Or Right(ActiveCell.Value, 3) = "Gob" Or Right(ActiveCell.Value, 3) = "BBC" Or Right(ActiveCell.Value, 6) = "GOBCLP" Or Right(ActiveCell.Value, 6) = "GOBCLF" Or Right(ActiveCell.Value, 6) = "DPFCLP" Or Right(ActiveCell.Value, 6) = "DPRCLF" Or Right(ActiveCell.Value, 7) = "CORPCLP" Or Right(ActiveCell.Value, 7) = "CORPCLF" Then
        ActiveCell.Value = "ML_C46_Inversiones_Financieras"
        ActiveCell.Offset(0, -1).Value = "ML_C46_Inversiones_Financieras"
        
    End If
     ActiveCell.Offset(1, 0).Select
Wend


End Sub

Sub SumarFlujoCLP()

Sheets("MODELO_INVERSIONES").Select
Range("N2").Select

FLUJO_CLP_AMORT_INT = 0

While ActiveCell.Offset() <> ""
FLUJO_CLP_AMORT_INT = FLUJO_CLP_AMORT_INT + ActiveCell.Value
ActiveCell.Offset(1, 0).Select
Wend

End Sub

Sub SumarMontoContable()

Workbooks.Add
MONTO_CONTABLE = ActiveWorkbook.Name
Range("a1").Select

    Range("a1").Select
    ActiveCell.FormulaR1C1 = "Inversion Financiera Privado"
    Range("a2").Select
    ActiveCell.FormulaR1C1 = "Inversion Financiera Publico"
    Range("a3").Select
    ActiveCell.FormulaR1C1 = "INVERSIONES FINANCIERAS FONDOS MUTUOS"
     Range("B1").Select
    ActiveCell.FormulaR1C1 = _
        "=VLOOKUP(RC[-1],'Z:\RF_PROCESOS\RF_Balance\[RF_Generador_Balance_Carteras.xlsm]Cuadratura'!C3:C4,2,0)"
    Range("B2").Select
    ActiveCell.FormulaR1C1 = _
        "=VLOOKUP(RC[-1],'Z:\RF_PROCESOS\RF_Balance\[RF_Generador_Balance_Carteras.xlsm]Cuadratura'!C3:C4,2,0)"
    Range("B3").Select
    ActiveCell.FormulaR1C1 = _
        "=VLOOKUP(RC[-1],'Z:\RF_PROCESOS\RF_Balance\[RF_Generador_Balance_Carteras.xlsm]Cuadratura'!C3:C4,2,0)"
    Range("B4").Select
    ActiveCell.FormulaR1C1 = "=SUM(R[-3]C:R[-1]C)"
    
    MONTO_CONT = ActiveCell.Value
Workbooks(MONTO_CONTABLE).Close SaveChanges:=False

End Sub

Sub MensajeDiferenciaModeloContraBalance()
'vbCr SE DEBE AGREGAR REF: SCRIPTINGRUNTIME
MONTOMM = FormatNumber(FLUJO_CLP_AMORT_INT, 0)
MONTO_CONTM = FormatNumber(MONTO_CONT, 0)
DIFERMM = FormatNumber(FLUJO_CLP_AMORT_INT - MONTO_CONT, 0)
'MsgBox ("PRUEBA")
  
  CreateObject("wscript.shell").PopUp "Modelo e inversiones:   " & MONTOMM & vbCr & "Cuadratura Contable:    " & MONTO_CONTM & vbCr & "Monto diferencia total:  " & DIFERMM, 6, "Modelo Inversiones ", 64
 


End Sub
Sub CopiarTablaDesarrollo()
Sheets("ML_ACCESS").Select
Range(Range("A2").End(xlDown), Range("AE2")).Select
Selection.Interior.Color = xlNone
Selection.ClearContents
        '######################
    
    'SELECCION DE DATOS PARA COPIAR
Sheets("INTERFAZ_MODELO_INVERSIONES").Select
Range(Range("A2").End(xlDown), Range("AE2")).Select
Selection.Copy
    '######################
    
'PEGADO TABLA
Sheets("ML_ACCESS").Select
Range("A2:AE2").Select
Selection.PasteSpecial Paste:=xlPasteValues, Operation:=xlNone, SkipBlanks _
    :=False, Transpose:=False
Selection.PasteSpecial xlPasteFormats
Selection.Interior.Color = xlNone
Application.CutCopyMode = False
'######################
End Sub

'############### MODULO 2

Public LR As Variant
Sub CarteraAdicional()
'
' Macro1 Macro
'


Dim PROCESO As Date
Dim DIAPROCESO As String


Dim arr1, arr2, arr3, arr4, arr5, arr6, arr7, arr8, arr9, arr10
Dim arr11, arr12, arr13, arr14, arr15, arr16, arr17, arr18, arr19, arr20
Dim arr21, arr22, arr23, arr24, arr25

Dim Rng1, Rng2, Rng3, Rng4, Rng5, Rng6, Rng7, Rng8, Rng9, Rng10 As Range
Dim Rng11, Rng12, Rng13, Rng14, Rng15, Rng16, Rng17, Rng18, Rng19, Rng20 As Range
Dim Rng21, Rng22, Rng23, Rng24, Rng25 As Range

Dim Ini_cpy, Fn_cpy As String



'Limpieza de tabla t-1
Sheets("CartAdcnl").Select
Range(Range("A2").End(xlDown), Range("BB2")).Select
Selection.ClearContents

Sheets("INTERFAZ_MODELO_INVERSIONES").Select

Call NumeroDeFilas
    
Nrows = LR

Ini_cpy = "2"
Fn_cpy = CStr(Nrows)

    With ActiveSheet
        Set Rng1 = ActiveSheet.Range("A" + Ini_cpy, "A" + Fn_cpy)  'Fecha Proceso
        Set Rng2 = ActiveSheet.Range("B" + Ini_cpy, "B" + Fn_cpy)  'CODIGO_EMPRESA
        
        Set Rng3 = ActiveSheet.Range("E" + Ini_cpy, "E" + Fn_cpy)  'MONEDA_ORIGEN
        Set Rng4 = ActiveSheet.Range("D" + Ini_cpy, "D" + Fn_cpy)  'COD ACT/PAS
        Set Rng5 = ActiveSheet.Range("H" + Ini_cpy, "H" + Fn_cpy)  'CODIGO_PRODUCTO
        Set Rng6 = ActiveSheet.Range("I" + Ini_cpy, "I" + Fn_cpy)  'CODIGO_SUB_PRODUCTO
        
        Set Rng7 = ActiveSheet.Range("B" + Ini_cpy, "B" + Fn_cpy)  'OPERACION
        Set Rng8 = ActiveSheet.Range("K" + Ini_cpy, "K" + Fn_cpy)  'NUMERO_CUOTA
        Set Rng9 = ActiveSheet.Range("AD" + Ini_cpy, "AD" + Fn_cpy)  'NUMERO_CUOTA
        Set Rng10 = ActiveSheet.Range("G" + Ini_cpy, "G" + Fn_cpy)  'COMPENSACION
        Set Rng11 = ActiveSheet.Range("J" + Ini_cpy, "J" + Fn_cpy)  'FECHA CREACION
        Set Rng12 = ActiveSheet.Range("L" + Ini_cpy, "L" + Fn_cpy)  'FECHA_INICIO_CUOTA
        Set Rng13 = ActiveSheet.Range("M" + Ini_cpy, "M" + Fn_cpy)  'FECHA_VENCIMIENTO_CUOTA
        Set Rng14 = ActiveSheet.Range("O" + Ini_cpy, "O" + Fn_cpy)  'FECHA_REPRICING
        Set Rng15 = ActiveSheet.Range("N" + Ini_cpy, "N" + Fn_cpy)  'FECHA PAGO
        Set Rng16 = ActiveSheet.Range("P" + Ini_cpy, "P" + Fn_cpy)  'AMORTIZACION
        Set Rng17 = ActiveSheet.Range("Q" + Ini_cpy, "Q" + Fn_cpy)  'INTERES
        Set Rng18 = ActiveSheet.Range("R" + Ini_cpy, "R" + Fn_cpy)  'INTERES_DEVENGADO
        Set Rng19 = ActiveSheet.Range("S" + Ini_cpy, "S" + Fn_cpy)  'VP_AMORTIZACION
        Set Rng20 = ActiveSheet.Range("T" + Ini_cpy, "T" + Fn_cpy)  'VP_INTERES
        Set Rng21 = ActiveSheet.Range("F" + Ini_cpy, "F" + Fn_cpy)  'MONEDA_COMPENSACION
        Set Rng22 = ActiveSheet.Range("V" + Ini_cpy, "V" + Fn_cpy)  'TIPO_CUOTA
        Set Rng23 = ActiveSheet.Range("W" + Ini_cpy, "W" + Fn_cpy)  'AREA NEGOCIO
        Set Rng24 = ActiveSheet.Range("Y" + Ini_cpy, "Y" + Fn_cpy)  'AREA NEGOCIO
        Set Rng25 = ActiveSheet.Range("Z" + Ini_cpy, "Z" + Fn_cpy)  'CLASIFICACION_CONTABLE
        
        arr1 = Rng1.Value
        arr2 = Rng2.Value
        arr3 = Rng3.Value
        arr4 = Rng4.Value
        arr5 = Rng5.Value
        arr6 = Rng6.Value
        arr7 = Rng7.Value
        arr8 = Rng8.Value
        arr9 = Rng9.Value
        arr10 = Rng10.Value
        
        arr11 = Rng11.Value
        arr12 = Rng12.Value
        arr13 = Rng13.Value
        arr14 = Rng14.Value
        arr15 = Rng15.Value
        arr16 = Rng16.Value
        arr17 = Rng17.Value
        arr18 = Rng18.Value
        arr19 = Rng19.Value
        arr10 = Rng10.Value
        arr20 = Rng20.Value
        
        arr21 = Rng21.Value
        arr22 = Rng22.Value
        arr23 = Rng23.Value
        arr24 = Rng24.Value
        arr25 = Rng25.Value
        
        Worksheets("CartAdcnl").Range("A" + "2").Resize(UBound(arr1, 1), 1).Value = arr1 'Fec_Pro
        
        Worksheets("CartAdcnl").Range("B" + "2").Resize(UBound(arr2, 1), 1).Value = arr2 'Cod_Emp
        Worksheets("CartAdcnl").Range("C" + "2").Resize(UBound(arr3, 1), 1).Value = arr3 'Moneda
        Worksheets("CartAdcnl").Range("D" + "2").Resize(UBound(arr4, 1), 1).Value = arr4 'Cod_A_P
        
        Worksheets("CartAdcnl").Range("E" + "2").Resize(UBound(arr25, 1), 1).Value = "CARTERA ADICIONAL" 'Fuente
        Worksheets("CartAdcnl").Range("F" + "2").Resize(UBound(arr25, 1), 1).Value = "RF" 'Sistema
        
        Worksheets("CartAdcnl").Range("G" + "2").Resize(UBound(arr5, 1), 1).Value = arr5 'Cod_Pro
        Worksheets("CartAdcnl").Range("H" + "2").Resize(UBound(arr6, 1), 1).Value = arr6 'Cod_Sub_Pro
        Worksheets("CartAdcnl").Range("I" + "2").Resize(UBound(arr7, 1), 1).Value = "" 'Num_Oper
        Worksheets("CartAdcnl").Range("J" + "2").Resize(UBound(arr8, 1), 1).Value = "" 'Num_Cup
        
        Worksheets("CartAdcnl").Range("K" + "2").Resize(UBound(arr25, 1), 1).Value = "" 'Correlativo
        Worksheets("CartAdcnl").Range("N" + "2").Resize(UBound(arr25, 1), 1).Value = "" 'Tasa_Emi
        
        Worksheets("CartAdcnl").Range("O" + "2").Resize(UBound(arr9, 1), 1).Value = arr9 'Tasa_Cont
        Worksheets("CartAdcnl").Range("Q" + "2").Resize(UBound(arr10, 1), 1).Value = arr10 'Compensacion
        Worksheets("CartAdcnl").Range("R" + "2").Resize(UBound(arr11, 1), 1).Value = arr11 'Fec_Cre
        Worksheets("CartAdcnl").Range("S" + "2").Resize(UBound(arr12, 1), 1).Value = arr12 'Fec_Ini_Cup
        Worksheets("CartAdcnl").Range("T" + "2").Resize(UBound(arr13, 1), 1).Value = arr13 'Fec_Vcto_Cup
        Worksheets("CartAdcnl").Range("U" + "2").Resize(UBound(arr14, 1), 1).Value = arr14 'Fec_Rep
        Worksheets("CartAdcnl").Range("V" + "2").Resize(UBound(arr13, 1), 1).Value = arr13 'Fec_Vcto
        Worksheets("CartAdcnl").Range("W" + "2").Resize(UBound(arr15, 1), 1).Value = arr15 'Fec_Pago
        
        Worksheets("CartAdcnl").Range("X" + "2").Resize(UBound(arr25, 1), 1).Value = "" 'Dias_Liq
        Worksheets("CartAdcnl").Range("Y" + "2").Resize(UBound(arr25, 1), 1).Value = "" 'Dias_Vcto
        Worksheets("CartAdcnl").Range("Z" + "2").Resize(UBound(arr25, 1), 1).Value = "" 'Dias_Pago
        
        Worksheets("CartAdcnl").Range("AA" + "2").Resize(UBound(arr16, 1), 1).Value = arr16 'Cap_Amort
        Worksheets("CartAdcnl").Range("AB" + "2").Resize(UBound(arr17, 1), 1).Value = arr17 'Int_Total_Cont
        Worksheets("CartAdcnl").Range("AC" + "2").Resize(UBound(arr18, 1), 1).Value = arr18 'Int_Devengado
        Worksheets("CartAdcnl").Range("AD" + "2").Resize(UBound(arr19, 1), 1).Value = arr19 'VP_Cap_Amort
        Worksheets("CartAdcnl").Range("AE" + "2").Resize(UBound(arr20, 1), 1).Value = arr20 'VP_Int_Total
        
        Worksheets("CartAdcnl").Range("AF" + "2").Resize(UBound(arr25, 1), 1).Value = "0" 'Flujo_Liq
        
        Worksheets("CartAdcnl").Range("AG" + "2").Resize(UBound(arr21, 1), 1).Value = arr21 'Moneda_Liq
        Worksheets("CartAdcnl").Range("AH" + "2").Resize(UBound(arr22, 1), 1).Value = arr22 'Tipo_Cupon
        Worksheets("CartAdcnl").Range("AI" + "2").Resize(UBound(arr23, 1), 1).Value = arr23 'Cod_Area_Neg
        Worksheets("CartAdcnl").Range("AJ" + "2").Resize(UBound(arr24, 1), 1).Value = arr24 'Cod_Estrategia
        Worksheets("CartAdcnl").Range("AK" + "2").Resize(UBound(arr24, 1), 1).Value = arr24 'Tipo_Book
        Worksheets("CartAdcnl").Range("AL" + "2").Resize(UBound(arr25, 1), 1).Value = arr25 'Clasificacion_Contable
        
        Worksheets("CartAdcnl").Range("AN" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AO" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AP" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AQ" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AR" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AS" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AT" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AU" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AV" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AW" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AX" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AY" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("AZ" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("BA" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        Worksheets("CartAdcnl").Range("BB" + "2").Resize(UBound(arr25, 1), 1).Value = "0"
        
        


        
        
    End With
    
Sheets("CartAdcnl").Select
PROCESO = Range("A3").Value

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
    
DIAPROCESO = AÑO & MES & DIA

    Sheets("CartAdcnl").Copy
    Cells.Select
    Selection.Copy
    Selection.PasteSpecial Paste:=xlPasteValues, Operation:=xlNone, SkipBlanks _
        :=False, Transpose:=False
    Application.CutCopyMode = False
    'ChDir _
     '   "\\172.20.1.117\Riesgo Financiero2\RF_PROCESOS\RF_Modelos\RF_Modelo_Saldos_sin_Vencimiento\Cartera_Adicional"
 
rutaArchivo = "Z:\RF_PROCESOS\RF_Modelos\CARTERA_ADICIONAL\" & DIAPROCESO & "_Modelo_Inversiones.CSV"
ActiveWorkbook.SaveAs Filename:=rutaArchivo, FileFormat:=xlCSV, CreateBackup:=False, local:=True
 
ActiveWorkbook.Close SaveChanges = True
        
 End Sub
Sub NumeroDeFilas()
ThisWorkbook.Sheets("INTERFAZ_MODELO_INVERSIONES").Activate
LR = Cells(Rows.Count, 1).End(xlUp).Row
LR = LR
End Sub


