from copy import deepcopy


REQUIRED_TOP_LEVEL_FIELDS = ("asset_id", "overall_score", "overall_tier", "dimensions")
REQUIRED_DIMENSION_FIELDS = ("dimension", "score", "rationale", "gap_closing_action")
CANONICAL_DIMENSIONS = (
    "market_access",
    "medical_affairs",
    "marketing_brand",
    "commercial_operations",
    "regulatory_compliance",
    "patient_support",
    "competitive_positioning",
    "supply_distribution",
)
VALID_TIERS = ("LAUNCH-READY", "ON-TRACK", "AT-RISK", "NOT-READY")


def _require_dict(value, message: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(message)
    return value


def _require_number(value, message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    return float(value)


def _derive_tier(score: float) -> str:
    if score >= 80.0:
        return "LAUNCH-READY"
    if score >= 60.0:
        return "ON-TRACK"
    if score >= 40.0:
        return "AT-RISK"
    return "NOT-READY"


def _normalize_score(raw_value, field_name: str, treat_five_as_hundred: bool = False) -> float:
    score = _require_number(raw_value, f"VALIDATION_ERROR [B1]: {field_name} must be numeric.")
    if score < 0:
        raise ValueError(f"VALIDATION_ERROR [B1]: {field_name} {score} is below minimum of 0.")
    if score > 100:
        raise ValueError(f"VALIDATION_ERROR [B1]: {field_name} {score} exceeds maximum of 100.")
    if score == 5 and treat_five_as_hundred:
        return 5.0
    if score <= 5:
        return round((score / 5.0) * 100.0, 1)
    return round(score, 1)


def validate_output(data: dict) -> dict:
    scorecard = _require_dict(data, "VALIDATION_ERROR: scorecard must be a dictionary.")
    scorecard = deepcopy(scorecard)

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in scorecard:
            raise ValueError(f"VALIDATION_ERROR [A1]: {field} is missing.")

    dimensions = scorecard["dimensions"]
    if not isinstance(dimensions, list):
        raise ValueError("VALIDATION_ERROR [A1]: dimensions must be an array.")
    if len(dimensions) != 8:
        found_names = [item.get("dimension") for item in dimensions if isinstance(item, dict)]
        missing = sorted(set(CANONICAL_DIMENSIONS) - set(name for name in found_names if isinstance(name, str)))
        raise ValueError(
            f"VALIDATION_ERROR [A2]: dimensions array has {len(dimensions)} items; "
            f"expected exactly 8. Received dimension names: {found_names}. Missing: {missing}"
        )

    seen_names = {}
    for index, dimension in enumerate(dimensions):
        dimension = _require_dict(
            dimension,
            f"VALIDATION_ERROR [A3]: dimension object at index {index} must be a dictionary.",
        )
        dimensions[index] = dimension

        for field in REQUIRED_DIMENSION_FIELDS:
            if field not in dimension:
                if field == "dimension":
                    raise ValueError(
                        f"VALIDATION_ERROR [A3]: dimension object at index {index} is missing 'dimension' name."
                    )
                raise ValueError(
                    f"VALIDATION_ERROR [A3]: dimension '{dimension.get('dimension', index)}' is missing '{field}'."
                )

        name = dimension["dimension"]
        if not isinstance(name, str):
            raise ValueError(f"VALIDATION_ERROR [D2]: Unrecognised dimension name '{name}' at index {index}.")
        if name in seen_names:
            raise ValueError(
                f"VALIDATION_ERROR [D1]: Duplicate dimension '{name}' found at indices {seen_names[name]} and {index}."
            )
        if name not in CANONICAL_DIMENSIONS:
            raise ValueError(
                f"VALIDATION_ERROR [D2]: Unrecognised dimension name '{name}' at index {index}."
            )
        seen_names[name] = index

        rationale = dimension["rationale"]
        if not isinstance(rationale, str) or len(rationale.strip()) < 20:
            length = len(rationale.strip()) if isinstance(rationale, str) else 0
            raise ValueError(
                f"VALIDATION_ERROR [D4]: dimension '{name}' rationale is too short ({length} chars)."
            )

        action = dimension["gap_closing_action"]
        if not isinstance(action, str) or len(action.strip()) < 15:
            length = len(action.strip()) if isinstance(action, str) else 0
            raise ValueError(
                f"VALIDATION_ERROR [D5]: dimension '{name}' gap_closing_action is too short ({length} chars)."
            )

    dimension_raw_scores = []
    any_dimension_above_five = False
    for dimension in dimensions:
        raw_score = _require_number(
            dimension["score"],
            f"VALIDATION_ERROR [B1]: dimension '{dimension['dimension']}' score must be numeric.",
        )
        if raw_score < 0:
            raise ValueError(
                f"VALIDATION_ERROR [B1]: dimension '{dimension['dimension']}' score {raw_score} is below minimum of 0."
            )
        if raw_score > 100:
            raise ValueError(
                f"VALIDATION_ERROR [B1]: dimension '{dimension['dimension']}' score {raw_score} exceeds maximum of 100."
            )
        if raw_score > 5:
            any_dimension_above_five = True
        dimension_raw_scores.append(raw_score)

    for index, dimension in enumerate(dimensions):
        normalized = _normalize_score(
            dimension_raw_scores[index],
            f"dimension '{dimension['dimension']}' score",
        )
        if normalized < 0 or normalized > 100:
            raise ValueError(
                f"VALIDATION_ERROR [D3]: dimension '{dimension['dimension']}' score {normalized} is out of range [0, 100] after normalisation."
            )
        dimension["score"] = normalized

    scorecard["overall_score"] = _normalize_score(
        scorecard["overall_score"],
        "overall_score",
        treat_five_as_hundred=any_dimension_above_five,
    )
    scorecard["overall_tier"] = _derive_tier(scorecard["overall_score"])

    return scorecard

