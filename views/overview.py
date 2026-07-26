import streamlit as st
from config.universe import EQUITY_INDICES
from data.yahoo import download_close_batch
from core.metrics import build_market_table, normalized_frame
from charts.common import create_line_chart, create_bar_chart
from views.regime import render_market_regime


def _render_highlights(table) -> None:
    st.markdown("<div class='terminal-subheader'>TODAY'S HIGHLIGHTS</div>", unsafe_allow_html=True)
    ranked = table.dropna(subset=["1D %"]).sort_values("1D %", ascending=False)
    leader = ranked.iloc[0] if not ranked.empty else None
    laggard = ranked.iloc[-1] if not ranked.empty else None
    indexed = table.set_index("Strumento")
    cols = st.columns(4)
    cols[0].metric("GLOBAL LEADER", leader["Strumento"] if leader is not None else "N/D", f"{leader['1D %']:+.2f}%" if leader is not None else None)
    cols[1].metric("GLOBAL LAGGARD", laggard["Strumento"] if laggard is not None else "N/D", f"{laggard['1D %']:+.2f}%" if laggard is not None else None)
    vix = indexed.loc["VIX"] if "VIX" in indexed.index else None
    cols[2].metric("VIX", f"{vix['Ultimo']:,.2f}" if vix is not None else "N/D", f"{vix['1D %']:+.2f}%" if vix is not None else None)
    positive = int((ranked["1D %"] > 0).sum()) if not ranked.empty else 0
    cols[3].metric("POSITIVE MARKETS", f"{positive}/{len(ranked)}" if len(ranked) else "N/D")


def render_global_overview() -> None:
    st.markdown("<div class='terminal-header'>GLOBAL OVERVIEW // MARKET COMMAND CENTER</div>", unsafe_allow_html=True)

    with st.spinner("Aggiornamento indici globali..."):
        close = download_close_batch(tuple(EQUITY_INDICES.values()), period="6mo")

    table = build_market_table(close, EQUITY_INDICES)
    if table.empty:
        st.error("Yahoo Finance non ha restituito dati per gli indici.")
        return

    card_names = ["S&P 500", "NASDAQ", "FTSE MIB", "DAX", "NIKKEI 225", "VIX", "KOSPI"]
    indexed = table.set_index("Strumento")
    cols = st.columns(7)
    for col, name in zip(cols, card_names):
        if name not in indexed.index:
            col.metric(name, "N/D")
            continue
        row = indexed.loc[name]
        col.metric(name, f"{row['Ultimo']:,.2f}", f"{row['1D %']:+.2f}%")

    left, right = st.columns([2.1, 1])
    with left:
        st.markdown("<div class='terminal-subheader'>RELATIVE PERFORMANCE</div>", unsafe_allow_html=True)
        reverse = {ticker: name for name, ticker in EQUITY_INDICES.items()}
        renamed = close.rename(columns=reverse)
        defaults = [name for name in ["S&P 500", "NASDAQ", "EURO STOXX 50", "FTSE MIB", "DAX", "NIKKEI 225", "KOSPI"] if name in renamed.columns]
        selected = st.multiselect("Indici", options=list(renamed.columns), default=defaults, label_visibility="collapsed", key="overview_indices")
        if selected:
            st.plotly_chart(create_line_chart(normalized_frame(renamed[selected]), "GLOBAL EQUITY // BASE 100", "Base 100", 510), width="stretch")
    with right:
        st.markdown("<div class='terminal-subheader'>1D PERFORMANCE</div>", unsafe_allow_html=True)
        st.plotly_chart(create_bar_chart(table, "1D %", "LEADERS / LAGGARDS"), width="stretch")

    _render_highlights(table)
    render_market_regime(show_header=False)
