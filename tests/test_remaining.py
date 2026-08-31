import importlib.util

from config import ROOT, load_settings


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_net_r_is_less_than_gross():
    costs = _load("backtest/costs.py", "costsmod")
    assert costs.round_trip_cost_r(1.0) < 1.0
    assert costs.round_trip_cost_r(-1.0) < -1.0


def test_risk_blocks_too_many_positions():
    risk = _load("execution/risk_manager.py", "riskmod").RiskManager(max_positions=1, max_symbol_notional=100)
    assert risk.allow("ETH/USDT:USDT", 10)
    risk.on_fill("ETH/USDT:USDT", 10)
    assert risk.allow("ETH/USDT:USDT", 10) is False


def test_execution_stays_locked_in_settings():
    exe = load_settings()["execution"]
    assert exe["enabled"] is False
    assert exe["paper_only"] is True
    assert load_settings()["intraday"]["enabled"] is False
    assert load_settings()["learning"]["walk_forward_folds"] >= 6


def test_weights_still_one():
    w = load_settings()["confluence"]["weights"]
    assert abs(sum(w.values()) - 1.0) < 1e-6
