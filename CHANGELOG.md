﻿# Changelog

### 1.1.9 [#274](https://github.com/openfisca/openfisca-survey-manager/pull/274)

* Technical changes
  - Adapt config files location to private Ci-runs of LexImpact (hack like everything dealing with config files location definition).

### 1.1.8 [#272](https://github.com/openfisca/openfisca-survey-manager/pull/272)

* Technical changes
  - Use `openfisca-core` version >= 41.0.3.

### 1.1.7 [#271](https://github.com/openfisca/openfisca-survey-manager/pull/271)

* Technical changes
  - Set pandas dependency to version >= 2.0.3, <3.0.

### 1.1.5 [#265](https://github.com/openfisca/openfisca-survey-manager/pull/265)

* Technical changes
  - Use `find_namespace_packages` and instead of `find_packages` in `setup.py`

### 1.1.4 [#264](https://github.com/openfisca/openfisca-survey-manager/pull/264)

* Technical changes
  - Change importlib metadata import to work with all Python version

### 1.1.3 [#263](https://github.com/openfisca/openfisca-survey-manager/pull/263)

* Technical changes
  - Use importlib instead of pkg_resources to avoid deprecation warnings

### 1.1.2 [#262](https://github.com/openfisca/openfisca-survey-manager/pull/262)

* Technical changes
  - Remove old `CircleCI` continuous integration configuration
  - Set `README` CI badge to current `GitHub Actions` CI

### 1.1.1 [#261](https://github.com/openfisca/openfisca-survey-manager/pull/261)

* Technical changes
  - Fix `Conda build` step in `publish-to-conda` GitHub Actions job
    - Define `OpenFisca-Survey-Manager` package dependencies once for `PyPI` and `conda`
      - Use `setup.py` general requirement and extra requirements for `conda` package
      - Adapt `tables` library name to `pytables` for `conda`
  - Build `conda` package from repository sources instead of `PyPI` .tar.gz

## 1.1.0 [#260](https://github.com/openfisca/openfisca-survey-manager/pull/260)

* New features
- Add options in inflate_parameters and inflate_parameter_leaf:
  - `start_update_instant` : Instant of the year when the inflation should start, if different from January 1st
  - `round_ndigits` : number of digits in the rounded result
- Adjustment of inflate_parameters to use it with parameter leaf

### 1.0.2 [#259](https://github.com/openfisca/openfisca-survey-manager/pull/259)

* Technical changes
  - A parameter `config_files_directory` exist but it is not used evrywhere, this PR generalize it.
  - Add tests using this parameter.

### 1.0.1 [#257](https://github.com/openfisca/openfisca-survey-manager/pull/257)

* Technical changes
  - In GitHub Actions workflow, fixes the `check-for-functional-changes` → **`deploy`** → `publish-to-conda` jobs sequence
    - Fix the activation of the `deploy` job by fixing how it gets `check-for-functional-changes` output status
    - Allow the activation of `publish-to-conda` job that needs the `deploy` job
  - Add conda configuration files to non functional files for CI

# 1.0.0 [#252](https://github.com/openfisca/openfisca-survey-manager/pull/252)

* Technical improvement
  - Impacted periods: all.
  - Impacted areas: all.
  - Details:
    - Upgrade every dependencies & use their latest versions

### 0.47.2 [#249](https://github.com/openfisca/openfisca-survey-manager/pull/249)

* Technical changes
  - Fix `default_config_directory` for use with `openfisca-france-data` in a CI

### 0.47.1 [#246](https://github.com/openfisca/openfisca-survey-manager/pull/246)

* Bug fix
  - Debug france data ci (fixes 0.47.0)

## 0.47.0 [#245](https://github.com/openfisca/openfisca-survey-manager/pull/245)

* Technical changes
  - Fix `default_config_directory` for use with `openfisca-france-data` in a CI

### 0.46.19 [#244](https://github.com/openfisca/openfisca-survey-manager/pull/244)

* Technical changes
  - Bump to publish package

### 0.46.18 [#243](https://github.com/openfisca/openfisca-survey-manager/pull/243)

* Technical changes
  - Bump to publish package

