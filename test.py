from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style

class SlashCompleter(Completer):
    def __init__(self):
        self.commands = ["/help", "/exit", "/info", "/start"]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            # Filter commands that match the current input
            for cmd in self.commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
        # No suggestions if input doesn't start with "/"
        return

# Define custom styles for the prompt and completion menu
custom_style = Style.from_dict({
    "prompt": "fg:ansiblue", 
    "completion-menu": "bg:ansiblack fg:ansigreen",
    "completion-menu.completion": "bg:ansiblack fg:ansigreen",  
    "completion-menu.completion.current": "bg:ansigray fg:ansired", 
})

session = PromptSession(
    completer=SlashCompleter(),
    complete_while_typing=True,  # Show suggestions as you type
    style=custom_style  # Apply the custom style
)

# Custom logic to handle input
def dynamic_prompt():
    user_input = session.prompt(">>> ")
    return user_input

# Run it
while True:
    result = dynamic_prompt()
    print(f"You typed: {result}")
    if result == "/exit":
        break