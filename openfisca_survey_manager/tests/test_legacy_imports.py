import importlib


def test_policy_modules_are_importable():
    matching = importlib.import_module("openfisca_survey_manager.policy.matching")
    coicop = importlib.import_module("openfisca_survey_manager.policy.coicop")
    variables = importlib.import_module("openfisca_survey_manager.policy.variables")
    statshelpers = importlib.import_module("openfisca_survey_manager.policy.statshelpers")

    assert hasattr(matching, "nnd_hotdeck")
    assert hasattr(coicop, "build_coicop_level_nomenclature")
    assert hasattr(variables, "create_quantile")
    assert hasattr(statshelpers, "gini")


def test_policy_weight_modules_are_importable():
    calmar_module = importlib.import_module("openfisca_survey_manager.policy.calmar")
    calibration_module = importlib.import_module("openfisca_survey_manager.policy.calibration")

    assert hasattr(calmar_module, "calmar")
    assert hasattr(calmar_module, "check_calmar")
    assert hasattr(calibration_module, "Calibration")
