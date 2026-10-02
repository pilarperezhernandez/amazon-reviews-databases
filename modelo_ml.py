"""
Proyecto Bases de Datos - Reviews Amazon
Implementación del modelo de Machine Learning
Filtrado colaborativo basado en usuarios (User-Based Collaborative Filtering)
Pilar Pérez Hernández
María Roca Ramón
"""

import pymysql
import random
import math
from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
)

# PARAMS DEL MODELO
# num de vecinos más similares a considerar
K_VECINOS = 20
# proporcion de datos para entrenamiento
PROPORCION_TRAIN = 0.8
# num mínimo de artículos en común para considerar similitud
MIN_ARTICULOS_COMUN = 2
# categoría sobre la que trabajar
CATEGORIA = "Video_Games"
# num de usuarios a considerar para el modelo
N_USUARIOS_MODELO = 200

# FUNCIONES DE CONEXIÓN
def crear_conexion_mysql():
    """
    Crea una conexión a MySQL con la base de datos del proyecto.
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

# OBTENCIÓN DE DATOS
def obtener_usuarios_activos(categoria, n_usuarios):
    """
    Obtiene los n usuarios con más reviews en una categoría específica.
    Parámetros:
        categoria: categoría de producto
        n_usuarios: número máximo de usuarios a obtener
    Devuelve:
        lista de reviewerIDs
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    sql = """SELECT r.reviewerID, COUNT(*) AS total
             FROM reviews r
             INNER JOIN products p ON r.asin = p.asin
             WHERE p.category = %s
             GROUP BY r.reviewerID
             HAVING COUNT(*) >= 5
             ORDER BY total DESC
             LIMIT %s"""
    cursor.execute(sql, [categoria, n_usuarios])
    usuarios = [fila[0] for fila in cursor.fetchall()]

    cursor.close()
    conexion.close()

    print("Usuarios activos obtenidos: " + str(len(usuarios)))
    return usuarios


def obtener_reviews_categoria(usuarios, categoria):
    """
    Obtiene todas las reviews (asin, overall) de los usuarios dados para una categoría específica.
    Parámetros:
        usuarios: lista de reviewerIDs
        categoria: categoría de producto
    Devuelve:
        diccionario {reviewerID: {asin: overall}}
    """
    conexion = crear_conexion_mysql()
    cursor = conexion.cursor()

    reviews_por_usuario = {}

    for usuario in usuarios:
        sql = """SELECT r.asin, r.overall
                 FROM reviews r
                 INNER JOIN products p ON r.asin = p.asin
                 WHERE r.reviewerID = %s AND p.category = %s"""
        cursor.execute(sql, [usuario, categoria])
        resultados = cursor.fetchall()

        reviews_por_usuario[usuario] = {}
        for fila in resultados:
            reviews_por_usuario[usuario][fila[0]] = fila[1]

    cursor.close()
    conexion.close()

    total_reviews = sum(len(v) for v in reviews_por_usuario.values())
    print("Reviews obtenidas: " + str(total_reviews) + " de " +
          str(len(usuarios)) + " usuarios.")
    return reviews_por_usuario

# DIVISIÓN TRAIN Y TEST
def dividir_train_test(reviews_por_usuario, proporcion_train):
    """
    Divide las reviews de cada usuario en conjuntos de entrenamiento y test.
    Parámetros:
        reviews_por_usuario: diccionario {reviewerID: {asin: overall}}
        proporcion_train: proporción de reviews para entrenamiento (ej: 0.8)
    Devuelve:
        tupla (train, test) con la misma estructura de diccionarios
    """
    train = {}
    test = {}

    total_train = 0
    total_test = 0

    # Para cada usuario barajar sus reviews y dividir según la proporción dada
    for usuario, reviews in reviews_por_usuario.items():
        articulos = list(reviews.keys())
        random.shuffle(articulos)

        # Calcular el punto de corte para train/test
        n_train = max(1, int(len(articulos) * proporcion_train))

        train[usuario] = {}
        test[usuario] = {}
        # Asignar las reviews a train o test según el punto de corte
        for i, asin in enumerate(articulos):
            if i < n_train:
                train[usuario][asin] = reviews[asin]
                total_train += 1
            else:
                test[usuario][asin] = reviews[asin]
                total_test += 1

    print("División train/test completada:")
    print("  Train: " + str(total_train) + " reviews")
    print("  Test: " + str(total_test) + " reviews")
    return train, test

