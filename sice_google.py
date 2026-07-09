import re
import traceback
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


st.set_page_config(
    page_title="SICE Educacion Continua",
    page_icon="SICE",
    layout="wide",
)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MASTER_COLUMNS = [
    "Código EC",
    "CURP",
    "Nombre",
    "Paterno",
    "Materno",
    "Correo",
    "Sexo",
    "Fecha Nacimiento",
    "Discapacidad",
    "Comunidad Indígena",
    "Lengua Indígena",
    "Municipio",
    "Estado",
    "País",
    "Código Postal",
    "Teléfono",
    "Institución donde trabaja",
    "Cargo",
    "Sector Empleo",
    "Subsector Empleo",
    "Tipo Organización",
    "Jerarquía Empleo",
    "Grado Estudios",
    "Institución Graduó",
    "Estudiante UDGVirtual",
    "Cómo se enteró",
    "Fecha de Inscripción",
    "Clave Grupo",
    "Clave Curso",
    "Programa",
    "Asesor",
    "Fecha Pago 1",
    "Cantidad Pago 1",
    "Descuento Pago 1",
    "Beca Pago 1",
    "Factura Pago 1",
    "Fecha Pago 2",
    "Cantidad Pago 2",
    "Descuento Pago 2",
    "Beca Pago 2",
    "Factura Pago 2",
    "Fecha Pago 3",
    "Cantidad Pago 3",
    "Descuento Pago 3",
    "Beca Pago 3",
    "Factura Pago 3",
    "Título Incidencia 1",
    "Fecha Incidencia 1",
    "Título Incidencia 2",
    "Fecha Incidencia 2",
    "Título Incidencia 3",
    "Fecha Incidencia 3",
]

CONTROL_COLUMNS = [
    "Origen de carga",
    "Tipo de grupo",
    "Fecha inicio curso",
    "Llave participante",
    "Llave curso",
    "Llave registro",
    "Estatus validación",
    "Observaciones validación",
    "Fecha carga",
]

OUTPUT_COLUMNS = MASTER_COLUMNS + CONTROL_COLUMNS

COLUMN_ALIASES = {
    "codigo ec": "Código EC",
    "codigo": "Código EC",
    "curp": "CURP",
    "nombre": "Nombre",
    "nombres": "Nombre",
    "paterno": "Paterno",
    "apellido paterno": "Paterno",
    "materno": "Materno",
    "apellido materno": "Materno",
    "correo": "Correo",
    "correo electronico": "Correo",
    "email": "Correo",
    "sexo": "Sexo",
    "fecha nacimiento": "Fecha Nacimiento",
    "fecha de nacimiento": "Fecha Nacimiento",
    "discapacidad": "Discapacidad",
    "comunidad indigena": "Comunidad Indígena",
    "lengua indigena": "Lengua Indígena",
    "municipio": "Municipio",
    "ciudad": "Municipio",
    "estado": "Estado",
    "pais": "País",
    "codigo postal": "Código Postal",
    "telefono": "Teléfono",
    "telefono movil": "Teléfono",
    "telefono particular": "Teléfono",
    "institucion donde trabaja": "Institución donde trabaja",
    "cargo": "Cargo",
    "sector empleo": "Sector Empleo",
    "subsector empleo": "Subsector Empleo",
    "tipo organizacion": "Tipo Organización",
    "jerarquia empleo": "Jerarquía Empleo",
    "grado estudios": "Grado Estudios",
    "ultimo grado de estudios": "Grado Estudios",
    "institucion graduo": "Institución Graduó",
    "institucion de donde se graduo": "Institución Graduó",
    "estudiante udgvirtual": "Estudiante UDGVirtual",
    "ya ha estudiado en udgplus": "Estudiante UDGVirtual",
    "como se entero": "Cómo se enteró",
    "como se entero del evento": "Cómo se enteró",
    "fecha de inscripcion": "Fecha de Inscripción",
    "fecha inscripcion": "Fecha de Inscripción",
    "fecha registro": "Fecha de Inscripción",
    "clave grupo": "Clave Grupo",
    "clave curso": "Clave Curso",
    "programa": "Programa",
    "convocatoria": "Programa",
    "curso": "Programa",
    "asesor": "Asesor",
    "fecha pago 1": "Fecha Pago 1",
    "cantidad pago 1": "Cantidad Pago 1",
    "descuento pago 1": "Descuento Pago 1",
    "beca pago 1": "Beca Pago 1",
    "factura pago 1": "Factura Pago 1",
    "fecha pago 2": "Fecha Pago 2",
    "cantidad pago 2": "Cantidad Pago 2",
    "descuento pago 2": "Descuento Pago 2",
    "beca pago 2": "Beca Pago 2",
    "factura pago 2": "Factura Pago 2",
    "fecha pago 3": "Fecha Pago 3",
    "cantidad pago 3": "Cantidad Pago 3",
    "descuento pago 3": "Descuento Pago 3",
    "beca pago 3": "Beca Pago 3",
    "factura pago 3": "Factura Pago 3",
    "titulo incidencia 1": "Título Incidencia 1",
    "fecha incidencia 1": "Fecha Incidencia 1",
    "titulo incidencia 2": "Título Incidencia 2",
    "fecha incidencia 2": "Fecha Incidencia 2",
    "titulo incidencia 3": "Título Incidencia 3",
    "fecha incidencia 3": "Fecha Incidencia 3",
}

