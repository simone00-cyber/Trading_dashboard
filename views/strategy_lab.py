from __future__ import annotations
from typing import Dict
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analysis.backtest import run_documented_backtest
from analysis.research import build_research_report
from analysis.cyclical.formulas import FORMULA_REGISTRY
from charts.common import apply_terminal_layout
from config.theme import GREEN, RED, ORANGE, BLUE
from caruso_analysis import RESAMPLE_RULES, calculate_composite_momentum, download_prices, prepare_technical_prices, resample_ohlc


def _load_frames(ticker: str, period: str) -> Dict[str, pd.DataFrame]:
    daily_raw = download_prices(ticker, period)
    daily = prepare_technical_prices(daily_raw)
    frames: Dict[str, pd.DataFrame] = {}
    for timeframe, rule in RESAMPLE_RULES.items():
        ohlc = resample_ohlc(daily, rule)
        frames[timeframe] = calculate_composite_momentum(ohlc)
    return frames


def _equity_chart(frame: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame.index, y=frame["Equity"], name="Documented strategy", line=dict(width=2.2, color=ORANGE)))
    fig.add_trace(go.Scatter(x=frame.index, y=frame["BenchmarkEquity"], name="Buy & Hold", line=dict(width=1.5, color=BLUE)))
    fig.update_layout(title=f"{ticker} // EQUITY LINE", yaxis_title="Growth of 1.00")
    return apply_terminal_layout(fig, 460)


def _drawdown_chart(frame: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=frame.index, y=frame["Drawdown"] * 100.0, fill="tozeroy", name="Drawdown", line=dict(width=1.4, color=RED)))
    fig.update_layout(title=f"{ticker} // STRATEGY DRAWDOWN", yaxis_title="%")
    return apply_terminal_layout(fig, 320)