### 0.46.17 [#242](https://github.com/openfisca/openfisca-survey-manager/pull/242)

* Technical changes
  - Bug fix in `SurveyCollection.load`

### 0.46.16

* CI test

### 0.46.15 [#236](https://github.com/openfisca/openfisca-survey-manager/pull/236)

* Technical changes
  - Put back test in CI
  - Fix coveralls config fot GitHub Actions
  - Add a test for create_data_frame_by_entity
  - Bump Actions and Python version to fix warnings

### 0.46.14 [#234](https://github.com/openfisca/openfisca-survey-manager/pull/234)

* Technical changes
  - Convert every cells of a column to string.

### 0.46.13 [#233](https://github.com/openfisca/openfisca-survey-manager/pull/233)

* Technical changes
  - Correcting the code asking for the period before it's instated
  - Checking the new period assignment

### 0.46.12 [#232](https://github.com/openfisca/openfisca-survey-manager/pull/232)

* Technical changes
  - Deal with Nan in Enum variables

### 0.46.11 [#227](https://github.com/openfisca/openfisca-survey-manager/pull/227)

* Technical changes
  - Add build of a tar.gz
  - Add a make entry for build
  - Move CI from Circle CI to GitHub Action (Except `make test` that run only on CircleCI)

### 0.46.10 [#229](https://github.com/openfisca/openfisca-survey-manager/pull/229)

* Technical changes
  - Add tar.gz to PyPi
  - Add display readme to PyPi

### 0.46.9 [#228](https://github.com/openfisca/openfisca-survey-manager/pull/228)

* Technical changes
  - Refactor tables method to mutualize code
  - Save variables in table survey data

### 0.46.8 [#226](https://github.com/openfisca/openfisca-survey-manager/pull/226)

* Technical changes
  - Add a set seed in `mark_weighted_percentiles`, so that when a survey scenario with a baseline and a reform is run, variables which use this function take the same value for a given entity between the baseline and the reform.

### 0.46.7 [#227](https://github.com/openfisca/openfisca-survey-manager/pull/225)

* Technical changes
  - Handle explicitly SAS related dependecy.

### 0.46.6 [#224](https://github.com/openfisca/openfisca-survey-manager/pull/224)

* Bug fix
  - Using pyreadstat instead of SAS7BDAT which is no more the canonical way to read sas files into pandas dataframes.

### 0.46.5 [#223](https://github.com/openfisca/openfisca-survey-manager/pull/223)

* Bug fix
  - Deal with HDF5 file opening strict policy in build-collection

### 0.46.4 [#219](https://github.com/openfisca/openfisca-survey-manager/pull/219)

* Technical changes
  - Better handling of CategoricalDtype in input data

### 0.46.3 [#217](https://github.com/openfisca/openfisca-survey-manager/pull/217)

* Bug fix
  - Deal with HDF5 file opening strict policy

### 0.46.2 [#214](https://github.com/openfisca/openfisca-survey-manager/pull/214)

* New features
  - Introduce AbsstractSurveyScenario.calculate_series

### 0.46.1 [#211](https://github.com/openfisca/openfisca-survey-manager/pull/211)

* Technical changes
  - Improve dialect detection for csv files

## 0.46 [#210](https://github.com/openfisca/openfisca-survey-manager/pull/210)

* Technical changes
  - Hack to deal with encodings and delimiter not detected by pandas.read_csv

## 0.45 [#143](https://github.com/openfisca/openfisca-survey-manager/pull/143)

* Technical changes
  - In compute_marginal_tax_rate allow for automatic aggregation on group entity when target and varying variables entity are not the same and the varying variable entity is a person one.

### 0.44.2 [#208](https://github.com/openfisca/openfisca-survey-manager/pull/208)

* Bug fix
  - Fix typo.

### 0.44.1 [#207](https://github.com/openfisca/openfisca-survey-manager/pull/207)

* Bug fix
  - Fix aggregates export to html.

## 0.44 [#206](https://github.com/openfisca/openfisca-survey-manager/pull/206)

* New feature
  - Ability to export aggregates to html.

## 0.43 [#135](https://github.com/openfisca/openfisca-survey-manager/pull/135)

* New feature
  - Introduce aggregates.

