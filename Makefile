all: flake8 test

check-style:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	flake8 `git ls-files | grep "\.py$$"`

check-syntax-errors:
	python -m compileall -q .

clean:
	rm -rf build dist
	find . -name '*.pyc' -exec rm \{\} \;

ctags:
	ctags --recurse=yes .

pypi-upload:
	rm -rf dist/*
	python setup.py sdist bdist_wheel
	twine upload dist/*

test: clean check-syntax-errors
	pytest --ignore=openfisca_survey_manager/tests/test_legislation_inflator.py
