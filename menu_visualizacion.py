"""
Proyecto Bases de Datos - Reviews Amazon
Menú de visualización de datos
Pilar Pérez Hernández
María Roca Ramón
"""

import pymysql
from pymongo import MongoClient
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_CONNECTION_STRING, MONGO_DB, MONGO_COLLECTION_REVIEWS
)

# FUNCIONES CONEXIÓN
def crear_conexion_mysql():
    """
    Crea una conexión a MySQL con la base de datos del proyecto.
    Devuelve: 
        conexión a MySQL
    """
    # Establecer la conexión indicando host, puerto, usuario, contraseña y base de datos
    conexion = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    return conexion

def crear_conexion_mongo():
    """
    Crea una conexión a MongoDB y devuelve el cliente y la base de datos.
    Devuelve: 
        tupla con el cliente de MongoDB y la base de datos
    """
    # Crear la conexión empleando MongoClient
    client = MongoClient(MONGO_CONNECTION_STRING)
    # acceder a la base de datos indexando el cliente
    db = client[MONGO_DB]
    return client, db


# FUNCIONES AUXILIARES
def pedir_categoria(permitir_todo=True):
    """
    Muestra las categorías disponibles y pide al usuario que seleccione una.
    Si permitir_todo es True, se ofrece la opción de seleccionar todas las categorías. 
    Parámetros:
        permitir_todo: si True, se ofrece la opción de seleccionar Todas
    Devuelve:
        nombre de la categoría seleccionada o "todo" si elige todas, o None si no es válida
    """
    print("Selecciona la categoría:")
    print("1. Toys_and_Games")
    print("2. Video_Games")
    print("3. Digital_Music")
    print("4. Musical_Instruments")
    if permitir_todo:
        print("5. Todas las categorías")

    opcion = input("Selecciona una opción: ").strip()

    categorias = {
        "1": "Toys_and_Games",
        "2": "Video_Games",
        "3": "Digital_Music",
        "4": "Musical_Instruments"
    }

    if opcion in categorias:
        return categorias[opcion]
    elif opcion == "5" and permitir_todo:
        return "todo"
    else:
        print("Opción no válida.")
        return None

# opción 1: Evolución de reviews por años
def evolucion_reviews_por_anio():
    """
    Obtiene el número de reviews por año y muestra un histograma.
    """
    # Pedir al usuario la categoría que quiere visualizar
    categoria = pedir_categoria(permitir_todo=True)
    if categoria is None:
        return

    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    if categoria == "todo":
        sql = """SELECT YEAR(r.reviewDate) AS anio, COUNT(*) AS total
                 FROM reviews r
                 GROUP BY YEAR(r.reviewDate)
                 ORDER BY anio"""
        cursor.execute(sql)
        titulo = "Evolución del número de reviews por año (todas las categorías)"
    else:
        sql = """SELECT YEAR(r.reviewDate) AS anio, COUNT(*) AS total
                 FROM reviews r
                 INNER JOIN products p ON r.asin = p.asin
                 WHERE p.category = %s
                 GROUP BY YEAR(r.reviewDate)
                 ORDER BY anio"""
        cursor.execute(sql, [categoria])
        titulo = "Evolución del número de reviews por año - " + categoria

    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # Compruebo si hay resultados
    if not resultados:
        print("No se han encontrado resultados.")
        return

    # separo los datos en dos listas para el gráfico
    anios = [str(fila[0]) for fila in resultados]
    totales = [fila[1] for fila in resultados]

    # Crear el gráfico de barras (histograma)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=anios, y=totales, color="steelblue")
    plt.title(titulo)
    plt.xlabel("Año")
    plt.ylabel("Número de reviews")
    plt.tight_layout()
    plt.show()