def _format_pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def render_strategy_lab() -> None:
    st.markdown("<div class='terminal-header'>STRATEGY LAB // DOCUMENTED CYCLICAL MATRIX</div>", unsafe_allow_html=True)
    st.caption("Signals, Active Position, performance, equity line, drawdown and Buy & Hold use dividend- and split-adjusted prices when Yahoo Finance provides them. Price charts and displayed entry/exit levels remain actual market prices.")
    st.caption("FINAL BUILD v8.4 // Adjusted technical engine + actual-price display + Drawdown Analysis")
    st.caption("Research environment for the public matrix only. The proprietary Investitore Disciplinato algorithm, proprietary stops and undisclosed price levels are not used.")

    controls = st.columns([1.2, 1, 1, 1.3, 1])
    ticker = controls[0].text_input("Ticker Yahoo Finance", value="ENI.MI", key="strategy_ticker").strip().upper()
    period = controls[1].selectbox("Storico", ["max", "20y", "15y", "10y"], index=0, key="strategy_period")
    mode_label = controls[2].selectbox("Direction mode", ["Long only", "Long / Short"])
    tp_label = controls[3].selectbox(
        "TAKE PROFIT policy",
        ["Signal only", "Full exit scenario", "Partial exit research"],
        help="Signal only makes no undisclosed sizing assumption. Full and partial exits are research scenarios.",
    )
    cost_bps = controls[4].number_input("Cost (bps)", min_value=0.0, max_value=100.0, value=5.0, step=1.0)
    mode = "LONG_ONLY" if mode_label == "Long only" else "LONG_SHORT"
    take_profit_policy = {
        "Signal only": "SIGNAL_ONLY",
        "Full exit scenario": "FULL_EXIT",
        "Partial exit research": "PARTIAL_EXIT",
    }[tp_label]
    partial_exit_fraction = 0.50
    if take_profit_policy == "PARTIAL_EXIT":
        partial_exit_fraction = st.slider(
            "Partial monetisation assumption",
            min_value=0.10, max_value=0.90, value=0.50, step=0.05,
            format="%.0f%%",
            help="This percentage is not published by the source and is used only as a research parameter.",
        )
    st.button("RUN BACKTEST", type="primary", width="stretch")

    try:
        with st.spinner(f"Reconstructing completed-bar signals for {ticker}..."):
            frames = _load_frames(ticker, period)
            result = run_documented_backtest(
                frames, mode=mode, cost_bps=float(cost_bps),
                take_profit_policy=take_profit_policy,
                partial_exit_fraction=float(partial_exit_fraction),
            )
    except Exception as error:
        st.error(f"Backtest unavailable: {error}")
        return

    metrics = result.metrics
    st.info(f"Execution policy: {result.policy_label} — {result.policy_provenance}")
    top = st.columns(6)
    top[0].metric("CAGR", _format_pct(metrics.get("CAGR", 0.0)))
    top[1].metric("MAX DRAWDOWN", _format_pct(metrics.get("Max Drawdown", 0.0)))
    top[2].metric("SHARPE", f"{metrics.get('Sharpe (rf=0)', 0.0):.2f}")
    top[3].metric("TRADES", f"{metrics.get('Trades', 0)}")
    top[4].metric("WIN RATE", _format_pct(metrics.get("Win Rate", 0.0)))
    top[5].metric("TIME INVESTED", _format_pct(metrics.get("Time Invested", 0.0)))

    research = build_research_report(result.trades, result.weekly)
    tabs = st.tabs(["EQUITY LINE", "SIGNAL HISTORY", "TRADES", "DIAGNOSTICS", "AUDIT", "RESEARCH", "METHODOLOGY", "MATRIX EXPLORER"])
    with tabs[0]:
        st.plotly_chart(_equity_chart(result.weekly, ticker), width="stretch")
        st.plotly_chart(_drawdown_chart(result.weekly, ticker), width="stretch")
        rows = [
            {"METRIC": "Total return", "VALUE": _format_pct(metrics.get("Total Return", 0.0))},
            {"METRIC": "CAGR", "VALUE": _format_pct(metrics.get("CAGR", 0.0))},
            {"METRIC": "Buy & Hold CAGR", "VALUE": _format_pct(metrics.get("Buy & Hold CAGR", 0.0))},
            {"METRIC": "Annualized volatility", "VALUE": _format_pct(metrics.get("Annualized Volatility", 0.0))},
            {"METRIC": "Sharpe (rf=0)", "VALUE": f"{metrics.get('Sharpe (rf=0)', 0.0):.3f}"},
            {"METRIC": "Max drawdown", "VALUE": _format_pct(metrics.get("Max Drawdown", 0.0))},
            {"METRIC": "Profit factor", "VALUE": f"{metrics.get('Profit Factor', 0.0):.2f}"},
            {"METRIC": "Average trade", "VALUE": _format_pct(metrics.get("Average Trade", 0.0))},
            {"METRIC": "Average bars held", "VALUE": f"{metrics.get('Average Bars Held', 0.0):.1f}"},
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with tabs[1]:
        signal_rows = [{
            "DATE": s.date.strftime("%d/%m/%Y"), "EVENT": s.action, "PRICE": round(s.price, 4),
            "RATING": "●" * s.rating, "QUARTERLY": s.quarterly_direction,
            "MONTHLY": s.monthly_direction, "WEEKLY TURN": s.weekly_turn,
            "WEEKLY PHASE": s.weekly_phase, "WEEKLY CM": round(s.weekly_composite, 2),
        } for s in reversed(result.signals)]
        st.dataframe(pd.DataFrame(signal_rows), width="stretch", hide_index=True)

    with tabs[2]:
        trade_rows = [{
            "SIDE": t.side, "ENTRY": t.entry_date.strftime("%d/%m/%Y"),
            "EXIT": t.exit_date.strftime("%d/%m/%Y"), "ENTRY PRICE": round(t.entry_price, 4),
            "EXIT PRICE": round(t.exit_price, 4), "EXIT REASON": t.exit_reason,
            "RATING": "●" * t.entry_rating, "SIZE": f"{t.size:.0%}", "BARS": t.bars_held,
            "GROSS": _format_pct(t.gross_return), "NET": _format_pct(t.net_return),
        } for t in reversed(result.trades)]
        st.dataframe(pd.DataFrame(trade_rows), width="stretch", hide_index=True)

    with tabs[3]:
        if result.diagnostics.empty:
            st.info("No completed trades in the selected sample.")
        else:
            diagnostic = result.diagnostics.copy()
            diagnostic["ENTRY DATE"] = pd.to_datetime(diagnostic["ENTRY DATE"]).dt.strftime("%d/%m/%Y")
            diagnostic["EXIT DATE"] = pd.to_datetime(diagnostic["EXIT DATE"]).dt.strftime("%d/%m/%Y")
            diagnostic["GROSS RETURN"] = diagnostic["GROSS RETURN"].map(_format_pct)
            diagnostic["NET RETURN"] = diagnostic["NET RETURN"].map(_format_pct)
            diagnostic["ENTRY CM"] = diagnostic["ENTRY CM"].round(2)
            st.dataframe(diagnostic, width="stretch", hide_index=True)
            st.caption("These fields permit later grouping by rating, higher-timeframe alignment, weekly phase and Composite Momentum level without changing the execution rules.")

    with tabs[4]:
        st.markdown("### EXECUTION AUDIT // STATE MACHINE")
        status = "PASS" if result.audit.passed else "FAIL"
        st.metric("CORE EXECUTION AUDIT", status)
        checks = pd.DataFrame(result.audit.checks)
        st.dataframe(checks, width="stretch", hide_index=True)

        transitions = pd.DataFrame([{
            "DATE": row.date.strftime("%d/%m/%Y"),
            "SIGNAL": row.signal,
            "STATE BEFORE": row.state_before,
            "EXPOSURE BEFORE": f"{row.exposure_before:+.0%}",
            "ACTION": row.action_taken,
            "STATE AFTER": row.state_after,
            "EXPOSURE AFTER": f"{row.exposure_after:+.0%}",
            "RATING": "●" * row.signal_rating,
            "PRICE": round(row.signal_price, 4),
            "REASON": row.reason,
        } for row in reversed(result.audit.transitions)])
        st.markdown("#### VISUAL TRADE-ENGINE DEBUGGER")
        st.dataframe(transitions, width="stretch", hide_index=True)
        st.caption("Every matrix event is shown, including TAKE PROFIT signals that occur while the strategy is already FLAT. Such events are retained for traceability but correctly do not create a trade exit.")

    with tabs[5]:
        st.markdown("### RESEARCH LAB // STATISTICAL DIAGNOSTICS")
        st.success("Drawdown Analysis is available in the first tab: DRAWDOWNS")
        st.caption("All groupings are derived from completed trades generated by the documented matrix. Confidence labels and the Research Score are transparent software conventions, not parts of the proprietary methodology.")

        if research.enriched_trades.empty:
            st.info("No completed trades are available for research analysis.")
        else:
            research_tabs = st.tabs(["DRAWDOWNS", "SETUPS", "COMPOSITE", "HEAT MAPS", "HOLDING & EXCURSIONS", "HYPOTHESES"])

            with research_tabs[0]:
                st.markdown("#### DRAWDOWN ANALYSIS // WHERE THE RISK WAS CREATED")
                st.caption("Episodes are identified from the strategy equity curve. Trade attribution uses the peak-to-trough interval and existing trade features; it does not alter signals or execution.")

                episodes = research.drawdown_episodes.copy()
                if episodes.empty:
                    st.info("No drawdown episode is available in the selected sample.")
                else:
                    worst = episodes.iloc[0]
                    dd_cols = st.columns(5)
                    dd_cols[0].metric("WORST DRAWDOWN", _format_pct(float(worst["MAX DRAWDOWN"])))
                    dd_cols[1].metric("START", pd.Timestamp(worst["START"]).strftime("%d/%m/%Y"))
                    dd_cols[2].metric("TROUGH", pd.Timestamp(worst["TROUGH"]).strftime("%d/%m/%Y"))
                    dd_cols[3].metric("WEEKS TO TROUGH", f"{int(worst['WEEKS TO TROUGH'])}")
                    dd_cols[4].metric("TRADES INVOLVED", f"{int(worst['OVERLAPPING TRADES'])}")

                    chart_data = episodes.head(10).sort_values("MAX DRAWDOWN", ascending=False)
                    labels = [f"#{int(rank)} | {pd.Timestamp(date).strftime('%Y-%m')}" for rank, date in zip(chart_data["RANK"], chart_data["START"])]
                    fig = go.Figure(go.Bar(
                        x=chart_data["MAX DRAWDOWN"] * 100.0,
                        y=labels,
                        orientation="h",
                        text=(chart_data["MAX DRAWDOWN"] * 100.0).map(lambda x: f"{x:.1f}%"),
                        textposition="auto",
                        name="Drawdown",
                    ))
                    fig.update_layout(title="TOP 10 DRAWDOWN EPISODES", xaxis_title="Maximum drawdown %", yaxis_title="Episode")
                    st.plotly_chart(apply_terminal_layout(fig, 430), width="stretch")

                    episode_view = episodes.head(20).copy()
                    for column in ["START", "TROUGH", "RECOVERY"]:
                        episode_view[column] = pd.to_datetime(episode_view[column]).dt.strftime("%d/%m/%Y").replace("NaT", "ONGOING")
                    episode_view["MAX DRAWDOWN"] = episode_view["MAX DRAWDOWN"].map(_format_pct)
                    episode_view["LOSING TRADE CONTRIBUTION"] = episode_view["LOSING TRADE CONTRIBUTION"].map(_format_pct)
                    st.dataframe(
                        episode_view[["RANK", "START", "TROUGH", "RECOVERY", "MAX DRAWDOWN", "WEEKS TO TROUGH", "TOTAL WEEKS", "OVERLAPPING TRADES", "DOMINANT LOSS SETUP"]],
                        width="stretch", hide_index=True,
                    )

                    st.markdown("##### EPISODE DRILL-DOWN")
                    episode_rank = st.selectbox(
                        "Drawdown episode",
                        options=episodes["RANK"].astype(int).tolist(),
                        format_func=lambda rank: f"#{rank} — {_format_pct(float(episodes.loc[episodes['RANK'] == rank, 'MAX DRAWDOWN'].iloc[0]))}",
                    )
                    selected_episode = episodes.loc[episodes["RANK"] == episode_rank].iloc[0]
                    linked = research.drawdown_trades
                    linked = linked.loc[linked["EPISODE"] == int(selected_episode["EPISODE"])].copy() if not linked.empty else pd.DataFrame()
                    if linked.empty:
                        st.info("No completed trade overlaps this peak-to-trough interval.")
                    else:
                        linked = linked.sort_values("PNL CONTRIBUTION")
                        linked["ENTRY DATE"] = pd.to_datetime(linked["ENTRY DATE"]).dt.strftime("%d/%m/%Y")
                        linked["EXIT DATE"] = pd.to_datetime(linked["EXIT DATE"]).dt.strftime("%d/%m/%Y")
                        for column in ["NET RETURN", "PNL CONTRIBUTION", "MFE", "MAE"]:
                            linked[column] = linked[column].map(_format_pct)
                        st.dataframe(
                            linked[["SIDE", "ENTRY DATE", "EXIT DATE", "SETUP", "ENTRY RATING", "ENTRY CM", "BARS", "NET RETURN", "PNL CONTRIBUTION", "MFE", "MAE", "EXIT REASON"]],
                            width="stretch", hide_index=True,
                        )

                    st.markdown("##### LOSS ATTRIBUTION")
                    attribution_choice = st.radio(
                        "Group losing-trade contribution by",
                        ["Setup", "Monthly direction", "Entry rating", "Composite zone"],
                        horizontal=True,
                    )
                    attribution_map = {
                        "Setup": (research.loss_attribution_setup, "SETUP"),
                        "Monthly direction": (research.loss_attribution_monthly, "MONTHLY"),
                        "Entry rating": (research.loss_attribution_rating, "ENTRY RATING"),
                        "Composite zone": (research.loss_attribution_composite, "CM ZONE"),
                    }
                    attribution, group_column = attribution_map[attribution_choice]
                    if attribution.empty:
                        st.info("No losing trades are available for attribution.")
                    else:
                        attribution = attribution.copy()
                        fig = go.Figure(go.Bar(
                            x=attribution["LOSS SHARE"] * 100.0,
                            y=attribution[group_column].astype(str),
                            orientation="h",
                            text=(attribution["LOSS SHARE"] * 100.0).map(lambda x: f"{x:.1f}%"),
                            textposition="auto",
                            name="Loss share",
                        ))
                        fig.update_layout(title=f"GROSS LOSS CONTRIBUTION BY {attribution_choice.upper()}", xaxis_title="Share of total losing-trade contribution %", yaxis_title=group_column)
                        st.plotly_chart(apply_terminal_layout(fig, 390), width="stretch")
                        attribution["TOTAL_LOSS"] = attribution["TOTAL_LOSS"].map(lambda x: f"-{x * 100:.2f}%")
                        attribution["AVG_LOSS"] = attribution["AVG_LOSS"].map(lambda x: f"-{x * 100:.2f}%")
                        attribution["WORST_TRADE"] = attribution["WORST_TRADE"].map(_format_pct)
                        attribution["LOSS SHARE"] = attribution["LOSS SHARE"].map(lambda x: f"{x:.1%}")
                        st.dataframe(attribution, width="stretch", hide_index=True)
                        st.caption("Loss share is based on the absolute contribution of losing trade legs. It explains where realised trade losses are concentrated; it is not a causal model and does not include mark-to-market losses from still-open positions.")

            with research_tabs[1]:
                setup = research.setup_summary.copy()
                setup["WIN RATE"] = setup["WIN RATE"].map(_format_pct)
                setup["AVG RETURN"] = setup["AVG RETURN"].map(_format_pct)
                setup["MEDIAN RETURN"] = setup["MEDIAN RETURN"].map(_format_pct)
                setup["PROFIT FACTOR"] = setup["PROFIT FACTOR"].replace(float("inf"), pd.NA).round(2)
                setup["SCORE"] = setup["RESEARCH SCORE"].map(lambda x: "★" * int(x) + "☆" * (5 - int(x)))
                st.dataframe(setup.drop(columns=["RESEARCH SCORE"]), width="stretch", hide_index=True)
                st.caption("The score rewards sample size, positive expectancy and profit factor. It does not create or modify signals.")

            with research_tabs[2]:
                cm = research.composite_summary.copy()
                cm["WIN RATE"] = cm["WIN RATE"].map(_format_pct)
                cm["AVG RETURN"] = cm["AVG RETURN"].map(_format_pct)
                cm["MEDIAN RETURN"] = cm["MEDIAN RETURN"].map(_format_pct)
                cm["PROFIT FACTOR"] = cm["PROFIT FACTOR"].replace(float("inf"), pd.NA).round(2)
                cm["SCORE"] = cm["RESEARCH SCORE"].map(lambda x: "★" * int(x) + "☆" * (5 - int(x)))
                st.dataframe(cm.drop(columns=["RESEARCH SCORE"]), width="stretch", hide_index=True)

            with research_tabs[3]:
                metric = st.radio("Heat-map metric", ["Average return", "Win rate", "Trade count"], horizontal=True)
                matrix = research.heatmap_average if metric == "Average return" else research.heatmap_win_rate if metric == "Win rate" else research.heatmap_count
                if matrix.empty:
                    st.info("Insufficient data for the heat map.")
                else:
                    values = matrix * 100.0 if metric != "Trade count" else matrix
                    text = values.round(1).astype(str)
                    if metric != "Trade count":
                        text = text + "%"
                    fig = go.Figure(go.Heatmap(z=values.values, x=values.columns, y=values.index, text=text.values, texttemplate="%{text}", colorbar_title=metric))
                    fig.update_layout(title=f"QUARTERLY DIRECTION × WEEKLY ENTRY PHASE // {metric.upper()}", xaxis_title="Weekly phase", yaxis_title="Quarterly direction")
                    st.plotly_chart(apply_terminal_layout(fig, 430), width="stretch")
                    st.dataframe(matrix, width="stretch")

            with research_tabs[4]:
                hold = research.holding_summary.copy()
                hold["WIN RATE"] = hold["WIN RATE"].map(_format_pct)
                hold["AVG RETURN"] = hold["AVG RETURN"].map(_format_pct)
                hold["MEDIAN RETURN"] = hold["MEDIAN RETURN"].map(_format_pct)
                hold["PROFIT FACTOR"] = hold["PROFIT FACTOR"].replace(float("inf"), pd.NA).round(2)
                hold["SCORE"] = hold["RESEARCH SCORE"].map(lambda x: "★" * int(x) + "☆" * (5 - int(x)))
                st.dataframe(hold.drop(columns=["RESEARCH SCORE"]), width="stretch", hide_index=True)

                enriched = research.enriched_trades.copy()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=enriched["BARS"], y=enriched["NET RETURN"] * 100.0, mode="markers", name="Trades", text=enriched["SIDE"]))
                fig.update_layout(title="HOLDING PERIOD VS NET RETURN", xaxis_title="Weekly bars", yaxis_title="Net return %")
                st.plotly_chart(apply_terminal_layout(fig, 390), width="stretch")

                excursions = enriched[["SIDE", "ENTRY DATE", "EXIT DATE", "NET RETURN", "MFE", "MAE", "BARS"]].copy()
                for column in ["NET RETURN", "MFE", "MAE"]:
                    excursions[column] = excursions[column].map(_format_pct)
                excursions["ENTRY DATE"] = pd.to_datetime(excursions["ENTRY DATE"]).dt.strftime("%d/%m/%Y")
                excursions["EXIT DATE"] = pd.to_datetime(excursions["EXIT DATE"]).dt.strftime("%d/%m/%Y")
                st.dataframe(excursions.sort_values("ENTRY DATE", ascending=False), width="stretch", hide_index=True)
                st.caption("MFE and MAE are calculated from weekly closes between entry and exit; intraperiod highs and lows are not used.")

            with research_tabs[5]:
                hypotheses = research.hypotheses.copy()
                for column in ["TEST AVG", "CONTROL AVG", "DIFFERENCE"]:
                    hypotheses[column] = hypotheses[column].map(lambda x: _format_pct(x) if pd.notna(x) else "N/A")
                st.dataframe(hypotheses, width="stretch", hide_index=True)
                st.caption("A hypothesis is labelled SUPPORTED only when both groups contain at least 10 observations and the test group's average return is higher. This is descriptive comparison, not a statistical significance test.")

    with tabs[6]:
        st.markdown("### PUBLIC FORMULAS USED BY THE ENGINE")
        st.dataframe(pd.DataFrame(FORMULA_REGISTRY), width="stretch", hide_index=True)
        st.markdown("""
**Implemented and testable**

- KEY, XTL and Composite Momentum from the available published formulas.
- Quarterly/monthly direction and weekly turns.
- BUY, SELL SHORT and TAKE PROFIT events from the public 12-case matrix.
- Execution at the completed weekly close; the resulting position affects the next weekly return.
- Configurable transaction costs and comparison with Buy & Hold.
- Performance valuation includes cash dividends and stock splits through Yahoo Finance adjusted close when available; visible price charts remain unadjusted market prices.
- Separation between signal generation and execution policy.
- TAKE PROFIT as a management instruction in `Signal only` mode.
- Full and partial liquidation as explicitly labelled research scenarios.

**Money-management evidence used**

- Partial monetisation of profitable positions is documented.
- The source does not publish one universal liquidation percentage.
- Therefore the default policy does not alter exposure on TAKE PROFIT.
- Any partial percentage selected by the user is a research assumption, not a proprietary formula.

**Explicitly not implemented**

- Investitore Disciplinato.
- Proprietary regime-switching levels, stops or future trigger prices.
- Proprietary stop levels and undisclosed volatility calibration.
- Automatic pyramiding or portfolio allocation beyond published high-level principles.
- A claim that any research execution scenario replicates the proprietary system.

`Long only` and `Long / Short` govern direction. TAKE PROFIT is controlled independently by an execution policy. This keeps the published signal logic separate from position sizing and money management.
""")
    with tabs[7]:
        st.markdown("### MATRIX EXPLORER // WEEK-BY-WEEK DECISION TIMELINE")
        st.caption("This view reconstructs the inputs and output of the public 12-case matrix on every completed weekly bar. It explains decisions; it does not execute trades. Combinations absent from the published table remain explicitly NOT DEFINED.")
        matrix = result.matrix_timeline.copy() if result.matrix_timeline is not None else pd.DataFrame()
        if matrix.empty:
            st.info("Matrix timeline unavailable for the selected sample.")
        else:
            event_filter = st.radio("Timeline view", ["All weekly states", "New instruction changes only", "Documented cases only"], horizontal=True)
            shown = matrix.copy()
            if event_filter == "New instruction changes only":
                shown = shown[shown["NEW EVENT"]]
            elif event_filter == "Documented cases only":
                shown = shown[shown["INSTRUCTION"] != "NOT DEFINED"]

            summary_cols = st.columns(5)
            latest = matrix.iloc[-1]
            summary_cols[0].metric("CURRENT INSTRUCTION", str(latest["INSTRUCTION"]))
            summary_cols[1].metric("DECISION TYPE", str(latest["TYPE"]))
            summary_cols[2].metric("STABILITY", f"{int(latest['STABILITY WEEKS'])} weeks")
            summary_cols[3].metric("RATING", f"{int(latest['RATING'])}/4")
            summary_cols[4].metric("DEFINED COVERAGE", f"{(matrix['INSTRUCTION'] != 'NOT DEFINED').mean():.1%}")

            display = shown.copy().sort_values("DATE", ascending=False)
            display["DATE"] = pd.to_datetime(display["DATE"]).dt.strftime("%d/%m/%Y")
            display["PRICE"] = display["PRICE"].round(4)
            display["COMPOSITE"] = display["COMPOSITE"].round(2)
            display["RATING"] = display["RATING"].map(lambda x: "●" * int(x) if int(x) > 0 else "—")
            display["NEW EVENT"] = display["NEW EVENT"].map(lambda x: "YES" if x else "NO")
            st.dataframe(display, width="stretch", hide_index=True)

            st.markdown("#### LATEST DECISION // WHY")
            st.code(str(latest["WHY"]), language=None)
            st.caption(f"Provenance: {latest['PROVENANCE']}. A repeated instruction is a persistent matrix state, not automatically a new trade order.")

            transition_counts = matrix[matrix["NEW EVENT"]]["INSTRUCTION"].value_counts().rename_axis("INSTRUCTION").reset_index(name="NEW EVENTS")
            state_counts = matrix["INSTRUCTION"].value_counts().rename_axis("INSTRUCTION").reset_index(name="WEEKLY STATES")
            counts = transition_counts.merge(state_counts, on="INSTRUCTION", how="outer").fillna(0)
            st.markdown("#### STATE FREQUENCY VS NEW EVENTS")
            st.dataframe(counts, width="stretch", hide_index=True)
            st.caption("This distinction prevents a persistent TAKE PROFIT state from being counted as a fresh execution instruction every week.")

