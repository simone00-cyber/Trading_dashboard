import pandas as pd
import streamlit as st
from config.universe import RATE_CANDIDATES, BOND_PRICE_PROXIES, FX_UNIVERSE, COMMODITY_UNIVERSE, CRYPTO_UNIVERSE, CREDIT_UNIVERSE
from data.yahoo import download_close_batch, resolve_rate_series
from core.metrics import build_market_table, latest_change_bp, normalized_frame, ratio_series
from charts.common import create_line_chart, create_yield_curve_chart
from analysis.macro import build_macro_comment
from ui.tables import style_market_table

def render_rates_section() -> None:
    st.markdown("<div class='terminal-subheader'>RATES // US TREASURY YIELDS</div>", unsafe_allow_html=True)

    rates, symbols = resolve_rate_series(period="2y")
    if rates.empty:
        st.warning("Le serie dei rendimenti Treasury non sono disponibili su Yahoo Finance in questo momento.")
        return

    ordered = [label for label in ["US 13W", "US 2Y", "US 5Y", "US 10Y", "US 30Y"] if label in rates.columns]
    cols = st.columns(len(ordered))
    for col, label in zip(cols, ordered):
        series = rates[label].dropna()
        col.metric(
            label,
            f"{float(series.iloc[-1]):.3f}%",
            f"{latest_change_bp(series):+.1f} bp",
        )

    left, right = st.columns([1, 1.5])
    with left:
        st.plotly_chart(create_yield_curve_chart(rates), width="stretch")

    with right:
        st.plotly_chart(
            create_line_chart(rates[ordered], "TREASURY YIELDS // HISTORY", "Yield %", 440),
            width="stretch",
        )

    spreads = pd.DataFrame(index=rates.index)
    if "US 10Y" in rates.columns and "US 2Y" in rates.columns:
        spreads["10Y-2Y"] = (rates["US 10Y"] - rates["US 2Y"]) * 100.0
    if "US 10Y" in rates.columns and "US 13W" in rates.columns:
        spreads["10Y-13W"] = (rates["US 10Y"] - rates["US 13W"]) * 100.0
    if "US 30Y" in rates.columns and "US 5Y" in rates.columns:
        spreads["30Y-5Y"] = (rates["US 30Y"] - rates["US 5Y"]) * 100.0

    if not spreads.empty:
        st.plotly_chart(
            create_line_chart(spreads, "US CURVE SPREADS", "Basis points", 390),
            width="stretch",
        )

    symbol_text = ", ".join(f"{label}: {ticker}" for label, ticker in symbols.items())
    st.markdown(
        f"<div class='small-note'>Ticker Yahoo risolti: {symbol_text}. "
        "I valori sono rendimenti percentuali quando il ticker Yahoo rappresenta un indice di rendimento.</div>",
        unsafe_allow_html=True,
    )

def render_bond_proxies() -> None:
    st.markdown("<div class='terminal-subheader'>SOVEREIGN BOND PRICE PROXIES</div>", unsafe_allow_html=True)
    close = download_close_batch(tuple(BOND_PRICE_PROXIES.values()), period="1y")
    table = build_market_table(close, BOND_PRICE_PROXIES)

    if table.empty:
        st.warning("Proxy obbligazionari non disponibili.")
        return

    reverse = {ticker: name for name, ticker in BOND_PRICE_PROXIES.items()}
    renamed = close.rename(columns=reverse)
    selected = [name for name in BOND_PRICE_PROXIES if name in renamed.columns]
    normalized = normalized_frame(renamed[selected])

    left, right = st.columns([1.7, 1])
    with left:
        st.plotly_chart(
            create_line_chart(normalized, "BOND PRICES / FUTURES // BASE 100", "Base 100", 450),
            width="stretch",
        )
    with right:
        st.dataframe(style_market_table(table), width="stretch", hide_index=True, height=450)

    st.warning(
        "BTP10.MI e IS0L.DE sono proxy di prezzo tramite ETF, non rendimenti benchmark. "
        "Per questo il terminale non calcola un falso spread BTP-Bund partendo da questi prezzi. "
        "Un vero spread richiede rendimento BTP 10Y meno rendimento Bund 10Y."
    )

