# 🏗️ Vision : OpenFisca Data Stack officielle

**Objectif** : Formaliser une stack data OpenFisca claire, avec rôles et frontières bien définis. Ce ticket sert de référence pour les PR de refactor (survey-manager → data-manager, découplage, etc.) et les évolutions à venir.

---

## OpenFisca Data Stack (cible)

```
OpenFisca Data Stack
├── openfisca-data-manager
├── openfisca-<country>-data
├── openfisca-policy-analysis
└── (OpenFisca Core)
```

---

## 1️⃣ openfisca-data-manager (cœur officiel)

**Évolution cible de l’actuel openfisca-survey-manager.**

### 🎯 Rôle

Brique **universelle**, **indépendante des pays**.

**Responsabilités :**

- abstraction backend (parquet par défaut)
- gestion datasets versionnés
- pipeline data
- validation schéma
- métadonnées reproductibles
- **API stable d’accès aux microdata**

**Ce qu’il ne doit PAS faire :**

- dépendre d’un tax benefit system
- connaître des variables OpenFisca
- contenir de l’analyse policy

### API cible minimale stable (v1.0)

```python
dataset = DataManager.load("lfs", year=2019)
df = dataset.to_pandas(columns=["income", "weight"])
```

Et :

- `dataset.metadata`
- `dataset.schema`
- `dataset.hash`

---

## 2️⃣ openfisca-<country>-data

**Exemples :**

- `openfisca-france-data`
- `openfisca-tunisia-data`

### 🎯 Rôle

Préparer les **microdata pour ingestion OpenFisca**.

**Dépendances :**

- `openfisca-data-manager`
- `openfisca-<country>`

**Responsabilités :**

- mapping variables enquête → variables OpenFisca
- création entités
- périodes
- validation cohérence avec le TBS

**API possible :**

```python
adapter = CountryDataAdapter(dataset)
of_input = adapter.to_openfisca_entities()
```

---

## 3️⃣ openfisca-policy-analysis

**Contenu actuel du survey-manager à migrer / extraire ici.**

- survey scenarios
- baseline vs reform
- agrégations pondérées
- indicateurs inégalités
- diagnostics

---

## Liaison avec les PR

- Ce ticket (issue) est lié aux PR de **refactor openfisca-survey-manager** (réorganisation, nettoyage, processing/weights, etc.).
- Les PR suivantes (découplage data-manager / policy-analysis, API v1.0) pourront aussi référencer cette issue comme objectif de long terme.
