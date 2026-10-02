# Amazon reviews on MySQL, MongoDB and Neo4j

*Lee esto en español: [README.es.md](README.es.md).*

Final project of the Databases course, 2nd year of the IMAT degree (ICAI – Universidad Pontificia Comillas), 2025-26.
Authors: **Pilar Pérez Hernández** and **María Roca Ramón**.

A Python application that loads about 475,000 Amazon product reviews into three database systems, each used for what it does best, and then queries and visualises them: a terminal menu of charts, a graph analysis of user similarity in Neo4j, a user-based collaborative-filtering recommender evaluated with RMSE/MAE, and an interactive Streamlit dashboard.

- **MySQL** holds the structured part: reviewers, products (with their category) and the numeric review data (rating, helpful votes, dates).
- **MongoDB** holds the text: the full review body and its summary, plus the reference keys.
- **Neo4j** holds graphs built on demand from MySQL: user–user similarity (Pearson correlation), user–product ratings, user–category links and "items in common" between users.

The full report (`docs/Memoria.pdf`) and the poster (`docs/Poster.pdf`) are in Spanish.

## What is in the repository

| File | Contents |
|---|---|
| `configuracion.py` | Connection settings (hosts, ports, database names) and paths of the data files. Credentials come from environment variables. |
| `load_data.py` | Creates the MySQL database and tables and the MongoDB database from scratch, then streams the four JSON files line by line into both. |
| `inserta_dataset.py` | Adds a fifth dataset (Office Products) to the already-loaded databases, reusing reviewers and products that already exist. |
| `menu_visualizacion.py` | Terminal menu with eight analyses and charts (matplotlib / seaborn / WordCloud), including the "popular items not yet consumed" recommender. |
| `neo4J_proyecto.py` | Terminal menu that builds four different graphs in Neo4j from MySQL data (Pearson similarities, random items and their raters, multi-category users, popular items and items in common). |
| `modelo_ml.py` | User-based collaborative filtering: train/test split, Pearson similarities, k-nearest-neighbour rating prediction, RMSE/MAE evaluation and example recommendations. |
| `dashboard_streamlit.py` | Web dashboard (Streamlit + Plotly) that replaces the terminal menu. |
| `exportar_datos_tableau.py` | Exports a joined extract of MySQL to Excel for the Tableau Public charts. |
| `requirements.txt` | Python dependencies. |
| `docs/` | Report and poster (Spanish). |

## Data

The datasets are the public *Amazon product data* 5-core review files by Julian McAuley (UCSD). They are not in the repository because of their size; put them in a `data/` folder next to the scripts (the folder is git-ignored):

| Category | File | Reviews |
|---|---|---|
| Toys and Games | `Toys_and_Games_5.json` | 167,597 |
| Video Games | `Video_Games_5.json` | 231,780 |
| Digital Music | `Digital_Music_5.json` | 64,706 |
| Musical Instruments | `Musical_Instruments_5.json` | 10,261 |
| Office Products (added later with `inserta_dataset.py`) | `Office_Products_5.json` | — |

Each line is one JSON review with `reviewerID`, `asin`, `reviewerName`, `helpful` (a `[helpful, total]` pair), `reviewText`, `overall`, `summary`, `unixReviewTime` and `reviewTime`.

## Design: how the data is split

**MySQL** (`reviews_amazon`), normalised schema with foreign keys:

- `reviewers(reviewerID PK, reviewerName)`
- `products(asin PK, category)` — `category` does not exist in the JSON; it records which file the product came from.
- `reviews(id PK AUTO_INCREMENT, reviewerID FK, asin FK, overall, helpful_votes, total_votes, reviewDate DATE, unixReviewTime)` — `helpful` is split into two integers and `reviewTime` (`"MM DD, YYYY"`) is parsed to a `DATE`.

**MongoDB** (`reviews_amazon.reviews`), one document per review: `{reviewerID, asin, reviewText, summary, overall}`. The keys are duplicated so a text query can be linked back to MySQL without a cross-database join; for instance the word cloud takes the `asin`s of a category from MySQL and then fetches the matching `summary` fields from MongoDB with `$in`.

**Loading.** The course forbade reading whole files into memory, pandas and `LOAD DATA`, so `load_data.py` iterates each file with `for linea in fichero` and `json.loads` per line. Reviewers and products are inserted only the first time they appear (an in-memory set, with `IntegrityError` as a second barrier, because the same user can review several categories), and MySQL commits every 10,000 reviews. `inserta_dataset.py` does the same against a database that already has data: it first loads the existing reviewer and product ids, then inserts only what is new, and prints how many reviewers and products were added.

## The terminal menu (`menu_visualizacion.py`)

1. Reviews per year (bar chart; one category or all).
2. Item popularity curve: items sorted by number of reviews (long-tail curve).
3. Rating histogram, by category, for all categories, or for a single item by ASIN (the ASIN is validated first).
4. Cumulative number of reviews over time, one line per category (uses `unixReviewTime`).
5. Histogram of reviews per user (how many users wrote exactly *n* reviews).
6. Word cloud of review summaries for one category (words longer than 3 characters). This is the option that combines MySQL and MongoDB.
7. Average rating per category (extra chart).
8. Recommendation: given a `reviewerID` and a category, the 10 most-reviewed items of that category the user has not rated (`NOT IN` subquery, `GROUP BY asin`, `LIMIT 10`).

