# Flujo de Queries - RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM

**Entry Point:** `RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM`

**Queries alcanzables:** 2

---

## Flowchart

```mermaid
flowchart TD
  %% Estilos
  classDef entryClass fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
  classDef queryClass fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
  classDef ddlClass fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
  classDef tableClass fill:#9E9E9E,stroke:#424242,stroke-width:1px,color:#fff

  %% Nodos
  RF_PLI_044f_CarteraInv_FFMM["RF_PLI_044f_CarteraInv_FFMM<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM["RF_PLI_048a_Tabla_Desarrollo_Interna_..."]:::entryClass

  %% Dependencias
  RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM --> RF_PLI_044f_CarteraInv_FFMM
```

---

## Listado de Queries

🔹 **RF_PLI_044f_CarteraInv_FFMM** (Select)

🎯 **RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM** (Type64)
   - Depende de: RF_PLI_044f_CarteraInv_FFMM

