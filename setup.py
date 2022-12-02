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
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Topic :: Scientific/Engineering :: Information Analysis
"""

doc_lines = __doc__.split('\n')


setup(
    name = 'OpenFisca-Survey-Manager',
    version = '0.46.15',
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
    extras_require = {
        'matching': [
            'feather',
            'rpy2',
            ],
        'dev': [
            'autopep8 >= 1.4.0, < 1.5.0',
            'coveralls >=1.5.0,<3.4.0',
            'flake8 >= 4.0.0, < 4.1.0',
            'flake8-bugbear >= 19.3.0, < 20.0.0',
            'flake8-docstrings == 1.6.0',
            'flake8-print >= 3.1.0, < 4.0.0',
            'flake8-rst-docstrings == 0.2.3',
            'openfisca-country-template >= 3.13.2, < 4.0.0',
            'pytest >= 4.0.0, < 7.0.0',
            'pytest-cov >= 2.0.0, < 3.0.0',
            'scipy >= 1.2.1, < 2.0.0',
            'tables >= 3.5.1, < 4.0.0',
            ],
        'casd': [
            'autopep8 == 1.5.5',
            'flake8 >=3.5.0, <4.1.0',
            'pycodestyle >=2.3.0, <2.9.0',
            'pytest >=3.0, <7.0.0',
            'scipy >= 1.2.1, < 2.0.0',
            ],
        'sas': [
            'pyreadstat >= 1.1.4, < 2.0.0',
            'SAS7BDAT >= 2.2.2, < 3.0.0',
            ],
        },
    include_package_data = True,  # Will read MANIFEST.in
    install_requires = [
        'chardet >=4.0, <5.0',
        'configparser',
        'humanize',
        'openfisca-core >=35.0.0, <36.0.0',
        'pandas >= 0.22',
        'pyxdg',
        'PyYAML',
        'tables >= 3.4.4, < 4.0.0',
        'tabulate',
        'weightedcalcs',
        'wquantiles >= 0.3',
        ],
    packages = find_packages(),
    zip_safe = False,
    )
