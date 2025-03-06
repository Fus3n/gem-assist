import inspect
import json
from typing import Callable
import traceback
from typing import Union
import colorama
from pydantic import BaseModel
import litellm
from utility import TOOLS

from colorama import Fore, Style
from rich.console import Console
from rich.markdown import Markdown
import config as conf

from func_to_schema import function_to_json_schema

from dotenv import load_dotenv
load_dotenv()

class Assistant:


    def __init__(self, model: str, name: str = "Assistant", tools: list[Callable] = [], system_instruction: str = "") -> None:
        self.model = model
        self.name = name
        self.system_instruction = system_instruction
        self.messages = []
        self.available_functions = {func.__name__: func for func in tools}
        self.tools = list(map(function_to_json_schema, tools))

        self.temperature = 0.25
        
        if system_instruction: self.messages.append({"role": "system", "content": system_instruction})
        
        self.console = Console()

    def send_message(self, message):
        self.messages.append({"role": "user", "content": message})
        response = litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            temperature=self.temperature,
        )
        return self.__process_response(response)

    def print_ai(self, msg: str):
        print(f"{Fore.YELLOW}┌{'─' * 58}┐{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}│ {Fore.GREEN}{self.name}:{Style.RESET_ALL} ", end="")
        self.console.print(Markdown(msg.strip() if msg else ""))

    def get_completion(self):
        """Get a completion from the model with the current messages and tools and process the response."""
        response = litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            temperature=self.temperature,
        )
        return self.__process_response(response)
    
    def add_msg_assistant(self, msg: str):
        self.messages.append({"role": "assistant", "content": msg})

    def add_toolcall_output(self, tool_id, name, content):
        self.messages.append(
            {
                "tool_call_id": tool_id,
                "role": "tool",
                "name": name,
                "content": str(content),
            }
        )

    def convert_to_pydantic_model(self, annotation, arg_value):
        """
        Attempts to convert a value to a Pydantic model.
        """
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            try:
                return annotation(**arg_value)
            except (TypeError, ValueError):
                return arg_value  # not a valid Pydantic model or data mismatch
        elif hasattr(annotation, '__origin__'):
            origin = annotation.__origin__
            args = annotation.__args__

            if origin is list:
                return [self.convert_to_pydantic_model(args[0], item) for item in arg_value]
            elif origin is dict:
                return {key: self.convert_to_pydantic_model(args[1], value) for key, value in arg_value.items()}
            elif origin is Union:
                for arg_type in args:
                    try:
                        return self.convert_to_pydantic_model(arg_type, arg_value)
                    except (ValueError, TypeError):
                        continue
                raise ValueError(f"Could not convert {arg_value} to any type in {args}")
            elif origin is tuple:
                return tuple(self.convert_to_pydantic_model(args[i], arg_value[i]) for i in range(len(args)))
            elif origin is set:
                return {self.convert_to_pydantic_model(args[0], item) for item in arg_value}
        return arg_value
    
    def __process_response(self, response, print_response=True):
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        self.messages.append(response_message) 
        final_response = None

        # Multi-turn parallel tool calling
        # This will keep checking for tool calls and will call them
        # if any tools return an error it will be sent back to the AI
        try:
            while tool_calls:
                print(tool_calls)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name

                    function_to_call = self.available_functions.get(function_name, None)
                    if function_to_call is None:
                        err_msg = f"Function not found with name: {function_name}"
                        print(f"{Fore.RED}Error: {err_msg}{Style.RESET_ALL}")
                        self.add_toolcall_output(tool_call.id, function_name, err_msg)  
                        continue            

                    function_args = json.loads(tool_call.function.arguments)
                    
                    sig = inspect.signature(function_to_call)

                    for param_name, param in sig.parameters.items():
                        if param_name in function_args:
                            function_args[param_name] = self.convert_to_pydantic_model(param.annotation, function_args[param_name])

                    try:
                        function_response = function_to_call(**function_args)
                        # response of tool
                        self.add_toolcall_output(tool_call.id, function_name, function_response)
                    except Exception as e:
                        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                        self.add_toolcall_output(tool_call.id, tool_call.function.name, str(e))
                        continue

                final_response = litellm.completion(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools,
                    temperature=self.temperature,
                ) 

                tool_calls = final_response.choices[0].message.tool_calls
                if not tool_calls:
                    response_message = final_response.choices[0].message
                    self.messages.append(response_message) 
                    break

                self.messages.append(final_response.choices[0].message) 

            if print_response:
                self.print_ai(response_message.content)
            
            return response_message
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

            

if __name__ == "__main__":
    colorama.init(autoreset=True)

    sys_instruct = (conf.get_system_prompt() + "Here are the things previously saved on your notes:\n" + open("./ai-log.txt").read()).strip()
    
    assistant = Assistant(model=conf.MODEL, system_instruction=sys_instruct, tools=TOOLS)
    
    while True:
        try:
            print(f"{Fore.CYAN}┌{'─' * 58}┐{Style.RESET_ALL}")
            msg = input(f"{Fore.CYAN}│ {Fore.MAGENTA}You:{Style.RESET_ALL} ")
            print(f"{Fore.CYAN}└{'─' * 58}┘{Style.RESET_ALL}")
            
            if not msg: continue

            if msg.lower() in ['/exit', '/quit', '/bye']:
                print(f"\n{Fore.GREEN}Thank you for using {conf.NAME} AI Chat. Goodbye!{Style.RESET_ALL}")
                break

            assistant.send_message(msg)

        except KeyboardInterrupt:
            print(f"\n\n{Fore.GREEN}Chat session interrupted. Goodbye!{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
            traceback.print_exc()
            