import plotly.express as px
import plotly.graph_objects as go
from config.theme import BG, ORANGE, CYAN, BLUE, PURPLE
from charts.common import apply_terminal_layout

def create_shipping_risk_gauge(value):

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": "SHIPPING RISK INDEX"},
            gauge={
                "axis": {"range": [0,100]},
                "bar": {"color": ORANGE},

                "steps": [
                    {"range":[0,25],"color":"#0d3f1f"},
                    {"range":[25,50],"color":"#274d15"},
                    {"range":[50,75],"color":"#5b4700"},
                    {"range":[75,100],"color":"#5f1111"}
                ],
            }
        )
    )

    return apply_terminal_layout(fig, 320)

def create_hormuz_map(ships):

    color_map = {
        "Crude Tanker": ORANGE,
        "LNG": CYAN,
        "Container": BLUE,
        "Bulk": PURPLE,
    }

    fig = px.scatter_mapbox(
        ships,
        lat="lat",
        lon="lon",
        color="Type",
        hover_name="Ship",
        color_discrete_map=color_map,
        zoom=6,
        height=550,
    )

    fig.update_layout(
        mapbox_style="carto-darkmatter",
        paper_bgcolor=BG,
        margin=dict(l=0, r=0, t=0, b=0),
    )

    return fig
