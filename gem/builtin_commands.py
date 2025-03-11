from .command import cmd, CommandExecuter
from rich import print
import os

@cmd(["exit", "quit", "bye"], "Exit the chat")
def exit_chat():    
    exit()

@cmd(["help", "?"], "Show help about available commands.")
def show_help(command_name=None):
    """
    Args:
        command_name: The name of the command to show help for.
    """
    if command_name:
        help_text = CommandExecuter.help(command_name) 
        if help_text:
            print(help_text)
        else:
            print(f"No help available for command: {command_name}")
    else:
        print("No command name provided. Usage: /help <command_name>")

@cmd(["commands"], "List available commands.")
def list_commands():
    print("Available commands:")
    command_dict = {}
    for name, func in CommandExecuter.get_commands().items():
        if func not in command_dict:
            command_dict[func] = [name]
        else:
            command_dict[func].append(name)

    for func, names in command_dict.items():
        print(f"  /{', /'.join(names)}: {getattr(func, 'help', 'No help provided')}")

@cmd(["clear", "cls"], "Clear the screen, does not clear the chat history")
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

COMMANDS = [
    exit_chat,
    show_help,
    list_commands,
    clear_screen
]