# std lib imports
from io import BytesIO

# 3 party imports
import pandas as pd
import matplotlib.pyplot as plt
from flask import jsonify

def format_df_as_markdown(df, max_rows=10):
    if not isinstance(df, pd.DataFrame):
        return str(df)
    if df.empty:
        return "The table is empty."
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_markdown(index=False)


def format_df_as_html(df, max_rows=10):
    if not isinstance(df, pd.DataFrame):
        return f"<pre>{str(df)}</pre>"
    if df.empty:
        return "<p><em>The table is empty.</em></p>"
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_html(index=False, classes="table table-striped", border=0)



def format_chat_response(chat, response):
    if not isinstance(response, dict):
        response = {"type": "text", "content": str(response)}

    chat.append_message(
        role="assistant",
        content=response.get("content", ""),
        status=response.get("status"),
        data=response.get("data")
    )

    return jsonify({
        "chat_id": chat.chat_id,
        "messages": [
            {
                "id": chat.messages[-1]["id"],
                "role": "assistant",
                "content": chat.messages[-1]["content"],
                "status": chat.messages[-1].get("status"),
                "data": chat.messages[-1].get("data")
            }
        ]
    })