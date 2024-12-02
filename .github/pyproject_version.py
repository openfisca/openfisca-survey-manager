# Read package version in pyproject.toml and replace it in .conda/recipe.yaml

import argparse
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(message)s')
PACKAGE_VERSION = 'X.X.X'
CORE_VERSION = '>=43,<44'
NUMPY_VERSION = '>=1.24.3,<2'


def get_versions():
    '''
    Read package version and deps in pyproject.toml
    '''
    # openfisca_core_api = None
    openfisca_survey_manager = None
    # numpy = None
    with open('./pyproject.toml', 'r') as file:
        content = file.read()
    # Extract the version of openfisca_survey_manager
    version_match = re.search(r'^version\s*=\s*"([\d.]*)"', content, re.MULTILINE)
    if version_match:
        openfisca_survey_manager = version_match.group(1)
    else:
        raise Exception('Package version not found in pyproject.toml')
    # Extract dependencies
    # version = re.search(r'openfisca-core\s*(>=\s*[\d\.]*,\s*<\d*)"', content, re.MULTILINE)
    # if version:
    #     openfisca_core_api = version.group(1)
    # version = re.search(r'numpy\s*(>=\s*[\d\.]*,\s*<\d*)"', content, re.MULTILINE)
    # if version:
    #     numpy = version.group(1)
    # if not openfisca_core_api or not numpy:
    #     raise Exception('Dependencies not found in pyproject.toml')
    return {
        'openfisca_survey_manager': openfisca_survey_manager,
        # 'openfisca_core_api': openfisca_core_api.replace(' ', ''),
        # 'numpy': numpy.replace(' ', ''),
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--replace', type=bool, default=False, required=False, help='replace in file')
    parser.add_argument('-f', '--filename', type=str, default='.conda/recipe.yaml', help='Path to recipe.yaml, with filename')
    parser.add_argument('-o', '--only_package_version', type=bool, default=False, help='Only display current package version')
    args = parser.parse_args()
    info = get_versions()
    file = args.filename
    if args.only_package_version:
        print(f'{info["openfisca_survey_manager"]}')  # noqa: T201
        exit()
    logging.info('Versions :')
    print(info)  # noqa: T201