MONTHS_2026 = {
    "ENE": 1,
    "ENERO": 1,
    "FEB": 2,
    "FEBRERO": 2,
    "MAR": 3,
    "MARZO": 3,
    "ABR": 4,
    "ABRIL": 4,
    "MAY": 5,
    "MAYO": 5,
    "JUN": 6,
    "JUNIO": 6,
    "JUL": 7,
    "JULIO": 7,
    "AGO": 8,
    "AGOSTO": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTIEMBRE": 9,
    "OCT": 10,
    "OCTUBRE": 10,
    "NOV": 11,
    "NOVIEMBRE": 11,
    "DIC": 12,
    "DICIEMBRE": 12,
}

EMPTY_VALUES = {
    "",
    "S I",
    "SI",
    "NO APLICA",
    "N A",
    "NA",
    "NAN",
    "NONE",
    "NULL",
}
DATE_COLUMNS = [
    "Fecha Nacimiento",
    "Fecha de Inscripción",
    "Fecha Pago 1",
    "Fecha Pago 2",
    "Fecha Pago 3",
    "Fecha Incidencia 1",
    "Fecha Incidencia 2",
    "Fecha Incidencia 3",
    "Fecha inicio curso",
]
IDENTIFIER_COLUMNS = ["Código EC", "CURP", "Código Postal", "Teléfono", "Clave Grupo", "Clave Curso"]


@st.cache_resource
def conectar_google_sheets():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as exc:
        st.error(f"No se pudo conectar con Google Sheets: {exc}")
        st.code(traceback.format_exc())
        st.stop()


def obtener_spreadsheet(client, entrada_id_o_url):
    entrada = entrada_id_o_url.strip()
    if "docs.google.com" in entrada:
        if not entrada.startswith("http"):
            entrada = "https://" + entrada
        return client.open_by_url(entrada)
    return client.open_by_key(entrada)


def obtener_o_crear_worksheet(sh, nombre_hoja):
    try:
        return sh.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return sh.add_worksheet(title=nombre_hoja, rows=1000, cols=len(OUTPUT_COLUMNS))


@st.cache_data(ttl=60)
def cargar_hoja(_client, spreadsheet_id, nombre_hoja):
    sh = obtener_spreadsheet(_client, spreadsheet_id)
    ws = obtener_o_crear_worksheet(sh, nombre_hoja)
    datos = ws.get_all_records()
    if not datos:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.DataFrame(datos)


def subir_dataframe(client, spreadsheet_id, nombre_hoja, df):
    sh = obtener_spreadsheet(client, spreadsheet_id)
    ws = obtener_o_crear_worksheet(sh, nombre_hoja)
    salida = ordenar_columnas(df).fillna("").astype(str)
    ws.clear()
    ws.update([salida.columns.tolist()] + salida.values.tolist())


def quitar_acentos(texto):
    normal = unicodedata.normalize("NFKD", str(texto))
    return "".join(ch for ch in normal if not unicodedata.combining(ch))


