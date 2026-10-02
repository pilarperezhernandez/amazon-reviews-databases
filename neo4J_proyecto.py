"""
Proyecto Bases de Datos - Reviews Amazon
Aplicación Python junto con Neo4J
Pilar Pérez Hernández
María Roca Ramón
"""

import pymysql
import random
import csv
from neo4j import GraphDatabase
from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
)
# CTE PARA EL NÚMERO DE USUARIOS 
# número de usuarios con más reviews a considerar para similitudes
N_USUARIOS = 30

# FUNCIONES DE CONEXIÓN
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


def crear_driver_neo4j():
    """
    Crea el driver de conexión a Neo4J.
    Devuelve: 
        driver de Neo4J
    """
    # Crear el driver indicando la URI y las credenciales
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return driver


def limpiar_neo4j(driver):
    """
    Elimina todos los nodos y relaciones de Neo4J.
    Parámetros:
        driver: driver de Neo4J
    """
    with driver.session() as session:
        # Eliminar todos los nodos y sus relaciones
        consulta = "MATCH (n) DETACH DELETE n"
        session.run(consulta)
    print("Base de datos de Neo4J limpiada.")

# opción 1: Similitudes entre usuarios (pearson)
def obtener_top_usuarios(n_usuarios):
    """
    Obtiene los n usuarios con más reviews desde MySQL
    Parámetros:
        n_usuarios: número de usuarios a obtener
    Devuelve:
        lista de reviewerIDs
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    # Consulta para obtener los usuarios con más reviews
    sql = """SELECT reviewerID, COUNT(*) AS total
             FROM reviews
             GROUP BY reviewerID
             ORDER BY total DESC
             LIMIT %s"""
    cursor.execute(sql, [n_usuarios])
    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()

    # Extraer solo los IDs de los usuarios
    usuarios = [fila[0] for fila in resultados]
    print("Top " + str(n_usuarios) + " usuarios obtenidos de MySQL.")
    return usuarios

def obtener_reviews_usuarios(usuarios):
    """
    Obtiene las reviews (asin y overall) de una lista de usuarios desde MySQL
    Parámetros:
        usuarios: lista de reviewerIDs
    Devuelve:
        diccionario {reviewerID: {asin: overall}}
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    reviews_por_usuario = {}

    for usuario in usuarios:
        # Obtener las reviews de cada usuario
        sql = """SELECT asin, overall
                 FROM reviews
                 WHERE reviewerID = %s"""
        cursor.execute(sql, [usuario])
        resultados = cursor.fetchall()

        # Guardar en un diccionario 
        reviews_por_usuario[usuario] = {}
        for fila in resultados:
            reviews_por_usuario[usuario][fila[0]] = fila[1]

    cursor.close()
    conexion.close()

    print("Reviews de los usuarios obtenidas de MySQL.")
    return reviews_por_usuario


def calcular_pearson(reviews_u, reviews_v):
    """
    Calcula la correlación de Pearson entre dos usuarios.
    Parametros:
        reviews_u: diccionario {asin: overall} del usuario u
        reviews_v: diccionario {asin: overall} del usuario v
    Devuelve:
        valor de la correlación de Pearson o None si no hay artículos en común
    """
    # Obtener los artículos puntuados en común 
    articulos_comun = set(reviews_u.keys()) & set(reviews_v.keys())

    # Si no hay en común devolver None
    if len(articulos_comun) == 0:
        return None

    # medias de las valoraciones de cada usuario sobre Iuv
    media_u = sum(reviews_u[a] for a in articulos_comun) / len(articulos_comun)
    media_v = sum(reviews_v[a] for a in articulos_comun) / len(articulos_comun)

    # Calcular numerador de la fórmula de Pearson
    numerador = sum(
        (reviews_u[a] - media_u) * (reviews_v[a] - media_v)
        for a in articulos_comun
    )

    # Calcular dos componentes del denominador
    denominador_u = sum((reviews_u[a] - media_u) ** 2 for a in articulos_comun) ** 0.5
    denominador_v = sum((reviews_v[a] - media_v) ** 2 for a in articulos_comun) ** 0.5

    # Evitar división por cero
    if denominador_u == 0 or denominador_v == 0:
        return None

    # correlación de Pearson
    pearson = numerador / (denominador_u * denominador_v)
    return round(pearson, 4)


