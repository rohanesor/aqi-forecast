import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_export_web_bundle(tmp_path):
    if not list((ROOT / "artifacts").glob("*/manifest.json")):
        pytest.skip("no trained artifacts")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_web.py"), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["cities"] and len(index["categories"]) == 6
    for c in index["cities"]:
        b = json.loads((tmp_path / f"{c['slug']}.json").read_text(encoding="utf-8"))
        assert [f["horizon"] for f in b["forecasts"]] == [1, 2, 3]
        for f in b["forecasts"]:
            assert 0 <= f["aqi"] <= 500
            if f["range_low"] is not None:
                assert f["range_low"] <= f["aqi"] <= f["range_high"]
        assert "NaN" not in (tmp_path / f"{c['slug']}.json").read_text(encoding="utf-8")
        assert b["is_demo"] == (c["is_demo"])
