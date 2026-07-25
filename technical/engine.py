from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TechnicalSettings:
    swing_window: int = 5
    lookback: int = 252
    zone_tolerance_pct: float = 1.0
    proximity_pct: float = 2.0
    breakout_buffer_pct: float = 0.3
    breakout_confirmations: int = 1
    rsi_period: int = 14
    ma_periods: tuple[int, ...] = (20, 50, 200)
    pattern_tolerance_pct: float = 3.0
    timeframe: str = "DAILY"


@dataclass(frozen=True)
class TechnicalSnapshot:
    ticker: str
    last: float
    data_date: Any
    support_low: float | None
    support_high: float | None
    resistance_low: float | None
    resistance_high: float | None
    distance_support_pct: float | None
    distance_resistance_pct: float | None
    rsi: float | None
    state: str
    setups: tuple[str, ...]
    patterns: tuple[str, ...]
    diagnostics: dict[str, Any]


TIMEFRAME_RULES: dict[str, str | None] = {
    "DAILY": None,
    "WEEKLY": "W-FRI",
    "MONTHLY": "ME",
}


def resample_technical_frame(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Return OHLCV bars for the selected technical-analysis timeframe."""
    label = str(timeframe).upper()
    if label not in TIMEFRAME_RULES:
        raise ValueError(f"Unsupported technical timeframe: {timeframe}")
    clean = frame.sort_index().copy()
    rule = TIMEFRAME_RULES[label]
    if rule is None:
        return clean
    aggregation: dict[str, str] = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
    }
    if "Volume" in clean.columns:
        aggregation["Volume"] = "sum"
    return clean.resample(rule).agg(aggregation).dropna(subset=["Open", "High", "Low", "Close"])


def parse_ma_periods(value: str | Iterable[int], maximum: int = 8) -> tuple[int, ...]:
    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    else:
        raw = list(value)
    periods: list[int] = []
    for item in raw:
        try:
            period = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if period > 1 and period not in periods:
            periods.append(period)
    return tuple(sorted(periods[:maximum]))


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    period = max(2, int(period))
    delta = close.astype(float).diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.where(avg_loss.ne(0.0), 100.0).clip(0.0, 100.0)


def add_moving_averages(frame: pd.DataFrame, periods: Iterable[int]) -> pd.DataFrame:
    result = frame.copy()
    for period in parse_ma_periods(periods):
        result[f"MA{period}"] = result["Close"].rolling(period, min_periods=period).mean()
    return result


def _swing_points(series: pd.Series, window: int, mode: str) -> pd.Series:
    window = max(2, int(window))
    rolling = series.rolling(window * 2 + 1, center=True, min_periods=window * 2 + 1)
    if mode == "high":
        mask = series.eq(rolling.max())
    else:
        mask = series.eq(rolling.min())
    return series[mask].dropna()


def _cluster_levels(points: pd.Series, tolerance_pct: float) -> list[dict[str, Any]]:
    if points.empty:
        return []
    clusters: list[dict[str, Any]] = []
    for date, value in points.sort_index().items():
        value = float(value)
        match = None
        for cluster in clusters:
            center = cluster["center"]
            if center and abs(value / center - 1.0) * 100.0 <= tolerance_pct:
                match = cluster
                break
        if match is None:
            clusters.append({"values": [value], "dates": [date], "center": value})
        else:
            match["values"].append(value)
            match["dates"].append(date)
            match["center"] = float(np.mean(match["values"]))
    output = []
    for cluster in clusters:
        values = cluster["values"]
        center = float(np.mean(values))
        half_width = max(center * tolerance_pct / 200.0, np.std(values) if len(values) > 1 else 0.0)
        output.append({
            "center": center,
            "low": center - half_width,
            "high": center + half_width,
            "touches": len(values),
            "last_date": max(cluster["dates"]),
        })
    return output


def find_support_resistance(frame: pd.DataFrame, settings: TechnicalSettings) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    recent = frame.tail(settings.lookback).copy()
    lows = _swing_points(recent["Low"], settings.swing_window, "low")
    highs = _swing_points(recent["High"], settings.swing_window, "high")
    last = float(recent["Close"].dropna().iloc[-1])
    supports = [z for z in _cluster_levels(lows, settings.zone_tolerance_pct) if z["center"] <= last * 1.03]
    resistances = [z for z in _cluster_levels(highs, settings.zone_tolerance_pct) if z["center"] >= last * 0.97]
    supports.sort(key=lambda z: (abs(last - z["center"]), -z["touches"]))
    resistances.sort(key=lambda z: (abs(last - z["center"]), -z["touches"]))
    return supports, resistances


def _distance_pct(price: float, level: float | None) -> float | None:
    if level in (None, 0):
        return None
    return (price / float(level) - 1.0) * 100.0


def _confirmed_break(close: pd.Series, level: float, direction: str, buffer_pct: float, confirmations: int) -> bool:
    confirmations = max(1, int(confirmations))
    recent = close.dropna().tail(confirmations)
    if len(recent) < confirmations:
        return False
    if direction == "above":
        threshold = level * (1.0 + buffer_pct / 100.0)
        return bool((recent > threshold).all())
    threshold = level * (1.0 - buffer_pct / 100.0)
    return bool((recent < threshold).all())


def _ma_events(frame: pd.DataFrame, periods: tuple[int, ...]) -> list[str]:
    events: list[str] = []
    periods = parse_ma_periods(periods)
    if len(frame) < 3:
        return events
    close = frame["Close"]
    for period in periods:
        ma = close.rolling(period, min_periods=period).mean()
        if ma.dropna().empty:
            continue
        current = float(ma.iloc[-1])
        if close.iloc[-1] > current:
            events.append(f"Price above MA{period}")
        else:
            events.append(f"Price below MA{period}")
    for fast, slow in zip(periods, periods[1:]):
        fast_ma = close.rolling(fast, min_periods=fast).mean()
        slow_ma = close.rolling(slow, min_periods=slow).mean()
        if fast_ma.iloc[-2:].isna().any() or slow_ma.iloc[-2:].isna().any():
            continue
        previous = fast_ma.iloc[-2] - slow_ma.iloc[-2]
        current = fast_ma.iloc[-1] - slow_ma.iloc[-1]
        if previous <= 0 < current:
            events.append(f"Bullish MA crossover: MA{fast} above MA{slow}")
        elif previous >= 0 > current:
            events.append(f"Bearish MA crossover: MA{fast} below MA{slow}")
    return events


def detect_rsi_divergence(frame: pd.DataFrame, rsi: pd.Series, swing_window: int = 5, max_separation: int = 80) -> str | None:
    recent = frame.tail(max(120, max_separation + 20))
    rsi_recent = rsi.reindex(recent.index)
    price_lows = _swing_points(recent["Low"], swing_window, "low")
    price_highs = _swing_points(recent["High"], swing_window, "high")

    if len(price_lows) >= 2:
        first_date, second_date = price_lows.index[-2], price_lows.index[-1]
        first_rsi, second_rsi = rsi_recent.get(first_date), rsi_recent.get(second_date)
        if pd.notna(first_rsi) and pd.notna(second_rsi):
            if price_lows.iloc[-1] < price_lows.iloc[-2] and second_rsi > first_rsi:
                return "Potential bullish RSI divergence"

    if len(price_highs) >= 2:
        first_date, second_date = price_highs.index[-2], price_highs.index[-1]
        first_rsi, second_rsi = rsi_recent.get(first_date), rsi_recent.get(second_date)
        if pd.notna(first_rsi) and pd.notna(second_rsi):
            if price_highs.iloc[-1] > price_highs.iloc[-2] and second_rsi < first_rsi:
                return "Potential bearish RSI divergence"
    return None


def _slope(values: pd.Series) -> float:
    clean = values.dropna().astype(float)
    if len(clean) < 3:
        return 0.0
    x = np.arange(len(clean), dtype=float)
    return float(np.polyfit(x, clean.to_numpy(), 1)[0])


def detect_pattern_details(frame: pd.DataFrame, settings: TechnicalSettings) -> list[dict[str, Any]]:
    """Return heuristic pattern candidates plus chart coordinates for visual review."""
    recent = frame.tail(min(settings.lookback, 180)).copy()
    highs = _swing_points(recent["High"], settings.swing_window, "high")
    lows = _swing_points(recent["Low"], settings.swing_window, "low")
    details: list[dict[str, Any]] = []
    tol = settings.pattern_tolerance_pct / 100.0

    if len(highs) >= 2:
        pts = highs.tail(2)
        a, b = float(pts.iloc[0]), float(pts.iloc[1])
        if a and abs(b / a - 1.0) <= tol:
            details.append({"name": "Potential double top", "start": pts.index[0], "end": pts.index[1],
                            "anchors": [(pts.index[0], a), (pts.index[1], b)]})
    if len(lows) >= 2:
        pts = lows.tail(2)
        a, b = float(pts.iloc[0]), float(pts.iloc[1])
        if a and abs(b / a - 1.0) <= tol:
            details.append({"name": "Potential double bottom", "start": pts.index[0], "end": pts.index[1],
                            "anchors": [(pts.index[0], a), (pts.index[1], b)]})

    if len(highs) >= 3 and len(lows) >= 3:
        hp = highs.tail(4); lp = lows.tail(4)
        high_slope = _slope(hp); low_slope = _slope(lp)
        avg_price = float(recent["Close"].mean())
        flat_limit = avg_price * 0.002
        name = None
        if abs(high_slope) <= flat_limit and low_slope > flat_limit:
            name = "Potential ascending triangle"
        elif high_slope < -flat_limit and abs(low_slope) <= flat_limit:
            name = "Potential descending triangle"
        elif high_slope < -flat_limit and low_slope > flat_limit:
            name = "Potential symmetrical triangle / pennant"
        if name:
            anchors = [(d, float(v)) for d, v in hp.items()] + [(d, float(v)) for d, v in lp.items()]
            details.append({"name": name, "start": min(hp.index.min(), lp.index.min()),
                            "end": max(hp.index.max(), lp.index.max()), "anchors": anchors,
                            "upper": [(d, float(v)) for d, v in hp.items()],
                            "lower": [(d, float(v)) for d, v in lp.items()]})

    if len(recent) >= 45:
        impulse = recent["Close"].iloc[-30] / recent["Close"].iloc[-45] - 1.0
        consolidation = recent.tail(15)
        consolidation_return = consolidation["Close"].iloc[-1] / consolidation["Close"].iloc[0] - 1.0
        range_pct = consolidation["High"].max() / consolidation["Low"].min() - 1.0
        name = None
        if impulse > 0.12 and -0.10 < consolidation_return < 0.02 and range_pct < 0.18:
            name = "Potential bullish flag"
        elif impulse < -0.12 and -0.02 < consolidation_return < 0.10 and range_pct < 0.18:
            name = "Potential bearish flag"
        if name:
            details.append({"name": name, "start": recent.index[-45], "end": recent.index[-1],
                            "highlight_start": consolidation.index[0], "highlight_end": consolidation.index[-1],
                            "anchors": [(recent.index[-45], float(recent["Close"].iloc[-45])),
                                        (recent.index[-30], float(recent["Close"].iloc[-30]))]})

    if len(recent) >= 100:
        window = recent["Close"].tail(100)
        left = window.iloc[:25]; middle = window.iloc[25:75]; right = window.iloc[60:90]; handle = window.iloc[85:]
        left_high = float(left.max()); trough = float(middle.min()); right_high = float(right.max())
        depth = 1.0 - trough / left_high if left_high else 0.0
        recovered = abs(right_high / left_high - 1.0) <= tol * 1.5
        handle_pullback = 1.0 - float(handle.min()) / right_high if right_high else 0.0
        if 0.10 <= depth <= 0.45 and recovered and 0.0 <= handle_pullback <= 0.12:
            anchors = [(left.idxmax(), left_high), (middle.idxmin(), trough), (right.idxmax(), right_high),
                       (handle.idxmin(), float(handle.min()))]
            details.append({"name": "Potential cup and handle", "start": window.index[0], "end": window.index[-1],
                            "highlight_start": handle.index[0], "highlight_end": handle.index[-1], "anchors": anchors})

    unique: dict[str, dict[str, Any]] = {}
    for item in details:
        unique[item["name"]] = item
    return list(unique.values())


def detect_patterns(frame: pd.DataFrame, settings: TechnicalSettings) -> list[str]:
    return [item["name"] for item in detect_pattern_details(frame, settings)]


def analyse_technical(ticker: str, frame: pd.DataFrame, settings: TechnicalSettings) -> TechnicalSnapshot:
    if frame.empty or "Close" not in frame or len(frame.dropna(subset=["Close"])) < 30:
        raise ValueError("Insufficient price history for technical analysis")
    frame = frame.sort_index().copy()
    close = frame["Close"].dropna()
    last = float(close.iloc[-1])
    supports, resistances = find_support_resistance(frame, settings)
    support = supports[0] if supports else None
    resistance = resistances[0] if resistances else None
    rsi_series = calculate_rsi(close, settings.rsi_period)
    rsi_value = float(rsi_series.iloc[-1]) if pd.notna(rsi_series.iloc[-1]) else None

    setups: list[str] = []
    support_center = support["center"] if support else None
    resistance_center = resistance["center"] if resistance else None
    ds = _distance_pct(last, support_center)
    dr = _distance_pct(last, resistance_center)

    if support:
        if support["low"] <= last <= support["high"]:
            setups.append("In support area")
        elif ds is not None and 0 <= ds <= settings.proximity_pct:
            setups.append("Approaching support")
        if _confirmed_break(close, support["low"], "below", settings.breakout_buffer_pct, settings.breakout_confirmations):
            setups.append("Support breakdown")
    if resistance:
        if resistance["low"] <= last <= resistance["high"]:
            setups.append("In resistance area")
        elif dr is not None and -settings.proximity_pct <= dr <= 0:
            setups.append("Approaching resistance")
        if _confirmed_break(close, resistance["high"], "above", settings.breakout_buffer_pct, settings.breakout_confirmations):
            setups.append("Resistance breakout")

    setups.extend(_ma_events(frame, settings.ma_periods))
    if rsi_value is not None:
        if rsi_value >= 70:
            setups.append(f"RSI overbought ({rsi_value:.1f})")
        elif rsi_value <= 30:
            setups.append(f"RSI oversold ({rsi_value:.1f})")
    divergence = detect_rsi_divergence(frame, rsi_series, settings.swing_window)
    if divergence:
        setups.append(divergence)
    pattern_details = detect_pattern_details(frame, settings)
    patterns = [item["name"] for item in pattern_details]
    setups.extend(patterns)

    priority = [
        "Resistance breakout", "Support breakdown", "In support area", "In resistance area",
        "Approaching support", "Approaching resistance",
    ]
    state = next((item for item in priority if item in setups), "No active level event")
    return TechnicalSnapshot(
        ticker=ticker,
        last=last,
        data_date=close.index[-1],
        support_low=support["low"] if support else None,
        support_high=support["high"] if support else None,
        resistance_low=resistance["low"] if resistance else None,
        resistance_high=resistance["high"] if resistance else None,
        distance_support_pct=ds,
        distance_resistance_pct=dr,
        rsi=rsi_value,
        state=state,
        setups=tuple(dict.fromkeys(setups)),
        patterns=tuple(patterns),
        diagnostics={"supports": supports[:5], "resistances": resistances[:5], "pattern_details": pattern_details},
    )


def scan_universe(constituents: pd.DataFrame, data: dict[str, pd.DataFrame], settings: TechnicalSettings) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    meta = constituents.drop_duplicates("Ticker").set_index("Ticker")
    for ticker in constituents["Ticker"].drop_duplicates():
        frame = data.get(ticker)
        if frame is not None and not frame.empty:
            frame = resample_technical_frame(frame, settings.timeframe)
        if frame is None or frame.empty:
            failures.append({"Ticker": ticker, "Reason": "No price data"})
            continue
        try:
            snap = analyse_technical(ticker, frame, settings)
            company = str(meta.loc[ticker, "Company"]) if ticker in meta.index else ticker
            sector = str(meta.loc[ticker, "Sector"]) if ticker in meta.index else "Unclassified"
            rows.append({
                "Ticker": ticker,
                "Company": company,
                "Sector": sector,
                "Last": snap.last,
                "Technical State": snap.state,
                "Setups": " | ".join(snap.setups),
                "Setup Count": len(snap.setups),
                "Patterns": " | ".join(snap.patterns) if snap.patterns else "—",
                "Support Low": snap.support_low,
                "Support High": snap.support_high,
                "Distance Support %": snap.distance_support_pct,
                "Resistance Low": snap.resistance_low,
                "Resistance High": snap.resistance_high,
                "Distance Resistance %": snap.distance_resistance_pct,
                "RSI": snap.rsi,
                "Data Date": snap.data_date,
            })
        except Exception as exc:
            failures.append({"Ticker": ticker, "Reason": str(exc)})
    return pd.DataFrame(rows), pd.DataFrame(failures)
