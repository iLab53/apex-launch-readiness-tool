"""
APEX -- Launch Readiness Scorecard Validator
Implements Rules A1-D5 from scorecard_validation_design.md
Pure functions: input dict -> ValidationResult dict. No API calls.
"""

# The 8 canonical dimension names every scorecard must contain.
# If any name is different, the scorecard fails Rule D2.
CANONICAL_DIMENSIONS = [
    "market_access",
    "medical_affairs",
    "marketing_brand",
    "commercial_operations",
    "regulatory_compliance",
    "patient_support",
    "competitive_positioning",
    "supply_distribution",
]

# Top-level fields every scorecard must have (Rule A1)
TOP_LEVEL_REQUIRED = ["asset_id", "overall_score", "overall_tier", "dimensions"]

# Fields every dimension object must have (Rule A3)
DIM_REQUIRED = ["dimension", "score", "rationale", "gap_closing_action"]


def derive_tier(score):
    """Convert a 0-100 score to its readiness tier string."""
    if score >= 80.0:
        return "LAUNCH-READY"
    elif score >= 60.0:
        return "ON-TRACK"
    elif score >= 40.0:
        return "AT-RISK"
    else:
        return "NOT-READY"


def normalise_score(raw, field_path, corrections):
    """
    Convert a 0-5 score to 0-100 (Rule B2).
    Raises ValueError for scores outside 0-100 after conversion.
    """
    if raw < 0:
        raise ValueError(
            f"VALIDATION_ERROR [B1]: {field_path} value {raw} is below minimum 0."
        )
    if raw > 100:
        raise ValueError(
            f"VALIDATION_ERROR [B1]: {field_path} value {raw} exceeds maximum 100."
        )
    # Scores 0-5 are treated as the 0-5 scale and converted
    if raw <= 5.0:
        converted = round((raw / 5.0) * 100, 1)
        corrections.append({
            "code": "B2",
            "severity": "CORRECTION",
            "field": field_path,
            "message": f"Score {raw} (0-5 scale) converted to {converted} (0-100 scale).",
            "original_value": raw,
            "corrected_value": converted,
        })
        return converted
    return raw  # already on 0-100 scale


def validate_scorecard(scorecard):
    """
    Validate a Launch Readiness Scorecard dict.
    Returns:
        {"status": "VALID"|"CORRECTED"|"ERROR",
         "scorecard": <corrected dict>,
         "errors": [list of error/correction dicts]}
    """
    errors = []
    sc = dict(scorecard)  # work on a copy, never modify the original

    # ── RULE SET A: PRESENCE CHECKS ────────────────────────────────
    # Rule A1: top-level required fields must exist
    for field in TOP_LEVEL_REQUIRED:
        if field not in sc:
            return {
                "status": "ERROR",
                "scorecard": sc,
                "errors": [{"code": "A1", "severity": "HARD_ERROR",
                             "field": field,
                             "message": f"VALIDATION_ERROR [A1]: {field} is missing."}]
            }

    # Rule A2: dimensions must be a list of exactly 8 items
    dims = sc.get("dimensions", [])
    if not isinstance(dims, list) or len(dims) != 8:
        return {
            "status": "ERROR",
            "scorecard": sc,
            "errors": [{"code": "A2", "severity": "HARD_ERROR",
                         "field": "dimensions",
                         "message": f"VALIDATION_ERROR [A2]: dimensions has {len(dims)} items; need 8."}]
        }

    # Rule A3: each dimension must have all 4 required sub-fields
    for i, dim in enumerate(dims):
        for sub in DIM_REQUIRED:
            if sub not in dim:
                return {
                    "status": "ERROR",
                    "scorecard": sc,
                    "errors": [{"code": "A3", "severity": "HARD_ERROR",
                                 "field": f"dimensions[{i}].{sub}",
                                 "message": f"VALIDATION_ERROR [A3]: dim at index {i} missing '{sub}'"}]
                }

    # ── RULE SET B: SCORE NORMALISATION ────────────────────────────
    # Normalise overall_score first, then each dimension score
    sc["overall_score"] = normalise_score(sc["overall_score"], "overall_score", errors)
    for dim in sc["dimensions"]:
        name = dim["dimension"]
        dim["score"] = normalise_score(
            dim["score"], f"dimensions.{name}.score", errors
        )

    # ── RULE SET C: TIER CONSISTENCY ────────────────────────────────
    # Score is authoritative. Derive the correct tier and compare.
    derived = derive_tier(sc["overall_score"])
    if sc["overall_tier"] != derived:
        errors.append({
            "code": "C2",
            "severity": "CORRECTION",
            "field": "overall_tier",
            "message": (
                f"CORRECTION [C2]: overall_tier was '{sc['overall_tier']}'; "
                f"corrected to '{derived}' (score={sc['overall_score']})."
            ),
            "original_value": sc["overall_tier"],
            "corrected_value": derived,
        })
        sc["overall_tier"] = derived

    # ── RULE SET D: DIMENSION INTEGRITY ────────────────────────────
    seen_names = set()
    for i, dim in enumerate(sc["dimensions"]):
        name = dim["dimension"]

        # Rule D1: no duplicate dimension names
        if name in seen_names:
            return {
                "status": "ERROR", "scorecard": sc,
                "errors": [{"code": "D1", "severity": "HARD_ERROR",
                             "field": f"dimensions[{i}].dimension",
                             "message": f"VALIDATION_ERROR [D1]: Duplicate dimension '{name}'"}]
            }
        seen_names.add(name)

        # Rule D2: dimension name must be in the canonical list
        if name not in CANONICAL_DIMENSIONS:
            return {
                "status": "ERROR", "scorecard": sc,
                "errors": [{"code": "D2", "severity": "HARD_ERROR",
                             "field": f"dimensions[{i}].dimension",
                             "message": f"VALIDATION_ERROR [D2]: Unknown dimension '{name}'"}]
            }

        # Rule D4: rationale must be at least 20 characters
        if len(dim.get("rationale", "")) < 20:
            return {
                "status": "ERROR", "scorecard": sc,
                "errors": [{"code": "D4", "severity": "HARD_ERROR",
                             "field": f"dimensions.{name}.rationale",
                             "message": f"VALIDATION_ERROR [D4]: rationale too short in '{name}'"}]
            }

        # Rule D5: gap_closing_action must be at least 15 characters
        if len(dim.get("gap_closing_action", "")) < 15:
            return {
                "status": "ERROR", "scorecard": sc,
                "errors": [{"code": "D5", "severity": "HARD_ERROR",
                             "field": f"dimensions.{name}.gap_closing_action",
                             "message": f"VALIDATION_ERROR [D5]: gap_closing_action too short in '{name}'"}]
            }

    # ── FINAL STATUS ────────────────────────────────────────────────
    status = "CORRECTED" if errors else "VALID"
    return {"status": status, "scorecard": sc, "errors": errors}
