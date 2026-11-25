"""生成三份演示用 PresentMon CSV（合成数据，不是真实游戏采集）。

用来展示 1% Low、卡顿和配置取舍；真实使用时用 tools/capture.ps1。
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "demo-captures"
CONFIGS = [
    ("1080p-competitive", 8.4, 1.1, 0.012, 18.0),
    ("1440p-balanced", 10.8, 0.9, 0.004, 19.0),
    ("4k-cinematic", 14.0, 1.4, 0.020, 28.0),
]


def make(path, base, jitter, spike_pct, spike_ms, duration=45.0):
    random.seed(hash(path.name) & 0xFFFF)
    rows = []
    t = 0.0
    while t < duration:
        ms = base + random.uniform(-jitter, jitter)
        if random.random() < spike_pct:
            ms = spike_ms + random.uniform(-2.0, 3.0)
        rows.append((t, ms))
        t += ms / 1000.0
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Application", "ProcessID", "SwapChainAddress", "TimeInSeconds", "msBetweenPresents"])
        for stamp, ms in rows:
            writer.writerow(["demo.exe", 4242, "0xDEADBEEF", "%.6f" % stamp, "%.3f" % ms])
    print("%s: %d frames / %.1f s" % (path.name, len(rows), duration))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, base, jitter, pct, spike in CONFIGS:
        make(OUT / (name + ".csv"), base, jitter, pct, spike)


if __name__ == "__main__":
    main()
