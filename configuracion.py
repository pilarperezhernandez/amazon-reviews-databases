"""
Proyecto Bases de Datos - Reviews Amazon
Configuración de conexiones y rutas de datos
Pilar Pérez Hernández
María Roca Ramón
"""

import os

# Las credenciales se leen de variables de entorno (ver README).

# CONFIGURACIÓN DE MySQL
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = "reviews_amazon"

# CONFIGURACIÓN DE MongoDB
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_CONNECTION_STRING = "mongodb://localhost:27017"
MONGO_DB = "reviews_amazon"
MONGO_COLLECTION_REVIEWS = "reviews"

# CONFIGURACIÓN DE Neo4J
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")

# RUTAS DE LOS FICHEROS DE DATOS
DATA_PATH = "data/"

FICHEROS_REVIEWS = {
    "Toys_and_Games": DATA_PATH + "Toys_and_Games_5.json",
    "Video_Games": DATA_PATH + "Video_Games_5.json",
    "Digital_Music": DATA_PATH + "Digital_Music_5.json",
    "Musical_Instruments": DATA_PATH + "Musical_Instruments_5.json"
}