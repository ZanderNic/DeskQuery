# std imports 
from typing import List
#from datetime import datetime, timedelta
import datetime
import json
import argparse
from pathlib import Path
import re
import copy
import traceback

# 3-party imports
import pandas as pd
import matplotlib.pyplot as plt

# Projekt imports 
from deskquery.functions.function_registry import (
    function_registry,
    plot_function_registry,
    create_function_summaries, 
    get_function_docstring, 
    get_function_parameters
)
from deskquery.data.dataset import Dataset
from deskquery.llm.llm_api import LLM_Client, get_model_client, get_model_providers
from deskquery.webapp.helpers.chat_data import ChatData, FREF_from_dict
from deskquery.functions.core.helper.plot_helper import *
from deskquery.functions.core.plot import generate_plot_for_function


global current_model
current_model = None
global current_client
current_client = None
global function_data
function_data = {
    'function_registry': copy.deepcopy(function_registry)
}
global PARAM_EXTRACTION_chat_history
PARAM_EXTRACTION_chat_history = []


# Chat Naming Inferation Feature ##############################################

def get_chat_name(
    user_query: str,
):
    """
    Takes a user query of a chat and lets the LLM infer a name to determine
    a first automatically set name.

    Args:
        user_query (str):
            The first user message in a new chat to infer the chat name from.
    """
    global current_client

    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given the first user message in a new chat.

### Task:

Use the user message to infer a fitting name for the chat.
This name should only be at maximum 24 characters long.

Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"chat_title": "<chat_title>",
}}

### User Query:

{user_query}

### Your Response:
"""
    prompt = prompt_template.format(
        user_query=user_query
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)

    return resp_data


def infer_chat_renaming(
    chat_data: ChatData
):
    """
    Takes the first user message from a chat data object and uses its content
    to let an LLM infer a fitting title for automatic renaming.

    The title is set to be at most 24 characters long.

    Args:
        chat_data (ChatData):
            The chat data object of the chat to rename.

    Raises:
        RuntimeError:
            If the LLM was not able to generate a fitting title in 10 tries. 
    """
    # fetch the chat's first user message content
    for msg in chat_data.messages:
        if msg.get("role", "") == "user":
            user_msg = msg
            break
    user_query = user_msg['content']

    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 10:
        try:
            # generate the response from the LLM
            response = get_chat_name(user_query)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # check the given response's validity
        if (json_data.get("chat_title", False) and
            isinstance(json_data["chat_title"], str) and 
            len(json_data["chat_title"]) <= 24):
            # update the chat name directly
            chat_data.rename_chat(json_data["chat_title"])
            return  # quit without an error
        else:
            # if the title is not correctly specified, go to the next iteration
            generate_counter += 1
            error = True

    # abort after 10 insufficient generations
    if error and generate_counter >= 10:
        raise RuntimeError("Could not infer a chat title in 10 tries")


###############################################################################

def clean_llm_output(
    llm_output: str
) -> str:
    """
    Cleans the LLM's output from `client.chat_completion()` by removing 
    unwanted content.
    
    Args:
        response (str): The LLM's raw output.
    
    Returns:
        str: The cleaned output.
    """
    # clean potentially unwanted content from the response string
    cleaned_response = re.sub(
        r'<think>.*?</think>', '', llm_output, flags=re.DOTALL
    )
    resp_data = cleaned_response.strip('` \n')
    # if json is specified explicitly
    if resp_data.startswith('json'):
        resp_data = resp_data[4:]
    elif resp_data.startswith('python'):
        resp_data = resp_data[6:]
    return resp_data.strip('` \n')


def main(
    user_input: str,
    chat_data: ChatData,
    data: Dataset,
    model: dict = {'provider': 'google', 'model': 'gemini-2.0-flash-001'},
    START_STEP: int = 1,  # start with step 1
):
    """
    Takes a user input and evaluates it with the currently selected LLM client.
    The evaluation is handled in a stepwise approach using the function
    ``handleMessage``, which returns the current evaluation result. This is 
    either a question to the user to refine the input information or the answer
    to a user query.
    
    Args:
        user_input (str):
            The user input to evaluate.
        chat_data (ChatData):
            The chat data object containing the chat data including the message
            history.
        data (Dataset):
            The dataset to use for the evaluation.
        model (dict, optional): 
            The model to use for the evaluation. Defaults to 
            {'provider': 'google', 'model': 'gemini-2.0-flash-001'}.
        START_STEP (int, optional):
            The step to start the evaluation with. Defaults to 1. If the user 
            has to refine the input the start step has to be set to 30 to
            directly reach the parameter extraction step.

    Returns:
        dict:
            The result of the evaluation. This is either a question to the user
            to refine the input information or the answer to a user query.
    """
    global current_model
    global current_client

    # save current chat history if applicable
    current_chat_history = current_client.chat_history if current_client else []

    # apply the selected model if it exists
    if model is None:
        model = {'provider': 'google', 'model': 'gemini-2.0-flash-001'}
    if current_model is None or current_model != model:
        current_model = model
        client = get_model_client(model['provider'])  # default provider if not specified
        current_client = client(
            model=model['model'],  # default model if not specified
            chat_history=False,  # FIXME: according to the current prompt implementation
            sys_msg=None,
            output_schema=None
        )
        # paste previous chat history if applicable
        current_client.chat_history = current_chat_history

    print("Using model:", current_client.model)  # FIXME: DEBUG

    result = handleMessage(user_input, chat_data, data, model, START_STEP)

    return result

###############################################################################
# USER REQUEST HANDLING
###############################################################################

# STEP 1: Call LLM to decide for the next task

def decide_next_task(
    question: str,
    chat_history: List[dict] = [],
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
To fulfill your task, you get:
- a current user query
- a chat history with the user
- a set of available functions that would be used to answer the user query.

### Task:

Decide which task to perform next based on the user query and the chat history.
The available tasks (names) and their meanings are:
- "execute_function": Execute a SINGLE function to answer the user query.
- "explain_former_result": Explain the result of a previously executed function.
- "execute_function_on_former_result": Execute a function on the result of a previously executed function.
- "plot_former_result": Generate a plot for the result of a previously executed function.
- "execute_function_plan": Execute a sequence of functions to answer the user query.
- "chat": If the user query is a general question or a request for information that does not require function execution or any other of the given tasks.

Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"task": "task_name",
}}

### Available Functions (Summarized):

{function_summaries}

### Chat History:

{chat_history}

### User Query:

{question}

### Your Response:
"""
    global function_data
    global current_client

    function_summaries = create_function_summaries(function_registry=function_data['function_registry'])

    prompt = prompt_template.format(
        function_summaries=function_summaries,
        question=question,
        chat_history=chat_history
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)
    
    print("1) Decide next task:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_next_task(
    question: str,
    chat_history: List[dict] = [],
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = decide_next_task(question, chat_history)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the task is specified
        possible_tasks = [
            "chat",
            "execute_function",
            "explain_former_result",
            "execute_function_on_former_result",
            "plot_former_result",
            "execute_function_plan"
        ]
        if json_data.get("task", None) is not None and json_data["task"] in possible_tasks:
            # if the task is specified, return it
            return {
                "status": "success",
                "task": json_data["task"],
            }
        else:
            # if the task is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I couldn't understand your request. Please try again or describe it in a different way."
        }