# CÁLCULO SIMILITUDES CON PEARSON
def calcular_pearson(reviews_u, reviews_v, min_comun):
    """
    Calcula la correlación de Pearson entre dos usuarios usando
    solo los artículos puntuados en común.
        Parámetros:
        reviews_u: diccionario {asin: overall} del usuario u
        reviews_v: diccionario {asin: overall} del usuario v
        min_comun: número mínimo de artículos en común requeridos
    Devuelve:
        valor de la correlación de Pearson o None
    """
    # Obtener artículos en común
    articulos_comun = set(reviews_u.keys()) & set(reviews_v.keys())
    # Si no tienen suficientes artículos en común no se puede calcular la similitud
    if len(articulos_comun) < min_comun:
        return None

    # Medias sobre los artículos en común
    media_u = sum(reviews_u[a] for a in articulos_comun) / len(articulos_comun)
    media_v = sum(reviews_v[a] for a in articulos_comun) / len(articulos_comun)

    # Numerador
    numerador = sum(
        (reviews_u[a] - media_u) * (reviews_v[a] - media_v)
        for a in articulos_comun
    )

    # Denominador
    den_u = math.sqrt(sum((reviews_u[a] - media_u) ** 2 for a in articulos_comun))
    den_v = math.sqrt(sum((reviews_v[a] - media_v) ** 2 for a in articulos_comun))

    if den_u == 0 or den_v == 0:
        return None

    return numerador / (den_u * den_v)


def calcular_todas_similitudes(train, usuarios):
    """
    Calcula la matriz de similitudes de Pearson entre todos los pares
    de usuarios usando solo los datos de entrenamiento.
    Parámetros:
        train: diccionario {reviewerID: {asin: overall}} de entrenamiento
        usuarios: lista de reviewerIDs
    Devuelve:
        diccionario {(u1, u2): pearson}
    """
    similitudes = {}
    pares_calculados = 0

    for i in range(len(usuarios)):
        # Solo calcular la mitad superior de la matriz
        for j in range(i + 1, len(usuarios)):
            u = usuarios[i]
            v = usuarios[j]

            pearson = calcular_pearson(train[u], train[v], MIN_ARTICULOS_COMUN)
            # Solo almacenamos similitudes positivas para optimizar la búsqueda de vecinos
            if pearson is not None:
                similitudes[(u, v)] = pearson
                similitudes[(v, u)] = pearson
                pares_calculados += 1

    print("Similitudes calculadas: " + str(pares_calculados) + " pares.")
    return similitudes

# PREDICCIÓN DE PUNTUACIONES
def obtener_vecinos(usuario, usuarios, similitudes, k):
    """
    Obtiene los K vecinos más similares a un usuario dado considerando solo similitudes positivas.
    Parámetros:
        usuario: reviewerID del usuario objetivo
        usuarios: lista de todos los reviewerIDs
        similitudes: diccionario de similitudes
        k: número de vecinos a seleccionar
    Devuelve:
        lista de tuplas (reviewerID_vecino, similitud) ordenada
    """
    vecinos = []

    for otro in usuarios:
        if otro == usuario:
            continue
        # Obtener la similitud entre el usuario y el otro usuario
        sim = similitudes.get((usuario, otro), None)
        if sim is not None and sim > 0:
            vecinos.append((otro, sim))

    # Ordenar por similitud descendente y quedarse con los K primeros
    vecinos.sort(key=lambda x: x[1], reverse=True)
    return vecinos[:k]


