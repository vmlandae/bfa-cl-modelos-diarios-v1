# Workflow de Planificación Colaborativa

> **Última actualización:** 2026-02-25  
> **Autor:** vlandaetat

---

## El Sistema en 30 Segundos

```
roadmap.yaml          →  Fuente de verdad (editable, diffable, reviewable)
     │
     ├── MkDocs       →  Visualización bonita en docs/ (Gantt, dependencias, checklists)
     ├── GitLab MRs   →  Discusión y aprobación de cambios al plan
     └── GitLab Issues →  Tracking detallado por feature (opcional)
```

No necesitamos Monday ni Trello. **Git + GitLab + MkDocs** nos dan:

| Necesidad | Herramienta | Equivalente Trello/Monday |
|-----------|-------------|---------------------------|
| Ver el plan completo | MkDocs Roadmap | Board view |
| Proponer cambios | MR en GitLab | Crear/mover tarjeta |
| Discutir features | Comentarios en MR | Comentarios en tarjeta |
| Aprobar prioridades | Review + merge | Aprobación de manager |
| Historia de decisiones | Git log del YAML | Historial de actividad |
| Asignar responsables | Campo `asignado` en YAML | Asignar miembro |

---

## Flujos de Trabajo

### 1. Proponer una nueva feature

```bash
# 1. Crear rama
git checkout -b roadmap/nueva-feature-X

# 2. Editar roadmap.yaml — agregar un bloque al final de features:
```

```yaml
  - id: FXX
    titulo: "Mi nueva feature"
    descripcion: >
      Descripción clara de qué se quiere lograr y por qué.
    estado: backlog
    prioridad: media
    tamano: M
    sprint: backlog
    asignado: null
    etiquetas: [mi-etiqueta]
    dependencias: []
    criterios_aceptacion:
      - "Criterio 1"
      - "Criterio 2"
```

```bash
# 3. Commit y push
git add docs/roadmap/roadmap.yaml
git commit -m "roadmap: proponer feature FXX — Mi nueva feature"
git push origin roadmap/nueva-feature-X

# 4. Crear MR en GitLab con etiqueta 'roadmap'
# 5. El equipo discute en el MR
# 6. Se aprueba y mergea → aparece en MkDocs
```

### 2. Tomar una feature para desarrollar

```bash
# 1. Actualizar estado en roadmap.yaml
#    estado: planificado → en-progreso
#    asignado: "mi-usuario"

# 2. Crear rama de desarrollo
git checkout -b feat/FXX-nombre-corto

# 3. Desarrollar...

# 4. Al terminar, actualizar roadmap.yaml
#    estado: en-progreso → completado

# 5. Crear MR con los cambios de código + actualización del roadmap
git add .
git commit -m "feat(FXX): implementar nombre-corto

- Detalle de lo implementado
- Cierra FXX"
```

### 3. Sprint planning (cada ~2 semanas)

```bash
# 1. Crear rama
git checkout -b roadmap/sprint-SX

# 2. Editar roadmap.yaml:
#    - Mover features del backlog al sprint nuevo
#    - Ajustar prioridades según contexto
#    - Asignar responsables

# 3. Crear MR
git commit -m "roadmap: planificar sprint SX"

# 4. Review en equipo → merge
```

---

## Convenciones

### IDs de Features

- Formato: `FNN` (F01, F02, ..., F17, ...)
- Nunca reutilizar un ID, incluso si la feature se descarta
- IDs nuevos siempre incrementales

### Estados

```
backlog → planificado → en-progreso → completado
                    └→ descartado
```

| Estado | Significado |
|--------|-------------|
| `backlog` | Idea registrada, no priorizada para un sprint |
| `planificado` | Asignada a un sprint, lista para iniciar |
| `en-progreso` | Alguien está trabajando activamente |
| `completado` | Implementada, mergeada, verificada |
| `descartado` | No se hará (documentar razón en `notas`) |

