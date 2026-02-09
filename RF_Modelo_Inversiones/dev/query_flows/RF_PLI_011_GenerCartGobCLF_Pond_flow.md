# Flujo de Queries - RF_PLI_011_GenerCartGobCLF_Pond

**Entry Point:** `RF_PLI_011_GenerCartGobCLF_Pond`

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
  RF_PLI_009_CarteraGobCLF["RF_PLI_009_CarteraGobCLF<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_010_CarteraGobCLF_MonTotal["RF_PLI_010_CarteraGobCLF_MonTotal<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_011_GenerCartGobCLF_Pond["RF_PLI_011_GenerCartGobCLF_Pond"]:::entryClass

  %% Dependencias
  RF_PLI_009_CarteraGobCLF --> RF_PLI_001_CarteraInv
  RF_PLI_010_CarteraGobCLF_MonTotal --> RF_PLI_009_CarteraGobCLF
  RF_PLI_011_GenerCartGobCLF_Pond --> RF_PLI_009_CarteraGobCLF
  RF_PLI_011_GenerCartGobCLF_Pond --> RF_PLI_010_CarteraGobCLF_MonTotal
```

---

## Listado de Queries

🔹 **RF_PLI_001_CarteraInv** (Select)

🔹 **RF_PLI_009_CarteraGobCLF** (Select)
   - Depende de: RF_PLI_001_CarteraInv

🔹 **RF_PLI_010_CarteraGobCLF_MonTotal** (Select)
   - Depende de: RF_PLI_009_CarteraGobCLF

🎯 **RF_PLI_011_GenerCartGobCLF_Pond** (DDL)
   - Depende de: RF_PLI_009_CarteraGobCLF, RF_PLI_010_CarteraGobCLF_MonTotal

