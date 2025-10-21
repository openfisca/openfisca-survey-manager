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
	pip install --upgrade pip build twine

install: deps
	@# Install OpenFisca-Survey-Manager for development.
	@# `make install` installs the editable version of OpenFisca-Survey-Manager.
	@# This allows contributors to test as they code.
	pip install --editable .[dev,sas] --upgrade

build: clean deps
	@# Install OpenFisca-Survey-Manager for deployment and publishing.
	@# `make build` allows us to be be sure tests are run against the packaged version
	@# of OpenFisca-Survey-Manager, the same we put in the hands of users and reusers.
	python -m build
	pip uninstall --yes OpenFisca-Survey-Manager
	find dist -name "*.whl" -exec pip install {}[dev,sas] \;

check-syntax-errors:
	python -m compileall -q ./openfisca_survey_manager/.

test: clean check-syntax-errors lint
	@# Launch tests from openfisca_survey_manager/tests directory (and not .) because TaxBenefitSystem must be initialized
	@# before parsing source files containing formulas.
	rm -rf ./openfisca_survey_manager/tests/data_files/config.ini
	rm -rf ./openfisca_survey_manager/tests/data_files/dump
	pytest

format:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	ruff format `git ls-files | grep "\.py$$"`
	isort `git ls-files | grep "\.py$$"`

lint:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	isort --check `git ls-files | grep "\.py$$"`
	ruff check `git ls-files | grep "\.py$$"`
