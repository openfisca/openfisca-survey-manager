"""Compatibility module for Calibration under processing.weights."""

from importlib import import_module

_policy_calibration = import_module("openfisca_survey_manager.policy.calibration")

__all__ = [name for name in dir(_policy_calibration) if not name.startswith("_")]
globals().update({name: getattr(_policy_calibration, name) for name in __all__})
