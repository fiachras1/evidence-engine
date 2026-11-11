"""Volume profile maths: composites, value area, HVNs, LVNs and ledges."""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

import config

TICKS_PER_POINT = round(1 / config.TICK)
ROW = config.ROW_TICKS                       # ticks per profile row
ROWS_PER_POINT = TICKS_PER_POINT / ROW
ROW_HEIGHT = ROW * config.TICK               # in points


def load_daily(con):
    """Read every session's profile and roll information from the database.

    Returns (dates, profiles, gaps, contracts):
      dates      sorted list of session dates
      profiles   date -> (first tick, array of volume per tick)
      gaps       date -> running total of roll gaps, in ticks
      contracts  date -> contract id
    """
    df = con.execute(
        "SELECT session_date, price, volume FROM profile_daily ORDER BY session_date, price"
    ).fetchdf()
    profiles = {}
    for date, day in df.groupby("session_date"):
        ticks = np.rint(day["price"].to_numpy() * TICKS_PER_POINT).astype(int)
        vol = np.zeros(ticks[-1] - ticks[0] + 1)
        vol[ticks - ticks[0]] = day["volume"].to_numpy()
        profiles[date.date()] = (ticks[0], vol)

    info = con.execute("SELECT * FROM session_contract").fetchdf()
    gaps = {r.session_date.date(): int(round(r.roll_gap_total * TICKS_PER_POINT))
            for r in info.itertuples()}
    contracts = {r.session_date.date(): r.instrument_id for r in info.itertuples()}
    return sorted(profiles), profiles, gaps, contracts


def composite(window_dates, profiles, gaps):
    """Add several sessions' profiles into one.

    Sessions from an older contract are shifted by the roll gap so that all
    prices are in terms of the LAST session's contract.
    Ticks are then grouped into rows of ROW_TICKS (see config.py).
    Returns (prices, volume) as two arrays, one entry per row.
    """
    last = window_dates[-1]
    shifted = []
    for d in window_dates:
        first_tick, vol = profiles[d]
        shifted.append((first_tick + gaps[last] - gaps[d], vol))
    lo = min(t for t, _ in shifted) // ROW * ROW          # start on a row boundary
    hi = -(-max(t + len(v) for t, v in shifted) // ROW) * ROW
    total = np.zeros(hi - lo)
    for t, v in shifted:
        total[t - lo:t - lo + len(v)] += v
    rows = total.reshape(-1, ROW).sum(axis=1)             # add each group of ticks together
    # each row is labelled with its middle price
    prices = (lo + np.arange(len(rows)) * ROW + ROW // 2) / TICKS_PER_POINT
    return prices, rows


def value_area(vol, share=config.VALUE_AREA):
    """Return the positions of (POC, VAL, VAH) in the volume array.

    Start at the POC and keep adding whichever neighbouring price has more
    volume, above or below, until the area holds `share` of all volume.
    """
    poc = int(np.argmax(vol))
    lo = hi = poc
    inside, target = vol[poc], share * vol.sum()
    while inside < target and (lo > 0 or hi < len(vol) - 1):
        below = vol[lo - 1] if lo > 0 else -1
        above = vol[hi + 1] if hi < len(vol) - 1 else -1
        if above >= below:
            hi += 1
            inside += above
        else:
            lo -= 1
            inside += below
    return poc, lo, hi


def find_nodes(prices, vol, window):
    """Find HVNs, LVNs and ledges in one profile.

    Returns a list of (kind, price, strength, note).

    HVN    a peak in the smoothed profile that stands out from its surroundings.
           strength = its volume as a share of the POC's volume.
    LVN    a dip between two peaks. strength = its volume as a share of the POC's
           (lower = thinner).
    LEDGE  a price where volume falls away sharply: within LEDGE_SPAN_PTS the
           profile drops by at least LEDGE_MIN_DROP of the POC's volume.
           price = middle of the drop. strength = size of the drop.
           note says which side the volume shelf is on.
    """
    smooth = gaussian_filter1d(vol, config.SMOOTH_PTS[window] * ROWS_PER_POINT)
    top = smooth.max()
    need = config.NODE_MIN_PROMINENCE * top
    nodes = []

    for i in find_peaks(smooth, prominence=need)[0]:
        nodes.append(("HVN", prices[i], smooth[i] / top, ""))
    for i in find_peaks(-smooth, prominence=need)[0]:
        nodes.append(("LVN", prices[i], smooth[i] / top, ""))

    half = max(1, round(config.LEDGE_SPAN_PTS[window] * ROWS_PER_POINT / 2))
    change = np.zeros_like(smooth)
    change[half:-half] = smooth[2 * half:] - smooth[:-2 * half]   # volume above minus below
    steep, _ = find_peaks(np.abs(change), height=config.LEDGE_MIN_DROP * top,
                          distance=2 * half)
    for i in steep:
        side = "shelf below" if change[i] < 0 else "shelf above"
        nodes.append(("LEDGE", prices[i], abs(change[i]) / top, side))

    return sorted(nodes, key=lambda n: -n[1]), smooth
