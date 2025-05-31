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
    create_function_summaries, 
    get_function_docstring, 
    get_function_parameters
)
from deskquery.data.dataset import Dataset
from deskquery.llm.llm_api import LLM_Client, get_model_client, get_model_providers

global current_model
current_model = None
global current_client
current_client = None
global function_data
function_data = {
    'function_registry': copy.deepcopy(function_registry),
    'user_question': None,
    'selected_function': None,
    'function_docstring': None,
    'function_parameters': None,
    'function_parameter_assumptions': None
}
global STEP_3_PARAM_EXTRACTION_chat_history
STEP_3_PARAM_EXTRACTION_chat_history = []


def call_llm_and_execute(
    question: str, 
    function_summaries: str, 
    example_querys: str,
    client: LLM_Client = current_client,
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You have access to a predefined set of Python functions (see below).  

Your job is to:
1. Understand the user query.
2. Select the most appropriate function from the list (NEVER invent your own).
3. Fill in the parameters based on what the user has provided or can be reasonably assumed.
3.1 The current timestamp is '{timestamp}' if it might be needed for date specification.
4. If information is missing, mark it clearly with a placeholder and add a `missing_fields` list.
5. If no suitable function exists, return `"function": null` and `"reason"` explaining why.

### ONLY Available Functions (Summarized):

{function_summaries}

---

### STRICT JSON response format [Do not specify it explicitly]:
{{
"function": "function_name_or_null",
"parameters": {{ "param1": "...", "param2": "..." }},
# optional:
"missing_fields": ["..."],
# Only necessary if function is null or clarification is needed. If there are missing fields, explain what they are.
"reason": "..."
# Any optional notes for the user. If you executed code successfully, explain what you did.
"explanation": "..."
}}

Note: Avoid any conversational language!

---

### User Query:
{question}

---

### Old Example user querys with corosponding answer:
{example_querys_with_answers}

---

### Your Response:
"""
    
    prompt = prompt_template.format(            # fill in the variables in the string
        timestamp=datetime.now().isoformat(),
        function_summaries = function_summaries,
        question = question,
        example_querys_with_answers = example_querys
    )

    # print("LLM prompt:", prompt)  # FIXME: DEBUG
    
    response = client.chat_completion(
        input_str=prompt,
        role='user',
        response_json=False  # FIXME
    )
    # clean potentially unwanted content from the response string
    cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    code = cleaned_response.strip('` \n')
    # print("LLM response:", code)  # FIXME: DEBUG

    return code


def handle_llm_response(response: dict):
    
    if response.get("function") is None:
        return {
            "status": "no_match",
            "message": response.get("reason", "I couldn't find a suitable function.")
        }

    if response.get("missing_fields"):
        missing = ", ".join(response["missing_fields"])
        message = ""
        if response.get("reason"):
            message = response["reason"]
        else:
            message = f"Please provide the following fields: {missing}."
        if response.get("explanation"):
            if not message.endswith("."):
                message += ". "
            else:
                message += " "
            message += response["explanation"]
        return {
            "status": "ask_user",
            "message": message,
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
    # FIXME: Adjust if needed
    return response_as_json.get("message")


def main(
    question: str,
    data: Dataset,
    model: dict = {'provider': 'google', 'model': 'gemini-2.0-flash-001'},
    START_STEP: int = 1,  # start with step 1
):
    function_summaries_path = Path(__file__).resolve().parent / 'functions' / 'function_summaries_export.txt'
    with open(function_summaries_path, 'r') as f:
        function_summaries = f.read()

    example_querys = "" # TODO generate some example queries with the correct format for the answer

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

    ### Request Handling test
    result = handleMessage(question, data, model, START_STEP)
    ###

    # execution_params = {
    #     "question": question,
    #     "function_summaries": function_summaries,
    #     "example_querys": example_querys,
    #     "client": current_client
    # }

    # # try to generate a valid json response
    # error = True
    # generate_counter = 0
    # while error and generate_counter < 5:
    #     try:
    #         llm_response_str = call_llm_and_execute(
    #             **execution_params
    #         )
    #         llm_response = json.loads(llm_response_str)
    #         error = False
    #     except json.JSONDecodeError as e:
    #         print("Error while parsing the LLM response:", e)
    #         print("Raw response was:", llm_response_str, sep="\n")
    #         error = True
    #         generate_counter += 1

    # # abort after 5 insufficient generations
    # if error and generate_counter >= 5:
    #     return {
    #         "status": "error",
    #         "message": "I couldn't understand your request. Please try describing it in a different way."
    #     }

    # result_as_json = handle_llm_response(llm_response)

    # result_as_text = response_into_text(result_as_json)

    return result

###############################################################################
# USER REQUEST HANDLING
###############################################################################

# STEP 1: Call LLM to select a function to solve the problem

def selectFunction(
    question: str,
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You have access to a predefined set of Python functions (see below) to answer user querries.

### ONLY Available Functions (Summarized):

{function_summaries}

### Task:

Select the most appropriate function from the list to solve the following user query.
Answer in a strict JSON format as shown below.

### STRICT JSON response format [Do not specify it explicitly as JSON]:
{{
"function": "function_name_or_null",
# ONLY specify an explanation if function is null. Describe why no function fits.
"explanation": "..."
}}

### User Query:

{question}

### Your Response:
"""
    global function_data
    global current_client

    function_summaries = create_function_summaries(function_registry=function_data['function_registry'])

    prompt = prompt_template.format(
        function_summaries=function_summaries,
        question=question
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='user',
        response_json=True
    )

    # clean potentially unwanted content from the response string
    cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    resp_data = cleaned_response.strip('` \n')
    
    print("1) LLM function selection:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data


def validate_selected_function(
    question: str
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        try:
            # generate the response from the LLM
            response = selectFunction(question)
            # parse the response as JSON
            json_data = json.loads(response)
            error = False
        except json.JSONDecodeError as e:
            print("Error while parsing the LLM response:", e)
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

# STEP 2: Check the selected function and extract the needed parameters

def assess_function_usability(
    question: str,
    function_docstring: str,
):
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a user query and the docstring of function to possibly solve the request.
There is also access to a dataset called `data` which you can assume to be available if needed.

### Function Docstring:

{function_docstring}

### Task:

Decide if the given function can be used to process the user request. Answer in a strict JSON format as shown below.
- If you assume the function can not be used, set "status" to "abort".
- If you assume the function can be used, set "status" to "success".

### STRICT JSON response format [Do not specify it explicitly as JSON]:
{{
"status": "abort | success",
}}

Note: Avoid any conversational language!

### User Query:

{question}

### Your Response:
"""
    global current_client

    prompt = prompt_template.format(
        function_docstring=function_docstring,
        question=question
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='user',
        response_json=True
    )

    # clean potentially unwanted content from the response string
    cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    resp_data = cleaned_response.strip('` \n')
    
    print("2) LLM Function Assessment:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data
    

def validate_function_usability(
    question: str,
    function_docstring: str,
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        try:
            # generate the response from the LLM
            response = assess_function_usability(question, function_docstring)
            # parse the response as JSON
            json_data = json.loads(response)
            error = False
        except json.JSONDecodeError as e:
            print("Error while parsing the LLM response:", e)
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the usability is specified
        if json_data.get("status", None) == "abort" or json_data.get("status", None) == "success":
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

# STEP 3: Infer the parameters for the selected usable function

def infer_function_parameters(
    conv_hist: List[dict],
    function_docstring: str,
    function_name: str,
) -> dict:
    prompt_template = """
You are a smart assistant for a desk booking analytics system.
You are given a conversation history with a user including a query.
You get the docstring of a function to solve the request.
There is also access to a dataset which you can assume to be available. DO NOT specify it in the parameters.

### Function Docstring:

{function_docstring}

### Task:

Infer the parameters for the given function based on the initial user query and potential additional information of the chat history.
Also use the given default values for the parameters if applicable. If default values are used, explain them to the user in the "assumptions" field of the response.
- If all the function parameters can be inferred, specify them in your answer. Set "status" to "success" in this case.
- If information is missing, mark it clearly with a placeholder and add a `missing_fields` list. Set "status" to "pending" in this case and provide an "explanation" field for the user.
- If the chat history can not be used to infer the parameters, set "status" to "abort" and leave the rest. Use this only as a last resort.

The python datetime module is available as `datetime` for time timestamps if needed.

Answer in a strict JSON format as shown below.

### STRICT JSON response format [Do not specify it explicitly as JSON but provide valid JSON]:
{{
"status": "abort | pending | success",
"function": "{function_name}",
# for paramter definitions, put strings in extra quotes, e.g. "param1": "\'<str_value>\'" and everything else in one quotes, e.g. "param2": "<int_value>".
# Write values in Python syntax if applicable, e.g. "param3": "<list_value>".
# Do not make any comments in the JSON response.
"parameters": {{
{params}}},
# optional: ONLY if parameter information can not be inferred
"missing_fields": [param1, param2, ...],
# If there are missing fields, explain what they are and what you need from the user.
"explanation": "..."
# optional: ONLY if "status" is "success" and default values are used, describe the assumptions to the user.
"assumptions": "..."
}}

### Conversation History:
{conv_hist}
"""
    global current_client

    # extract the parameters from the function docstring
    params = get_function_parameters(function_name)
    params_str = ""
    for param in params[1:]:  # skip the first parameter (by definition 'data')
        params_str += f'  {param}: "<value>",\n'
    
    prompt = prompt_template.format(
        function_docstring=function_docstring,
        function_name=function_name,
        params=params_str,
        conv_hist=conv_hist
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=True
    )

    # clean potentially unwanted content from the response string
    cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    resp_data = cleaned_response.strip('` \n')
    
    print("3) LLM Parameter Inferation:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_function_parameter_extraction(
    conv_hist: List[dict],
    function_docstring: str,
    function_name: str,
):
    # try to generate a valid json response
    error = True
    generate_counter = 0
    while error and generate_counter < 5:
        try:
            # generate the response from the LLM
            response = infer_function_parameters(
                conv_hist=conv_hist,
                function_docstring=function_docstring,
                function_name=function_name
            )
            # parse the response as JSON
            json_data = json.loads(response)
            error = False
        except json.JSONDecodeError as e:
            print("Error while parsing the LLM response:", e)
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # if json loaded fine, check if the usability is specified
        if json_data.get("status", None) in ["abort", "pending", "success"]:
            # if the function is specified, return it
            if json_data["status"] == "success" and json_data.get("parameters", None):
                print("3) Parsing parameters to python objects...")  # FIXME: DEBUG
                for param in json_data["parameters"]:
                    # imply the parameter type by python evaluation
                    try:
                        if not isinstance(json_data["parameters"][param], str):
                            json_data["parameters"][param] = str(json_data["parameters"][param])
                        json_data["parameters"][param] = eval(json_data["parameters"][param])
                    except Exception as e:
                        print(f"Error while parsing parameter '{param}':", e)
                        traceback.print_exc()
                        generate_counter += 1
                        error = True
                        break
                else:
                    return json_data
                continue
            else:
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

# STEP 4: Execute the selected function with the extracted parameters

def validate_function_execution(
    data: Dataset = None,
):
    global function_data
    # try to generate a valid json response
    error = True
    generate_counter = 0

    func = function_registry[function_data["selected_function"]]

    # FIXME: DEBUG
    print("4) Executing function:", function_data["selected_function"], "with params:", function_data["function_parameters"], sep="\n")

    while error and generate_counter < 5:
        try:
            # generate the response from the selected function
            response = func(
                data=data,
                **function_data["function_parameters"]
            )
            print("4) Function Execution Result:", response, sep="\n")  # FIXME: DEBUG
            error = False
        except Exception as e:
            print(f"Error while executing function '{function_data["selected_function"]}':", e)
            traceback.print_exc()  # Print the stack trace to the console
            print("Raw response was:", response, sep="\n")
            error = True
            generate_counter += 1
            continue
        
        # check if there is a function internal error
        if not response.get("error", 0):
            # if the function executed successfully, return the response
            return response
        else:
            # if there is an error, provoke an error for the loop
            generate_counter += 1
            error = True

    # abort after 5 insufficient tries
    if error and generate_counter >= 5:
        return {
            "status": "error",
            "message": response.get("error_msg", "I could not process your request. Please try again or describe it in a different way.")
        }


###############################################################################

# STEP 5: Describe the result of the function execution

def describe_function_result():
    global function_data
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
If there were any assumptions made about the function parameters, explain them to the user.
If the function result contains the field "plotable" set to true, ask the user if they want to see a plot of the result.

Answer in a strict JSON format as shown below.

### STRICT JSON response format [Do not specify it explicitly as JSON]:
{{
"message": "Your Answer to the user query",
}}

### Your Response:
"""
    global current_client

    # prepare the prompt
    prompt = prompt_template.format(
        question=function_data["user_question"],
        function_name=function_data["selected_function"],
        function_parameters=json.dumps(function_data["function_parameters"], indent=2),
        function_parameter_assumptions=json.dumps(function_data["function_parameter_assumptions"], indent=2) if (
            function_data["function_parameter_assumptions"]) else "None",
        function_result=json.dumps(function_data["function_execution_result"], indent=2)
    )

    response = current_client.chat_completion(
        input_str=prompt,
        role='system',
        response_json=True
    )

    # clean potentially unwanted content from the response string
    cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    resp_data = cleaned_response.strip('` \n')
    print("5) LLM Function Result Description:", resp_data, sep="\n")  # FIXME: DEBUG

    return resp_data

def validate_function_result_description():
    # try to generate a valid json response
    error = True
    generate_counter = 0

    while error and generate_counter < 5:
        try:
            # generate the response from the LLM
            response = describe_function_result()
            # parse the response as JSON
            json_data = json.loads(response)
            error = False
        except json.JSONDecodeError as e:
            print("Error while parsing the LLM response:", e)
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
    global STEP_3_PARAM_EXTRACTION_chat_history

    while STEP != 0:
        if STEP == 1:
            # STEP 1: Call LLM to select a function to solve the problem 
            function_selection_response = validate_selected_function(user_message)

            if function_selection_response.get("status") == "error":
                return {
                    "status": "no_match",
                    "message": function_selection_response.get("message"),
                    "explanation": function_selection_response.get("explanation", None)
                }

            # save the selected function for the next step
            function_data['selected_function'] = function_selection_response.get("function", None)
            function_data['user_question'] = user_message
            STEP = 2

        if STEP == 2:
            # STEP 2: Check the selected function and extract the needed parameters
            function_docstring = get_function_docstring(
                function_data["selected_function"], function_data["function_registry"]
            )
            
            # this case should not occur since the invalid functions have already
            # been removed from the function registry in STEP 1
            if not function_docstring:
                return {
                    "status": "error",
                    "message": f"The function '{function_data["selected_function"]}' does not exist or has no documentation."
                }
            else:
                # save the function docstring for the next step
                function_data['function_docstring'] = function_docstring
            
            # assess the usability of the selected function
            response = validate_function_usability(
                question=user_message,
                function_docstring=function_docstring,
            )

            # if the response could not be parsed
            if response.get("status") == "error":
                # FIXME: DEBUG
                print("Function usability assessment failed. Aborting.")
                del function_data["function_registry"][function_data["selected_function"]]
                FUNCTIONS_DISCARDED += 1
                STEP = 1
                continue
            # if the function is not usable, discard it and try to find another one
            elif response.get("status") == "abort":
                del function_data["function_registry"][function_data["selected_function"]]
                FUNCTIONS_DISCARDED += 1
                STEP = 1

                if FUNCTIONS_DISCARDED >= 5:
                    return {
                        "status": "error",
                        "message": "I couldn't find a suitable function to solve your request. Please try again or describe it in a different way."
                    }
                continue
            # if the function is usable, continue to the next step
            elif response.get("status") == "success":
                STEP = 3

        if STEP == 3:
            # STEP 3: Infer the parameters for the selected usable function
            STEP_3_PARAM_EXTRACTION_chat_history.append({
                "role": "user",
                "message": user_message
            })
            
            response = validate_function_parameter_extraction(
                conv_hist=STEP_3_PARAM_EXTRACTION_chat_history,
                function_docstring=function_data['function_docstring'],
                function_name=function_data["selected_function"]
            )

            # if the response could not be parsed
            if response.get("status") == "error":
                return response
            # if the function is not usable, discard it and try to find another one
            elif response.get("status") == "abort":
                del function_data["function_registry"][function_data["selected_function"]]
                FUNCTIONS_DISCARDED += 1
                STEP = 1

                if FUNCTIONS_DISCARDED >= 5:
                    return {
                        "status": "error",
                        "message": "I couldn't find a suitable function to solve your request. Please try again or describe it in a different way."
                    }
            # if the function parameters could not be extracted entirely
            elif response.get("status") == "pending":
                # if the function is pending, ask the user for the missing fields
                message = ""
                if response.get("explanation", None):
                    message = response["explanation"]
                else:
                    missing = ", ".join(response.get("missing_fields", []))
                    message = f"Please provide the following missing information: {missing}."

                # update the chat history with the assistant message:
                STEP_3_PARAM_EXTRACTION_chat_history.append({
                    "role": "assistant",
                    "message": message
                })
                
                return {
                    "status": "ask_user",
                    "missing_fields": response.get("missing_fields", []),
                    "message": message,
                    "NEXT_STEP": 3,  # continue with STEP 3 on the next user message
                }
            elif response.get("status") == "success":
                # if the function is valid, execute it in the next step
                function_data["function_parameters"] = response["parameters"]
                function_data["function_parameter_assumptions"] = response.get("assumptions", None)
                STEP = 4

        if STEP == 4:
            # STEP 4: Execute the selected function with the extracted parameters
            response = validate_function_execution(data=data)

            # if the function execution failed
            if not response.get("error", 1):
                return {
                    "status": "error",
                    "message": response["message"]
                }
            else:
                function_data["function_execution_result"] = response
                STEP = 5
        
        if STEP == 5:
            # STEP 5: Return the result of the function execution
            response = validate_function_result_description()
                
            # reset local variables for the next request
            function_data = {
                'function_registry': copy.deepcopy(function_registry),
                'user_question': None,
                'selected_function': None,
                'function_docstring': None,
                'function_parameters': None,
                'function_parameter_assumptions': None
            }
            STEP_3_PARAM_EXTRACTION_chat_history = []
            STEP = 0

            return response
    

###############################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask a question to the desk booking analytics assistant.")
    parser.add_argument('--question', type=str, required=True, help='The user query to be analyzed and executed.')

    args = parser.parse_args()

    # TODO: add model decision logic[?]
    result = main(args.question)
    
    print(result)