Every option is wrapped in `try/except` so a failing query does not kill the menu.

## The Neo4j application (`neo4J_proyecto.py`)

Each option wipes the graph (`MATCH (n) DETACH DELETE n`) and rebuilds it from MySQL:

1. **User similarity.** Takes the `N_USUARIOS = 30` users with most reviews, fetches their `{asin: overall}` ratings, computes the Pearson correlation for every pair over the items both have rated (`None` if there are none or a denominator is zero), saves the pairs to `similitudes.csv`, creates `USER` nodes and a `SIMILITUD {pearson}` relationship in both directions, and prints the user with most neighbours (Cypher `COUNT` + `ORDER BY`).
2. **Random items of a category** and every user who rated them: `ARTICULO` and `USER` nodes (`MERGE` for users) joined by `HA_PUNTUADO {nota, tiempo}`.
3. **Users who rated more than one category**, out of the first 400 reviewers by name: `USER` → `HA_CONSUMIDO {num_articulos}` → `TIPO_ARTICULO`.
4. **Popular items with fewer than 40 reviews** (top 5), their raters, and an `ARTICULOS_EN_COMUN {cantidad}` relationship between every pair of users who share at least one of those items (the intersection is computed in Python on sets rather than with one SQL query per pair).

## The recommender (`modelo_ml.py`)

User-based collaborative filtering on one category (`Video_Games` by default), implemented with the standard library only:

1. Take the 200 most active users of the category with at least 5 reviews (19,549 reviews in the report's run).
2. Split each user's reviews 80/20 into train and test with a fixed seed (`random.seed(42)`): 15,556 train / 3,993 test.
3. Compute Pearson similarity between every pair of users using training data only, keeping pairs with at least 2 items in common (3,446 pairs).
4. For each test rating, predict with the k = 20 most similar users with positive correlation:
   `pred(u, i) = mean(u) + Σ sim(u,v)·(r(v,i) − mean(v)) / Σ |sim(u,v)|`, clipped to [1, 5].
5. Report RMSE and MAE, show top-10 recommendations for three users, and check whether the items each user rated ≥ 4 in the test set appear in their top-10/top-20.

Results reported in `docs/Memoria.pdf`: **1,745 predictions made, 2,248 not possible** (no neighbour had rated the item), **RMSE = 1.1619, MAE = 0.8395**. The report discusses the usual limitations seen here: sparsity (over 30,000 distinct items in the category), cold start, and the bias towards 5-star predictions that mirrors the dataset.

## The dashboard (`dashboard_streamlit.py`)

A sidebar with nine pages: a home page with overall metrics (reviews, products, users, categories) and reviews per category, then one page per option of the terminal menu, rebuilt with Plotly (zoom, hover, toggling series, PNG download), dropdowns instead of typed options, readable dates instead of Unix timestamps, expandable data tables, word-cloud controls (max words, background colour) and a horizontal bar chart of the recommended items. The MongoDB client is cached with `@st.cache_resource`; the category list with `@st.cache_data`.

Three of the charts (reviews per year, rating histogram, average rating per category) were also reproduced in Tableau Public from the Excel produced by `exportar_datos_tableau.py` (`data/datos_tableau.xlsx`, one row per review joined with its category).

## How to run

Requires Python 3, and MySQL, MongoDB and Neo4j running locally on their default ports (`3306`, `27017`, `bolt://localhost:7687`).

```bash
pip install -r requirements.txt

# credentials are read from the environment (never stored in the code)
export MYSQL_USER=root MYSQL_PASSWORD=your_password NEO4J_PASSWORD=your_password
# on Windows (cmd): set MYSQL_USER=root  etc.

python load_data.py              # creates both databases and loads the 4 datasets (takes a while)
python inserta_dataset.py        # optional: adds Office Products
python menu_visualizacion.py     # terminal menu
python neo4J_proyecto.py         # Neo4j menu (open http://localhost:7474 to see the graphs)
python modelo_ml.py              # train and evaluate the recommender
python exportar_datos_tableau.py # Excel extract for Tableau
streamlit run dashboard_streamlit.py   # dashboard at http://localhost:8501
```

`MYSQL_USER` defaults to `root`; `MYSQL_PASSWORD` and `NEO4J_PASSWORD` default to empty. The MongoDB connection assumes no authentication. Hosts, ports and database names can be changed in `configuracion.py`.

## Work split

Pilar: relational design and MySQL/MongoDB split, `load_data.py`, the visualisation menu, the Tableau export and charts, the recommender (`modelo_ml.py`), the Streamlit dashboard and the report. María: `configuracion.py`, `inserta_dataset.py`, the Neo4j application, testing and data validation, report review and the poster.