### Tamaños

| Tamaño | Tiempo estimado | Ejemplo |
|--------|-----------------|---------|
| XS | < 2 horas | F02: Snapshot de parámetros |
| S | 2h — 1 día | F13: Pre-flight checks |
| M | 1 — 3 días | F11: Logging estructurado |
| L | 3 días — 1 semana | F01: Torre de Control |
| XL | 1 — 2 semanas | F04: Scenario Playground |
| XXL | > 2 semanas | F10: Model API |

### Prioridades

| Prioridad | Cuándo usarla |
|-----------|---------------|
| `crítica` | Bloquea trabajo de otros o tiene deadline externo |
| `alta` | Alto impacto, esfuerzo razonable |
| `media` | Importante pero no urgente |
| `baja` | Nice to have, cuando haya tiempo |

### Ramas y Commits

| Tipo | Rama | Commit |
|------|------|--------|
| Feature | `feat/FXX-nombre` | `feat(FXX): descripción` |
| Roadmap | `roadmap/descripción` | `roadmap: descripción` |
| Fix | `fix/FXX-descripción` | `fix(FXX): descripción` |
| Docs | `docs/descripción` | `docs: descripción` |

---

## GitLab Issues (Opcional)

Para features complejas que requieren tracking más granular, se puede crear un Issue en GitLab:

1. Título: `[FXX] Nombre de la feature`
2. Descripción: copiar criterios de aceptación del YAML
3. Labels: las etiquetas del YAML
4. Milestone: el sprint correspondiente

```
roadmap.yaml  ←→  GitLab Issue
(plan macro)      (tracking diario, subtareas, discusión extendida)
```

No es obligatorio crear Issues para todas las features. El YAML es suficiente para features pequeñas (XS, S). Para features L+ considerar crear un Issue.

### Configuración de GitLab Board

Si quieren un board tipo Kanban en GitLab:

1. Ir a **Issues → Boards** en el repo
2. Crear listas por estado: `Backlog`, `Planificado`, `En Progreso`, `Completado`
3. Crear labels correspondientes
4. Cada Issue se mueve entre listas arrastrando

---

## Checklist para Nuevos Miembros

- [ ] Clonar el repo y ejecutar `mkdocs serve` para ver la documentación
- [ ] Leer el [Roadmap](index.md) completo
- [ ] Identificar features en las que te interesa contribuir
- [ ] Leer la [Guía de Contribución](../desarrollo/contribuir.md)
- [ ] Crear tu primera rama `roadmap/` con una propuesta o comentario

---

## FAQ

??? question "¿Por qué no usar solo GitLab Issues/Boards?"
    - Los Issues no dan una vista de conjunto con Gantt y dependencias
    - El YAML en el repo es versionable, diffable, y reviewable como código
    - No todos tienen acceso cómodo a GitLab (algunos ven solo MkDocs)
    - El YAML se puede procesar programáticamente (generar reportes, métricas)

??? question "¿Por qué no usar Monday/Trello/Jira?"
    - Requiere licencia adicional y aprobación corporativa
    - No está integrado con el código (el plan vive separado del repo)
    - No es versionable ni tiene historia de cambios granular
    - Para un equipo de 3-5 personas, Git + YAML es suficiente

??? question "¿Cómo mantenemos sincronizado el YAML con MkDocs?"
    - MkDocs lee directamente los archivos `.md` de `docs/`
    - El roadmap visual (`docs/roadmap/index.md`) se actualiza manualmente
      cuando hay cambios grandes al YAML
    - Futuro: script que genera el `.md` automáticamente desde el YAML

??? question "¿Qué pasa si dos personas editan el YAML al mismo tiempo?"
    - Mismo flujo que con código: cada uno en su rama, merge via MR
    - Git resuelve conflictos automáticamente si editan secciones distintas
    - Si editan la misma sección, el segundo MR tendrá conflicto → resolver manualmente
