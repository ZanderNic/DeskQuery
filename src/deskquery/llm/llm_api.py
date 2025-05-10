import os
from dotenv import load_dotenv
from abc import ABC, abstractmethod
import json

from groq import Groq
from google import genai
from google.genai import types


class LLM_Client(ABC):

    model: str
    chat_history: list = None
    
    @abstractmethod
    def __init__(
        self,
        model: str,
        chat_history: bool = True,
        sys_msg: str = None,
        output_schema: str = None
    ):
        """
        Creates a model client and initializes the chat with a system message
        and output schema if desired.

        Parameters
        ----------
            model: str
                The model to be used with the client.
            chat_history: bool
                If True, the chat history will be saved.
                If False, every input message and response will be a new chat.
            sys_msg: str
                The system message to be used with the model.
                This message will be used as the first message in the chat.
            output_schema: str
                The output schema to be used with the model.
                This message will be used as the second message in the chat.
        """
        pass
    
    @abstractmethod
    def chat_completion(
        self, 
        input_str: str, 
        role: str = 'user',
        response_json: bool = False
    ) -> str:
        """
        Provides a chat response to a given input calling the asynchronous
        function `_get_response()`.
        The role associated with the input message can usually be defined
        to either `system`, `user` or `assistant`.
        
        Parameters
        ----------
            input_str: str
                The input message to be sent to the model.
            role: str
                The role of the input message. Can be either `system`,
                `user` or `assistant`.
            response_json: bool
                If True, the response will be returned as a json object.
                If False, the response will be returned as a string.
                
        Returns
        -------
            response: str
                The model response string
        """
        pass
    
    def conv_to_json(
        self,
        filename: str
    ):
        """
        Saves the current conversation history to `json` format if a chat
        history exists.

        Parameters
        ----------
            filename: str
                The name of the json file to save the chat history to.
                If None, defaults to `chat_history.json` in the current
                directory.
        """
        if self._chf:
            fn = filename if filename.endswith('.json') else filename + '.json'
            with open(fn, 'w') as json_file:
                json.dump(self.chat_history, json_file, indent=2)
    

class GroqClient(LLM_Client):

    def __init__(
        self,
        model: str = 'llama3-70b-8192',
        chat_history: bool = True,
        sys_msg: str = None,
        output_schema: str = None
    ):
        self.model = model if model else 'llama3-8b-8192'
        if chat_history:
            self._chf = True
            self.chat_history = []
        else:
            self._chf = False
            self.chat_history = None
        self.output_schema = output_schema
        
        load_dotenv()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        if self._chf:
            if sys_msg:
                self.chat_completion(sys_msg, 'system')
            if output_schema:
                self.chat_completion(
                    f'Use this following json schema to provide your answers:\n{output_schema}',
                    'system'
                )
        else:
            self._sys_msg = ""
            if sys_msg:
                self._sys_msg += sys_msg
            if self.output_schema:
                self._sys_msg += f'\n\nUse this following json schema to provide your answers:\n{self.output_schema}'
    
    def chat_completion(
        self, 
        input_str: str, 
        role: str = 'user',
        response_json: bool = False
    ) -> str:
        if self._chf:
            self.chat_history.append({"role": role, "content": input_str})
        else:
            message = [{"role": role, "content": self._sys_msg + "\nUser:\n" + input_str}]
        
        chat_comp = self.client.chat.completions.create(
            messages=self.chat_history if self.chat_history else message,
            model=self.model,
            response_format={"type": "json_object"} if self.output_schema and response_json else None
        )
        
        if self._chf:
            self.chat_history.append({
                "role": chat_comp.choices[0].message.role,
                "content": chat_comp.choices[0].message.content
            })
            
        return chat_comp.choices[0].message.content
        
        
class GoogleClient(LLM_Client):

    def __init__(
        self,
        model: str = 'gemini-2.0-flash-001',
        chat_history: bool = True,
        sys_msg: str = None,
        output_schema: str = None
    ):
        self.model = model if model else 'gemini-2.0-flash-001'
        if chat_history:
            self._chf = True
            self.chat_history = []
        else:
            self._chf = False
            self.chat_history = None
        self.output_schema = output_schema
        
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_AIS_API_KEY"))
        
        self._config = None
        
        if sys_msg:
            add = f'\nUse this following json schema at all times to provide your answers:\n{self.output_schema}' if self.output_schema else ""
            sys_msg = str(sys_msg) + add
            self._config = types.GenerateContentConfig(
                system_instruction=sys_msg
            )
            if self._chf:
                chat_history = [
                    {"role": "system", "content": sys_msg}
                ]
        
        if self._chf:
            self._chat = self.client.chats.create(
                model=self.model,
                config=self._config
            )

    def chat_completion(
        self,
        input_str: str, 
        role: str = 'user',
        response_json: bool = False
    ):
        """
        `role` must be either `user` or `model` to work with the api.
        For simplicity reasons, it is set to `user`.
        """
        if self._chf:
            self.chat_history.append({"role": 'user', "content": input_str})
            chat_comp = self._chat.send_message(input_str)
        else:
            chat_comp = self.client.models.generate_content(
                model=self.model,
                contents=input_str,
                config=self._config,
            )

        if self._chf:
            self.chat_history.append({
                "role": chat_comp.candidates[0].content.role,
                "content": chat_comp.text
            })

        return chat_comp.text


######################################
# Available model providers and models
######################################

_model_providers = {
    "google": {
        'client': GoogleClient,
        'models': [
            {'value': 'gemini-2.0-flash-001', 'label': 'Gemini 2.0 Flash'},
            {'value': 'gemini-1.5-flash-002', 'label': 'Gemini 1.5 Flash'},
            {'value': 'gemini-2.5-flash-preview-04-17', 'label': 'Gemini 2.5 Flash Preview'},
        ]
    },
    "groq": {
        'client': GroqClient,
        'models': [
            {'value': 'llama3-70b-8192', 'label': 'Llama 3 70B'},
            {'value': 'deepseek-r1-distill-llama-70b', 'label': 'DeepSeek R1 Distill'},
            {'value': 'llama-3.3-70b-versatile', 'label': 'Llama 3.3 70B'},
            {'value': 'meta-llama/llama-4-maverick-17b-128e-instruct', 'label': 'Llama 4 Maverick'},
        ]
    }
}

######################################

def get_model_providers() -> dict:
    """
    Returns a list of available model providers and models to map the models
    to the client.

    Returns
    -------
        dict
            A dictionary with the model provider as key that links to a
            dictionary with the client and models as values.
    """
    return _model_providers

def models_to_json(filename: str = None):
    """
    Saves the available models from the `_model_providers` dict to a json file.
    
    Parameters
    ----------
        filename: str
            The name of the json file to save the models to. If None, defaults
            to `models.json` in the current directory.
    """
    if filename is None:
        filename = 'models.json'
    models_list = []
    for provider, details in _model_providers.items():
        for model in details['models']:
            models_list.append({
                'provider': provider,
                'model': model['value'],
                'label': model['label']
            })

    filename = filename if filename else './models.json'
    with open(filename, 'w') as json_file:
        json.dump(models_list, json_file, indent=2)

def get_model_client(model_provider: str) -> LLM_Client:
    """
    Searches the model client for a given model name.

    Parameters
    ----------
        provider: str
            The model provider to search for.
    
    Returns
        LLM_Client
            The model client associated with the given model provider.
    """
    for provider, details in _model_providers.items():
        if provider == model_provider:
            return details['client']
    
    raise ValueError(
        f"Provider '{model_provider}' not found in available providers."
    )