def limpiar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).replace("\n", " ").replace("\r", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    if texto.endswith(".0") and texto.replace(".", "", 1).isdigit():
        texto = texto[:-2]
    return texto


def normalizar_token(valor):
    texto = quitar_acentos(limpiar_texto(valor)).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def canonical_header(columna):
    token = normalizar_token(columna)
    return COLUMN_ALIASES.get(token, limpiar_texto(columna))


def valor_vacio(valor):
    texto = normalizar_token(valor).upper()
    return texto in EMPTY_VALUES


def limpiar_identificador(valor):
    if pd.isna(valor):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    texto = limpiar_texto(valor)
    if not texto:
        return ""
    try:
        decimal = Decimal(texto)
        if decimal == decimal.to_integral():
            return str(decimal.to_integral())
    except (InvalidOperation, ValueError):
        pass
    texto = re.sub(r"\.0$", "", texto)
    texto = re.sub(r"\s+", "", texto)
    return texto


def convertir_fecha(valor):
    if pd.isna(valor) or limpiar_texto(valor) == "":
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 20000 <= float(valor) <= 80000:
            fecha = pd.to_datetime(valor, unit="D", origin="1899-12-30", errors="coerce")
            return "" if pd.isna(fecha) else fecha.strftime("%Y-%m-%d")
    texto = limpiar_texto(valor)
    if re.fullmatch(r"\d+(\.\d+)?", texto):
        numero = float(texto)
        if 20000 <= numero <= 80000:
            fecha = pd.to_datetime(numero, unit="D", origin="1899-12-30", errors="coerce")
            return "" if pd.isna(fecha) else fecha.strftime("%Y-%m-%d")
    fecha = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    return texto if pd.isna(fecha) else fecha.strftime("%Y-%m-%d")


def leer_archivo(archivo):
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo, engine="openpyxl")


def unir_columnas_duplicadas(df):
    columnas = []
    for col in df.columns:
        if col not in columnas:
            columnas.append(col)

    salida = pd.DataFrame()
    for col in columnas:
        bloque = df.loc[:, df.columns == col]
        if bloque.shape[1] == 1:
            salida[col] = bloque.iloc[:, 0]
        else:
            salida[col] = bloque.bfill(axis=1).iloc[:, 0]
    return salida


def homologar_dataframe(df_raw, origen, tipo_grupo):
    df = df_raw.copy()
    df = df.dropna(how="all")
    df.columns = [canonical_header(col) for col in df.columns]
    df = unir_columnas_duplicadas(df)

    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    for col in IDENTIFIER_COLUMNS:
        df[col] = df[col].map(limpiar_identificador)

    for col in DATE_COLUMNS:
        df[col] = df[col].map(convertir_fecha)

    for col in df.columns:
        if col not in DATE_COLUMNS and col not in IDENTIFIER_COLUMNS:
            df[col] = df[col].map(limpiar_texto)

    df["Origen de carga"] = origen
    df["Tipo de grupo"] = tipo_grupo
    df["Fecha carga"] = pd.Timestamp.now(tz="America/Mexico_City").strftime("%Y-%m-%d %H:%M:%S")
    df = construir_llaves(df)
    df = validar_registros(df)
    return ordenar_columnas(df)


def ordenar_columnas(df):
    salida = df.copy()
    for col in OUTPUT_COLUMNS:
        if col not in salida.columns:
            salida[col] = ""
    extras = [col for col in salida.columns if col not in OUTPUT_COLUMNS]
    return salida[OUTPUT_COLUMNS + extras]


def nombre_completo(row):
    partes = [row.get("Nombre", ""), row.get("Paterno", ""), row.get("Materno", "")]
    return " ".join(limpiar_texto(p) for p in partes if limpiar_texto(p))


