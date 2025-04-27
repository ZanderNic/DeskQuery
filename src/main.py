from function_reg import function_registry



prompt_template = """
    You are a smart assistant for a desk booking analytics system.
    You have access to a predefined set of Python functions (see below).  

    Your job is to:
    1. Understand the user query.
    2. Select the most appropriate function from the list (never invent your own).
    3. Fill in the parameters based on what the user has provided or can be reasonably assumed.
    4. If information is missing, mark it clearly with a placeholder and add a `missing_fields` list.
    5. If no suitable function exists, return `"function": null` and `"reason"` explaining why.

    ### Available Functions (Summarized):

    {function_summaries}

    ---

    ### Response format:
    {{
    "function": "function_name_or_null",
    "parameters": {{ "param1": "...", "param2": "..." }},
    "missing_fields": ["..."],  # optional
    "reason": "..."             # only if function is null or clarification is needed
    }}

    ---

    ### Example user query:
    {example_query}
"""



def handle_llm_response(response: dict):
    
    if response.get("function") is None:
        return {
            "status": "no_match",
            "message": response.get("reason", "I couldn't find a suitable function.")
        }

    if response.get("missing_fields"):
        missing = ", ".join(response["missing_fields"])
        return {
            "status": "ask_user",
            "message": response.get("explanation", f"Please provide: {missing}"),
            "missing_fields": response["missing_fields"]
        }

    try:
        func = function_registry[response["function"]]
        result = func(**response["parameters"])
        return {
            "status": "success",
            "function": response["function"],
            "parameters": response["parameters"],
            "result": result,
            "message": response.get("explanation", f"I executed {response['function']}.")
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error while calling {response['function']}: {e}"
        }



if __name__ == "__main__":
    pass