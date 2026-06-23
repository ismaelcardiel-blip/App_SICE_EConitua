# --- MOTOR UPSERT INTELIGENTE POR CÓDIGO EC + CLAVE CURSO ---
def aplicar_upsert_maestro(df_google_sheets, df_nuevos_datos):
    df_base = df_google_sheets.copy()
    df_nuevos = df_nuevos_datos.copy()
    
    # CONSTRUCCIÓN DE LA LLAVE CORRECTA: Alumno + Evento
    for df in [df_base, df_nuevos]:
        if not df.empty:
            # Usamos Código EC (ID Alumno) y Clave Curso (o Programa si Clave viene vacía)
            df['id_control'] = (
                df['Código EC'].astype(str).str.strip().str.upper() + "_" + 
                df['Convocatoria_SICE'].astype(str).str.strip().str.upper()
            )
        else:
            df['id_control'] = pd.Series(dtype=str)
            
    # Eliminar duplicados históricos en la base por seguridad antes de comparar
    df_base.drop_duplicates(subset=['id_control'], keep='first', inplace=True)
    base_dict = df_base.set_index('id_control').to_dict(orient='index')
    
    contador_nuevos = 0
    contador_actualizados = 0
    
    for _, row in df_nuevos.iterrows():
        id_act = row['id_control']
        
        # Si el participante YA ESTÁ inscrito en este evento específico
        if id_act in base_dict:
            hubo_cambio = False
            for col in df_nuevos_datos.columns:
                if col != 'id_control':
                    val_sheets = str(base_dict[id_act].get(col, "S/I")).strip()
                    val_nuevo = str(row[col]).strip()
                    
                    # Rellenar solo si en la nube estaba vacío/SI y en el SI ya cayó el dato
                    if val_sheets in ["S/I", "", "nan", "None"] and val_nuevo not in ["S/I", "", "nan", "None"]:
                        base_dict[id_act][col] = row[col]
                        hubo_cambio = True
            if hubo_cambio:
                contador_actualizados += 1
        else:
            # Si es una inscripción nueva de ese alumno a ese curso, se agrega
            base_dict[id_act] = row.to_dict()
            contador_nuevos += 1
            
    df_final = pd.DataFrame.from_dict(base_dict, orient='index').reset_index(drop=True)
    if 'id_control' in df_final.columns:
        df_final.drop(columns=['id_control'], inplace=True)
        
    return df_final[df_nuevos_datos.columns.drop('id_control')], contador_nuevos, contador_actualizados
