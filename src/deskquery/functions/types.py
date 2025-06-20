from __future__ import annotations
from typing import Any, MutableMapping, Iterator, Dict, Optional, List
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
        self.available_plots = available_plots
    
    def to_json(self) -> str:
        return f"{{default_plot: {self.default_plot.to_json()}, available_plots: {[plot.__name__ for plot in self.available_plots if isinstance(plot, PlotFunction)]}}}"

    def __str__(self) -> str:
        return self.to_json()


class FunctionData(Dict):
    data: dict[str, dict[str, Any]] = {}


class FunctionRegistryExpectedFormat(MutableMapping):
    def __init__(
        self, 
        data: FunctionData = FunctionData(), 
        plot: PlotForFunction = PlotForFunction(),
        plotted: bool = False,
    ):
        self.data = data
        self.plot = plot
        self.plotable = True if plot.available_plots else False
        self.plotted = plotted

    def __getitem__(self, key: str) -> Any:
        if key == "plot":
            return self.plot
        elif key == "data":
            return self.data
        elif key == "plotable":
            return self.plotable
        elif key == "plotted":
            return self.plotted
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
        return self.to_json()
    
    def __repr__(self) -> str:
        return f"FunctionRegistryExpectedFormat({self.to_json()})"
    
    def to_json(self) -> str:
        """
        Converts the FunctionRegistryExpectedFormat to a JSON string.
        """
        return str({
            "data": self.data,
            "plot": self.plot.to_json(),
            "plotable": self.plotable,
            "plotted": self.plotted
        })
