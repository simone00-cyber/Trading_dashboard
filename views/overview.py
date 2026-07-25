import streamlit as st
from config.universe import EQUITY_INDICES
from data.yahoo import download_close_batch
from core.metrics import build_market_table, normalized_frame
from charts.common import create_line_chart, create_bar_chart
from ui.tables import style_market_table

def render_global_overview() -> None:
    st.markdown(
        "<div class='terminal-header'>GLOBAL OVERVIEW // EQUITY INDICES</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Aggiornamento indici globali..."):
        close = download_close_batch(tuple(EQUITY_INDICES.values()), period="6mo")

    table = build_market_table(close, EQUITY_INDICES)
    if table.empty:
        st.error("Yahoo Finance non ha restituito dati per gli indici.")
        return

    card_names = ["S&P 500", "NASDAQ", "FTSE MIB", "DAX", "NIKKEI 225", "VIX","KOSPI"]
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
        defaults = [name for name in ["S&P 500", "NASDAQ", "EURO STOXX 50", "FTSE MIB", "DAX", "NIKKEI 225","KOSPI"] if name in renamed.columns]
        selected = st.multiselect(
            "Indici",
            options=list(renamed.columns),
            default=defaults,
            label_visibility="collapsed",
            key="overview_indices",
        )
        if selected:
            chart = normalized_frame(renamed[selected])
            st.plotly_chart(
                create_line_chart(chart, "GLOBAL EQUITY // BASE 100", "Base 100", 510),
                width="stretch",
            )

    with right:
        st.markdown("<div class='terminal-subheader'>1D PERFORMANCE</div>", unsafe_allow_html=True)
        st.plotly_chart(
            create_bar_chart(table, "1D %", "LEADERS / LAGGARDS"),
            width="stretch",
        )

    st.markdown("<div class='terminal-subheader'>WORLD INDEX TABLE</div>", unsafe_allow_html=True)
    st.dataframe(style_market_table(table), width="stretch", hide_index=True, height=570)
