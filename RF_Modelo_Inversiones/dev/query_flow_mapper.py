#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
query_flow_mapper.py — v1.0.0

Mapea el flujo completo de queries SQL de Access desde un entrypoint.
Detecta dependencias entre queries (FROM, INSERT INTO, etc.) y construye un DAG.

Inputs:
- CSV de queries (generado por access_extractor.py)
- Nombre de query entrypoint

Outputs:
- DAG completo de queries llamadas (directo e indirecto)
- Flowchart Mermaid visualizando el flujo
- CSV con todas las queries alcanzables y sus dependencias

Uso:
    python query_flow_mapper.py queries.csv --entry QUERY_PRINCIPAL --out flow.md
"""

import sys
import os
import csv
import re
import argparse
import textwrap
from collections import defaultdict, deque

# ------------------ Config ------------------
CSV_DELIMITER = ';'
ENCODING = 'utf-8-sig'

# ------------------ Parsing SQL ------------------

def extract_table_references_from_sql(sql: str):
    """
    Extrae nombres de tablas/queries referenciadas en SQL.
    Detecta:
    - FROM <tabla/query> (incluyendo multiples tablas separadas por coma)
    - JOIN <tabla/query>
    - INSERT INTO <tabla/query>
    - INTO <tabla> (SELECT INTO)
    - Referencias tabla.columna en SELECT y WHERE
    - Subqueries con alias
    """
    if not sql:
        return set()
    
    # Limpiar SQL
    sql_upper = sql.upper()
    
    # Eliminar strings literales para evitar falsos positivos
    sql_clean = re.sub(r"'[^']*'", "''", sql_upper)
    sql_clean = re.sub(r'"[^"]*"', '""', sql_clean)
    
    tables = set()
    
    # Palabras clave SQL a filtrar
    SQL_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 
        'UNION', 'EXCEPT', 'INTERSECT', 'AS', 'ON', 'AND', 'OR',
        'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'CROSS', 'FULL',
        'INSERT', 'INTO', 'UPDATE', 'DELETE', 'SET', 'VALUES',
        'CREATE', 'DROP', 'ALTER', 'TABLE', 'INDEX', 'VIEW',
        'NOT', 'NULL', 'IS', 'IN', 'LIKE', 'BETWEEN', 'EXISTS',
        'ALL', 'ANY', 'SOME', 'DISTINCT', 'TOP', 'LIMIT', 'OFFSET',
        'ASC', 'DESC', 'BY', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'SUM', 'COUNT', 'AVG', 'MIN', 'MAX', 'IIF', 'DATE', 'NOW'
    }
    
    # Patrones de extraccion (soportan nombres con guiones y puntos)
    patterns = [
        # FROM tabla / FROM [tabla]
        r'\bFROM\s+\[?([A-Za-z_][A-Za-z0-9_\-]*)\]?',
        # JOIN tabla / JOIN [tabla] (captura INNER JOIN, LEFT JOIN, etc.)
        r'\bJOIN\s+\[?([A-Za-z_][A-Za-z0-9_\-]*)\]?',
        # INSERT INTO tabla
        r'\bINSERT\s+INTO\s+\[?([A-Za-z_][A-Za-z0-9_\-]*)\]?',
        # SELECT ... INTO tabla FROM
        r'\bINTO\s+\[?([A-Za-z_][A-Za-z0-9_\-]*)\]?\s+FROM',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, sql_clean, re.IGNORECASE)
        for m in matches:
            table_name = m.group(1).strip()
            if table_name.upper() not in SQL_KEYWORDS:
                tables.add(table_name)
    
    # NUEVO: Extraer tablas de clausulas FROM con multiples tablas separadas por coma
    # Ejemplo: FROM tabla1, tabla2, tabla3 WHERE ...
    from_clause_pattern = r'\bFROM\s+([^;]+?)(?:\s+WHERE\b|\s+GROUP\s+BY\b|\s+ORDER\s+BY\b|\s+HAVING\b|\s+UNION\b|;|$)'
    from_matches = re.finditer(from_clause_pattern, sql_clean, re.IGNORECASE | re.DOTALL)
    
    for match in from_matches:
        from_content = match.group(1)
        # Dividir por coma, pero cuidado con JOINs
        # Primero remover partes con JOIN para no duplicar
        from_content_no_joins = re.sub(r'\b(?:INNER|LEFT|RIGHT|OUTER|CROSS|FULL)?\s*JOIN\b.*', '', from_content, flags=re.IGNORECASE)
        
        # Separar por coma
        parts = from_content_no_joins.split(',')
        for part in parts:
            # Limpiar y extraer nombre de tabla (puede tener alias)
            part = part.strip()
            # Patron: tabla [AS] alias o solo tabla
            table_match = re.match(r'\[?([A-Za-z_][A-Za-z0-9_\-]*)\]?(?:\s+(?:AS\s+)?[A-Za-z_][A-Za-z0-9_\-]*)?', part, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(1)
                if table_name.upper() not in SQL_KEYWORDS:
                    tables.add(table_name)
    
    # NUEVO: Extraer tablas de referencias tabla.columna
    # Ejemplo: RF_PLI_044b_Modelo_Inversiones_Pacto_FB.Moneda
    # Solo capturamos nombres que empiecen con RF_ para evitar falsos positivos
    table_dot_pattern = r'\b([A-Za-z_][A-Za-z0-9_\-]*)\.[A-Za-z_][A-Za-z0-9_\-]*\b'
    dot_matches = re.finditer(table_dot_pattern, sql_clean, re.IGNORECASE)
    
    for match in dot_matches:
        table_name = match.group(1)
        if table_name.upper() not in SQL_KEYWORDS:
            tables.add(table_name)
    
    return tables

def build_query_graph(queries_csv: str):
    """
    Lee el CSV de queries y construye grafo de dependencias.
    
    Returns:
        (query_dict, dependencies, reverse_deps)
        - query_dict: {nombre: {'tipo': ..., 'sql': ..., 'hash': ...}}
        - dependencies: {query_name: set(referenced_queries)}
        - reverse_deps: {query_name: set(queries_that_reference_this)}
    """
    query_dict = {}
    dependencies = defaultdict(set)
    reverse_deps = defaultdict(set)
    
    with open(queries_csv, 'r', encoding=ENCODING, newline='') as f:
        reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
        
        for row in reader:
            nombre = row['nombre']
            tipo = row['tipo']
            sql = row['sql']
            hash_sha1 = row['hash_sha1']
            
            query_dict[nombre] = {
                'tipo': tipo,
                'sql': sql,
                'hash': hash_sha1
            }
    
    # Construir grafo de dependencias
    all_query_names = set(query_dict.keys())
    
    # Crear índice case-insensitive para matching
    query_name_lower_map = {name.lower(): name for name in all_query_names}
    
    for query_name, data in query_dict.items():
        sql = data['sql']
        referenced = extract_table_references_from_sql(sql)
        
        # Filtrar solo las que son queries (no tablas base)
        # Hacemos matching case-insensitive
        referenced_queries = set()
        for ref in referenced:
            ref_lower = ref.lower()
            if ref_lower in query_name_lower_map:
                referenced_queries.add(query_name_lower_map[ref_lower])
        
        dependencies[query_name] = referenced_queries
        
        # Reverse dependencies
        for ref in referenced_queries:
            reverse_deps[ref].add(query_name)
    
    return query_dict, dependencies, reverse_deps

# ------------------ DAG Traversal ------------------

def find_all_dependencies(entry_point: str, dependencies: dict):
    """
    BFS para encontrar todas las queries alcanzables desde entry_point.
    
    Returns:
        set de nombres de queries alcanzables (incluyendo entry_point)
    """
    visited = set()
    queue = deque([entry_point])
    
    while queue:
        current = queue.popleft()
        
        if current in visited:
            continue
        
        visited.add(current)
        
        # Agregar dependencias a la cola
        for dep in dependencies.get(current, set()):
            if dep not in visited:
                queue.append(dep)
    
    return visited

def find_all_dependents(entry_point: str, reverse_deps: dict):
    """
    BFS para encontrar todas las queries que usan entry_point (directo o indirecto).
    
    Returns:
        set de nombres de queries que dependen de entry_point
    """
    visited = set()
    queue = deque([entry_point])
    
    while queue:
        current = queue.popleft()
        
        if current in visited:
            continue
        
        visited.add(current)
        
        # Agregar dependientes a la cola
        for dep in reverse_deps.get(current, set()):
            if dep not in visited:
                queue.append(dep)
    
    return visited

# ------------------ Mermaid Generation ------------------

def generate_mermaid_flowchart(entry_point: str, query_dict: dict, dependencies: dict, 
                               reachable_queries: set):
    """
    Genera flowchart Mermaid mostrando el flujo desde entry_point.
    """
    lines = []
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("  %% Estilos")
    lines.append("  classDef entryClass fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff")
    lines.append("  classDef queryClass fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff")
    lines.append("  classDef ddlClass fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff")
    lines.append("  classDef tableClass fill:#9E9E9E,stroke:#424242,stroke-width:1px,color:#fff")
    lines.append("")
    
    # Función helper para sanitizar IDs
    def sanitize_id(name):
        return re.sub(r'[^A-Za-z0-9_]', '_', name)
    
    # Nodos
    lines.append("  %% Nodos")
    for query_name in sorted(reachable_queries):
        qid = sanitize_id(query_name)
        data = query_dict.get(query_name, {})
        tipo = data.get('tipo', 'Unknown')
        
        # Label
        label = query_name
        if len(label) > 40:
            label = label[:37] + "..."
        
        # Determinar clase
        if query_name == entry_point:
            css_class = "entryClass"
            lines.append(f'  {qid}["{label}"]:::{css_class}')
        elif tipo == 'DDL':
            css_class = "ddlClass"
            lines.append(f'  {qid}["{label}<br/><small>({tipo})</small>"]:::{css_class}')
        else:
            css_class = "queryClass"
            lines.append(f'  {qid}["{label}<br/><small>({tipo})</small>"]:::{css_class}')
    
    lines.append("")
    
    # Edges
    lines.append("  %% Dependencias")
    edges_seen = set()
    
    for query_name in sorted(reachable_queries):
        qid_src = sanitize_id(query_name)
        
        for dep in sorted(dependencies.get(query_name, set())):
            if dep not in reachable_queries:
                continue  # Solo mostrar edges dentro del subgrafo alcanzable
            
            qid_dst = sanitize_id(dep)
            edge = (qid_src, qid_dst)
            
            if edge not in edges_seen:
                edges_seen.add(edge)
                lines.append(f"  {qid_src} --> {qid_dst}")
    
    lines.append("```")
    return "\n".join(lines)

# ------------------ Output CSV ------------------

def calculate_depth_from_entry(entry_point: str, dependencies: dict, reachable_queries: set):
    """
    Calcula la profundidad (distancia) de cada query desde el entry_point.
    Entry point tiene profundidad 0, sus dependencias directas profundidad 1, etc.
    
    Returns:
        dict: {query_name: depth}
    """
    depths = {entry_point: 0}
    queue = deque([entry_point])
    
    while queue:
        current = queue.popleft()
        current_depth = depths[current]
        
        for dep in dependencies.get(current, set()):
            if dep in reachable_queries and dep not in depths:
                depths[dep] = current_depth + 1
                queue.append(dep)
    
    return depths

def get_parent_queries(query_name: str, dependencies: dict, reachable_queries: set):
    """
    Encuentra las queries que dependen de esta query (queries padre en el grafo).
    Es decir, queries que tienen a query_name como dependencia directa.
    
    Returns:
        set de nombres de queries padre
    """
    parents = set()
    for q in reachable_queries:
        if query_name in dependencies.get(q, set()):
            parents.add(q)
    return parents

def write_flow_csv(out_csv: str, entry_point: str, query_dict: dict, 
                   dependencies: dict, reachable_queries: set):
    """
    Escribe CSV con todas las queries alcanzables, dependencias, SQL y metadata para recrear el grafo.
    
    Columnas:
    - query: nombre de la query
    - tipo: tipo de query (Select, DDL, Type128, etc.)
    - es_entrypoint: Si/No
    - nivel_profundidad: distancia desde el entry_point (0 = entry, 1 = deps directas, etc.)
    - queries_padre: queries que dependen de esta (hacia arriba en el grafo)
    - dependencias_directas: queries de las que depende esta (hacia abajo en el grafo)
    - num_dependencias: cantidad de dependencias directas
    - hash_sha1: hash del SQL
    - sql: codigo SQL de la query
    """
    # Calcular profundidades
    depths = calculate_depth_from_entry(entry_point, dependencies, reachable_queries)
    
    with open(out_csv, 'w', encoding=ENCODING, newline='') as f:
        writer = csv.writer(f, delimiter=CSV_DELIMITER)
        writer.writerow([
            'query', 
            'tipo', 
            'es_entrypoint', 
            'nivel_profundidad',
            'queries_padre',
            'dependencias_directas', 
            'num_dependencias', 
            'hash_sha1',
            'sql'
        ])
        
        # Ordenar por profundidad primero, luego por nombre
        sorted_queries = sorted(reachable_queries, key=lambda q: (depths.get(q, 999), q))
        
        for query_name in sorted_queries:
            data = query_dict.get(query_name, {})
            tipo = data.get('tipo', 'Unknown')
            hash_val = data.get('hash', '')
            sql = data.get('sql', '')
            
            # Dependencias directas (hacia abajo)
            deps = dependencies.get(query_name, set())
            # Filtrar solo las que estan en el subgrafo alcanzable
            deps_in_scope = deps.intersection(reachable_queries)
            deps_str = ', '.join(sorted(deps_in_scope))
            num_deps = len(deps_in_scope)
            
            # Queries padre (hacia arriba)
            parents = get_parent_queries(query_name, dependencies, reachable_queries)
            parents_str = ', '.join(sorted(parents))
            
            is_entry = 'Si' if query_name == entry_point else 'No'
            depth = depths.get(query_name, -1)
            
            writer.writerow([
                query_name, 
                tipo, 
                is_entry, 
                depth,
                parents_str,
                deps_str, 
                num_deps, 
                hash_val,
                sql
            ])

# ------------------ Main ------------------

def run(queries_csv: str, entry_point: str, out_markdown: str, out_csv: str):
    """
    Ejecuta el análisis completo de flujo de queries.
    """
    print(f"📊 Analizando queries desde: {queries_csv}")
    print(f"🎯 Entry point: {entry_point}")
    
    # 1. Construir grafo
    query_dict, dependencies, reverse_deps = build_query_graph(queries_csv)
    
    total_queries = len(query_dict)
    print(f"  OK: {total_queries} queries encontradas")
    
    # Validar entry point
    if entry_point not in query_dict:
        print(f"\nERROR: ERROR: Query '{entry_point}' no encontrada en el CSV")
        print(f"\nQueries disponibles (primeras 10):")
        for i, qname in enumerate(sorted(query_dict.keys())[:10], 1):
            print(f"  {i}. {qname}")
        if total_queries > 10:
            print(f"  ... y {total_queries - 10} más")
        sys.exit(1)
    
    # 2. Encontrar todas las dependencias (queries que usa el entry point)
    print(f"\n🔍 Buscando dependencias desde '{entry_point}'...")
    reachable = find_all_dependencies(entry_point, dependencies)
    
    print(f"  OK: {len(reachable)} queries alcanzables (incluyendo entry point)")
    
    # 3. Generar flowchart Mermaid
    print(f"\n📐 Generando flowchart Mermaid...")
    mermaid_content = generate_mermaid_flowchart(entry_point, query_dict, 
                                                  dependencies, reachable)
    
    # 4. Escribir outputs
    print(f"\n💾 Escribiendo outputs...")
    
    # Markdown con mermaid
    with open(out_markdown, 'w', encoding=ENCODING, newline='') as f:
        f.write(f"# Flujo de Queries - {entry_point}\n\n")
        f.write(f"**Entry Point:** `{entry_point}`\n\n")
        f.write(f"**Queries alcanzables:** {len(reachable)}\n\n")
        f.write("---\n\n")
        f.write("## Flowchart\n\n")
        f.write(mermaid_content)
        f.write("\n\n---\n\n")
        f.write("## Listado de Queries\n\n")
        
        for query_name in sorted(reachable):
            data = query_dict[query_name]
            tipo = data['tipo']
            deps = dependencies.get(query_name, set())
            
            marker = "🎯" if query_name == entry_point else "🔹"
            f.write(f"{marker} **{query_name}** ({tipo})\n")
            
            if deps:
                f.write(f"   - Depende de: {', '.join(sorted(deps))}\n")
            
            f.write("\n")
    
    # CSV con detalles
    write_flow_csv(out_csv, entry_point, query_dict, dependencies, reachable)
    
    print(f"  OK: Markdown: {out_markdown}")
    print(f"  OK: CSV: {out_csv}")
    
    # 5. Estadísticas
    print(f"\n📈 Estadísticas:")
    print(f"  - Total queries en base: {total_queries}")
    print(f"  - Queries alcanzables: {len(reachable)}")
    print(f"  - Cobertura: {len(reachable)/total_queries*100:.1f}%")
    
    # Queries con más dependencias
    deps_sorted = sorted([(q, len(dependencies.get(q, set()))) 
                          for q in reachable], 
                         key=lambda x: x[1], reverse=True)
    
    if deps_sorted:
        print(f"\n  Top 5 queries con más dependencias:")
        for i, (qname, num_deps) in enumerate(deps_sorted[:5], 1):
            print(f"    {i}. {qname}: {num_deps} dependencias")

def main():
    parser = argparse.ArgumentParser(
        description='Mapea flujo de queries SQL desde un entrypoint (v1.0.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''\
            Ejemplo:
              python query_flow_mapper.py queries.csv \\
                  --entry QUERY_PRINCIPAL \\
                  --out flow.md \\
                  --out-csv flow_queries.csv
              
            El CSV debe ser generado por access_extractor.py con formato:
              nombre;tipo;sql;hash_sha1
        '''))
    
    parser.add_argument('csv', help='CSV de queries (generado por access_extractor.py)')
    parser.add_argument('--entry', required=True, help='Query entrypoint')
    parser.add_argument('--out', default=None, 
                       help='Archivo Markdown de salida (default: <entry>_flow.md)')
    parser.add_argument('--out-csv', default=None,
                       help='CSV de salida con queries alcanzables (default: <entry>_flow.csv)')
    
    args = parser.parse_args()
    
    queries_csv = args.csv
    entry_point = args.entry
    
    if not os.path.isfile(queries_csv):
        print(f"ERROR: no existe el archivo {queries_csv}")
        sys.exit(1)
    
    # Defaults para outputs
    safe_entry = re.sub(r'[^A-Za-z0-9_]', '_', entry_point)
    out_md = args.out or f"{safe_entry}_flow.md"
    out_csv = args.out_csv or f"{safe_entry}_flow.csv"
    
    try:
        run(queries_csv, entry_point, out_md, out_csv)
        print(f"\nOK: Análisis completado exitosamente")
    except Exception as e:
        print(f"\nERROR: ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == '__main__':
    main()
