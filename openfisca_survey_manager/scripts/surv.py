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


from openfisca_survey_manager.surveys import Survey, SurveyCollection


@click.group()
@click.version_option()
@click.option('--config-file',
              type = click.Path(),
              default = os.path.abspath(
                  "/home/benjello/openfisca/openfisca-survey-manager/config_local.ini"
                  ),
              help = "configuration file.")  # TODO show default
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
@click.argument("collection", type = click.STRING)
@click.argument("survey", type = click.STRING, required = False)
@click.argument("tables", type = click.STRING, nargs = -1, required = False)
def show(ctx, collection, survey = None, tables = None):
    parser = SafeConfigParser()
    parser.read(ctx.obj['CONFIG_FILE'])
    file_path = os.path.abspath(parser.get("collections", collection))
    survey_collection = SurveyCollection.load(file_path = file_path)
    click.echo(survey_collection)
    if survey is not None:
        survey = survey_collection.surveys.get(survey)
        if survey is not None:
            click.echo(survey)
        else:
            click.echo("{} is not an element of collection {} surveys ({})".format(
                survey, collection, str(survey_collection.surveys.keys()).strip('[]')))

        if tables:
            for table in tables:
                import yaml
                click.echo(yaml.safe_dump(
                    {"table {}".format(table): survey.tables[table]},
                    default_flow_style = False,
                    ))


@surv.command()
@click.pass_context
@click.argument('directory_path', type = click.Path(exists = True))
@click.argument('collection', type = click.STRING, required = False)
@click.argument('survey', type = click.STRING, required = False)
def create_from(ctx, directory_path, collection = None, survey = None,):

    parser = SafeConfigParser()
    parser.read(ctx.obj['CONFIG_FILE'])

    collections = [option for option in parser._sections['collections'].keys()]
    collections.remove('__name__')
    collections_directory = parser.get('collections', 'collections_directory')
    collections.remove('collections_directory')

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

    click.confirm(u"Create a new survey using this information ?", abort = False)
    collection_json_path = os.path.join(collections_directory, collection + ".json") if collection else None

    if collection not in collections:
        if collection is None:
            click.confirm(u"Create a new collection ?", abort = False)
            collection = click.prompt("Name of the new collection")
            collection_json_path = os.path.join(collections_directory, collection + ".json")
        click.confirm(u"Create a the new collection {} ?".format(collection), abort = False)

        if os.path.isfile(collection_json_path):
            click.confirm(u"Erase existing {} collection file ?".format(collection_json_path), abort = False)
            os.remove(collection_json_path)
        survey_collection = create_collection(collection)

    else:
        survey_collection = SurveyCollection.load(collection_json_path)

    if not survey:
        survey = click.prompt('Enter a name for the survey in collection {}'.format(survey_collection.name))

    print survey
    add_survey_to_collection(
        survey_name = survey,
        survey_collection = survey_collection,
        sas_files = sas_files,
        stata_files = stata_files,
        )

    print survey_collection.surveys[survey].informations
    print collection_json_path

    survey_collection.dump(
        file_path = collection_json_path,
        )

    parser.set("collections", collection, collection_json_path)

    cfgfile = open(ctx.obj['CONFIG_FILE'], 'w')
    parser.write(cfgfile)
    cfgfile.close()


def create_collection(collection_name):
    # Create the new collection
    name = collection_name
    label = click.prompt('Enter a description for collection {}'.format(name), default = name)
    survey_collection = SurveyCollection(name = name, label = label)
    return survey_collection


def add_survey_to_collection(survey_name = None, survey_collection = None, sas_files = [], stata_files = []):
    assert survey_collection is not None
    overwrite = True
    label = click.prompt('Enter a description for the survey {}'.format(survey_name), default = survey_name)

    if survey_name in survey_collection.surveys.keys():
        click.echo('The following information is available for survey {}'.format(survey_name))
        click.echo(survey_collection.surveys[survey_name])
        overwrite = click.prompt('Overwrite previous survey {} informations ?'.format(survey_name), default = False)

    if click.confirm('Are all the files part of the same survey ?', default = True):
        if overwrite:
            survey = Survey(
                name = survey_name,
                label = label,
                sas_files = sas_files,
                stata_files = stata_files,
                )
        else:
            survey = survey_collection.surveys[survey_name]
            survey.label = label
            survey.informations.update({
                "sas_files": sas_files,
                "stata_files": stata_files,
                })

        survey_collection.surveys.update({survey_name: survey})


if __name__ == '__main__':
    surv(obj={})
