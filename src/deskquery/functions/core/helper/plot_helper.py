#!/usr/bin/env python 
from typing import Optional, List, Callable, Sequence, Iterable
from datetime import datetime
import plotly.graph_objects as go
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction, Plot, FunctionData
from pathlib import Path
from deskquery.data.dataset import Dataset
import PIL

def create_plotly_figure(traces: Sequence[go.Trace],
                      title: Optional[str] = None, 
                      xaxis_title: Optional[str] = None,
                      yaxis_title: Optional[str] = None):
    fig = Plot()

    for trace in traces:
        fig.add_trace(trace)

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        template="plotly_white",
        bargap=0.15,
        font=dict(size=14),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig

def add_to_marks_to_fig(fig, mark_dict, mark_set_width, mark_set_height, img_width, img_height, shape_width, shape_height, color):
    if not mark_dict:
        return

    marks_x_coords, marks_y_coords = list(zip(*[
        (img_width * x / mark_set_width, img_height * y / mark_set_height)
        for x, y in mark_dict.values()
    ]))

    for x, y in zip(marks_x_coords, marks_y_coords):
        fig.layout.shapes += (dict(
            type='rect',
            xref='x',
            yref='y',
            x0=x - shape_width / 2,
            y0=y - shape_height / 2,
            x1=x + shape_width / 2,
            y1=y + shape_height / 2,
            line=dict(color=color),
            fillcolor=color,
            opacity=0.5
        ),)

    fig.add_trace(go.Scatter(
        x=marks_x_coords,
        y=marks_y_coords,
        mode='markers',
        marker=dict(size=20, color='rgba(0,0,0,0)'),
        hoverinfo='text',
        text=list(mark_dict.keys()),
        showlegend=False
    ))

def add_img_to_fig(fig, img, img_width, img_height):
    fig.update_layout(
        images=[dict(
            source=img,
            x=0,
            y=0,
            sizex=img_width,
            sizey=img_height,
            xref="x",
            yref="y",
            sizing="stretch",
            layer="below"
        )],
        xaxis=dict(
            visible=False,
            range=[0, img_width]
        ),
        yaxis=dict(
            visible=False,
            range=[img_height, 0]
        ),
        width=img_width,
        height=img_height,
        margin=dict(l=0, r=0, t=0, b=0)
    )


def generate_heatmap(data: FunctionData, 
                      title: Optional[str] = None, 
                      xaxis_title: Optional[str] = None,
                      yaxis_title: Optional[str] = None,
                      colorscale: str = 'Viridis'
                      ) -> Plot:
    """ 
    Generates a heatmap
    """
    traces = list()
    for trace_name, trace_data in data.items():
        trace = go.Heatmap(
            # TODO: Not finished yet
            z = list(trace_data.values()), # z label
            x = list(trace_data.keys()[0]), # x label
            y = list(trace_data.keys()[1]), # y label
            colorscale = colorscale
        )
        traces.append(trace)

    fig = create_plotly_figure(traces, 
                         title=title, 
                         xaxis_title=xaxis_title, 
                         yaxis_title=yaxis_title)

    return fig

def generate_barchart(data: FunctionData, 
                      title: Optional[str] = None, 
                      xaxis_title: Optional[str] = None,
                      yaxis_title: Optional[str] = None
                      ) -> Plot:
    """
    Generates a barchart
    """
    traces = list()
    for trace_name, trace_data in data.items():
        trace = go.Bar(
            name=trace_name,
            x=list(trace_data.keys()),
            y=list(trace_data.values()),
            textposition="auto",
        )
        traces.append(trace)

    fig = create_plotly_figure(traces, 
                         title=title, 
                         xaxis_title=xaxis_title, 
                         yaxis_title=yaxis_title)

    return fig

def generate_scatterplot(data: FunctionData, 
                         title: Optional[str] = None, 
                         xaxis_title: Optional[str] = None,
                         yaxis_title: Optional[str] = None
                         ) -> Plot:
    """
    Generates a scatter plot
    """
    traces = list()
    for trace_name, trace_data in data.items():
        trace = go.Scatter(
            name=trace_name,
            x=list(trace_data.keys()),
            y=list(trace_data.values()),
            mode="markers",
        )
        traces.append(trace)

    fig = create_plotly_figure(traces, 
                         title=title, 
                         xaxis_title=xaxis_title, 
                         yaxis_title=yaxis_title)

    return fig


def generate_lineplot(data: FunctionData, 
                      title: Optional[str] = None, 
                      xaxis_title: Optional[str] = None,
                      yaxis_title: Optional[str] = None
                      ) -> Plot:
    """
    Generates a line plot
    """
    traces = list()
    for trace_name, trace_data in data.items():
        trace = go.Scatter(
            name=trace_name,
            x=list(trace_data.keys()),
            y=list(trace_data.values()),
            mode="lines",
        )
        traces.append(trace)

    fig = create_plotly_figure(traces, 
                         title=title, 
                         xaxis_title=xaxis_title, 
                         yaxis_title=yaxis_title)

    return fig