def render_global_macro() -> None:
    st.markdown("<div class='terminal-header'>GLOBAL MACRO // RATES, FX, COMMODITIES, CREDIT</div>", unsafe_allow_html=True)

    render_rates_section()
    render_bond_proxies()

    macro_tickers = tuple(
        list(FX_UNIVERSE.values())
        + list(COMMODITY_UNIVERSE.values())
        + list(CRYPTO_UNIVERSE.values())
        + list(CREDIT_UNIVERSE.values())
    )

    with st.spinner("Aggiornamento macro assets..."):
        close = download_close_batch(macro_tickers, period="1y")

    fx_table = build_market_table(close, FX_UNIVERSE)
    commodity_table = build_market_table(close, COMMODITY_UNIVERSE)
    crypto_table = build_market_table(close, CRYPTO_UNIVERSE)
    credit_table = build_market_table(close, CREDIT_UNIVERSE)

    tabs = st.tabs(["FX", "COMMODITIES", "CRYPTO", "CREDIT"])

    with tabs[0]:
        if fx_table.empty:
            st.warning("Dati FX non disponibili.")
        else:
            left, right = st.columns([1.6, 1])
            with left:
                reverse = {ticker: name for name, ticker in FX_UNIVERSE.items()}
                data = normalized_frame(close.rename(columns=reverse)[[name for name in reverse.values() if name in close.rename(columns=reverse).columns]])
                st.plotly_chart(create_line_chart(data, "FX PERFORMANCE // BASE 100", "Base 100", 470), width="stretch")
            with right:
                st.dataframe(style_market_table(fx_table), width="stretch", hide_index=True, height=470)

    with tabs[1]:
        if commodity_table.empty:
            st.warning("Dati commodity non disponibili.")
        else:
            left, right = st.columns([1.6, 1])
            with left:
                reverse = {ticker: name for name, ticker in COMMODITY_UNIVERSE.items()}
                renamed = close.rename(columns=reverse)
                columns = [name for name in COMMODITY_UNIVERSE if name in renamed.columns]
                st.plotly_chart(create_line_chart(normalized_frame(renamed[columns]), "COMMODITIES // BASE 100", "Base 100", 470), width="stretch")
            with right:
                st.dataframe(style_market_table(commodity_table), width="stretch", hide_index=True, height=470)

    with tabs[2]:
        if crypto_table.empty:
            st.warning("Dati crypto non disponibili.")
        else:
            reverse = {ticker: name for name, ticker in CRYPTO_UNIVERSE.items()}
            renamed = close.rename(columns=reverse)
            columns = [name for name in CRYPTO_UNIVERSE if name in renamed.columns]
            st.plotly_chart(create_line_chart(normalized_frame(renamed[columns]), "CRYPTO // BASE 100", "Base 100", 470), width="stretch")
            st.dataframe(style_market_table(crypto_table), width="stretch", hide_index=True)

    with tabs[3]:
        if credit_table.empty:
            st.warning("Dati credit proxy non disponibili.")
        else:
            left, right = st.columns([1.5, 1])
            with left:
                hy_ig = ratio_series(close, "HYG", "LQD")
                risk_treasury = ratio_series(close, "HYG", "TLT")
                ratios = pd.DataFrame({"HYG/LQD": hy_ig, "HYG/TLT": risk_treasury}).dropna(how="all")
                st.plotly_chart(create_line_chart(normalized_frame(ratios), "CREDIT RISK RATIOS // BASE 100", "Base 100", 470), width="stretch")
            with right:
                st.dataframe(style_market_table(credit_table), width="stretch", hide_index=True, height=470)

    rates, _ = resolve_rate_series(period="6mo")
    comment = build_macro_comment(rates, fx_table, commodity_table, close)
    st.markdown("<div class='terminal-subheader'>MACRO STRATEGIST COMMENT</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='report-box'>{comment}</div>", unsafe_allow_html=True)
