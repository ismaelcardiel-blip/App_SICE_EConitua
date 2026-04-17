import streamlit as st
import pandas as pd
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Información Concentrada y Estadística (SICE) EContinua", layout="wide")

# --- CONEXIÓN A GOOGLE (MODIFICADA PARA NUBE) ---
def conectar_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 1. Cargamos el diccionario desde los secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. LIMPIEZA EXTREMA de la llave privada
        # Esto quita espacios accidentales y asegura que los saltos de línea sean reales
        raw_key = creds_dict["private_key"]
        
        # Primero quitamos espacios al inicio y fin
        clean_key = raw_key.strip()
        
        # Si Streamlit guardó los \n como texto literal, los convertimos a saltos reales
        if "\\n" in clean_key:
            clean_key = clean_key.replace("\\n", "\n")
            
        creds_dict["private_key"] = clean_key
        
        # 3. Autorizar
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("SICE_Base_Maestra").sheet1
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- MOTOR DE EDAD REGLA DE ORO (v5.5) ---
def procesar_edad_v55(valor):
    if pd.isna(valor) or str(valor).strip().lower() in ["s/i", "nan", "", "none", "nanb"]:
        return "S/I"
    
    v_str = str(valor).strip().upper()
    try:
        numeros = re.findall(r'\d+', v_str)
        if not numeros: return "S/I"
        
        for num in numeros:
            n = int(num)
            if 1920 <= n <= 2026:
                if n > 100: return 2026 - n
        
        for num in numeros:
            n = int(num)
            if 10 <= n <= 100: return n
                
        return "S/I"
    except:
        return "S/I"

# --- GENERADOR DE CLAVES ---
def generar_clave_curso(nombre_curso):
    nombre_str = str(nombre_curso).upper()
    if "CONSENTIMIENTO" in nombre_str and "SEXUAL" in nombre_str: return "COSEX"
    nombre = re.sub(r'[^\w\s]', '', nombre_str)
    palabras = [p for p in nombre.split() if p not in ['DE', 'LA', 'EL', 'Y', 'EN', 'QUE', 'PARA', 'CON']]
    if len(palabras) >= 2: return palabras[0][:2] + palabras[1][:2]
    return palabras[0][:4] if palabras else "GEN"

# --- LAVANDERÍA v5.5 (SIN DUPLICADOS) ---
def lavanderia_v55(df, nombre_archivo, p_manual, f_manual):
    mapeo = {
        'Nombre': ['nombre', 'participante', 'alumno'],
        'Sexo': ['sexo', 'género', 'genero'],
        'Edad_Raw': ['edad', 'f.nac', 'nacimiento', 'años'], 
        'Regional': ['estado', 'ciudad', 'zona', 'regional'],
        'Programa_Archivo': ['programa', 'curso', 'convocatoria'],
        'Correo': ['correo', 'email', 'mail']
    }
    
    temp_df = pd.DataFrame()
    
    for estandar, sinonimos in mapeo.items():
        col_encontrada = None
        for s in sinonimos:
            col_encontrada = next((c for c in df.columns if s in str(c).lower() 
                                  and "registro" not in str(c).lower()
                                  and "antigüedad" not in str(c).lower()
                                  and "antiguedad" not in str(c).lower()), None)
            if col_encontrada: break
        
        temp_df[estandar] = df[col_encontrada] if col_encontrada else "S/I"

    temp_df['Convocatoria'] = p_manual if p_manual else temp_df['Programa_Archivo'].replace("S/I", "General")
    temp_df['count'] = temp_df.groupby('Convocatoria').cumcount() + 1
    
    folios = []
    for _, row in temp_df.iterrows():
        clave = f_manual.upper() if f_manual else generar_clave_curso(row['Convocatoria'])
        folios.append(f"2026-{clave}-{str(row['count']).zfill(4)}")
    
    temp_df['Folio'] = folios
    temp_df['Año'] = 2026
    temp_df['Edad_Final'] = temp_df['Edad_Raw'].apply(procesar_edad_v55)
    temp_df['Sexo_Final'] = temp_df['Sexo'].apply(lambda v: 'Mujer' if 'fem' in str(v).lower() or 'muj' in str(v).lower() else ('Hombre' if 'masc' in str(v).lower() or 'hom' in str(v).lower() else 'S/I'))
    temp_df['Fuente_Origen'] = nombre_archivo

    cols_finales = ['Folio', 'Año', 'Convocatoria', 'Nombre', 'Sexo_Final', 'Edad_Final', 'Regional', 'Correo', 'Fuente_Origen']
    res = temp_df[cols_finales].rename(columns={'Sexo_Final': 'Sexo', 'Edad_Final': 'Edad'})
    
    return res.fillna("S/I").replace(['nan', 'NaN', 'None', 'nanb', ''], "S/I")

# --- INTERFAZ ---
st.title("🏛️ SICE v5.5 Cloud")
st.sidebar.header("Opciones")
p_mod = st.sidebar.radio("Programa:", ["Auto", "Manual"])
p_val = st.sidebar.text_input("Nombre curso:") if p_mod == "Manual" else ""
f_mod = st.sidebar.radio("Prefijo Folio:", ["Auto", "Manual"])
f_val = st.sidebar.text_input("Ej: BACH") if f_mod == "Manual" else ""

archivo = st.file_uploader("📂 Sube tu Excel o CSV", type=['xlsx', 'xls', 'csv'])

if archivo:
    try:
        df_in = pd.read_excel(archivo) if archivo.name.endswith(('xlsx', 'xls')) else pd.read_csv(archivo)
        df_out = lavanderia_v55(df_in, archivo.name, p_val, f_val)
        
        st.dataframe(df_out, use_container_width=True)
        
        if st.button("🚀 Enviar a Google Sheets"):
            with st.spinner("Subiendo..."):
                hoja = conectar_google_sheets()
                if hoja:
                    hoja.append_rows(df_out.astype(str).values.tolist())
                    st.success("¡Datos enviados correctamente!")
                    st.balloons()
    except Exception as e:
        st.error(f"Error: {e}")
