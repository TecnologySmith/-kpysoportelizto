import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración inicial de la página (Título en pestaña y layout ancho)
st.set_page_config(page_title="Analizador de Chats Excel", layout="wide")

# Título principal de la interfaz
st.title("📊 Analizador de Chats Pro")
st.markdown("Sube tu archivo de Excel para procesar las métricas de agentes y tiempos.")

# --- 1. CARGA DE ARCHIVOS ---
uploaded_file = st.file_uploader("Elige un archivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    # Lectura del archivo Excel usando pandas
    df = pd.read_excel(uploaded_file)
    
    try:
        # Conversión de la columna fecha a formato datetime de Python
        df['Fecha Creación'] = pd.to_datetime(df['Fecha Creación'])
        
        # --- 2. FILTRO LATERAL (SIDEBAR) ---
        st.sidebar.header("Filtros")
        fecha_min = df['Fecha Creación'].min().date()
        fecha_max = df['Fecha Creación'].max().date()
        
        # Widget para seleccionar rango de fechas
        rango_fechas = st.sidebar.date_input(
            "Selecciona el rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

        # Aplicación del filtro de fechas si el usuario seleccionó un rango válido
        if len(rango_fechas) == 2:
            inicio, fin = rango_fechas
            mask = (df['Fecha Creación'].dt.date >= inicio) & (df['Fecha Creación'].dt.date <= fin)
            df = df.loc[mask]

        # --- 3. PROCESAMIENTO DE DATOS TEMPORALES ---
        df['Hora'] = df['Fecha Creación'].dt.hour
        df['Día del Mes'] = df['Fecha Creación'].dt.day
        df['Nombre Día'] = df['Fecha Creación'].dt.day_name()
        df['Fecha'] = df['Fecha Creación'].dt.date
        
        # Diccionario para traducir días de inglés a español
        traduccion_dias = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df['Día Semana'] = df['Nombre Día'].map(traduccion_dias)
        # Orden lógico para las gráficas de días de la semana
        orden_espanol = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

        # --- 4. CÁLCULO DE KPIs (INDICADORES CLAVE) ---
        total_chats = len(df)
        total_agentes = df['Agente'].nunique() if 'Agente' in df.columns else 0
        dias_unicos = df['Fecha'].nunique()
        promedio_dia = round(total_chats / dias_unicos, 1) if dias_unicos > 0 else 0

        # Mostrar métricas en 3 columnas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Chats Global", f"{total_chats:,}")
        m2.metric("Agentes Activos", total_agentes)
        m3.metric("Promedio Chats/Día", promedio_dia)
        
        st.divider()

        # --- 5. SECCIÓN: DESEMPEÑO POR AGENTE ---
        st.header("👨‍💻 Desempeño por Agente")
        
        # Agrupamos y contamos chats por agente
        agente_counts = df['Agente'].value_counts().reset_index()
        agente_counts.columns = ['Agente', 'Total Chats']
        
        # Preparación de tabla resumen con fila de total al final
        df_tabla_agentes = agente_counts.copy()
        fila_total_ag = pd.DataFrame([{'Agente': 'TOTAL', 'Total Chats': agente_counts['Total Chats'].sum()}])
        df_tabla_agentes = pd.concat([df_tabla_agentes, fila_total_ag], ignore_index=True)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("**Resumen Numérico**")
            st.dataframe(df_tabla_agentes, use_container_width=True, hide_index=True)
        
        with col2:
            # Gráfico de barras horizontal o vertical para agentes
            fig_agente = px.bar(agente_counts, x='Agente', y='Total Chats', 
                                color='Agente', text_auto=True,
                                title="Distribución de Carga por Agente")
            st.plotly_chart(fig_agente, use_container_width=True)

        st.divider()

        # --- 6. SECCIÓN: ANÁLISIS HORARIO ---
        st.header("⏰ Volumen por Horas")
        hora_counts = df.groupby('Hora').size().reset_index(name='Cantidad')
        # Gráfico de líneas para ver picos de tráfico
        fig_hora = px.line(hora_counts, x='Hora', y='Cantidad', markers=True, text='Cantidad',
                          title="Flujo de Chats durante el Día")
        fig_hora.update_traces(textposition="top center")
        st.plotly_chart(fig_hora, use_container_width=True)

        # --- 7. SECCIÓN: ANÁLISIS CALENDARIO ---
        col_a, col_b = st.columns(2)

        with col_a:
            st.header("📅 Por Día del Mes")
            dia_mes_counts = df.groupby('Día del Mes').size().reset_index(name='Cantidad')
            fig_dia = px.bar(dia_mes_counts, x='Día del Mes', y='Cantidad', 
                             color_discrete_sequence=['#00CC96'], text_auto=True)
            st.plotly_chart(fig_dia, use_container_width=True)

        with col_b:
            st.header("🗓️ Por Día de la Semana")
            dia_semana_counts = df['Día Semana'].value_counts().reindex(orden_espanol).reset_index()
            dia_semana_counts.columns = ['Día', 'Cantidad']
            dia_semana_counts = dia_semana_counts.dropna()
            # Gráfico de dona para ver distribución semanal
            fig_semana = px.pie(dia_semana_counts, values='Cantidad', names='Día', hole=0.4)
            st.plotly_chart(fig_semana, use_container_width=True)

        st.divider()

        # --- 8. SECCIÓN: ANÁLISIS POR CLASIFICACIÓN ---
        # Verificamos si la columna existe antes de intentar graficar
        if 'Clasificación' in df.columns:
            st.header("🏷️ Análisis por Clasificación")
            
            # Conteo de chats por tipo de clasificación
            class_counts = df['Clasificación'].value_counts().reset_index()
            class_counts.columns = ['Categoría', 'Total Chats'] # Renombrado claro
            
            # Fila de total para la tabla
            df_tabla_class = class_counts.copy()
            fila_total_cl = pd.DataFrame([{'Categoría': 'TOTAL', 'Total Chats': class_counts['Total Chats'].sum()}])
            df_tabla_class = pd.concat([df_tabla_class, fila_total_cl], ignore_index=True)

            col_c1, col_c2 = st.columns([1, 2])
            with col_c1:
                st.write("**Resumen de Categorías**")
                st.dataframe(df_tabla_class, use_container_width=True, hide_index=True)
            
            with col_c2:
                # Gráfico de barras para clasificaciones (CORREGIDO: x='Categoría')
                fig_class = px.bar(class_counts, x='Categoría', y='Total Chats', 
                                    color='Categoría', text_auto=True,
                                    title="Chats por Tipo de Clasificación")
                st.plotly_chart(fig_class, use_container_width=True)
        else:
            st.warning("No se encontró la columna 'Clasificación' en el archivo.")

        st.divider()

    except Exception as e:
        # Captura de errores para evitar que la app se caiga
        st.error(f"Error en el procesamiento: {e}")

else:
    # Mensaje inicial cuando no hay archivos
    st.info("Esperando archivo... Asegúrate de que el Excel tenga las columnas: 'Agente', 'Fecha Creación' y 'Clasificación'.")