def predecir_puntuacion(usuario, articulo, train, vecinos):
    """
    Predice la puntuación que un usuario daría a un artículo usando
    la media ponderada de las puntuaciones de sus vecinos.
    Parámetros:
        usuario: reviewerID del usuario objetivo
        articulo: asin del artículo a predecir
        train: datos de entrenamiento
        vecinos: lista de tuplas (vecino, similitud)
    Devuelve:
        puntuación predicha o None si no se puede predecir
    """
    # Media del usuario objetivo sobre sus datos de entrenamiento
    if len(train[usuario]) == 0:
        return None
    media_u = sum(train[usuario].values()) / len(train[usuario])

    numerador = 0.0
    denominador = 0.0

    for vecino, sim in vecinos:
        # Solo considerar vecinos que hayan puntuado este artículo
        if articulo in train[vecino]:
            media_v = sum(train[vecino].values()) / len(train[vecino])
            numerador += sim * (train[vecino][articulo] - media_v)
            denominador += abs(sim)

    if denominador == 0:
        return None

    prediccion = media_u + (numerador / denominador)

    # Limitar la predicción al rango válido
    prediccion = max(1.0, min(5.0, prediccion))
    return round(prediccion, 2)

# EVALUACIÓN DEL MODELO
def evaluar_modelo(train, test, usuarios, similitudes):
    """
    Evalúa el modelo calculando las predicciones sobre el conjunto de test
    y comparándolas con las puntuaciones reales.
    Calcula las métricas RMSE y MAE.
    Parámetros:
    train: datos de entrenamiento
        test: datos de test
        usuarios: lista de reviewerIDs
        similitudes: diccionario de similitudes
    Devuelve:
        tupla (rmse, mae, n_predicciones, n_fallidas)
    """
    errores_cuadrado = []
    errores_absoluto = []
    predicciones_realizadas = 0
    predicciones_fallidas = 0

    print("\nEvaluando modelo sobre el conjunto de test...")

    for usuario in usuarios:
        if len(test[usuario]) == 0:
            continue

        # Obtener los K vecinos de este usuario
        vecinos = obtener_vecinos(usuario, usuarios, similitudes, K_VECINOS)

        if len(vecinos) == 0:
            predicciones_fallidas += len(test[usuario])
            continue

        # Para cada artículo en el test del usuario predecir la puntuación y compararla con la real
        for articulo, nota_real in test[usuario].items():
            prediccion = predecir_puntuacion(usuario, articulo, train, vecinos)

            if prediccion is not None:
                error = prediccion - nota_real
                errores_cuadrado.append(error ** 2)
                errores_absoluto.append(abs(error))
                predicciones_realizadas += 1
            else:
                predicciones_fallidas += 1

    # Calcular métricas
    if len(errores_cuadrado) == 0:
        print("No se pudieron realizar predicciones.")
        return None, None, 0

    rmse = math.sqrt(sum(errores_cuadrado) / len(errores_cuadrado))
    mae = sum(errores_absoluto) / len(errores_absoluto)

    return rmse, mae, predicciones_realizadas, predicciones_fallidas

