import pandas as pd

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