def generate_hist(data: FunctionRegistryExpectedFormat,
                  nbinsx: Optional[int] = None,
                  title: Optional[str] = None, 
                  xaxis_title: Optional[str] = None,
                  yaxis_title: Optional[str] = None
                  ) -> Plot:
    """Generates a histogramm"""
    traces = list()
    for trace_name, trace_data in data.items():
        traces.append(go.Histogram(name=trace_name,
                                   x=list(trace_data.values()),
                                   nbinsx=nbinsx if nbinsx else len(trace_data.values())))

    fig = create_plotly_figure(traces, 
                         title=title, 
                         xaxis_title=xaxis_title, 
                         yaxis_title=yaxis_title)

    return fig

def generate_map(room_ids: Optional[Iterable[int]] = None, 
                 room_names: Optional[Iterable[str]] = None, 
                 desk_ids: Optional[Iterable[int]] = None):

    room_ids = set(room_ids) if room_ids is not None else set()
    room_names = set(room_names) if room_names is not None else set()
    desk_ids = set(desk_ids) if desk_ids is not None else set()

    room_name_id_mapping = Dataset._desk_room_mapping.set_index("roomId")["roomName"].to_dict()
    desk_id_number_mapping = Dataset._desk_room_mapping.set_index("deskId")["deskNumber"].to_dict()

    room_ids.update(Dataset._desk_room_mapping.loc[
        Dataset._desk_room_mapping["roomName"].isin(room_names), "roomId"
    ])

    map_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "office_plan_optisch.png"
    map = PIL.Image.open(map_path)
    map_width, map_height = (640, 480)

    # the marks were set in the image when the image had that size
    # to make sure they are still correct if image_sizes changes
    # divide by them first
    mark_set_width, mark_set_height = (640, 480)
    # desk_id: (desk_x, desk_y)
    desk_coords = {1: (620, 445),
             2: (620, 430),
             3: (567, 157),
             4: (601, 157),
             5: (567, 104),
             6: (570, 84),
             7: (607, 87),
             8: (568, 37),
             9: (610, 37),
             10: (65, 90),
             11: (28, 100), 
             12: (28, 115), 
             13: (28, 200),
             14: (28, 213),
             15: (28, 285),
             16: (28, 295),
             17: (75, 285),
             18: (75, 295),
             19: (58, 370),
             20: (38, 368),
             21: (40, 370),
             22: (47, 392),
             23: (95, 375),
             24: (100, 394),
             25: (102, 430),
             26: (104, 450),
             27: (82, 440),
             28: (40, 428),
             29: (42, 445),
             30: (155, 385),
             31: (170, 369),
             32: (153, 385),
             33: (165, 445),
             34: (182, 430),
             35: (188, 445),
             36: (175, 384),
             37: (235, 431),
             38: (235, 445),
             39: (291, 431),
             40: (291, 445),
             41: (321, 431),
             42: (321, 445),
             43: (377, 445),
             44: (406, 430),
             45: (406, 445),
             46: (463, 430),
             47: (463, 445),
             48: (490, 430),
             49: (490, 445),
             50: (550, 433),
             51: (548, 445),
             52: (578, 430),
             53: (578, 445),}

    # room_id: (room_x, room_y)
    room_coords = {1: (599, 440),
        2: (588, 160),
        3: (590, 65),
        4: (51, 111),
        5: (51, 209),
        6: (52, 290),
        7: (70, 408),
        8: (171, 411),
        9: (264, 437),
        10: (352, 440),
        11: (435, 440),
        12: (520, 440)}

    desks_to_mark = {
        (f"Desk ID: {id} Desk Number: {desk_id_number_mapping[id]}"): coords
        for id, coords in desk_coords.items()
        if id in desk_ids
    }

    rooms_to_mark = {f"Room ID: {id} Room Name: {room_name_id_mapping[id]}": coords
        for id, coords in room_coords.items()
        if id in room_ids
    }

    fig = Plot()

    add_to_marks_to_fig(fig, desks_to_mark, mark_set_width, mark_set_height, map_width, map_height, 10, 10, 'red')
    add_to_marks_to_fig(fig, rooms_to_mark, mark_set_width, mark_set_height, map_width, map_height, 20, 20, 'blue')
    add_img_to_fig(fig, map, map_width, map_height)

    return fig

def generate_table():
    #TO DO:
    #Function which creates beautiful tables using plotly
    pass


if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    from deskquery.functions.core.employee import get_avg_employee_bookings
    dataset = create_dataset()
    result = get_avg_employee_bookings(dataset, num_employees=200, include_fixed=False)
    fig = generate_map(room_ids=[1, 5, 2], room_names=["Galgenberg"], desk_ids=[1, 8, 23])
    fig.write_html("hist.html")