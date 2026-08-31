import importlib.util

from config import ROOT

_spec = importlib.util.spec_from_file_location("fedmod", ROOT / "data" / "fed.py")
fed = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fed)


def test_summarize_hold_and_cut():
    payload = {
        "current_target": "3.50%-3.75%",
        "meetings": [
            {
                "date": "2026-09-16",
                "probabilities": {
                    "3.25%-3.50%": 10.0,
                    "3.50%-3.75%": 80.0,
                    "3.75%-4.00%": 10.0,
                },
            }
        ],
    }
    hold, cut, flag = fed.summarize_meetings(payload)
    assert flag == "fed:implied"
    assert abs(hold - 0.80) < 1e-9
    assert abs(cut - 0.10) < 1e-9


def test_empty_is_unavailable_shape():
    hold, cut, flag = fed.summarize_meetings({"meetings": []})
    assert hold is None and cut is None
    assert flag == "fed:empty"
