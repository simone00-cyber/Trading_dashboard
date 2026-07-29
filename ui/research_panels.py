from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from analysis.cyclical.models import HierarchyAssessment
from analysis.cyclical.technical_cross_check import CrossCheckRead
from analysis.security_signal import TacticalSignalState
from config.theme import GREEN, MUTED, ORANGE, RED
from technical.assessment import TechnicalAssessment
from technical.engine import PatternReliability
from technical.multi_timeframe import MultiTimeframeAlignment


def _stat_row(items: list[tuple[str, str]]) -> None:
    """Compact stat tiles with a small, wrapping value font — unlike st.metric, long
    values (e.g. a sequence label or a price range) are never clipped with an ellipsis."""
    blocks = "".join(
        "<div class='opp-card-metric'>"
        f"<span class='opp-card-metric-label'>{html.escape(label)}</span>"
        f"<span class='opp-card-metric-value' style='font-size:.88rem;white-space:normal;'>{html.escape(value)}</span>"
        "</div>"
        for label, value in items
    )
    st.markdown(f"<div class='opp-card-metrics'>{blocks}</div>", unsafe_allow_html=True)


def _confidence_color(confidence: int) -> str:
    if confidence >= 70:
        return GREEN
    if confidence >= 45:
        return ORANGE
    return RED


