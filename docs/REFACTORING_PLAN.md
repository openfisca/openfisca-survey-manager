# Plan de réorganisation du code – OpenFisca Survey Manager

Ce document décrit la réorganisation interne du code en trois axes : **structure**, **responsabilités**, et **nettoyage technique**. Objectif : meilleure séparation des couches, **sans changement fonctionnel**.

---

## 1. Réorganisation interne (arborescence cible)

Arborescence proposée pour séparer config, I/O, traitement et orchestration :

```
openfisca_survey_manager/
├── __init__.py
├── exceptions.py          # SurveyManagerError, SurveyConfigError, SurveyIOError
│
├── config/                # (après migration de config.py ; éviter config/ tant que config.py existe)
│   ├── loader.py          # chargement config (depuis config.py)
│   └── models.py          # modèles / types de config
│
├── io/
│   ├── readers.py         # lecture SAS / CSV / Stata / Parquet
│   ├── writers.py         # écriture HDF / Parquet
│   └── hdf.py             # logique HDF si à isoler
│
├── processing/
│   ├── cleaning.py        # nettoyage (ex. clean_data_frame)
│   ├── harmonization.py   # harmonisation / renommage
│   └── weights.py         # calibration, calmar
│
├── core/
│   ├── survey.py          # Survey, Table
│   └── dataset.py         # SurveyCollection, orchestration dataset
│
├── utils/                 # (après migration de utils.py ; éviter utils/ tant que utils.py existe)
│   └── misc.py            # helpers partagés (éviter imports circulaires)
│
├── scenarios/             # inchangé pour l’instant
├── policy/                # simulations, simulation_builder, aggregates (à terme autre paquet)
├── scripts/
├── tests/
└── ...
```

**État actuel** : les dossiers suivants existent avec des `__init__.py` de préparation (pas de code déplacé encore) :
- `configuration/` → deviendra `config/` une fois `config.py` migré (évite de masquer `config.py`)
- `io/`, `processing/`, `core/` → noms définitifs
- `common/` → deviendra `utils/` une fois `utils.py` migré (évite de masquer `utils.py`)

Le déplacement effectif des modules se fera par étapes pour garder la compatibilité des imports.

