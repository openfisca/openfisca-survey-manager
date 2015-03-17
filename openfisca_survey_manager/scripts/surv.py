#!/usr/bin/python
# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import os


from ConfigParser import SafeConfigParser


import click

from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey

import yaml
import pkg_resources

survey_manager_path = pkg_resources.get_distribution('openfisca-survey-manager').location


@click.group()
@click.version_option()
@click.option(
    '--config-file',
    type = click.Path(),
    default = os.path.join(
        survey_manager_path,
        'config_local.ini',
        ),
    help = "configuration file."
    )  # TODO use default_config as the rest of the package


@click.pass_context
def surv(ctx, config_file):
    ctx.obj['CONFIG_FILE'] = config_file
    """Survey manager

    This tool helps managing surveys collections
    """


@surv.command('show_config')
@click.pass_context
def show_config(ctx):
    config_file = ctx.obj['CONFIG_FILE']
    click.echo("coucou")
    with open(config_file, 'r') as file_input:
        click.echo(file_input.read())


@surv.command('list_collections')
@click.pass_context
def list_collections(ctx):
    parser = SafeConfigParser()
    parser.read(ctx.obj['CONFIG_FILE'])
    click.echo([name for name, _ in parser.items('collections')])


@surv.command()
@click.pass_context
@click.argument("collection_name", type = click.STRING)
@click.argument("survey_name", type = click.STRING, required = False)
@click.argument("tables_names", type = click.STRING, nargs = -1, required = False)
def show(ctx, collection_name, survey_name = None, tables_names = None):
    parser = SafeConfigParser()
    parser.read(ctx.obj['CONFIG_FILE'])
    json_file_path = os.path.abspath(parser.get("collections", collection_name))
    survey_collection = SurveyCollection.load(json_file_path = json_file_path)
    click.echo(survey_collection)
    if survey_name is not None:
        survey = [
            kept_survey for kept_survey in survey_collection.surveys if kept_survey.name == survey_name
            ][0]
        if survey is not None:
            click.echo(survey)
        else:
            click.echo("{} is not an element of collection {} surveys ({})".format(
                survey_name, collection_name, str(survey_collection.surveys.keys()).strip('[]')))

        if tables_names:
            for table_name in tables_names:
                click.echo(yaml.safe_dump(
                    {"table {}".format(table_name): survey.tables[table_name]},
                    default_flow_style = False,
                    ))


@surv.command()
@click.pass_context
@click.argument('directory_path', type = click.Path(exists = True))
@click.argument('collection_name', type = click.STRING, required = False)
@click.argument('survey_name', type = click.STRING, required = False)
def create_from(ctx, directory_path, collection_name = None, survey_name = None):

    parser = SafeConfigParser()
    parser.read(ctx.obj['CONFIG_FILE'])

    collection_names = [option for option in parser._sections['collections'].keys()]
    collection_names.remove('__name__')
    collections_directory = parser.get('collections', 'collections_directory')
    collection_names.remove('collections_directory')

    data_file_by_format = create_data_file_by_format(directory_path)
    sas_files = data_file_by_format['sas']
    stata_files = data_file_by_format['stata']

    click.confirm(u"Create a new survey using this information ?", abort = False, default = True)

    if collection_name not in collection_names:
        if collection_name is None:
            click.confirm(u"Create a new collection ?", abort = False, default = True)
            collection_name = click.prompt("Name of the new collection")
            collection_json_path = os.path.join(collections_directory, collection_name + ".json")
        click.confirm(u"Create a collection {} ?".format(collection_name), abort = False, default = True)
        if os.path.isfile(collection_json_path):
            click.confirm(
                u"Erase existing {} collection file ?".format(collection_json_path), abort = False, default = True)
            os.remove(collection_json_path)
        survey_collection = create_collection(collection_name)

    else:
        click.echo(u"The new survey is being add to the existing collection {} ".format(collection_name))
        collection_json_path = os.path.join(collections_directory, collection_name + ".json")
        survey_collection = SurveyCollection.load(collection_json_path)

    if survey_name is not None:
        click.echo(u"The survey {} is being add to the existing collection {} ".format(survey_name, collection_name))

    if not survey_name:
        survey_name = click.prompt('Enter a name for the survey in collection {}'.format(survey_collection.name))

    add_survey_to_collection(
        survey_name = survey_name,
        survey_collection = survey_collection,
        sas_files = sas_files,
        stata_files = stata_files,
        )
    survey_collection.dump(
        json_file_path = collection_json_path,
        )

    for format_extension, data_files in data_file_by_format.iteritems():
        if data_files != []:
            to_print = yaml.safe_dump(data_files, default_flow_style = False)
            click.echo("Here are the {} files: \n {}".format(format_extension, to_print))
            if click.confirm('Do you want to fill the {} HDF5 file using the {} files ?'.format(
                    survey_name, format_extension, default = False)):
                survey_collection.fill_hdf(source_format = format_extension)
        else:
            click.echo("There are no {} files".format(format_extension))

    survey_collection.dump()

    config_file = open(ctx.obj['CONFIG_FILE'], 'w')
    parser.write(config_file)
    config_file.close()


def create_collection(collection_name):
    # Create the new collection
    name = collection_name
    label = click.prompt('Enter a description for collection {}'.format(name), default = name)
    survey_collection = SurveyCollection(name = name, label = label)
    return survey_collection


def create_data_file_by_format(directory_path = None):
    '''
    Browse subdirectories to extract stata and sas files
    '''
    stata_files = []
    sas_files = []

    for root, subdirs, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if os.path.basename(file_name).endswith(".dta"):
                click.echo("Found stata file {}".format(file_path))
                stata_files.append(file_path)
            if os.path.basename(file_name).endswith(".sas7bdat"):
                click.echo("Found sas file {}".format(file_path))
                sas_files.append(file_path)
    return {'stata': stata_files, 'sas': sas_files}


def add_survey_to_collection(survey_name = None, survey_collection = None, sas_files = [], stata_files = [],
        question = False):
    assert survey_collection is not None
    overwrite = True

    if question:
        label = click.prompt('Enter a description for the survey {}'.format(survey_name), default = survey_name)
    else:
        label = survey_name

    for test_survey in survey_collection.surveys:
        if test_survey.name == survey_name:
            if question:
                click.echo('The following information is available for survey {}'.format(survey_name))
            survey = survey_collection.get_survey(survey_name)
            if question:
                click.echo(survey)
                overwrite = click.confirm(
                    'Overwrite previous survey {} informations ?'.format(survey_name), default = True)
            else:
                overwrite = True
    if question:
        same_survey = click.confirm('Are all the files part of the same survey ?', default = True)
    else:
        same_survey = True
    if same_survey:
            if overwrite:
                survey = Survey(
                    name = survey_name,
                    label = label,
                    sas_files = sas_files,
                    stata_files = stata_files,
                    survey_collection = survey_collection,
                    )
            else:
                survey = survey_collection.get(survey_name)
                survey.label = label
                survey.informations.update({
                    "sas_files": sas_files,
                    "stata_files": stata_files,
                    })
            survey_collection.surveys = [
                kept_survey for kept_survey in survey_collection.surveys if kept_survey.name != survey_name
                ]
            survey_collection.surveys.append(survey)


if __name__ == '__main__':
    surv(obj={})