# MOSTRAR RECOMENDACIONES
def demostrar_recomendaciones(train, usuarios, similitudes):
    """
    Muestra ejemplos de recomendaciones para algunos usuarios del conjunto
    de datos prediciendo la puntuación que darían a artículos que no han
    consumido y ordenándolos de mayor a menor predicción.
    Parámetros:
        train: datos de entrenamiento
        usuarios: lista de reviewerIDs
        similitudes: diccionario de similitudes
    """
    print("\n" + "=" * 60)
    print("DEMOSTRACIÓN DE RECOMENDACIONES")
    print("=" * 60)

    # Obtener todos los artículos disponibles en el train
    todos_articulos = set()
    for reviews in train.values():
        todos_articulos.update(reviews.keys())

    # Seleccionar 3 usuarios con suficientes vecinos para la demostración
    usuarios_demo = []
    for usuario in usuarios:
        vecinos = obtener_vecinos(usuario, usuarios, similitudes, K_VECINOS)
        if len(vecinos) >= 5:
            usuarios_demo.append(usuario)
        if len(usuarios_demo) >= 3:
            break

    for usuario in usuarios_demo:
        print("\n--- Usuario: " + usuario + " ---")
        print("Reviews en entrenamiento: " + str(len(train[usuario])))

        media_usuario = sum(train[usuario].values()) / len(train[usuario])
        print("Nota media del usuario: " + str(round(media_usuario, 2)))

        vecinos = obtener_vecinos(usuario, usuarios, similitudes, K_VECINOS)
        print("Vecinos encontrados: " + str(len(vecinos)))

        # Predecir para artículos que no ha consumido
        predicciones = []
        articulos_consumidos = set(train[usuario].keys())

        for articulo in todos_articulos:
            if articulo not in articulos_consumidos:
                pred = predecir_puntuacion(usuario, articulo, train, vecinos)
                if pred is not None:
                    predicciones.append((articulo, pred))

        # Ordenar por predicción descendente
        predicciones.sort(key=lambda x: x[1], reverse=True)

        # Mostrar el top 10 recomendaciones
        print("\nTop 10 artículos recomendados:")
        for i, (articulo, pred) in enumerate(predicciones[:10]):
            print("  " + str(i + 1) + ". " + articulo +
                  " (puntuación predicha: " + str(pred) + ")")

        if len(predicciones) == 0:
            print("  No se pudieron generar recomendaciones para este usuario.")

# VALIDAR RECOMENDACIONES
def validar_recomendaciones(train, test, usuarios, similitudes):
    """
    Valida las recomendaciones comprobando si los artículos que el usuario
    realmente puntuó bien en el test están entre los recomendados
    Parámetros:
        train: datos de entrenamiento
        test: datos de test
        usuarios: lista de reviewerIDs
        similitudes: diccionario de similitudes
    """
    print("\n" + "=" * 60)
    print("VALIDACIÓN DE RECOMENDACIONES")
    print("=" * 60)

    aciertos_top10 = 0
    aciertos_top20 = 0
    total_evaluados = 0
    ejemplos_mostrados = 0

    for usuario in usuarios:
        # Solo evaluar usuarios con reviews en test puntuadas con 4 o 5
        articulos_buenos_test = {a: n for a, n in test[usuario].items() if n >= 4}
        if len(articulos_buenos_test) == 0:
            continue

        vecinos = obtener_vecinos(usuario, usuarios, similitudes, K_VECINOS)
        if len(vecinos) == 0:
            continue

        # Generar predicciones para artículos no consumidos en train
        predicciones = []
        for articulo in set(a for u in train.values() for a in u.keys()):
            if articulo not in train[usuario]:
                pred = predecir_puntuacion(usuario, articulo, train, vecinos)   # Solo predecir para artículos no consumidos en train
                if pred is not None:
                    predicciones.append((articulo, pred))
        # Ordenar por predicción descendente
        predicciones.sort(key=lambda x: x[1], reverse=True)
        top10 = set(a for a, _ in predicciones[:10])
        top20 = set(a for a, _ in predicciones[:20])

        for articulo in articulos_buenos_test:
            total_evaluados += 1
            if articulo in top10:
                aciertos_top10 += 1
            if articulo in top20:
                aciertos_top20 += 1

        # Mostrar algunos ejemplos concretos
        if ejemplos_mostrados < 3 and len(predicciones) > 0:
            print("\n--- Usuario: " + usuario + " ---")
            print("Artículos bien puntuados en test (nota >= 4):")
            for a, n in list(articulos_buenos_test.items())[:3]:
                esta_en_top = "SÍ" if a in top20 else "NO"
                print("  " + a + " (nota real: " + str(n) +
                      ") - En top 20 recomendados: " + esta_en_top)
            print("Top 5 recomendaciones del modelo:")
            for i, (a, p) in enumerate(predicciones[:5]):
                print("  " + str(i+1) + ". " + a + " (pred: " + str(p) + ")")
            ejemplos_mostrados += 1

    if total_evaluados > 0:
        print("\n" + "-" * 60)
        print("RESULTADOS DE VALIDACIÓN:")
        print("Artículos bien puntuados evaluados: " + str(total_evaluados))
        print("Encontrados en Top 10 recomendaciones: " + str(aciertos_top10) +
              " (" + str(round(100 * aciertos_top10 / total_evaluados, 1)) + "%)")
        print("Encontrados en Top 20 recomendaciones: " + str(aciertos_top20) +
              " (" + str(round(100 * aciertos_top20 / total_evaluados, 1)) + "%)")
    else:
        print("No se pudieron validar recomendaciones.")