### 0.42.3 [#189](https://github.com/openfisca/openfisca-survey-manager/pull/189)

* Technical changes
  - Accept categorical columns in input data frames to initialize Enum variables.

### 0.42.2 [#204](https://github.com/openfisca/openfisca-survey-manager/pull/204)

* Technical changes
  - Add on sub-periods when creating a quantile on a larger period

### 0.42.1 [#200](https://github.com/openfisca/openfisca-survey-manager/pull/200)

* Bug fix
  - Let numpy dependence come from openfisca-core

### 0.42.0 [#198](https://github.com/openfisca/openfisca-survey-manager/pull/198)

* New feature
  - Allow to build collections/surveys from csv files

### 0.41.3 [#196](https://github.com/openfisca/openfisca-survey-manager/pull/196)

* Bug fix
  - Enforce HDF store closing when done

### 0.41.2 [#194](https://github.com/openfisca/openfisca-survey-manager/pull/194)

* Bug fix
  - Enforce us of np.array for weights and filters when computing aggregates

### 0.41.1 [#187](https://github.com/openfisca/openfisca-survey-manager/pull/187)

* Update dependencies
### 0.41.0 [#185](https://github.com/openfisca/openfisca-survey-manager/pull/186)

* New features
  - Add a method to compute quantile
  - Extend the computation of marginal tax rate

### 0.40.1 [#185](https://github.com/openfisca/openfisca-survey-manager/pull/185)

* Technical improvement
  - Introduce weighted option in `compute_aggregate` and `compute_pivot_table`
  - Change `weights` to `alternative_weights` in `compute_aggregate` and `compute_pivot_table`

### 0.40.0 [#184](https://github.com/openfisca/openfisca-survey-manager/pull/184)

* Technical improvement
  - Add weights keyword argument to `compute_aggregate` and `compute_pivot_table`

* Improve documentation
  - Use googl style in docstring
  - Add some docstring

### 0.39.1 [#178](https://github.com/openfisca/openfisca-survey-manager/pull/178)

* Bug fix
  - Fix inflate that inflated twice when baseline_simulation == simulation

### 0.39.0 [#170](https://github.com/openfisca/openfisca-survey-manager/pull/170)

- Add statistical helpers to compute top and bottom shares

### 0.38.3 [#XXX](https://github.com/openfisca/openfisca-survey-manager/pull/XXX)

- Fix _set_used_as_input_variables_by_entity

### 0.38.2 [#162](https://github.com/openfisca/openfisca-survey-manager/pull/162)

- Update `pytables` and `numpy` dependencies

### 0.38.1 [#158](https://github.com/openfisca/openfisca-survey-manager/pull/158)

- Clarify documentation on configuration directory and build-collection command

## 0.38.0 [#156](https://github.com/openfisca/openfisca-survey-manager/pull/156)

* New features
  - Introduce `survey_scenario.generate_performance_data(output_dir)`
    - This generates a performance graph and CSV tables containing details about execution times of OpenFisca formulas

### 0.37.3 [#157](https://github.com/openfisca/openfisca-survey-manager/pull/157)

* Technical changes
  - Add `tables` library to default requirements
* Add documentation for users installing, configuring and running the module for the first time

### 0.37.2 [#155](https://github.com/openfisca/openfisca-survey-manager/pull/155)

* Technical changes
  - Improve error mesage in build_collection (fix previous version)

### 0.37.1 [#154](https://github.com/openfisca/openfisca-survey-manager/pull/154)

* Technical changes
  - Improve error mesage in build_collection

## 0.37.0

* Technical changes
  - Add ignorecase argument to Survey.get_values

### 0.36.3 [#152](https://github.com/openfisca/openfisca-survey-manager/pull/152)

* Technical changes
  - Fix asof for `TaxScale`
  - Use `simulation.get_known_periods` instead of `Holder`'s method in `summariaze_variable`

## 0.36.0 [#152](https://github.com/openfisca/openfisca-survey-manager/pull/152)

* Technical changes
  - Create collections directory when it is missing

### 0.35.2 [#150](https://github.com/openfisca/openfisca-survey-manager/pull/150)

* Technical changes
  - Fix assets inclusion

