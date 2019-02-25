all: test

uninstall:
	pip freeze | grep -v "^-e" | xargs pip uninstall -y

clean:
	rm -rf build dist
	find . -name '*.pyc' -exec rm \{\} \;

deps:
	pip install --upgrade pip twine wheel

install: deps
	@# Install OpenFisca-Survey-Manager for development.
	@# `make install` installs the editable version of OpenFisca-Survey-Manager.
	@# This allows contributors to test as they code.
	pip install --editable .[dev] --upgrade

check-syntax-errors:
	python -m compileall -q .

format-style:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	autopep8 `git ls-files | grep "\.py$$"`

check-style:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	flake8 `git ls-files | grep "\.py$$"`

test: clean check-syntax-errors check-style
	@# Launch tests from openfisca_survey_manager/tests directory (and not .) because TaxBenefitSystem must be initialized
	@# before parsing source files containing formulas.
	rm -rf ./openfisca_survey_manager/tests/data_files/config.ini
	rm -rf ./openfisca_survey_manager/tests/data_files/dump
	pytest
