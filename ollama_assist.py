# Ollama version (WIP)

import ollama
from utility import TOOLS
import colorama
from colorama import Fore, Style
import config as conf

from rich.console import Console
from rich.markdown import Markdown

class OllamaAssistant:

    available_functions = {func.__name__: func for func in TOOLS}

    def __init__(self, model: str, name: str = "Ollama", system_instruction: str = "", thinking=False) -> None:
        self.model = model
        self.name = name
        self.system_instruction = system_instruction
        self.messages = []
        
        if thinking: self.messages.append({"role": "control", "content": "thinking"})
        if system_instruction: self.messages.append({"role": "system", "content": system_instruction})
        
        self.tools = TOOLS
        
        self.console = Console()

    def send_message(self, message):
        self.messages.append({"role": "user", "content": message})
        response = ollama.chat(self.model, self.messages, tools=self.tools, options={"temperature": 0.2})
        self.__process_response(response)

    def print_ai(self, msg: str):
        print(f"{Fore.YELLOW}┌{'─' * 58}┐{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}│ {Fore.GREEN}{self.name}:{Style.RESET_ALL} ", end="")
        self.console.print(Markdown(msg.strip()))

    def __process_response(self, response):
        if response.message.tool_calls:
            # There may be multiple tool calls in the response
            for tool in response.message.tool_calls:
                # Ensure the function is available, and then call it
                if function_to_call := self.available_functions.get(tool.function.name):
                    # print('Calling function:', tool.function.name)
                    # print('Arguments:', tool.function.arguments)
                    output = function_to_call(**tool.function.arguments)
                    # print('Function output:', output)
                else:
                    print('Function', tool.function.name, 'not found')

        # Only needed to chat with the model using the tool call results
        if response.message.tool_calls:
            # Add the function response to messages for the model to use
            self.messages.append(response.message)
            self.messages.append({'role': 'tool', 'content': str(output), 'name': tool.function.name})

            # Get final response from model with function outputs
            final_response = ollama.chat(self.model, messages=self.messages)
            self.print_ai(final_response.message.content)

        else:
            self.messages.append(response.message)
            self.print_ai(response.message.content)

if __name__ == "__main__":
    colorama.init(autoreset=True)

    sys_instruct = (conf.SYSTEM_PROMPT + "Here are the things previously saved on your notes:\n" + open("./ai-log.txt").read()).strip()

    MODEL = "phi-4-mini-instruct_Q8"
    
    ollama_assist = OllamaAssistant(MODEL, system_instruction=sys_instruct, thinking=False)
    
    while True:
        try:
            print(f"{Fore.CYAN}┌{'─' * 58}┐{Style.RESET_ALL}")
            msg = input(f"{Fore.CYAN}│ {Fore.MAGENTA}You:{Style.RESET_ALL} ")
            print(f"{Fore.CYAN}└{'─' * 58}┘{Style.RESET_ALL}")
            
            if msg.lower() in ['exit', 'quit', 'bye']:
                print(f"\n{Fore.GREEN}Thank you for using Ollama AI Chat. Goodbye!{Style.RESET_ALL}")
                break
                
            ollama_assist.send_message(msg)

        except KeyboardInterrupt:
            print(f"\n\n{Fore.GREEN}Chat session interrupted. Goodbye!{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")