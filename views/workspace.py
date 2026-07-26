from __future__ import annotations

import html
import streamlit as st


_WORKSPACE_MODULES = ["TECHNICAL ANALYSIS", "CYCLICAL ANALYSIS", "RELATIVE STRENGTH"]


def _request_workspace_module() -> None:
    st.session_state["workspace_loading"] = True


def _loading_overlay(title: str, detail: str):
    placeholder = st.empty()
    placeholder.markdown(
        f"""
        <div class="terminal-loading-overlay">
          <div class="terminal-loading-panel">
            <div class="terminal-loading-kicker">CYCLICAL GLOBAL MACRO TERMINAL</div>
            <div class="terminal-loading-title">{html.escape(title)}</div>
            <div class="terminal-loading-detail">{html.escape(detail)}</div>
            <div class="terminal-loading-track"><div class="terminal-loading-bar"></div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return placeholder


def render_asset_workspace() -> None:
    st.markdown("<div class='terminal-header'>ASSET WORKSPACE // COMPLETE SECURITY RESEARCH</div>", unsafe_allow_html=True)
    st.caption(
        "One ticker controls the complete Technical Analysis, Cyclical Analysis and Relative Strength modules. "
        "Only the active module is executed, reducing network calls and calculation time without removing functionality."
    )

    st.session_state.setdefault("workspace_ticker", "AAPL")
    st.session_state.setdefault("workspace_module", "TECHNICAL ANALYSIS")
    st.session_state.setdefault("workspace_loading", False)

    with st.form("workspace_asset_form", clear_on_submit=False):
        controls = st.columns([2.4, 1.0, 2.6])
        requested = controls[0].text_input(
            "YAHOO FINANCE TICKER",
            value=st.session_state.workspace_ticker,
            placeholder="AAPL, ENI.MI, ASML.AS, BTC-USD",
        ).strip().upper()
        load = controls[1].form_submit_button("LOAD ASSET", type="primary", width="stretch")
        controls[2].caption(
            "The ticker is shared by every research module. Cached market data is reused for one hour; "
            "changing controls no longer reloads inactive modules."
        )

    if load and requested and requested != st.session_state.workspace_ticker:
        st.session_state.workspace_ticker = requested
        st.session_state.workspace_loading = True
        st.rerun()

    ticker = st.session_state.workspace_ticker
    st.markdown(f"## {ticker}")

    active_module = st.segmented_control(
        "WORKSPACE MODULE",
        _WORKSPACE_MODULES,
        default=st.session_state.workspace_module,
        key="workspace_module",
        on_change=_request_workspace_module,
        width="stretch",
    ) or "TECHNICAL ANALYSIS"

    overlay = None
    if st.session_state.get("workspace_loading", False):
        overlay = _loading_overlay(
            f"LOADING {active_module}",
            f"Preparing {ticker} and restoring cached research data...",
        )

    try:
        if active_module == "TECHNICAL ANALYSIS":
            from views.technical import render_technical_analysis
            render_technical_analysis(ticker_override=ticker, embedded=True)
        elif active_module == "CYCLICAL ANALYSIS":
            from views.security import render_security_report
            render_security_report(ticker_override=ticker, embedded=True)
        else:
            from views.screener import render_relative_strength_lab
            render_relative_strength_lab(initial_ticker=ticker)
    finally:
        if overlay is not None:
            overlay.empty()
        st.session_state.workspace_loading = False
