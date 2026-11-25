import csv

import pytest

from frame_chef.analyze import analyze_file, compare, percentile
from frame_chef.report import chart_svg, render_report

HEADER = ["Application", "ProcessID", "SwapChainAddress", "TimeInSeconds", "msBetweenPresents"]


def write_capture(path, frames):
    t = 0.0
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for ms in frames:
            writer.writerow(["test.exe", 1, "0x1", "%.6f" % t, "%.3f" % ms])
            t += ms / 1000.0


def test_percentile():
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert percentile([1, 2, 3, 4, 5], 0.99) > 4.9
    assert percentile([], 0.5) is None


def test_analyze_basic(tmp_path):
    frames = [10.0] * 200 + [50.0] * 5
    path = tmp_path / "capture.csv"
    write_capture(path, frames)
    result = analyze_file(path, "测试配置")
    assert result["label"] == "测试配置"
    assert result["frames"] == 205
    assert result["avg_fps"] < 100
    assert result["fps_1low"] < 30
    assert result["stutter_count"] >= 5
    assert len(result["series"]) <= 600


def test_compare_pareto(tmp_path):
    fast = tmp_path / "fast.csv"
    smooth = tmp_path / "smooth.csv"
    write_capture(fast, [7.0] * 300 + [20.0] * 10)
    write_capture(smooth, [9.0] * 300 + [10.0] * 2)
    result = compare([str(fast), str(smooth)], ["快", "稳"])
    labels = {item["label"] for item in result["captures"]}
    assert labels == {"快", "稳"}
    assert result["advice"]
    assert result["pareto"]


def test_missing_frame_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("Application,TimeInSeconds\ntest,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        analyze_file(path)


def test_report_contains_chart_and_metrics(tmp_path):
    path = tmp_path / "demo.csv"
    write_capture(path, [16.7] * 100 + [40.0] * 3)
    result = analyze_file(path, "demo")
    svg = chart_svg(result)
    assert "<svg" in svg and "polyline" in svg
    comparison = {"captures": [result], "pareto": [], "advice": "单次测试"}
    html_text = render_report(comparison)
    assert "帧率甜点师" in html_text
    assert "1% Low" in html_text
    assert "demo" in html_text