### 0.35.1 [#149](https://github.com/openfisca/openfisca-survey-manager/pull/149)

* Technical changes
  - Fix deprecation in pandas.
  - Fix stripping of coicop categories

## 0.35 [#148](https://github.com/openfisca/openfisca-survey-manager/pull/148)

* Introduce some functions to deal with coicop nomenclature

## 0.34 [#147](https://github.com/openfisca/openfisca-survey-manager/pull/147)

* Better handling of categorical variables

## 0.33 [#145](https://github.com/openfisca/openfisca-survey-manager/pull/145)

* Convert string-like columns to category and save to HDF files in table mode

### 0.32.1 [#144](https://github.com/openfisca/openfisca-survey-manager/pull/144)

* Fix typo (remove quotes) in inflate

## 0.32 [#143](https://github.com/openfisca/openfisca-survey-manager/pull/143)

* Remove python 2 unicode marks `u"` and `u'`.

## 0.31 [#140](https://github.com/openfisca/openfisca-survey-manager/pull/140)

* Group column dropping since DataFrame.drop is expensive.

### 0.30.1 [#137](https://github.com/openfisca/openfisca-survey-manager/pull/137)

* Fix bug in input data loader

## 0.30.0 [#136](https://github.com/openfisca/openfisca-survey-manager/pull/136)

* Adding description
* Adding function documentation.

## 0.29.0 [#134](https://github.com/openfisca/openfisca-survey-manager/pull/134)

* New features
  - Introduce compute_marginal_tax_rate.

## 0.28.0 [#133](https://github.com/openfisca/openfisca-survey-manager/pull/133)

- Fix _set_used_as_input_variables_by_entity
- Add missing custom_input_data_frame before initializing the data
- Fix entity ids setting

## 0.27.0 [#132](https://github.com/openfisca/openfisca-survey-manager/pull/132)

* Technical changes
  - Fix create_data_frame_by_entity
  - Fix some deprecations

## 0.26.0

* New features
  - Neutralized variables are now correctly handled by summarize_variable
  - Extend testing to doctest

## 0.25.0 [#126](https://github.com/openfisca/openfisca-survey-manager/pull/126)

* New features
  - create_data_frame_by_entity is able to handle expressions for filtering (filter_by can be an expression)
  - This allow compute_aggregate and compute_pivot_table to handle expressions as well for filter_by.

* Deprecations
  - Deprecate helper get_entity
  - Deprecate helper get_weights

## 0.24.0 [#127](https://github.com/openfisca/openfisca-survey-manager/pull/127)

* Fix a bug in create_data_frame_by_entity

## 0.23.0 [#124](https://github.com/openfisca/openfisca-survey-manager/pull/124)

* Rename weight_column_name_by_entity to weight_variable_by_entity

## 0.22.0 [#123](https://github.com/openfisca/openfisca-survey-manager/pull/123)

* Add github templates

## 0.21.0 [#122](https://github.com/openfisca/openfisca-survey-manager/pull/122)

* Use SimulationBuilder.join_with_persons to initialize entites

## 0.20.0 [#120](https://github.com/openfisca/openfisca-survey-manager/pull/120)

* Adapt to SimulatioBuilder shipping with openfisa-core v34

### 0.19.1 [#107](https://github.com/openfisca/openfisca-survey-manager/pull/107)

* Fix `set_table_in_survey`

## 0.19.0 [#103](https://github.com/openfisca/openfisca-survey-manager/pull/103)

* Add a `--path PATH` option to `build-collection`

### 0.18.5 [#101](https://github.com/openfisca/openfisca-survey-manager/pull/101)

* Add documentation to `init_from_data`
* Split setters to gain readability

### 0.18.4

* Add badges to help and reassure users/contributors

### 0.18.3

* Update `setup.py` with missing dependencies

### 0.18.2

* Incrementally fixing Calibration

### 0.18.1

* Lower version for pandas dependency

## 0.18.0

* Add a way of creating a raw_data.ini file on Google Colab

### 0.17.5

* Add pyxdg as a core dependency

### 0.17.4

* Fix config.ini initialisation
* Remove ptyhon2 tests

### 0.17.3

