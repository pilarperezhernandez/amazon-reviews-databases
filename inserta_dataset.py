"""
Proyecto Bases de Datos - Reviews Amazon
Inserción de un nuevo dataset en la base de datos
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
    DATA_PATH
)


# CONFIGURACIÓN DEL NUEVO DATASET
# Ruta del nuevo fichero de reviews
NUEVO_FICHERO = DATA_PATH + "Office_Products_5.json"
# Nombre de la categoría del nuevo dataset
NUEVA_CATEGORIA = "Office_Products"


# FUNCIONES DE CONEXIÓN
def crear_conexion_mysql():
    """
    Crea una conexión a MySQL con la base de datos del proyecto.
    Devuelve: 
        conexión a MySQL
    """
    # Establecer la conexión con MySQL
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
    # Acceder a la base de datos
    db = client[MONGO_DB]
    return client, db


# FUNCIÓN DE PARSEO DE FECHA
def parsear_fecha(fecha_str):
    """
    Parsea la fecha del formato del JSON (ej: '02 28, 2014') a un objeto date.
    Parametros:
        fecha_str: cadena con la fecha en formato 'MM DD, YYYY'
    Devuelve:
        objeto datetime.date
    """
    # Convertir la cadena de fecha a un objeto date
    fecha = datetime.strptime(fecha_str.strip(), "%m %d, %Y")
    return fecha.date()


# FUNCIÓN PRINCIPAL DE CARGA DEL NUEVO DATASET
def insertar_nuevo_dataset():
    """
    Lee el nuevo fichero JSON línea a línea e inserta los datos en MySQL y MongoDB. 
    Tiene en cuenta que un usuario puede existir ya en la base
    de datos si ha hecho reviews en otros conjuntos de datos.
    """
    print("Insertando nuevo dataset: " + NUEVA_CATEGORIA)
    print("Fichero: " + NUEVO_FICHERO)

    # Conexión a MySQL
    conexion_mysql = crear_conexion_mysql()
    cursor_mysql = conexion_mysql.cursor()

    # Conexión a MongoDB
    client_mongo, db_mongo = crear_conexion_mongo()
    coleccion_mongo = db_mongo[MONGO_COLLECTION_REVIEWS]

    # Obtener los reviewers y products que ya existen en la base de datos
    cursor_mysql.execute("SELECT reviewerID FROM reviewers")
    reviewers_existentes = set(fila[0] for fila in cursor_mysql.fetchall())	# Set de reviewers ya insertados
    print("Reviewers ya existentes en la BBDD: " + str(len(reviewers_existentes)))

    cursor_mysql.execute("SELECT asin FROM products")
    products_existentes = set(fila[0] for fila in cursor_mysql.fetchall())	# Set de los products ya insertados
    print("Products ya existentes en la BBDD: " + str(len(products_existentes)))

    contador = 0
    nuevos_reviewers = 0
    nuevos_products = 0

    # Leer el fichero línea a línea
    with open(NUEVO_FICHERO, "r", encoding="utf-8") as fichero:
        for linea in fichero:
            linea = linea.strip()
            if not linea:
                continue

            # Parsear la línea JSON
            review = json.loads(linea)

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
            if reviewer_id not in reviewers_existentes:
                sql = """INSERT INTO reviewers (reviewerID, reviewerName)
                         VALUES (%s, %s)"""
                try:
                    cursor_mysql.execute(sql, [reviewer_id, reviewer_name])
                    reviewers_existentes.add(reviewer_id)
                    nuevos_reviewers += 1
                except pymysql.IntegrityError:
                    # Ya existe por una inserción concurrente
                    reviewers_existentes.add(reviewer_id)

            # Insertar product si no existe
            if asin not in products_existentes:
                sql = """INSERT INTO products (asin, category)
                         VALUES (%s, %s)"""
                try:
                    cursor_mysql.execute(sql, [asin, NUEVA_CATEGORIA])
                    products_existentes.add(asin)
                    nuevos_products += 1
                except pymysql.IntegrityError:
                    products_existentes.add(asin)

            # Insertar la review en MySQL
            sql = """INSERT INTO reviews (reviewerID, asin, overall, helpful_votes,
                     total_votes, reviewDate, unixReviewTime)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            cursor_mysql.execute(sql, [reviewer_id, asin, overall, helpful_votes,
                                       total_votes, review_date, unix_time])

            # Insertar la review en MongoDB
            documento = {
                "reviewerID": reviewer_id,
                "asin": asin,
                "reviewText": review.get("reviewText", ""),
                "summary": review.get("summary", ""),
                "overall": overall
            }
            coleccion_mongo.insert_one(documento)

            contador += 1
            if contador % 10000 == 0:
                conexion_mysql.commit()	# Hacer commit cada 10000 reviews
                print("  " + str(contador) + " reviews procesadas...")

    # Commit final
    conexion_mysql.commit()

    # Mostrar resumen de la carga
    print("=" * 50)
    print("CARGA DEL NUEVO DATASET COMPLETADA")
    print("Categoría: " + NUEVA_CATEGORIA)
    print("Total de reviews insertadas: " + str(contador))
    print("Nuevos reviewers añadidos: " + str(nuevos_reviewers))
    print("Nuevos products añadidos: " + str(nuevos_products))
    print("=" * 50)

    # Cerrar conexiones
    cursor_mysql.close()
    conexion_mysql.close()
    client_mongo.close()


if __name__ == "__main__":
    insertar_nuevo_dataset()