# opción 2: Evolución de la popularidad de los artículos
def evolucion_popularidad_articulos():
    """
    Obtiene una curva mostrando los artículos ordenados de mayor a menor popularidad. 
    """
    # Pedir al usuario la categoría que quiere visualizar
    categoria = pedir_categoria(permitir_todo=True)
    if categoria is None:
        return

    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    if categoria == "todo":
        sql = """SELECT r.asin, COUNT(*) AS total
                 FROM reviews r
                 GROUP BY r.asin
                 ORDER BY total DESC"""
        cursor.execute(sql)
        titulo = "Evolución de la popularidad de los artículos (todas las categorías)"
    else:
        sql = """SELECT r.asin, COUNT(*) AS total
                 FROM reviews r
                 INNER JOIN products p ON r.asin = p.asin
                 WHERE p.category = %s
                 GROUP BY r.asin
                 ORDER BY total DESC"""
        cursor.execute(sql, [categoria])
        titulo = "Evolución de la popularidad de los artículos - " + categoria

    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # comprobar si hay resultados
    if not resultados:
        print("No se han encontrado resultados.")
        return

    # número de reviews de cada artículo (ya ordenados de mayor a menor)
    popularidades = [fila[1] for fila in resultados]
    # Crear un índice para el eje X (posición del artículo en el ranking)
    posiciones = list(range(1, len(popularidades) + 1))

    # curva de popularidad
    plt.figure(figsize=(12, 6))
    plt.plot(posiciones, popularidades, color="steelblue", linewidth=1.5)
    plt.title(titulo)
    plt.xlabel("Artículos (ordenados de mayor a menor popularidad)")
    plt.ylabel("Número de reviews")
    plt.tight_layout()
    plt.show()


# opción 3: Histograma por nota

def histograma_por_nota():
    """
    Obtiene el número de reviews por cada nota y muestra un histograma.
    """
    # preguntar modo de consulta
    print("¿Cómo quieres ver el histograma de notas?")
    print("1. Por tipo de artículo (o todos)")
    print("2. Buscar por un artículo individual (introducir ASIN)")
    opcion = input("Selecciona una opción (1 o 2): ").strip()

    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    if opcion == "2":
        # Buscar por un artículo individual
        asin = input("Introduce el ASIN del artículo: ").strip()

        # Comprobar que el artículo existe en la base de datos
        sql_check = """SELECT asin FROM products WHERE asin = %s"""
        cursor.execute(sql_check, [asin])
        existe = cursor.fetchone()

        if not existe:
            print("El artículo con ASIN '" + asin + "' no existe en la base de datos.")
            cursor.close()
            conexion.close()
            return

        # Obtener histograma de notas para ese artículo
        sql = """SELECT overall, COUNT(*) AS total
                 FROM reviews
                 WHERE asin = %s
                 GROUP BY overall
                 ORDER BY overall"""
        cursor.execute(sql, [asin])
        titulo = "Histograma de notas - Artículo " + asin
    else:
        # Pedir categoría
        categoria = pedir_categoria(permitir_todo=True)
        if categoria is None:
            cursor.close()
            conexion.close()
            return

        if categoria == "todo":
            # Histograma global de todas las categorías
            sql = """SELECT overall, COUNT(*) AS total
                     FROM reviews
                     GROUP BY overall
                     ORDER BY overall"""
            cursor.execute(sql)
            titulo = "Histograma de notas (todas las categorías)"
        else:
            # Histograma filtrado por categoría
            sql = """SELECT r.overall, COUNT(*) AS total
                     FROM reviews r
                     INNER JOIN products p ON r.asin = p.asin
                     WHERE p.category = %s
                     GROUP BY r.overall
                     ORDER BY r.overall"""
            cursor.execute(sql, [categoria])
            titulo = "Histograma de notas - " + categoria

    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # comprobar si hay resultados
    if not resultados:
        print("No se han encontrado resultados.")
        return

    # Separar notas y totales 
    notas = [str(int(fila[0])) for fila in resultados]
    totales = [fila[1] for fila in resultados]

    # Crear histograma
    plt.figure(figsize=(8, 6))
    sns.barplot(x=notas, y=totales, color="coral")
    plt.title(titulo)
    plt.xlabel("Nota (overall)")
    plt.ylabel("Número de reviews")
    plt.tight_layout()
    plt.show()


