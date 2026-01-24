# Read package version in pyproject.toml and replace it in .conda/meta.yaml

import argparse
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")


def get_versions():
    """
    Read package version and deps in pyproject.toml
    """
    openfisca_survey_manager = None
    pyproject_toml_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_toml_path.open("r") as file:
        content = file.read()
    # Extract the version of openfisca_survey_manager
    version_match = re.search(r'^version\s*=\s*"([\d.]*)"', content, re.MULTILINE)
    if version_match:
        openfisca_survey_manager = version_match.group(1)
    else:
        raise Exception("Package version not found in pyproject.toml")

    return {
        "openfisca_survey_manager": openfisca_survey_manager,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--replace", action="store_true", help="replace in file")
    parser.add_argument(
        "-f", "--filename", type=str, default=".conda/meta.yaml", help="Path to meta.yaml, with filename"
    )
    parser.add_argument(
        "-o", "--only_package_version", action="store_true", help="Only display current package version"
    )
    args = parser.parse_args()
    info = get_versions()

    if args.only_package_version:
        print(f"{info['openfisca_survey_manager']}")  # noqa: T201
        exit()

    logging.info("Versions :")
    print(info)  # noqa: T201

    if args.replace:
        file_path = Path(args.filename)
        if file_path.exists():
            with file_path.open("r") as f:
                content = f.read()

            # Replace version line
            new_content = re.sub(
                r"\{% set version = .* %\}", f'{{% set version = "{info["openfisca_survey_manager"]}" %}}', content
            )

            # Also comment out/remove setup.py dependency if it exists
            new_content = new_content.replace(
                "{% set data = load_setup_py_data() %}", "# {% set data = load_setup_py_data() %}"
            )

            if new_content != content:
                with file_path.open("w") as f:
                    f.write(new_content)
                logging.info(f"Updated {args.filename}")
