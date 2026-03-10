# RFC-002 : Architecture des métadonnées et de la configuration

**Statut** : Implémenté (chargement config.yaml + manifest, compat legacy)  
**Branche** : feature/backend  
**Date** : 2025-01

---

## 1. Résumé

Cette RFC propose une architecture **plus simple et plus standard** pour la gestion des métadonnées et des chemins dans openfisca-survey-manager, en s’appuyant sur les conventions XDG, un seul format de configuration par répertoire, et une structure de répertoires prévisible. Elle prévoit une **migration progressive** de l’existant.

---

## 2. État actuel (à migrer)

### 2.1 Où est la config ?

Le répertoire de configuration (« config_files_directory ») est résolu dans `configuration/paths.py` par une **cascade de hacks** :

| Priorité | Condition | Répertoire |
|----------|-----------|------------|
| 1 | Package `taxipp` importé et répertoire existe | `taxipp_install/.config/openfisca-survey-manager` |
| 2 | Package `openfisca_france_data` importé et répertoire existe | `BaseDirectory.save_config_path("openfisca-survey-manager")` → **~/.config/openfisca-survey-manager** |
| 3 | CI ou pytest | `openfisca_survey_manager/tests/data_files` |
| 4 | Fallback | `~/.config/openfisca-survey-manager` (XDG) |

Problèmes : ordre dépendant des imports, écriture possible de `config.ini` dans les tests à l’import, assertion si le répertoire n’existe pas.

### 2.2 Fichiers dans le répertoire de config

Aujourd’hui, **deux INI** + des **JSON** externes :

- **config.ini** (obligatoire dans le répertoire)
  - `[collections]` : `collections_directory` + paires `nom_collection` = chemin vers un fichier JSON.
  - `[data]` : `output_directory`, `tmp_directory` (et en tests `input_directory`).
- **raw_data.ini** (utilisé uniquement par le script `build-collection`)
  - Une section par collection : `[nom_collection]`.
  - Clés = noms d’enquêtes, valeurs = chemins vers répertoire/fichier de données brutes.
- **Fichiers JSON** (un par collection, chemin dans config.ini ou sous `collections_directory`)
  - Contenu : `name`, `label`, `surveys` : { `survey_name` → métadonnées du survey (tables, hdf5_file_path, parquet_file_path, **informations** dont `csv_files`, `sas_files`, etc.) }.

Les métadonnées sont donc réparties entre : config.ini (où trouver les JSON), raw_data.ini (où sont les données brutes, seulement pour build), et les JSON (décriture des surveys, chemins de stockage, listes de fichiers sources). Redondance et deux formats INI différents.

### 2.3 Utilisation dans le code

- **SurveyCollection** : lit `Config(config_files_directory)` → `config.ini` ; get/set `collections` (nom → json_path) ; `config.get("data", "output_directory")` pour `fill_store`.
- **Survey** : `informations` (dict) contient p.ex. `csv_files`, `sas_files` ; utilisé dans `fill_store` pour savoir quels fichiers lire.
- **build_collection** : lit `raw_data.ini` pour savoir quels répertoires associer à quelles enquêtes, puis crée/met à jour la collection JSON et les données.

---

## 3. Proposition : architecture cible

### 3.1 Principes

1. **Un seul répertoire de configuration** : XDG uniquement par défaut, ou chemin explicite (variable d’environnement ou argument). Plus de résolution selon `taxipp` / `openfisca_france_data`.
2. **Un seul fichier de config par répertoire** : tout ce qui est « config globale » (chemins de base, options) dans un seul fichier (voir 3.2).
3. **Métadonnées des datasets au plus près des données** : un « dataset » (ex-collection) = un répertoire dédié avec un manifeste (metadata) à l’intérieur, plutôt qu’un JSON éclaté référencé par un INI.
4. **Standard et lisible** : YAML ou INI clair pour la config ; YAML ou JSON pour les manifests (alignement possible avec RFC-001 Data Stack).

### 3.2 Répertoire de configuration (XDG)

**Emplacement par défaut** : `$XDG_CONFIG_HOME/openfisca-survey-manager/` (sinon `~/.config/openfisca-survey-manager/`).