# opción 4: Evolución de reviews a lo largo del tiempo por categoría
def evolucion_reviews_tiempo():
    """
    Muestra la evolución del número de reviews acumuladas a lo largo del
    tiempo para todas las categorías de producto. 
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    # Obtener todas las categorías existentes en la base de datos
    sql = """SELECT DISTINCT category FROM products ORDER BY category"""
    cursor.execute(sql)
    categorias = [fila[0] for fila in cursor.fetchall()]

    plt.figure(figsize=(14, 7))

    for categoria in categorias:
        # Obtener los timestamps de las reviews de esta categoría ordenados
        sql = """SELECT r.unixReviewTime
                 FROM reviews r
                 INNER JOIN products p ON r.asin = p.asin
                 WHERE p.category = %s
                 ORDER BY r.unixReviewTime ASC"""
        cursor.execute(sql, [categoria])
        resultados = cursor.fetchall()

        if not resultados:
            continue

        # Extraer los timestamps y calcular el acumulado
        timestamps = [fila[0] for fila in resultados]
        acumulado = list(range(1, len(timestamps) + 1))
        plt.plot(timestamps, acumulado, label=categoria, linewidth=1.5)

    cursor.close()
    conexion.close()

    plt.title("Evolución del número de reviews a lo largo del tiempo")
    plt.xlabel("Tiempo (Unix Timestamp)")
    plt.ylabel("Número de reviews acumuladas")
    plt.legend()
    plt.tight_layout()
    plt.show()


# opción 5: Histograma de reviews por usuario
def histograma_reviews_por_usuario():
    """
    Obtiene un histograma donde el eje X indica el número de reviews
    y el eje Y indica el número de usuarios que han hecho esa cantidad de reviews. 
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    # obtener cuántas reviews ha hecho cada usuario
    sql = """SELECT reviewerID, COUNT(*) AS total_reviews
             FROM reviews
             GROUP BY reviewerID"""
    cursor.execute(sql)
    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # Comprobar si hay resultados
    if not resultados:
        print("No se han encontrado resultados.")
        return

    # Número de reviews por usuario
    reviews_por_usuario = [fila[1] for fila in resultados]

    # Contamos cuántos usuarios tienen cada número de reviews
    conteo = {}
    for num in reviews_por_usuario:
        if num in conteo:
            conteo[num] += 1
        else:
            conteo[num] = 1

    # Ordenar por número de reviews
    num_reviews_ordenado = sorted(conteo.keys())
    num_usuarios = [conteo[k] for k in num_reviews_ordenado]

    # histograma
    plt.figure(figsize=(12, 6))
    plt.bar(num_reviews_ordenado, num_usuarios, color="teal", width=0.8)
    plt.title("Histograma de reviews por usuario")
    plt.xlabel("Número de reviews")
    plt.ylabel("Número de usuarios")
    plt.tight_layout()
    plt.show()


# opción 6: Nube de palabras por categoría
def nube_de_palabras():
    """
    Genera nube de palabras a partir del campo summary de las reviews
    de una categoría seleccionada por el usuario.
    """
    # Pedir categoría al usuario sin opción de todas
    categoria = pedir_categoria(permitir_todo=False)
    if categoria is None:
        return

    # Obtener los asin de esa categoría desde mySQL
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()
    sql = """SELECT asin FROM products WHERE category = %s"""
    cursor.execute(sql, [categoria])
    asins = [fila[0] for fila in cursor.fetchall()]
    cursor.close()
    conexion.close()

    # Obtener los summaries de MongoDB filtrando por los asin obtenidos
    client, db = crear_conexion_mongo()
    coleccion = db[MONGO_COLLECTION_REVIEWS]
    # filtrar por los asin de la categoría
    resultados = coleccion.find(
        {"asin": {"$in": asins}},
        {"summary": 1, "_id": 0}
    )

    # Construir texto concatenando los summaries filtrados
    texto = ""
    for doc in resultados:
        summary = doc.get("summary", "")
        if summary:
            # Filtrar palabras de longitud mayor que 3
            palabras = [p for p in summary.split() if len(p) > 3]
            texto += " ".join(palabras) + " "

    client.close()

    # Comprobar que haya texto para crear la nube
    if not texto.strip():
        print("No se han encontrado datos para generar la nube de palabras.")
        return

    # crear la nube de palabras con wordcloud
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color="white",
        max_words=100
    ).generate(texto)

    # Mostrarla 
    plt.figure(figsize=(12, 6))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.title("Nube de palabras - " + categoria)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