**Réalisé** :
- `io/readers.py` : `read_sas`, `read_spss`, `read_dbf` (anciens modules en ré-export).
- `common/misc.py` : helpers sans dépendance survey (`do_nothing`, `inflate_parameters`, `asof`, `parameters_asof`, `variables_asof`) ; `utils.py` importe depuis `common.misc` et garde `load_table`.
- **Nettoyage** : `print()` remplacés par `logging` (matching, calmar, scenarios, scripts/build_collection, simulations). Exceptions génériques remplacées par `SurveyManagerError` / `SurveyConfigError` / `SurveyIOError` (survey_collections, tables, simulations, simulation_builder, surveys, scenarios, calmar).
- **processing/weights** : `calmar` et `Calibration` déplacés dans `processing/weights/calmar.py` et `processing/weights/calibration.py` ; `calibration.py` et `calmar.py` à la racine sont des ré-exports pour compatibilité.
- **processing/cleaning** : `clean_data_frame` déplacé dans `processing/cleaning.py` ; `tables.py` importe depuis `processing.cleaning` (compatibilité conservée).
- **policy/** : répertoire créé pour `simulations`, `simulation_builder`, `aggregates` (à terme déplacés dans un paquet dédié). Les modules à la racine (`simulations.py`, `simulation_builder.py`, `aggregates.py`) sont des placeholders avec `DeprecationWarning` qui ré-exportent depuis `policy`.
- **policy/tests/** : tests concernant le paquet policy (test_aggregates, test_compute_aggregate, test_compute_pivot_table, test_compute_winners_losers, test_create_data_frame_by_entity, test_marginal_tax_rate, test_summarize_variables). Ils importent depuis `openfisca_survey_manager.policy` et utilisent `create_randomly_initialized_survey_scenario` depuis `openfisca_survey_manager.tests.test_scenario`.

---

## 2. Clarifier les responsabilités

### A) Lecture des données → `io/`

- **Tout ce qui lit** SAS, CSV, Stata, Parquet doit terminer dans `io/` (ex. `read_sas`, `read_spss`, `read_dbf`, `tables.read_source` / readers par format).
- Responsabilité unique : lire depuis le disque et retourner des structures (DataFrame, etc.) sans logique métier survey.

### B) Transformation → `processing/`

- Nettoyage (ex. `clean_data_frame`), renommage, harmonisation, gestion des catégories.
- Ponds et calibration : `calmar`, `calibration` → `processing/weights.py` (ou sous-modules dédiés).
- Entrée : données brutes ou intermédiaires. Sortie : données prêtes pour la simulation / l’agrégation.

### C) Orchestration → `core/`

- Classe centrale **Survey** et **SurveyCollection** : pilotage des étapes (config → lecture → traitement → écriture).
- `core/survey.py` : Survey, Table.
- `core/dataset.py` : SurveyCollection, gestion des collections et des chemins.

Aujourd’hui ces couches sont entremêlées (ex. lecture + nettoyage dans `tables`, config dans plusieurs endroits). L’objectif est de les séparer progressivement sans casser l’API publique.

---

## 3. Nettoyage technique

### 3.1 Fonctions longues (> 100 lignes)

- Découper les grosses fonctions en étapes nommées, par exemple :
  - `load_survey()` → `_parse_config()`, `_load_raw_data()`, `_transform()`, `_store()`.
- Cible : lisibilité et testabilité, sans changer le comportement.

### 3.2 Dépendances circulaires

- Si des modules s’importent mutuellement, extraire la logique commune dans `utils/` (ou `config/`) et faire dépendre les deux côtés de ce module commun.
- Vérifier avec des imports à froid (démarrer l’app et importer les sous-modules).

### 3.3 Typage Python

- **Entamé** : type hints sur les signatures publiques de `core/`, `io/` et `processing/` (cleaning, harmonization, weights/calmar, weights/calibration).
- À poursuivre : reste du package (scenarios, simulations, etc.).

### 3.4 Logging

- **Fait** : `print()` remplacés par du `logging` structuré (matching, calmar, scenarios, scripts/build_collection, simulations, readers, writers, calibration, core, processing, etc.).
- **Fait** : logging étendu à tous les modules métier (configuration/models, google_colab, statshelpers, et l’ensemble des modules concernés).

### 3.5 Gestion d’erreurs centralisée

- **Fait** : `openfisca_survey_manager.exceptions` avec `SurveyManagerError`, `SurveyConfigError`, `SurveyIOError`.
- À faire : remplacer progressivement les `ValueError` / `TypeError` spécifiques au survey par ces classes (ou sous-classes) pour permettre à l’appelant de catcher les erreurs Survey Manager de façon ciblée.

---

## 4. Mapping modules actuels → cible (résumé)

| Actuel | Cible |
|--------|--------|
| `config.py`, `paths.py` | `config/` (loader, models) |
| `read_sas.py`, `read_spss.py`, `read_dbf.py`, lecture dans `tables.py` | `io/readers.py` (ou sous-modules) |
| Écriture HDF/Parquet (tables, surveys) | `io/writers.py`, `io/hdf.py` |
| `tables.clean_data_frame`, harmonisation | `processing/cleaning.py`, `processing/harmonization.py` |
| `calibration.py`, `calmar.py` | `processing/weights.py` |
| `surveys.py`, `survey_collections.py`, `tables.py` (orchestration) | `core/survey.py`, `core/dataset.py` |
| `utils.py`, helpers partagés | `utils/misc.py` (dossier `common/` en transition) |
| `exceptions.py` | déjà à la racine du package |

---

## 5. Ordre d’exécution recommandé

1. **Sans casser les imports** : déplacer un module à la fois, en réexportant depuis l’ancien emplacement (ex. `from openfisca_survey_manager.io.readers import read_sas` puis dans `read_sas.py` : `from openfisca_survey_manager.io.readers import read_sas` et `read_sas = read_sas` pour compatibilité).
2. Introduire `SurveyManagerError` (et sous-classes) à chaque nouveau remplacement d’exception.
3. Découper les fonctions > 100 lignes au fil des déplacements.
4. Vérifier les tests et la non-régression après chaque vague de déplacement.