def calcular_similitudes(usuarios, reviews_por_usuario):
    """
    Calcula las similitudes de Pearson entre todos los pares de usuarios
    Parámetros:
        usuarios: lista de reviewerIDs
        reviews_por_usuario: diccionario {reviewerID: {asin: overall}}
    Devuelve:
        lista de tuplas (usuario1, usuario2, similitud)
    """
    similitudes = []

    # Recorrer todos los pares de usuarios 
    for i in range(len(usuarios)):
        for j in range(i + 1, len(usuarios)):
            u = usuarios[i]
            v = usuarios[j]

            # calcular correlación de Pearson entre los dos usuarios
            pearson = calcular_pearson(reviews_por_usuario[u], reviews_por_usuario[v])

            # Solo almacenar si hay artículos en común
            if pearson is not None:
                similitudes.append((u, v, pearson))

    print("Similitudes calculadas: " + str(len(similitudes)) + " pares con artículos en común.")

    # Guardamos las similitudes en un fichero auxiliar CSV
    with open("similitudes.csv", "w", newline="", encoding="utf-8") as fichero:
        writer = csv.writer(fichero)
        writer.writerow(["usuario1", "usuario2", "pearson"])
        for u, v, sim in similitudes:
            writer.writerow([u, v, sim])
    print("Similitudes guardadas en el fichero auxiliar 'similitudes.csv'.")

    return similitudes


def cargar_similitudes_neo4j(driver, usuarios, similitudes):
    """
    Carga los usuarios como nodos y las similitudes como relaciones en Neo4J
    Parámetros:
        driver: driver de Neo4J
        usuarios: lista de reviewerIDs
        similitudes: lista de tuplas (usuario1, usuario2, similitud)
    """
    with driver.session() as session:
        # nodo por cada usuario
        for usuario in usuarios:
            consulta = """
                CREATE (u:USER {reviewerID: $reviewerID})
            """
            session.run(consulta, reviewerID=usuario)

        print("Nodos de usuarios creados en Neo4J: " + str(len(usuarios)))

        # relaciones de similitud entre los usuarios
        for u, v, sim in similitudes:
            consulta = """
                MATCH (u1:USER {reviewerID: $id1})
                MATCH (u2:USER {reviewerID: $id2})
                CREATE (u1) - [:SIMILITUD {pearson: $pearson}] -> (u2)
                CREATE (u2) - [:SIMILITUD {pearson: $pearson}] -> (u1)
            """
            session.run(consulta, id1=u, id2=v, pearson=sim)

        print("Relaciones de similitud creadas en Neo4J: " + str(len(similitudes)))

def mostrar_usuario_mas_vecinos(driver):
    """
    Muestra por pantalla el usuario con más vecinos.
    Parámetros:
        driver: driver de Neo4J
    """
    with driver.session() as session:
        consulta = """
            MATCH (u:USER) - [r:SIMILITUD] -> ()
            WITH u, COUNT(r) AS num_vecinos
            ORDER BY num_vecinos DESC
            LIMIT 1
            RETURN u.reviewerID AS usuario, num_vecinos
        """
        resultado = session.run(consulta)
        res = resultado.data()

        if res:
            print("\nUsuario con más vecinos: " + res[0]["usuario"])
            print("Número de vecinos: " + str(res[0]["num_vecinos"]))
        else:
            print("\nNo se encontraron usuarios con vecinos.")


