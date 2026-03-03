# Migration des imports après retrait des ré-exports

Ce document décrit les changements à effectuer **lorsqu’on retirera les ré-exports** (fichiers de compatibilité) à la racine du package : mise à jour de tous les imports vers les nouveaux chemins, puis suppression des anciens modules.

**Référence** : `docs/REFACTORING_PLAN.md`.

---

## Mise en garde

Le retrait des ré-exports est une **breaking change** : tout code (interne ou externe) qui importe depuis les anciens chemins (`config`, `paths`, `tables`, `surveys`, `survey_collections`, `read_sas`, `read_spss`, `read_dbf`, `calibration`, `calmar`, `utils`) verra ses imports **échouer** (`ModuleNotFoundError`). Il faut migrer tous les imports **avant** de supprimer les fichiers listés en section 3, et documenter le changement dans le CHANGELOG pour les projets dépendants (ex. openfisca-france-data).

---

## 1. Correspondance ancien → nouveau

| Ancien import (à supprimer) | Nouvel import (à utiliser) |
|-----------------------------|----------------------------|
| `from openfisca_survey_manager.config import Config` | `from openfisca_survey_manager.configuration.models import Config` |
| `from openfisca_survey_manager.paths import ...` | `from openfisca_survey_manager.configuration.paths import ...` |
| `from openfisca_survey_manager.tables import Table` | `from openfisca_survey_manager.core.table import Table` |
| `from openfisca_survey_manager.surveys import Survey` | `from openfisca_survey_manager.core.survey import Survey` |
| `from openfisca_survey_manager.surveys import NoMoreDataError` | `from openfisca_survey_manager.core.survey import NoMoreDataError` |
| `from openfisca_survey_manager.survey_collections import SurveyCollection` | `from openfisca_survey_manager.core.dataset import SurveyCollection` |
| `from openfisca_survey_manager.read_sas import read_sas` | `from openfisca_survey_manager.io.readers import read_sas` |
| `from openfisca_survey_manager.read_spss import read_spss` | `from openfisca_survey_manager.io.readers import read_spss` |
| `from openfisca_survey_manager.read_dbf import read_dbf` | `from openfisca_survey_manager.io.readers import read_dbf` |
| `from openfisca_survey_manager.calibration import Calibration` | `from openfisca_survey_manager.processing.weights import Calibration` |
| `from openfisca_survey_manager.calmar import calmar` | `from openfisca_survey_manager.processing.weights import calmar` |
| `from openfisca_survey_manager.calmar import check_calmar` | `from openfisca_survey_manager.processing.weights import check_calmar` |
| `from openfisca_survey_manager.utils import do_nothing, load_table, ...` | Voir section 2 (utils) |

**Symboles exportés par `paths`** (même noms dans `configuration.paths`) :
`config_ini`, `default_config_files_directory`, `is_in_ci`, `openfisca_survey_manager_location`, `private_run_with_data`, `test_config_files_directory`.

**Symboles exportés par `utils`** :
- Depuis `common.misc` : `asof`, `do_nothing`, `inflate_parameter_leaf`, `inflate_parameters`, `parameters_asof`, `variables_asof`.
- Définis dans `utils.py` : `load_table` (à déplacer vers un module adapté, ex. `core` ou `io`, avant suppression de `utils.py`).

---

## 2. Fichiers à modifier quand on retire les ré-exports

Avant (ou en même temps que) la suppression des fichiers listés en section 3, mettre à jour les imports dans les fichiers suivants.

### 2.1 Imports depuis `config`, `paths`

| Fichier | Remplacer |
|---------|-----------|
| `tests/input_dataframe_generator.py` | `paths` → `configuration.paths` (module déplacé dans `tests/`) |
| `scripts/build_collection.py` | `paths` → `configuration.paths` |
| `temporary.py` | `paths` → `configuration.paths` |
| `google_colab.py` | `paths` → `configuration.paths` |
| `coicop.py` | `paths` → `configuration.paths` |
| `matching.py` | `paths` → `configuration.paths` |
| `tests/test_read_sas.py` | `paths` → `configuration.paths` ; `read_sas` → `io.readers` |
| `tests/test_quantile.py` | `paths` → `configuration.paths` |
| `tests/test_scenario.py` | `paths` → `configuration.paths` |

### 2.2 Imports depuis `survey_collections`, `surveys`, `tables`

| Fichier | Remplacer |
|---------|-----------|
| `tests/input_dataframe_generator.py` | `survey_collections`, `surveys` → `core.dataset`, `core.survey` |
| `simulations.py` | `survey_collections`, `utils` → `core.dataset` ; utils → `common.misc` + module de `load_table` |
| `utils.py` | `survey_collections` → `core.dataset` (pour `load_table`) |
| `scripts/build_collection.py` | `survey_collections`, `surveys` → `core.dataset`, `core.survey` |
| `scenarios/abstract_scenario.py` | `calibration`, `surveys` → `processing.weights`, `core.survey` |
| `tests/test_surveys.py` | `survey_collections`, `surveys` → `core.dataset`, `core.survey` |
| `tests/test_coverage_boost.py` | `survey_collections`, `surveys`, `utils` → idem |
| `tests/test_add_survey_to_collection.py` | `survey_collections` → `core.dataset` |
| `tests/test_parquet.py` | `survey_collections` → `core.dataset` ; `surveys` (NoMoreDataError) → `core.survey` |

