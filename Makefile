all: test

uninstall:
	pip freeze | grep -v "^-e" | sed "s/@.*//" | xargs pip uninstall -y

clean:
	rm -rf build dist
	rm -f openfisca_survey_manager/tests/data_files/config.ini
	rm -f openfisca_survey_manager/tests/data_files/test_parquet_collection.json
	rm -rf openfisca_survey_manager/tests/data_files/test_multiple_parquet_collection
	rm -rf openfisca_survey_manager/tests/data_files/test_parquet_collection
	rm -rf openfisca_survey_manager/tests/data_files/test_random_generator.json
	find . -name '*.pyc' -exec rm \{\} \;

deps:
	uv pip install build twine

install: deps
	@# Install OpenFisca-Survey-Manager for development.
	@# `make install` installs the editable version of OpenFisca-Survey-Manager.
	@# This allows contributors to test as they code.
	uv pip install --editable .[dev,sas]

build: clean deps
	@# Install OpenFisca-Survey-Manager for deployment and publishing.
	@# `make build` allows us to be be sure tests are run against the packaged version
	@# of OpenFisca-Survey-Manager, the same we put in the hands of users and reusers.
	python -m build
	uv pip uninstall --yes OpenFisca-Survey-Manager
	find dist -name "*.whl" -exec uv pip install {}[dev,sas] \;

check-syntax-errors:
	python -m compileall -q .

format-style:
	isort .
	ruff format .

check-style:
	ruff check .

test: clean check-syntax-errors check-style
	@# Launch tests from openfisca_survey_manager/tests directory (and not .) because TaxBenefitSystem must be initialized
	@# before parsing source files containing formulas.
	rm -rf ./openfisca_survey_manager/tests/data_files/config.ini
	rm -rf ./openfisca_survey_manager/tests/data_files/dump
	pytest