def opcion_similitudes(driver):
    """
    Ejecuta toda la funcionalidad de la opción 1
    Parámetros:
        driver: driver de Neo4J
    """
    # Limpiar Neo4J antes de empezar
    limpiar_neo4j(driver)
    # top usuarios con más reviews
    usuarios = obtener_top_usuarios(N_USUARIOS)
    # reviews de esos usuarios
    reviews_por_usuario = obtener_reviews_usuarios(usuarios)
    # Calcular similitudes de Pearson y guardarlas en fichero auxiliar
    similitudes = calcular_similitudes(usuarios, reviews_por_usuario)
    # Cargar en Neo4J
    cargar_similitudes_neo4j(driver, usuarios, similitudes)
    # Mostrar el usuario con más vecinos mediante consulta Neo4J
    mostrar_usuario_mas_vecinos(driver)

    print("\nCarga completada. Puedes consultar los datos en Neo4J:")
    print("http://localhost:7474/browser/")
    print("Ejecuta MATCH (n) RETURN n para ver el grafo.")

# opción 2: Enlaces entre usuarios y artículos
def opcion_enlaces_articulos(driver):
    """
    Selecciona n artículos aleatorios de un tipo determinado
    y muestra en Neo4J cada artículo con todos los usuarios que lo han puntuado.
    Parámetros:
        driver: driver de Neo4J
    """
    # Limpiar Neo4J 
    limpiar_neo4j(driver)

    # Pedir tipo de artículo
    print("Selecciona el tipo de artículo:")
    print("1. Toys_and_Games")
    print("2. Video_Games")
    print("3. Digital_Music")
    print("4. Musical_Instruments")
    opcion = input("Selecciona una opción (1-4): ").strip()

    categorias = {
        "1": "Toys_and_Games",
        "2": "Video_Games",
        "3": "Digital_Music",
        "4": "Musical_Instruments"
    }

    # Validar opción
    if opcion not in categorias:
        print("Opción no válida.")
        return

    categoria = categorias[opcion]

    # Pedir número de artículos aleatorios
    n = input("¿Cuántos artículos aleatorios quieres seleccionar?: ").strip()
    if not n.isdigit() or int(n) <= 0:
        print("Número no válido.")
        return
    n = int(n)

    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()
    sql = """SELECT asin FROM products WHERE category = %s"""
    cursor.execute(sql, [categoria])
    todos_los_articulos = [fila[0] for fila in cursor.fetchall()]

    if len(todos_los_articulos) == 0:
        print("No se encontraron artículos de la categoría " + categoria + ".")
        cursor.close()
        conexion.close()
        return

    # Ajustar n si supera total de artículos disponibles
    if n > len(todos_los_articulos):
        n = len(todos_los_articulos)
        print("Se ajusta a " + str(n) + " artículos (máximo disponible).")

    # Seleccionar n artículos aleatorios
    articulos_aleatorios = random.sample(todos_los_articulos, n)
    print("Artículos aleatorios seleccionados: " + str(len(articulos_aleatorios)))

    # Cargar en Neo4J los artículos y sus usuarios con las propiedades del enlace
    with driver.session() as session:
        for asin in articulos_aleatorios:
            # Crear nodo del artículo
            consulta = """
                CREATE (a:ARTICULO {asin: $asin, categoria: $categoria})
            """
            session.run(consulta, asin=asin, categoria=categoria)

            # Obtener los usuarios que han puntuado este artículo con nota y fecha
            sql = """SELECT r.reviewerID, r.overall, r.unixReviewTime
                     FROM reviews r
                     WHERE r.asin = %s"""
            cursor.execute(sql, [asin])
            reviews = cursor.fetchall()

            for review in reviews:
                reviewer_id = review[0]
                overall = review[1]
                tiempo = review[2]

                # Crear nodo del usuario si no existe (MERGE evita duplicados)
                consulta = """
                    MERGE (u:USER {reviewerID: $reviewerID})
                """
                session.run(consulta, reviewerID=reviewer_id)

                # Crear relación entre usuario y artículo con propiedades
                consulta = """
                    MATCH (u:USER {reviewerID: $reviewerID})
                    MATCH (a:ARTICULO {asin: $asin})
                    CREATE (u) - [:HA_PUNTUADO {nota: $nota, tiempo: $tiempo}] -> (a)
                """
                session.run(consulta, reviewerID=reviewer_id, asin=asin,
                            nota=overall, tiempo=tiempo)

    cursor.close()
    conexion.close()

    print("\nCarga completada. Puedes consultar los datos en Neo4J:")
    print("http://localhost:7474/browser/")
    print("Ejecuta MATCH (n) RETURN n para ver el grafo.")