def construir_llaves(df):
    salida = df.copy()
    participante = []
    curso = []
    registro = []

    for _, row in salida.iterrows():
        curp = normalizar_token(row.get("CURP", "")).upper()
        correo = normalizar_token(row.get("Correo", "")).upper()
        telefono = limpiar_identificador(row.get("Teléfono", ""))
        nombre = normalizar_token(nombre_completo(row)).upper()

        if curp:
            llave_participante = f"CURP:{curp}"
        elif correo:
            llave_participante = f"CORREO:{correo}"
        elif nombre and telefono:
            llave_participante = f"NOMBRE_TEL:{nombre}:{telefono}"
        elif nombre:
            llave_participante = f"NOMBRE:{nombre}"
        else:
            llave_participante = ""

        codigo = normalizar_token(row.get("Código EC", "")).upper()
        clave_curso = normalizar_token(row.get("Clave Curso", "")).upper()
        programa = normalizar_token(row.get("Programa", "")).upper()
        inicio = limpiar_texto(row.get("Fecha inicio curso", ""))
        inscripcion = limpiar_texto(row.get("Fecha de Inscripción", ""))

        if codigo:
            llave_curso = f"CODIGO_EC:{codigo}"
        elif clave_curso:
            llave_curso = f"CLAVE_CURSO:{clave_curso}"
        elif programa and inicio:
            llave_curso = f"PROGRAMA_INICIO:{programa}:{inicio}"
        elif programa and inscripcion:
            llave_curso = f"PROGRAMA_FECHA:{programa}:{inscripcion}"
        elif programa:
            llave_curso = f"PROGRAMA:{programa}"
        else:
            llave_curso = ""

        llave_registro = f"{llave_participante}|{llave_curso}" if llave_participante and llave_curso else ""
        participante.append(llave_participante)
        curso.append(llave_curso)
        registro.append(llave_registro)

    salida["Llave participante"] = participante
    salida["Llave curso"] = curso
    salida["Llave registro"] = registro
    return salida


def validar_registros(df):
    salida = df.copy()
    observaciones = []
    estatus = []

    for _, row in salida.iterrows():
        obs = []
        if not limpiar_texto(row.get("Llave participante", "")):
            obs.append("Sin CURP, correo o nombre suficiente para identificar participante")
        if not limpiar_texto(row.get("Programa", "")):
            obs.append("Sin programa")
        if not limpiar_texto(row.get("Fecha de Inscripción", "")):
            obs.append("Sin fecha de inscripción/registro")
        if not limpiar_texto(row.get("Llave registro", "")):
            obs.append("Sin llave de registro")
        observaciones.append("; ".join(obs))
        estatus.append("Revisar" if obs else "OK")

    salida["Observaciones validación"] = observaciones
    salida["Estatus validación"] = estatus
    return salida


def normalizar_cartelera(df_raw, anio):
    df = df_raw.copy().dropna(how="all")
    if df.empty:
        return pd.DataFrame(columns=["Programa", "Fecha inicio curso", "Mes cartelera"])

    primera_columna = df.columns[0]
    filas = []
    for _, row in df.iterrows():
        programa = limpiar_texto(row.get(primera_columna, ""))
        if not programa:
            continue
        for col in df.columns[1:]:
            mes = MONTHS_2026.get(normalizar_token(col).upper())
            if not mes:
                continue
            dia_raw = row.get(col, "")
            if pd.isna(dia_raw) or limpiar_texto(dia_raw) == "":
                continue
            try:
                dia = int(float(dia_raw))
                fecha = pd.Timestamp(year=int(anio), month=mes, day=dia)
            except (TypeError, ValueError):
                continue
            filas.append(
                {
                    "Programa": programa,
                    "Programa normalizado": normalizar_token(programa),
                    "Fecha inicio curso": fecha.strftime("%Y-%m-%d"),
                    "Mes cartelera": fecha.strftime("%Y-%m"),
                }
            )
    return pd.DataFrame(filas)


def asignar_fecha_cartelera(df, cartelera, tolerancia_dias):
    if cartelera is None or cartelera.empty:
        return df

    salida = df.copy()
    salida["Fecha inicio curso"] = salida["Fecha inicio curso"].map(limpiar_texto)
    cartelera = cartelera.copy()
    cartelera["fecha_dt"] = pd.to_datetime(cartelera["Fecha inicio curso"], errors="coerce")
    cartelera = cartelera.dropna(subset=["fecha_dt"])

    fechas_asignadas = []
    for _, row in salida.iterrows():
        actual = limpiar_texto(row.get("Fecha inicio curso", ""))
        if actual:
            fechas_asignadas.append(actual)
            continue

        programa = normalizar_token(row.get("Programa", ""))
        fecha_registro = pd.to_datetime(row.get("Fecha de Inscripción", ""), errors="coerce")
        opciones = cartelera[cartelera["Programa normalizado"] == programa].copy()
        if opciones.empty or pd.isna(fecha_registro):
            fechas_asignadas.append("")
            continue

        opciones["distancia"] = (opciones["fecha_dt"] - fecha_registro).dt.days
        futuras = opciones[(opciones["distancia"] >= 0) & (opciones["distancia"] <= tolerancia_dias)]
        if not futuras.empty:
            elegida = futuras.sort_values("distancia").iloc[0]
        else:
            opciones["distancia_abs"] = opciones["distancia"].abs()
            cercanas = opciones[opciones["distancia_abs"] <= tolerancia_dias]
            if cercanas.empty:
                fechas_asignadas.append("")
                continue
            elegida = cercanas.sort_values("distancia_abs").iloc[0]
        fechas_asignadas.append(elegida["Fecha inicio curso"])

    salida["Fecha inicio curso"] = fechas_asignadas
    salida = construir_llaves(salida)
    salida = validar_registros(salida)
    return salida


