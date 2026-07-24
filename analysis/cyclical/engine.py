"""Facade for the verified/documented cyclical engine."""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from analysis.cyclical.alignment import assess_hierarchy
from analysis.cyclical.models import CycleState, HierarchyAssessment
from analysis.cyclical.states import build_cycle_state


def build_cyclical_engine(
    frames: Dict[str, pd.DataFrame],
) -> Tuple[Dict[str, CycleState], HierarchyAssessment]:
    states = {
        timeframe: build_cycle_state(timeframe, frame)
        for timeframe, frame in frames.items()
        if timeframe in {"YEARLY", "QUARTERLY", "MONTHLY", "WEEKLY"}
    }
    hierarchy = assess_hierarchy(states)
    return states, hierarchy