Contenu proposé :

```
~/.config/openfisca-survey-manager/
├── config.yaml          # unique fichier de config (remplace config.ini + raw_data.ini pour la partie “où sont les choses”)
```

**config.yaml** (exemple) :

```yaml
# Répertoire où sont stockées les collections/datasets (manifests + données dérivées)
collections_dir: ~/.local/share/openfisca-survey-manager/collections

# Répertoire de sortie par défaut pour build / fill_store (optionnel, peut être overridé par dataset)
default_output_dir: ~/.local/share/openfisca-survey-manager/output

# Répertoire temporaire (optionnel)
tmp_dir: /tmp/openfisca-survey-manager
```

Alternative si on garde l’INI : un seul **config.ini** avec des sections claires, p.ex. :

```ini
[paths]
collections_dir = ~/.local/share/openfisca-survey-manager/collections
default_output_dir = ~/.local/share/openfisca-survey-manager/output
tmp_dir = /tmp/openfisca-survey-manager
```

On supprime : `[collections]` avec une entrée par collection (les manifests seront dans chaque dataset, voir 3.3). On supprime **raw_data.ini** : les sources brutes seront décrites dans le manifest du dataset.

### 3.3 Structure d’un dataset (ex-collection)

Un dataset = un répertoire sous `collections_dir` (ou chemin absolu configuré), avec un **manifeste** à l’intérieur :

```
collections_dir/
└── erfs/
    ├── manifest.yaml    # métadonnées du dataset + liste des surveys
    ├── erfs_2019/       # (optionnel) données dérivées par survey
    │   ├── data.parquet
    │   └── ...
    └── erfs_2020/
        └── ...
```

**manifest.yaml** (exemple) :

```yaml
name: erfs
label: "Enquête Revenus Fiscaux et Sociaux"

# Backend de stockage des tables (hdf5, parquet, zarr) ; par défaut parquet
store_format: parquet

# Par survey : sources brutes (remplace raw_data.ini + informations)
surveys:
  erfs_2019:
    label: "ERFS 2019"
    source:
      format: sas  # ou csv, stata, parquet
      path: /data/erfs/2019   # répertoire ou fichier
    # optionnel : chemins de sortie relatifs au dataset
    output_subdir: erfs_2019

  erfs_2020:
    label: "ERFS 2020"
    source:
      format: parquet
      path: /data/erfs/2020
    output_subdir: erfs_2020
```

Cela remplace : la section `[erfs]` de raw_data.ini + la partie « informations » (csv_files, sas_files, …) dans le JSON de collection. Un seul endroit pour « où sont les données brutes » et « où écrire les sorties ».

Pour la rétrocompatibilité, on peut prévoir un **adaptateur** qui lit l’ancien JSON + raw_data.ini et produit (ou expose) un équivalent manifest.

### 3.4 Résolution du répertoire de config (simplifiée)

- **Valeur explicite** : toujours possible de passer `config_dir` (ou `config_files_directory`) en argument aux APIs et au CLI.
- **Par défaut** : `os.environ.get("OPENFISCA_SURVEY_CONFIG_DIR")` ou `xdg_config_home() / "openfisca-survey-manager"`.
- **Tests** : répertoire dédié (ex. `tests/data_files`) fourni explicitement par les tests ; plus d’effet de bord à l’import (plus d’écriture de config.ini au chargement de `paths`).

On **ne** résout plus le répertoire en fonction de la présence de `taxipp` ou `openfisca_france_data`. Les projets (france-data, taxipp) peuvent :
- soit définir `OPENFISCA_SURVEY_CONFIG_DIR` vers leur répertoire,
- soit passer le chemin de config à chaque appel.

### 3.5 Backends de stockage (store)

Le stockage des tables d’enquête peut s’effectuer via différents **backends** (choix au build / `fill_store`) :

| Backend  | Format              | Usage                                      |
|----------|---------------------|--------------------------------------------|
| **hdf5** | Un fichier .h5      | Historique (déprécié à terme)              |
| **parquet** | Répertoire, un .parquet par table | Recommandé (interop, colonnes) |
| **zarr** | Répertoire .zarr, un groupe par table | Optionnel (dépendance `[zarr]`)     |

