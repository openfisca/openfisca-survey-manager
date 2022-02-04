#! /usr/bin/env bash

python -m build  # build this package in the dist directory
twine upload dist/* --username $PYPI_USERNAME --password $PYPI_PASSWORD  # publish