###############################################################################

# STEP 5: Let the LLM answer the user query without any function execution or referenced messages

def get_chat_answer(
    user_message: str,
    chat_history: List[dict] = [],
):
    global current_client
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
Your general purpose is to answer user queries about office desk analytics. You have the ability to execute functions to help answering user queries.
These functions include the areas of:
    - desk and room utilizations and their anomalies
    - simulating attandance policies and detecting policy violations
    - employee booking behavior and patterns including cesk clustering and co-booking frequencies
    - employee booking forecasts and necessary desk estimations
You are also able to provide different visualizations of the data and results.
Result visualizations include:
    - histograms
    - bar charts
    - line charts
    - scatter plots
    - a marked office desk map for desk bookings

You are given a user query and a chat history with the user to fulfill your task.

### Task:

Answer the user query with respect to the chat history if applicable.
If the user query does not relate to your functionality, politely inform the user about your purpose in a short message.

Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:

{{
"message": "<Your answer to the user query>",
}}

### User Query:

{user_message}

### Chat History:

{chat_history}

### Your Response:
"""
    prompt = prompt_template.format(
        user_message=user_message,
        chat_history=chat_history
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)

    print("5) LLM Chat Answer:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_chat_answer(
    user_message: str, 
    chat_history: List[dict] = [],
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = get_chat_answer(user_message, chat_history)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # check the given response's validity
        if json_data.get("message", False) and isinstance(json_data["message"], str):
            return {
                "status": "success",
                "message": json_data["message"],
            }
        else:
            # if the task is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I could not process your request. Please try again or describe it in a different way."
        }

###############################################################################

# STEP 10: Decide on the message to use next referenced by the user query

def select_referenced_messages(
    question: str,
    chat_history: List[dict],
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a user query and a chat history with the user to fulfill your task.

### Task:

The user query refers to ONE or MULTIPLE messages in the chat history to perform the future actions on.
For the moment, infer the list of messages that are referenced by the user query and list their IDs in your response.
Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"message_ids": [<message_1_id_int>, (optionally:) <message_2_id_int>, ...]
}}

### User Query:

{question}

### Chat History:

{chat_history}

### Your Response:
"""
    global current_client

    prompt = prompt_template.format(
        question=question,
        chat_history=chat_history
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)
    
    print("10) LLM Referenced Message Selection:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data


def validate_referenced_messages(
    question: str,
    chat_history: List[dict],
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = select_referenced_messages(question, chat_history)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the message ID is specified
        if json_data.get("message_ids", None) is not None:
            if isinstance(json_data["message_ids"], str):
                json_data["message_ids"] = eval(json_data["message_ids"])
            if not isinstance(json_data["message_ids"], list):
                json_data["message_ids"] = [json_data["message_ids"]]
            return {
                "status": "success",
                "message_ids": json_data["message_ids"],
            }
        else:
            # if the message ID is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I couldn't infer the message referenced in your request. Please try again or describe it in a different way."
        }


###############################################################################

# STEP 30: Call LLM to further explain the specified messages to the user 

def explain_referenced_messages(
    question: str,
    referenced_messages: List[dict],
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a user query and a selection of the chat history with the user.
The user is asking about an explanation of previous messages in the chat history.

### Task:

Answer the user query with respect to the given messages of the chat history.
Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"message": "<Your answer to the user query>",
}}

