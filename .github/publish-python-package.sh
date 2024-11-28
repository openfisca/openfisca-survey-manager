#! /usr/bin/env bash

make build
twine upload dist/* --username $PYPI_USERNAME --password $PYPI_PASSWORD  # publish
