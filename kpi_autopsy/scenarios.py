from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    title: str
    metric_id: str
    query_file: str
    expected_issue: str | None



SCENARIOS = {
    "wrong-stage": Scenario("Accepted at the wrong stage", "accepted_offer_rate",
                            "wrong_stage.sql", "EVENT_DEFINITION_MISMATCH"),
    "offer-join": Scenario("Offer join changes application grain", "accepted_offer_rate",
                           "offer_join.sql", "GRAIN_MISMATCH"),
    "offer-cohort": Scenario("Offer-date cohort replaces intake cohort", "accepted_offer_rate",
                             "offer_date_cohort.sql", "COHORT_MISMATCH"),
    "outcome-filter": Scenario("Accepted-only turnaround population", "first_offer_hours",
                               "accepted_only_delay.sql", "OUTCOME_FILTER"),
    "clean-rate": Scenario("Clean accepted-offer report", "accepted_offer_rate",
                           "accepted_offer_rate.sql", None),
    "clean-delay": Scenario("Clean first-offer report", "first_offer_hours",
                            "first_offer_hours.sql", None),
    "clean-backlog": Scenario("Clean backlog report", "open_backlog", "open_backlog.sql", None),
}
