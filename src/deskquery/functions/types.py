from typing import Any, Dict, Optional
import plotly.graph_objects as go

class FunctionRegistryExpectedFormat(Dict):
    data: dict[str, Any]

class PlotFunctionReturnFormat(go.Figure):
    data: go.Figure

class PlotForFunction:
    default_plot: Optional[Any] = None
    avaiable_plots: Optional[Any] = None

    @classmethod
    def __if__(cls):
        return True if cls.default_plot else False