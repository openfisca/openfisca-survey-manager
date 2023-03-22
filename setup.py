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
    version = '0.47.2',
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
            'autopep8',
            'coveralls',
            'flake8',
            'flake8-bugbear',
            'flake8-docstrings',
            'flake8-print',
            'flake8-rst-docstrings',
            'openfisca-country-template',
            'pytest',
            'pytest-cov',
            'scipy',
            'tables',
            ],
        'casd': [
            'autopep8',
            'flake8',
            'pycodestyle',
            'pytest',
            'scipy',
            ],
        'sas': [
            'pyreadstat',
            'SAS7BDAT',
            ],
        },
    include_package_data = True,  # Will read MANIFEST.in
    install_requires = [
        'chardet',
        'configparser',
        'humanize',
        # 'openfisca-core >=35.0.0, <36.0.0',
        'OpenFisca-Core @ git+https://github.com/openfisca/openfisca-core.git@version_leap',
        'pandas',
        'pyxdg',
        'PyYAML',
        'tables',
        'tabulate',
        'weightedcalcs',
        'wquantiles',
        ],
    packages = find_packages(),
    zip_safe = False,
    )