# FUNCIÓN PPAL
def main():
    """
    Función principal que ejecuta todo el pipeline del modelo
    """
    print("=" * 60)
    print("MODELO DE MACHINE LEARNING")
    print("Filtrado colaborativo basado en usuarios")
    print("=" * 60)
    print("\nParámetros:")
    print("  Categoría: " + CATEGORIA)
    print("  K vecinos: " + str(K_VECINOS))
    print("  Train/Test: " + str(int(PROPORCION_TRAIN * 100)) + "% / " +
          str(int((1 - PROPORCION_TRAIN) * 100)) + "%")
    print("  Mín. artículos en común: " + str(MIN_ARTICULOS_COMUN))
    print("  Usuarios considerados: " + str(N_USUARIOS_MODELO))

    # Obtener usuarios activos de la categoría
    print("\n--- Paso 1: Obtención de datos ---")
    usuarios = obtener_usuarios_activos(CATEGORIA, N_USUARIOS_MODELO)

    if len(usuarios) < 10:
        print("No hay suficientes usuarios activos. Prueba otra categoría.")
        return

    # Obtener sus reviews
    reviews = obtener_reviews_categoria(usuarios, CATEGORIA)

    # Dividir en train/test
    print("\n--- Paso 2: División train/test ---")
    random.seed(42)  # Semilla fija para reproducibilidad
    train, test = dividir_train_test(reviews, PROPORCION_TRAIN)

    # Calcular similitudes usando solo datos de train
    print("\n--- Paso 3: Cálculo de similitudes ---")
    similitudes = calcular_todas_similitudes(train, usuarios)

    # Evaluar modelo
    print("\n--- Paso 4: Evaluación del modelo ---")
    resultado = evaluar_modelo(train, test, usuarios, similitudes)

    if resultado[0] is not None:
        rmse, mae, n_pred, n_fallidas = resultado
        print("\n" + "=" * 60)
        print("RESULTADOS DE LA EVALUACIÓN")
        print("=" * 60)
        print("Predicciones realizadas: " + str(n_pred))
        print("Predicciones no posibles: " + str(n_fallidas))
        print("RMSE (Root Mean Squared Error): " + str(round(rmse, 4)))
        print("MAE (Mean Absolute Error): " + str(round(mae, 4)))
        print("\nInterpretación:")
        if mae < 1.0:
            print("  El modelo tiene un error medio menor a 1 punto,")
            print("  lo que indica predicciones razonablemente buenas.")
        else:
            print("  El error medio es de " + str(round(mae, 2)) + " puntos.")
            print("  Hay margen de mejora (más datos, ajustar K, etc.).")

    # mostramos recomendaciones
    print("\n--- Paso 5: Demostración de recomendaciones ---")
    demostrar_recomendaciones(train, usuarios, similitudes)

    # validamos recomendaciones
    print("\n--- Paso 6: Validación de recomendaciones ---")
    validar_recomendaciones(train, test, usuarios, similitudes)

    print("\n" + "=" * 60)
    print("MODELO COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    main()