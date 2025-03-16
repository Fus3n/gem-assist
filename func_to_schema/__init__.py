"""
This package provides functionality to convert Python functions into JSON schemas,
primarily for use with Large Language Models (LLMs) that support function calling.

It leverages type hints, docstrings, and function signatures to automatically
generate a JSON schema representing the function's parameters, descriptions, and
other relevant information. This allows LLMs to understand the function's
purpose and how to call it correctly.
"""

import inspect
from types import UnionType
from typing import Any, Dict, get_type_hints, get_origin, get_args, Literal, Callable
import docstring_parser
from pydantic import BaseModel
import warnings
import re

def function_to_json_schema(func: Callable) -> Dict[str, Any]:
    """
    Converts a Python function to a JSON schema for LLM function calling.

    Args:
        func: The Python function to convert.

    Returns:
        A dictionary representing the JSON schema.
    """
    signature = inspect.signature(func)
    docstring = docstring_parser.parse(func.__doc__ or "") 
    parameters = {}
    required_params = []

    type_hints = get_type_hints(func)

    for param_name, param in signature.parameters.items():
        param_info = {}
        if param_name in type_hints:
            param_info.update(type_hint_to_json_schema(type_hints[param_name]))

        docstring_param = next((p for p in docstring.params if p.arg_name == param_name), None)
        if docstring_param and docstring_param.description:
            param_info["description"] = docstring_param.description

        if param.default == inspect.Parameter.empty:
            required_params.append(param_name)

        parameters[param_name] = param_info

    doc_str_desc = docstring.description
    if doc_str_desc:
        doc_str_desc = re.sub(r'\s+', ' ', doc_str_desc).strip()

    json_schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc_str_desc or "",
        }
    }

    if parameters:
        json_schema["function"]["parameters"] = {}
        json_schema["function"]["parameters"]["type"] = "object"
        json_schema["function"]["parameters"]["properties"] = parameters
        json_schema["function"]["parameters"]["required"] = required_params if required_params else None,
    
    if docstring.returns and docstring.returns.description:
        json_schema["function"]["returns"] = {
            "description": docstring.returns.description
        }
    
    return json_schema


def type_hint_to_json_schema(type_hint) -> Dict[str, Any]:
    """
    Converts a Python type hint to a JSON schema type.  Handles:
        - Basic types (str, int, float, bool)
        - typing.Optional[T]  ->  T with nullable=True
        - typing.Union[T1, T2] ->  type: [T1, T2]
        - typing.List[T]      ->  array of T
        - Pydantic BaseModel   ->  Use schema() method
        - typing.Dict        -> object

    Args:
        type_hint: The Python type hint.

    Returns:
        A dictionary representing the JSON schema type.  Returns an empty
        dictionary if the type is not supported.
    """
    if type_hint == str:
        return {"type": "string"}
    elif type_hint == int:
        return {"type": "integer"}
    elif get_origin(type_hint) is Literal:
        total_types = [type_hint_to_json_schema(type(arg))["type"] for arg in type_hint.__args__]
        return {"type": total_types[0], "enum": list(type_hint.__args__)}
    elif type_hint == float:
        return {"type": "number"}  
    elif type_hint == bool:
        return {"type": "boolean"}
    elif type_hint == type(None): 
        return {"type": "null"}
    elif get_origin(type_hint) is list:
        args = get_args(type_hint)
        if args:
            return {"type": "array", "items": type_hint_to_json_schema(args[0])}
        else:
            return {"type": "array"} 
    elif get_origin(type_hint) is dict:
        return {"type": "object"} 
    elif get_origin(type_hint) is UnionType:
        args = get_args(type_hint)
        # handle Optional[T] (which is Union[T, None])
        if type(None) in args: 
            non_none_args = [arg for arg in args if arg is not type(None)]  # noqa: E721
            if len(non_none_args) == 1:
                # optional[T] case
                schema = type_hint_to_json_schema(non_none_args[0])
                schema["nullable"] = True 
                return schema

        return {"type": [type_hint_to_json_schema(arg)["type"] for arg in args if arg is not type(None)]} # handling for Union and skip None

    elif isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
        schema = type_hint.model_json_schema()
        if 'title' in schema:
            del schema['title']
        if "properties" in schema:
            for _, prop_schema in schema["properties"].items():
                if "title" in prop_schema:
                    del prop_schema["title"]
        return schema
    
    warnings.warn(f"Unsupported type hint: {type_hint}. Treating as Any.", UserWarning)
    return {}

