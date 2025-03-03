import os
import warnings

import colorama
from colorama import Fore, Back, Style
from dotenv import load_dotenv
from google import genai
from google.genai.types import (FinishReason, GenerateContentConfig,
                                 HarmBlockThreshold, HarmCategory,
                                 SafetySetting)
from rich.console import Console
from rich.markdown import Markdown

import config as conf
from utility import TOOLS
import platform
from pprint import pformat

load_dotenv()

def terminal_link(text, url):
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

# Example usage
if __name__ == "__main__":
    API_KEY = os.getenv("GEMINI_API_KEY")
    
    console = Console()
    colorama.init(autoreset=True)
    
    # Suppress all warnings from the 'pydantic' category
    warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

    client = genai.Client(api_key=API_KEY)

    sys_instruct = (conf.get_system_prompt() + "Here are the things previously saved on your notes:\n" + open("./ai-log.txt").read()).strip()


    tools = TOOLS


    client_config = GenerateContentConfig(
        tools=tools,
        system_instruction=sys_instruct,
        response_modalities=['TEXT'],
        safety_settings=[
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_NONE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_NONE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_NONE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_NONE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=HarmBlockThreshold.BLOCK_NONE,
            ),
        ]
        # max_output_tokens=18432*5,
    )

    # Only going for latest models for now
    available_models = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-pro-exp-02-05",
    ]

    if conf.MODEL not in available_models:
        print(f"{Fore.RED}Invalid model: {conf.MODEL} {Style.RESET_ALL}")
        exit()

    chat = client.chats.create(model=conf.MODEL, config=client_config)
    
    os.system("cls" if platform.system() == "Windows" else "clear")
    width = 60
    title = f" {conf.NAME} CHAT INTERFACE "
    padding = (width - len(title)) // 2
    
    print(f"\n{Back.BLUE}{Fore.WHITE}┌{'─' * width}┐{Style.RESET_ALL}")
    print(f"{Back.BLUE}{Fore.WHITE}│{' ' * padding}{title}{' ' * (width - len(title) - padding)}│{Style.RESET_ALL}")
    print(f"{Back.BLUE}{Fore.WHITE}└{'─' * width}┘{Style.RESET_ALL}\n")
    
    while True:
        try:
            print(f"{Fore.CYAN}┌{'─' * 58}┐{Style.RESET_ALL}")
            msg = input(f"{Fore.CYAN}│ {Fore.MAGENTA}You:{Style.RESET_ALL} ")
            print(f"{Fore.CYAN}└{'─' * 58}┘{Style.RESET_ALL}")
            if not msg:
                continue
            
            if msg.lower() in ['exit', 'quit', 'bye']:
                print(f"\n{Fore.GREEN}Quitting {conf.NAME}...{Style.RESET_ALL}")
                break
                
            response = chat.send_message(msg)

            
            print(f"{Fore.YELLOW}┌{'─' * 58}┐{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}│ {Fore.GREEN}{conf.NAME}:{Style.RESET_ALL} ", end="")
            console.print(Markdown(response.text.strip()) if response.text else "")

            if response.candidates[0].finish_reason != FinishReason.STOP:
                print(f"{Fore.RED}An error occurred: {response.candidates[0].finish_reason}{Style.RESET_ALL}")
                with open("tool-calling-fail.json", "w", encoding="utf-8") as f:
                    f.write(pformat(response.model_dump_json()))
                    
            if response.candidates and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
                print(f"{Fore.BLUE}┌{'─' * 58}┐{Style.RESET_ALL}")
                print(f"{Fore.BLUE}│ {Fore.CYAN}Sources:{Style.RESET_ALL}")
                for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web'):
                        clickable_link = terminal_link(chunk.web.title, chunk.web.uri)
                        
                        print(f"{Fore.BLUE}│ {Fore.WHITE}- {clickable_link}{Style.RESET_ALL}")
                print(f"{Fore.BLUE}└{'─' * 58}┘{Style.RESET_ALL}")
                
            print(f"{Fore.YELLOW}└{'─' * 58}┘{Style.RESET_ALL}\n")
        except KeyboardInterrupt:
            print(f"\n\n{Fore.GREEN}Chat session interrupted.{Style.RESET_ALL}")
            break
        except Exception as e:
            for resp in response.candidates:
                with open("test.logs", "w", encoding="utf-8") as f:
                    f.write(str(resp) + "\n")
            print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")