### Given Messages of the Chat History:

{referenced_messages}

### User Query:

{question}

### Your Response:
"""
    global current_client

    prompt = prompt_template.format(
        question=question,
        referenced_messages=referenced_messages
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)

    print("30) LLM Referenced Message Explanation:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_referenced_message_explanation(
    question: str,
    referenced_messages: List[dict],
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = explain_referenced_messages(question, referenced_messages)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the message is specified
        if json_data.get("message", None) is not None:
            # if the message is specified, return it
            return {
                "status": "success",
                "message": json_data["message"],
            }
        else:
            # if the message is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I couldn't understand your request. Please try again or describe it in a different way."
        }


###############################################################################

# STEP 50: Plot Function Selection

def select_plot_function(
    query : List[dict],
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You have access to a predefined set of Python plotting functions (see below) to fulfill the user query.
If there are referenced messages, use them to find the most appropriate function to solve the user query.

### ONLY Available Plotting Functions (Summarized):

{function_summaries}

### Task:

Select the most appropriate plot function from the list to visualize the result of the referenced function execution.
Respect the former function result's available plots in your function decision.
Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"plot_function": "<plot_function_name>" | None,
# ONLY specify an explanation if plot_function is None. Describe to the user directly why no plot function fits.
"explanation": "..."
}}

### Query:

{query}

### Your Response:
"""
    global current_client

    prompt = prompt_template.format(
        function_summaries=create_function_summaries(function_registry=plot_function_registry),
        query=query
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)
    
    print("50) LLM plot function selection:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_plot_function_selection(
    query: List[dict],
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = select_plot_function(query)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the plot function is specified
        if json_data.get("plot_function", None) is not None:
            # if the plot function is specified, return it
            return {
                "status": "success",
                "plot_function": json_data["plot_function"],
            }
        else:
            # if the plot function is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I couldn't understand your request. Please try again or describe it in a different way.",
            "explanation": json_data.get("explanation", None) 
        }

###############################################################################

# STEP 80: Execute Selected Plot Function

def validate_plot_function_execution():
    global function_data
    # try to generate a valid json response
    error = True
    generate_counter = 0

    plot_func = plot_function_registry[function_data["selected_function"]]
    last_data_message = None
    for message in reversed(function_data['referenced_messages']):
        if message.get("data", False) and message["data"].get("plotable", False):
            last_data_message = message

    if last_data_message is None:
        return {
            "status": "error",
            "message": "I could not identify a valid message with data to plot. Please try again or describe it in a different way."
        }
    else:
        last_FREF = FREF_from_dict(last_data_message["data"])

    # FIXME: DEBUG
    print("80) Executing function:", function_data["selected_function"], "with params:", function_data["function_parameters"], sep="\n")
    print("80) last_data_message:", last_data_message, sep="\n")
    print("80) Last data message available plots:", last_FREF.plot.available_plots, sep="\n")

    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the selected function
            # print("80) Last FREF:", last_FREF, sep="\n")  # FIXME: DEBUG
            response = generate_plot_for_function(
                function_result=last_FREF,
                additional_plot_args=function_data["function_parameters"],
                plot_to_generate=plot_func,
                use_default_plot=False
            )
            print("80) Function Execution Result:", response, sep="\n")  # FIXME: DEBUG
            error = False
        except Exception as e:
            print(f"Error while executing function {function_data['selected_function']}:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if the response is valid
        return {
            "status": "success",
            "function_result": response,
        }

    # abort after 5 insufficient tries
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": response.get("error_msg", "I could not process your request. Please try again or describe it in a different way.")
        }

###############################################################################

# STEP 100: Call LLM to select a function to solve the problem

def select_function(
    query: str,
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You have access to a predefined set of Python functions (see below) to answer user queries.
If there are referenced messages, use them to find the most appropriate function to solve the user query.

### ONLY Available Functions (Summarized):

{function_summaries}

### Task:

Select the most appropriate function from the list to solve the following user query.
Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"function": "<function_name>" | None,
# ONLY specify an explanation if function is None. Describe to the user directly why no function fits.
"explanation": "..."
}}

### Query:

{query}

