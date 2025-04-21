from llm_api import *

llm_c = GoogleClient(
    model= 'gemini-2.0-flash-001',  #  'gemini-2.0-flash-001', 'llama3-70b-8192',
    chat_history=True,
    sys_msg="You are an assistant of a office desk occupation analysis tool. Extract the user\'s request information and use the following schema at all times to provide the answer directly in json format.", #  Fill not applicable fields with None.
    output_schema={
        'required': [
            'desk_id',
            'room_id',
            'begin_time',
            'end_time',
            'person',
            'aggregation',
            'function_id'
        ],
        'properties': {
            'desk_id': {'type': 'INTEGER'},
            'room_id': {'type': 'INTEGER'},
            'begin_time': {'type': 'STRING', 'format': 'DD-MM-YYYY'},
            'end_time': {'type': 'STRING', 'format': 'DD-MM-YYYY'},
            'person': {'type': 'STRING'},
            'aggregation': {'type': 'STRING'},
            'function_id': {'type': 'INTEGER'}
        },
    }
)

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "exit()":
        break
    
    response = llm_c.chat_completion(input_str=user_input,response_json=True)
    
    print("Assistant:", response)

llm_c.conv_to_json("conv_3")