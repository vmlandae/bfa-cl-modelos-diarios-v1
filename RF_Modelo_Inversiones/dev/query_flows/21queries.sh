#!/bin/bash
# Análisis de dependencias para las 21 queries del Modelo Inversiones
# Ejecutar desde la raíz del proyecto: c:\Users\vlandaetat\code\PROCESOS_DIARIOS_MODELOS

CSV_INPUT="data/external/ml_inversiones/RF_Gener_Modelo_Inversiones_20251121_local/RF_Gener_Modelo_inversiones_20251121_local_queries.csv"
SCRIPT="MODELOS/ML_INVERSIONES/dev/notebooks/query_flow_mapper.py"
OUTPUT_DIR="data/interim/ml_inversiones/query_flows"

# Crear directorio de salida
mkdir -p "$OUTPUT_DIR"

# Lista de las 21 queries
QUERIES=(
    "RF_PLI_000_Gener_CarteraInv"
    "RF_PLI_004_GenerCartGobCLP_Pond"
    "RF_PLI_008_LimpiaFlujGobCLP"
    "RF_PLI_011_GenerCartGobCLF_Pond"
    "RF_PLI_015_LimpiaFlujGobCLP"
    "RF_PLI_018_GenerCartDPF_Pond"
    "RF_PLI_022_LimpiaFlujDPF"
    "RF_PLI_025_GenerCartDPR_Pond"
    "RF_PLI_029_LimpiaFlujDPR"
    "RF_PLI_032_GenerCartLCH_Pond"
    "RF_PLI_036_LimpiaFlujLCH"
    "RF_PLI_039_GenerCartBBC_Pond"
    "RF_PLI_043_LimpiaFlujBBC"
    "RF_PLI_045_Gener_Precios_Dia"
    "RF_PLI_044e_Modelo_Inversiones_Tabla_Final"
    "RF_PLI_047_Limpia_Tabla_Desarrollo_Interna"
    "RF_PLI_048_Tabla_Desarrollo_Interna_Add_ML"
    "RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM"
    "RF_PLI_048b_Tabla_Desarrollo_Interna_Add_HTM"
    "RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT"
    "RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel"
)

echo "========================================"
echo "Análisis de Dependencias - 21 Queries"
echo "========================================"
echo ""

for QUERY in "${QUERIES[@]}"; do
    echo "[INFO] Procesando: $QUERY"
    python "$SCRIPT" "$CSV_INPUT" \
        --entry "$QUERY" \
        --out "$OUTPUT_DIR/${QUERY}_flow.md" \
        --out-csv "$OUTPUT_DIR/${QUERY}_flow.csv"
    echo ""
done

echo "========================================"
echo "Análisis completado!"
echo "Resultados en: $OUTPUT_DIR"
echo "========================================"

