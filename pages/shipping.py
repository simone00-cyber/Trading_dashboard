import plotly.graph_objects as go
import streamlit as st
from config.theme import ORANGE, BLUE, RED
from analysis.shipping import get_shipping_data, build_shipping_comment
from config.settings import SHIPPING_DEMO_ENABLED
from charts.shipping import create_hormuz_map, create_shipping_risk_gauge
from charts.common import apply_terminal_layout

def render_shipping():
    if not SHIPPING_DEMO_ENABLED:
        st.info("Il modulo Shipping demo è disabilitato in config/settings.py.")
        return

    st.markdown(
        "<div class='terminal-header'>GLOBAL SHIPPING & ENERGY FLOWS</div>",
        unsafe_allow_html=True
    )

    st.markdown(f"<div class='signal-box' style='border-left-color:{RED}'><b style='color:{RED}'>DEMO DATA</b><br><span class='small-note'>I dati shipping visualizzati sono simulati e non rappresentano traffico navale reale.</span></div>", unsafe_allow_html=True)

    traffic, ships = get_shipping_data()

    latest = float(traffic["Hormuz"].iloc[-1])
    avg30 = float(traffic["Hormuz"].tail(30).mean())

    crude = 54
    lng = 18

    risk_index = min(
        100,
        max(
            10,
            int(50 + (avg30-latest)*2)
        )
    )

    c1,c2,c3,c4 = st.columns(4)

    c1.metric(
        "HORMUZ TRANSITS",
        f"{latest:.0f}",
        f"{((latest/avg30)-1)*100:+.1f}%"
    )

    c2.metric(
        "CRUDE TANKERS",
        crude
    )

    c3.metric(
        "LNG CARRIERS",
        lng
    )

    c4.metric(
        "RISK INDEX",
        risk_index
    )

    left,right = st.columns([2,1])

    with left:

        st.plotly_chart(
            create_hormuz_map(ships),
            use_container_width=True
        )

    with right:

        st.plotly_chart(
            create_shipping_risk_gauge(risk_index),
            use_container_width=True
        )

    st.markdown(
        "<div class='terminal-subheader'>HORMUZ TRAFFIC TREND</div>",
        unsafe_allow_html=True
    )

    trend = go.Figure()

    trend.add_trace(
        go.Scatter(
            x=traffic["Date"],
            y=traffic["Hormuz"],
            name="Traffic",
            line=dict(color=ORANGE,width=2)
        )
    )

    trend.add_trace(
        go.Scatter(
            x=traffic["Date"],
            y=traffic["Hormuz"].rolling(30).mean(),
            name="30D Average",
            line=dict(color=BLUE,width=2)
        )
    )

    st.plotly_chart(
        apply_terminal_layout(
            trend,
            420
        ),
        use_container_width=True
    )

    comment = build_shipping_comment(
        latest,
        avg30
    )

    st.markdown(
        "<div class='terminal-subheader'>SHIPPING STRATEGIST COMMENT</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<div class='report-box'>{comment}</div>",
        unsafe_allow_html=True
    )
