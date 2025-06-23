#!/usr/bin/env python 
# std lib imports
from typing import Optional, Sequence, Iterable, Dict
import PIL
from pathlib import Path

# 3 party imports
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# Projekt imports
from deskquery.data.dataset import Dataset
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction, Plot, FunctionData


def create_plotly_figure(
    traces: Sequence[go.Trace],
    title: Optional[str] = None, 
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None
) -> Plot:
    fig = Plot()

    for trace in traces:
        fig.add_trace(trace)

    fig.update_layout(
        title=title if title else "",
        xaxis_title=xaxis_title if xaxis_title else "",
        yaxis_title=yaxis_title if yaxis_title else "",
        template="ggplot2",
        bargap=0.15,
        font=dict(size=14),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig


def add_to_marks_to_fig(
    fig,
    mark_dict,
    mark_set_width,
    mark_set_height,
    img_width,
    img_height,
    shape_width,
    shape_height,
    default_color
):
    if not mark_dict:
        return

    marks_x_coords, marks_y_coords, colors, texts = [], [], [], []

    for text, entry in mark_dict.items():
        coords = entry["coords"] if isinstance(entry, dict) else entry
        color = entry.get("color", default_color) if isinstance(entry, dict) else default_color

        x = img_width * coords[0] / mark_set_width
        y = img_height * coords[1] / mark_set_height

        marks_x_coords.append(x)
        marks_y_coords.append(y)
        colors.append(color)
        texts.append(text)

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
            opacity=0.9
        ),)

    fig.add_trace(go.Scatter(
        x=marks_x_coords,
        y=marks_y_coords,
        mode='markers',
        marker=dict(size=20, color=colors),
        hoverinfo='text',
        text=texts,
        showlegend=False,
        opacity=0
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


def value_to_color(value: float) -> str:
    rgba = plt.cm.RdYlGn(value)
    return f'rgb({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)})'


def generate_heatmap(
    data: FunctionData = None,
    title: Optional[str] = None, 
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    colorscale: str = 'Viridis'
) -> Plot:
    """ 
    Generate a heatmap from structured input data of correct format.

    Args:
        data (FunctionData, optional): A dictionary in the format 
            {trace_name: {"x": x_values, "y": y_values, "z": z_values}}. 
            Defaults to `None`, meaning no data is plotted unless explicitly provided.
        title (str, optional): Title of the heatmap. Defaults to `None`, 
            meaning no title is displayed unless specified.
        xaxis_title (str, optional): Label for the x-axis. Defaults to `None`, 
            meaning the x-axis will have no label unless specified.
        yaxis_title (str, optional): Label for the y-axis. Defaults to `None`, 
            meaning the y-axis will have no label unless specified.
        colorscale (str, optional): Color scale used for the heatmap. 
            Defaults to 'Viridis'.

    Returns:
        Plot: A Plotly heatmap figure.
    """
    traces = list()
    for trace_name, trace_data in data.items():
        try:
            x = list(trace_data.values())[0]
            y = list(trace_data.values())[1]
            z = list(trace_data.values())[2]
        except IndexError:
            raise ValueError(
                "Data for heatmap have to be in the following format: {trace1_name: {x: x_data, y: y_data, z: z_data}}"
            )

        trace = go.Heatmap(
            x=x,
            y=y,
            z=z,
            colorscale=colorscale
        )
        traces.append(trace)

    fig = create_plotly_figure(
        traces, 
        title=title, 
        xaxis_title=xaxis_title, 
        yaxis_title=yaxis_title
    )

    return fig


def generate_barchart(
    data: FunctionData = None, 
    title: Optional[str] = None, 
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None
) -> Plot:
    """
    Generate a bar chart/bar plot from structured input data of correct format.

    Args:
        data (FunctionData, optional): A dictionary in the format 
            {trace_name: {category: value}}. Defaults to `None`, 
            meaning no data is plotted unless explicitly provided.
        title (str, optional): Title of the bar chart. Defaults to `None`, 
            meaning no title is displayed unless specified.
        xaxis_title (str, optional): Label for the x-axis. Defaults to `None`, 
            meaning the x-axis will have no label unless specified.
        yaxis_title (str, optional): Label for the y-axis. Defaults to `None`, 
            meaning the y-axis will have no label unless specified.

    Returns:
        Plot: A Plotly bar chart figure.
    """
    traces = list()
    for trace_name, trace_data in data.items():
        try:
            x = list(trace_data.keys())
            y = list(trace_data.values())
        except AttributeError:
            raise ValueError(
                "Data for barchart have to be in following format: {trace1_name: {x: y}}"
            )

        trace = go.Bar(
            name=trace_name,
            x=x,
            y=y,
            textposition="auto",
        )

        traces.append(trace)

    fig = create_plotly_figure(
        traces, 
        title=title if title else '', 
        xaxis_title=xaxis_title if xaxis_title else '', 
        yaxis_title=yaxis_title if yaxis_title else ''
    )

    return fig


def generate_scatterplot(
    data: FunctionData = None, 
    title: Optional[str] = None, 
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None
) -> Plot:
    """
    Generate a scatter plot from structured input data of correct format.

    Args:
        data (FunctionData, optional): A dictionary in the format 
            {trace_name: {x_value: y_value}}. Defaults to `None`, 
            meaning no data is plotted unless explicitly provided.
        title (str, optional): Title of the scatter plot. Defaults to `None`, 
            meaning no title is displayed unless specified.
        xaxis_title (str, optional): Label for the x-axis. Defaults to `None`, 
            meaning the x-axis will have no label unless specified.
        yaxis_title (str, optional): Label for the y-axis. Defaults to `None`, 
            meaning the y-axis will have no label unless specified.

    Returns:
        Plot: A Plotly scatter plot figure.
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

    fig = create_plotly_figure(
        traces, 
        title=title if title else '', 
        xaxis_title=xaxis_title if xaxis_title else '', 
        yaxis_title=yaxis_title if yaxis_title else ''
    )

    return fig


def generate_lineplot(
    data: FunctionData = None, 
    title: Optional[str] = None, 
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None
) -> Plot:
    """
    Generate a line plot from structured input data of correct format.

    Args:
        data (FunctionData, optional): A dictionary in the format 
            {trace_name: {x_value: y_value}}. Defaults to `None`, 
            meaning no data is plotted unless explicitly provided.
        title (str, optional): Title of the line plot. Defaults to `None`, 
            meaning no title is displayed unless specified.
        xaxis_title (str, optional): Label for the x-axis. Defaults to `None`, 
            meaning the x-axis will have no label unless specified.
        yaxis_title (str, optional): Label for the y-axis. Defaults to `None`, 
            meaning the y-axis will have no label unless specified.

    Returns:
        Plot: A Plotly line plot figure.
    """
    traces = list()
    for trace_name, trace_data in data.items():
        try:
            x = list(trace_data.keys())
            y = list(trace_data.values())
        except AttributeError:
            raise ValueError(
                "Data for lineplot have to be in following format: {trace1_name: {x: y}}"
            )

        trace = go.Scatter(
            name=trace_name,
            x=x,
            y=y,
            mode="lines",
        )
        traces.append(trace)

    fig = create_plotly_figure(
        traces, 
        title=title if title else '',
        xaxis_title=xaxis_title if xaxis_title else '',
        yaxis_title=yaxis_title if yaxis_title else ''
    )

    return fig


def generate_hist(
    data: FunctionData = None,
    nbinsx: Optional[int] = None,
    title: Optional[str] = None, 
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None
) -> Plot:
    """
    Generate a histogram from structured input data of correct format.

    Args:
        data (FunctionData, optional): A dictionary in the format 
            {trace_name: {"x": x_values}}. Defaults to `None`, 
            meaning no data is provided unless explicitly passed.
        nbinsx (int, optional): Number of bins along the x-axis. 
            If not specified, defaults to the length of x_values.
        title (str, optional): Title of the histogram. Defaults to `None`, 
            meaning no title is displayed unless specified.
        xaxis_title (str, optional): Label for the x-axis. Defaults to `None`, 
            meaning the x-axis will have no label unless specified.
        yaxis_title (str, optional): Label for the y-axis. Defaults to `None`, 
            meaning the y-axis will have no label unless specified.

    Returns:
        Plot: A Plotly histogram figure.
    """
    traces = list()
    for trace_name, trace_data in data.items():
        try:
            x = list(trace_data.values())
        except AttributeError:
            raise ValueError(
                "Data for histogramm have to be in following format: {trace1_name: {x: x_data}}"
            )

        traces.append(go.Histogram(
            name=trace_name,
            x=x,
            nbinsx=nbinsx if nbinsx else len(trace_data.values())
        ))

    fig = create_plotly_figure(
        traces, 
        title=title if title else '',
        xaxis_title=xaxis_title if xaxis_title else '',
        yaxis_title=yaxis_title if yaxis_title else ''
    )

    return fig


def generate_map(
    room_ids: Optional[Dict[int, float]] = None,
    room_names: Optional[Dict[int, float]] = None,
    desk_ids: Optional[Dict[int, float]] = None,
    label_markings: Optional[str] = None,
    title: Optional[str] = "Map",
) -> Plot:
    """
    Generate an interactive office layout map with color-coded highlights for desks and rooms.

    The function overlays a fixed background image of the office floor plan with colored rectangular
    markers for desks and rooms based on their usage or custom values. Hover tooltips provide details 
    like room/desk ID, name/number, and value. The color reflects the numeric value (e.g. utilization),
    using a red-yellow-green colormap that is between 0 and 1.

    A valid map can be created by setting all parameters to `None`.

    Args:
        room_ids (dict[int, float], optional):
            Mapping of room IDs to values (e.g. utilization). These will be marked in the image.
            Defaults to `None`, which means no specific rooms are marked.
        room_names (dict[str, float], optional):
            Alternative to `room_ids`. Room names are internally mapped to IDs.
            Defaults to `None`, which means no specific rooms are marked.
        desk_ids (dict[int, float], optional):
            Mapping of desk IDs to values. These will be shown as smaller colored boxes.
            Defaults to `None`, which means no specific values are shown for desks.
        label_markings (str, optional):
            Optional label description shown in the hover tooltip. Defaults to "label" if not given.
        title (str, optional):
            Title of the map. Defaults to "Map", meaning this title is displayed unless overridden.

    Returns:
        Plot: A Plotly figure with the office background and interactive overlays.

    Notes:
        - Coordinates for desks and rooms are statically defined and tied to a 640x480 image.
        - Desk/room positions are predefined and not inferred from layout data.
        - The base image is located at: `data/office_plan_optisch.png`
    """
    # set default values if applicable
    room_ids = room_ids if room_ids and isinstance(room_ids, dict) else dict()
    room_names = room_names if room_names and isinstance(room_names, dict) else dict()
    desk_ids = desk_ids if desk_ids and isinstance(desk_ids, dict) else dict()
    if not label_markings:
        label_markings = "label"
    if not title:
        title = "Map"

    room_name_id_mapping = Dataset._desk_room_mapping.set_index("roomId")["roomName"].to_dict()
    desk_id_number_mapping = Dataset._desk_room_mapping.set_index("deskId")["deskNumber"].to_dict()
    room_name_to_id = Dataset._desk_room_mapping.drop_duplicates("roomName").set_index("roomName")["roomId"].to_dict()

    room_ids.update({
        room_name_to_id[name]: value
        for name, value in room_names.items()
        if name in room_name_to_id
    })

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
        f"Desk ID: {id} Number: {desk_id_number_mapping[id]} {label_markings or 'label'}: {value}": {
            "coords": desk_coords[id],
            "color": value_to_color(value)
        }
        for id, value in desk_ids.items()
        if id in desk_coords
    }

    rooms_to_mark = {
        f"Room ID: {id} Name: {room_name_id_mapping[id]} {label_markings or 'label'}: {value}": {
            "color": value_to_color(value),
            "coords": room_coords[id]
        }
        for id, value in room_ids.items()
        if id in room_coords
    }

    fig = Plot()

    add_to_marks_to_fig(fig, desks_to_mark, mark_set_width, mark_set_height, map_width, map_height, 10, 10, 'red')
    add_to_marks_to_fig(fig, rooms_to_mark, mark_set_width, mark_set_height, map_width, map_height, 20, 20, "blue")
    add_img_to_fig(fig, map, map_width, map_height)

    fig.update_layout(title=title)
    
    return fig


def generate_table(
    data: FunctionData = None, 
    title: Optional[str] = None
) -> Plot:
    """
    Generate a formatted table using Plotly.

    Args:
        data (FunctionData, optional): 
            A dictionary where each key is a column name and the value is a 
            list of column values. Defaults to `None`, meaning no table is 
            rendered unless data is explicitly provided.
        title (str, optional): 
            Title for the table. Defaults to `None`, meaning no title is 
            displayed unless specified.

    Returns:
        Plot: A Plotly table figure.
    """
    traces = list()
    for trace_name, trace_data in data.items():
        try:
            headers = list(trace_data.keys())
            columns = list(trace_data.values())
        except AttributeError:
            raise ValueError(
                "Data for table have to be in following format: {trace1_name: {col_header1: col_data1}}"
            )

        trace = go.Table(
            header=dict(
                values=headers,
                fill_color='lightgrey',
                align='left'
            ),
            cells=dict(
                values=columns,
                fill_color='white',
                align='left'
            )
        )
        traces.append(trace)

    fig = create_plotly_figure(
        traces, 
        title=title if title else ''
    )

    return fig


if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    from deskquery.functions.core.forecasting import estimate_necessary_desks, forecast_employees
    from deskquery.functions.core.policy import simulate_policy
    dataset = create_dataset()

    policy = {
        "fixed_days":["tuesday"],
        "choseable_days":["wednesday", "thursday"],
        "number_choseable_days":1,
        "number_days":3,
        "more_days_allowed":True
    }

    # exceptions = {
    #     4: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True},
    #     14: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True}
    # }

    # random_assignments = [
    #     (10, {'number_days': 1, 'more_days_allowed': False})
    # ]

    result = estimate_necessary_desks(dataset, forecast_model="sarima", weekly_absolute_growth=1, weeks_ahead=52, policy=policy)
    output = generate_lineplot(result["data"])

    # result = simulate_policy(dataset, policy=policy)
    # output = generate_barchart(result["data"])

    # result = forecast_employees(dataset, forecast_model="sarima")
    # output = generate_lineplot(result["data"])

    output.write_html("hist.html")