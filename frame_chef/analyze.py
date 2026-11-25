# -*- coding: utf-8 -*-
"""PresentMon CSV 分析：把帧时间翻译成 1% Low、卡顿和配置取舍。"""

import csv
import math
from pathlib import Path

TIME_FIELDS = ("TimeInSeconds", "timeinseconds", "Time", "time")
FRAME_FIELDS = ("msBetweenPresents", "msBetweenDisplayChange", "msUntilNextFrame", "FrameTime", "frametime")


def _find_field(fields, names):
    lower = {str(key).strip().lower(): key for key in fields}
    for name in names:
        key = lower.get(name.lower())
        if key is not None:
            return key
    return None


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def load_frames(path):
    path = Path(path)
    rows = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return rows
        frame_key = _find_field(reader.fieldnames, FRAME_FIELDS)
        time_key = _find_field(reader.fieldnames, TIME_FIELDS)
        if frame_key is None:
            raise ValueError("找不到帧时间列（msBetweenPresents / msBetweenDisplayChange）")
        elapsed = 0.0
        for row in reader:
            ms = _num(row.get(frame_key))
            if ms is None or ms <= 0 or ms > 1000:
                continue
            if time_key:
                stamp = _num(row.get(time_key))
            else:
                stamp = None
            if stamp is None:
                elapsed += ms / 1000.0
                stamp = elapsed
            rows.append((stamp, ms))
    return rows


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    return values[lower] * (upper - position) + values[upper] * (position - lower)


def _series(rows, width=600):
    if len(rows) <= width:
        return [{"t": round(t, 3), "ms": round(ms, 2)} for t, ms in rows]
    bucket = len(rows) / width
    out = []
    for index in range(width):
        start = int(index * bucket)
        end = max(start + 1, int((index + 1) * bucket))
        chunk = rows[start:end]
        if not chunk:
            continue
        peak = max(chunk, key=lambda item: item[1])
        out.append({"t": round(peak[0], 3), "ms": round(peak[1], 2)})
    return out


def _fps_bins(rows, seconds=1.0):
    bins = {}
    for stamp, ms in rows:
        bucket = int(stamp // seconds)
        bins.setdefault(bucket, []).append(ms)
    return [{"t": bucket, "fps": round(1000.0 / (sum(values) / len(values)), 1)}
            for bucket, values in sorted(bins.items())]


def analyze_file(path, label=None):
    rows = load_frames(path)
    if not rows:
        return {"label": label or Path(path).stem, "file": str(path), "frames": 0,
                "error": "没有有效帧数据", "series": [], "bins": []}
    frames = [ms for _, ms in rows]
    duration = max(rows[-1][0] - rows[0][0], 0.001)
    mean = sum(frames) / len(frames)
    median = percentile(frames, 0.5)
    p95 = percentile(frames, 0.95)
    p99 = percentile(frames, 0.99)
    p999 = percentile(frames, 0.999)
    stutter_threshold = max(median * 2.0, 25.0)
    stutters = sum(1 for value in frames if value > stutter_threshold)
    result = {
        "label": label or Path(path).stem,
        "file": str(path),
        "frames": len(frames),
        "duration_s": round(duration, 1),
        "avg_fps": round(1000.0 / mean, 1),
        "fps_1low": round(1000.0 / p99, 1),
        "fps_01low": round(1000.0 / p999, 1),
        "median_frame_ms": round(median, 2),
        "p95_frame_ms": round(p95, 2),
        "p99_frame_ms": round(p99, 2),
        "stutter_count": stutters,
        "stutter_pct": round(stutters / len(frames) * 100, 2),
        "series": _series(rows),
        "bins": _fps_bins(rows),
    }
    return result


def dominates(a, b):
    """a 是否在平均帧率和 1% Low 上都不差，且至少一项更好。"""
    if a.get("error") or b.get("error"):
        return False
    avg_diff = a["avg_fps"] - b["avg_fps"]
    low_diff = a["fps_1low"] - b["fps_1low"]
    return avg_diff >= -0.1 and low_diff >= -0.1 and (avg_diff > 0.1 or low_diff > 0.1)


def compare(paths, labels=None):
    labels = labels or []
    results = [analyze_file(path, labels[index] if index < len(labels) else None)
               for index, path in enumerate(paths)]
    valid = [item for item in results if not item.get("error")]
    frontier = [item for item in valid if not any(dominates(other, item) for other in valid if other is not item)]
    best_avg = max(valid, key=lambda item: item["avg_fps"]) if valid else None
    best_low = max(valid, key=lambda item: item["fps_1low"]) if valid else None
    return {
        "captures": results,
        "pareto": [item["label"] for item in frontier],
        "best_avg": best_avg["label"] if best_avg else None,
        "best_low": best_low["label"] if best_low else None,
        "advice": _advice(frontier, best_avg, best_low),
    }


def _advice(frontier, best_avg, best_low):
    if not best_avg:
        return "没有可用数据。"
    if len(frontier) == 1:
        return "「%s」在平均帧率和 1%% Low 上同时占优，直接用它。" % frontier[0]["label"]
    if best_avg and best_low and best_avg["label"] == best_low["label"]:
        return "「%s」平均帧率和 1%% Low 都最好，是当前数据里的综合最优。" % best_avg["label"]
    return ("帧率优先选「%s」（平均 %.1f FPS）；稳定优先选「%s」（1%% Low %.1f FPS）。"
            " 两个都在帕累托前沿上，没有白给的选项。" % (
                best_avg["label"], best_avg["avg_fps"], best_low["label"], best_low["fps_1low"]))
