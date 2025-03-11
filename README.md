# Gem-assist - A Personal Assistant In Your Terminal

Gem-Assist is a Python-based personal assistant that leverages the power of Google's Gemini models(and other) to help you with various tasks. It's designed to be versatile and extensible, offering a range of tools to interact with your system and the internet. (These were written by AI)

A short disclaimer this was originally made to be my personal assistant so it might not be as versatile as you might expect. Originally this was Gemini only now it supports alot because of litellm support, look into `config.py` for more information.

<p align="center">
  <img src="images/gem-assist-demo.gif" alt="Gem-Assist Demo" width="800"/>
</p>

## Features

- **Powered by LLM:** Utilizes LLM's for natural language understanding and generation.

- **Tool-based architecture:** Equipped with a variety of tools for tasks like:
  - Web searching (DuckDuckGo)
  - File system operations (listing directories, reading/writing files, etc.)
  - System information retrieval
  - Reddit interaction
  - Running shell commands
  - And more!
- **Customizable:** Easily configure the assistant's behavior and extend its capabilities with new tools.
- **Simple Chat Interface:** Interact with the assistant through a straightforward command-line chat interface.
- **Memory:** Can save notes between conversation and remember them.
- **Saving Conversation:** Save and load previous conversations.
- **Commands:** Supports creating/executing (code), use `/commands` for more information.
- **Extension:** For now you are required to write some code to extend its capabilities like adding commands to `CommandExecutor` or making new tools, there should be enough examples in `gem/builtin_commands.py` for commands and `utility.py` for tools

## Getting Started

### Prerequisites

- Python 3.11 or higher
- uv (for dependency management) - [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
- Google Gemini API key - [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Installation

1.  Clone the repository:

```bash
git clone https://github.com/Fus3n/gem-assist
cd gem-assist
```

2.  Install dependencies using uv:

This will create venv if it doesn't exist

```bash
uv sync
```

3.  Set up environment variables:
    - Create a `.env` file in the project root.
    - Add your Google Cloud API key:
      ```
      GEMINI_API_KEY=YOUR_API_KEY # or any other API key with proper key name, if used
      REDDIT_ID=YOUR_REDDIT_CLIENT_ID # (Optional, for Reddit tools)
      REDDIT_SECRET=YOUR_REDDIT_CLIENT_SECRET # (Optional, for Reddit tools)
      ```

### Usage

Run the `assistant.py` script to start the chat interface:

```bash
uv run assistant.py
```

Ignore `ollama_assist_old.py`

You can then interact with Gemini by typing commands in the chat. Type `exit`, `quit`, or `bye` to close the chat.

## Configuration

The main configuration file is `config.py`. Here you can customize:

- **`MODEL`**: Choose the Gemini model to use (e.g., `"gemini/gemini-2.0-flash"`, `"gemini/gemini-2.0-pro-exp-02-05"`) for more models checkout: [docs.litellm.ai/docs/providers/](https://docs.litellm.ai/docs/providers/), for local models its recommended to not run really small models.
- **`NAME`**: Set the name of your assistant.
- **`SYSTEM_PROMPT`**: Modify the system prompt to adjust the assistant's personality and instructions.

And more

**Note:** Restart the `assistant.py` script after making changes to `config.py`.

## Tools

gem-assist comes with a set of built-in tools that you can use in your conversations. These tools are defined in the `utility.py` file, some of the functionalities are:

- **Web Search:** `duckduckgo_search_tool`
- **File System:** `list_dir`, `read_file`, `write_files`, `create_directory`, `copy_file`, `move_file`, `rename_file`, `rename_directory`, `get_file_metadata`, `get_directory_size`, `get_multiple_directory_size`
- **System:** `get_system_info`, `run_shell_command`, `get_current_time`, `get_current_directory`, `get_drives`, `get_environment_variable`
- **Web Interaction:** `get_website_text_content`, `http_get_request`, `open_url`, `download_file_from_url`
- **Reddit:** `reddit_search`, `get_reddit_post`, `reddit_submission_comments`
- **Utility:** `evaluate_math_expression`, `zip_archive_files`, `zip_extract_files`, `write_note`, `read_note`

**And much more!**

## Dependencies

The project dependencies are managed by UV and listed in `pyproject.toml`. Key dependencies include:

- `google-genai`
- `ollama`
- `duckduckgo-search`
- `praw`
- `rich`
- `python-dotenv`

## Contributing

All contributions are welcome! Please fork the repository and create a pull request.

## Known Issues

- **Web Interaction:** Web interaction tools may not work as expected due to rate limits and other issues.
- **File download tool:** Might not show progress or filename (if not explicitly provided) correctly if file download endpoint is dynamic

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

---

**Disclaimer:** This is a personal project and is provided as-is. Use at your own risk.