### Your Response:
"""
    global function_data
    global current_client

    function_summaries = create_function_summaries(function_registry=function_data['function_registry'])

    prompt = prompt_template.format(
        function_summaries=function_summaries,
        query=query,
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)
    
    print("100) LLM function selection:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data


def validate_selected_function(
    query: str
):
    global function_data
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = select_function(query)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")                  
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the function is specified
        if json_data.get("function", None) is not None:
            # if the function is specified, return it
            return {
                "status": "success",
                "function": json_data["function"],
            }
        else:
            # if the function is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I couldn't understand your request. Please try again or describe it in a different way.",
            "explanation": json_data.get("explanation", None) 
        }

###############################################################################

# STEP 200: Confirm the selected function

def assess_function_usability(
    query: str,
    function_docstring: str,
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a user query and the docstring of a function to possibly solve the request.
There is also access to a dataset called `data` which you can assume to be available if needed.
If there are referenced messages, use them predominantly to assess the usability of the function.

### Function Docstring:

{function_docstring}

### Task:

Decide if the given function can be used to process the user request. Answer in a strict PYTHON DICT format as shown below.
- If you assume the function can not be used, set "status" to "abort".
- If you assume the function can be used, set "status" to "success".

### STRICT PXTHON DICT response format:
{{
"status": "abort | success",
# ONLY if the status is "abort", explain why the function can not be used.
"explanation": "..."
}}

Note: Avoid any conversational language!

### Query:

{query}

### Your Response:
"""
    global current_client

    prompt = prompt_template.format(
        function_docstring=function_docstring,
        query=query
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)

    print("200) LLM Function Assessment:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data
    

def validate_function_usability(
    query: str,
    function_docstring: str,
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = assess_function_usability(query, function_docstring)
            # parse the response as dict
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the usability is specified
        if json_data.get("status", "") == "abort" or json_data.get("status", "") == "success":
            # if the function is specified, return it
            return {
                "status": json_data["status"]
            }
        else:
            # if the usability is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error"
        }


###############################################################################

# STEP 300: Infer the parameters for the selected usable function

def infer_function_parameters(
    conv_hist: List[dict],
    function_docstring: str,
    function_name: str,
    function_registry: dict,
) -> dict:
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a conversation history with a user including a query.
You get the docstring of a function to solve the request.
There is also access to a dataset which you can assume to be available. DO NOT specify it in the parameters.
If there are referenced messages, use them predominantly to infer the parameters.

### Function Docstring:

{function_docstring}

### Task:

Infer the parameters for the given function based on the initial user query and potential additional information of the chat history.
Also use the given default values for the parameters if applicable. If default values are used, explain them to the user in the "assumptions" field of the response.
- If all the function parameters can be inferred, specify them in your answer. Set "status" to "success" in this case.
- If information is missing, mark it clearly with a placeholder and add a `missing_fields` list. Set "status" to "pending" in this case and provide an "explanation" field for the user.
- If the chat history can not be used to infer the parameters, set "status" to "abort" and leave the rest. Use this only as a last resort.

The python datetime module is available as `datetime` for e.g. timestamps if needed.

Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"status": "abort | pending | success",
"function": "{function_name}",
# DO NOT make any comments in the dict response.
"parameters": {{
{params}}},
# optional: ONLY if parameter information can not be inferred
"missing_fields": ["param1", "param2", ...],
# If there are missing fields, directly address the user and explain what you need.
"explanation": "..."
# optional: ONLY if "status" is "success" and default values are used, describe the assumptions to the user as you were speaking to them directly.
"assumptions": "..."
}}

### Conversation History:

