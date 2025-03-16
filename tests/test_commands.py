import pytest
from gem.command import cmd, CommandExecuter, InvalidCommand, CommandNotFound

def test_cmd_decorator():
    @cmd(["test"], "Test command")
    def test_command():
        return "test success"
    
    assert hasattr(test_command, 'aliases')
    assert test_command.aliases == ["test"]
    assert test_command.help == "Test command"

def test_cmd_decorator_invalid_aliases():
    with pytest.raises(TypeError):
        @cmd("not_a_list")
        def invalid_command():
            pass

def test_cmd_decorator_empty_aliases():
    with pytest.raises(ValueError):
        @cmd([])
        def empty_command():
            pass

def test_command_execution():
    @cmd(["greet"], "Greets a person")
    def greet(name: str):
        return f"Hello, {name}!"
    
    CommandExecuter.register_commands([greet])
    
    result = CommandExecuter.execute("/greet John")
    assert result == "Hello, John!"

def test_command_help():
    @cmd(["echo"], "Echoes input")
    def echo(text: str):
        """
        Repeats the input text back.
        
        Args:
            text: The text to echo
        """
        return text
    
    CommandExecuter.register_commands([echo])
    
    # Test help command
    result = CommandExecuter.execute("/echo ?")
    assert result is None  # Help command returns None
    
    # Test help method
    help_text = CommandExecuter.help("echo")
    assert "Echoes input" in help_text

def test_invalid_command():
    with pytest.raises(InvalidCommand):
        CommandExecuter.execute("invalid_command")  # Missing prefix

def test_command_not_found():
    with pytest.raises(CommandNotFound):
        CommandExecuter.execute("/nonexistent") 