def render_confidence_bar(confidence: int, components: dict[str, int] | None = None) -> None:
    color = _confidence_color(confidence)
    st.markdown(
        "<div class='confidence-row'>"
        f"<div class='confidence-track'><div class='confidence-fill' style='width:{confidence}%;background:{color}'></div></div>"
        f"<div class='confidence-label'>{confidence}/100</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if components:
        parts = " · ".join(f"{name.replace('_', ' ').title()}: {value}" for name, value in components.items())
        st.markdown(f"<div class='small-note'>{html.escape(parts)}</div>", unsafe_allow_html=True)


def render_header(ticker: str, assessment: TechnicalAssessment, signal_state: TacticalSignalState | None) -> None:
    snapshot = assessment.snapshot
    cols = st.columns(4)
    cols[0].metric("TICKER", ticker)
    cols[1].metric("LAST", f"{snapshot.last:,.2f}")
    cols[2].metric("DATA DATE", pd.Timestamp(snapshot.data_date).strftime("%d %b %Y"))
    if signal_state is not None:
        cols[3].metric("CYCLICAL POSITION", signal_state.position_label)
    else:
        cols[3].metric("CYCLICAL POSITION", "N/A")


def render_market_structure_panel(assessment: TechnicalAssessment) -> None:
    st.markdown("<div class='terminal-subheader'>MARKET STRUCTURE &amp; TREND QUALITY</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='insight-banner'>{html.escape(assessment.current_assessment)}</div>", unsafe_allow_html=True)

    _stat_row(
        [
            ("Trend Quality", f"{assessment.trend_quality.label} ({assessment.trend_quality.score}/100)"),
            ("Swing Structure", assessment.trend_quality.swing_structure.sequence.title()),
            ("MA Alignment", assessment.trend_quality.ma_alignment.title()),
            ("Risk Level", assessment.risk_read.level),
        ]
    )

    st.markdown("<b>Supporting evidence</b>", unsafe_allow_html=True)
    st.markdown(
        "<ul class='evidence-list'>" + "".join(f"<li>{html.escape(item)}</li>" for item in assessment.supporting_evidence) + "</ul>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='risk-callout'><b>Risk:</b> {html.escape(assessment.risk)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='invalidation-callout'><b>Invalidation:</b> {html.escape(assessment.invalidation)}</div>", unsafe_allow_html=True)
    st.markdown("<b>Confidence</b>", unsafe_allow_html=True)
    render_confidence_bar(assessment.confidence, assessment.confidence_components)


def render_key_levels_panel(assessment: TechnicalAssessment) -> None:
    st.markdown("<div class='terminal-subheader'>KEY LEVELS</div>", unsafe_allow_html=True)
    snapshot = assessment.snapshot
    support_text = f"{snapshot.support_low:,.2f} – {snapshot.support_high:,.2f}" if snapshot.support_low else "N/A"
    support_distance = f"{snapshot.distance_support_pct:+.2f}%" if snapshot.distance_support_pct is not None else "N/A"
    resistance_text = f"{snapshot.resistance_low:,.2f} – {snapshot.resistance_high:,.2f}" if snapshot.resistance_low else "N/A"
    resistance_distance = f"{snapshot.distance_resistance_pct:+.2f}%" if snapshot.distance_resistance_pct is not None else "N/A"
    _stat_row(
        [
            ("Nearest Support", support_text),
            ("Distance to Support", support_distance),
            ("Nearest Resistance", resistance_text),
            ("Distance to Resistance", resistance_distance),
        ]
    )
    st.caption(f"Current state: {snapshot.state}")


_STATUS_COLOR = {"DEVELOPING": ORANGE, "CONFIRMED": GREEN, "RETESTED": MUTED}


def render_developing_patterns_panel(
    patterns: list[dict[str, Any]],
    reliabilities: dict[str, PatternReliability],
) -> None:
    st.markdown("<div class='terminal-subheader'>DEVELOPING PATTERNS</div>", unsafe_allow_html=True)
    if not patterns:
        st.info("No pattern currently meets the precision threshold — this is treated as a feature, not a gap: no low-quality candidates are shown.")
        return

    for pattern in patterns:
        color = _STATUS_COLOR.get(pattern["status"], MUTED)
        completion = pattern.get("completion_pct")
        completion_text = f"{completion:.0f}% toward trigger" if completion is not None else "directionally undefined"
        zone = pattern.get("expected_breakout_zone")
        zone_text = f"{zone[0]:,.2f} – {zone[1]:,.2f}" if zone else "N/A"
        invalidation = pattern.get("invalidation")
        invalidation_text = f"{invalidation:,.2f}" if invalidation is not None else "N/A"
        reliability = reliabilities.get(pattern["name"])

        with st.container(border=True):
            st.markdown(
                f"<div class='pattern-card-title'>{html.escape(pattern['name'])}"
                f"<span style='color:{color}'>{html.escape(pattern['status'])}</span></div>"
                f"<div class='pattern-card-meta'>{html.escape(pattern['category'])} · {html.escape(pattern['direction'])} · {completion_text}</div>",
                unsafe_allow_html=True,
            )
            _stat_row(
                [
                    ("Confidence", f"{pattern['confidence']}/100"),
                    ("Expected Breakout Zone", zone_text),
                    ("Invalidation Level", invalidation_text),
                ]
            )
            st.caption(pattern.get("notes") or "No additional notes.")
            if reliability is None:
                pass
            elif reliability.favorable_rate is None:
                st.caption(f"Historical reliability: {reliability.note} (sample size {reliability.sample_size}).")
            else:
                st.caption(
                    f"Historical reliability on this ticker: {reliability.favorable_rate:.0%} of {reliability.sample_size} prior occurrences "
                    f"moved favorably over the next {reliability.horizon_bars} bars (median return {reliability.median_forward_return_pct:+.1f}%)."
                )


def render_momentum_volatility_panel(assessment: TechnicalAssessment) -> None:
    st.markdown("<div class='terminal-subheader'>MOMENTUM &amp; VOLATILITY</div>", unsafe_allow_html=True)
    snapshot = assessment.snapshot
    risk = assessment.risk_read
    volume_setups = [s for s in snapshot.setups if "volume" in s.lower()]
    _stat_row(
        [
            ("RSI", f"{snapshot.rsi:.1f}" if snapshot.rsi is not None else "N/A"),
            ("Volatility Regime", risk.volatility_regime),
            ("ATR % of Price", f"{risk.atr_pct:.2f}%" if pd.notna(risk.atr_pct) else "N/A"),
            ("Volume Confirmation", volume_setups[0] if volume_setups else "No confirmation signal"),
        ]
    )
    divergence_setups = [s for s in snapshot.setups if "divergence" in s.lower()]
    if divergence_setups:
        st.caption(" · ".join(divergence_setups))


def render_multi_timeframe_panel(alignment: MultiTimeframeAlignment) -> None:
    st.markdown("<div class='terminal-subheader'>MULTI-TIMEFRAME ALIGNMENT</div>", unsafe_allow_html=True)
    if not alignment.reads:
        st.info(alignment.summary)
        return
    st.markdown(f"<div class='insight-banner'>{html.escape(alignment.summary)}</div>", unsafe_allow_html=True)
    chips = "".join(
        f"<div class='timeframe-chip'><b>{html.escape(read.timeframe.title())}</b><br>{html.escape(read.direction.split(' (')[0].title())} "
        f"({read.trend_quality.score}/100)</div>"
        for read in alignment.reads
    )
    st.markdown(f"<div class='timeframe-row'>{chips}</div>", unsafe_allow_html=True)


def render_cyclical_position_panel(
    signal_state: TacticalSignalState,
    hierarchy: HierarchyAssessment,
    cross_check: CrossCheckRead | None,
) -> None:
    st.markdown("<div class='terminal-subheader'>CYCLICAL POSITION</div>", unsafe_allow_html=True)
    signal_color = GREEN if signal_state.current_position == "LONG" else RED if signal_state.current_position == "SHORT" else ORANGE
    st.markdown(
        f"<div class='signal-box' style='border-left-color:{signal_color}'>"
        f"<b style='color:{signal_color};font-size:1.1rem'>{html.escape(signal_state.position_label)}</b><br>"
        f"Status: <b>{html.escape(signal_state.status)}</b> · Alignment: <b>{html.escape(hierarchy.alignment)}</b><br>"
        f"<span class='small-note'>{html.escape(signal_state.weekly_phase)}</span></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    cols[0].markdown(f"<div class='risk-callout'><b>Next trigger:</b> {html.escape(signal_state.next_trigger)}</div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='invalidation-callout'><b>Invalidation:</b> {html.escape(signal_state.invalidation_condition)}</div>", unsafe_allow_html=True)

    if cross_check is not None:
        chip_class = {"CONFIRMS": "is-good", "DIVERGES": "is-critical"}.get(cross_check.agreement, "is-neutral")
        st.markdown(
            f"<div class='status-chip {chip_class}'>TECHNICAL × CYCLICAL: {html.escape(cross_check.agreement)}</div>"
            f"<div class='small-note' style='margin-top:.4rem'>{html.escape(cross_check.summary)}</div>",
            unsafe_allow_html=True,
        )


_POSTURE_STYLE = {
    "WATCH BREAKOUT": "is-warning",
    "CONTINUE MONITORING": "is-good",
    "WAIT FOR CONFIRMATION": "is-info",
    "REDUCE EXPOSURE / REASSESS": "is-critical",
}


def determine_posture(assessment: TechnicalAssessment, patterns: list[dict[str, Any]], cross_check: CrossCheckRead | None) -> str:
    """A single recommended posture derived from what's already computed — never a
    trading instruction, just the natural next research step."""
    near_breakout = any((p.get("completion_pct") or 0) >= 60 and p["status"] == "DEVELOPING" for p in patterns)
    if near_breakout:
        return "WATCH BREAKOUT"
    if cross_check is not None and cross_check.agreement == "DIVERGES":
        return "WAIT FOR CONFIRMATION"
    if assessment.risk_read.level == "ELEVATED" and assessment.trend_quality.label in {"WEAK", "NO CLEAR TREND"}:
        return "REDUCE EXPOSURE / REASSESS"
    return "CONTINUE MONITORING"


def _navigate_to_build_strategy(ticker: str, company: str, assessment: TechnicalAssessment) -> None:
    """Prefill the AI Strategy Lab prompt and navigate there if the page is registered."""
    pages = st.session_state.get("_pages", {})
    st.session_state["pending_ai_message"] = (
        f"Build a strategy idea around {ticker} ({company}), using its current technical structure "
        f"({assessment.trend_quality.label.lower()}-quality {assessment.current_assessment.split(' is ')[-1]}) as context."
    )
    if "AI Strategy Lab" in pages:
        st.switch_page(pages["AI Strategy Lab"])


def _navigate_to_compare_sector() -> None:
    """Navigate to the Opportunities page (sector leadership) if it is registered."""
    pages = st.session_state.get("_pages", {})
    if "Opportunities" in pages:
        st.switch_page(pages["Opportunities"])


def render_summary_and_actions(
    ticker: str,
    company: str,
    assessment: TechnicalAssessment,
    alignment: MultiTimeframeAlignment,
    cross_check: CrossCheckRead | None,
    patterns: list[dict[str, Any]],
) -> None:
    st.markdown("<div class='terminal-subheader'>TECHNICAL SUMMARY</div>", unsafe_allow_html=True)
    posture = determine_posture(assessment, patterns, cross_check)
    summary_parts = [assessment.current_assessment, alignment.summary]
    if cross_check is not None:
        summary_parts.append(cross_check.summary)
    st.markdown(f"<div class='insight-banner'>{html.escape(' '.join(summary_parts))}</div>", unsafe_allow_html=True)

    style = _POSTURE_STYLE.get(posture, "is-neutral")
    st.markdown(f"<span class='status-chip {style}'>RECOMMENDED POSTURE: {html.escape(posture)}</span>", unsafe_allow_html=True)

    action_cols = st.columns(2)
    if action_cols[0].button("Build Strategy", key="research_build_strategy", width="stretch", type="primary"):
        _navigate_to_build_strategy(ticker, company, assessment)
    if action_cols[1].button("Compare with Sector", key="research_compare_sector", width="stretch"):
        _navigate_to_compare_sector()
