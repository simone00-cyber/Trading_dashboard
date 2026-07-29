import numpy as np
import pandas as pd

from technical.engine import TechnicalSettings
from technical.market_structure import (
    assess_risk,
    assess_trend_quality,
    classify_swing_structure,
    classify_volatility_regime,
)


def _trending_frame(n: int = 400, slope: float = 0.05, wiggle: float = 3.0) -> pd.DataFrame:
    x = np.arange(n)
    close = 100 + slope * x + wiggle * np.sin(x / 10)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close_s = pd.Series(close, index=idx)
    return pd.DataFrame(
        {
            "Open": close_s.shift(1).fillna(close_s.iloc[0]),
            "High": close_s + 1.0,
            "Low": close_s - 1.0,
            "Close": close_s,
            "Volume": 1000,
        },
        index=idx,
    )


def _flat_frame(n: int = 300) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close_s = pd.Series(100.0 + np.random.default_rng(0).normal(0, 0.2, n), index=idx)
    return pd.DataFrame(
        {
            "Open": close_s,
            "High": close_s + 0.5,
            "Low": close_s - 0.5,
            "Close": close_s,
            "Volume": 1000,
        },
        index=idx,
    )


def test_classify_swing_structure_detects_uptrend_sequence():
    frame = _trending_frame(slope=0.06)
    structure = classify_swing_structure(frame, TechnicalSettings())
    assert structure.sequence == "HIGHER HIGHS / HIGHER LOWS"
    assert structure.higher_highs > 0
    assert structure.higher_lows > 0


def test_classify_swing_structure_detects_downtrend_sequence():
    frame = _trending_frame(slope=-0.06)
    structure = classify_swing_structure(frame, TechnicalSettings())
    assert structure.sequence == "LOWER HIGHS / LOWER LOWS"


def test_assess_trend_quality_scores_strong_uptrend_highly():
    frame = _trending_frame(slope=0.06, wiggle=1.0)
    quality = assess_trend_quality(frame, TechnicalSettings())
    assert quality.ma_alignment == "BULLISH STACK"
    assert quality.score >= 60
    assert quality.label in {"STRONG", "MODERATE"}


def test_assess_trend_quality_scores_flat_series_low():
    frame = _flat_frame()
    quality = assess_trend_quality(frame, TechnicalSettings())
    assert quality.score < 60


def test_classify_volatility_regime_returns_known_bucket():
    frame = _trending_frame()
    regime, percentile, atr_pct = classify_volatility_regime(frame)
    assert regime in {"CONTRACTING", "NORMAL", "EXPANDING", "UNKNOWN"}
    assert atr_pct >= 0 or np.isnan(atr_pct)
    if regime != "UNKNOWN":
        assert 0 <= percentile <= 100


def test_assess_risk_distance_to_invalidation_is_computed():
    frame = _trending_frame()
    last_close = float(frame["Close"].iloc[-1])
    risk = assess_risk(frame, invalidation=last_close * 0.9)
    assert risk.level in {"LOW", "MODERATE", "ELEVATED"}
    assert risk.distance_to_invalidation_pct is not None
    assert risk.distance_to_invalidation_pct > 0


def test_assess_risk_handles_missing_invalidation():
    frame = _trending_frame()
    risk = assess_risk(frame, invalidation=None)
    assert risk.distance_to_invalidation_pct is None
