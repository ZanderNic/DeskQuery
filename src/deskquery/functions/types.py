from __future__ import annotations
from typing import Any, Dict, Optional, Sequence, Callable, List
import plotly.graph_objects as go
from abc import ABC, abstractmethod

class FunctionRegistryExpectedFormat(Dict):
    data: dict[str, Any]
    plot: PlotForFunction

class Plot(go.Figure):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class PlotFunction(ABC):
    @abstractmethod
    def __call__(self, data, *args, **kwargs) -> Plot:
        pass

class PlotForFunction:
    def __init__(self, default_plot: Plot, available_plots: List[PlotFunction]):
        self.default_plot = default_plot
        if default_plot not in available_plots:
            available_plots.append(default_plot)
        self.available_plots = available_plots
