# std lib imports
from io import BytesIO

# 3 party imports
import pandas as pd
import matplotlib.pyplot as plt


def format_df_as_markdown(df, max_rows=10):
    if not isinstance(df, pd.DataFrame):
        return str(df)
    if df.empty:
        return "Die Tabelle ist leer."
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_markdown(index=False)


def format_df_as_html(df, max_rows=10):
    if not isinstance(df, pd.DataFrame):
        return f"<pre>{str(df)}</pre>"
    if df.empty:
        return "<p><em>Die Tabelle ist leer.</em></p>"
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_html(index=False, classes="table table-striped", border=0)


def create_image():
    fig, ax = plt.subplots(figsize=(6, 4)) 
    ax.plot([0, 1, 2], [0, 1, 4])
    ax.set_title("Generated Image")
    img_io = BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight')
    plt.close(fig)
    return img_io
