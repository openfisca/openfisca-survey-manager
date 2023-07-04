# Publish to conda

There are two publishing systems for `openfisca-survey-manager` conda packages:
- A fully automatic CI that publishes to an _openfisca_ channel. See below for more information.
- A more complex CI calling Conda-Forge CI, that publishes to the _Conda-Forge_ channel. See https://www.youtube.com/watch?v=N2XwK9BkJpA for an introduction to Conda-Forge. We do not use it for this project.

## Automatic upload

The CI automaticaly builds the conda package from the [PyPi package](https://pypi.org/project/OpenFisca-Survey-Manager/), and uploads it to [anaconda.org](https://anaconda.org/search?q=openfisca-survey-manager). You can check this out in the GitHub Actions CI file `.github/workflow/workflow.yml` and its `publish-to-conda` step.

## Manual actions made to make it works the first time

- Create an account on https://anaconda.org.
- Create a token on https://anaconda.org/openfisca/settings/access with _Allow write access to the API site_. Warning, it expire on 2023/01/13.
- Put the token in a CI env variable ANACONDA_TOKEN.

## Manual actions before CI exist

To create the package you can do the following in the project root folder:

- Edit `.conda/meta.yaml` and update it if needed:
    - Version number
    - Hash SHA256
    - Package URL on PyPi

- Build & Upload package:
    - `conda install -c anaconda conda-build anaconda-client`
    - `conda build .conda`
    - `anaconda login`
    - `anaconda upload openfisca-core-<VERSION>-py_0.tar.bz2`