# opción 7: Nota media por categoría
def nota_media_por_categoria():
    """
    Muestra un gráfico de barras con la nota media de cada categoría de producto. 
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    sql = """SELECT p.category, AVG(r.overall) AS media
             FROM reviews r
             INNER JOIN products p ON r.asin = p.asin
             GROUP BY p.category
             ORDER BY media DESC"""
    cursor.execute(sql)
    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # comprobar si hay resultados
    if not resultados:
        print("No se han encontrado resultados.")
        return

    # Separar categorías y medias 
    categorias = [fila[0] for fila in resultados]
    medias = [round(fila[1], 2) for fila in resultados]

    # gráfico de barras
    plt.figure(figsize=(10, 6))
    barras = sns.barplot(x=categorias, y=medias, color="mediumpurple")
    plt.title("Nota media por categoría de producto")
    plt.xlabel("Categoría")
    plt.ylabel("Nota media (overall)")
    plt.ylim(0, 5.5)

    # Poner el valor de la media encima de cada barra
    for i, v in enumerate(medias):
        barras.text(i, v + 0.1, str(v), ha="center", fontweight="bold")

    plt.tight_layout()
    plt.show()


# opción 8: Recomendación de artículos (Parte 5)
def recomendar_articulos():
    """
    Dado un identificador original de usuario y un tipo de artículo devuelve
    los 10 artículos más populares de ese tipo que el usuario no ha consumido.
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    # Pedir ID del usuario
    reviewer_id = input("Introduce el reviewerID del usuario: ").strip()

    # Comprobar que el usuario existe en la base de datos
    sql = """SELECT reviewerID, reviewerName FROM reviewers WHERE reviewerID = %s"""
    cursor.execute(sql, [reviewer_id])
    usuario = cursor.fetchone()

    if not usuario:
        print("No se ha encontrado el usuario con ID: " + reviewer_id)
        cursor.close()
        conexion.close()
        return

    print("Usuario encontrado: " + str(usuario[1]))

    # Pedir tipo de artículo
    print("Selecciona el tipo de artículo:")
    print("1. Toys_and_Games")
    print("2. Video_Games")
    print("3. Digital_Music")
    print("4. Musical_Instruments")
    print("5. Office_Products")
    opcion = input("Selecciona una opción (1-5): ").strip()

    categorias = {
        "1": "Toys_and_Games",
        "2": "Video_Games",
        "3": "Digital_Music",
        "4": "Musical_Instruments",
        "5": "Office_Products"
    }

    # Validar opción seleccionada
    if opcion not in categorias:
        print("Opción no válida.")
        cursor.close()
        conexion.close()
        return

    categoria = categorias[opcion]

    # Obtener los 10 artículos más populares de esa categoría que el usuario no ha consumido antes
    sql = """SELECT p.asin, COUNT(*) AS total_reviews
             FROM reviews r
             INNER JOIN products p ON r.asin = p.asin
             WHERE p.category = %s
             AND p.asin NOT IN (
                 SELECT asin FROM reviews WHERE reviewerID = %s
             )
             GROUP BY p.asin
             ORDER BY total_reviews DESC
             LIMIT 10"""
    cursor.execute(sql, [categoria, reviewer_id])
    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # Mostrar resultados
    if not resultados:
        print("No se han encontrado artículos para recomendar.")
        return

    print("\nTop 10 artículos de " + categoria + " recomendados para " + reviewer_id + ":")
    print("-" * 50)
    for i, fila in enumerate(resultados):
        print(str(i + 1) + ". " + fila[0] + " (" + str(fila[1]) + " reviews)")


def mostrar_menu():
    """
    Muestra el menú principal de la aplicación de visualización
    """
    print("\n" + "=" * 55)
    print("   MENÚ DE VISUALIZACIÓN - Reviews Amazon")
    print("=" * 55)
    print("1. Evolución de reviews por años")
    print("2. Evolución de la popularidad de los artículos")
    print("3. Histograma por nota")
    print("4. Evolución de reviews a lo largo del tiempo")
    print("5. Histograma de reviews por usuario")
    print("6. Nube de palabras por categoría")
    print("7. Nota media por categoría (gráfica extra)")
    print("8. Recomendación de artículos")
    print("9. Salir")
    print("=" * 55)


def main():
    """
    Función principal que ejecuta el menú de visualización.
    """
    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción (1-9): ").strip()

        try:
            if opcion == "1":
                evolucion_reviews_por_anio()
            elif opcion == "2":
                evolucion_popularidad_articulos()
            elif opcion == "3":
                histograma_por_nota()
            elif opcion == "4":
                evolucion_reviews_tiempo()
            elif opcion == "5":
                histograma_reviews_por_usuario()
            elif opcion == "6":
                nube_de_palabras()
            elif opcion == "7":
                nota_media_por_categoria()
            elif opcion == "8":
                recomendar_articulos()
            elif opcion == "9":
                print("Saliendo del programa...")
                break
            else:
                print("Opción no válida. Introduce un número del 1 al 9.")
        except Exception as e:
            print("Se ha producido un error: " + str(e))
            print("Por favor, inténtalo de nuevo.")


if __name__ == "__main__":
    main()