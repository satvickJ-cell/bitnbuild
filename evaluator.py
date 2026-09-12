import json
import os
from typing import Dict, Any, Union
from schema import WardBudgetData, EvaluationResult

DEFAULT_RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")

def load_rules(rules_path: str = DEFAULT_RULES_PATH) -> Dict[str, Any]:
    """Load threshold rules from rules.json."""
    if not os.path.exists(rules_path):
        return {
            "min_drain_budget_per_km": 150000,
            "historical_ward_avg": 3400000,
            "min_commercial_road_width_m": 12
        }
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)

def _to_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _to_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def evaluate_ward_data(
    data: Union[WardBudgetData, Dict[str, Any], str], 
    rules_path: str = DEFAULT_RULES_PATH
) -> Dict[str, Any]:
    """
    Evaluates extracted ward data deterministically against rules in rules.json.

    Args:
        data: WardBudgetData instance, dictionary, or JSON string containing extracted fields.
        rules_path: Path to rules.json file.

    Returns:
        dict: {"flag_triggered": bool, "plain_english_reason": str}
    """
    if isinstance(data, str):
        try:
            data_dict = json.loads(data)
        except Exception:
            data_dict = {}
    elif isinstance(data, WardBudgetData):
        data_dict = data.model_dump()
    elif isinstance(data, dict):
        data_dict = data
    else:
        data_dict = {}

    rules = load_rules(rules_path)

    ward_number = _to_int(data_dict.get("ward_number"), 0)
    budget_head = str(data_dict.get("budget_head") or "N/A")
    amount_this_year = _to_float(data_dict.get("amount_this_year"), 0.0)
    amount_last_year = _to_float(data_dict.get("amount_last_year"), 0.0)
    drain_length_km = _to_float(data_dict.get("drain_length_km"), 0.0)
    zone_new = str(data_dict.get("zone_new") or "")
    stated_road_width = _to_float(data_dict.get("stated_road_width"), 0.0)

    min_drain_budget_per_km = _to_float(rules.get("min_drain_budget_per_km"), 150000.0)
    historical_ward_avg = _to_float(rules.get("historical_ward_avg"), 3400000.0)
    min_commercial_road_width_m = _to_float(rules.get("min_commercial_road_width_m"), 12.0)

    reasons = []

    # Rule 1: Drain budget per KM calculation
    if drain_length_km > 0:
        budget_per_km = amount_this_year / drain_length_km
        if budget_per_km < min_drain_budget_per_km:
            reasons.append(
                f"Violation 1: Allocated drainage budget per km (₹{budget_per_km:,.2f}/km) "
                f"is below the statutory minimum required threshold of ₹{min_drain_budget_per_km:,.2f}/km "
                f"for Ward {ward_number} under Budget Head '{budget_head}'."
            )
    else:
        reasons.append(
            f"Violation 1: Drain length specified as {drain_length_km} km for Ward {ward_number}, "
            f"making budget per km calculation invalid."
        )

    # Rule 2: Historical Ward Average Baseline Comparison
    if amount_this_year < historical_ward_avg:
        shortfall = historical_ward_avg - amount_this_year
        pct_deficit = (shortfall / historical_ward_avg) * 100
        reasons.append(
            f"Violation 2: Current year allocation (₹{amount_this_year:,.2f}) is {pct_deficit:.1f}% "
            f"below the historical ward average baseline of ₹{historical_ward_avg:,.2f} "
            f"(Shortfall: ₹{shortfall:,.2f})."
        )

    # Rule 2b: Year-on-year allocation drop comparison
    if amount_last_year > 0 and amount_this_year < amount_last_year * 0.8:
        drop_pct = ((amount_last_year - amount_this_year) / amount_last_year) * 100
        reasons.append(
            f"Violation 2b: Year-on-year allocation for Ward {ward_number} dropped by {drop_pct:.1f}% "
            f"compared to previous year's allocation (₹{amount_last_year:,.2f})."
        )

    # Rule 3: Commercial Road Width Standard
    is_commercial = "commercial" in zone_new.lower()
    if is_commercial and stated_road_width < min_commercial_road_width_m:
        reasons.append(
            f"Violation 3: Stated road width ({stated_road_width}m) in commercial zone '{zone_new}' "
            f"fails to meet the mandatory minimum commercial road width standard of {min_commercial_road_width_m}m."
        )

    # Composite Risk Score Calculation (Civic Negligence Index)
    # Composite index based on YoY cut severity and statutory shortfall
    yoy_cut_ratio = max(0.0, (amount_last_year - amount_this_year) / amount_last_year) if amount_last_year > 0 else 0.0
    cost_per_km = (amount_this_year / drain_length_km) if drain_length_km > 0 else 0.0
    norm_deficit_ratio = max(0.0, (150000.0 - cost_per_km) / 150000.0)

    negligence_score = round(((yoy_cut_ratio * 0.6) + (norm_deficit_ratio * 0.4)) * 100, 1)

    if negligence_score >= 60.0:
        risk_level = "CRITICAL RISK"
        risk_color = "#ef4444"
    elif negligence_score >= 40.0:
        risk_level = "HIGH RISK"
        risk_color = "#f97316"
    elif negligence_score >= 20.0:
        risk_level = "MODERATE RISK"
        risk_color = "#eab308"
    else:
        risk_level = "COMPLIANT"
        risk_color = "#22c55e"

    flag_triggered = len(reasons) > 0 or negligence_score >= 20.0

    if len(reasons) > 0:
        plain_english_reason = " | ".join(reasons)
    else:
        plain_english_reason = (
            f"Ward {ward_number} drainage allocation (₹{amount_this_year:,.2f}) complies with all civic rules. "
            f"Budget per km (₹{cost_per_km:,.2f}/km) meets "
            f"the minimum threshold of ₹{min_drain_budget_per_km:,.2f}/km, meets historical ward average baseline, "
            f"and road width standards are satisfied."
        )

    cost_per_km_formatted = f"₹{int(cost_per_km):,}/km"
    statutory_norm_formatted = "₹1,50,000/km"
    yoy_cut_percentage = f"-{round(yoy_cut_ratio * 100, 1)}%" if yoy_cut_ratio > 0 else "0.0%"

    return {
        "flag_triggered": flag_triggered,
        "plain_english_reason": plain_english_reason,
        "negligence_score": negligence_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "cost_per_km": round(cost_per_km, 2),
        "cost_per_km_formatted": cost_per_km_formatted,
        "statutory_norm_formatted": statutory_norm_formatted,
        "yoy_cut_percentage": yoy_cut_percentage,
        "yoy_cut_ratio": round(yoy_cut_ratio, 4),
        "norm_deficit_ratio": round(norm_deficit_ratio, 4)
    }


if __name__ == "__main__":
    sample_data = {
        "ward_number": 42,
        "budget_head": "2217-01-101 Drainage Infrastructure",
        "amount_this_year": 1200000.0,
        "amount_last_year": 3800000.0,
        "drain_length_km": 10.0,
        "zone_new": "Commercial South",
        "stated_road_width": 9.5
    }
    result = evaluate_ward_data(sample_data)
    print("Evaluation Result:")
    print(json.dumps(result, indent=2))
