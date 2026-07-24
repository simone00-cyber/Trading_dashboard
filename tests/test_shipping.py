from analysis.shipping import get_shipping_data


def test_shipping_demo_is_deterministic_and_labelled_by_config():
    traffic_a, ships_a = get_shipping_data()
    traffic_b, ships_b = get_shipping_data()
    assert traffic_a.equals(traffic_b)
    assert ships_a.equals(ships_b)
    assert len(traffic_a) == 180
