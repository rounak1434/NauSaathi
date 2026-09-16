"""
Automated Backend & Recommendation Scenario Verification Test Suite
===================================================================
Tests:
1. Representative BOOK NOW scenario (Prompt 7-day fixture or rising forward rate)
2. Representative WAIT scenario (Multi-month horizon with >=3.5% trough)
3. Infeasible vessel / port scenario (Extreme cargo or restrictive river port)
4. Data integrity and transparent fields audit (No fabricated R², proper signal labels)
"""

import sys
from pathlib import Path

# Add App to path
app_dir = Path(__file__).resolve().parent / "App"
sys.path.insert(0, str(app_dir))

from recommendation_engine import get_sail_recommendation, find_destination_profile, VESSEL_REGISTRY


def test_book_now_scenario():
    print("Testing BOOK NOW scenario (Prompt 7-day chartering window)...")
    res = get_sail_recommendation(
        cargo_type="coal",
        cargo_tonnes=80_000.0,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        chartering_window="Within 7 Days",
        contract_duration_months=1,
    )
    assert res["recommendation"]["action"] == "BOOK NOW", f"Expected BOOK NOW, got {res['recommendation']['action']}"
    assert res["chartering_window"]["decision_action"] == "BOOK NOW"
    assert res["chartering_window"]["strategy_score"] == 100
    assert res["chartering_window"]["risk"] == "LOW"
    assert res["recommended_vessel"] == "Panamax"
    assert res["port_feasibility"] == "PASS"
    assert "model_validation" in res
    assert res["model_validation"]["metrics"]["R_squared"] is None
    print("  -> PASS: BOOK NOW scenario correctly verified.")


def test_wait_scenario():
    print("Testing WAIT scenario (6-month horizon with forward trough >= 3.5%)...")
    res = get_sail_recommendation(
        cargo_type="coal",
        cargo_tonnes=80_000.0,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        chartering_window="6 Months",
        contract_duration_months=6,
    )
    assert res["recommendation"]["action"] == "WAIT / DEFER", f"Expected WAIT / DEFER, got {res['recommendation']['action']}"
    assert res["chartering_window"]["decision_action"] == "WAIT"
    assert res["chartering_window"]["strategy_score"] >= 75
    assert res["chartering_window"]["risk"] == "MODERATE"
    assert res["recommended_vessel"] == "Panamax"
    print("  -> PASS: WAIT scenario correctly verified.")


def test_infeasible_scenario():
    print("Testing INFEASIBLE scenario (250,000 MT single parcel exceeds max Capesize)...")
    res = get_sail_recommendation(
        cargo_type="coal",
        cargo_tonnes=250_000.0,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        chartering_window="1 Month",
        contract_duration_months=1,
    )
    assert "NO FEASIBLE" in res["recommendation"]["action"], f"Expected NO FEASIBLE, got {res['recommendation']['action']}"
    assert res["chartering_window"]["decision_action"] == "INFEASIBLE"
    assert res["chartering_window"]["strategy_score"] == 0
    assert res["chartering_window"]["risk"] == "HIGH"
    print("  -> PASS: INFEASIBLE scenario correctly verified.")


def test_transparency_metrics():
    print("Testing transparency & absence of fake validation claims...")
    res = get_sail_recommendation(
        cargo_type="coal",
        cargo_tonnes=80_000.0,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        chartering_window="1 Month",
    )
    mv = res["model_validation"]
    metrics = mv["metrics"]
    assert metrics["R_squared"] is None, "R_squared must be None"
    assert metrics["MAE"] is None, "MAE must be None"
    assert metrics["RMSE"] is None, "RMSE must be None"
    assert metrics["MAPE"] is None, "MAPE must be None"
    assert mv["live_inference"] is False, "live_inference must be False"
    assert "forecast_signal" in res["forecast"]
    signal = res["forecast"]["forecast_signal"]
    assert signal["signal"] in ["Strong", "Moderate", "Weak"]
    assert "coverage_ratio" in signal
    print("  -> PASS: Transparency audit passed with zero fake metrics.")


if __name__ == "__main__":
    print("Running NauSaarthi Backend Automated Verification Suite...\n")
    test_book_now_scenario()
    test_wait_scenario()
    test_infeasible_scenario()
    test_transparency_metrics()
    print("\nALL BACKEND AUTOMATED TESTS PASSED SUCCESSFULLY.")
