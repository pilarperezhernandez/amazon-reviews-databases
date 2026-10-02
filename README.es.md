# Reviews de Amazon en MySQL, MongoDB y Neo4j

*English version: [README.md](README.md).*

Proyecto final de la asignatura Bases de Datos, 2º del grado IMAT (ICAI – Universidad Pontificia Comillas), curso 2025-26.
Autoras: **Pilar Pérez Hernández** y **María Roca Ramón**.

Aplicación en Python que carga unas 475.000 reseñas de productos de Amazon en tres sistemas de bases de datos, cada uno para lo que mejor hace, y después las consulta y visualiza: un menú de gráficas por terminal, un análisis de similitud entre usuarios en grafo con Neo4j, un recomendador por filtrado colaborativo evaluado con RMSE/MAE y un dashboard interactivo con Streamlit.

- **MySQL** guarda la parte estructurada: revisores, productos (con su categoría) y los datos numéricos de cada review (nota, votos de utilidad, fechas).
- **MongoDB** guarda el texto: el cuerpo completo de la review y su resumen, más las claves de referencia.
- **Neo4j** guarda grafos que se construyen bajo demanda a partir de MySQL: similitud usuario–usuario (correlación de Pearson), puntuaciones usuario–producto, enlaces usuario–categoría y "artículos en común" entre usuarios.

La memoria completa (`docs/Memoria.pdf`) y el póster (`docs/Poster.pdf`) están en español.

## Qué hay en el repositorio

| Fichero | Contenido |
|---|---|
| `configuracion.py` | Parámetros de conexión (hosts, puertos, nombres de las bases de datos) y rutas de los ficheros de datos. Las credenciales se leen de variables de entorno. |
| `load_data.py` | Crea de cero la base de datos y las tablas de MySQL y la base de datos de MongoDB, y carga los cuatro JSON línea a línea en ambas. |
| `inserta_dataset.py` | Añade un quinto dataset (Office Products) a las bases de datos ya cargadas, reutilizando los revisores y productos que ya existen. |
| `menu_visualizacion.py` | Menú por terminal con ocho análisis y gráficas (matplotlib / seaborn / WordCloud), incluida la recomendación de "artículos populares no consumidos". |
| `neo4J_proyecto.py` | Menú por terminal que construye cuatro grafos distintos en Neo4j a partir de MySQL (similitudes de Pearson, artículos aleatorios y sus usuarios, usuarios multicategoría, artículos populares y artículos en común). |
| `modelo_ml.py` | Filtrado colaborativo basado en usuarios: división train/test, similitudes de Pearson, predicción con k vecinos, evaluación RMSE/MAE y recomendaciones de ejemplo. |
| `dashboard_streamlit.py` | Dashboard web (Streamlit + Plotly) que sustituye al menú por terminal. |
| `exportar_datos_tableau.py` | Exporta a Excel un extracto de MySQL (reviews unidas con su categoría) para las gráficas de Tableau Public. |
| `requirements.txt` | Dependencias de Python. |
| `docs/` | Memoria y póster. |

## Datos

Los datasets son los ficheros públicos *Amazon product data* (5-core) de Julian McAuley (UCSD). No están en el repositorio por tamaño; van en una carpeta `data/` junto a los scripts (está en el `.gitignore`):

| Categoría | Fichero | Reviews |
|---|---|---|
| Toys and Games | `Toys_and_Games_5.json` | 167.597 |
| Video Games | `Video_Games_5.json` | 231.780 |
| Digital Music | `Digital_Music_5.json` | 64.706 |
| Musical Instruments | `Musical_Instruments_5.json` | 10.261 |
| Office Products (se añade después con `inserta_dataset.py`) | `Office_Products_5.json` | — |

Cada línea es una review en JSON con `reviewerID`, `asin`, `reviewerName`, `helpful` (un par `[útiles, totales]`), `reviewText`, `overall`, `summary`, `unixReviewTime` y `reviewTime`.

## Diseño: cómo se reparten los datos

**MySQL** (`reviews_amazon`), esquema normalizado con claves foráneas:

- `reviewers(reviewerID PK, reviewerName)`
- `products(asin PK, category)` — `category` no existe en el JSON; indica de qué fichero viene el producto.
- `reviews(id PK AUTO_INCREMENT, reviewerID FK, asin FK, overall, helpful_votes, total_votes, reviewDate DATE, unixReviewTime)` — `helpful` se desglosa en dos enteros y `reviewTime` (`"MM DD, YYYY"`) se parsea a `DATE`.

**MongoDB** (`reviews_amazon.reviews`), un documento por review: `{reviewerID, asin, reviewText, summary, overall}`. Las claves se duplican para poder enlazar una consulta de texto con MySQL sin hacer un join entre bases de datos; por ejemplo, la nube de palabras saca de MySQL los `asin` de una categoría y después pide a MongoDB los `summary` correspondientes con `$in`.

**Carga.** El enunciado prohibía leer los ficheros enteros en memoria, usar pandas o `LOAD DATA`, así que `load_data.py` recorre cada fichero con `for linea in fichero` y hace `json.loads` por línea. Los revisores y productos se insertan solo la primera vez que aparecen (un set en memoria, con `IntegrityError` como segunda barrera, porque un mismo usuario puede tener reviews en varias categorías), y en MySQL se hace commit cada 10.000 reviews. `inserta_dataset.py` hace lo mismo sobre una base de datos que ya tiene datos: primero carga los ids de revisores y productos existentes, inserta solo lo nuevo e imprime cuántos revisores y productos se han añadido.

## El menú por terminal (`menu_visualizacion.py`)

1. Reviews por año (barras; una categoría o todas).
2. Curva de popularidad: artículos ordenados por número de reviews (curva de cola larga).
3. Histograma de notas, por categoría, para todas o para un artículo concreto por ASIN (se comprueba antes que el ASIN existe).
4. Número acumulado de reviews a lo largo del tiempo, una línea por categoría (usa `unixReviewTime`).
5. Histograma de reviews por usuario (cuántos usuarios han escrito exactamente *n* reviews).
6. Nube de palabras de los resúmenes de una categoría (palabras de más de 3 caracteres). Es la opción que combina MySQL y MongoDB.
7. Nota media por categoría (gráfica extra).
8. Recomendación: dado un `reviewerID` y una categoría, los 10 artículos con más reviews de esa categoría que el usuario no ha puntuado (subconsulta `NOT IN`, `GROUP BY asin`, `LIMIT 10`).

Cada opción va dentro de un `try/except` para que un fallo en una consulta no cierre el menú.

## La aplicación con Neo4j (`neo4J_proyecto.py`)

Cada opción vacía el grafo (`MATCH (n) DETACH DELETE n`) y lo reconstruye a partir de MySQL:

1. **Similitud entre usuarios.** Toma los `N_USUARIOS = 30` usuarios con más reviews, saca sus puntuaciones `{asin: overall}`, calcula la correlación de Pearson de cada par sobre los artículos que ambos han puntuado (`None` si no hay ninguno o un denominador es cero), guarda los pares en `similitudes.csv`, crea nodos `USER` y una relación `SIMILITUD {pearson}` en los dos sentidos, y muestra el usuario con más vecinos (Cypher con `COUNT` + `ORDER BY`).
2. **Artículos aleatorios de una categoría** y todos los usuarios que los han puntuado: nodos `ARTICULO` y `USER` (`MERGE` para los usuarios) unidos por `HA_PUNTUADO {nota, tiempo}`.
3. **Usuarios que han puntuado más de una categoría**, entre los primeros 400 revisores por nombre: `USER` → `HA_CONSUMIDO {num_articulos}` → `TIPO_ARTICULO`.
4. **Artículos populares con menos de 40 reviews** (los 5 primeros), sus usuarios, y una relación `ARTICULOS_EN_COMUN {cantidad}` entre cada par de usuarios que comparten al menos uno de esos artículos (la intersección se calcula en Python con sets en vez de con una consulta SQL por par).

## El recomendador (`modelo_ml.py`)