def aplicar_upsert_maestro(df_base_raw, df_nuevos_raw):
    df_base = homologar_base_existente(df_base_raw)
    df_nuevos = homologar_base_existente(df_nuevos_raw)

    if df_base.empty:
        base_dict = {}
        base_sin_llave = pd.DataFrame(columns=OUTPUT_COLUMNS)
    else:
        con_llave = df_base["Llave registro"].map(limpiar_texto) != ""
        base_sin_llave = df_base[~con_llave].copy()
        df_base = df_base[con_llave].drop_duplicates(subset=["Llave registro"], keep="first")
        base_dict = df_base.set_index("Llave registro").to_dict(orient="index")

    nuevos = 0
    actualizados = 0
    omitidos = 0

    for _, row in df_nuevos.iterrows():
        llave = limpiar_texto(row.get("Llave registro", ""))
        if not llave:
            omitidos += 1
            continue

        datos = row.to_dict()
        if llave not in base_dict:
            base_dict[llave] = datos
            nuevos += 1
            continue

        cambio = False
        for col, valor_nuevo in datos.items():
            if col == "Llave registro":
                continue
            valor_actual = base_dict[llave].get(col, "")
            if valor_vacio(valor_actual) and not valor_vacio(valor_nuevo):
                base_dict[llave][col] = valor_nuevo
                cambio = True
        if cambio:
            actualizados += 1

    if not base_dict:
        return ordenar_columnas(base_sin_llave), nuevos, actualizados, omitidos

    df_final = pd.DataFrame.from_dict(base_dict, orient="index").reset_index(drop=True)
    if not base_sin_llave.empty:
        df_final = pd.concat([base_sin_llave, df_final], ignore_index=True)
    df_final = ordenar_columnas(df_final)
    con_llave_final = df_final["Llave registro"].map(limpiar_texto) != ""
    df_final = pd.concat(
        [
            df_final[~con_llave_final],
            df_final[con_llave_final].drop_duplicates(subset=["Llave registro"], keep="first"),
        ],
        ignore_index=True,
    )
    return df_final, nuevos, actualizados, omitidos


