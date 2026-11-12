"""Volume profile maths: composites, value area, HVNs, LVNs and ledges."""
from collections import namedtuple

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

    Returns (nodes, ledges, smooth).

    nodes   list of (kind, price, strength)
            HVN  a peak in the smoothed profile that stands out from its surroundings
            LVN  a dip between two peaks
            strength = volume there as a share of the POC's volume
    ledges  list of Ledge (see find_ledges)
    smooth  the smoothed profile
    """
    smooth = gaussian_filter1d(vol, config.SMOOTH_PTS[window] * ROWS_PER_POINT)
    top = smooth.max()
    need = config.NODE_MIN_PROMINENCE * top
    peaks = find_peaks(smooth, prominence=need)[0]
    dips = find_peaks(-smooth, prominence=need)[0]

    nodes = [("HVN", prices[i], smooth[i] / top) for i in peaks]
    nodes += [("LVN", prices[i], smooth[i] / top) for i in dips]
    ledges = find_ledges(prices, smooth, peaks, dips)
    return sorted(nodes, key=lambda n: -n[1]), ledges, smooth


Ledge = namedtuple("Ledge", "low high width fall size node side wide")


def find_ledges(prices, smooth, peaks, dips):
    """Find ledges: where a volume node falls away steeply into a thin area.

    For every node (HVN), look at the nearest thin area on each side: the next
    LVN, or the end of the profile. If volume falls far enough between them,
    the ledge is the middle half of that slope (from 25% to 75% of the fall).

    Each Ledge has:
      low, high   the price zone of the ledge
      width       high - low, in points
      fall        how much volume falls, as a share of the node's own volume
      size        the same fall as a share of the POC's volume
      node        the node's share of the whole profile's volume
      side        "top" (thin area above the node) or "bottom" (thin area below)
      wide        True if wider than LEDGE_MAX_WIDTH
    """
    top, total = smooth.max(), smooth.sum()
    thin = [0] + list(dips) + [len(smooth) - 1]      # profile ends count as thin areas
    ledges = []
    for h in peaks:
        below = max((t for t in thin if t < h), default=None)
        above = min((t for t in thin if t > h), default=None)
        # the node is everything between the thin areas either side of the peak
        node = smooth[(below or 0):(above or len(smooth) - 1) + 1].sum() / total
        for t, side in ((below, "bottom"), (above, "top")):
            if t is None:
                continue
            drop = smooth[h] - smooth[t]
            if drop < config.LEDGE_MIN_FALL * smooth[h] or drop < config.LEDGE_MIN_SIZE * top:
                continue
            if node < config.LEDGE_MIN_NODE:       # ledges of small nodes are ignored
                continue
            a, b = sorted((h, t))
            slope = smooth[a:b + 1]
            steep = np.flatnonzero((slope >= smooth[t] + 0.25 * drop) &
                                   (slope <= smooth[t] + 0.75 * drop))
            if len(steep) == 0:        # fall happens within a single row
                steep = np.array([len(slope) // 2])
            low, high = prices[a + steep.min()], prices[a + steep.max()]
            width = high - low
            ledges.append(Ledge(low, high, width, drop / smooth[h], drop / top,
                                node, side, width > config.LEDGE_MAX_WIDTH))
    return sorted(ledges, key=lambda g: -g.low)


def grade_ledges(daily, five_day, twenty_day, last_low, last_high):
    """Grade ledges by how many profiles agree on them.

    daily        {session date: [Ledge, ...]} for the daily profiles being compared
    five_day     [Ledge, ...] from the 5-day profile
    twenty_day   [Ledge, ...] from the 20-day profile
    last_low, last_high   the latest session's RTH low and high

    A ledge is graded when at least 2 daily profiles show a ledge on the same
    side within GRADE_TOLERANCE points of each other. Wide ledges are ignored.
    Two graded ledges within GRADE_TOLERANCE of each other become one: the
    higher grade wins, and equal grades are merged. A ledge must be within
    tolerance of every ledge in a group to join it, so zones cannot chain.
    status is "pending" while the latest session traded through the ledge,
    otherwise "active".
    Returns a list of (grade, low, high, side, days, in_5d, in_20d, status).
    """
    tol = config.GRADE_TOLERANCE
    rank = config.GRADE_ORDER.index
    graded = []
    for side in ("top", "bottom"):
        found = sorted((g.low, g.high, day) for day, ledges in daily.items()
                       for g in ledges if g.side == side and not g.wide)
        groups = []
        for low, high, day in found:
            # join the group only if within tolerance of EVERY ledge already in it
            # ("nearest" is the lowest top edge in the group), so groups cannot chain
            if groups and low - groups[-1]["nearest"] <= tol:
                groups[-1]["high"] = max(groups[-1]["high"], high)
                groups[-1]["nearest"] = min(groups[-1]["nearest"], high)
                groups[-1]["days"].add(day)
            else:
                groups.append({"low": low, "high": high, "nearest": high, "days": {day}})
        for grp in groups:
            if len(grp["days"]) < 2:
                continue

            def agrees(ledges):
                return any(g.side == side and not g.wide and
                           g.low <= grp["high"] + tol and g.high >= grp["low"] - tol
                           for g in ledges)

            in_5d, in_20d = agrees(five_day), agrees(twenty_day)
            grade = "A" if in_5d and in_20d else "B+" if in_20d else "B" if in_5d else "C"
            graded.append([grade, grp["low"], grp["high"], side,
                           len(grp["days"]), in_5d, in_20d, grp["nearest"]])

    # ledges within tolerance of each other: keep the higher grade, merge equal grades
    graded.sort(key=lambda r: r[1])
    kept = []
    widest = 2 * config.LEDGE_MAX_WIDTH + tol     # two full-width ledges, tolerance apart
    for row in graded:
        if kept and row[1] - kept[-1][2] <= tol:        # zones within tolerance of each other
            prev = kept[-1]
            if rank(row[0]) < rank(prev[0]):
                kept[-1] = row                          # higher grade wins
            elif row[0] != prev[0]:
                pass                                    # lower grade is dropped
            elif max(prev[2], row[2]) - prev[1] > widest:
                kept.append(row)                        # merging would make the zone too wide
            else:                                       # same grade: merge
                prev[2] = max(prev[2], row[2])
                prev[3] = prev[3] if prev[3] == row[3] else "both"
                prev[4] = max(prev[4], row[4])
                prev[5], prev[6] = prev[5] or row[5], prev[6] or row[6]
        else:
            kept.append(row)
    kept = [row[:7] for row in kept]

    for row in kept:
        traded_through = last_low <= row[2] and last_high >= row[1]
        row.append("pending" if traded_through else "active")
    return [tuple(r) for r in sorted(kept, key=lambda r: -r[1])]
