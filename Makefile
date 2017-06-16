all: flake8 test

check-syntax-errors:
	python -m compileall -q .

clean-pyc:
	rm -rf build dist
	find . -name '*.pyc' -exec rm \{\} \;

ctags:
	ctags --recurse=yes .

flake8:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	flake8 `git ls-files | grep "\.py$$"`

pypi-upload:
	rm -rf dist/*
	python setup.py sdist bdist_wheel
	twine upload dist/*

test: check-syntax-errors
	nosetests openfisca_survey_manager/tests --ignore-files='(test_read_dbf.py)' --exe --with-doctest
