from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from screener.engine import (
    PERFORMANCE_WINDOWS,
    ScreenerResult,
    analyse_universe,
    build_sector_performance,
    sort_by_methodology,
)
from screener.universes import UNIVERSES, load_universe


SCREEN_PERIOD = "max"


@st.cache_data(ttl=86400, show_spinner=False)
def _constituents(name: str) -> tuple[pd.DataFrame, str]:
    return load_universe(name)


@st.cache_data(ttl=3600, show_spinner=False)
def _run_screen(name: str) -> tuple[ScreenerResult, str, int]:
    constituents, source = _constituents(name)
    result = analyse_universe(constituents, period=SCREEN_PERIOD)
    return result, source, len(constituents)


def _fmt_table(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    numeric = [
        "Last",
        "1D %",
        "1W %",
        "1M %",
        "1Y %",
        "Quarterly CM",
        "Monthly CM",
        "Weekly CM",
        "Performance",
        "Median",
        "Best",
        "Worst",
    ]
    for column in numeric:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(2)
    return result


def _methodology_columns() -> list[str]:
    return [
        "Order",
        "Ticker",
        "Company",
        "Sector",
        "Matrix Action",
        "Rating Visual",
        "Rating",
        "Quarterly Trend",
        "Monthly Trend",
        "Weekly Turn",
        "Quarterly CM",
        "Monthly CM",
        "Weekly CM",
        "Last",
        "Data Date",
    ]


def _performance_columns(performance_column: str) -> list[str]:
    return ["Ticker", "Company", "Sector", performance_column, "Last"]


def _action_badge_counts(rows: pd.DataFrame) -> dict[str, int]:
    return {
        "BUY": int((rows["Matrix Action"] == "BUY").sum()),
        "TAKE PROFIT": int((rows["Matrix Action"] == "TAKE PROFIT").sum()),
        "SELL SHORT": int((rows["Matrix Action"] == "SELL SHORT").sum()),
        "NO NEW JUNCTION": int((rows["Matrix Action"] == "NESSUNA NUOVA GIUNTURA").sum()),
    }


def _render_methodology_screener(rows: pd.DataFrame, universe_size: int) -> None:
    counts = _action_badge_counts(rows)
    cards = st.columns(6)
    cards[0].metric("CONSTITUENTS", universe_size)
    cards[1].metric("ANALYSED", len(rows))
    cards[2].metric("BUY", counts["BUY"])
    cards[3].metric("TAKE PROFIT", counts["TAKE PROFIT"])
    cards[4].metric("SELL SHORT", counts["SELL SHORT"])
    cards[5].metric("NO NEW JUNCTION", counts["NO NEW JUNCTION"])

    st.markdown("<div class='terminal-subheader'>PUBLIC MATRIX SIGNALS</div>", unsafe_allow_html=True)
    st.caption(
        "Signals and Reward/Risk ratings are generated directly from the implemented public "
        "quarterly/monthly/weekly matrix. No synthetic score or weighted ranking is used."
    )

    controls = st.columns([1.15, 1.25, 1.2, 1])
    sectors = ["ALL"] + sorted(rows["Sector"].dropna().astype(str).unique())
    sector = controls[0].selectbox("SECTOR", sectors, key="method_sector")

    actions = ["BUY", "TAKE PROFIT", "SELL SHORT", "NESSUNA NUOVA GIUNTURA"]
    selected_actions = controls[1].multiselect(
        "MATRIX ACTION",
        actions,
        default=actions,
        format_func=lambda value: "NO NEW JUNCTION" if value == "NESSUNA NUOVA GIUNTURA" else value,
    )
    min_rating = controls[2].selectbox("MIN REWARD/RISK", [0, 1, 2, 3, 4], index=0)
    only_latest_signal = controls[3].toggle("SIGNALS ONLY", value=False)

    filtered = rows.copy()
    if sector != "ALL":
        filtered = filtered[filtered["Sector"].astype(str) == sector]
    if selected_actions:
        filtered = filtered[filtered["Matrix Action"].isin(selected_actions)]
    filtered = filtered[filtered["Rating"] >= min_rating]
    if only_latest_signal:
        filtered = filtered[filtered["Matrix Action"] != "NESSUNA NUOVA GIUNTURA"]

    filtered = sort_by_methodology(filtered)
    st.caption(f"{len(filtered)} securities match the active methodology filters.")
    st.dataframe(
        _fmt_table(filtered[_methodology_columns()]),
        use_container_width=True,
        hide_index=True,
        height=690,
        column_config={
            "Rating Visual": st.column_config.TextColumn("R/R"),
            "Rating": st.column_config.NumberColumn("R/R Level", format="%d"),
            "Matrix Action": st.column_config.TextColumn("Action"),
        },
    )
    st.download_button(
        "DOWNLOAD METHODOLOGY SCREEN",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="methodology_screener.csv",
        mime="text/csv",
        use_container_width=False,
    )


def _render_sector_ranking(rows: pd.DataFrame) -> None:
    header = st.columns([1.15, 2.3])
    selected_window = header[0].selectbox(
        "PERFORMANCE WINDOW",
        list(PERFORMANCE_WINDOWS),
        index=2,
        key="sector_window",
    )
    performance_column = PERFORMANCE_WINDOWS[selected_window][0]
    header[1].markdown(
        "<div class='small-note'><br>Sector performance is the equal-weight average adjusted-price return "
        "of the analysed constituents in the selected index.</div>",
        unsafe_allow_html=True,
    )

    sectors = build_sector_performance(rows, performance_column)
    if sectors.empty:
        st.info("Sector ranking unavailable for the selected period.")
        return

    best = sectors.iloc[0]
    worst = sectors.iloc[-1]
    cards = st.columns(4)
    cards[0].metric("LEADING SECTOR", str(best["Sector"]), f"{best['Performance']:+.2f}%")
    cards[1].metric("LAGGING SECTOR", str(worst["Sector"]), f"{worst['Performance']:+.2f}%")
    cards[2].metric("SECTORS", len(sectors))
    cards[3].metric("WINDOW", selected_window)

    left, right = st.columns([1.05, 1.35])
    with left:
        table = sectors.rename(
            columns={
                "Performance": f"AVG {selected_window} %",
                "Median": f"MEDIAN {selected_window} %",
                "Best": "BEST STOCK %",
                "Worst": "WORST STOCK %",
            }
        )
        st.dataframe(_fmt_table(table), use_container_width=True, hide_index=True, height=610)

    with right:
        chart = sectors.sort_values("Performance", ascending=True)
        fig = px.bar(
            chart,
            x="Performance",
            y="Sector",
            orientation="h",
            text="Performance",
            hover_data=["Stocks", "Median", "Best", "Worst"],
            labels={"Performance": f"{selected_window} return (%)", "Sector": ""},
        )
        fig.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
        fig.update_layout(
            template="plotly_dark",
            height=610,
            margin=dict(l=10, r=35, t=15, b=10),
            xaxis_title=f"Equal-weight {selected_window} performance (%)",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_top_flop(rows: pd.DataFrame) -> None:
    controls = st.columns([1.1, 1.35, 1, 1.6])
    selected_window = controls[0].selectbox(
        "PERFORMANCE WINDOW",
        list(PERFORMANCE_WINDOWS),
        index=2,
        key="top_flop_window",
    )
    performance_column = PERFORMANCE_WINDOWS[selected_window][0]

    sectors = ["ALL SECTORS"] + sorted(rows["Sector"].dropna().astype(str).unique())
    selected_sector = controls[1].selectbox("SECTOR", sectors, key="top_flop_sector")
    count = controls[2].selectbox("SECURITIES PER SIDE", [5, 10, 15, 20], index=0)
    controls[3].markdown(
        "<div class='small-note'><br>Top and Flop are based exclusively on adjusted-price performance, "
        "not on the cyclical matrix.</div>",
        unsafe_allow_html=True,
    )

    filtered = rows.dropna(subset=[performance_column]).copy()
    if selected_sector != "ALL SECTORS":
        filtered = filtered[filtered["Sector"].astype(str) == selected_sector]

    if filtered.empty:
        st.info("No securities are available for the selected filters.")
        return

    top = filtered.nlargest(count, performance_column)
    flop = filtered.nsmallest(count, performance_column)

    left, right = st.columns(2)
    with left:
        st.markdown("<div class='terminal-subheader'>TOP PERFORMERS</div>", unsafe_allow_html=True)
        top_display = top[_performance_columns(performance_column)].copy()
        top_display.insert(0, "Rank", range(1, len(top_display) + 1))
        st.dataframe(
            _fmt_table(top_display),
            use_container_width=True,
            hide_index=True,
            height=510,
            column_config={performance_column: st.column_config.NumberColumn(selected_window, format="%+.2f%%")},
        )

    with right:
        st.markdown("<div class='terminal-subheader'>FLOP PERFORMERS</div>", unsafe_allow_html=True)
        flop_display = flop[_performance_columns(performance_column)].copy()
        flop_display.insert(0, "Rank", range(1, len(flop_display) + 1))
        st.dataframe(
            _fmt_table(flop_display),
            use_container_width=True,
            hide_index=True,
            height=510,
            column_config={performance_column: st.column_config.NumberColumn(selected_window, format="%+.2f%%")},
        )

    chart_rows = pd.concat(
        [
            top.assign(Group="TOP"),
            flop.assign(Group="FLOP"),
        ],
        ignore_index=True,
    ).sort_values(performance_column)
    fig = px.bar(
        chart_rows,
        x=performance_column,
        y="Ticker",
        orientation="h",
        text=performance_column,
        hover_data=["Company", "Sector"],
        labels={performance_column: f"{selected_window} return (%)", "Ticker": ""},
    )
    fig.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
    fig.update_layout(
        template="plotly_dark",
        height=max(430, 32 * len(chart_rows)),
        margin=dict(l=10, r=35, t=20, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_market_screener() -> None:
    st.markdown(
        "<div class='terminal-header'>MARKET SCREENER // MATRIX SIGNALS // SECTOR PERFORMANCE</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Choose an index universe. The Screener follows the implemented public cyclical matrix; "
        "Sector Ranking and Top & Flop use adjusted-price performance over the selected horizon."
    )

    controls = st.columns([1.25, 1, 2.75])
    universe = controls[0].selectbox("INDEX UNIVERSE", list(UNIVERSES), index=0)
    refresh = controls[1].button("REFRESH", type="primary", use_container_width=True)
    controls[2].markdown(
        "<div class='small-note'><br>Price history is managed internally for indicator calculation and is not a user setting. "
        "Results are cached for one hour.</div>",
        unsafe_allow_html=True,
    )

    if refresh:
        _run_screen.clear()
        _constituents.clear()

    try:
        with st.spinner(f"Screening {universe}..."):
            result, source, universe_size = _run_screen(universe)
    except Exception as exc:
        st.error(f"Screener unavailable: {exc}")
        return

    rows = result.rows
    if rows.empty:
        st.error("No securities could be analysed.")
        if not result.failures.empty:
            st.dataframe(result.failures, use_container_width=True, hide_index=True)
        return

    st.caption(
        f"Universe source: {source} | Analysed: {len(rows)}/{universe_size} | "
        f"Updated: {pd.Timestamp.utcnow().strftime('%d %b %Y, %H:%M UTC')}"
    )

    tabs = st.tabs(["SCREENER", "SECTOR RANKING", "TOP & FLOP", "DATA AUDIT"])
    with tabs[0]:
        _render_methodology_screener(rows, universe_size)
    with tabs[1]:
        _render_sector_ranking(rows)
    with tabs[2]:
        _render_top_flop(rows)
    with tabs[3]:
        st.markdown("<div class='terminal-subheader'>METHODOLOGY & PROVENANCE</div>", unsafe_allow_html=True)
        st.write(
            "The Screener does not use an Opportunity Score, Cyclical Score, weighted average or price-performance rank. "
            "Matrix Action and Reward/Risk Rating are the direct outputs of the implemented public quarterly/monthly/weekly matrix."
        )
        st.write(
            "Display order is non-numeric and transparent: Matrix Action, published Reward/Risk rating, "
            "quarterly direction, monthly direction and Composite values as tie-breakers."
        )
        st.write(
            "Sector Ranking is the equal-weight mean adjusted-price return of constituents in each sector. "
            "Top & Flop ranks individual securities only by adjusted-price return for 1 day, 1 week, 1 month or 1 year."
        )
        st.write("Adjusted prices are used to neutralise dividends and splits, consistently with the terminal technical engine.")

        if not result.failures.empty:
            st.markdown("<div class='terminal-subheader'>FAILED SECURITIES</div>", unsafe_allow_html=True)
            st.dataframe(result.failures, use_container_width=True, hide_index=True, height=350)
            st.download_button(
                "DOWNLOAD FAILURE LOG",
                result.failures.to_csv(index=False).encode("utf-8"),
                file_name="screener_failures.csv",
                mime="text/csv",
            )
