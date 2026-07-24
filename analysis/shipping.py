import numpy as np
from config.settings import SHIPPING_DEMO_SEED
import pandas as pd

def build_shipping_comment(latest, avg30):

    delta = ((latest/avg30)-1)*100

    risk = "LOW"

    if delta < -5:
        risk = "ELEVATED"

    if delta < -10:
        risk = "HIGH"

    return (
        f"Hormuz traffic is {delta:+.1f}% versus "
        f"the 30-day average. "

        f"Current flow regime suggests "
        f"{risk.lower()} logistics risk. "

        f"Persistent weakness in crude tanker "
        f"traffic historically coincides with "
        f"tighter energy market conditions and "
        f"higher Brent sensitivity."
    )

def get_shipping_data():

    np.random.seed(SHIPPING_DEMO_SEED)

    dates = pd.date_range(
        end=pd.Timestamp.today().normalize(),
        periods=180,
        freq="D"
    )

    traffic = pd.DataFrame({
        "Date": dates,
        "Hormuz": np.random.normal(115, 8, len(dates)).cumsum()/20,
    })

    traffic["Hormuz"] = (
        120
        + np.sin(np.arange(len(dates))/15)*10
        + np.random.normal(0, 4, len(dates))
    )

    ships = pd.DataFrame({
        "Ship": [
            "VLCC Alpha",
            "LNG Falcon",
            "Box Asia",
            "Bulk Star",
            "VLCC Titan",
            "LNG Horizon",
        ],

        "Type": [
            "Crude Tanker",
            "LNG",
            "Container",
            "Bulk",
            "Crude Tanker",
            "LNG",
        ],

        "lat": [
            26.40,
            26.55,
            26.20,
            26.75,
            26.10,
            26.35,
        ],

        "lon": [
            56.10,
            56.30,
            56.45,
            56.00,
            56.60,
            56.20,
        ]
    })

    return traffic, ships
