# OpenFisca Survey Manager

[![Build Status via Travis CI](https://travis-ci.org/openfisca/openfisca-survey-manager.svg?branch=travis)](https://travis-ci.org/openfisca/openfisca-survey-manager)

## Presentation

[OpenFisca](http://www.openfisca.fr/) is a versatile microsimulation free software.

This is the source code to a survey manager when openfisca is used with data.
It provides an API to access HDF data.
It also provides a script that transforms SAS, stata, SPSS, CSV data files to HDF data files along with some meta-data so they can be used by the API.

## Usage

To be able to use the survey manager you have to edit two configuration files.

- Copy [raw_data_template.ini](raw_data_template.ini) to `raw_data.ini` and edit the latter to reference
    the location of your raw data (SAS, stata, SPSS, CSV files). For paths in Windows, use `/` instead of `\` to separate folders. You do not need to put quotes, even when the path name contains spaces.

- Copy [config_template.ini](config_template.ini) to `config.ini` and edit its mandatory fields.

`raw_data.ini` and `config.ini` must not be committed (they are ignored by `.gitignore`).

These configurations files will be used by the script [`build_collection.py`](openfisca_survey_manager/scripts/build_collection.py) to build the
HDF files.

## Contribute

OpenFisca is a free software project.
Its source code is distributed under the [GNU Affero General Public Licence](http://www.gnu.org/licenses/agpl.html)
version 3 or later (see COPYING).

Feel free to join the OpenFisca development team on [GitHub](https://github.com/openfisca) or contact us by email at
contact@openfisca.fr
