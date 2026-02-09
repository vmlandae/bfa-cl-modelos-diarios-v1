# Flujo de Queries - RF_PLI_004_GenerCartGobCLP_Pond

**Entry Point:** `RF_PLI_004_GenerCartGobCLP_Pond`

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
  RF_PLI_002_CarteraGobCLP["RF_PLI_002_CarteraGobCLP<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_003_CarteraGobCLP_MonTotal["RF_PLI_003_CarteraGobCLP_MonTotal<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_004_GenerCartGobCLP_Pond["RF_PLI_004_GenerCartGobCLP_Pond"]:::entryClass

  %% Dependencias
  RF_PLI_002_CarteraGobCLP --> RF_PLI_001_CarteraInv
  RF_PLI_003_CarteraGobCLP_MonTotal --> RF_PLI_002_CarteraGobCLP
  RF_PLI_004_GenerCartGobCLP_Pond --> RF_PLI_002_CarteraGobCLP
  RF_PLI_004_GenerCartGobCLP_Pond --> RF_PLI_003_CarteraGobCLP_MonTotal
```

---

## Listado de Queries

🔹 **RF_PLI_001_CarteraInv** (Select)

🔹 **RF_PLI_002_CarteraGobCLP** (Select)
   - Depende de: RF_PLI_001_CarteraInv

🔹 **RF_PLI_003_CarteraGobCLP_MonTotal** (Select)
   - Depende de: RF_PLI_002_CarteraGobCLP

🎯 **RF_PLI_004_GenerCartGobCLP_Pond** (DDL)
   - Depende de: RF_PLI_002_CarteraGobCLP, RF_PLI_003_CarteraGobCLP_MonTotal

