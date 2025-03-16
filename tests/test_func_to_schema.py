import pytest
from func_to_schema import function_to_json_schema
from pydantic import BaseModel

# Test simple function
def test_basic_function():
    def test_func(name: str, age: int):
        """
        A test function.
        
        Args:
            name: The person's name
            age: The person's age
        """
        pass

    schema = function_to_json_schema(test_func)
    assert isinstance(schema, dict)
    assert "function" in schema
    assert "parameters" in schema["function"]

# Test with default values
def test_function_with_defaults():
    def test_func(name: str = "John", age: int = 25):
        """Test function with defaults"""
        pass

    schema = function_to_json_schema(test_func)
    assert isinstance(schema, dict)

    params = schema.get("function", {}).get("parameters", {})
    properties = params.get("properties", {})
    # check properties name and age
    assert properties == {'age': {'type': 'integer'}, 'name': {'type': 'string'}}
    assert properties.get("required") == None

# Test with Pydantic model
def test_pydantic_model_parameter():
    class UserModel(BaseModel):
        name: str
        age: int
        email: str

    def test_func(user: UserModel):
        """Test function with Pydantic model"""
        pass

    schema = function_to_json_schema(test_func)
    assert isinstance(schema, dict)
    params = schema.get("function", {}).get("parameters", {})
    properties = params.get("properties", {})
    
    # check that the Pydantic model fields are correctly converted to properties
    assert "user" in properties
    assert properties["user"]["type"] == "object"
    assert "properties" in properties["user"]
    
    # check the nested properties match the Pydantic model fields
    user_properties = properties["user"]["properties"]
    assert "name" in user_properties
    assert user_properties["name"]["type"] == "string"
    assert "age" in user_properties
    assert user_properties["age"]["type"] == "integer"
    assert "email" in user_properties
    assert user_properties["email"]["type"] == "string"
    
    # check that required fields are properly set
    assert "required" in properties["user"]
    assert set(properties["user"]["required"]) == {"name", "age", "email"}

# Test with lists and dicts
def test_complex_types():
    def test_func(names: list[str], data: dict[str, int]):
        """Test function with complex types"""
        pass

    schema = function_to_json_schema(test_func)
    assert isinstance(schema, dict)

    params = schema.get("function", {}).get("parameters", {})
    properties = params.get("properties", {})
    
    assert "names" in properties
    assert properties["names"]["type"] == "array"
    assert properties["names"]["items"]["type"] == "string"
    
    assert "data" in properties
    assert properties["data"]["type"] == "object"

def test_function_description():
    def test_func(name: str):
        """
        This is a test function.
        
        It does testing things.
        
        Args:
            name: The name to test
        """
        pass

    schema = function_to_json_schema(test_func)
    assert isinstance(schema, dict)

    assert "description" in schema["function"]
    print(schema["function"])
    assert schema["function"]["description"] == "This is a test function. It does testing things." # both long and short description are combined in single line

    properties = schema.get("function", {}).get("parameters", {}).get("properties", {})
    assert "name" in properties
    assert properties["name"]["description"] == "The name to test"

def test_invalid_function():
    def test_func(name): 
        pass
    
    schema = function_to_json_schema(test_func)
    assert isinstance(schema, dict)
    from pprint import pprint
    pprint(schema)
    properties = schema.get("function", {}).get("parameters", {}).get("properties", {})
    assert properties["name"] == {}


def test_unsupportd_type_hints():
    from typing import Callable

    def test_func(func: Callable):
        pass

    with pytest.warns(UserWarning, match="Unsupported type hint: typing.Callable. Treating as Any."):
        _ = function_to_json_schema(test_func)