def homologar_base_existente(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    salida = df.copy()
    salida.columns = [canonical_header(col) for col in salida.columns]
    salida = unir_columnas_duplicadas(salida)
    for col in OUTPUT_COLUMNS:
        if col not in salida.columns:
            salida[col] = ""
    for col in IDENTIFIER_COLUMNS:
        salida[col] = salida[col].map(limpiar_identificador)
    for col in DATE_COLUMNS:
        salida[col] = salida[col].map(convertir_fecha)
    salida = construir_llaves(salida)
    salida = validar_registros(salida)
    return ordenar_columnas(salida)


def resumen_calidad(df):
    total = len(df)
    sin_llave = int((df["Llave registro"].map(limpiar_texto) == "").sum()) if total else 0
    duplicados = int(df.duplicated(subset=["Llave registro"]).sum()) if total and "Llave registro" in df else 0
    revisar = int((df["Estatus validación"] == "Revisar").sum()) if total else 0
    return total, duplicados, revisar, sin_llave


st.title("SICE Educacion Continua")
st.caption("Carga, homologacion y actualizacion de la base maestra de participantes")

with st.sidebar:
    st.header("Conexion")
    spreadsheet_id = st.text_input(
        "ID o URL del Google Sheet",
        help="Puedes pegar el ID o la URL completa de Google Sheets.",
    )
    nombre_hoja = st.text_input("Hoja de base maestra", value="Base_Datos")
    st.divider()
    st.header("Carga")
    origen = st.selectbox(
        "Tipo de archivo",
        [
            "SII - reporte descargado",
            "Matriculados / grupo cerrado",
            "Base maestra historica",
            "Otro formato",
        ],
    )
    tipo_grupo = st.selectbox("Tipo de grupo", ["Abierto", "Cerrado", "Mixto / revisar"])
    anio_cartelera = st.number_input("Año de cartelera", min_value=2020, max_value=2035, value=2026)
    tolerancia_dias = st.slider("Tolerancia para empatar cartelera", 0, 90, 45)

if not spreadsheet_id:
    st.info("Ingresa el ID o URL del Google Sheet para comenzar.")
    st.stop()

client = conectar_google_sheets()

with st.spinner("Leyendo base maestra en Google Sheets..."):
    df_sheets = cargar_hoja(client, spreadsheet_id, nombre_hoja)
    df_sheets = homologar_base_existente(df_sheets)

st.subheader("Base maestra actual")
m1, m2, m3, m4 = st.columns(4)
total, duplicados, revisar, sin_llave = resumen_calidad(df_sheets)
m1.metric("Registros", total)
m2.metric("Duplicados por llave", duplicados)
m3.metric("Por revisar", revisar)
m4.metric("Sin llave", sin_llave)
st.dataframe(df_sheets, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Cartelera de cursos")
archivo_cartelera = st.file_uploader(
    "Opcional: sube Fechas de cartelera.xlsx para asignar fecha de inicio",
    type=["xlsx", "csv"],
    key="cartelera",
)

cartelera = pd.DataFrame()
if archivo_cartelera:
    try:
        cartelera_raw = leer_archivo(archivo_cartelera)
        cartelera = normalizar_cartelera(cartelera_raw, anio_cartelera)
        st.caption(f"{len(cartelera):,} fechas de inicio detectadas")
        st.dataframe(cartelera, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"No se pudo leer la cartelera: {exc}")
        st.code(traceback.format_exc())
        st.stop()
else:
    st.caption("Si no subes cartelera, la app conserva las fechas que ya vengan en el archivo.")

st.divider()
st.subheader("Cargar participantes")
archivo = st.file_uploader("Sube archivo Excel o CSV", type=["xlsx", "csv"], key="participantes")

if archivo:
    try:
        df_raw = leer_archivo(archivo)
        df_nuevo = homologar_dataframe(df_raw, origen=origen, tipo_grupo=tipo_grupo)
        if not cartelera.empty:
            df_nuevo = asignar_fecha_cartelera(df_nuevo, cartelera, tolerancia_dias)
    except Exception as exc:
        st.error(f"No se pudo procesar el archivo: {exc}")
        st.code(traceback.format_exc())
        st.stop()

    st.write(f"Vista previa del archivo normalizado: {len(df_nuevo):,} filas")
    n_total, n_duplicados, n_revisar, n_sin_llave = resumen_calidad(df_nuevo)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas detectadas", n_total)
    c2.metric("Duplicados internos", n_duplicados)
    c3.metric("Por revisar", n_revisar)
    c4.metric("Sin llave", n_sin_llave)

    st.dataframe(df_nuevo, use_container_width=True, hide_index=True)

    if n_revisar:
        with st.expander("Registros que requieren revision"):
            columnas_revision = [
                "Nombre",
                "Paterno",
                "Materno",
                "Correo",
                "Programa",
                "Fecha de Inscripción",
                "Observaciones validación",
            ]
            st.dataframe(df_nuevo[df_nuevo["Estatus validación"] == "Revisar"][columnas_revision])

    csv_normalizado = df_nuevo.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Descargar normalizado",
        data=csv_normalizado,
        file_name="participantes_normalizados.csv",
        mime="text/csv",
    )

    st.divider()
    confirmar = st.button("Aplicar actualizacion a Google Sheets", type="primary")

    if confirmar:
        with st.spinner("Actualizando base maestra..."):
            try:
                df_final, nuevos, actualizados, omitidos = aplicar_upsert_maestro(df_sheets, df_nuevo)
                subir_dataframe(client, spreadsheet_id, nombre_hoja, df_final)
                cargar_hoja.clear()
            except Exception as exc:
                st.error(f"No se pudo actualizar Google Sheets: {exc}")
                st.code(traceback.format_exc())
                st.stop()

        st.success("Base maestra actualizada correctamente.")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Nuevos", nuevos)
        r2.metric("Enriquecidos", actualizados)
        r3.metric("Omitidos sin llave", omitidos)
        r4.metric("Total final", len(df_final))
        st.dataframe(df_final, use_container_width=True, hide_index=True)
