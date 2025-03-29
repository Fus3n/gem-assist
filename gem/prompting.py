from prompt_toolkit.completion import Completer, Completion

class SlashCompleter(Completer):
    def __init__(self, completions: list[str]):
        self.commands = completions

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            for cmd in self.commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
        return



# # Custom logic to handle input
# def dynamic_prompt():
#     user_input = session.prompt(">>> ")
#     return user_input

# # Run it
# while True:
#     result = dynamic_prompt()
#     print(f"You typed: {result}")
#     if result == "/exit":
#         break