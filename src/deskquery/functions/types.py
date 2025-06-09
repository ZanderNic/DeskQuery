from __future__ import annotations
from typing import Any, MutableMapping, Iterator, Dict, Optional, Sequence, Callable, List
import plotly.graph_objects as go
from abc import ABC, abstractmethod
from deskquery.data.dataset import Dataset

class Plot(go.Figure):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class PlotFunction(ABC):
    @abstractmethod
    def __call__(self, data: Dataset, *args: Any, **kwargs: Any) -> Plot:
        pass


class PlotForFunction:
    def __init__(self, default_plot: Optional[Plot] = Plot(), available_plots: List[PlotFunction] = []):
        self.default_plot = default_plot
        if default_plot not in available_plots and default_plot:
            available_plots.append(default_plot)
        self.available_plots = available_plots

class FunctionData(Dict):
    data: dict[str, dict[str, Any]] = {}

class FunctionRegistryExpectedFormat(MutableMapping):
    def __init__(self, data: FunctionData = FunctionData(), plot: PlotForFunction = PlotForFunction()):
        self.data = data
        self.plot = plot

    def __getitem__(self, key: str) -> Any:
        if key == "plot":
            return self.plot
        elif key == "data":
            return self.data
        else:
            raise KeyError(f"{key} not defined.")

    def __setitem__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delitem__(self, key: str) -> None:
        del self[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __str__(self) -> str:
        return f"{{data: {self.data}, plot: {self.plot}}}"


