# RFC-001 : OpenFisca Data Stack

**Statut** : Draft  
**Issue** : [#381](https://github.com/openfisca/openfisca-survey-manager/issues/381)  
**Auteur(s)** : Équipe OpenFisca  
**Date** : 2025-01

---

## Résumé

Cette RFC formalise une **stack data OpenFisca** avec rôles et frontières explicites. Elle définit l’évolution cible de l’actuel `openfisca-survey-manager` vers un cœur data réutilisable (`openfisca-data-manager`), la place des dépôts pays (`openfisca-<country>-data`) et celle de la couche analyse (`openfisca-policy-analysis`). Elle sert de référence pour les PR de refactor et les évolutions à venir.

---

## 1. Contexte et motivation

### 1.1 Problème

Aujourd’hui, la gestion des données d’enquête et l’analyse de politique sont fortement couplées dans `openfisca-survey-manager`. Il en résulte :

- une frontière floue entre « accès aux microdata » et « analyse (scénarios, réformes, agrégats) » ;
- une réutilisation limitée du cœur data en dehors des cas d’usage policy ;
- une évolution difficile (backend, schémas, reproductibilité) sans impacter toute la stack.

### 1.2 Objectif

Définir une **OpenFisca Data Stack** claire : briques, responsabilités, APIs cibles et règles de dépendance, afin de guider le refactor et les futures évolutions.

---

## 2. Objectifs et non-objectifs

### 2.1 Objectifs

- Séparer conceptuellement (et à terme en code) : **données** (accès, stockage, schémas) vs **analyse** (scénarios, réformes, agrégats).
- Proposer une API data minimale stable (v1.0) pour l’accès aux microdata.
- Clarifier le rôle de chaque brique (data-manager, country-data, policy-analysis) et leurs dépendances.
- Aligner les PR de refactor (survey-manager) et les décisions long terme sur cette vision.

### 2.2 Non-objectifs

- Cette RFC ne fixe pas de calendrier de mise en œuvre ni d’ordre précis de migration.
- Elle ne détaille pas l’implémentation technique (choix de librairies, formats internes) au-delà des principes et des APIs cibles.

---

## 3. Spécification : OpenFisca Data Stack (cible)

### 3.1 Vue d’ensemble

```
OpenFisca Data Stack
├── openfisca-data-manager   (cœur data, pays-agnostique)
├── openfisca-<country>-data (adaptation microdata → OpenFisca par pays)
├── openfisca-policy-analysis( scénarios, réformes, agrégats, indicateurs )
└── OpenFisca Core           (moteur de calcul)
```

### 3.2 Brique 1 : openfisca-data-manager

**Évolution cible de l’actuel openfisca-survey-manager (cœur data).**

- **Rôle** : brique **universelle**, **indépendante des pays**.
- **Responsabilités** :
  - abstraction backend (parquet par défaut, HDF en transition) ;
  - gestion de datasets versionnés ;
  - pipeline data (lecture, nettoyage, écriture) ;
  - validation de schéma ;
  - métadonnées reproductibles ;
  - **API stable d’accès aux microdata**.
- **Ce qu’il ne doit pas faire** :
  - dépendre d’un tax benefit system ;
  - connaître des variables OpenFisca ;
  - contenir de l’analyse policy.

**API cible minimale stable (v1.0)** :

```python
dataset = DataManager.load("lfs", year=2019)
df = dataset.to_pandas(columns=["income", "weight"])
```

Et exposition de :

- `dataset.metadata`
- `dataset.schema`
- `dataset.hash`

### 3.3 Brique 2 : openfisca-<country>-data

Exemples : `openfisca-france-data`, `openfisca-tunisia-data`.

- **Rôle** : préparer les **microdata pour ingestion OpenFisca**.
- **Dépendances** : `openfisca-data-manager`, `openfisca-<country>` (Core).
- **Responsabilités** :
  - mapping variables enquête → variables OpenFisca ;
  - création des entités et périodes ;
  - validation de cohérence avec le TBS.

**API possible** :

```python
adapter = CountryDataAdapter(dataset)
of_input = adapter.to_openfisca_entities()
```

### 3.4 Brique 3 : openfisca-policy-analysis

Contenu actuel du survey-manager à **migrer ou extraire** dans cette brique (ou un module dédié) :

- survey scenarios (baseline vs reform) ;
- agrégations pondérées ;
- indicateurs d’inégalités ;
- diagnostics.

Cette brique s’appuie sur les microdata (via data-manager ou country-data) et sur OpenFisca Core pour les calculs.

---

## 4. Compatibilité et liaison avec le refactor

- Les PR de **refactor openfisca-survey-manager** (réorganisation, nettoyage, processing/weights, core/io, typage, etc.) restent compatibles avec cette RFC : elles préparent la séparation des couches sans imposer de big-bang.
- Les évolutions ultérieures (découplage data-manager / policy-analysis, exposition de l’API v1.0) pourront référencer cette RFC (et l’issue #381) comme objectif de long terme.
- Aucune rupture d’API publique n’est requise à court terme ; la RFC décrit une cible et un cap.

---

## 5. Références

- [Issue #381](https://github.com/openfisca/openfisca-survey-manager/issues/381) (vision Data Stack).
- `docs/REFACTORING_PLAN.md` (réorganisation interne du survey-manager).
- `docs/MIGRATION_IMPORTS.md` (migration des imports après retrait des ré-exports).
- `docs/TICKET_OPENFISCA_DATA_STACK.md` (version ticket originale, à considérer comme remplacée par la présente RFC).
