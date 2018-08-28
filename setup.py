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
Topic :: Scientific/Engineering :: Information Analysis
"""

doc_lines = __doc__.split('\n')


setup(
    name = 'OpenFisca-Survey-Manager',
    version = '0.11.1',
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
        'calmar': [
            'scipy',
            ],
        'matching': [
            'feather',
            'rpy2',
            ],
        'test': [
            'openfisca-country-template',
            'SAS7BDAT',
            ],
        },
    include_package_data = True,  # Will read MANIFEST.in
    install_requires = [
        'configparser',
        'humanize',
        'numpy >= 1.12',
        'openfisca-core >= 23.1.2, < 24.0.0',
        'pandas >= 0.20',
        'PyYAML',
        'pyxdg',
        'tables',
        'wquantiles >= 0.3',
        ],
    message_extractors = {
        'openfisca_survey_manager': [
            ('**.py', 'python', None),
            ],
        },
    packages = find_packages(),
    zip_safe = False,
    )
