# Publish to conda

There are two publishing systems for `openfisca-survey-manager` conda packages:
- A fully automatic CI that publishes to an _openfisca_ channel. See below for more information.
- A more complex CI calling Conda-Forge CI, that publishes to the _Conda-Forge_ channel. See https://www.youtube.com/watch?v=N2XwK9BkJpA for an introduction to Conda-Forge. We do not use it for this project.

## Automatic upload

The CI automaticaly builds the conda package from the [PyPi package](https://pypi.org/project/OpenFisca-Survey-Manager/), and uploads it to [anaconda.org](https://anaconda.org/search?q=openfisca-survey-manager). You can check this out in the GitHub Actions configuration file `.github/workflow/workflow.yml` and its `publish-to-conda` step.

## Manual actions made to make it work the first time

- Create an account on https://anaconda.org.
- Create a token on https://anaconda.org/openfisca/settings/access with _Allow write access to the API site_.
- Put the token in a CI environment variable named `ANACONDA_TOKEN`.

⚠️ Warning, the current token expires on 2025/01/14. Check existing tokens and their expiration dates on Anaconda.org website and its [_Access_ section](https://anaconda.org/openfisca/settings/access).

## Manual actions before initializing the CI

To create a conda package for this repository you can do the following in the project root folder:

- Edit the `.conda/meta.yaml` and update it if needed with:
    - Version number
    - Hash SHA256
    - Package URL on PyPi

- Build & Upload the package:
    - `conda install -c anaconda conda-build anaconda-client`
    - `conda build .conda`
    - `anaconda login`
    - `anaconda upload openfisca-survey-manager-<VERSION>-py_0.tar.bz2`
