"""
Proyecto Bases de Datos - Reviews Amazon
Exportar datos de MySQL a Excel para Tableau
Pilar Pérez Hernández
María Roca Ramón
"""

import pymysql
from openpyxl import Workbook
from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
)


def exportar_datos():
    """
    Exporta los datos de MySQL a un fichero Excel con las columnas necesarias
    para poder crear las gráficas en Tableau.
    """
    # Conectar a MySQL
    conexion = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conexion.cursor()

    # Consulta que une reviews con products para tener la categoría
    sql = """SELECT r.id, r.reviewerID, r.asin, r.overall,
                    r.helpful_votes, r.total_votes, r.reviewDate,
                    p.category
             FROM reviews r
             INNER JOIN products p ON r.asin = p.asin"""
    cursor.execute(sql)
    resultados = cursor.fetchall()

    # Crear el libro de Excel
    wb = Workbook() 
    ws = wb.active  # Obtener la hoja activa
    ws.title = "Reviews"

    # Escribir la cabecera
    ws.append(["id", "reviewerID", "asin", "overall",
               "helpful_votes", "total_votes", "reviewDate", "category"])

    # Escribir los datos fila a fila
    for fila in resultados:
        # Convertir la fecha a string para evitar problemas
        fila_lista = list(fila)
        fila_lista[6] = str(fila_lista[6])	# Convertir reviewDate a string
        ws.append(fila_lista)

    # Guardar el fichero
    wb.save("data/datos_tableau.xlsx")

    print("Datos exportados a data/datos_tableau.xlsx")
    print("Total de filas: " + str(len(resultados)))

    cursor.close()
    conexion.close()


if __name__ == "__main__":
    exportar_datos()