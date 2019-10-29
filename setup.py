#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""A tool for managing survey data

Useful to deal with survey data imported in OpenFisca
"""


from setuptools import setup, find_packages


classifiers = """\
Development Status :: 2 - Pre-Alpha
License :: OSI Approved :: GNU Affero General Public License v3
Operating System :: POSIX
Programming Language :: Python
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Topic :: Scientific/Engineering :: Information Analysis
"""

doc_lines = __doc__.split('\n')


setup(
    name = 'OpenFisca-Survey-Manager',
    version = '0.37.3',
    author = 'OpenFisca Team',
    author_email = 'contact@openfisca.fr',
    classifiers = [classifier for classifier in classifiers.split('\n') if classifier],
    description = doc_lines[0],
    keywords = 'survey data',
    license = 'http://www.fsf.org/licensing/licenses/agpl-3.0.html',
    long_description = '\n'.join(doc_lines[2:]),
    url = 'https://github.com/openfisca/openfisca-survey-manager',
    data_files = [
        ('share/openfisca/openfisca-survey-manager', ['CHANGELOG.md', 'LICENSE.AGPL.txt', 'README.md']),
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
            'coveralls >=1.5.0,<1.9.0',
            'flake8 >= 3.7.0, < 3.8.0',
            'openfisca-country-template >= 3.6.0, < 4.0.0',
            'pytest >= 4.0.0, < 6.0.0',
            'pytest-cov >= 2.0.0, < 3.0.0',
            'SAS7BDAT >= 2.2.2, < 3.0.0',
            'scipy >= 1.2.1, < 2.0.0',
            'tables >= 3.4.4, < 4.0.0',
            ],
        'casd': [
            'autopep8 == 1.4.3',
            'flake8 >=3.5.0, <3.8.0',
            'pycodestyle >=2.3.0, <2.6.0',
            'pytest >=3.0, <6.0.0',
            'scipy >= 1.2.1, < 2.0.0',
            'tables >= 3.4.4, < 4.0.0',
            ],
        },
    include_package_data = True,  # Will read MANIFEST.in
    install_requires = [
        'configparser',
        'future',
        'humanize',
        'numpy >= 1.11, < 1.16',  # to work with tables
        'tables >= 3.4.4, < 4.0.0',
        'openfisca-core >=34.2.2,<35.0.0',
        'pandas >= 0.22',
        'pyxdg',
        'PyYAML',
        'weightedcalcs',
        'wquantiles >= 0.3',
        ],
    packages = find_packages(),
    zip_safe = False,
    )
