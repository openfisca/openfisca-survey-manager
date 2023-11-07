import configparser
import os


from openfisca_survey_manager import default_config_files_directory as config_files_directory


def create_raw_data_ini(value_by_option_by_section = None):
    """Creates raw_data.ini configureation file

    Args:
      value_by_option_by_section(dict(dict)): Options value by section (Default value = None)

    """
    config_parser = configparser.ConfigParser()

    if value_by_option_by_section is not None:
        for section, value_by_option in value_by_option_by_section.items():
            config_parser.add_section(section)
            for option, value in value_by_option.items():
                config_parser.set(section, option, value)

    with open(os.path.join(config_files_directory, 'raw_data.ini'), 'w') as raw_data_config_file:
        config_parser.write(raw_data_config_file)