# opción 3: Usuarios con más de un tipo de artículo
def opcion_usuarios_multitipo(driver):
    """
    Selecciona los usuarios que han puntuado artículos de más de un tipo
    y muestra en Neo4J cada usuario con los tipos de artículos que ha puntuado
    Parámetros:
        driver: driver de Neo4J
    """
    limpiar_neo4j(driver)

    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    # Obtener los primeros 400 usuarios ordenados por nombre
    sql = """SELECT DISTINCT rev.reviewerID, rev.reviewerName
             FROM reviewers rev
             ORDER BY rev.reviewerName ASC
             LIMIT 400"""
    cursor.execute(sql)
    usuarios_400 = cursor.fetchall()
    print("Usuarios obtenidos: " + str(len(usuarios_400)))

    with driver.session() as session:
        for usuario in usuarios_400:
            reviewer_id = usuario[0]
            reviewer_name = usuario[1] if usuario[1] else reviewer_id

            # Obtener los tipos de artículos que ha puntuado este usuario y cuántos
            sql = """SELECT p.category, COUNT(*) AS total
                     FROM reviews r
                     INNER JOIN products p ON r.asin = p.asin
                     WHERE r.reviewerID = %s
                     GROUP BY p.category"""
            cursor.execute(sql, [reviewer_id])
            categorias_usuario = cursor.fetchall()

            # Solo incluiyo si ha puntuado artículos de más de un tipo
            if len(categorias_usuario) > 1:
                # nodo del usuario
                consulta = """
                    CREATE (u:USER {reviewerID: $reviewerID, nombre: $nombre})
                """
                session.run(consulta, reviewerID=reviewer_id, nombre=reviewer_name)

                for cat in categorias_usuario:
                    categoria = cat[0]
                    total = cat[1]

                    # nodo del tipo de artículo si no existe
                    consulta = """
                        MERGE (t:TIPO_ARTICULO {nombre: $nombre})
                    """
                    session.run(consulta, nombre=categoria)

                    # relación entre usuario y tipo con el número de artículos
                    consulta = """
                        MATCH (u:USER {reviewerID: $reviewerID})
                        MATCH (t:TIPO_ARTICULO {nombre: $categoria})
                        CREATE (u) - [:HA_CONSUMIDO {num_articulos: $total}] -> (t)
                    """
                    session.run(consulta, reviewerID=reviewer_id,
                                categoria=categoria, total=total)

    cursor.close()
    conexion.close()

    print("\nCarga completada. Puedes consultar los datos en Neo4J:")
    print("http://localhost:7474/browser/")
    print("Ejecuta MATCH (n) RETURN n para ver el grafo.")

# opción 4: Artículos populares y artículos en común
def opcion_articulos_populares(driver):
    """
    Seleccionan los 5 artículos más populares con menos de 40 reviews y se muestran.
    Parámetros:
        driver: driver de Neo4J
    """
    limpiar_neo4j(driver)

    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    # Obtener los 5 artículos más populares con menos de 40 reviews
    sql = """SELECT asin, COUNT(*) AS total
             FROM reviews
             GROUP BY asin
             HAVING COUNT(*) < 40
             ORDER BY total DESC
             LIMIT 5"""
    cursor.execute(sql)
    articulos_populares = cursor.fetchall()

    # Comprobar que se encontraron artículos
    if not articulos_populares:
        print("No se encontraron artículos con menos de 40 reviews.")
        cursor.close()
        conexion.close()
        return

    print("Artículos populares seleccionados:")
    for art in articulos_populares:
        print("  " + art[0] + " - " + str(art[1]) + " reviews")

    # Obtener los asins seleccionados
    asins = [art[0] for art in articulos_populares]

    with driver.session() as session:
        # nodos de artículos
        for asin, total in articulos_populares:
            consulta = """
                CREATE (a:ARTICULO {asin: $asin, num_reviews: $total})
            """
            session.run(consulta, asin=asin, total=total)

        # usuarios que han puntuado esos artículos
        usuarios_set = set()
        for asin in asins:
            sql = """SELECT r.reviewerID
                     FROM reviews r
                     WHERE r.asin = %s"""
            cursor.execute(sql, [asin])
            for fila in cursor.fetchall():
                usuarios_set.add(fila[0])

        # nodos de usuarios
        for usuario in usuarios_set:
            consulta = """
                MERGE (u:USER {reviewerID: $reviewerID})
            """
            session.run(consulta, reviewerID=usuario)

        # relaciones entre usuarios y artículos
        for asin in asins:
            sql = """SELECT r.reviewerID, r.overall
                     FROM reviews r
                     WHERE r.asin = %s"""
            cursor.execute(sql, [asin])
            reviews = cursor.fetchall()

            for review in reviews:
                consulta = """
                    MATCH (u:USER {reviewerID: $reviewerID})
                    MATCH (a:ARTICULO {asin: $asin})
                    CREATE (u) - [:HA_PUNTUADO {nota: $nota}] -> (a)
                """
                session.run(consulta, reviewerID=review[0], asin=asin, nota=review[1])

        # Calcular artículos en común entre pares de usuarios
        print("Calculando artículos en común entre usuarios...")
        usuarios_lista = list(usuarios_set)

        # sacar qué artículos ha puntuado cada usuario
        reviews_por_usuario = {}
        for usuario in usuarios_lista:
            # Construir la consulta parametrizada con los asins
            placeholders = ",".join(["%s"] * len(asins))
            sql = "SELECT asin FROM reviews WHERE reviewerID = %s AND asin IN (" + placeholders + ")"
            params = [usuario] + asins
            cursor.execute(sql, params)
            reviews_por_usuario[usuario] = set(fila[0] for fila in cursor.fetchall())

        # relaciones de artículos en común entre pares de usuarios
        for i in range(len(usuarios_lista)):
            for j in range(i + 1, len(usuarios_lista)):
                u1 = usuarios_lista[i]
                u2 = usuarios_lista[j]
                # Calcular artículos en común
                comun = reviews_por_usuario[u1] & reviews_por_usuario[u2]
                if len(comun) > 0:
                    consulta = """
                        MATCH (u1:USER {reviewerID: $id1})
                        MATCH (u2:USER {reviewerID: $id2})
                        CREATE (u1) - [:ARTICULOS_EN_COMUN {cantidad: $cantidad}] -> (u2)
                    """
                    session.run(consulta, id1=u1, id2=u2, cantidad=len(comun))

    cursor.close()
    conexion.close()

    print("\nCarga completada. Puedes consultar los datos en Neo4J:")
    print("http://localhost:7474/browser/")
    print("Ejecuta MATCH (n) RETURN n para ver el grafo.")


def mostrar_menu():
    """
    Muestra el menú principal de la aplicación de Neo4J.
    """
    print("\n" + "=" * 55)
    print("   MENÚ NEO4J - Reviews Amazon")
    print("=" * 55)
    print("1. Similitudes entre usuarios (Pearson)")
    print("2. Enlaces entre usuarios y artículos aleatorios")
    print("3. Usuarios con más de un tipo de artículo")
    print("4. Artículos populares y artículos en común")
    print("5. Salir")
    print("=" * 55)


def main():
    """
    Función principal que ejecuta el menú de Neo4J
    """
    driver = crear_driver_neo4j()

    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción (1-5): ").strip()

        try:
            if opcion == "1":
                opcion_similitudes(driver)
            elif opcion == "2":
                opcion_enlaces_articulos(driver)
            elif opcion == "3":
                opcion_usuarios_multitipo(driver)
            elif opcion == "4":
                opcion_articulos_populares(driver)
            elif opcion == "5":
                print("Saliendo del programa...")
                driver.close()
                break
            else:
                print("Opción no válida. Introduce un número del 1 al 5.")
        except Exception as e:
            print("Se ha producido un error: " + str(e))
            print("Por favor, inténtalo de nuevo.")


if __name__ == "__main__":
    main()