- **API** : `io.backends.get_backend(name)`, `get_available_backend_names()`, `register_backend(name, backend)` pour étendre.
- **CLI** : `build-collection --parquet` ou `build-collection --zarr` ; par défaut HDF5 (avec avertissement).
- **Survey** : `store_format`, `hdf5_file_path` / `parquet_file_path` / `zarr_file_path` selon le backend.
- **Zarr (compression, parallélisation)** : voir [docs/ZARR-BACKEND.md](ZARR-BACKEND.md).

### 3.6 API cible (alignement RFC-001)

- Charger un dataset par nom : `DataManager.load("erfs", config_dir=...)` → lit `collections_dir/erfs/manifest.yaml` et les données associées.
- Accès aux métadonnées : `dataset.metadata` (provenant du manifest), `dataset.schema` (si on l’expose), chemins dérivés déterministes à partir de `collections_dir` + `name` + `output_subdir`.

On garde une compatibilité avec l’API actuelle « SurveyCollection.load(collection=...) » pendant la transition, en faisant que cette API s’appuie en interne sur la nouvelle config + manifests (éventuellement via un bridge depuis l’ancien JSON).

---

## 4. Migration de l’existant

### 4.1 Conserver l’existant en parallèle

- Garder la lecture de **config.ini** et **raw_data.ini** tant que la nouvelle config n’est pas présente.
- Si `config.yaml` (ou le nouveau config.ini [paths]) existe dans le répertoire de config : utiliser la nouvelle structure (manifests sous `collections_dir`).
- Sinon : comportement actuel (config.ini [collections] + [data], raw_data.ini, JSON externes).

### 4.2 Script de migration

Un script permet de migrer l’existant vers la nouvelle structure :

- **Emplacement** : `openfisca_survey_manager.scripts.migrate_config_to_rfc002`
- **Usage** :
  ```bash
  python -m openfisca_survey_manager.scripts.migrate_config_to_rfc002 [--config-dir PATH] [--dry-run] [-v]
  ```
- **Comportement** : lit `config.ini` ([collections] + [data]) et, si présent, `raw_data.ini` ; pour chaque collection, charge le JSON, déduit `source.format` et `source.path` à partir de `informations` (csv_files, sas_files, etc.) ou de la section correspondante de raw_data.ini ; **infère `store_format`** (parquet, hdf5 ou zarr) à partir des champs `parquet_file_path` / `zarr_file_path` / `hdf5_file_path` des surveys du JSON legacy, et l’écrit dans le manifest ; crée `config.yaml` et `collections_dir/<name>/manifest.yaml` pour chaque collection. Avec `--dry-run`, n’écrit aucun fichier.
- **Répertoire de config par défaut** : celui retourné par `get_config_dir()` (env `OPENFISCA_SURVEY_CONFIG_DIR` ou XDG). On peut imposer un répertoire avec `--config-dir`.

### 4.3 Dépréciation

- À terme : annoncer comme dépréciés `config.ini` [collections] (mapping nom → JSON), `raw_data.ini`, et les JSON de collection « à l’ancienne ». Documenter la migration dans MIGRATION_IMPORTS.md ou un nouveau MIGRATION_CONFIG.md.

---

## 5. Résumé des changements proposés

| Actuel | Cible |
|--------|--------|
| Résolution config par taxipp / france_data / CI / XDG | XDG ou env `OPENFISCA_SURVEY_CONFIG_DIR` ou argument explicite |
| config.ini + raw_data.ini | Un seul fichier (config.yaml ou config.ini [paths]) |
| JSON de collection hors répertoire, référencé par config | Manifest (YAML/JSON) par dataset dans `collections_dir/<name>/manifest.yaml` |
| Sources brutes dans raw_data.ini + informations (JSON) | Sources dans le manifest du dataset (`surveys.*.source`) |
| Écriture config.ini au chargement des paths (tests) | Plus d’écriture à l’import ; tests passent un config_dir explicite |

Cela donne une architecture **plus simple** (un format, un lieu par dataset), **plus standard** (XDG, chemins explicites), et **migrable** en gardant l’ancien comportement tant que la nouvelle config n’est pas en place.