* Update MANIFEST.in

### 0.17.2

* Minor change in dependencies to allow more flexibility and use in Binder

### 0.17.1

* Minor Python 2/3 compatibility string issue fixed

## 0.17

* Fix, test and document calmar

### 0.16.5

* Fix asof
* Clean Makefile
* Clean style

### 0.16.4

* Use `simulation.delete_arrays` introduced by openfisca-core version 24.10.0

### 0.16.2, 0.16.3

* Add stata file conversion helper for survey scenarios

### 0.16.1

* Rename test_random_data_generator method to create_randomly_initialized_survey_scenario
* Improve doc tests
* use pytest instead of nosetest

## 0.16.0

* Provide summarize_variable for enums

### 0.15.3

* Fix asof

### 0.15.2

* Test tagging

### 0.15.1

* Remove travis config file

## 0.15.0

* openfisca-survey-manager can be used with both python 2 and 3

### 0.14.2

* Use `simulation.set_input` introduced by openfisca-core version 24.5.0

### 0.14.1

* Use [weightedcalcs](https://github.com/jsvine/weightedcalcs) to compute quantiles

## 0.14.0

* Introduce new tools: `asof` extract from any tax_benefit_system its variables and parameters as of some date

## 0.13.0

* Introduce new option : add the `count_non_zero` value in the `aggfunc` argument of `compute_aggregate`

## 0.12

* Introduce new `SurveyScenario` methods:
  - dump_simulations: dumps the `survey_scenario simulations
  - restore_simulations: retores previously dumped `survey_scenario simulations

### 0.11.1

* Fix travis tests

## 0.11.0

* Add legislation parameters inflator

### 0.10.1

* Cleaner checks for travis use

### 0.10

* Migrate to a new method to pass data to SurveyScenario

### 0.9.10

* Add a difference argument for compute_aggregate (fixes #45)

### 0.9.9

* Add `trace` and `debug` attributes to `AbstractSurveyScenario` to use with `new_simulation`

### 0.9.8

* Create directory for config templates files

### 0.9.7

* Remove unused imports

### 0.9.6

* Add a Quantile class inheriting for Variable

### 0.9.5

* Pandas deprecates the use of sort_index for sort_values
* Numpy [deprecates use of np.float with issubdtype](https://github.com/numpy/numpy/pull/9505)

### 0.9.4

* Fix bug when initialising mono-entity (person-only) TaxBenefitSystem

### 0.9.3

* Fix difference pivot_table computation
* Clarify code (use variable instead of column) and add some doctring

### 0.9.2

* Hack to custom default_config_files_diretory at CASD when using taxipp

## 0.9.0

* Migrate to openfisca-core v20 syntax
* Fix a bug in `create_data_frame_by_entity`

### 0.8.13

* Migrate to openfisca-core v14.1.2 syntax

### 0.8.12

* Fix a bug resulting from pandas [v0.20 pivot_table fix](https://github.com/pandas-dev/pandas/pull/13554)

### 0.8.11

* Decrease logs verbosity by starting using the DEBUG level more often

### 0.8.10

* Fix a bug in `compute_pivot_table` which was no more able to compute non-difference pivot-table

### 0.8.9

* Fix a bug when variables are missing form the tax and benefit system in `create_entity_by_dataframe`

### 0.8.8

* Improve handling of difference option in `create_entity_by_dataframe`

### 0.8.7

* Improve `create_entity_by_dataframe` by adding `expressions` and `merge` options and enhancing `filter_by`

### 0.8.4

* Fix `summarize_variable` when dealing with neutralized variables

### 0.8.3

* Add humanize to dependencies

### 0.8.2

* Fix a bug when `output_cache` is unset

### 0.8.1

* Add automatic push to PyPi

## 0.8.0

* Improve `compute_aggregates` and `compute_pivot_table`

### 0.6.1

* Fix `config_files_directory` default in utils

### 0.6.0

* Adapat to new syntax (progressive elimination of `entity_key_plural`)

### 0.5.2

* Fix path of entry point build-collection
* Add entry point build-collection

### 0.5.1

* Fix tagging

## 0.5

* Create Changelog.md
* Check version and changelog when pushing
