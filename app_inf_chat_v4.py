import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re
import io

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analizador de Chats Pro",
    page_icon="💬",
    layout="wide",
)

# ── Estilos CSS personalizados ─────────────────────────────────────────────────
st.markdown("""
<style>
    /* Fondo general oscuro */
    .stApp { background-color: #0f1117; }

    /* Métricas */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #3a3f6b;
        border-radius: 12px;
        padding: 16px 20px;
    }
    div[data-testid="metric-container"] label { color: #8b92b8 !important; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
    div[data-testid="metric-container"] div[data-testid="metric-value"] { color: #e2e8ff !important; font-size: 2rem; font-weight: 700; }

    /* Títulos de sección */
    h1 { color: #c9d1ff !important; }
    h2, h3 { color: #a5b4fc !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: #1a1d2e; border-radius: 10px; padding: 4px; gap: 4px; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: #6b7280; border-radius: 8px; padding: 8px 20px; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: #3730a3 !important; color: white !important; }

    /* Botones */
    .stButton > button {
        background: linear-gradient(135deg, #4338ca, #6d28d9);
        color: white; border: none; border-radius: 8px;
        padding: 8px 20px; font-weight: 600;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* Info / warning */
    .stAlert { border-radius: 10px; }

    /* Dataframe */
    .stDataFrame { border-radius: 10px; overflow: hidden; }

    /* Input */
    .stTextInput input, .stSelectbox select {
        background: #1e2130; border-color: #3a3f6b; color: #e2e8ff; border-radius: 8px;
    }

    /* Divider */
    hr { border-color: #2d3154; }

    /* Tabla detalle highlight */
    .detail-header {
        background: #1e2130;
        border-left: 4px solid #6d28d9;
        padding: 10px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ── Columnas del detalle de chats ──────────────────────────────────────────────
COLS_DETALLE = [
    'Consecutivo', 'Canal', 'Ciclo', 'Clasificación', 'Cliente', 'Celular',
    'Agente', 'Fecha Creación', 'Fecha cierre', 'Tiempo de Cierre',
    'Cerrado por', 'Ticket', 'Último mensaje'
]


def cols_presentes(df: pd.DataFrame, cols: list) -> list:
    """Devuelve las columnas de `cols` que existen en el dataframe."""
    return [c for c in cols if c in df.columns]


def mostrar_tabla_detalle(df_sub: pd.DataFrame, titulo: str, key: str):
    """Muestra una tabla de detalle expandible con las columnas estándar."""
    with st.expander(f"📋 {titulo} — {len(df_sub):,} registros", expanded=True):
        columnas = cols_presentes(df_sub, COLS_DETALLE)
        st.dataframe(
            df_sub[columnas] if columnas else df_sub,
            use_container_width=True,
            hide_index=True,
            key=key,
        )


# ── Carga desde Google Drive ───────────────────────────────────────────────────
def extraer_id_drive(url: str) -> str | None:
    """Extrae el file ID de una URL de Google Drive."""
    patrones = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/spreadsheets/d/([a-zA-Z0-9_-]+)",
    ]
    for p in patrones:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def cargar_desde_drive(url: str) -> pd.DataFrame | None:
    file_id = extraer_id_drive(url)
    if not file_id:
        st.error("No se pudo extraer el ID del archivo desde la URL. Asegúrate de que sea un enlace de Google Drive con permisos de acceso público.")
        return None

    # Intentamos primero formato xlsx, luego csv (Sheets exportado)
    url_xlsx = f"https://drive.google.com/uc?export=download&id={file_id}"
    url_csv  = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"

    for download_url, fmt in [(url_xlsx, "excel"), (url_csv, "csv")]:
        try:
            resp = requests.get(download_url, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 100:
                if fmt == "excel":
                    return pd.read_excel(io.BytesIO(resp.content))
                else:
                    return pd.read_csv(io.StringIO(resp.text))
        except Exception:
            continue

    st.error("No se pudo descargar el archivo. Verifica que el enlace sea público (compartido con 'cualquier persona con el enlace').")
    return None


# ── MAIN ───────────────────────────────────────────────────────────────────────
st.title("💬 Analizador de Chats Pro")
st.markdown("Analiza métricas de agentes, tiempos y clasificaciones desde tu archivo Excel.")

# ── Selector de fuente del archivo ────────────────────────────────────────────
st.subheader("📂 Cargar archivo")

origen = st.radio(
    "¿Desde dónde quieres cargar el archivo?",
    ["💻 Mi computador", "☁️ Google Drive (URL)"],
    horizontal=True,
)

df_raw: pd.DataFrame | None = None

if origen == "💻 Mi computador":
    uploaded_file = st.file_uploader(
        "Selecciona tu archivo Excel", type=["xlsx", "xls"],
        help="El archivo debe tener las columnas: Agente, Fecha Creación, Clasificación"
    )
    if uploaded_file:
        try:
            df_raw = pd.read_excel(uploaded_file)
            st.success(f"✅ Archivo cargado: **{uploaded_file.name}** — {len(df_raw):,} filas")
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

else:
    drive_url = st.text_input(
        "Pega la URL de Google Drive o Google Sheets",
        placeholder="https://drive.google.com/file/d/... o https://docs.google.com/spreadsheets/d/...",
    )
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        cargar_btn = st.button("☁️ Cargar desde Drive")

    if cargar_btn and drive_url:
        with st.spinner("Descargando archivo desde Google Drive..."):
            df_raw = cargar_desde_drive(drive_url)
        if df_raw is not None:
            st.success(f"✅ Archivo cargado desde Drive — {len(df_raw):,} filas")

    st.caption("⚠️ El archivo de Google Drive debe tener permisos de acceso público ('Cualquier persona con el enlace puede ver').")


# ── Proceso principal ─────────────────────────────────────────────────────────
if df_raw is not None:
    try:
        df_raw['Fecha Creación'] = pd.to_datetime(df_raw['Fecha Creación'], errors='coerce')

        # ── Filtro lateral ────────────────────────────────────────────────────
        st.sidebar.header("🔍 Filtros")
        fecha_min = df_raw['Fecha Creación'].min().date()
        fecha_max = df_raw['Fecha Creación'].max().date()

        rango_fechas = st.sidebar.date_input(
            "Rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max,
        )

        df = df_raw.copy()
        if len(rango_fechas) == 2:
            inicio, fin = rango_fechas
            mask = (df['Fecha Creación'].dt.date >= inicio) & (df['Fecha Creación'].dt.date <= fin)
            df = df.loc[mask]

        if 'Agente' in df.columns:
            agentes_disp = ['Todos'] + sorted(df['Agente'].dropna().unique().tolist())
            agente_sel = st.sidebar.selectbox("Agente", agentes_disp)
            if agente_sel != 'Todos':
                df = df[df['Agente'] == agente_sel]

        if 'Clasificación' in df.columns:
            clasif_disp = ['Todas'] + sorted(df['Clasificación'].dropna().unique().tolist())
            clasif_sel = st.sidebar.selectbox("Clasificación", clasif_disp)
            if clasif_sel != 'Todas':
                df = df[df['Clasificación'] == clasif_sel]

        # ── Campos temporales ─────────────────────────────────────────────────
        df['Hora']       = df['Fecha Creación'].dt.hour
        df['Día del Mes'] = df['Fecha Creación'].dt.day
        df['Nombre Día'] = df['Fecha Creación'].dt.day_name()
        df['Fecha']      = df['Fecha Creación'].dt.date

        traduccion_dias = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df['Día Semana'] = df['Nombre Día'].map(traduccion_dias)
        orden_espanol = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

        # ── Tabs principales ──────────────────────────────────────────────────
        tab_dash, tab_agentes, tab_clasif, tab_tiempo, tab_buscador = st.tabs([
            "📊 Dashboard", "👨‍💻 Agentes", "🏷️ Clasificaciones", "⏰ Tiempos", "🔎 Buscador"
        ])

        # ════════════════════════════════════════════════════════════════════
        # TAB 1 — DASHBOARD
        # ════════════════════════════════════════════════════════════════════
        with tab_dash:
            total_chats   = len(df)
            total_agentes = df['Agente'].nunique() if 'Agente' in df.columns else 0
            dias_unicos   = df['Fecha'].nunique()
            promedio_dia  = round(total_chats / dias_unicos, 1) if dias_unicos > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Chats", f"{total_chats:,}")
            m2.metric("Agentes Activos", total_agentes)
            m3.metric("Promedio Chats / Día", promedio_dia)
            m4.metric("Días con Actividad", dias_unicos)

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("⏰ Flujo por Hora")
                hora_counts = df.groupby('Hora').size().reset_index(name='Cantidad')
                fig_hora = px.area(
                    hora_counts, x='Hora', y='Cantidad', markers=True,
                    color_discrete_sequence=['#6d28d9'],
                    template='plotly_dark',
                )
                fig_hora.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_hora, use_container_width=True)

            with col_b:
                st.subheader("🗓️ Por Día de la Semana")
                dia_semana_counts = (
                    df['Día Semana'].value_counts()
                    .reindex(orden_espanol)
                    .reset_index()
                )
                dia_semana_counts.columns = ['Día', 'Cantidad']
                dia_semana_counts = dia_semana_counts.dropna()
                fig_semana = px.pie(
                    dia_semana_counts, values='Cantidad', names='Día', hole=0.45,
                    color_discrete_sequence=px.colors.sequential.Purp,
                    template='plotly_dark',
                )
                fig_semana.update_layout(paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_semana, use_container_width=True)

            st.subheader("📅 Chats por Día del Mes")
            dia_mes_counts = df.groupby('Día del Mes').size().reset_index(name='Cantidad')
            fig_dia = px.bar(
                dia_mes_counts, x='Día del Mes', y='Cantidad',
                color_discrete_sequence=['#4338ca'], text_auto=True,
                template='plotly_dark',
            )
            fig_dia.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_dia, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # TAB 2 — AGENTES (con detalle al hacer clic)
        # ════════════════════════════════════════════════════════════════════
        with tab_agentes:
            st.subheader("👨‍💻 Desempeño por Agente")

            agente_counts = df['Agente'].value_counts().reset_index()
            agente_counts.columns = ['Agente', 'Total Chats']

            df_tabla_ag = agente_counts.copy()
            fila_total  = pd.DataFrame([{'Agente': 'TOTAL', 'Total Chats': agente_counts['Total Chats'].sum()}])
            df_tabla_ag = pd.concat([df_tabla_ag, fila_total], ignore_index=True)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.write("**Haz clic en una fila para ver el detalle de esos chats**")
                evento_ag = st.dataframe(
                    df_tabla_ag,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="tabla_agentes",
                )

            with col2:
                fig_ag = px.bar(
                    agente_counts, x='Agente', y='Total Chats',
                    color='Total Chats',
                    color_continuous_scale='Purples', text_auto=True,
                    title="Carga por Agente",
                    template='plotly_dark',
                )
                fig_ag.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_ag, use_container_width=True)

            # ── Detalle al seleccionar fila ───────────────────────────────
            filas_sel = evento_ag.selection.get("rows", [])
            if filas_sel:
                idx    = filas_sel[0]
                ag_val = df_tabla_ag.iloc[idx]['Agente']

                if ag_val == 'TOTAL':
                    df_det = df
                    titulo = "Todos los agentes"
                else:
                    df_det = df[df['Agente'] == ag_val]
                    titulo = f"Agente: {ag_val}"

                st.divider()
                mostrar_tabla_detalle(df_det, titulo, key=f"det_ag_{ag_val}")

        # ════════════════════════════════════════════════════════════════════
        # TAB 3 — CLASIFICACIONES (con detalle al hacer clic)
        # ════════════════════════════════════════════════════════════════════
        with tab_clasif:
            if 'Clasificación' not in df.columns:
                st.warning("No se encontró la columna 'Clasificación' en el archivo.")
            else:
                st.subheader("🏷️ Análisis por Clasificación")

                class_counts = df['Clasificación'].value_counts().reset_index()
                class_counts.columns = ['Categoría', 'Total Chats']

                df_tabla_cl = class_counts.copy()
                fila_total_cl = pd.DataFrame([{'Categoría': 'TOTAL', 'Total Chats': class_counts['Total Chats'].sum()}])
                df_tabla_cl = pd.concat([df_tabla_cl, fila_total_cl], ignore_index=True)

                col_c1, col_c2 = st.columns([1, 2])
                with col_c1:
                    st.write("**Haz clic en una categoría para ver el detalle**")
                    evento_cl = st.dataframe(
                        df_tabla_cl,
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row",
                        key="tabla_clasif",
                    )

                with col_c2:
                    fig_cl = px.bar(
                        class_counts, x='Categoría', y='Total Chats',
                        color='Total Chats',
                        color_continuous_scale='Purples', text_auto=True,
                        title="Chats por Clasificación",
                        template='plotly_dark',
                    )
                    fig_cl.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_cl, use_container_width=True)

                # ── Detalle al seleccionar ────────────────────────────────
                filas_cl = evento_cl.selection.get("rows", [])
                if filas_cl:
                    idx    = filas_cl[0]
                    cl_val = df_tabla_cl.iloc[idx]['Categoría']

                    if cl_val == 'TOTAL':
                        df_det = df
                        titulo = "Todas las clasificaciones"
                    else:
                        df_det = df[df['Clasificación'] == cl_val]
                        titulo = f"Clasificación: {cl_val}"

                    st.divider()
                    mostrar_tabla_detalle(df_det, titulo, key=f"det_cl_{cl_val}")

        # ════════════════════════════════════════════════════════════════════
        # TAB 4 — TIEMPOS
        # ════════════════════════════════════════════════════════════════════
        with tab_tiempo:
            st.subheader("⏰ Análisis de Tiempos")

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.write("**Flujo de Chats por Hora**")
                hora_counts = df.groupby('Hora').size().reset_index(name='Cantidad')
                fig_h = px.line(
                    hora_counts, x='Hora', y='Cantidad', markers=True, text='Cantidad',
                    color_discrete_sequence=['#a78bfa'],
                    template='plotly_dark',
                )
                fig_h.update_traces(textposition="top center")
                fig_h.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_h, use_container_width=True)

            with col_t2:
                if 'Tiempo de Cierre' in df.columns:
                    st.write("**Distribución del Tiempo de Cierre**")
                    df_tc = df[pd.to_numeric(df['Tiempo de Cierre'], errors='coerce').notna()].copy()
                    df_tc['Tiempo de Cierre'] = pd.to_numeric(df_tc['Tiempo de Cierre'])
                    fig_tc = px.histogram(
                        df_tc, x='Tiempo de Cierre', nbins=30,
                        color_discrete_sequence=['#7c3aed'],
                        template='plotly_dark',
                        title="Tiempo de Cierre (minutos)"
                    )
                    fig_tc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_tc, use_container_width=True)
                else:
                    st.info("Columna 'Tiempo de Cierre' no encontrada.")

            # Chats por fecha
            st.write("**Chats diarios**")
            chats_fecha = df.groupby('Fecha').size().reset_index(name='Chats')
            fig_fecha = px.area(
                chats_fecha, x='Fecha', y='Chats',
                color_discrete_sequence=['#6d28d9'],
                template='plotly_dark',
            )
            fig_fecha.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_fecha, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # TAB 5 — BUSCADOR
        # ════════════════════════════════════════════════════════════════════
        with tab_buscador:
            st.subheader("🔎 Buscador de Tickets")
            st.markdown("Busca por **número de ticket**, **nombre del cliente** o **número de celular/teléfono**.")

            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                query = st.text_input(
                    "Ingresa el término de búsqueda",
                    placeholder="Ej: TK-1234 · Juan Pérez · 3001234567",
                    label_visibility="collapsed",
                )
            with col_s2:
                buscar_btn = st.button("🔍 Buscar", use_container_width=True)

            if query or buscar_btn:
                q = str(query).strip().lower()
                if not q:
                    st.info("Ingresa un término para buscar.")
                else:
                    columnas_busq = cols_presentes(df, ['Ticket', 'Cliente', 'Celular', 'Consecutivo'])

                    if not columnas_busq:
                        st.warning("No se encontraron columnas de búsqueda (Ticket, Cliente, Celular) en el archivo.")
                    else:
                        mask_busq = pd.Series(False, index=df.index)
                        for col in columnas_busq:
                            mask_busq |= df[col].astype(str).str.lower().str.contains(q, na=False)

                        resultados = df[mask_busq]

                        if resultados.empty:
                            st.warning(f"No se encontraron resultados para **'{query}'**.")
                        else:
                            st.success(f"Se encontraron **{len(resultados):,}** registro(s) para **'{query}'**")
                            columnas_det = cols_presentes(resultados, COLS_DETALLE)
                            st.dataframe(
                                resultados[columnas_det] if columnas_det else resultados,
                                use_container_width=True,
                                hide_index=True,
                                key="tabla_busqueda",
                            )

                            # Descarga de resultados
                            csv_bytes = resultados.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "⬇️ Descargar resultados (CSV)",
                                data=csv_bytes,
                                file_name=f"busqueda_{q}.csv",
                                mime="text/csv",
                            )

    except Exception as e:
        st.error(f"❌ Error en el procesamiento: {e}")
        st.exception(e)

else:
    # Estado vacío
    st.divider()
    st.info(
        "📄 Carga tu archivo para comenzar. El Excel debe tener las columnas: "
        "**Agente**, **Fecha Creación** y **Clasificación** como mínimo."
    )
    st.markdown("""
    **Columnas opcionales que amplían el análisis:**
    `Consecutivo · Canal · Ciclo · Cliente · Celular · Fecha cierre · Tiempo de Cierre · Cerrado por · Ticket · Último mensaje`
    """)
