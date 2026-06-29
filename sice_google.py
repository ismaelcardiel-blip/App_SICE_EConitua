import streamlit as st
import traceback

try:
    def aplicar_upsert_maestro(df_google_sheets, df_nuevos_datos):
    """
    Motor UPSERT por clave compuesta: Código EC + Convocatoria_SICE.
    Retorna: (df_final, contador_nuevos, contador_actualizados)
    """
    COLS_REQUERIDAS = ['Código EC', 'Convocatoria_SICE']
    
    # --- Validación defensiva de columnas requeridas ---
    for col in COLS_REQUERIDAS:
        if col not in df_google_sheets.columns:
            raise ValueError(f"Columna requerida ausente en Google Sheets: '{col}'")
        if col not in df_nuevos_datos.columns:
            raise ValueError(f"Columna requerida ausente en datos nuevos: '{col}'")

    df_base  = df_google_sheets.copy()
    df_nuevos = df_nuevos_datos.copy()

    # --- Construcción de la clave de control ---
    def construir_id(df):
        return (
            df['Código EC'].astype(str).str.strip().str.upper()
            + "_"
            + df['Convocatoria_SICE'].astype(str).str.strip().str.upper()
        )

    df_base['id_control']   = construir_id(df_base)   if not df_base.empty   else ""
    df_nuevos['id_control'] = construir_id(df_nuevos) if not df_nuevos.empty else ""

    # --- Deduplicar base (sin inplace sobre copia) ---
    df_base = df_base.drop_duplicates(subset=['id_control'], keep='first')
    base_dict = df_base.set_index('id_control').to_dict(orient='index')

    VALORES_VACIOS = {"S/I", "", "nan", "None", "none", "NaN"}
    contador_nuevos      = 0
    contador_actualizados = 0

    # --- Columnas a comparar (excluye id_control) ---
    cols_datos = [c for c in df_nuevos_datos.columns if c != 'id_control']

    for _, row in df_nuevos.iterrows():
        id_act = row['id_control']
        if not id_act:          # fila con clave vacía → saltar
            continue

        if id_act in base_dict:
            # UPDATE: rellenar solo campos vacíos/S/I en la base
            hubo_cambio = False
            for col in cols_datos:
                val_sheets = str(base_dict[id_act].get(col, "S/I")).strip()
                val_nuevo  = str(row.get(col, "")).strip()

                if val_sheets in VALORES_VACIOS and val_nuevo not in VALORES_VACIOS:
                    base_dict[id_act][col] = row[col]
                    hubo_cambio = True

            if hubo_cambio:
                contador_actualizados += 1
        else:
            # INSERT: inscripción nueva
            base_dict[id_act] = row.to_dict()
            contador_nuevos += 1

    # --- Reconstruir DataFrame final ---
    if not base_dict:
        return pd.DataFrame(columns=cols_datos), 0, 0

    df_final = pd.DataFrame.from_dict(base_dict, orient='index').reset_index(drop=True)

    # Eliminar id_control del resultado final de forma segura
    cols_salida = [c for c in cols_datos if c in df_final.columns]
    return df_final[cols_salida], contador_nuevos, contador_actualizados
     pass
except Exception as e:
    st.error(f"💥 Error capturado: {e}")
    st.code(traceback.format_exc())