{conv_hist}
"""
    global current_client

    # extract the parameters from the function docstring
    params = get_function_parameters(function_name, function_registry)
    params_str = ""
    for param in params[1:]:  # skip the first parameter (by definition 'data')
        params_str += f'  "{param}": <value>,\n'
    
    prompt = prompt_template.format(
        function_docstring=function_docstring,
        function_name=function_name,
        params=params_str,
        conv_hist=conv_hist
    )

    print("LLM prompt:", prompt, sep="\n")  # FIXME: DEBUG

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)    
    
    print("300) LLM Parameter Inferation:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_function_parameter_extraction(
    conv_hist: List[dict],
    function_docstring: str,
    function_name: str,
    function_registry: dict,
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = infer_function_parameters(
                conv_hist=conv_hist,
                function_docstring=function_docstring,
                function_name=function_name,
                function_registry=function_registry
            )
            # parse the response as JSON
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the usability is specified
        if json_data.get("status", "") in ["abort", "pending", "success"]:
            # if the function is specified, return it
            return json_data
        else:
            # if the usability is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient generations
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I couldn't understand your request. Please try again or describe it in a different way."
        }


###############################################################################

# STEP 400: Execute the selected function with the extracted parameters

def validate_function_execution(
    data: Dataset = None,
):
    global function_data
    # try to generate a valid json response
    error = True
    generate_counter = 0

    func = function_registry[function_data["selected_function"]]

    # FIXME: DEBUG
    print("400) Executing function:", function_data["selected_function"], "with params:", function_data["function_parameters"], sep="\n")

    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the selected function
            response = func(
                data=data,
                **function_data["function_parameters"]
            )
            print("400) Function Execution Result:", response, sep="\n")  # FIXME: DEBUG
            error = False
        except Exception as e:
            print(f"Error while executing function {function_data['selected_function']}:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if the response is valid
        return {
            "status": "success",
            "function_result": response,
        }

    # abort after 5 insufficient tries
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": response.get("error_msg", "I could not process your request. Please try again or describe it in a different way.")
        }


###############################################################################

# STEP 500: Describe the result of the function execution

def describe_function_result():
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a user query and some information about the executed function to solve the request.
To provide an answer to the query, you have to describe the function results in a way that the user can understand them. 

### User Query:

{question}

### Executed Function:

#### function name:
'{function_name}'

#### set function parameters:
{function_parameters}

#### parameter assumptions:
{function_parameter_assumptions}

### Function Result:

{function_result}

### Task:

Answer the user query by describing the function results. 
Do not use the underlying function name or parameter names to describe the results but their semantic.
If there were any assumptions made about the function parameters, explain them to the user without using variable names.
If the function result's field "plotted" is set to "True", a visualization of the result data will be provided to the user.
If the function result's field "plotable" is set to "True" AND "plotted" IS FALSE:
    - The user will get a table with the evaluated data result
    - NO PLOT will be generated
    - Ask the user if they want to see a plot of the result

Answer in a strict PYTHON DICT format as shown below.

### STRICT PYTHON DICT response format:
{{
"message": "<Your Answer to the user query>",
}}

### Your Response:
"""
    global function_data
    global current_client

    # prepare the prompt
    prompt = prompt_template.format(
        question=function_data["user_question"],
        function_name=function_data["selected_function"],
        function_parameters=json.dumps(function_data["function_parameters"], indent=2, default=str),
        function_parameter_assumptions=json.dumps(function_data["function_parameter_assumptions"], indent=2) if (
            function_data["function_parameter_assumptions"]) else "None",
        function_result={
            "data": True if function_data["function_execution_result"].get("data", False) else False,
            "plotable": function_data["function_execution_result"]["plotable"],
            "plotted": function_data["function_execution_result"]["plotted"],
        }
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=False
    )

    resp_data = clean_llm_output(response)
    
    print("500) LLM Function Result Description:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_function_result_description():
    # try to generate a valid json response
    error = True
    generate_counter = 0

    while error and generate_counter < 5:
        response = "<Error inside executed function>"
        try:
            # generate the response from the LLM
            response = describe_function_result()
            # parse the response as JSON
            json_data = eval(response)
            if not isinstance(json_data, dict):
                raise ValueError("Response is not a valid dictionary object.")
            error = False
        except Exception as e:
            print("Error while parsing the LLM response:", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the description is specified
        if json_data.get("message", None):
            return {
                "status": "success",
                "message": json_data["message"]
            }
        else:
            # if the description is not correctly specified, provoke an error
            generate_counter += 1
            error = True

    # abort after 5 insufficient tries
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": "I could not process your request. Please try again or describe it in a different way."
        }


###############################################################################

# ENTRY POINT FOR USER REQUESTS

def handleMessage(
    user_message: str,
    chat_data: ChatData,
    data: Dataset,
    model: dict = {'provider': 'google', 'model': 'gemini-2.0-flash-001'},
    START_STEP: int = 1,  # start with step 1
):
    # select model
    global current_model
    global current_client

    # save current chat history if applicable
    current_chat_history = current_client.chat_history if current_client else []

    # apply the selected model
    if current_model is None or current_model != model:
        current_model = model
        client = get_model_client(model['provider'])
        current_client = client(
            model=model['model'],
            chat_history=False,
            sys_msg=None,
            output_schema=None
        )
        # paste previous chat history if applicable
        current_client.chat_history = current_chat_history

    print("Using model:", current_client.model)  # FIXME: DEBUG

    STEP = START_STEP
    FUNCTIONS_DISCARDED = 0

    global function_data
    global PARAM_EXTRACTION_chat_history

    while STEP != 0:
        if STEP == 1:
            # STEP 1: Call LLM to select the correct next task

            # reset variables
            function_data = {}
            function_data["function_registry"] = copy.deepcopy(function_registry)
            PARAM_EXTRACTION_chat_history = []


            function_data['user_question'] = user_message
            
            task_selection_response = validate_next_task(
                user_message, 
                chat_data.filter_messages(
                    exclude_status=["error", "no_match"],
                    include_data=False,
                )[:-1] # use limited chat messages without the user query
            )

            if task_selection_response.get("status", "") == "error":
                # quit loop
                STEP = 0

                return {
                    "status": "error",
                    "message": task_selection_response.get("message", "I couldn't infer a task to solve your request. Please try again or describe it in a different way.")
                }
            elif task_selection_response.get("status", "") == "success":
                # save task type
                function_data['task'] = task_selection_response["task"]
                # continue with the next step based on the task
                if function_data['task'] == "execute_function":
                    STEP = 100  # continue with function selection
                elif function_data['task'] == "explain_former_result":
                    STEP = 10  # continue with the referenced message selection
                elif function_data['task'] == "execute_function_on_former_result":
                    STEP = 10
                elif function_data['task'] == "plot_former_result":
                    STEP = 10
                elif function_data['task'] == "execute_function_plan":
                    pass
                else:
                    STEP = 5

        if STEP == 5:
            # STEP 5: Let the LLM answer the query without any function and without any referenced messages

            response = validate_chat_answer(
                user_message, 
                chat_data.filter_messages(
                    exclude_status=["error", "no_match"],
                    include_data=False,
                )[:-1]  # use limited chat messages without the user query
            )

            if response.get("status", "") == "error":
                # quit loop
                STEP = 0

                return {
                    "status": "error",
                    "message": response.get("message", "I could not process your request. Please try again or describe it in a different way.")
                }
            else:
                # quit loop
                STEP = 0

                return response

        if STEP == 10:
            # STEP 10: Decide on the message to explain referenced by the user query
            referenced_messages_response = validate_referenced_messages(
                user_message, 
                chat_data.filter_messages(
                    exclude_status=["error", "no_match"],
                    include_data=False,
                )[:-1]
            )

            if referenced_messages_response.get("status", "") == "error":
                # quit loop
                STEP = 0

                return {
                    "status": "error",
                    "message": referenced_messages_response.get(
                        "message", 
                        "I couldn't infer the message referenced in your request. Please try again or describe it in a different way."
                    )
                }
            elif referenced_messages_response.get("status", "") == "success":
                # save the message ID for the next step
                function_data['referenced_message_ids'] = referenced_messages_response["message_ids"]
                function_data['referenced_messages'] = chat_data.filter_messages(
                    include_ids=function_data['referenced_message_ids'],
                    include_data=True,
                    sort="asc",
                )
                function_data['referenced_messages_stripped'] = chat_data.filter_messages(
                    include_ids=function_data['referenced_message_ids'],
                    include_data=False,
                    sort="asc",
                )
                
                if function_data['task'] == "explain_former_result":
                    # continue with the next step to explain the referenced message
                    STEP = 30
                elif function_data['task'] == "plot_former_result":
                    # continue with the next step to plot the referenced message
                    STEP = 50
                elif function_data['task'] == "execute_function_on_former_result":
                    # continue with the next step to execute a function on the referenced message
                    STEP = 100 

        if STEP == 30:
            # STEP 30: Call LLM to further explain the specified messages to the user
            explanation_response = validate_referenced_message_explanation(
                user_message, 
                function_data['referenced_messages_stripped'],
            )

            if explanation_response.get("status", "") == "error":
                # quit loop
                STEP = 0

                return {
                    "status": "error",
                    "message": explanation_response.get(
                        "message", 
                        "I could not understand your request. Please try again or describe it in a different way."
                    )
                }
            else:
                # quit loop
                STEP = 0

                return explanation_response

        if STEP == 50:
            # STEP 50: Choose the desired plot type function for the referenced messages

            # prepare system message
            query = [
                {
                    "role": "system",
                    "user_query": function_data['user_question']
                },
                {
                    "role": "system",
                    "referenced_messages": function_data['referenced_messages_stripped']
                }
            ]
            # call LLM to select the plot function
            function_selection_response = validate_plot_function_selection(query)

            if function_selection_response.get("status", "error") == "error":
                message = function_selection_response.get("message")
                if function_selection_response.get("explanation", None):
                    message += " " + function_selection_response["explanation"]

                # quit loop
                STEP = 0

                return {
                    "status": "no_match",
                    "message": message
                }

            # save the selected function for the next step
            function_data['selected_function'] = function_selection_response.get("plot_function", None)
            STEP = 60
        
        if STEP == 60:
            # STEP 60: Confirm the selected plot function
            function_docstring = get_function_docstring(
                function_data["selected_function"], plot_function_registry
            )
            
            print("60) Selected function docstring:", function_docstring, sep="\n")  # FIXME: DEBUG
            function_data['function_docstring'] = function_docstring
            
            # assess the usability of the selected plot function
            query = [
                {
                    "role": "system",
                    "user_query": function_data['user_question']
                },
                {
                    "role": "system",
                    "referenced_messages": function_data['referenced_messages_stripped']
                }
            ]
            response = validate_function_usability(
                query=query,
                function_docstring=function_docstring,
            )

            # if the response could not be parsed
            if response.get("status", "") == "error":
                # FIXME: DEBUG
                print("Function usability assessment failed. Aborting.")
                FUNCTIONS_DISCARDED += 1
                STEP = 50
                continue
            # if the function is not usable, discard it and try to find another one
            elif response.get("status", "") == "abort":
                FUNCTIONS_DISCARDED += 1
                STEP = 50

                if FUNCTIONS_DISCARDED >= 5:
                    # quit loop
                    STEP = 0

                    return {
                        "status": "error",
                        "message": "I couldn't find a suitable function to solve your request. Please try again or describe it in a different way."
                    }
                continue
            # if the function is usable, continue to the next step
            elif response.get("status", "") == "success":
                STEP = 70
        
        if STEP == 70:
            # STEP 70: Infer the parameters for the selected usable plot function

            # prepare the chat history for the parameter extraction
            # if the task is to execute a function on referenced messages and previous data, the messages are appended 
            if not PARAM_EXTRACTION_chat_history:
                PARAM_EXTRACTION_chat_history.append({
                    "role": "system",
                    "user_query": user_message
                })
                PARAM_EXTRACTION_chat_history.append({
                    "role": "system",
                    "referenced_messages": function_data['referenced_messages_stripped']
                })
            else:
                # conversation history is not empty, i.e the user is responding to a previous message
                PARAM_EXTRACTION_chat_history.append({
                    "role": "user",
                    "message": user_message
                })

            response = validate_function_parameter_extraction(
                conv_hist=PARAM_EXTRACTION_chat_history,
                function_docstring=function_data['function_docstring'],
                function_name=function_data["selected_function"],
                function_registry=plot_function_registry,
            )

            # if the response could not be parsed
            if response.get("status", "") == "error":
                return response
            # if the function is not usable, discard it and try to find another one
            elif response.get("status", "") == "abort":
                FUNCTIONS_DISCARDED += 1
                STEP = 50

                if FUNCTIONS_DISCARDED >= 5:
                    # quit loop
                    STEP = 0

                    return {
                        "status": "error",
                        "message": "I couldn't find a suitable function to solve your request. Please try again or describe it in a different way."
                    }
            # if the function parameters could not be extracted entirely
            elif response.get("status", "") == "pending":
                # if the function is pending, ask the user for the missing fields
                message = ""
                if response.get("explanation", None):
                    message = response["explanation"]
                else:
                    missing = ", ".join(response.get("missing_fields", []))
                    message = f"Please provide the following missing information: {missing}."

                # update the chat history with the assistant message:
                PARAM_EXTRACTION_chat_history.append({
                    "role": "assistant",
                    "message": message
                })
                
                return {
                    "status": "ask_user",
                    "missing_fields": response.get("missing_fields", []),
                    "message": message,
                    "NEXT_STEP": 70,  # continue with STEP 70 on the next user message
                }
            elif response.get("status", "") == "success":
                # clean the response from a potentially existing data field, since
                # the data is inherited from the last data message in the reference 
                if "data" in response.get("parameters", {}):
                    del response["parameters"]["data"]

                # save the extracted parameters and assumptions for the next step
                function_data["function_parameters"] = response["parameters"]
                function_data["function_parameter_assumptions"] = response.get("assumptions", None)
                # if the function is valid, execute it in the next step
                STEP = 80

        if STEP == 80:
            # STEP 80: Execute the selected function with the extracted parameters
            response = validate_plot_function_execution()

            if response.get("status", "") == "error":
                # quit loop
                STEP = 0

                return {
                    "status": "error",
                    "message": response.get("message", "I could not process your request. Please try again or describe it in a different way.")
                }
            else:
                # continue to the next step to describe the result
                function_data['function_execution_result'] = response["function_result"]
                STEP = 500

        if STEP == 100:
            # STEP 100: Call LLM to select a function to solve the problem

            # prepare system message
            if function_data["task"] == "execute_function_on_former_result":
                message = [
                    {
                        "role": "system",
                        "user_query": function_data['user_question']
                    },
                    {
                        "role": "system",
                        "referenced_messages": function_data['referenced_messages_stripped']
                    }
                ]
            else:
                message = function_data['user_question']

            function_selection_response = validate_selected_function(message)

            if function_selection_response.get("status", "error") == "error":
                message = function_selection_response.get("message")
                if function_selection_response.get("explanation", None):
                    message += " " + function_selection_response["explanation"]

                # quit loop
                STEP = 0

                return {
                    "status": "no_match",
                    "message": message
                }

            # save the selected function for the next step
            function_data['selected_function'] = function_selection_response.get("function", None)
            STEP = 200

        if STEP == 200:
            # STEP 200: Confirm the selected function
            function_docstring = get_function_docstring(
                function_data["selected_function"], function_data["function_registry"]
            )
            
            # this case should not occur since the invalid functions have already
            # been removed from the function registry in STEP 100
            if not function_docstring:
                # quit loop
                STEP = 0

                return {
                    "status": "error",
                    "message": f"The function {function_data['selected_function']} does not exist or has no documentation."
                }
            else:
                # save the function docstring for the next step
                function_data['function_docstring'] = function_docstring
            
            # assess the usability of the selected function
            if function_data['task'] == "execute_function_on_former_result":
                message = [
                    {
                        "role": "system",
                        "user_query": function_data['user_question']
                    },
                    {
                        "role": "system",
                        "referenced_messages": function_data['referenced_messages_stripped']
                    }
                ]
            else:
                message = function_data['user_question']
            response = validate_function_usability(
                query=message,
                function_docstring=function_docstring,
            )

            # if the response could not be parsed
            if response.get("status", "") == "error":
                # FIXME: DEBUG
                print("Function usability assessment failed. Aborting.")
                del function_data["function_registry"][function_data["selected_function"]]
                FUNCTIONS_DISCARDED += 1
                STEP = 100
                continue
            # if the function is not usable, discard it and try to find another one
            elif response.get("status", "") == "abort":
                del function_data["function_registry"][function_data["selected_function"]]
                FUNCTIONS_DISCARDED += 1
                STEP = 100

                if FUNCTIONS_DISCARDED >= 5:
                    # quit loop
                    STEP = 0

                    return {
                        "status": "error",
                        "message": "I couldn't find a suitable function to solve your request. Please try again or describe it in a different way."
                    }
                continue
            # if the function is usable, continue to the next step
            elif response.get("status", "") == "success":
                STEP = 300

        if STEP == 300:
            # STEP 300: Infer the parameters for the selected usable function

            # prepare the chat history for the parameter extraction
            # if the task is to execute a function on referenced messages and previous data, the messages are appended 
            if not PARAM_EXTRACTION_chat_history and (
                function_data['task'] in ["execute_function_on_former_result", "plot_former_result"]):
                PARAM_EXTRACTION_chat_history.append({
                    "role": "system",
                    "user_query": user_message
                })
                PARAM_EXTRACTION_chat_history.append({
                    "role": "system",
                    "referenced_messages": function_data['referenced_messages_stripped']
                })
            else:  # conversation history is not empty, i.e the user is responding to a previous message
                PARAM_EXTRACTION_chat_history.append({
                    "role": "user",
                    "message": user_message
                })
            
            response = validate_function_parameter_extraction(
                conv_hist=PARAM_EXTRACTION_chat_history,
                function_docstring=function_data['function_docstring'],
                function_name=function_data["selected_function"],
                function_registry=function_data['function_registry'],
            )

            # if the response could not be parsed
            if response.get("status", "") == "error":
                return response
            # if the function is not usable, discard it and try to find another one
            elif response.get("status", "") == "abort":
                del function_data["function_registry"][function_data["selected_function"]]
                FUNCTIONS_DISCARDED += 1
                STEP = 100

                if FUNCTIONS_DISCARDED >= 5:
                    # quit loop
                    STEP = 0

                    return {
                        "status": "error",
                        "message": "I couldn't find a suitable function to solve your request. Please try again or describe it in a different way."
                    }
            # if the function parameters could not be extracted entirely
            elif response.get("status", "") == "pending":
                # if the function is pending, ask the user for the missing fields
                message = ""
                if response.get("explanation", None):
                    message = response["explanation"]
                else:
                    missing = ", ".join(response.get("missing_fields", []))
                    message = f"Please provide the following missing information: {missing}."

                # update the chat history with the assistant message:
                PARAM_EXTRACTION_chat_history.append({
                    "role": "assistant",
                    "message": message
                })
                
                return {
                    "status": "ask_user",
                    "missing_fields": response.get("missing_fields", []),
                    "message": message,
                    "NEXT_STEP": 300,  # continue with STEP 300 on the next user message
                }
            elif response.get("status", "") == "success":
                # if the function is valid, execute it in the next step
                # clear any unwanted data
                if "data" in response.get("parameters", {}):
                    del response["parameters"]["data"]
                function_data["function_parameters"] = response["parameters"]
                function_data["function_parameter_assumptions"] = response.get("assumptions", None)
                STEP = 400

        if STEP == 400:
            # STEP 400: Execute the selected function with the extracted parameters
            response = validate_function_execution(data=data)

            # if the function execution failed
            if response.get("status", "error") == "error":
                return {
                    "status": "error",
                    "message": response.get("error_msg", "I could not process your request. Please try again or describe it in a different way.")
                }
            else:
                function_data["function_execution_result"] = response["function_result"]
                STEP = 500
        
        if STEP == 500:
            # STEP 500: Return the result of the function execution
            response = validate_function_result_description()
            
            # if the function result description failed
            if response.get("status", "error") == "error":
                return {
                    "status": "error",
                    "message": response.get(
                        "message", 
                        "I could not process your request. Please try again or describe it in a different way."
                    )
                }
            elif response.get("status", "") == "success":
                response["data"] = function_data["function_execution_result"]

            # quit request loop
            STEP = 0

            return response
    

###############################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask a question to the desk booking analytics assistant.")
    parser.add_argument('--question', type=str, required=True, help='The user query to be analyzed and executed.')

    args = parser.parse_args()

    result = main(args.question)
    
    print(result)