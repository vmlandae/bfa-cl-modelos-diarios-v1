# Guía de Contribución

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-01-29

---

## Flujo de Trabajo

### 1. Crear rama desde main

```bash
git checkout main
git pull origin main
git checkout -b feat/mi-nueva-feature
```

### 2. Convención de nombres de ramas

| Prefijo | Uso |
|---------|-----|
| `feat/` | Nueva funcionalidad |
| `fix/` | Corrección de bugs |
| `docs/` | Solo documentación |
| `refactor/` | Refactorización sin cambio funcional |
| `test/` | Agregar o modificar tests |

### 3. Commits

Usar [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: agregar modelo de prepago CMR
fix: corregir cálculo de SMM en consumo
docs: actualizar guía de instalación
refactor: extraer lógica común de cargadores
test: agregar tests para DuckDB manager
```

### 4. Crear Merge Request

1. Push de tu rama: `git push origin feat/mi-feature`
2. Crear MR en GitLab
3. Asignar reviewers
4. Esperar aprobación
5. Merge a main

## Estándares de Código

### Python

- Usar type hints
- Docstrings en funciones públicas
- Formatear con `black`
- Lint con `flake8`

```python
def calcular_smm(tasa: float, factor: float) -> float:
    """
    Calcula la tasa SMM ajustada.
    
    Args:
        tasa: Tasa base SMM
        factor: Factor de ajuste
        
    Returns:
        Tasa SMM ajustada
    """
    return tasa * factor
```

### Documentación

- Usar Markdown
- Incluir autor y fecha
- Mantener actualizado el CHANGELOG

## Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=. --cov-report=html
```

## Documentación Local

```bash
# Instalar mkdocs
pip install mkdocs-material

# Servir documentación localmente
mkdocs serve

# Abrir http://localhost:8000
```
