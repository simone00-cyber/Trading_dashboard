from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis.cyclical import build_cyclical_engine
from analysis.cyclical.technical_cross_check import CrossCheckRead, build_technical_cyclical_cross_check
from analysis.security_signal import build_tactical_signal_state
from screener.engine import download_universe_ohlc
from technical.assessment import build_technical_assessment
from technical.engine import PatternReliability, TechnicalSettings, estimate_pattern_reliability, parse_ma_periods
from technical.multi_timeframe import build_multi_timeframe_alignment
from ui.research_panels import (
    render_cyclical_position_panel,
    render_developing_patterns_panel,
    render_header,
    render_key_levels_panel,
    render_market_structure_panel,
    render_momentum_volatility_panel,
    render_multi_timeframe_panel,
    render_summary_and_actions,
)
from views.security import load_analysis as load_cyclical_analysis


@st.cache_data(ttl=3600, show_spinner=False, max_entries=32)
def _daily_prices(ticker: str) -> pd.DataFrame:
    data = download_universe_ohlc([ticker], period="max", chunk_size=1)
    return data.get(ticker, pd.DataFrame())


def _settings_panel(key_prefix: str) -> TechnicalSettings:
    with st.expander("ADJUST TECHNICAL PARAMETERS", expanded=False):
        cols = st.columns(4)
        ma_text = cols[0].text_input("MOVING AVERAGES", value="20, 50, 200", key=f"{key_prefix}_ma")
        swing_window = cols[1].slider("SWING WINDOW", 2, 10, 5, key=f"{key_prefix}_swing")
        rsi_period = cols[2].slider("RSI PERIOD", 5, 30, 14, key=f"{key_prefix}_rsi")
        pattern_tolerance = cols[3].slider("PATTERN TOLERANCE %", 1.0, 8.0, 3.0, step=0.5, key=f"{key_prefix}_tol")
    return TechnicalSettings(
        swing_window=swing_window,
        rsi_period=rsi_period,
        ma_periods=parse_ma_periods(ma_text) or (20, 50, 200),
        pattern_tolerance_pct=pattern_tolerance,
    )


def _developing_or_leading_patterns(snapshot_diagnostics: dict, limit: int = 3) -> list[dict]:
    details = snapshot_diagnostics.get("pattern_details", [])
    developing = [p for p in details if p["status"] == "DEVELOPING"]
    return (developing or details)[:limit]


