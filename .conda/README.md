# Publish to conda

There are two publishing systems for openfisca conda packages:
- A fully automatic CI that publishes to an _openfisca_ channel. `openfisca-survey-manager` conda package is published to this channel. See below for more information.
- A more complex CI calling Conda-Forge CI, that publishes to the _Conda-Forge_ channel. See https://www.youtube.com/watch?v=N2XwK9BkJpA for an introduction to Conda-Forge. We do not use it for this repository.

## Automatic upload

The CI automaticaly builds the conda package from the [PyPi package](https://pypi.org/project/OpenFisca-Survey-Manager/), and uploads it to [anaconda.org](https://anaconda.org/search?q=openfisca-survey-manager). You can check this out in the GitHub Actions configuration file `.github/workflow/workflow.yml` and its `publish-to-conda` step.

## Manual actions made to make it work the first time

- Create an account on https://anaconda.org.
- Create a token on https://anaconda.org/openfisca/settings/access with _Allow write access to the API site_.
- Put the token in a CI environment variable named `ANACONDA_TOKEN`.

⚠️ Warning, the current token expires on 2025/01/14. Check existing tokens and their expiration dates on Anaconda.org website and its [_Access_ section](https://anaconda.org/openfisca/settings/access).

## Manual actions before initializing the CI or to test the conda packaging

Before initializing the CI the conda package was created locally. Now, the conda packaging is done by the CI. Nevertheless, if you want to test it, this section describes how a package is built and uploaded.

To create a conda package for this repository you can check the packaging configuration in `.conda/meta.yaml` and do the following in the project root folder:

1. Build package:
    - `conda install -c anaconda conda-build anaconda-client`  
      (`conda-build` to build the package and [anaconda-client](https://github.com/Anaconda-Platform/anaconda-client) to push the package to anaconda.org)
    - `conda build .conda --channel openfisca`

2. Upload the package to Anaconda.org, but DON'T do it if you don't want to publish your locally built package as an official OpenFisca-Survey-Manager library:
    - `anaconda login`
    - `anaconda upload openfisca-survey-manager-<VERSION>-py_0.tar.bz2`
