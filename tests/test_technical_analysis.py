import numpy as np
import pandas as pd

from technical.engine import TechnicalSettings, analyse_technical, calculate_rsi, parse_ma_periods, scan_universe


def _frame(n=420):
    idx = pd.date_range('2024-01-01', periods=n, freq='B')
    base = 100 + np.sin(np.arange(n) / 12) * 5 + np.arange(n) * 0.03
    return pd.DataFrame({
        'Open': base - 0.3,
        'High': base + 1.0,
        'Low': base - 1.0,
        'Close': base,
        'Volume': 1000,
    }, index=idx)


def test_parse_ma_periods():
    assert parse_ma_periods('50, 20, 20, 200') == (20, 50, 200)


def test_rsi_is_bounded():
    rsi = calculate_rsi(_frame()['Close'], 14).dropna()
    assert not rsi.empty
    assert rsi.between(0, 100).all()


def test_technical_snapshot_has_levels_and_setups():
    snap = analyse_technical('TEST', _frame(), TechnicalSettings())
    assert snap.last > 0
    assert isinstance(snap.setups, tuple)
    assert snap.rsi is not None


def test_universe_scan():
    constituents = pd.DataFrame([{'Ticker': 'TEST', 'Company': 'Test Co', 'Sector': 'Technology'}])
    rows, failures = scan_universe(constituents, {'TEST': _frame()}, TechnicalSettings())
    assert len(rows) == 1
    assert failures.empty
    assert 'Technical State' in rows.columns
