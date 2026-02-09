# Flujo de Queries - RF_PLI_039_GenerCartBBC_Pond

**Entry Point:** `RF_PLI_039_GenerCartBBC_Pond`

**Queries alcanzables:** 4

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
  RF_PLI_001_CarteraInv["RF_PLI_001_CarteraInv<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_037_CarteraBBC_CLP["RF_PLI_037_CarteraBBC_CLP<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_038_CarteraBBC_CLP_MonTotal["RF_PLI_038_CarteraBBC_CLP_MonTotal<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_039_GenerCartBBC_Pond["RF_PLI_039_GenerCartBBC_Pond"]:::entryClass

  %% Dependencias
  RF_PLI_037_CarteraBBC_CLP --> RF_PLI_001_CarteraInv
  RF_PLI_038_CarteraBBC_CLP_MonTotal --> RF_PLI_037_CarteraBBC_CLP
  RF_PLI_039_GenerCartBBC_Pond --> RF_PLI_037_CarteraBBC_CLP
  RF_PLI_039_GenerCartBBC_Pond --> RF_PLI_038_CarteraBBC_CLP_MonTotal
```

---

## Listado de Queries

🔹 **RF_PLI_001_CarteraInv** (Select)

🔹 **RF_PLI_037_CarteraBBC_CLP** (Select)
   - Depende de: RF_PLI_001_CarteraInv

🔹 **RF_PLI_038_CarteraBBC_CLP_MonTotal** (Select)
   - Depende de: RF_PLI_037_CarteraBBC_CLP

🎯 **RF_PLI_039_GenerCartBBC_Pond** (DDL)
   - Depende de: RF_PLI_037_CarteraBBC_CLP, RF_PLI_038_CarteraBBC_CLP_MonTotal

