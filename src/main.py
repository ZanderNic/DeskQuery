# std imports 
from datetime import datetime, timedelta
import json
import argparse

# 3-party imports
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai

# Projekt imports 
from functions.function_registry import function_registry


def call_llm_and_execute(question: str, function_summaries: str, example_querys: str):
    
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
        
        ### User Query:
        {question}
        ---

        ### Old Example user querys with corosponding answer:
        {example_querys_with_answers}
    """
    
    prompt = prompt_template.format(            # fill in the variables in the string
        function_summaries = function_summaries,
        question = question,
        example_querys = example_querys
    )
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    code = response.text.strip('` \n')

    return code



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


def response_into_text(response_as_json):
    
    pass


def main(question: str):
    function_summaries = 1

    example_querys = "" # TODO generate some example queries with the correct format for the answer

    llm_response_str = call_llm_and_execute(question, function_summaries, example_querys)

    try:
        llm_response = json.loads(llm_response_str)
    except json.JSONDecodeError as e:
        print("Error while parsing the LLM response:", e)
        print("Raw response was:", llm_response_str)
        return

    result_as_json = handle_llm_response(llm_response)

    result_as_text = response_into_text(result_as_json)

    return result_as_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask a question to the desk booking analytics assistant.")
    parser.add_argument('--question', type=str, required=True, help='The user query to be analyzed and executed.')

    args = parser.parse_args()

    result = main(args.question)
    
    print(result)