
# Changelog

## 0.16.2

* Use `simulation.delete_arrays` introduced by openfisca-core version 24.10.0

## 0.16.1

* Rename test_random_data_generator method to create_randomly_initialized_survey_scenario
* Improve doc tests
* use pytest instead of nosetest

## 0.16.0

* Provide summarize_variable for enums

## 0.15.3

* Fix asof

## 0.15.2

* Test tagging

## 0.15.1

* Remove travis config file

## 0.15.0

* openfisca-survey-manager can be used with both python 2 and 3

## 0.14.2

* Use `simulation.set_input` introduced by openfisca-core version 24.5.0

## 0.14.1

* Use [weightedcalcs](https://github.com/jsvine/weightedcalcs) to compute quantiles

## 0.14.0

* Introduce new tools: `asof` extract from any tax_benefit_system its variables and parameters as of some date

## 0.13.0

* Introduce new option : add the `count_non_zero` value in the `aggfunc` argument of `compute_aggregate`

## 0.12

* Introduce new `SurveyScenario` methods:
  - dump_simulations: dumps the `survey_scenario simulations
  - restore_simulations: retores previously dumped `survey_scenario simulations

## 0.11

### 0.11.1

* Fix travis tests

### 0.11.0

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
* CLarify code (use variable instead of column) and add some doctring

## 0.9.2
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

### 0.8.0

* Improve `compute_aggregates` and `compute_pivot_table`

### 0.6.1

* Fix `config_files_directory` default in utils

### 0.6.0

* Adapat to new syntax (progressive elimination of `entity_key_plural`)

## 0.5.2

* Fix path of entry point build-collection

### 0.5.2

* Add entry point build-collection

### 0.5.1

* Fix tagging

## 0.5

* Create Changelog.md
* Check version and changelog when pushing
