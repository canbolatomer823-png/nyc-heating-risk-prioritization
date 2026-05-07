PROBLEM_FRAME = "nyc_heating_and_hot_water_complaint_risk"

PRIMARY_TARGET = "next_day_complaint_count"
SECONDARY_TARGET = "next_day_positive_flag"

ENTITY_KEY = "building_id"
TIME_GRAIN = "building-day"

PRIMARY_MODEL = "negative_binomial_glm"
SECONDARY_MODEL = "gee_logistic"
BENCHMARK_MODEL = "logistic_regression"

EQUITY_LAYER = "tract_level_cre_vulnerability"
