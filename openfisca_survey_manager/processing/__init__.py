# Target: cleaning (tables.clean_data_frame), harmonization, weights (calibration, calmar).
from openfisca_survey_manager.processing.cleaning import clean_data_frame
from openfisca_survey_manager.processing.harmonization import harmonize_data_frame_columns


# Lazy import to avoid circular dependency (processing -> policy -> survey_collections -> core)
def __getattr__(name: str):
    if name in ("Calibration", "calmar", "check_calmar"):
        from openfisca_survey_manager.processing.weights import Calibration, calmar, check_calmar

        return {"Calibration": Calibration, "calmar": calmar, "check_calmar": check_calmar}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Calibration",
    "calmar",
    "check_calmar",
    "clean_data_frame",
    "harmonize_data_frame_columns",
]
