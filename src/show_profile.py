"""Show one profile: its levels, and a chart.

    python src/show_profile.py 2026-11-06        (single day)
    python src/show_profile.py 2026-11-06 5      (5 sessions ending that day)
    python src/show_profile.py 2026-11-06 20
"""
import subprocess
import sys
from datetime import date

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
import vp

if len(sys.argv) < 2:
    sys.exit("Give a date, e.g.  python src/show_profile.py 2026-11-06 5")
day = date.fromisoformat(sys.argv[1])
window = int(sys.argv[2]) if len(sys.argv) > 2 else 1
if window not in config.WINDOWS:
    sys.exit(f"Window must be one of {config.WINDOWS}")

con = duckdb.connect(str(config.DB_PATH), read_only=True)
dates, profiles, gaps, contracts = vp.load_daily(con)
con.close()
if day not in profiles:
    sys.exit(f"No session on {day}. Weekend or holiday?")
i = dates.index(day)
if i < window - 1:
    sys.exit("Not enough earlier sessions for that window.")

window_dates = dates[i - window + 1:i + 1]
prices, vol = vp.composite(window_dates, profiles, gaps)
poc, val, vah = vp.value_area(vol)
nodes, ledges, smooth = vp.find_nodes(prices, vol, window)

title = f"NQ {window}-day profile, {window_dates[0]:%d %b} to {day:%d %b %Y}" \
    if window > 1 else f"NQ daily profile, {day:%a %d %b %Y}"
print(f"\n{title}")
if len({contracts[d] for d in window_dates}) > 1:
    print("  (spans a contract roll: older sessions shifted by the roll gap)")
print(f"  VAH   {prices[vah]:.2f}\n  POC   {prices[poc]:.2f}\n  VAL   {prices[val]:.2f}")
for kind, price, strength in nodes:
    print(f"  {kind:<5} {price:.2f}   {strength:>4.0%}")
print("  Ledges (wide ones are not graded):")
for g in ledges:
    print(f"    {g.low:.2f} to {g.high:.2f}   {g.width:>5.2f} pts   {g.side:<6} of node, "
          f"falls {g.fall:.0%}, node holds {g.node:.0%}{'   WIDE' if g.wide else ''}")

# ---- chart -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 10))
in_va = (prices >= prices[val]) & (prices <= prices[vah])
ax.barh(prices[in_va], vol[in_va], height=vp.ROW_HEIGHT, color="#4c78a8")
ax.barh(prices[~in_va], vol[~in_va], height=vp.ROW_HEIGHT, color="#b8c4d6")
ax.plot(smooth, prices, color="black", linewidth=0.8)
edge = vol.max() * 1.02
for name, idx, colour in (("VAH", vah, "#555555"), ("POC", poc, "#d62728"), ("VAL", val, "#555555")):
    ax.axhline(prices[idx], color=colour, linewidth=1)
    ax.text(edge, prices[idx], f" {name} {prices[idx]:.2f}", va="center", color=colour, fontsize=8)
colours = {"HVN": "#2ca02c", "LVN": "#ff7f0e"}
for kind, price, strength in nodes:
    ax.axhline(price, color=colours[kind], linewidth=0.8, linestyle="--")
    ax.text(edge, price, f" {kind} {price:.2f}", va="center", color=colours[kind], fontsize=8)
for g in ledges:                      # ledges are shaded zones; wide ones are fainter
    ax.axhspan(g.low - vp.ROW_HEIGHT / 2, g.high + vp.ROW_HEIGHT / 2,
               color="#9467bd", alpha=0.15 if g.wide else 0.45, linewidth=0)
if window == 1:                       # micro balance candidates (test 003) are shaded green
    for end in ("high", "low"):
        node = vp.end_node(prices, vol, window, end)
        if node and config.MICRO_SHARE[0] <= node["share"] <= config.MICRO_SHARE[1]:
            ax.axhspan(node["low"], node["high"], color="#17a673", alpha=0.35, linewidth=0)
            ax.text(vol.max() * 0.55, (node["low"] + node["high"]) / 2,
                    f"micro balance? {node['low']:.2f} to {node['high']:.2f} "
                    f"({node['share']:.0%} of volume)", va="center", fontsize=8, color="#0b5e41")
            print(f"  Micro balance candidate at the {end}: {node['low']:.2f} to {node['high']:.2f}, "
                  f"{node['share']:.0%} of the day's volume")
ax.set_xlim(0, vol.max() * 1.25)
ax.set_title(title)
ax.set_xlabel(f"Volume (contracts per {config.ROW_TICKS}-tick row)")
ax.set_ylabel("Price")
fig.tight_layout()

config.CHARTS_DIR.mkdir(parents=True, exist_ok=True)
out = config.CHARTS_DIR / f"profile_{day}_{window}d.png"
fig.savefig(out, dpi=130)
print(f"\nChart saved to {out}")
if sys.platform == "darwin":
    subprocess.run(["open", str(out)])
