# Gem-assist - A Gemini-Powered (And Ollama) Personal Assistant

Gem-Assist is a Python-based personal assistant that leverages the power of Google's Gemini models to help you with various tasks. It's designed to be versatile and extensible, offering a range of tools to interact with your system and the internet. (These were written by AI)

A short disclaimer this was originally made to be my personal assistant so it might not be as versatile as you might expect.

## Features

*   **Powered by Gemini:** Utilizes the latest Gemini models for natural language understanding and generation. (**Ollama** version is still very early WIP)

*   **Tool-based architecture:** Equipped with a variety of tools for tasks like:
    *   Web searching (DuckDuckGo)
    *   File system operations (listing directories, reading/writing files, etc.)
    *   System information retrieval
    *   Reddit interaction
    *   Running shell commands
    *   And more!
*   **Customizable:**  Easily configure the assistant's behavior and extend its capabilities with new tools.
*   **Simple Chat Interface:** Interact with the assistant through a straightforward command-line chat interface.

## Getting Started

### Prerequisites

*   Python 3.11 or higher
*   uv (for dependency management) - [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
*   Google Gemini API key - [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Installation

1.  Clone the repository:
```bash
git clone [repository_url]
cd gem-assist
```

2.  Install dependencies using uv:

This will create venv if it doesn't exist

```bash
uv sync
```

3.  Set up environment variables:
    *   Create a `.env` file in the project root.
    *   Add your Google Cloud API key:
        ```
        GOOGLE_API_KEY=YOUR_API_KEY
        REDDIT_ID=YOUR_REDDIT_CLIENT_ID # (Optional, for Reddit tools)
        REDDIT_SECRET=YOUR_REDDIT_CLIENT_SECRET # (Optional, for Reddit tools)
        ```

### Usage

Run the `gem-assist.py` script to start the chat interface:

```bash
uv run gem-assist.py
```

You can then interact with Gemini by typing commands in the chat.  Type `exit`, `quit`, or `bye` to close the chat.

## Configuration

The main configuration file is `config.py`. Here you can customize:

*   **`MODEL`**:  Choose the Gemini model to use (e.g., `"gemini-2.0-flash"`, `"gemini-2.0-pro-exp-02-05"`).
*   **`NAME`**: Set the name of your assistant.
*   **`SYSTEM_PROMPT`**:  Modify the system prompt to adjust the assistant's personality and instructions.

**Note:**  Restart the `gemini_assist.py` script after making changes to `config.py`.

## Tools

GemFunc comes with a set of built-in tools that you can use in your conversations.  These tools are defined in the `utility.py` file and include functionalities for:

*   **Web Search:** `duckduckgo_search_tool`
*   **File System:** `list_dir`, `read_file`, `write_files`, `create_directory`, `copy_file`, `move_file`, `rename_file`, `rename_directory`, `get_file_metadata`, `get_directory_size`, `get_multiple_directory_size`
*   **System:** `get_system_info`, `run_shell_command`, `get_current_time`, `get_current_directory`, `get_drives`, `get_environment_variable`
*   **Web Interaction:** `get_website_text_content`, `http_get_request`, `open_url`
*   **Reddit:** `reddit_search`, `get_reddit_post`, `reddit_submission_comments`
*   **Utility:** `evaluate_math_expression`, `zip_archive_files`, `zip_extract_files`, `log_note`, `read_log_note`

## Dependencies

The project dependencies are managed by UV and listed in `pyproject.toml`. Key dependencies include:

*   `google-genai`
*   `ollama`
*   `duckduckgo-search`
*   `praw`
*   `rich`
*   `python-dotenv`


## Known Issues

*   **Web Interaction:**  Web interaction tools may not work as expected due to rate limits and other issues.
*   **File system** There is a bug with gemini sending large payload in function calling argument, it just fails to parse for some reason, so make sure to not tell it to write large files it might stop because of MALFORMED_FUNCTION_CALL.


## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

---

**Disclaimer:** This is a personal project and is provided as-is. Use at your own risk.
