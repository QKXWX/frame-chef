# -*- coding: utf-8 -*-
"""把帧时间画成 SVG，并生成一份可存档的对比报告。"""

import html


def chart_svg(result, width=1000, height=260):
    series = result.get("series") or []
    if not series:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d'></svg>" % (width, height)
    pad_l, pad_r, pad_t, pad_b = 54, 18, 18, 32
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    t_max = max(item["t"] for item in series) or 1.0
    t_min = min(item["t"] for item in series)
    span = max(t_max - t_min, 0.001)
    y_max = max(max(item["ms"] for item in series), result.get("p99_frame_ms") or 0) * 1.15
    y_max = max(y_max, 1.0)

    def x(t):
        return pad_l + (t - t_min) / span * plot_w

    def y(ms):
        return pad_t + (1 - ms / y_max) * plot_h

    points = " ".join("%0.1f,%0.1f" % (x(item["t"]), y(item["ms"])) for item in series)
    parts = [
        "<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>" % (width, height, width, height),
        "<rect width='100%' height='100%' fill='#070b12'/>",
        "<rect x='%d' y='%d' width='%d' height='%d' fill='#0b111e'/>" % (pad_l, pad_t, plot_w, plot_h),
    ]
    for i in range(1, 5):
        gy = pad_t + plot_h * i / 5
        parts.append("<line x1='%d' y1='%0.1f' x2='%d' y2='%0.1f' stroke='#1c2b47'/>" % (pad_l, gy, width - pad_r, gy))
    p99 = result.get("p99_frame_ms")
    if p99:
        parts.append("<line x1='%d' y1='%0.1f' x2='%d' y2='%0.1f' stroke='#ffb84d' stroke-dasharray='5 4' stroke-opacity='.8'/>" % (
            pad_l, y(p99), width - pad_r, y(p99)))
        parts.append("<text x='%d' y='%0.1f' fill='#ffb84d' font-size='10' font-family='monospace'>P99 %0.1f ms</text>" % (
            width - pad_r - 92, y(p99) - 6, p99))
    parts.append("<polyline points='%s' fill='none' stroke='#35d6c4' stroke-width='1.6' stroke-linejoin='round'/>" % points)
    parts.append("<text x='%d' y='%d' fill='#7d8fae' font-size='10' font-family='monospace'>0 s</text>" % (pad_l, height - 10))
    parts.append("<text x='%d' y='%d' fill='#7d8fae' font-size='10' font-family='monospace'>%0.1f s</text>" % (
        width - pad_r - 42, height - 10, t_max))
    parts.append("<text x='%d' y='%d' fill='#7d8fae' font-size='10' font-family='monospace'>frame time</text>" % (10, pad_t + 12))
    parts.append("</svg>")
    return "\n".join(parts)


def _metric(label, value, unit=""):
    return "<div class='metric'><small>%s</small><b>%s%s</b></div>" % (html.escape(label), value, unit)


def render_report(comparison):
    captures = comparison.get("captures", [])
    valid = [item for item in captures if not item.get("error")]
    cards = []
    for item in captures:
        if item.get("error"):
            cards.append("<section class='panel'><h2>%s</h2><p class='err'>%s</p></section>" % (
                html.escape(item["label"]), html.escape(item["error"])))
            continue
        metrics = "".join([
            _metric("平均帧率", "%.1f" % item["avg_fps"], " FPS"),
            _metric("1% Low", "%.1f" % item["fps_1low"], " FPS"),
            _metric("0.1% Low", "%.1f" % item["fps_01low"], " FPS"),
            _metric("卡顿帧", "%.2f" % item["stutter_pct"], "%"),
        ])
        cards.append("""
        <section class="panel capture">
          <div class="cap-head"><h2>%s</h2><span>%d 帧 / %.1f 秒</span></div>
          <div class="metrics">%s</div>
          <div class="chart">%s</div>
          <p class="note">中位帧时间 %.2f ms · P95 %.2f ms · P99 %.2f ms · 卡顿 %d 帧</p>
        </section>""" % (html.escape(item["label"]), item["frames"], item["duration_s"], metrics,
                         chart_svg(item), item["median_frame_ms"], item["p95_frame_ms"],
                         item["p99_frame_ms"], item["stutter_count"]))

    table = ""
    if len(valid) > 1:
        rows = "".join("""
          <tr><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.1f</td><td>%.1f%%</td><td>%s</td></tr>""" % (
            html.escape(item["label"]), item["avg_fps"], item["fps_1low"], item["fps_01low"],
            item["stutter_pct"], "前沿" if item["label"] in comparison.get("pareto", []) else "被支配")
            for item in valid)
        table = """<section class="panel"><h2>配置对比</h2>
        <table><thead><tr><th>配置</th><th>平均 FPS</th><th>1%% Low</th><th>0.1%% Low</th><th>卡顿</th><th>帕累托</th></tr></thead>
        <tbody>%s</tbody></table></section>""" % rows

    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>帧率甜点师 · 对比报告</title>
<style>
:root{--bg:#070b12;--panel:#0c1524;--line:#1c2b47;--text:#dbe7ff;--muted:#7d8fae;--cyan:#35d6c4;--amber:#ffb84d;--red:#ff5d6c;--green:#8ee36b}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1100px 600px at 70%% -10%%,#10263f,#070b12 60%%);color:var(--text);font-family:"Segoe UI","Noto Sans SC",sans-serif}
.wrap{width:min(1180px,calc(100%% - 36px));margin:34px auto 70px}.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:18px}
.brand b{font-size:24px;letter-spacing:.08em}.brand small{display:block;color:var(--muted);font:11px monospace;letter-spacing:.18em;margin-top:5px}
.advice{border:1px solid #315b57;background:linear-gradient(90deg,#0a2421,#0b1220);border-left:4px solid var(--cyan);border-radius:10px;padding:16px 18px;margin:22px 0;color:#c9f3ea;line-height:1.7;font-size:13px}
.panel{background:linear-gradient(180deg,#111d33,#0b1220);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:18px}
.cap-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px}.cap-head h2{font-size:18px;margin:0}.cap-head span{color:var(--muted);font:11px monospace}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:15px 0}.metric{border:1px solid var(--line);border-radius:9px;padding:11px}.metric small{display:block;color:var(--muted);font-size:10px;letter-spacing:.06em}.metric b{display:block;font:21px monospace;color:var(--cyan);margin-top:6px}
.chart{border:1px solid var(--line);border-radius:9px;overflow:hidden;background:#070b12}.chart svg{display:block;width:100%%;height:auto}
.note{color:var(--muted);font-size:11px;line-height:1.7;margin:10px 0 0}.err{color:var(--red);font-size:12px}
table{width:100%%;border-collapse:collapse;margin-top:12px;font-size:12px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}td:first-child{color:var(--text)}
.foot{color:var(--muted);font:11px monospace;margin-top:22px}.muted{color:var(--muted)}
@media(max-width:800px){.metrics{grid-template-columns:1fr 1fr}.top{flex-direction:column;align-items:flex-start;gap:10px}}
</style></head><body><div class="wrap">
<header class="top"><div class="brand"><b>帧率甜点师</b><small>FRAME CHEF / FRAME TIME LAB</small></div><span class="muted">PresentMon CSV · 本地分析</span></header>
<div class="advice">%s</div>
%s
%s
<p class="foot">数据来源：PresentMon CSV。只分析，不自动改游戏设置；改设置前请确认反作弊规则。</p>
</div></body></html>""" % (html.escape(comparison.get("advice", "")), "".join(cards), table)
