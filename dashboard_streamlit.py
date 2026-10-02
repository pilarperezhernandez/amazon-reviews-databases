"""
Proyecto Bases de Datos - Reviews Amazon
Mejora en visualización - Dashboard interactivo con Streamlit
Pilar Pérez Hernández
María Roca Ramón

Para ejecutar: streamlit run dashboard_streamlit.py
"""

import streamlit as st
import pymysql
from pymongo import MongoClient
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_CONNECTION_STRING, MONGO_DB, MONGO_COLLECTION_REVIEWS
)

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Reviews Amazon - Dashboard",
    page_icon="📊",
    layout="wide"
)

# FUNCIONES DE CONEXIÓN
@st.cache_resource
def crear_conexion_mongo():
    """
    Crea una conexión persistente a MongoDB y usa cache_resource 
    para mantener la conexión durante toda la sesión
    Devuelve: 
        tupla con el cliente de MongoDB y la base de datos
    """
    client = MongoClient(MONGO_CONNECTION_STRING)
    db = client[MONGO_DB]
    return client, db

def crear_conexion_mysql():
    """
    Crea una conexión a MySQL con la base de datos del proyecto
    Devuelve: 
        conexión a MySQL
    """
    conexion = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    return conexion

def ejecutar_consulta(sql, params=None):
    """
    Ejecuta una consulta SQL y devuelve los resultados como lista de tuplas
    Parametros:
        sql (str): consulta SQL
        params (tuple): parámetros de la consulta
    Devuelve:
        lista de tuplas con los resultados
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()
    if params:  # Si se han pasado parámetros los usamos para evitar inyección SQL
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    resultados = cursor.fetchall()  # Devolvemos los resultados como lista de tuplas
    cursor.close()
    conexion.close()
    return resultados


# FUNCIONES AUXILIARES
@st.cache_data(ttl=600)
def obtener_categorias():
    """
    Obtiene la lista de categorías disponibles en la base de datos
    Devuelve:
        lista de categorías
    """
    resultados = ejecutar_consulta(
        "SELECT DISTINCT category FROM products ORDER BY category"
    )
    return [fila[0] for fila in resultados]


# SIDEBAR NAVEGACIÓN
st.sidebar.title("📊 Reviews Amazon")
st.sidebar.markdown("---")

opcion = st.sidebar.radio(
    "Selecciona una visualización:",
    [
        "🏠 Inicio",
        "📈 Evolución de reviews por años",
        "🔥 Popularidad de los artículos",
        "⭐ Histograma por nota",
        "📅 Evolución temporal de reviews",
        "👤 Reviews por usuario",
        "☁️ Nube de palabras",
        "📊 Nota media por categoría",
        "🎯 Recomendación de artículos"
    ]
)
# Información del proyecto
st.sidebar.markdown("---")
st.sidebar.markdown(
    "*Proyecto Bases de Datos*  \n"
    "*Pilar Pérez Hernández*  \n"
    "*María Roca Ramón*  \n"
    "*Curso 2025-2026*"
)


# PÁGINA DE INICIO
if opcion == "🏠 Inicio":
    st.title("📊 Dashboard de Reviews de Amazon")
    st.markdown(
        "Bienvenido al dashboard interactivo del proyecto de Bases de Datos. "
        "Este dashboard reemplaza el menú por terminal ofreciendo una experiencia "
        "visual e interactiva."
    )

    st.markdown("### Resumen del dataset")

    # Métricas generales
    col1, col2, col3, col4 = st.columns(4)

    total_reviews = ejecutar_consulta("SELECT COUNT(*) FROM reviews")[0][0]
    total_productos = ejecutar_consulta("SELECT COUNT(*) FROM products")[0][0]
    total_usuarios = ejecutar_consulta("SELECT COUNT(*) FROM reviewers")[0][0]
    total_categorias = ejecutar_consulta(
        "SELECT COUNT(DISTINCT category) FROM products"
    )[0][0]

    col1.metric("Total reviews", f"{total_reviews:,}")
    col2.metric("Productos", f"{total_productos:,}")
    col3.metric("Usuarios", f"{total_usuarios:,}")
    col4.metric("Categorías", total_categorias)

    st.markdown("### Reviews por categoría")

    resultados = ejecutar_consulta(
        """SELECT p.category, COUNT(*) AS total
           FROM reviews r INNER JOIN products p ON r.asin = p.asin
           GROUP BY p.category ORDER BY total DESC"""
    )
    df = pd.DataFrame(resultados, columns=["Categoría", "Total reviews"])

    fig = px.bar(
        df, x="Categoría", y="Total reviews",
        color="Categoría",
        title="Número de reviews por categoría"
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# 1) EVOLUCIÓN DE REVIEWS POR AÑOS
elif opcion == "📈 Evolución de reviews por años":
    st.title("📈 Evolución de reviews por años")

    categorias = obtener_categorias()
    seleccion = st.selectbox(
        "Selecciona la categoría:",
        ["Todas las categorías"] + categorias
    )

    if seleccion == "Todas las categorías":
        resultados = ejecutar_consulta(
            """SELECT YEAR(r.reviewDate) AS anio, COUNT(*) AS total
               FROM reviews r
               GROUP BY YEAR(r.reviewDate)
               ORDER BY anio"""
        )
        titulo = "Evolución del número de reviews por año (todas las categorías)"
    else:
        resultados = ejecutar_consulta(
            """SELECT YEAR(r.reviewDate) AS anio, COUNT(*) AS total
               FROM reviews r
               INNER JOIN products p ON r.asin = p.asin
               WHERE p.category = %s
               GROUP BY YEAR(r.reviewDate)
               ORDER BY anio""",
            [seleccion]
        )
        titulo = "Evolución del número de reviews por año - " + seleccion

    if resultados:  # Se muestran los resultados si los hay
        df = pd.DataFrame(resultados, columns=["Año", "Total"])
        df["Año"] = df["Año"].astype(str)

        fig = px.bar(df, x="Año", y="Total", title=titulo,
                     color_discrete_sequence=["steelblue"])
        fig.update_layout(xaxis_title="Año", yaxis_title="Número de reviews")   # Actualizar los títulos de los ejes para mayor claridad
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver datos en tabla"):     # Opción para mostrar la tabla de datos debajo del gráfico
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("No se han encontrado resultados.")


# 2) POPULARIDAD DE LOS ARTÍCULOS
elif opcion == "🔥 Popularidad de los artículos":
    st.title("🔥 Evolución de la popularidad de los artículos")

    categorias = obtener_categorias()
    seleccion = st.selectbox(
        "Selecciona la categoría:",
        ["Todas las categorías"] + categorias
    )

    if seleccion == "Todas las categorías":
        resultados = ejecutar_consulta(
            """SELECT r.asin, COUNT(*) AS total
               FROM reviews r
               GROUP BY r.asin
               ORDER BY total DESC"""
        )
        titulo = "Popularidad de los artículos (todas las categorías)"
    else:
        resultados = ejecutar_consulta(
            """SELECT r.asin, COUNT(*) AS total
               FROM reviews r
               INNER JOIN products p ON r.asin = p.asin
               WHERE p.category = %s
               GROUP BY r.asin
               ORDER BY total DESC""",
            [seleccion]
        )
        titulo = "Popularidad de los artículos - " + seleccion

    if resultados:
        popularidades = [fila[1] for fila in resultados]
        posiciones = list(range(1, len(popularidades) + 1))

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=posiciones, y=popularidades,
            mode='lines', line=dict(color='steelblue', width=1.5),
            name='Popularidad'
        ))
        fig.update_layout(
            title=titulo,
            xaxis_title="Artículos (ordenados de mayor a menor popularidad)",
            yaxis_title="Número de reviews"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info("Total de artículos: " + str(len(popularidades)) +
                " | Máx. reviews: " + str(popularidades[0]) +
                " | Mediana: " + str(popularidades[len(popularidades)//2]))
    else:
        st.warning("No se han encontrado resultados.")


# 3) HISTOGRAMA POR NOTA
elif opcion == "⭐ Histograma por nota":
    st.title("⭐ Histograma por nota")

    modo = st.radio(
        "Modo de consulta:",
        ["Por categoría", "Por artículo individual (ASIN)"]
    )

    if modo == "Por categoría":
        categorias = obtener_categorias()
        seleccion = st.selectbox(
            "Selecciona la categoría:",
            ["Todas las categorías"] + categorias
        )

        if seleccion == "Todas las categorías":
            resultados = ejecutar_consulta(
                """SELECT overall, COUNT(*) AS total
                   FROM reviews GROUP BY overall ORDER BY overall"""
            )
            titulo = "Histograma de notas (todas las categorías)"
        else:
            resultados = ejecutar_consulta(
                """SELECT r.overall, COUNT(*) AS total
                   FROM reviews r
                   INNER JOIN products p ON r.asin = p.asin
                   WHERE p.category = %s
                   GROUP BY r.overall ORDER BY r.overall""",
                [seleccion]
            )
            titulo = "Histograma de notas - " + seleccion
    else:
        asin = st.text_input("Introduce el ASIN del artículo:")
        if asin:
            existe = ejecutar_consulta(
                "SELECT asin FROM products WHERE asin = %s", [asin]
            )
            if not existe:  # Si no existe no intentamos ejecutar la consulta del histograma
                st.error("El artículo con ASIN '" + asin +
                         "' no existe en la base de datos.")
                resultados = []
            else:
                resultados = ejecutar_consulta(
                    """SELECT overall, COUNT(*) AS total
                       FROM reviews WHERE asin = %s
                       GROUP BY overall ORDER BY overall""",
                    [asin]
                )
                titulo = "Histograma de notas - Artículo " + asin
        else:
            resultados = []
            titulo = ""

    if resultados:
        df = pd.DataFrame(resultados, columns=["Nota", "Total"])
        df["Nota"] = df["Nota"].astype(int).astype(str)

        fig = px.bar(df, x="Nota", y="Total", title=titulo,
                     color_discrete_sequence=["coral"])
        fig.update_layout(xaxis_title="Nota (overall)",
                          yaxis_title="Número de reviews")
        st.plotly_chart(fig, use_container_width=True)


# 4) EVOLUCIÓN TEMPORAL DE REVIEWS
elif opcion == "📅 Evolución temporal de reviews":
    st.title("📅 Evolución de reviews a lo largo del tiempo")

    categorias = obtener_categorias()

    fig = go.Figure()

    for categoria in categorias:
        resultados = ejecutar_consulta(
            """SELECT r.unixReviewTime
               FROM reviews r
               INNER JOIN products p ON r.asin = p.asin
               WHERE p.category = %s
               ORDER BY r.unixReviewTime ASC""",
            [categoria]
        )

        if resultados:
            timestamps = [fila[0] for fila in resultados]
            # Convertir unix timestamps a fechas para mejor visualización
            fechas = pd.to_datetime(timestamps, unit='s')
            acumulado = list(range(1, len(timestamps) + 1))

            fig.add_trace(go.Scatter(
                x=fechas, y=acumulado,
                mode='lines', name=categoria, line=dict(width=1.5)
            ))

    fig.update_layout(
        title="Evolución del número de reviews acumuladas por categoría",
        xaxis_title="Fecha",
        yaxis_title="Número de reviews acumuladas",
        legend_title="Categoría"
    )
    st.plotly_chart(fig, use_container_width=True)


# 5) REVIEWS POR USUARIO
elif opcion == "👤 Reviews por usuario":
    st.title("👤 Histograma de reviews por usuario")

    resultados = ejecutar_consulta(
        """SELECT reviewerID, COUNT(*) AS total_reviews
           FROM reviews GROUP BY reviewerID"""
    )

    if resultados:
        reviews_por_usuario = [fila[1] for fila in resultados]

        # Crear el histograma con pandas para agrupar
        df = pd.DataFrame({"num_reviews": reviews_por_usuario})

        fig = px.histogram(
            df, x="num_reviews", nbins=100,
            title="Distribución del número de reviews por usuario",
            color_discrete_sequence=["teal"]
        )
        fig.update_layout(
            xaxis_title="Número de reviews",
            yaxis_title="Número de usuarios"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Estadísticas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total usuarios", f"{len(reviews_por_usuario):,}")
        col2.metric("Media reviews/usuario", f"{sum(reviews_por_usuario)/len(reviews_por_usuario):.1f}")
        col3.metric("Máximo", max(reviews_por_usuario))
        col4.metric("Mediana", sorted(reviews_por_usuario)[len(reviews_por_usuario)//2])


# 6) NUBE DE PALABRAS
elif opcion == "☁️ Nube de palabras":
    st.title("☁️ Nube de palabras por categoría")

    categorias = obtener_categorias()
    seleccion = st.selectbox("Selecciona la categoría:", categorias)

    # Opciones de personalización
    col1, col2 = st.columns(2)
    max_palabras = col1.slider("Máximo de palabras:", 50, 300, 100)
    color_fondo = col2.selectbox("Color de fondo:", ["white", "black"])

    if st.button("Generar nube de palabras"):
        with st.spinner("Generando nube de palabras..."):
            # Obtener los asin de esa categoría desde MySQL
            asins_result = ejecutar_consulta(
                "SELECT asin FROM products WHERE category = %s",
                [seleccion]
            )
            asins = [fila[0] for fila in asins_result]

            # Obtener los summaries de MongoDB
            _, db = crear_conexion_mongo()
            coleccion = db[MONGO_COLLECTION_REVIEWS]
            resultados = coleccion.find(
                {"asin": {"$in": asins}},
                {"summary": 1, "_id": 0}
            )

            # Construir texto filtrado
            texto = ""
            for doc in resultados:
                summary = doc.get("summary", "")
                if summary:
                    palabras = [p for p in summary.split() if len(p) > 3]
                    texto += " ".join(palabras) + " "

            if texto.strip():
                wordcloud = WordCloud(
                    width=800, height=400,
                    background_color=color_fondo,
                    max_words=max_palabras
                ).generate(texto)

                fig, ax = plt.subplots(figsize=(12, 6))
                ax.imshow(wordcloud, interpolation="bilinear")
                ax.set_title("Nube de palabras - " + seleccion)
                ax.axis("off")
                st.pyplot(fig)
                plt.close()
            else:
                st.warning("No se han encontrado datos para generar la nube.")


# 7) NOTA MEDIA POR CATEGORÍA
elif opcion == "📊 Nota media por categoría":
    st.title("📊 Nota media por categoría de producto")

    resultados = ejecutar_consulta(
        """SELECT p.category, AVG(r.overall) AS media, COUNT(*) AS total
           FROM reviews r
           INNER JOIN products p ON r.asin = p.asin
           GROUP BY p.category
           ORDER BY media DESC"""
    )

    if resultados:
        df = pd.DataFrame(resultados,
                          columns=["Categoría", "Nota media", "Total reviews"])
        df["Nota media"] = df["Nota media"].round(2)

        fig = px.bar(
            df, x="Categoría", y="Nota media",
            color="Nota media",
            color_continuous_scale="Viridis",
            title="Nota media por categoría de producto",
            text="Nota media"
        )
        fig.update_layout(yaxis_range=[0, 5.5],
                          yaxis_title="Nota media (overall)")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Detalle por categoría")
        st.dataframe(df, use_container_width=True)


# 8) RECOMENDACIÓN DE ARTÍCULOS
elif opcion == "🎯 Recomendación de artículos":
    st.title("🎯 Recomendación de artículos")
    st.markdown(
        "Introduce un identificador de usuario y un tipo de artículo para "
        "obtener los 10 artículos más populares que no ha consumido."
    )

    col1, col2 = st.columns(2)

    reviewer_id = col1.text_input("ReviewerID del usuario:")
    categorias = obtener_categorias()
    categoria = col2.selectbox("Tipo de artículo:", categorias)

    if st.button("Obtener recomendaciones"):
        if not reviewer_id:
            st.error("Introduce un reviewerID válido.")
        else:
            # Comprobar que el usuario existe
            usuario = ejecutar_consulta(
                "SELECT reviewerID, reviewerName FROM reviewers WHERE reviewerID = %s",
                [reviewer_id]
            )

            if not usuario:
                st.error("No se ha encontrado el usuario con ID: " + reviewer_id)
            else:
                st.success("Usuario encontrado: " + str(usuario[0][1]))

                # Obtener recomendaciones
                resultados = ejecutar_consulta(
                    """SELECT p.asin, COUNT(*) AS total_reviews
                       FROM reviews r
                       INNER JOIN products p ON r.asin = p.asin
                       WHERE p.category = %s
                       AND p.asin NOT IN (
                           SELECT asin FROM reviews WHERE reviewerID = %s
                       )
                       GROUP BY p.asin
                       ORDER BY total_reviews DESC
                       LIMIT 10""",
                    [categoria, reviewer_id]
                )

                if resultados:
                    st.markdown("### Top 10 artículos recomendados de " + categoria)

                    df = pd.DataFrame(resultados,
                                      columns=["ASIN", "Nº Reviews"])

                    # Mostrar como tabla con ranking
                    df.index = range(1, len(df) + 1)
                    df.index.name = "Ranking"
                    st.dataframe(df, use_container_width=True)

                    # Gráfico de barras horizontal
                    fig = px.bar(
                        df, x="Nº Reviews", y="ASIN",
                        orientation='h',
                        title="Popularidad de los artículos recomendados",
                        color_discrete_sequence=["mediumpurple"]
                    )
                    fig.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se han encontrado artículos para recomendar.")