### 2.3 Imports depuis `read_sas`, `read_spss`, `read_dbf`

| Fichier | Remplacer |
|---------|-----------|
| `core/table.py` | `from openfisca_survey_manager import read_sas` → `from openfisca_survey_manager.io.readers import read_sas` ; `read_sas.read_sas` → `read_sas` dans `reader_by_source_format`. Puis `from openfisca_survey_manager.read_spss import read_spss` → `from openfisca_survey_manager.io.readers import read_spss` (dans le try/except). |
| `tests/test_read_sas.py` | `from ...paths import ...` → `configuration.paths` ; `from ...read_sas import read_sas` → `from ...io.readers import read_sas` |

### 2.4 Imports depuis `calibration`, `calmar`

| Fichier | Remplacer |
|---------|-----------|
| `scenarios/abstract_scenario.py` | `calibration` → `processing.weights` |
| `tests/test_calibration.py` | `calibration` → `processing.weights` |
| `tests/test_calmar.py` | `calmar` → `processing.weights` |

### 2.5 Imports depuis `utils`

| Fichier | Remplacer |
|---------|-----------|
| `simulations.py` | `utils.do_nothing`, `utils.load_table` → `common.misc.do_nothing` + module contenant `load_table` |
| `tests/test_coverage_boost.py` | `utils.do_nothing` → `common.misc.do_nothing` |
| `tests/test_legislation_inflator.py` | `utils.inflate_parameters`, `parameters_asof` → `common.misc` |
| `tests/test_tax_benefit_system_asof.py` | `utils.parameters_asof`, `variables_asof` → `common.misc` |

**Note** : `load_table` dépend de `SurveyCollection` ; il doit vivre soit dans un module qui importe `core.dataset`, soit être déplacé (ex. `core.dataset` ou un module `io.loaders`) avant de supprimer `utils.py`.

---

## 3. Fichiers à supprimer (ré-exports)

Une fois tous les imports mis à jour selon les sections 1 et 2, on pourra supprimer les fichiers suivants (ils ne contiennent que des ré-exports) :

- `config.py`
- `paths.py`
- `tables.py`
- `surveys.py`
- `survey_collections.py`
- `read_sas.py`
- `read_spss.py`
- `read_dbf.py`
- `calibration.py`
- `calmar.py`
- `utils.py` (après déplacement de `load_table` et mise à jour des imports listés en 2.5)

---

## 4. Modules sans ré-export (imports canoniques)

Ces modules n’ont pas de fichier ré-export à la racine ; le code interne les utilise déjà. Pour du code externe ou de la doc, les imports canoniques sont :

| Symbole | Import canonique |
|---------|------------------|
| `harmonize_data_frame_columns` | `from openfisca_survey_manager.processing.harmonization import harmonize_data_frame_columns` (ou `from openfisca_survey_manager.processing import harmonize_data_frame_columns`) |
| `write_table_to_hdf5` | `from openfisca_survey_manager.io.hdf import write_table_to_hdf5` (ou `from openfisca_survey_manager.io.writers import write_table_to_hdf5`) |
| `write_table_to_parquet` | `from openfisca_survey_manager.io.writers import write_table_to_parquet` |

---

## 5. Package racine `openfisca_survey_manager`

Aujourd’hui le `__init__.py` du package n’expose que les exceptions. Si du code externe fait par exemple `from openfisca_survey_manager import read_sas`, il s’appuie sur le sous-module `read_sas.py`. **Après retrait des ré-exports**, ces chemins d’import ne seront plus valides (échec à l’import) ; les migrer vers `from openfisca_survey_manager.io.readers import read_sas` (voir section 1).

À faire avant ou après la migration : vérifier dans ce dépôt et les projets dépendants (openfisca-france-data, etc.) les imports depuis la racine du package ou depuis les anciens modules listés en section 3.

---

## 6. Ordre recommandé pour la migration

1. **Déplacer `load_table`** vers un module définitif (ex. `core.dataset` ou `io.loaders`) et mettre à jour les appels (section 2.5).
2. **Mettre à jour tous les imports internes** (section 2) vers les nouveaux chemins, fichier par fichier.
3. **Lancer la suite de tests** : `pytest` ; corriger les oublis jusqu’à 0 échec.
4. **Supprimer les fichiers de ré-export** listés en section 3.
5. **Vérifier les usages externes** (section 5) et documenter les changements dans le CHANGELOG (breaking changes).

---

## 7. Évolutions optionnelles ultérieures

- Renommer le dossier `common/` en `utils/` une fois `utils.py` supprimé (comme prévu dans le plan de refactoring).
- Renommer `configuration/` en `config/` si on souhaite un nom plus court (en cohérence avec le plan).
- Ces renommages impliqueront une nouvelle vague de mise à jour des imports (configuration → config, common → utils).
