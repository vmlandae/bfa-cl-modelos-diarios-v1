# Flujo de Queries - RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT

**Entry Point:** `RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT`

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
  RF_PLI_044g_CarteraInv_RT["RF_PLI_044g_CarteraInv_RT<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT["RF_PLI_048c_Tabla_Desarrollo_Interna_..."]:::entryClass

  %% Dependencias
  RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT --> RF_PLI_044g_CarteraInv_RT
```

---

## Listado de Queries

🔹 **RF_PLI_044g_CarteraInv_RT** (Select)

🎯 **RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT** (Type64)
   - Depende de: RF_PLI_044g_CarteraInv_RT

