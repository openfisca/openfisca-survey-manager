# Plan d'améliorations – OpenFisca Survey Manager

Ce document reformule et met en œuvre un plan d’améliorations pour OpenFisca Survey Manager (inspiré du [partage ChatGPT Améliorations OpenFisca Survey](https://chatgpt.com/share/69a1ce50-d17c-8004-9a23-33144b6afa37), dont le détail n’est pas lisible côté outil).

## Objectifs

- **Qualité du code** : remplacer les sorties debug ad hoc par du logging structuré.
- **Maintenabilité** : faciliter le diagnostic en production et en CI sans `print()`.
- **Cohérence** : utiliser le module `logging` partout pour les messages de diagnostic.

## Réalisé dans cette PR

1. **`matching.py`**
   - Remplacement du `print(r_script)` par `log.debug(...)` pour le script R (feather).
   - Dans `nnd_hotdeck_using_rpy2`, remplacement des `print(1)`, `print(receiver)`, etc. en cas d’exception par un `log.exception(...)` avec contexte (shapes, match_vars) puis re-raise, pour ne plus avaler l’erreur.

2. **`calmar.py`**
   - Dans `check_calmar()`, remplacement du `print(variable, margin, ...)` par `log.debug(...)` pour la comparaison des marges.

## Pistes pour la suite (hors cette PR)

- Remplacer les autres `print()` restants (e.g. `read_sas`, `read_spss`, `simulations.py`, `abstract_scenario.py`) par du logging adapté (niveau debug/info).
- Traiter les TODOs identifiés (calibration, filtering, etc.) et documenter les limites.
- Enrichir les type hints et réduire l’usage d’`assert` pour les erreurs métier au profit d’exceptions explicites.
