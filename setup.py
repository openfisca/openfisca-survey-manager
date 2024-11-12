#! /usr/bin/env python


"""A tool for managing survey/administrative data.

Useful to deal with survey/administrative data imported in OpenFisca
"""


from setuptools import find_packages, setup
from pathlib import Path

# Read the contents of our README file for PyPi
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

classifiers = """\
Development Status :: 2 - Pre-Alpha
License :: OSI Approved :: GNU Affero General Public License v3
Operating System :: POSIX
Programming Language :: Python
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Topic :: Scientific/Engineering :: Information Analysis
"""

doc_lines = __doc__.split('\n')


setup(
    name = 'OpenFisca-Survey-Manager',
    version = '2.3.3',
    author = 'OpenFisca Team',
    author_email = 'contact@openfisca.fr',
    classifiers = [classifier for classifier in classifiers.split('\n') if classifier],
    description = doc_lines[0],
    keywords = 'survey data',
    license = 'http://www.fsf.org/licensing/licenses/agpl-3.0.html',
    license_files = ("LICENSE.AGPL.txt",),
    url = 'https://github.com/openfisca/openfisca-survey-manager',
    long_description=long_description,
    long_description_content_type='text/markdown',

    data_files = [
        ('share/openfisca/openfisca-survey-manager', ['CHANGELOG.md', 'README.md']),
        ],
    entry_points = {
        'console_scripts': ['build-collection=openfisca_survey_manager.scripts.build_collection:main'],
        },

    # requirements: for conda, package names should follow the package match specifications (e.g. no space after ">=")
    # see https://conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications
    extras_require = {
        'matching': [
            'feather',
            'rpy2 >=3.5.10, < 4.0',
            ],
        'dev': [
            'autopep8 >=2.0.2, < 3',
            'coveralls >=3.3.1, < 4.0',
            'flake8 >= 6.0.0, < 8.0',
            'flake8-bugbear >= 23.3.12, < 25.0',
            'flake8-docstrings >=1.7.0, < 2.0',
            'flake8-print >=5.0.0, < 6.0',
            'flake8-rst-docstrings >=0.3.0, < 0.4.0',
            'openfisca-country-template >=7.1.5, <8.0.0',
            'pytest >=8.3.3, < 9.0',
            'pytest-cov >= 4.0.0, < 7.0',
            'scipy >=1.10.1, < 2.0',
            'pytest-order >=1.1.0, <2.0',
            ],
        'casd': [
            'autopep8 >=2.0.2, < 3',
            'flake8 >= 6.0.0, < 8.0',
            'pycodestyle >=2.10.0, < 3.0',
            'pytest >=7.2.2, < 8.0',
            'scipy >=1.10.1, < 2.0',
            ],
        'sas': [
            'pyreadstat >=1.2.1, < 2.0',
            'sas7bdat >=2.2.3, < 3.0',
            ],
        },
    include_package_data = True,  # Will read MANIFEST.in
    install_requires = [
        'chardet >=5.1.0, < 6.0',
        'configparser >= 5.3.0, < 8.0',
        'humanize >=4.6.0, < 5.0',
        'openfisca-core >=43.0.0, <44.0.0',
        'pandas >=2.0.3, < 3.0',
        'pyarrow >= 13.0.0, < 19.0.0',
        'pyxdg >=0.28, < 0.29',
        'PyYAML >=6.0, < 7.0',
        'tables >=3.8.0, < 4.0',
        'tabulate >=0.9.0, < 0.10.0',
        'weightedcalcs >=0.1.2, < 0.2.0',
        'wquantiles >=0.6, < 0.7',
        ],
    packages = find_packages(),
    zip_safe = False,
    )
