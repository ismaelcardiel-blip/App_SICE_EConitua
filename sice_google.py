import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import re

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA (debe ser lo primero)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Unidad de Educación Continua",
    page_icon="🎓",
    layout="wide"
)

# ─────────────────────────────────────────────
# CONEXIÓN A GOOGLE SHEETS
# ─────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_google_sheets():
    """Retorna el cliente de gspread autenticado con saneamiento de llave."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Saneamiento preventivo de la llave privada
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
            
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Error al conectar con Google: {e}")
        st.code(traceback.format_exc())
        st.stop()

def obtener_spreadsheet(client, entrada_id_o_url):
    """
    Función adaptativa / Capa de abstracción:
    Determina si la entrada es una URL o un ID y abre el archivo correctamente.
    """
    entrada_limpia = entrada_id_o_url.strip()
    if "docs.google.com" in entrada_limpia:
        if not entrada_limpia.startswith("http"):
            entrada_limpia = "https://" + entrada_limpia
        return client.open_by_url(entrada_limpia)
    else:
        return client.open_by_key(entrada_limpia)

@st.cache_data(ttl=60)
def cargar_hoja(_client, spreadsheet_id: str, nombre_hoja: str) -> pd.DataFrame:
    """Lee la hoja de Google Sheets y retorna un DataFrame."""
    try:
        sh = obtener_spreadsheet(_client, spreadsheet_id)
        ws = sh.worksheet(nombre_hoja)
        datos = ws.get_all_records()
        return pd.DataFrame(datos)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ No se encontró la pestaña llamada '{nombre_hoja}' en el archivo.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al leer Google Sheets: {e}")
        st.code(traceback.format_exc())
        st.stop()

def subir_dataframe(client, spreadsheet_id: str, nombre_hoja: str, df: pd.DataFrame):
    """Reemplaza el contenido de la hoja con el DataFrame actualizado."""
    sh = obtener_spreadsheet(client, spreadsheet_id)
    ws = sh.worksheet(nombre_hoja)
    ws.clear()
    ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())

# ─────────────────────────────────────────────
# MOTOR UPSERT
# ─────────────────────────────────────────────
def aplicar_upsert_maestro(df_google_sheets, df_nuevos_datos):
    """
    Motor UPSERT por clave compuesta ternaria (Año-Mes): Código EC + Programa + Periodo Mensual.
    Retorna: (df_final, contador_nuevos, contador_actualizados)
    """
    # 1. ACTUALIZAMOS LAS COLUMNAS REQUERIDAS DE LA FUNCIÓN
    COLS_REQUERIDAS = ["Código EC", "Programa", "Fecha de Inscripción"]

    for col in COLS_REQUERIDAS:
        if col not in df_google_sheets.columns:
            raise ValueError(f"Columna requerida ausente en Google Sheets: '{col}'")
        if col not in df_nuevos_datos.columns:
            raise ValueError(f"Columna requerida ausente en archivo cargado: '{col}'")

    df_base   = df_google_sheets.copy()
    df_nuevos = df_nuevos_datos.copy()

    # 2. AQUÍ REEMPLAZAMOS TU FUNCIÓN CONSTRUIR_ID POR LA DE AÑO-MES
    def construir_id(df):
        # Extraemos estrictamente el Año y el Mes (YYYY-MM), ignorando días y horas
        periodo_mensual = (
            pd.to_datetime(df["Fecha de Inscripción"], dayfirst=True, errors='coerce')
            .dt.strftime('%Y-%m')
            .fillna(df["Fecha de Inscripción"].astype(str).str.strip().str.upper())
        )
        return (
            df["Código EC"].astype(str).str.strip().str.upper()
            + "_"
            + df["Programa"].astype(str).str.strip().str.upper()
            + "_"
            + periodo_mensual
        )

    df_base["id_control"]   = construir_id(df_base)   if not df_base.empty   else ""
    df_nuevos["id_control"] = construir_id(df_nuevos) if not df_nuevos.empty else ""

    df_base   = df_base.drop_duplicates(subset=["id_control"], keep="first")
    base_dict = df_base.set_index("id_control").to_dict(orient="index")

    VALORES_VACIOS    = {"S/I", "", "nan", "None", "none", "NaN"}
    contador_nuevos   = 0
    contador_actualizados = 0
    cols_datos = [c for c in df_nuevos_datos.columns if c != "id_control"]

    for _, row in df_nuevos.iterrows():
        id_act = row["id_control"]
        if not id_act:
            continue

        if id_act in base_dict:
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
            base_dict[id_act] = row.to_dict()
            contador_nuevos   += 1

    if not base_dict:
        return pd.DataFrame(columns=cols_datos), 0, 0

    df_final    = pd.DataFrame.from_dict(base_dict, orient="index").reset_index(drop=True)
    cols_salida = [c for c in cols_datos if c in df_final.columns]
    return df_final[cols_salida], contador_nuevos, contador_actualizados

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎓 Unidad de Educación Continua")
st.caption("Portal de carga y actualización de participantes")

# ── Sidebar: configuración ──
with st.sidebar:
    st.header("⚙️ Configuración")
    spreadsheet_id = st.text_input(
        "ID del Google Sheet",
        help="Es la parte larga en la URL: docs.google.com/spreadsheets/d/ESTE_ID/edit"
    )
    nombre_hoja = st.text_input("Nombre de la hoja", value="Base_Datos")
    st.divider()
    st.caption("Los cambios se aplican sobre la hoja indicada.")

if not spreadsheet_id:
    st.info("👈 Ingresa el ID de tu Google Sheet en el panel lateral para comenzar.")
    st.stop()

# ── Cargar datos actuales de Sheets ──
client = conectar_google_sheets()

with st.spinner("Leyendo base de datos en Google Sheets..."):
    df_sheets = cargar_hoja(client, spreadsheet_id, nombre_hoja)

st.subheader("📋 Base de datos actual")
st.caption(f"{len(df_sheets):,} registros en Google Sheets")
st.dataframe(df_sheets, use_container_width=True, hide_index=True)

st.divider()

# ── Cargar archivo nuevo ──
st.subheader("📂 Cargar nuevos participantes")
archivo = st.file_uploader(
    "Sube un archivo Excel (.xlsx) o CSV (.csv)",
    type=["xlsx", "csv"]
)

if archivo:
    try:
        if archivo.name.endswith(".csv"):
            df_nuevo = pd.read_csv(archivo)
        else:
            df_nuevo = pd.read_excel(archivo, engine="openpyxl")
        
        # ── CAPA DE NORMALIZACIÓN DE COLUMNAS ──
        # 1. Limpieza de espacios y formateo inicial de guiones bajos
        df_nuevo.columns = (
            df_nuevo.columns
            .astype(str)
            .str.strip()
            .str.replace(" ", "_")
        )
        
        # 2. Corrección selectiva: Forzamos la nomenclatura exacta
        columnas_mapeo = {
            "programa": "Programa",
            "PROGRAMA": "Programa",
            "codigo_ec": "Código EC",
            "CÓDIGO_EC": "Código EC",
            "Código_EC": "Código EC"
        }
        df_nuevo.rename(columns=columnas_mapeo, inplace=True)

    except Exception as e:
        st.error(f"❌ No se pudo leer el archivo: {e}")
        st.code(traceback.format_exc())
        st.stop()

    st.write(f"**Vista previa del archivo** — {len(df_nuevo):,} filas")
    st.dataframe(df_nuevo, use_container_width=True, hide_index=True)

    # Verificar columnas mínimas obligatorias
    cols_faltantes = [c for c in ["Código EC", "Programa"] if c not in df_nuevo.columns]
    if cols_faltantes:
        st.error(f"❌ El archivo no tiene las columnas requeridas: {cols_faltantes}")
        st.stop()

    st.divider()

    col1, col2 = st.columns([1, 3])
    with col1:
        confirmar = st.button("✅ Aplicar actualización", type="primary", use_container_width=True)

    if confirmar:
        with st.spinner("Procesando upsert..."):
            try:
                df_final, nuevos, actualizados = aplicar_upsert_maestro(df_sheets, df_nuevo)
                subir_dataframe(client, spreadsheet_id, nombre_hoja, df_final)
                cargar_hoja.clear()
            except ValueError as e:
                st.error(f"❌ {e}")
                st.stop()
            except Exception as e:
                st.error(f"❌ Error al subir datos: {e}")
                st.code(traceback.format_exc())
                st.stop()

        st.success("✅ Base de datos actualizada correctamente")
        m1, m2, m3 = st.columns(3)
        m1.metric("Registros nuevos",       nuevos)
        m2.metric("Registros actualizados", actualizados)
        m3.metric("Total en Sheets",        len(df_final))

        st.subheader("📋 Base de datos actualizada")
        st.dataframe(df_final, use_container_width=True, hide_index=True)
