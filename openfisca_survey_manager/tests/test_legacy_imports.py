import importlib


def test_legacy_policy_modules_are_importable():
    matching = importlib.import_module("openfisca_survey_manager.matching")
    coicop = importlib.import_module("openfisca_survey_manager.coicop")
    variables = importlib.import_module("openfisca_survey_manager.variables")
    statshelpers = importlib.import_module("openfisca_survey_manager.statshelpers")

    assert hasattr(matching, "nnd_hotdeck")
    assert hasattr(coicop, "build_coicop_level_nomenclature")
    assert hasattr(variables, "create_quantile")
    assert hasattr(statshelpers, "gini")


def test_processing_weights_legacy_modules_are_importable():
    calmar_module = importlib.import_module("openfisca_survey_manager.processing.weights.calmar")
    calibration_module = importlib.import_module("openfisca_survey_manager.processing.weights.calibration")

    assert hasattr(calmar_module, "calmar")
    assert hasattr(calmar_module, "check_calmar")
    assert hasattr(calibration_module, "Calibration")
