# -*- coding: utf-8 -*-
"""命令行入口：分析单次 capture，或比较多个配置。"""

import argparse
import json
import webbrowser
from pathlib import Path

from .analyze import analyze_file, compare
from .report import render_report


def summary(comparison):
    print("%-22s %10s %10s %10s %10s" % ("配置", "平均 FPS", "1% Low", "0.1% Low", "卡顿%"))
    for item in comparison["captures"]:
        if item.get("error"):
            print("%-22s %s" % (item["label"], item["error"]))
            continue
        print("%-22s %10.1f %10.1f %10.1f %10.2f" % (
            item["label"], item["avg_fps"], item["fps_1low"], item["fps_01low"], item["stutter_pct"]))
    print("\n建议：%s" % comparison["advice"])
    if comparison.get("pareto"):
        print("帕累托前沿：%s" % ", ".join(comparison["pareto"]))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="frame-chef", description="帧率甜点师 · PresentMon 帧时间分析")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("analyze", help="分析一次 capture")
    one.add_argument("capture", help="PresentMon CSV")
    one.add_argument("--label", default=None, help="配置名，默认用文件名")
    one.add_argument("--out", default="frame-report.html")
    one.add_argument("--json", action="store_true")
    one.add_argument("--open", action="store_true")
    many = sub.add_parser("compare", help="比较多个配置")
    many.add_argument("captures", nargs="+", help="多个 PresentMon CSV")
    many.add_argument("--labels", default="", help="逗号分隔的配置名；默认用文件名")
    many.add_argument("--out", default="frame-compare.html")
    many.add_argument("--json", action="store_true")
    many.add_argument("--open", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "analyze":
        comparison = {"captures": [analyze_file(args.capture, args.label)],
                      "pareto": [], "best_avg": None, "best_low": None,
                      "advice": ""}
        comparison["advice"] = "单次采集：先看 1% Low 和卡顿，再和下一个配置比。"
        out = args.out
        open_after = args.open
        want_json = args.json
    else:
        labels = [part.strip() for part in args.labels.split(",") if part.strip()]
        comparison = compare(args.captures, labels)
        out = args.out
        open_after = args.open
        want_json = args.json

    report = render_report(comparison)
    Path(out).write_text(report, encoding="utf-8")
    summary(comparison)
    print("\n报告：%s" % Path(out).resolve())
    if want_json:
        brief = [{key: item.get(key) for key in ("label", "frames", "avg_fps", "fps_1low",
                                                 "fps_01low", "stutter_pct", "error")}
                 for item in comparison["captures"]]
        print(json.dumps({"captures": brief, "pareto": comparison["pareto"],
                          "advice": comparison["advice"]}, ensure_ascii=False, indent=2))
    if open_after:
        webbrowser.open(Path(out).resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
