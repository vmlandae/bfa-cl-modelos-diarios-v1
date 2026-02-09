#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolidar_analisis.py

Consolida los 21 CSVs de flujo de queries y genera análisis de patrones
para identificar oportunidades de parametrización y reducción de queries.

Uso:
    python consolidar_analisis.py
"""

import csv
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple


# Configuración
CSV_DELIMITER = ';'
ENCODING = 'utf-8-sig'

# Directorio de trabajo
SCRIPT_DIR = Path(__file__).parent
OUTPUT_CSV = SCRIPT_DIR / "queries_consolidado_21_entrypoints.csv"
OUTPUT_MD = SCRIPT_DIR / "ANALISIS_PATRONES_QUERIES.md"

# Lista de las 21 queries entrypoint
ENTRYPOINTS = [
    "RF_PLI_000_Gener_CarteraInv",
    "RF_PLI_004_GenerCartGobCLP_Pond",
    "RF_PLI_008_LimpiaFlujGobCLP",
    "RF_PLI_011_GenerCartGobCLF_Pond",
    "RF_PLI_015_LimpiaFlujGobCLP",
    "RF_PLI_018_GenerCartDPF_Pond",
    "RF_PLI_022_LimpiaFlujDPF",
    "RF_PLI_025_GenerCartDPR_Pond",
    "RF_PLI_029_LimpiaFlujDPR",
    "RF_PLI_032_GenerCartLCH_Pond",
    "RF_PLI_036_LimpiaFlujLCH",
    "RF_PLI_039_GenerCartBBC_Pond",
    "RF_PLI_043_LimpiaFlujBBC",
    "RF_PLI_045_Gener_Precios_Dia",
    "RF_PLI_044e_Modelo_Inversiones_Tabla_Final",
    "RF_PLI_047_Limpia_Tabla_Desarrollo_Interna",
    "RF_PLI_048_Tabla_Desarrollo_Interna_Add_ML",
    "RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM",
    "RF_PLI_048b_Tabla_Desarrollo_Interna_Add_HTM",
    "RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT",
    "RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel"
]


def leer_csv_flow(ruta: Path) -> List[Dict]:
    """Lee un CSV de flujo y retorna lista de registros."""
    registros = []
    try:
        with open(ruta, 'r', encoding=ENCODING, newline='') as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            for row in reader:
                registros.append(row)
    except Exception as e:
        print(f"  [ERROR] No se pudo leer {ruta.name}: {e}")
    return registros


def consolidar_csvs() -> Tuple[List[Dict], Set[str]]:
    """
    Consolida todos los CSVs de flujo en una lista única.
    Elimina duplicados basándose en el nombre de la query.
    
    Returns:
        (lista_consolidada, set_queries_unicas)
    """
    queries_vistas = {}  # query_name -> registro
    entrypoints_por_query = defaultdict(set)  # query -> set de entrypoints que la usan
    
    for entrypoint in ENTRYPOINTS:
        archivo_csv = SCRIPT_DIR / f"{entrypoint}_flow.csv"
        
        if not archivo_csv.exists():
            print(f"  [WARN] No existe: {archivo_csv.name}")
            continue
        
        registros = leer_csv_flow(archivo_csv)
        
        for reg in registros:
            query_name = reg.get('query', '')
            if not query_name:
                continue
            
            # Rastrear qué entrypoints usan esta query
            entrypoints_por_query[query_name].add(entrypoint)
            
            # Guardar registro si no existe
            if query_name not in queries_vistas:
                queries_vistas[query_name] = reg
    
    # Agregar columna de entrypoints que usan cada query
    for query_name, reg in queries_vistas.items():
        eps = entrypoints_por_query[query_name]
        reg['entrypoints_que_usan'] = ', '.join(sorted(eps))
        reg['num_entrypoints'] = len(eps)
    
    return list(queries_vistas.values()), set(queries_vistas.keys())


def escribir_csv_consolidado(registros: List[Dict]):
    """Escribe el CSV consolidado sin la columna SQL."""
    columnas = [
        'query', 'tipo', 'es_entrypoint', 'nivel_profundidad',
        'queries_padre', 'dependencias_directas', 'num_dependencias',
        'num_entrypoints', 'entrypoints_que_usan', 'hash_sha1'
    ]
    
    with open(OUTPUT_CSV, 'w', encoding=ENCODING, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columnas, delimiter=CSV_DELIMITER, extrasaction='ignore')
        writer.writeheader()
        
        # Ordenar por número de query (extraer número del nombre)
        def extraer_numero(reg):
            match = re.search(r'RF_PLI_(\d+)', reg.get('query', ''))
            return int(match.group(1)) if match else 999
        
        for reg in sorted(registros, key=extraer_numero):
            writer.writerow(reg)
    
    print(f"  [OK] CSV consolidado: {OUTPUT_CSV.name}")


def analizar_patrones(registros: List[Dict]) -> Dict:
    """
    Analiza patrones en las queries para identificar oportunidades
    de parametrización y reducción.
    """
    analisis = {
        'total_queries': len(registros),
        'por_tipo': Counter(),
        'por_nivel': Counter(),
        'queries_compartidas': [],  # usadas por múltiples entrypoints
        'familias': defaultdict(list),  # agrupaciones por patrón de nombre
        'patrones_similares': [],
    }
    
    # Contadores básicos
    for reg in registros:
        analisis['por_tipo'][reg.get('tipo', 'Unknown')] += 1
        try:
            nivel = int(reg.get('nivel_profundidad', 0))
            analisis['por_nivel'][nivel] += 1
        except:
            pass
        
        # Queries compartidas
        num_eps = int(reg.get('num_entrypoints', 1))
        if num_eps > 1:
            analisis['queries_compartidas'].append({
                'query': reg.get('query'),
                'num_entrypoints': num_eps,
                'entrypoints': reg.get('entrypoints_que_usan', '')
            })
    
    # Detectar familias por patrón de nombre
    # Ej: RF_PLI_002_CarteraGobCLP, RF_PLI_009_CarteraGobCLF -> Familia "Cartera"
    patrones_familia = [
        (r'RF_PLI_\d+_Cartera(GobCLP|GobCLF|DPF|DPR|LCH|BBC)', 'Cartera_Instrumentos'),
        (r'RF_PLI_\d+b_Cartera.*_Final', 'Cartera_Final'),
        (r'RF_PLI_\d+c_Monto_FueraPlazo', 'Monto_FueraPlazo'),
        (r'RF_PLI_\d+b_.*_MontoPlazo_Pacto', 'MontoPlazo_Pacto'),
        (r'RF_PLI_\d+_Cartera.*_Pacto', 'Cartera_Pacto'),
        (r'RF_PLI_\d+_GenerCart.*_Pond', 'GenerarCartera_Ponderada'),
        (r'RF_PLI_\d+_LimpiaFluj', 'Limpiar_Flujo'),
        (r'RF_PLI_048.*_Tabla_Desarrollo_Interna_Add', 'Agregar_Tabla_Desarrollo'),
        (r'RF_PLI_044.*_Modelo_Inversiones', 'Modelo_Inversiones_Final'),
    ]
    
    for reg in registros:
        query_name = reg.get('query', '')
        for patron, familia in patrones_familia:
            if re.match(patron, query_name):
                analisis['familias'][familia].append(query_name)
                break
    
    # Ordenar queries compartidas por número de usos
    analisis['queries_compartidas'].sort(key=lambda x: x['num_entrypoints'], reverse=True)
    
    return analisis


def detectar_parametrizables(registros: List[Dict]) -> List[Dict]:
    """
    Detecta grupos de queries que podrían convertirse en funciones parametrizadas.
    """
    grupos = []
    
    # Grupo 1: Queries de Cartera por tipo de instrumento
    # RF_PLI_002_CarteraGobCLP, RF_PLI_009_CarteraGobCLF, RF_PLI_016_CarteraDPF, etc.
    cartera_queries = [r for r in registros if re.match(r'RF_PLI_\d{3}_Cartera(GobCLP|GobCLF|DPF|DPR|LCH|BBC)$', r.get('query', ''))]
    if cartera_queries:
        grupos.append({
            'nombre': 'filtrar_cartera_por_instrumento',
            'descripcion': 'Filtra RF_PLI_001_CarteraInv por tipo de instrumento (BCP, BTU, DPF, etc.)',
            'queries_actuales': [q['query'] for q in cartera_queries],
            'cantidad': len(cartera_queries),
            'parametros_sugeridos': ['tipo_instrumento: str', 'codigos_instrumento: List[str]'],
            'reduccion': f'{len(cartera_queries)} queries -> 1 función'
        })
    
    # Grupo 2: Queries de MonTotal (agregación por moneda/producto)
    montotal_queries = [r for r in registros if 'MonTotal' in r.get('query', '')]
    if montotal_queries:
        grupos.append({
            'nombre': 'calcular_monto_total',
            'descripcion': 'Agrupa y suma VP_Cap_Amort + VP_Int_Total por Fec_Pro, Moneda, Cod_Pro',
            'queries_actuales': [q['query'] for q in montotal_queries],
            'cantidad': len(montotal_queries),
            'parametros_sugeridos': ['tabla_origen: str', 'columnas_grupo: List[str]'],
            'reduccion': f'{len(montotal_queries)} queries -> 1 función'
        })
    
    # Grupo 3: Queries de Ponderador
    pond_queries = [r for r in registros if '_Pond' in r.get('query', '') and 'GenerCart' in r.get('query', '')]
    if pond_queries:
        grupos.append({
            'nombre': 'generar_cartera_ponderada',
            'descripcion': 'Calcula ponderador = (VP_Cap + VP_Int) / VP_Flujo_Total',
            'queries_actuales': [q['query'] for q in pond_queries],
            'cantidad': len(pond_queries),
            'parametros_sugeridos': ['tabla_cartera: str', 'tabla_montotal: str', 'tabla_destino: str'],
            'reduccion': f'{len(pond_queries)} queries -> 1 función'
        })
    
    # Grupo 4: Queries de Limpieza (DELETE)
    limpia_queries = [r for r in registros if 'Limpia' in r.get('query', '') and r.get('tipo') == 'Type32']
    if limpia_queries:
        grupos.append({
            'nombre': 'limpiar_tabla',
            'descripcion': 'DELETE FROM tabla (limpieza antes de repoblar)',
            'queries_actuales': [q['query'] for q in limpia_queries],
            'cantidad': len(limpia_queries),
            'parametros_sugeridos': ['tabla_destino: str'],
            'reduccion': f'{len(limpia_queries)} queries -> 1 función'
        })
    
    # Grupo 5: Queries de Cartera Final (formato estándar de salida)
    final_queries = [r for r in registros if re.match(r'RF_PLI_\d+b_Cartera.*_Final', r.get('query', ''))]
    if final_queries:
        grupos.append({
            'nombre': 'formatear_cartera_final',
            'descripcion': 'Formatea flujo con estructura estándar: Fec_Pro, Cod_Emp, Moneda, Cod_A_P, etc.',
            'queries_actuales': [q['query'] for q in final_queries],
            'cantidad': len(final_queries),
            'parametros_sugeridos': ['tabla_flujo: str', 'moneda: str', 'cod_sub_pro: str'],
            'reduccion': f'{len(final_queries)} queries -> 1 función'
        })
    
    # Grupo 6: Queries de Pacto
    pacto_queries = [r for r in registros if '_Pacto' in r.get('query', '') and 'Cartera' in r.get('query', '')]
    if pacto_queries:
        grupos.append({
            'nombre': 'filtrar_cartera_pacto',
            'descripcion': 'Filtra instrumentos con pacto de retroventa',
            'queries_actuales': [q['query'] for q in pacto_queries],
            'cantidad': len(pacto_queries),
            'parametros_sugeridos': ['tabla_origen: str', 'tipo_instrumento: str'],
            'reduccion': f'{len(pacto_queries)} queries -> 1 función'
        })
    
    # Grupo 7: Queries de MontoPlazo
    montoplazo_queries = [r for r in registros if 'MontoPlazo' in r.get('query', '')]
    if montoplazo_queries:
        grupos.append({
            'nombre': 'calcular_monto_por_plazo',
            'descripcion': 'Agrupa montos por días de pacto',
            'queries_actuales': [q['query'] for q in montoplazo_queries],
            'cantidad': len(montoplazo_queries),
            'parametros_sugeridos': ['tabla_pacto: str'],
            'reduccion': f'{len(montoplazo_queries)} queries -> 1 función'
        })
    
    # Grupo 8: Queries de Monto_FueraPlazo
    fueraplazo_queries = [r for r in registros if 'FueraPlazo' in r.get('query', '')]
    if fueraplazo_queries:
        grupos.append({
            'nombre': 'filtrar_monto_fuera_plazo',
            'descripcion': 'Filtra montos con Dias_Pacto > 90',
            'queries_actuales': [q['query'] for q in fueraplazo_queries],
            'cantidad': len(fueraplazo_queries),
            'parametros_sugeridos': ['tabla_monto_plazo: str', 'dias_limite: int = 90'],
            'reduccion': f'{len(fueraplazo_queries)} queries -> 1 función'
        })
    
    # Grupo 9: Queries Add_* (INSERT INTO tabla_desarrollo)
    add_queries = [r for r in registros if 'Add_' in r.get('query', '') and 'Tabla_Desarrollo' in r.get('query', '')]
    if add_queries:
        grupos.append({
            'nombre': 'agregar_a_tabla_desarrollo',
            'descripcion': 'INSERT INTO RF_Tabla_Desarrollo_Interna desde diferentes fuentes',
            'queries_actuales': [q['query'] for q in add_queries],
            'cantidad': len(add_queries),
            'parametros_sugeridos': ['tabla_origen: str', 'transformaciones: Dict'],
            'reduccion': f'{len(add_queries)} queries -> 1 función'
        })
    
    return grupos


def generar_markdown(registros: List[Dict], analisis: Dict, grupos_parametrizables: List[Dict]):
    """Genera el archivo Markdown con el análisis completo."""
    
    total_queries = analisis['total_queries']
    total_parametrizables = sum(g['cantidad'] for g in grupos_parametrizables)
    
    # Calcular reducción potencial
    queries_en_grupos = set()
    for g in grupos_parametrizables:
        queries_en_grupos.update(g['queries_actuales'])
    
    queries_unicas_restantes = total_queries - len(queries_en_grupos) + len(grupos_parametrizables)
    
    md_lines = [
        "# Análisis de Patrones y Estrategia de Reducción de Queries",
        "",
        f"**Fecha de análisis**: 2026-02-04",
        "",
        "---",
        "",
        "## Resumen Ejecutivo",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| **Total queries únicas** | {total_queries} |",
        f"| **Queries parametrizables** | {len(queries_en_grupos)} |",
        f"| **Funciones Python resultantes** | {len(grupos_parametrizables)} |",
        f"| **Queries no parametrizables** | {total_queries - len(queries_en_grupos)} |",
        f"| **Total final estimado** | ~{queries_unicas_restantes} unidades de código |",
        f"| **Reducción** | **{((total_queries - queries_unicas_restantes) / total_queries * 100):.0f}%** |",
        "",
        "---",
        "",
        "## Distribución por Tipo de Query",
        "",
        "| Tipo | Cantidad | Descripción |",
        "|------|----------|-------------|",
    ]
    
    tipos_descripcion = {
        'Select': 'Query de lectura/transformación',
        'Type128': 'Query UNION (combina múltiples fuentes)',
        'DDL': 'CREATE/SELECT INTO (crea tablas)',
        'Type64': 'INSERT INTO (agrega registros)',
        'Type32': 'DELETE (limpieza de tablas)',
    }
    
    for tipo, cantidad in sorted(analisis['por_tipo'].items(), key=lambda x: -x[1]):
        desc = tipos_descripcion.get(tipo, 'Otro tipo')
        md_lines.append(f"| {tipo} | {cantidad} | {desc} |")
    
    md_lines.extend([
        "",
        "---",
        "",
        "## Distribución por Nivel de Profundidad",
        "",
        "| Nivel | Cantidad | Significado |",
        "|-------|----------|-------------|",
    ])
    
    for nivel in sorted(analisis['por_nivel'].keys()):
        cantidad = analisis['por_nivel'][nivel]
        if nivel == 0:
            significado = "Entrypoints (queries principales)"
        elif nivel == 1:
            significado = "Dependencias directas de entrypoints"
        else:
            significado = f"Dependencias de nivel {nivel-1}"
        md_lines.append(f"| {nivel} | {cantidad} | {significado} |")
    
    md_lines.extend([
        "",
        "---",
        "",
        "## Queries Compartidas (Reutilizadas)",
        "",
        "Queries usadas por múltiples entrypoints (oportunidades de función común):",
        "",
        "| Query | Nº Entrypoints | Entrypoints |",
        "|-------|----------------|-------------|",
    ])
    
    for q in analisis['queries_compartidas'][:15]:  # Top 15
        entrypoints_cortos = ', '.join([e.split('_')[-1][:15] for e in q['entrypoints'].split(', ')[:3]])
        if q['num_entrypoints'] > 3:
            entrypoints_cortos += f" (+{q['num_entrypoints']-3})"
        md_lines.append(f"| `{q['query']}` | {q['num_entrypoints']} | {entrypoints_cortos} |")
    
    md_lines.extend([
        "",
        "---",
        "",
        "## Familias de Queries Detectadas",
        "",
    ])
    
    for familia, queries in sorted(analisis['familias'].items(), key=lambda x: -len(x[1])):
        md_lines.append(f"### {familia} ({len(queries)} queries)")
        md_lines.append("")
        for q in sorted(queries):
            md_lines.append(f"- `{q}`")
        md_lines.append("")
    
    md_lines.extend([
        "---",
        "",
        "## Estrategia de Parametrización",
        "",
        "### Grupos de Queries Parametrizables",
        "",
    ])
    
    for i, grupo in enumerate(grupos_parametrizables, 1):
        md_lines.extend([
            f"### {i}. `{grupo['nombre']}()`",
            "",
            f"**Descripción**: {grupo['descripcion']}",
            "",
            f"**Reducción**: {grupo['reduccion']}",
            "",
            f"**Parámetros sugeridos**:",
            ""
        ])
        for param in grupo['parametros_sugeridos']:
            md_lines.append(f"- `{param}`")
        
        md_lines.extend([
            "",
            f"**Queries actuales que reemplaza** ({grupo['cantidad']}):",
            ""
        ])
        for q in grupo['queries_actuales']:
            md_lines.append(f"- `{q}`")
        md_lines.append("")
    
    md_lines.extend([
        "---",
        "",
        "## Plan de Implementación Propuesto",
        "",
        "### Fase 1: Funciones Base (Semana 1)",
        "",
        "Crear módulo `MODELOS/ML_INVERSIONES/utils/queries_inversiones.py` con:",
        "",
        "```python",
        "# Funciones principales a implementar",
        "",
        "def limpiar_tabla(df_conexion, tabla: str) -> None:",
        '    """Equivalente a DELETE FROM tabla."""',
        "    pass",
        "",
        "def filtrar_cartera_por_instrumento(",
        "    df_cartera: pd.DataFrame,",
        "    codigos_instrumento: List[str]",
        ") -> pd.DataFrame:",
        '    """Filtra cartera por código de instrumento (BCP, BTU, DPF, etc.)."""',
        "    pass",
        "",
        "def calcular_monto_total(",
        "    df: pd.DataFrame,",
        "    columnas_grupo: List[str] = ['Fec_Pro', 'Moneda', 'Cod_Pro']",
        ") -> pd.DataFrame:",
        '    """Agrupa y suma VP_Cap_Amort + VP_Int_Total."""',
        "    pass",
        "",
        "def generar_cartera_ponderada(",
        "    df_cartera: pd.DataFrame,",
        "    df_monto_total: pd.DataFrame",
        ") -> pd.DataFrame:",
        '    """Calcula ponderador = flujo / flujo_total."""',
        "    pass",
        "```",
        "",
        "### Fase 2: Consolidación Flujos (Semana 2)",
        "",
        "- Implementar funciones de formateo final",
        "- Consolidar queries de pacto y fuera de plazo",
        "- Tests unitarios para cada función",
        "",
        "### Fase 3: Integración (Semana 3)",
        "",
        "- Crear pipeline principal `ml_inversiones.py`",
        "- Integrar con orquestador",
        "- Validar outputs vs Access original",
        "",
        "---",
        "",
        "## Arquitectura Propuesta",
        "",
        "```",
        "MODELOS/ML_INVERSIONES/",
        "├── ml_inversiones.py          # Orquestador principal",
        "├── utils/",
        "│   ├── __init__.py",
        "│   ├── queries_inversiones.py  # Funciones parametrizadas",
        "│   ├── transformaciones.py     # Lógica de negocio",
        "│   └── validaciones.py         # Validación de outputs",
        "├── queries/",
        "│   ├── cartera_base.sql        # Query base RF_PLI_001",
        "│   └── modelo_final.sql        # Consolidación final",
        "└── tests/",
        "    └── test_queries.py",
        "```",
        "",
        "---",
        "",
        "## Métricas de Éxito",
        "",
        f"| Métrica | Antes | Después | Mejora |",
        f"|---------|-------|---------|--------|",
        f"| Queries/Funciones | {total_queries} | ~{queries_unicas_restantes} | -{total_queries - queries_unicas_restantes} |",
        f"| Líneas de código SQL | ~{total_queries * 15} | ~{queries_unicas_restantes * 20} | ~{((total_queries * 15) - (queries_unicas_restantes * 20))//100 * 100} |",
        f"| Tiempo mantenimiento | Alto | Bajo | -70% est. |",
        f"| Testabilidad | Nula | Alta | +100% |",
        "",
        "---",
        "",
        "## Notas Adicionales",
        "",
        "1. **Priorizar** las queries compartidas (usadas por múltiples entrypoints)",
        "2. **Validar** cada función contra output original del Access",
        "3. **Documentar** mapeo entre queries Access y funciones Python",
        "4. Considerar **cacheo** de resultados intermedios para optimizar performance",
        "",
    ])
    
    # Escribir archivo
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    print(f"  [OK] Análisis MD: {OUTPUT_MD.name}")


def main():
    """Función principal."""
    print("=" * 60)
    print("CONSOLIDACIÓN Y ANÁLISIS DE QUERIES - ML_INVERSIONES")
    print("=" * 60)
    
    # 1. Consolidar CSVs
    print("\n[1/4] Consolidando 21 CSVs de flujo...")
    registros, queries_unicas = consolidar_csvs()
    print(f"      OK - {len(registros)} queries únicas encontradas")
    
    # 2. Escribir CSV consolidado
    print("\n[2/4] Escribiendo CSV consolidado (sin SQL)...")
    escribir_csv_consolidado(registros)
    
    # 3. Analizar patrones
    print("\n[3/4] Analizando patrones...")
    analisis = analizar_patrones(registros)
    print(f"      - {len(analisis['queries_compartidas'])} queries compartidas")
    print(f"      - {len(analisis['familias'])} familias detectadas")
    
    # 4. Detectar parametrizables
    grupos = detectar_parametrizables(registros)
    total_parametrizables = sum(g['cantidad'] for g in grupos)
    print(f"      - {len(grupos)} grupos parametrizables ({total_parametrizables} queries)")
    
    # 5. Generar Markdown
    print("\n[4/4] Generando análisis Markdown...")
    generar_markdown(registros, analisis, grupos)
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  Total queries únicas: {len(registros)}")
    print(f"  Queries parametrizables: {total_parametrizables}")
    print(f"  Funciones Python estimadas: {len(grupos)}")
    print(f"  Reducción estimada: ~{(total_parametrizables - len(grupos)) / len(registros) * 100:.0f}%")
    print("\nArchivos generados:")
    print(f"  - {OUTPUT_CSV}")
    print(f"  - {OUTPUT_MD}")
    print("=" * 60)


if __name__ == "__main__":
    main()
