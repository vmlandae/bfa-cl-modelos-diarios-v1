import pandas as pd
import numpy as np
from bfa_cl_utilidades import estandariza_nombre_columnas_dataframe

class LimpiadorDatos:
    """Clase estática para limpieza y transformación de datos"""
    
    @staticmethod
    def estandarizar_interfaz_pml(df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplicar estructuración básica a datos de interfaz
        
        Args:
            df: DataFrame con datos de interfaz
            
        Returns:
            DataFrame limpio
        """
        print("      • Aplicando limpieza básica de datos...")
        
        df_limpio = estandariza_nombre_columnas_dataframe(df.copy())

        # Convertir fechas con manejo especial para fechas inválidas
        campos_fecha = ['FECHA_PROCESO', 'FECHA_CREACION','FECHA_INICIO_CUOTA','FECHA_VENCIMIENTO_CUOTA', 'FECHA_PAGO','FECHA_REPRICING',]
        for campo in campos_fecha:
            if campo in df_limpio.columns:
                # Reemplazar valores que representan fechas nulas (19000101 = 1 enero 1900)
                df_limpio[campo] = df_limpio[campo].astype(str).str.strip()
                df_limpio[campo] = df_limpio[campo].replace(['19000101', '0', ''], pd.NaT)
                try:

                    df_limpio[campo] = pd.to_datetime(
                        df_limpio[campo], 
                        format='%Y%m%d', 
                        errors='raise'
                    )
                except ValueError as e:
                    # Obtener valores problemáticos para el mensaje de error
                    valores_problematicos = df_limpio[campo][df_limpio[campo].notna()].unique()[:5]
                    valores_str = [str(val) for val in valores_problematicos]
                    
                    error_msg = f"ERROR: Valores inválidos encontrados en la columna '{campo}'.\n"
                    error_msg += "Formato esperado: YYYYMMDD o valores nulos ['19000101', '0', ''].\n"
                    error_msg += f"Valores problemáticos encontrados: {valores_str}\n"
                    error_msg += f"Error original: {str(e)}"
                    
                    raise ValueError(error_msg) from e
        
        # Limpiar campos de texto
        campos_texto = ['SISTEMA','CODIGO_EMPRESA', 'COD_ACT_PAS', 'CODIGO_PRODUCTO', 'CODIGO_SUBPRODUCTO', 'DESTINOCREDITO', 
                        'FACTOR_DE_RIESGO','TIPO_CUOTA','CODIGO_EJECUTIVO', 'CODIGO_ESTRATEGIA', 'CLASIFICACION_CONTABLE', 
                        'TIPO_TASA', 'MAYORISTAMINORISTA', 'MARCA_CUMPLIMIENTO','EMPRESA_RELACIONADA', 'MODELO_PERFIL']
        for campo in campos_texto:
            if campo in df_limpio.columns:
                df_limpio[campo] = df_limpio[campo].str.strip()
        
        # Convertir campos numéricos
        campos_numericos = ['OPERACION','MONEDA_ORIGEN','MONEDA_COMPENSACION','NUMERO_CUOTA', 
                            'AMORTIZACION', 'INTERES','INTERES_DEVENGADO','VP_AMORTIZACION', 'VP_INTERES', 'TASA', 'TASA_CF','SPREAD']
        for campo in campos_numericos:
                try:
                    if campo in df_limpio.columns:
                        df_limpio[campo] = df_limpio[campo].astype(str).str.strip()
                        df_limpio[campo] = df_limpio[campo].str.replace(',', '.')  # Convertir coma decimal a punto
                        
                        # # Manejar valores especiales
                        df_limpio[campo] = df_limpio[campo].replace(['nan', 'NaN', 'null', 'NULL', ''], np.nan)
                        
                        df_limpio[campo] = pd.to_numeric(df_limpio[campo], errors='raise')
                except (ValueError, TypeError) as e:
                    # Obtener valores problemáticos para el mensaje de error
                    valores_problematicos = df_limpio[campo][df_limpio[campo].notna()].unique()[:5]
                    valores_str = [str(val) for val in valores_problematicos]
                    
                    error_msg = f"ERROR: Valores inválidos encontrados en la columna numérica '{campo}'.\n"
                    error_msg += "Formato esperado: Valores numéricos válidos.\n"
                    error_msg += f"Valores problemáticos encontrados: {valores_str}\n"
                    error_msg += f"Error original: {str(e)}"
                    raise ValueError(error_msg) from e
                
        # Validar campos que deben ser nulos
        campos_nulos = ['COMPENSACION','AREA_NEGOCIO','INDEXADOR']
        for campo in campos_nulos:
            if campo in df_limpio.columns:
                # Limpiar y normalizar valores antes de validar
                df_limpio[campo] = df_limpio[campo].astype(str).str.strip()
                
                # Reemplazar valores que representan nulos con pd.NA
                valores_nulos_permitidos = ['nan', 'NaN', 'None', 'NULL', 'null', '', ' ']
                df_limpio[campo] = df_limpio[campo].replace(valores_nulos_permitidos, pd.NA)
                
                # Verificar que todos los valores sean nulos después de la limpieza
                valores_no_nulos = df_limpio[campo].notna()
                if valores_no_nulos.any():
                    # Obtener valores problemáticos (no nulos)
                    valores_problematicos = df_limpio[campo][valores_no_nulos].unique()[:5]
                    valores_str = [str(val) for val in valores_problematicos]
                    count_no_nulos = valores_no_nulos.sum()
                    
                    error_msg = f"ERROR: Se encontraron valores no nulos en la columna '{campo}' que debe ser nula.\n"
                    error_msg += "Se esperaba que todos los valores fueran nulos/NaN o espacios en blanco.\n"
                    error_msg += f"Registros con valores no nulos: {count_no_nulos:,}\n"
                    error_msg += f"Valores encontrados: {valores_str}"
                    
                    raise ValueError(error_msg)
                 
        return df_limpio
    
    
    
    @staticmethod
    def transformar_datos_mr_prepago_consumo(df: pd.DataFrame) -> pd.DataFrame:

        print("      • Asignando categorías de consumo...")
        
        # Listas de subproductos por categoría
        subproducto_consumo = ["1", "4", "31", "33", "35", "68", "69", "71", "73", "78", "81"]
        subproducto_automotriz = ["16"]
        subproducto_refinanciado = ["24", "36", "43", "75"]
        subproducto_consolidado = ["27", "32", "34", "37", "42", "46"]
        subproducto_renegociado = ["1", "4", "16", "23", "24", "27", "31", "32", 
                                  "35", "37", "42", "43", "46", "100"]
        
        # Condiciones para categorización
        condiciones = [
            (df['SISTEMA'] == "CRC") & (df['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo)),
            (df['SISTEMA'] == "CRC") & (df['CODIGO_SUBPRODUCTO'].isin(subproducto_automotriz)),
            (df['SISTEMA'] == "CRC") & (df['CODIGO_SUBPRODUCTO'].isin(subproducto_refinanciado)),
            (df['SISTEMA'] == "CRC") & (df['CODIGO_SUBPRODUCTO'].isin(subproducto_consolidado)),
            (df['SISTEMA'] == "REC") & (df['CODIGO_SUBPRODUCTO'].isin(subproducto_renegociado)),
        ]
        
        resultados = ["CONSUMO", "AUTOMOTRIZ", "REFINANCIADO", "CONSOLIDADO", "RENEGOCIADO"]
        
        df["GLOSA_CODIGO_DESTINOCREDITO"] = np.select(condiciones, resultados, default="OTROS")
        
        # Validar que no haya registros sin categorizar
        registros_otros = df[df["GLOSA_CODIGO_DESTINOCREDITO"] == "OTROS"]
        if not registros_otros.empty:
            info_problematicos = registros_otros[['SISTEMA', 'CODIGO_PRODUCTO', 'CODIGO_SUBPRODUCTO']].drop_duplicates()
            error_msg = f"ERROR: Se encontraron {len(registros_otros)} registros sin categoría válida.\n"
            error_msg += "Combinaciones problemáticas:\n"
            for _, row in info_problematicos.iterrows():
                error_msg += f"  - SISTEMA: {row['SISTEMA']}, PRODUCTO: {row['CODIGO_PRODUCTO']}, SUBPRODUCTO: {row['CODIGO_SUBPRODUCTO']}\n"
            raise ValueError(error_msg)
        
        print("        - Categorización completada")

        df['FECHA_VENCIMIENTO_AJUSTADA'] = LimpiadorDatos._estandariza_vencimiento_mr_prepago_consumo(df)
        return df
    
    @staticmethod
    def filtrar_por_subproductos_consumo(df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtrar datos para modelo de consumo
        
        Args:
            df: DataFrame con datos
            
        Returns:
            DataFrame filtrado
        """
        print("      • Filtrando para modelo de consumo...")
        
        # Subproductos válidos para consumo
        subproductos_crc = ["1", "4", "16", "24", "27", 
                            "31", "32","33", "32", "34", "35", 
                            "36", "37", "38", "42", "43", 
                            "46", "68", "69", "71", "73", 
                            "75", "78", "81"
                        ]
        
        subproductos_rec = [
            "1", "4", "16", "23", "24", "27", "31", "32", 
            "35", "37", "42", "43", "46", "100"
        ]
        
        filtro = (
            ((df['SISTEMA'] == "CRC") & (df['CODIGO_PRODUCTO'] == "150001") & 
             (df['CODIGO_SUBPRODUCTO'].isin(subproductos_crc))) |
            ((df['SISTEMA'] == "REC") & (df['CODIGO_PRODUCTO'] == "150001") & 
             (df['CODIGO_SUBPRODUCTO'].isin(subproductos_rec)))
        )
        
        df_filtrado = df[filtro].reset_index(drop=True).copy()
        print(f"        - Filtrado completado: {len(df_filtrado):,} registros válidos")
        
        return df_filtrado
    
    
    @staticmethod
    def _estandariza_vencimiento_mr_prepago_consumo(df: pd.DataFrame) -> pd.Series:
        """
        Estandarizar fechas de vencimiento según reglas de negocio
        """
        fecha_venc = df['FECHA_VENCIMIENTO_CUOTA'].copy()
        fecha_proceso = df['FECHA_PROCESO'].iloc[0]
        
        # Condiciones
        es_anterior = fecha_venc < fecha_proceso
        mismo_mes_año = (fecha_venc.dt.year == fecha_proceso.year) & (fecha_venc.dt.month == fecha_proceso.month)
        
        # Aplicar reglas
        # Regla 1: Si es anterior o mismo mes/año → fecha_proceso + 1 día
        mask_regla_1 = es_anterior | mismo_mes_año
        fecha_venc.loc[mask_regla_1] = fecha_proceso + pd.Timedelta(days=1)
        
        # Regla 2: Para el resto → día 5 del mismo mes
        mask_regla_2 = ~mask_regla_1
        if mask_regla_2.any():
            fechas_a_cambiar = fecha_venc.loc[mask_regla_2]
            # Crear nuevas fechas con día 5
            nuevas_fechas = pd.to_datetime({
                'year': fechas_a_cambiar.dt.year,
                'month': fechas_a_cambiar.dt.month, 
                'day': 5
            })
            fecha_venc.loc[mask_regla_2] = nuevas_fechas
        
        return fecha_venc
    # @staticmethod
    # def _estandariza_vencimiento_mr_prepago_consumo(df: pd.DataFrame) -> pd.Series:
    #     """
    #     Estandarizar fechas de vencimiento según reglas de negocio (versión vectorizada)
        
    #     Returns:
    #         Series con fechas ajustadas (NO modifica el DataFrame original)
    #     """
    #     fecha_venc = df['FECHA_VENCIMIENTO_CUOTA']
    #     fecha_proceso = df['FECHA_PROCESO'].iloc[0]
        
    #     # Condiciones
    #     es_anterior = fecha_venc < fecha_proceso
    #     mismo_mes_año = (fecha_venc.dt.year == fecha_proceso.year) & (fecha_venc.dt.month == fecha_proceso.month)
        
    #     # Aplicar transformaciones y retornar solo la Serie ajustada
    #     fecha_ajustada = np.where(
    #         (es_anterior | mismo_mes_año),
    #         fecha_proceso + pd.Timedelta(days=1),
    #         fecha_venc + pd.offsets.MonthBegin(0) + pd.Timedelta(days=4)
    #     )
        
    #     return pd.Series(fecha_ajustada, index=df.index)
        
    # @staticmethod
    # def ajustar_fechas_vencimiento(df: pd.DataFrame, fecha_proceso: datetime) -> pd.DataFrame:
        """
        Ajustar fechas de vencimiento según reglas de negocio
        
        Args:
            df: DataFrame con datos
            fecha_proceso: Fecha de proceso actual
            
        Returns:
            DataFrame con fechas ajustadas
        """
        print("      • Ajustando fechas de vencimiento...")
        
        def estandarizar_vencimiento(row):
            fv = row['FECHA_VENCIMIENTO_CUOTA']
            if fv < fecha_proceso:
                return fecha_proceso + pd.Timedelta(days=1)
            elif fv.year == fecha_proceso.year and fv.month == fecha_proceso.month:
                return fecha_proceso + pd.Timedelta(days=1)
            else:
                return fv.replace(day=5)
        
        df['FECHA_VENCIMIENTO_AJUSTADA'] = df.apply(estandarizar_vencimiento, axis=1)
        print(f"        - Ajuste de fechas completado")
        return df