def render_research(*, ticker_override: str | None = None, embedded: bool = False) -> None:
    if not embedded:
        st.markdown("<div class='terminal-header'>RESEARCH WORKSPACE // MARKET STRUCTURE, PATTERNS &amp; CYCLICAL POSITION</div>", unsafe_allow_html=True)
        st.caption("One unified read: current market structure, developing patterns, multi-timeframe alignment and the documented cyclical position — always with the evidence and the invalidation level behind it.")

    if ticker_override:
        ticker = ticker_override.strip().upper()
        st.info(f"Workspace ticker: {ticker}")
    else:
        ticker = st.text_input("Yahoo Finance ticker", value="AAPL", key="research_direct_ticker").strip().upper()

    if not ticker:
        st.info("Enter a ticker to begin.")
        return

    settings = _settings_panel("research")

    try:
        with st.spinner(f"Analysing {ticker}..."):
            daily_frame = _daily_prices(ticker)
    except Exception as exc:
        st.error(f"Unable to download price history for {ticker}: {exc}")
        return
    if daily_frame.empty or len(daily_frame.dropna(subset=["Close"])) < 60:
        st.error(f"Not enough price history for {ticker} to build a research view.")
        return

    try:
        assessment = build_technical_assessment(ticker, daily_frame, settings)
    except ValueError as exc:
        st.error(str(exc))
        return

    alignment = build_multi_timeframe_alignment(daily_frame, settings)
    patterns = _developing_or_leading_patterns(assessment.snapshot.diagnostics)
    reliabilities: dict[str, PatternReliability] = {}
    for pattern in patterns:
        try:
            reliabilities[pattern["name"]] = estimate_pattern_reliability(daily_frame, settings, pattern["name"], pattern["direction"])
        except Exception:
            continue

    signal_state = None
    hierarchy = None
    cross_check: CrossCheckRead | None = None
    try:
        _, _, cyclical_frames, cyclical_summaries, _ = load_cyclical_analysis(ticker, "max")
        signal_state = build_tactical_signal_state(cyclical_frames, cyclical_summaries)
        _, hierarchy = build_cyclical_engine(cyclical_frames)
        cross_check = build_technical_cyclical_cross_check(assessment, hierarchy)
    except Exception:
        pass

    company = ticker

    # --- Above the fold: header, structure, levels, patterns ---
    render_header(ticker, assessment, signal_state)
    render_market_structure_panel(assessment)
    render_key_levels_panel(assessment)
    render_developing_patterns_panel(patterns, reliabilities)
    render_momentum_volatility_panel(assessment)
    render_multi_timeframe_panel(alignment)

    if signal_state is not None and hierarchy is not None:
        render_cyclical_position_panel(signal_state, hierarchy, cross_check)
    else:
        st.markdown("<div class='terminal-subheader'>CYCLICAL POSITION</div>", unsafe_allow_html=True)
        st.info("Cyclical position unavailable — insufficient history to build the quarterly/monthly/weekly Composite Momentum hierarchy for this ticker.")

    render_summary_and_actions(ticker, company, assessment, alignment, cross_check, patterns)

    # --- Progressive disclosure ---
    with st.expander("FULL PATTERN LIST", expanded=False):
        details = assessment.snapshot.diagnostics.get("pattern_details", [])
        if not details:
            st.caption("No patterns currently meet the precision threshold.")
        else:
            table = pd.DataFrame(
                [
                    {
                        "Pattern": d["name"],
                        "Category": d["category"],
                        "Direction": d["direction"],
                        "Status": d["status"],
                        "Confidence": d["confidence"],
                        "Completion %": d.get("completion_pct"),
                        "Trigger": d.get("trigger"),
                        "Invalidation": d.get("invalidation"),
                    }
                    for d in details
                ]
            )
            st.dataframe(table, width="stretch", hide_index=True)

    with st.expander("SUPPORT / RESISTANCE DIAGNOSTICS", expanded=False):
        for label, zones in (("SUPPORTS", assessment.snapshot.diagnostics.get("supports", [])), ("RESISTANCES", assessment.snapshot.diagnostics.get("resistances", []))):
            st.markdown(f"**{label}**")
            if not zones:
                st.caption("None detected.")
                continue
            st.dataframe(pd.DataFrame(zones)[["center", "low", "high", "role", "state", "strength", "touches"]], width="stretch", hide_index=True)

    if signal_state is not None:
        with st.expander("CYCLICAL SIGNAL HISTORY", expanded=False):
            if not signal_state.history:
                st.caption("No documented matrix events in the available history.")
            else:
                history_rows = [
                    {
                        "DATE": event.date.strftime("%d/%m/%Y"),
                        "EVENT": event.action,
                        "RATING": "●" * event.rating,
                        "QUARTERLY": event.quarterly_direction,
                        "MONTHLY": event.monthly_direction,
                        "WEEKLY": event.weekly_turn,
                        "WEEKLY CM": round(event.weekly_composite, 2),
                    }
                    for event in reversed(signal_state.history[-12:])
                ]
                st.dataframe(pd.DataFrame(history_rows), width="stretch", hide_index=True)

    with st.expander("METHODOLOGY &amp; PROVENANCE", expanded=False):
        st.write(
            "Market Structure, Developing Patterns, Momentum & Volatility and Multi-Timeframe Alignment are this "
            "workspace's own technical engine (technical/engine.py, technical/market_structure.py) — heuristic, "
            "transparent and never a trading signal. Pattern categories (triangles, flags, wedges, rectangles, "
            "double/triple top/bottom, head & shoulders, rounded formations, channels) and concepts (support/"
            "resistance, breakout/breakdown, divergence, RSI overbought/oversold) match the published Caruso "
            "technical glossary; the precision heuristics themselves (trendline fit quality, volume bias, "
            "completion %, per-ticker reliability replay) are this software's own, not part of that methodology."
        )
        st.write(
            "Cyclical Position reuses the documented Composite Momentum matrix and hierarchy unchanged "
            "(caruso_analysis.py, analysis/cyclical/*) — verified against the original ProRealTime and MetaStock "
            "source formulas. The Technical × Cyclical cross-check only compares the two engines' outputs; it "
            "does not feed back into or alter either one."
        )
