# Flujo de Queries - RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel

**Entry Point:** `RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel`

**Queries alcanzables:** 6

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
  RF_PLI_044g_CarteraInv_RT["RF_PLI_044g_CarteraInv_RT<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_044i_CarteraInv_HTM["RF_PLI_044i_CarteraInv_HTM<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_046_Modelo_Inversiones_Final_CLP["RF_PLI_046_Modelo_Inversiones_Final_CLP<br/><small>(Select)</small>"]:::queryClass
  RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones["RF_PLI_049_Tabla_Desarrollo_Modelo_In...<br/><small>(Type128)</small>"]:::queryClass
  RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel["RF_PLI_050_Tabla_Desarrollo_Modelo_In..."]:::entryClass

  %% Dependencias
  RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones --> RF_PLI_044f_CarteraInv_FFMM
  RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones --> RF_PLI_044g_CarteraInv_RT
  RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones --> RF_PLI_044i_CarteraInv_HTM
  RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones --> RF_PLI_046_Modelo_Inversiones_Final_CLP
  RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel --> RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones
```

---

## Listado de Queries

🔹 **RF_PLI_044f_CarteraInv_FFMM** (Select)

🔹 **RF_PLI_044g_CarteraInv_RT** (Select)

🔹 **RF_PLI_044i_CarteraInv_HTM** (Select)

🔹 **RF_PLI_046_Modelo_Inversiones_Final_CLP** (Select)

🔹 **RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones** (Type128)
   - Depende de: RF_PLI_044f_CarteraInv_FFMM, RF_PLI_044g_CarteraInv_RT, RF_PLI_044i_CarteraInv_HTM, RF_PLI_046_Modelo_Inversiones_Final_CLP

🎯 **RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel** (DDL)
   - Depende de: RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones

