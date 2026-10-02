"""
Proyecto Bases de Datos - Reviews Amazon
Carga de datos en MySQL y MongoDB
Pilar Pérez Hernández
María Roca Ramón
"""

import json
from datetime import datetime
import pymysql
from pymongo import MongoClient
from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_CONNECTION_STRING, MONGO_DB, MONGO_COLLECTION_REVIEWS,
    FICHEROS_REVIEWS
)


# FUNCIONES DE MySQL
def crear_conexion_mysql_sin_db():
    """
    Crea una conexión a MySQL sin especificar base de datos.
    Se usa para crear la base de datos.
    Devuelve: 
        conexión a MySQL
    """
    conexion = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    return conexion

def crear_conexion_mysql():
    """
    Crea una conexión a MySQL especificando la base de datos.
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


def crear_base_datos_mysql():
    """
    Crea la base de datos de MySQL si no existe.
    Si ya existe, la elimina y la vuelve a crear para partir de cero.
    """
    conexion = crear_conexion_mysql_sin_db()
    cursor = conexion.cursor()
    cursor.execute("DROP DATABASE IF EXISTS " + MYSQL_DB)
    cursor.execute("CREATE DATABASE " + MYSQL_DB)
    print("Base de datos '" + MYSQL_DB + "' creada en MySQL.")
    cursor.close()
    conexion.close()


def crear_tablas_mysql():
    """
    Crea las tablas de reviewers, products y reviews en MySQL.
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    sql_reviewers = """CREATE TABLE reviewers (
        reviewerID VARCHAR(50) NOT NULL,
        reviewerName VARCHAR(255),
        PRIMARY KEY (reviewerID)
    )"""
    cursor.execute(sql_reviewers)

    sql_products = """CREATE TABLE products (
        asin VARCHAR(20) NOT NULL,
        category VARCHAR(50) NOT NULL,
        PRIMARY KEY (asin)
    )"""
    cursor.execute(sql_products)

    sql_reviews = """CREATE TABLE reviews (
        id INT AUTO_INCREMENT,
        reviewerID VARCHAR(50) NOT NULL,
        asin VARCHAR(20) NOT NULL,
        overall FLOAT NOT NULL,
        helpful_votes INT NOT NULL,
        total_votes INT NOT NULL,
        reviewDate DATE NOT NULL,
        unixReviewTime INT NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY (reviewerID) REFERENCES reviewers(reviewerID),
        FOREIGN KEY (asin) REFERENCES products(asin)
    )"""
    cursor.execute(sql_reviews)

    conexion.commit()
    print("Tablas creadas en MySQL: reviewers, products, reviews.")
    cursor.close()
    conexion.close()


def parsear_fecha(fecha_str):
    """
    Parsea la fecha del formato del JSON (ej: '02 28, 2014') a un objeto date
    Parametros:
        fecha_str: cadena con la fecha en formato 'MM DD, YYYY'
    Devuelve:
        objeto datetime.date
    """
    fecha = datetime.strptime(fecha_str.strip(), "%m %d, %Y")
    return fecha.date()


def insertar_datos_mysql(review, categoria, cursor, reviewers_insertados, products_insertados):
    """
    Inserta los datos de una review en las tablas de MySQL.
    Parametros:
        review: diccionario con los datos de la review
        categoria: tipo de producto (Toys_and_Games, Video_Games, etc.)
        cursor: cursor de la conexión MySQL
        reviewers_insertados: set con los reviewerID ya insertados
        products_insertados: set con los asin ya insertados
    """
    reviewer_id = review["reviewerID"]
    asin = review["asin"]
    reviewer_name = review.get("reviewerName", "")
    overall = review["overall"]
    helpful = review["helpful"]
    helpful_votes = helpful[0]
    total_votes = helpful[1]
    review_date = parsear_fecha(review["reviewTime"])
    unix_time = review["unixReviewTime"]

    # Insertar reviewer si no existe
    if reviewer_id not in reviewers_insertados:
        sql = """INSERT INTO reviewers (reviewerID, reviewerName)
                 VALUES (%s, %s)"""
        try:
            cursor.execute(sql, [reviewer_id, reviewer_name])
            reviewers_insertados.add(reviewer_id)
        except pymysql.IntegrityError:
            # Ya existe en la base de datos (de una ejecución anterior parcial)
            reviewers_insertados.add(reviewer_id)

    # Insertar product si no existe
    if asin not in products_insertados:
        sql = """INSERT INTO products (asin, category)
                 VALUES (%s, %s)"""
        try:
            cursor.execute(sql, [asin, categoria])
            products_insertados.add(asin)
        except pymysql.IntegrityError:
            products_insertados.add(asin)

    # Insertar review
    sql = """INSERT INTO reviews (reviewerID, asin, overall, helpful_votes,
             total_votes, reviewDate, unixReviewTime)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    cursor.execute(sql, [reviewer_id, asin, overall, helpful_votes,
                         total_votes, review_date, unix_time])


# FUNCIONES DE MongoDB
def crear_conexion_mongo():
    """
    Crea una conexión a MongoDB y devuelve la base de datos.
    Devuelve: 
        base de datos de MongoDB
    """
    client = MongoClient(MONGO_CONNECTION_STRING)
    return client

def crear_base_datos_mongo():
    """
    Elimina la base de datos de MongoDB si existe y la prepara para insertar datos.
    """
    client = crear_conexion_mongo()
    client.drop_database(MONGO_DB)
    print("Base de datos '" + MONGO_DB + "' preparada en MongoDB.")
    client.close()


def insertar_dato_mongo(review, coleccion):
    """
    Inserta los datos textuales de una review en MongoDB.
    Parametros:
        review: diccionario con los datos de la review
        coleccion: colección de MongoDB donde insertar
    """
    documento = {
        "reviewerID": review["reviewerID"],
        "asin": review["asin"],
        "reviewText": review.get("reviewText", ""),
        "summary": review.get("summary", ""),
        "overall": review["overall"]
    }
    coleccion.insert_one(documento)


# FUNCION PRINCIPAL DE CARGA
def cargar_datos():
    """
    Funcion principal que lee los ficheros JSON línea a línea
    e inserta los datos en MySQL y MongoDB.
    """
    # Crear bases de datos
    crear_base_datos_mysql()
    crear_tablas_mysql()
    crear_base_datos_mongo()

    # Conexiones
    conexion_mysql = crear_conexion_mysql()
    cursor_mysql = conexion_mysql.cursor()
    client_mongo = crear_conexion_mongo()
    db_mongo = client_mongo[MONGO_DB]
    coleccion_mongo = db_mongo[MONGO_COLLECTION_REVIEWS]

    # Sets para controlar duplicados
    reviewers_insertados = set()
    products_insertados = set()

    total_reviews = 0

    for categoria, ruta_fichero in FICHEROS_REVIEWS.items():
        print("Cargando fichero: " + ruta_fichero + " ...")
        contador = 0

        with open(ruta_fichero, "r", encoding="utf-8") as fichero:
            for linea in fichero:
                linea = linea.strip()
                if not linea:
                    continue

                review = json.loads(linea)

                # MySQL
                insertar_datos_mysql(review, categoria, cursor_mysql,
                                     reviewers_insertados, products_insertados)
                # MongoDB
                insertar_dato_mongo(review, coleccion_mongo)

                contador += 1
                # Hago commit cada 10.000 reviews para no saturar la memoria
                if contador % 10000 == 0:
                    conexion_mysql.commit()
                    print("  " + str(contador) + " reviews procesadas...")

        # Commit final del fichero
        conexion_mysql.commit()
        total_reviews += contador
        print("Fichero " + categoria + " completado: " + str(contador) + " reviews.")

    print("=" * 50)
    print("CARGA COMPLETADA")
    print("Total de reviews insertadas: " + str(total_reviews))
    print("Reviewers únicos: " + str(len(reviewers_insertados)))
    print("Products únicos: " + str(len(products_insertados)))
    print("=" * 50)

    cursor_mysql.close()
    conexion_mysql.close()
    client_mongo.close()


if __name__ == "__main__":
    cargar_datos()