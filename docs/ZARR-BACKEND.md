# Utiliser Zarr avec OpenFisca Survey Manager

Ce document explique **si et comment** utiliser le backend Zarr pour stocker les enquêtes, et ce qu’il en est de la **compression** et de la **parallélisation** en lecture/écriture.

---

## 1. Utiliser Zarr avec OpenFisca

### Oui, c’est possible

Le backend **zarr** est disponible dans `openfisca-survey-manager` à condition d’installer la dépendance optionnelle :

```bash
pip install openfisca-survey-manager[zarr]
# ou
pip install openfisca-survey-manager zarr numcodecs
```

(pandas 2.x utilise `to_zarr` / `read_zarr` ; le package **zarr** est requis.)

### En ligne de commande (build-collection)

Pour construire une collection en stockant les tables au format Zarr :

```bash
build-collection -c ma_collection --zarr
```

Sans `--zarr`, le format par défaut reste HDF5 (avec avertissement) ou vous pouvez utiliser `--parquet`.

### En Python (fill_store)

```python
from openfisca_survey_manager.core.dataset import SurveyCollection

col = SurveyCollection.load(collection="ma_collection", config_files_directory="...")
col.fill_store(
    source_format="sas",   # ou csv, parquet, etc.
    store_format="zarr",
)
```

Après cela, chaque survey a un répertoire `{output}/{survey.name}.zarr`, et chaque table est un **groupe zarr** (sous-répertoire) dans ce store. La lecture se fait comme d’habitude avec `survey.get_values(table=..., variables=...)` ; le code utilise automatiquement le backend zarr si `store_format == "zarr"`.

### Vérifier que Zarr est disponible

```python
from openfisca_survey_manager.io.backends import get_available_backend_names, get_backend

print(get_available_backend_names())  # doit contenir "zarr" si le package est installé
backend = get_backend("zarr")         # lève ValueError si zarr absent
```

---

## 2. Compression

### Comportement actuel

Dans l’implémentation actuelle, l’écriture Zarr passe par `pandas.DataFrame.to_zarr(path, mode="w")` **sans options de compression explicites**. Zarr/pandas peuvent donc utiliser un comportement par défaut (par ex. compression légère ou aucune selon les versions).

### Ce que Zarr permet en général

Zarr gère la compression **par blocs (chunks)** via **numcodecs**. On peut utiliser par exemple :

- **Blosc** (LZ4, Zstd, Zlib) : bon compromis vitesse / ratio, très utilisé
- **Zstd** : bon ratio, décompression rapide
- **LZ4** : très rapide, ratio moindre
- **Gzip** : standard, plus lent

Ces options se configurent au moment de la **création** du tableau zarr (compressor, chunks). Avec **pandas** :

- `df.to_zarr(path, ...)` peut accepter des arguments supplémentaires passés au store zarr sous-jacent (selon la version de pandas).
- Pour un contrôle fin (compression, chunking), on peut créer soi‑même un store zarr avec le bon `compressor` puis y écrire les colonnes, ou étendre le backend (voir ci‑dessous).

### Évolution possible dans le survey-manager

On peut faire évoluer le backend Zarr pour accepter des options (compression, chunks) soit :

- via des **kwargs** dans `fill_store(..., store_format="zarr", **zarr_options)` transmis à `to_zarr`,  
- soit via la **config** (manifest ou config.yaml) pour définir un compressor par défaut pour le format zarr.

Aujourd’hui, si vous avez besoin d’une compression précise, vous pouvez :

1. **Enregistrer un backend personnalisé** (`register_backend`) qui appelle `to_zarr` avec le `compressor` (et éventuellement les chunks) de votre choix.
2. Ou **post‑traiter** les répertoires `.zarr` générés (ré‑écriture avec d’autres options zarr) en dehors du survey-manager.

---

## 3. Parallélisation lecture / écriture

### Zarr en général

- **Parallélisme par blocs** : Zarr est conçu pour que des **chunks différents** puissent être lus ou écrits en parallèle sans verrou global (chaque chunk est indépendant).
- **En Python** : le **GIL** limite le gain avec des threads pour la partie compression/décompression ; le parallélisme efficace passe souvent par **multi‑processus** ou des runtimes qui libèrent le GIL (Cython, C extensions utilisées par numcodecs/blosc).
- **Goulot d’étranglement** : en pratique, la **compression/décompression** peut saturer le CPU (~1 GB/s) alors que le disque ou le réseau peuvent aller plus vite ; des évolutions (batch encode/decode, GPU) sont en cours dans l’écosystème zarr.

### Dans le survey-manager aujourd’hui

- **Écriture** : `fill_store(store_format="zarr")` appelle `to_zarr` pour chaque table, de façon **séquentielle** (une table après l’autre, pas de parallélisation interne exposée).
- **Lecture** : `get_values()` utilise `read_zarr` pour une table donnée, également de façon **séquentielle** par appel.

Donc **par défaut** : pas de parallélisation multi‑tables ni multi‑chunks exposée dans l’API actuelle.

### Comment paralléliser quand même

1. **Plusieurs tables / plusieurs surveys**  
   Vous pouvez paralléliser vous‑même au niveau applicatif : lancer plusieurs processus ou threads qui appellent `fill_store` (ou `get_values`) sur des collections/surveys/tables différents ; chaque processus écrira/lira ses propres fichiers ou groupes zarr sans conflit.

2. **Dask**  
   Pour des tableaux zarr, **Dask** (dask.array, ou chargement des zarr en Dask) gère le chargement parallèle par chunks. Cela ne passe pas directement par l’API Survey/SurveyCollection actuelle : il faudrait soit exporter les chemins `.zarr` puis les ouvrir avec Dask, soit ajouter une couche d’intégration (p.ex. une fonction qui retourne un Dask DataFrame à partir d’un survey zarr).

3. **Évolution du backend**  
   On pourrait ajouter plus tard un mode « écriture parallèle par table » (threads/processes) ou une option de lecture qui retourne un objet Dask pour exploiter le parallélisme par chunks côté zarr.

---

## 4. Résumé pratique

| Question | Réponse |
|----------|--------|
| **Utiliser Zarr avec OpenFisca ?** | Oui : `pip install openfisca-survey-manager[zarr]`, puis `build-collection --zarr` ou `fill_store(store_format="zarr")`. |
| **Compression ?** | Par défaut : comportement zarr/pandas (souvent léger). Pour plus de contrôle : backend personnalisé avec `to_zarr(..., compressor=...)` ou post‑traitement des stores zarr. |
| **Parallélisation lecture/écriture ?** | Pas exposée dans l’API actuelle (une table à la fois). Parallélisme possible : vous-même sur plusieurs tables/surveys, ou en utilisant Dask sur les chemins zarr générés. |

Si vous voulez, on peut détailler une proposition d’API pour passer des options de compression (et éventuellement de chunking) au backend Zarr dans `fill_store` ou dans la config.
