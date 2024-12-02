import collections
from datetime import datetime
import logging
import os

import numpy as np
import pandas as pd


log = logging.getLogger(__name__)


# TODO:
#  * Localisation

class AbstractAggregates(object):
    aggregate_variables = None
    amount_unit = 1e6
    currency = None
    base_data_frame = None
    baseline_simulation = None
    beneficiaries_unit = 1e3
    filter_by = None
    labels = None
    simulation = None
    survey_scenario = None
    totals_df = None

    def __init__(self, survey_scenario = None):
        assert survey_scenario is not None

        self.period = survey_scenario.period
        self.survey_scenario = survey_scenario
        assert len(survey_scenario.simulations) >= 1

        self.simulations = survey_scenario.simulations

        for name in survey_scenario.tax_benefit_systems.keys():
            assert survey_scenario.simulations[name] is not None

        self.weight_variable_by_entity = survey_scenario.weight_variable_by_entity
        if self.labels is None:
            amount_unit_str = "({} {})".format(self.amount_unit, self.currency)
            beneficiaries_unit_str = "({})".format(self.beneficiaries_unit)
            self.labels = collections.OrderedDict((
                ('label', "Mesure"),
                ('entity', "Entité"),
                ('reform_amount', "Dépenses\n" + amount_unit_str),
                ('reform_beneficiaries', "Bénéficiaires\n(milliers)"),
                ('baseline_amount', "Dépenses initiales\n" + amount_unit_str),
                ('baseline_beneficiaries', "Bénéficiaires\ninitiaux\n" + beneficiaries_unit_str),
                ('actual_amount', "Dépenses\nréelles\n" + amount_unit_str),
                ('actual_beneficiaries', "Bénéficiaires\nréels\n" + beneficiaries_unit_str),
                ('amount_absolute_difference', "Diff. absolue\nDépenses\n" + amount_unit_str),
                ('beneficiaries_absolute_difference', "Diff absolue\nBénéficiaires\n" + beneficiaries_unit_str),
                ('amount_relative_difference', "Diff. relative\nDépenses"),
                ('beneficiaries_relative_difference', "Diff. relative\nBénéficiaires"),
                ))

    def compute_aggregates(self, use_baseline: bool = True, reform: bool = True, actual: bool = True) -> pd.DataFrame:
        """
        Compute aggregate amounts.

        Args:
            use_baseline (bool, optional): _description_. Defaults to True.
            reform (bool, optional): _description_. Defaults to True.
            actual (bool, optional): _description_. Defaults to True.

        Returns:
            pd.DataFrame: The aggregates
        """
        filter_by = self.filter_by
        if actual:
            self.totals_df = self.load_actual_data(period = self.period)

        simulation_types = list()
        if use_baseline:
            assert self.simulations['baseline'] is not None
            simulation_types.append('baseline')
        if reform:
            simulation_types.append('reform')
        if actual:
            simulation_types.append('actual')

        data_frame_by_simulation_type = dict()

        for simulation_type in simulation_types:
            if simulation_type == 'actual':
                data_frame_by_simulation_type['actual'] = self.totals_df.copy() if self.totals_df is not None else None
            else:
                use_baseline = False if simulation_type == 'reform' else True
                data_frame = pd.DataFrame()
                assert self.aggregate_variables is not None
                for variable in self.aggregate_variables:
                    variable_data_frame = self.compute_variable_aggregates(
                        variable, use_baseline = use_baseline, filter_by = filter_by)
                    data_frame = pd.concat((data_frame, variable_data_frame))

                data_frame.rename(columns = {
                    'amount': '{}_amount'.format(simulation_type),
                    'beneficiaries': '{}_beneficiaries'.format(simulation_type),
                    },
                    inplace = True
                    )
                data_frame_by_simulation_type[simulation_type] = data_frame

        if use_baseline and reform:
            del data_frame_by_simulation_type['reform']['entity']
            del data_frame_by_simulation_type['reform']['label']

        self.base_data_frame = pd.concat(
            list(data_frame_by_simulation_type.values()),
            axis = 1,
            sort = True,
            ).loc[self.aggregate_variables]
        return self.base_data_frame

    def compute_difference(self, target: str = "baseline", default: str = 'actual', amount: bool = True,
            beneficiaries: bool = True, absolute: bool = True, relative: bool = True) -> pd.DataFrame:
        """
        Compute and add relative and/or absolute differences to the data_frame.

        Args:
            target (str, optional): Target simulation. Defaults to "baseline".
            default (str, optional): Default simulation. Defaults to 'actual'.
            amount (bool, optional): Provide amounts. Defaults to True.
            beneficiaries (bool, optional): Provide beneficiaries. Defaults to True.
            absolute (bool, optional): Return absolute values. Defaults to True.
            relative (bool, optional): Return relative values. Defaults to True.

        Returns:
            pd.DataFrame: The differences
        """
        assert relative or absolute
        assert amount or beneficiaries
        base_data_frame = self.base_data_frame if self.base_data_frame is not None else self.compute_aggregates()

        difference_data_frame = base_data_frame[['label', 'entity']].copy()
        # Remove duplicates
        difference_data_frame = difference_data_frame.loc[:, ~difference_data_frame.columns.duplicated()].copy()

        quantities = list()
        quantities += ['amount'] if amount else None
        quantities += ['beneficiaries'] if beneficiaries else None

        try:
            for quantity in quantities:
                difference_data_frame['{}_absolute_difference'.format(quantity)] = (
                    abs(base_data_frame['{}_{}'.format(target, quantity)]) - base_data_frame['{}_{}'.format(default, quantity)]
                    )
                difference_data_frame['{}_relative_difference'.format(quantity)] = (
                    abs(base_data_frame['{}_{}'.format(target, quantity)]) - base_data_frame['{}_{}'.format(default, quantity)]
                    ) / abs(base_data_frame['{}_{}'.format(default, quantity)])
        except KeyError as e:
            log.debug(e)
            log.debug("Do not computing differences")
            return None

        return difference_data_frame

    def compute_variable_aggregates(self, variable: str, use_baseline: bool = False, filter_by: str = None) -> pd.DataFrame:
        """
        Return aggregate spending, and number of beneficiaries for the relevant entity level.

        Args:
            variable (str): Name of the variable aggregated according to its entity
            use_baseline (bool, optional): Use the baseline or the reform or the only avalilable simulation when no reform (default). Defaults to False.
            filter_by (str, optional): The variable to filter by. Defaults to None.

        Returns:
            pd.DataFrame: The amount and beneficiaries for the variable
        """
        if len(self.simulations) == 1:
            simulation = list(self.simulations.values())[0]
        elif use_baseline:
            simulation = self.simulations['baseline']
        else:
            simulation = self.simulations['reform']

        variables = simulation.tax_benefit_system.variables
        column = variables.get(variable)

        if column is None:
            msg = "Variable {} is not available".format(variable)
            if use_baseline:
                msg += " in baseline simulation"
            log.info(msg)
            return pd.DataFrame(
                data = {
                    'label': variable,
                    'entity': 'Unknown entity',
                    'amount': 0,
                    'beneficiaries': 0,
                    },
                index = [variable],
                )
        weight = self.weight_variable_by_entity[column.entity.key]
        assert weight in variables, f"{weight} not a variable of the tax_benefit_system"

        weight_array = simulation.calculate(weight, period = self.period).astype('float')
        assert not np.isnan(np.sum(weight_array)), f"The are some NaN in weights {weight} for entity {column.entity.key}"
        # amounts and beneficiaries from current data and default data if exists
        # Build weights for each entity
        variable_array = simulation.calculate_add(variable, period = self.period).astype('float')
        assert np.isfinite(variable_array).all(), f"The are non finite values in variable {variable} for entity {column.entity.key}"
        data = pd.DataFrame({
            variable: variable_array,
            weight: weight_array,
            })
        if filter_by:
            filter_dummy_variable = (
                filter_by
                if filter_by in variables
                else self.survey_scenario.filtering_variable_by_entity[column.entity.key]
                )
            filter_dummy_array = simulation.calculate(filter_dummy_variable, period = self.period)

        else:
            filter_dummy_array = 1

        assert np.isfinite(filter_dummy_array).all(), "The are non finite values in variable {} for entity {}".format(
            filter_dummy_variable, column.entity.key)

        amount = int(
            (
                data[variable]
                * data[weight]
                * filter_dummy_array
                / self.amount_unit
                ).sum()
            )
        beneficiaries = int(
            (
                (data[variable] != 0)
                * data[weight]
                * filter_dummy_array
                / self.beneficiaries_unit
                ).sum()
            )
        variable_data_frame = pd.DataFrame(
            data = {
                'label': variables[variable].label,
                'entity': variables[variable].entity.key,
                'amount': amount,
                'beneficiaries': beneficiaries,
                },
            index = [variable],
            )

        return variable_data_frame

    def create_description(self):
        """Create a description dataframe."""
        now = datetime.now()
        return pd.DataFrame([
            'OpenFisca',
            'Calculé le %s à %s' % (now.strftime('%d-%m-%Y'), now.strftime('%H:%M')),
            'Système socio-fiscal au %s' % self.simulation.period.start.year,
            "Données d'enquêtes de l'année %s" % str(self.data_year),
            ])

    def to_csv(self, path = None, absolute = True, amount = True, beneficiaries = True, default = 'actual',
            relative = True, target = "reform"):
        """Saves the table to csv."""
        assert path is not None

        if os.path.isdir(path):
            now = datetime.now()
            file_path = os.path.join(path, 'Aggregates_%s.%s' % (now.strftime('%d-%m-%Y'), ".csv"))
        else:
            file_path = path

        df = self.get_data_frame(
            absolute = absolute,
            amount = amount,
            beneficiaries = beneficiaries,
            default = default,
            relative = relative,
            target = target,
            )
        df.to_csv(file_path, index = False, header = True)

    def to_excel(self, path = None, absolute = True, amount = True, beneficiaries = True, default = 'actual',
            relative = True, target = "reform"):
        """Save the table to excel."""
        assert path is not None

        if os.path.isdir(path):
            now = datetime.now()
            file_path = os.path.join(path, 'Aggregates_%s.%s' % (now.strftime('%d-%m-%Y'), ".xlsx"))
        else:
            file_path = path

        df = self.get_data_frame(
            absolute = absolute,
            amount = amount,
            beneficiaries = beneficiaries,
            default = default,
            relative = relative,
            target = target,
            )
        writer = pd.ExcelWriter(file_path)
        df.to_excel(writer, "aggregates", index = False, header = True)
        descr = self.create_description()
        descr.to_excel(writer, "description", index = False, header = False)
        writer.save()

    def to_html(self, path = None, absolute = True, amount = True, beneficiaries = True, default = 'actual',
            relative = True, target = "reform"):
        """Get or saves the table to html format."""
        df = self.get_data_frame(
            absolute = absolute,
            amount = amount,
            beneficiaries = beneficiaries,
            default = default,
            relative = relative,
            target = target,
            )

        if path is not None and os.path.isdir(path):
            now = datetime.now()
            file_path = os.path.join(path, 'Aggregates_%s.%s' % (now.strftime('%d-%m-%Y'), ".html"))
        else:
            file_path = path

        if file_path is not None:
            with open(file_path, "w") as html_file:
                df.to_html(html_file)
        return df.to_html()

    def to_markdown(self, path = None, absolute = True, amount = True, beneficiaries = True, default = 'actual',
            relative = True, target = "reform"):
        """Get or saves the table to markdown format."""
        df = self.get_data_frame(
            absolute = absolute,
            amount = amount,
            beneficiaries = beneficiaries,
            default = default,
            relative = relative,
            target = target,
            )

        if path is not None and os.path.isdir(path):
            now = datetime.now()
            file_path = os.path.join(path, 'Aggregates_%s.%s' % (now.strftime('%d-%m-%Y'), ".md"))
        else:
            file_path = path

        if file_path is not None:
            with open(file_path, "w") as markdown_file:
                df.to_markdown(markdown_file)

        return df.to_markdown()

    def get_calibration_coeffcient(self, target: str = "reform") -> pd.DataFrame:
        df = self.compute_aggregates(
            actual = True,
            use_baseline = 'baseline' == target,
            reform = 'reform' == target,
            )
        return df['{}_amount'.format(target)] / df['actual_amount']

    def get_data_frame(
            self,
            absolute: bool = True,
            amount: bool = True,
            beneficiaries: bool = True,
            default: str = 'actual',
            formatting: bool = True,
            relative: bool = True,
            target: str = "reform",
            ):
        assert target is None or target in ['reform', 'baseline']

        columns = self.labels.keys()
        if (absolute or relative) and (target != default):
            difference_data_frame = self.compute_difference(
                absolute = absolute,
                amount = amount,
                beneficiaries = beneficiaries,
                default = default,
                relative = relative,
                target = target,
                )
        else:
            difference_data_frame = None

        # Removing unwanted columns
        if amount is False:
            columns = [column for column in columns if 'amount' not in columns]

        if beneficiaries is False:
            columns = [column for column in columns if 'beneficiaries' not in column]

        if absolute is False:
            columns = [column for column in columns if 'absolute' not in column]

        if relative is False:
            columns = [column for column in columns if 'relative' not in column]

        for simulation_type in ['reform', 'baseline', 'actual']:
            if simulation_type not in [target, default]:
                columns = [column for column in columns if simulation_type not in column]

        aggregates_data_frame = self.compute_aggregates(
            actual = 'actual' in [target, default],
            use_baseline = 'baseline' in [target, default],
            reform = 'reform' in [target, default],
            )
        ordered_columns = [
            'label',
            'entity',
            'reform_amount',
            'baseline_amount',
            'actual_amount',
            'amount_absolute_difference',
            'amount_relative_difference',
            'reform_beneficiaries',
            'baseline_beneficiaries',
            'actual_beneficiaries',
            'beneficiaries_absolute_difference',
            'beneficiaries_relative_difference'
            ]
        if difference_data_frame is not None:
            # Remove eventual duplication
            difference_data_frame = difference_data_frame.loc[:, ~difference_data_frame.columns.duplicated()].copy()
            aggregates_data_frame = aggregates_data_frame.loc[:, ~aggregates_data_frame.columns.duplicated()].copy()
            df = aggregates_data_frame.merge(difference_data_frame, how = 'left')[columns]
        else:
            columns = [column for column in columns if column in aggregates_data_frame.columns]
            df = aggregates_data_frame[columns]

        df = df.reindex(columns = ordered_columns).dropna(axis = 1, how = 'all').rename(columns = self.labels)

        if formatting:
            relative_columns = [column for column in df.columns if 'relative' in column]
            df[relative_columns] = df[relative_columns].applymap(
                lambda x: "{:.2%}".format(x) if str(x) != 'nan' else 'nan'
                )
            for column in df.columns:
                if issubclass(np.dtype(df[column]).type, np.number):
                    df[column] = (
                        df[column]
                        .apply(lambda x: "{:d}".format(int(round(x))) if str(x) != 'nan' else 'nan')
                        )
        return df

    def load_actual_data(self, period = None):
        NotImplementedError
