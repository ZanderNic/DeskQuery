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


def generate_heatmap(data: Plot, 
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
    """Generates a barchart"""
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
    desk_coords = {1: (65, 90),
             2: (28, 100), 
             3: (28, 115), 
             4: (28, 200),
             5: (28, 213),
             6: (28, 285),
             7: (28, 295),
             8: (75, 285),
             9: (75, 295),
             10: (58, 370),
             11: (38, 368),
             12: (40, 370),
             13: (47, 392),
             14: (95, 375),
             15: (100, 394),
             16: (102, 430),
             17: (104, 450),
             18: (82, 440),
             19: (40, 428),
             20: (42, 445),
             21: (155, 385),
             22: (170, 369),
             23: (153, 385),
             24: (165, 445),
             25: (182, 430),
             26: (188, 445),
             27: (175, 384),
             28: (235, 431),
             29: (235, 445),
             30: (291, 431),
             31: (291, 445),
             32: (321, 431),
             33: (321, 445),
             34: (377, 445),
             35: (406, 430),
             36: (406, 445),
             37: (463, 430),
             38: (463, 445),
             39: (490, 430),
             40: (490, 445),
             41: (550, 433),
             42: (548, 445),
             43: (578, 430),
             44: (578, 445),
             45: (620, 430),
             46: (620, 445),
             47: (567, 157),
             48: (601, 157),
             49: (567, 104),
             50: (570, 84),
             51: (607, 87),
             52: (568, 37),
             53: (610, 37)}

    # room_id: (room_x, room_y)
    room_coords = {1: (51, 111),
        2: (51, 209),
        3: (52, 290),
        4: (70, 408),
        5: (171, 411),
        6: (264, 437),
        7: (352, 440),
        8: (435, 440),
        9: (520, 440),
        10: (599, 440),
        11: (588, 160),
        12: (590, 65)}

    desks_to_mark = {
        (f"ID: {id}"): coords
        for id, coords in desk_coords.items()
        if id in desk_ids
    }

    rooms_to_mark = {f"ID: {id} Name: {room_name_id_mapping[id]}": coords
        for id, coords in room_coords.items()
        if id in room_ids
    }


    fig = go.Figure()

    add_to_marks_to_fig(fig, desks_to_mark, mark_set_width, mark_set_height, map_width, map_height, 10, 10, 'red')
    add_to_marks_to_fig(fig, rooms_to_mark, mark_set_width, mark_set_height, map_width, map_height, 20, 20, 'blue')
    add_img_to_fig(fig, map, map_width, map_height)

    return fig


if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    from deskquery.functions.core.employee import get_avg_employee_bookings
    dataset = create_dataset()
    result = get_avg_employee_bookings(dataset, num_employees=200, include_fixed=False)
    fig = generate_map(room_ids=[5, 2], room_names=["Galgenberg"], desk_ids=[1, 8, 23])
    fig.write_html("hist.html")