import inspect
import json
import os
import platform
from typing import Callable
import traceback
from typing import Union
import colorama
from pydantic import BaseModel
import litellm
from utility import TOOLS
import pickle

from colorama import Fore, Style
from rich.console import Console
from rich.markdown import Markdown
import config as conf

from func_to_schema import function_to_json_schema
from gem.command import InvalidCommand, CommandNotFound, CommandExecuter, cmd
import gem

from dotenv import load_dotenv

load_dotenv()


class Assistant:

    def __init__(
        self,
        model: str,
        name: str = "Assistant",
        tools: list[Callable] = [],
        system_instruction: str = "",
    ) -> None:
        self.model = model
        self.name = name
        self.system_instruction = system_instruction
        self.messages = []
        self.available_functions = {func.__name__: func for func in tools}
        self.tools = list(map(function_to_json_schema, tools))

        if system_instruction:
            self.messages.append({"role": "system", "content": system_instruction})

        self.console = Console()

    def send_message(self, message):
        self.messages.append({"role": "user", "content": message})
        response = self.get_completion()
        return self.__process_response(response)

    def print_ai(self, msg: str):
        print(f"{Fore.YELLOW}┌{'─' * 58}┐{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}│ {Fore.GREEN}{self.name}:{Style.RESET_ALL} ", end="")
        self.console.print(
            Markdown(msg.strip() if msg else ""), end="", soft_wrap=True, no_wrap=False
        )
        print(f"{Fore.YELLOW}└{'─' * 58}┘{Style.RESET_ALL}")

    def get_completion(self):
        """Get a completion from the model with the current messages and tools."""
        return litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            temperature=conf.TEMPERATURE,
            top_p=conf.TOP_P,
            max_tokens=conf.MAX_TOKENS,
            seed=conf.SEED,
            safety_settings=conf.SAFETY_SETTINGS
        )

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

    @cmd(["save"], "Saves the current chat session to pickle file.")
    def save_session(self, name: str, filepath=f"chats"):
        """
        Args:
            name: The name of the file to save the session to. (can be either with or without json extension)
            filepath: The path to the directory to save the file to. (default: "/chats")
        """
        try:
            # create directory if default path doesn't exist
            if filepath == "chats":
                os.makedirs(filepath, exist_ok=True)

            final_path = os.path.join(filepath, name + ".pkl")
            with open(final_path, "wb") as f:
                pickle.dump(self.messages, f)

            print(
                f"{Fore.GREEN}Chat session saved to {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    @cmd(["load"], "Loads a chat session from a pickle file. Resets the session.")
    def load_session(self, name: str, filepath=f"chats"):
        """
        Args:
            name: The name of the file to load the session from. (can be either with or without json extension)
            filepath: The path to the directory to load the file from. (default: "/chats")
        """
        try:
            final_path = os.path.join(filepath, name + ".pkl")
            with open(final_path, "rb") as f:
                self.messages = pickle.load(f)
            print(
                f"{Fore.GREEN}Chat session loaded from {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except FileNotFoundError:
            print(
                f"{Fore.RED}Chat session not found{Style.RESET_ALL} {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    @cmd(["reset"], "Resets the chat session.")
    def reset_session(self):
        self.messages = []
        if self.system_instruction:
            self.messages.append({"role": "system", "content": self.system_instruction})

    def convert_to_pydantic_model(self, annotation, arg_value):
        """
        Attempts to convert a value to a Pydantic model.
        """
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            try:
                return annotation(**arg_value)
            except (TypeError, ValueError):
                return arg_value  # not a valid Pydantic model or data mismatch
        elif hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            args = annotation.__args__

            if origin is list:
                return [
                    self.convert_to_pydantic_model(args[0], item) for item in arg_value
                ]
            elif origin is dict:
                return {
                    key: self.convert_to_pydantic_model(args[1], value)
                    for key, value in arg_value.items()
                }
            elif origin is Union:
                for arg_type in args:
                    try:
                        return self.convert_to_pydantic_model(arg_type, arg_value)
                    except (ValueError, TypeError):
                        continue
                raise ValueError(f"Could not convert {arg_value} to any type in {args}")
            elif origin is tuple:
                return tuple(
                    self.convert_to_pydantic_model(args[i], arg_value[i])
                    for i in range(len(args))
                )
            elif origin is set:
                return {
                    self.convert_to_pydantic_model(args[0], item) for item in arg_value
                }
        return arg_value

    def __process_response(self, response, print_response=True):
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        self.messages.append(response_message)
        final_response = response_message

        # Multi-turn parallel tool calling
        # This will keep checking for tool calls and will call them
        # if any tools return an error it will be sent back to the AI
        try:
            if tool_calls:
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
                            function_args[param_name] = self.convert_to_pydantic_model(
                                param.annotation, function_args[param_name]
                            )

                    try:
                        function_response = function_to_call(**function_args)
                        if final_response.content:
                            print(
                                f"{Fore.YELLOW}│ {Fore.GREEN}{self.name}:{Style.RESET_ALL} {Style.DIM}{Fore.WHITE}{final_response.content.strip()}{Style.RESET_ALL}{Style.RESET_ALL}"
                            )
                        # response of tool
                        self.add_toolcall_output(
                            tool_call.id, function_name, function_response
                        )
                    except Exception as e:
                        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                        self.add_toolcall_output(
                            tool_call.id, tool_call.function.name, str(e)
                        )
                        continue

                final_response = self.get_completion()

                tool_calls = final_response.choices[0].message.tool_calls
                # if no more tool calls end and return
                if not tool_calls:
                    response_message = final_response.choices[0].message
                    self.messages.append(response_message)
                    if print_response:
                        self.print_ai(response_message.content)
                    return response_message
            else:
                if print_response:
                    self.print_ai(response_message.content)
                return response_message

            # if there are more tool calls
            return self.__process_response(
                final_response, print_response=print_response
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    colorama.init(autoreset=True)

    notes = ""
    if os.path.exists("./ai-log.txt"):
        with open("ai-log.txt", "r", encoding="utf-8") as f:
            notes = f.read()

    sys_instruct = (
        conf.get_system_prompt()
        + "Here are the things previously saved on your notes:\n"
        + notes
    ).strip()

    assistant = Assistant(
        model=conf.MODEL, system_instruction=sys_instruct, tools=TOOLS
    )

    # handle commands
    command = gem.CommandExecuter.register_commands(
        gem.builtin_commands.COMMANDS + [assistant.save_session, assistant.load_session, assistant.reset_session]
    )
    # set command prefix (default is /)
    # CommandExecuter.command_prefix = "/"

    if conf.CLEAR_BEFORE_START:
        gem.clear_screen()

    gem.print_header(f"{conf.NAME} CHAT INTERFACE")
    while True:
        try:
            print(f"{Fore.CYAN}┌{'─' * 58}┐{Style.RESET_ALL}")
            msg = input(f"{Fore.CYAN}│ {Fore.MAGENTA}You:{Style.RESET_ALL} ")
            print(f"{Fore.CYAN}└{'─' * 58}┘{Style.RESET_ALL}")

            if not msg:
                continue

            if msg.startswith("/"):
                CommandExecuter.execute(msg)
                continue

            assistant.send_message(msg)

        except KeyboardInterrupt:
            print(
                f"\n\n{Fore.GREEN}Chat session interrupted.{Style.RESET_ALL}"
            )
            break
        except InvalidCommand as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        except CommandNotFound as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
            traceback.print_exc()
