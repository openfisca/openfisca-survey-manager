"""Compatibility module for CALMAR under processing.weights."""

from importlib import import_module

_policy_calmar = import_module("openfisca_survey_manager.policy.calmar")

__all__ = [name for name in dir(_policy_calmar) if not name.startswith("_")]
globals().update({name: getattr(_policy_calmar, name) for name in __all__})