Filtrado colaborativo basado en usuarios sobre una categoría (`Video_Games` por defecto), implementado solo con la librería estándar:

1. Se toman los 200 usuarios más activos de la categoría con al menos 5 reviews (19.549 reviews en la ejecución de la memoria).
2. Las reviews de cada usuario se dividen 80/20 en train y test con semilla fija (`random.seed(42)`): 15.556 de train / 3.993 de test.
3. Se calcula la similitud de Pearson entre todos los pares de usuarios usando solo train, guardando los pares con al menos 2 artículos en común (3.446 pares).
4. Para cada nota del test se predice con los k = 20 usuarios más similares con correlación positiva:
   `pred(u, i) = media(u) + Σ sim(u,v)·(r(v,i) − media(v)) / Σ |sim(u,v)|`, acotada a [1, 5].
5. Se calculan RMSE y MAE, se muestran las 10 recomendaciones de tres usuarios y se comprueba si los artículos que cada usuario puntuó con ≥ 4 en el test aparecen en su top-10/top-20.

Resultados recogidos en `docs/Memoria.pdf`: **1.745 predicciones realizadas, 2.248 no posibles** (ningún vecino había puntuado el artículo), **RMSE = 1,1619, MAE = 0,8395**. La memoria comenta las limitaciones habituales que se observan: dispersión (más de 30.000 artículos distintos en la categoría), cold start y el sesgo hacia predicciones de 5 estrellas que refleja el propio dataset.

## El dashboard (`dashboard_streamlit.py`)

Una barra lateral con nueve páginas: una de inicio con métricas globales (reviews, productos, usuarios, categorías) y reviews por categoría, y después una página por cada opción del menú por terminal, rehecha con Plotly (zoom, hover, activar/desactivar series, descarga PNG), desplegables en vez de opciones escritas, fechas legibles en lugar de timestamps Unix, tablas de datos desplegables, controles para la nube de palabras (máximo de palabras, color de fondo) y un gráfico de barras horizontal con los artículos recomendados. El cliente de MongoDB se cachea con `@st.cache_resource`; la lista de categorías con `@st.cache_data`.

Tres de las gráficas (reviews por año, histograma de notas y nota media por categoría) se reprodujeron también en Tableau Public a partir del Excel que genera `exportar_datos_tableau.py` (`data/datos_tableau.xlsx`, una fila por review unida con su categoría).

## Cómo ejecutarlo

Hace falta Python 3 y tener MySQL, MongoDB y Neo4j en local en sus puertos por defecto (`3306`, `27017`, `bolt://localhost:7687`).

```bash
pip install -r requirements.txt

# las credenciales se leen del entorno (nunca van en el código)
export MYSQL_USER=root MYSQL_PASSWORD=tu_clave NEO4J_PASSWORD=tu_clave
# en Windows (cmd): set MYSQL_USER=root  etc.

python load_data.py              # crea las dos bases de datos y carga los 4 datasets (tarda un rato)
python inserta_dataset.py        # opcional: añade Office Products
python menu_visualizacion.py     # menú por terminal
python neo4J_proyecto.py         # menú de Neo4j (abre http://localhost:7474 para ver los grafos)
python modelo_ml.py              # entrena y evalúa el recomendador
python exportar_datos_tableau.py # extracto en Excel para Tableau
streamlit run dashboard_streamlit.py   # dashboard en http://localhost:8501
```

`MYSQL_USER` vale `root` por defecto; `MYSQL_PASSWORD` y `NEO4J_PASSWORD` están vacías por defecto. La conexión a MongoDB asume que no hay autenticación. Hosts, puertos y nombres de las bases de datos se cambian en `configuracion.py`.

## Reparto del trabajo

Pilar: diseño relacional y reparto MySQL/MongoDB, `load_data.py`, el menú de visualización, la exportación y las gráficas de Tableau, el recomendador (`modelo_ml.py`), el dashboard de Streamlit y la memoria. María: `configuracion.py`, `inserta_dataset.py`, la aplicación de Neo4j, pruebas y validación de datos, revisión de la memoria y el póster.
