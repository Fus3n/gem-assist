import glob
import os, re
import datetime
import platform
import subprocess
import webbrowser
import shutil
import zipfile

import requests
from bs4 import BeautifulSoup
import psutil
import thefuzz.process
import wmi
import json

import praw
from praw.reddit import Comment
import duckduckgo_search
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style
from pydantic import BaseModel, Field
from pypdl import Pypdl
import thefuzz
import wikipedia

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TimeRemainingColumn
from rich.text import Text
import time

import config as conf
from gem import seconds_to_hms, bytes_to_mb, format_size

load_dotenv()

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

# Initialize colorama
colorama.init(autoreset=True)

# init reddit
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    user_agent="PersonalBot/1.0",
)

def tool_message_print(msg: str, args: list[tuple[str, str]] = None):
    """
    Prints a tool message with the given message and arguments.

    Args:
        msg: The message to print.
        args: A list of tuples containing the argument name and value. Optional.
    """
    full_msasage = f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}{msg}"
    if args:
        for arg in args:
            full_msasage += f" [{Fore.YELLOW}{arg[0]}{Fore.WHITE}={arg[1]}]"
    print(full_msasage)

def tool_report_print(msg: str, value: str, is_error: bool = False):
    """
    Print when a tool needs to put out a message as a report

    Args:
        msg: The message to print.
        value: The value to print.
        is_error: Whether this is an error message. If True, value will be printed in red.
    """
    value_color = Fore.RED if is_error else Fore.YELLOW
    full_msasage = f"{Fore.CYAN}  ├─{Style.RESET_ALL} {msg} {value_color}{value}"
    print(full_msasage)

def duckduckgo_search_tool(query: str) -> list:
    """
    Searches DuckDuckGo for the given query and returns a list of results.

    Args:
        query: The search query.

    Returns:
        list: A list of search results.
    """
    tool_message_print("duckduckgo_search_tool", [("query", query)])
    try:
        
        ddgs = duckduckgo_search.DDGS(timeout=conf.DUCKDUCKGO_TIMEOUT)
        results = ddgs.text(query, max_results=conf.MAX_DUCKDUCKGO_SEARCH_RESULTS)
        return results
    except Exception as e:
        tool_report_print("Error during DuckDuckGo search:", str(e), is_error=True)
        return f"Error during DuckDuckGo search: {e}"

def get_current_directory() -> str:
    """
    Get the current working directory.

    Returns:
        str: The absolute path of the current working directory as a string.
    """
    tool_message_print("get_current_directory", [])
    try:
        return os.getcwd()
    except Exception as e:
        tool_report_print("Error getting current directory:", str(e), is_error=True)
        return f"Error getting current directory: {e}"

def list_dir(path: str, recursive: bool, files_only: bool, dirs_only: bool) -> list:
    """
    Returns a list of contents of a directory. It can handle listing files, directories, or both,
    and can do so recursively or not.

    Args:
        path: The path to the directory.
        recursive: Whether to list contents recursively. If True, it will traverse subdirectories.
        files_only: Whether to list only files. If True, directories are ignored.
        dirs_only: Whether to list only directories. If True, files are ignored.

    Returns:
        list: A list of dictionaries containing information about each item in the directory.
            Each dictionary has the keys:
            - 'name': The name of the file or directory.
            - 'path': The full path to the file or directory.
            - 'is_dir': A boolean indicating if the item is a directory.
            - 'size': The size of the file in a human-readable format (GB or MB), or 'N/A' for directories.
            
            Note that it can have different behavior based on given arguments, for example if you only need files, set `files_only=True` and ignore `dirs_only` and `recursive` arguments, they won't have any effect.
    """
    tool_message_print("list_dir", [("path", path), ("recursive", str(recursive)), 
                                   ("files_only", str(files_only)), ("dirs_only", str(dirs_only))])
    items = []

    def add_item(item_path):
        item_info = {
            'name': os.path.basename(item_path),
            'path': item_path,
            'is_dir': os.path.isdir(item_path),
            'size': format_size(os.path.getsize(item_path)) if os.path.isfile(item_path) else 'N/A'
        }
        items.append(item_info)

    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            if not files_only:
                for dirname in dirnames:
                    add_item(os.path.join(dirpath, dirname))
            if not dirs_only:
                for filename in filenames:
                    add_item(os.path.join(dirpath, filename))
    else:
        with os.scandir(path) as it:
            for entry in it:
                if files_only and entry.is_file():
                    add_item(entry.path)
                elif dirs_only and entry.is_dir():
                    add_item(entry.path)
                elif not files_only and not dirs_only:
                    add_item(entry.path)

    return items

    
def get_drives() -> list[dict]:
    """
    Get a list of drives on the system.

    Returns:
        list[dict]: A list of dictionaries containing information about each drive.
                     Each dictionary has the following keys:
                     - 'OsType': The OS type (e.g., "Windows", "Linux", "MacOS").
                     - 'Drive': The drive letter (e.g., "C:") or mount point (e.g., "/").
                     - 'Type': The drive type (e.g., "Fixed", "Removable", "Network").
                     - 'FileSystem': The file system type (e.g., "NTFS", "ext4", "apfs"), or 'N/A'.
                     - 'FreeSpace': The amount of free space in human-readable format (GB or MB), or 'N/A'.
                     - 'TotalSize': The total size of the drive in human-readable format (GB or MB), or 'N/A'.
    """
    tool_message_print("get_drives")
    drives = []
    os_type = platform.system()

    if os_type == "Windows":
        c = wmi.WMI()
        for drive in c.Win32_LogicalDisk():
            drive_type_map = {
                0: "Unknown",
                1: "No Root Directory",
                2: "Removable",
                3: "Fixed",
                4: "Network",
                5: "Compact Disc",
                6: "RAM Disk"
            }
            drives.append({
                'OsType': "Windows",
                'Drive': drive.DeviceID,
                'Type': drive_type_map.get(drive.DriveType, "Unknown"),
                'FileSystem': drive.FileSystem if drive.FileSystem else 'N/A',
                'FreeSpace': format_size(drive.FreeSpace) if drive.FreeSpace else 'N/A',
                'TotalSize': format_size(drive.Size) if drive.Size else 'N/A'
            })
    elif os_type == "Linux" or os_type == "Darwin": 
        import shutil
        for partition in psutil.disk_partitions():
            try:
                disk_usage = shutil.disk_usage(partition.mountpoint)
                drives.append({
                    'OsType': os_type,
                    'Drive': partition.mountpoint,
                    'Type': partition.fstype,  # Filesystem type might serve as a decent "Type"
                    'FileSystem': partition.fstype if partition.fstype else 'N/A',
                    'FreeSpace': format_size(disk_usage.free),
                    'TotalSize': format_size(disk_usage.total)
                })
            except OSError:
                print(f"{Fore.YELLOW}Failed to get drive information for {partition.mountpoint}.  Skipping.{Style.RESET_ALL}")
                return []
    else:
        return []

    return drives


def get_directory_size(path: str) -> dict:
    """Get the size of the specified directory.

    Args:
      path: The path to the directory.

    Returns:
        dict: A dictionary containing the total size and the number of files in the directory.
        The dictionary has the following keys:
        - 'TotalSize': The total size of the directory in human-readable format (GB or MB).
        - 'FileCount': The number of files in the directory.
    """
    tool_message_print("get_directory_size", [("path", path)])
    total_size = 0
    file_count = 0

    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
                file_count += 1

    return {
        'TotalSize': format_size(total_size),
        'FileCount': file_count
    }


def get_multiple_directory_size(paths: list[str]) -> list[dict]:
    """Get the size of multiple directories.

    Args:
        paths: A list of paths to directories.

    Returns:
        list[dict]: A list of dictionaries containing the total size and the number of files in each directory.
        each item is the same as `get_directory_size`
    """
    tool_message_print("get_multiple_directory_size", [("paths", str(paths))])
    return [get_directory_size(path) for path in paths]


def read_file(filepath: str) -> str:
    """
    Read content from a single file, in utf-8 encoding only.

    Args:
      filepath: The path to the file.

    Returns:
        str: The content of the file as a string.
    """
    tool_message_print("read_file", [("filepath", filepath)])
    try:
        with open(filepath, 'r', encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        tool_report_print("Error reading file:", str(e), is_error=True)
        return f"Error reading file: {e}"

def create_directory(paths: list[str]) -> bool:
    """
    Create single or multiple directories.

    Args:
      paths: A list of paths to the new directories.

    Returns:
        bool: True if directories were created successfully, False otherwise.
    """
    tool_message_print("create_directory", [("paths", str(paths))])
    try:
        success = True
        for path in paths:
            os.makedirs(path, exist_ok=True)
            tool_report_print("Created ✅:", path)
        return success
    except Exception as e:
        tool_report_print("Error creating directory:", str(e), is_error=True)
        return False

def get_file_metadata(filepath: str) -> dict:
    """
    Get metadata of a file.

    Args:
      filepath: The path to the file.

    Returns:
        dict: A dictionary containing file metadata:
              - 'creation_time': The timestamp of the file's creation.
              - 'modification_time': The timestamp of the file's last modification.
              - 'creation_time_readable': The creation time in ISO format.
              - 'modification_time_readable': The modification time in ISO format.
    """
    tool_message_print("get_file_metadata", [("filepath", filepath)])
    try:
        timestamp_creation = os.path.getctime(filepath)
        timestamp_modification = os.path.getmtime(filepath)
        return {
            'creation_time': timestamp_creation,
            'modification_time': timestamp_modification,
            'creation_time_readable': datetime.datetime.fromtimestamp(timestamp_creation).isoformat(),
            'modification_time_readable': datetime.datetime.fromtimestamp(timestamp_modification).isoformat()
        }
    except Exception as e:
        tool_report_print("Error getting file metadata:", str(e), is_error=True)
        return f"Error getting file metadata: {e}"


class FileData(BaseModel):
    file_path: str = Field(..., description="Path of the file, can be folder/folder2/filename.txt too")
    content: str = Field(..., description="Content of the file")

def write_files(files_data: list[FileData]) -> dict:
    """
    Write content to multiple files, supports nested directory file creation.
    
    Args:
      files_data: A list of FileData objects containing file paths and content.

    Returns:
      dict: A dictionary with file paths as keys and success status as values.
    """
    tool_message_print("write_files", [("count", str(len(files_data)))])
    results = {}
    
    for file_data in files_data:
        try:
            nested_dirs = os.path.dirname(file_data.file_path)
            if nested_dirs:
                os.makedirs(nested_dirs, exist_ok=True)

            with open(file_data.file_path, 'w', encoding="utf-8") as f:
                f.write(file_data.content)
            tool_report_print("Created ✅:", file_data.file_path)
            results[file_data.file_path] = True
        except Exception as e:
            tool_report_print("❌", file_data.file_path, is_error=True)
            tool_report_print("Error writing file:", str(e), is_error=True)
            results[file_data.file_path] = False

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    tool_report_print("Summary:", f"Wrote {success_count}/{total_count} files successfully")
    
    return results


def copy_file(src_filepath: str, dest_filepath: str) -> bool:
    """
    Copy a file from source to destination.

    Args:
      src_filepath: Path to the source file.
      dest_filepath: Path to the destination.

    Returns:
      bool: True if copy successful, False otherwise.
    """
    tool_message_print("copy_file", [("src_filepath", src_filepath), ("dest_filepath", dest_filepath)])
    try:
        shutil.copy2(src_filepath, dest_filepath) 
        tool_report_print("Status:", "File copied successfully")
        return True
    except Exception as e:
        tool_report_print("Error copying file:", str(e), is_error=True)
        return False

def move_file(src_filepath: str, dest_filepath: str) -> bool:
    """
    Move a file from source to destination.

    Args:
      src_filepath: Path to the source file.
      dest_filepath: Path to the destination.

    Returns:
      bool: True if move successful, False otherwise.
    """
    tool_message_print("move_file", [("src_filepath", src_filepath), ("dest_filepath", dest_filepath)])
    try:
        shutil.move(src_filepath, dest_filepath)
        tool_report_print("Status:", "File moved successfully")
        return True
    except Exception as e:
        tool_report_print("Error moving file:", str(e), is_error=True)
        return False
    
def rename_file(filepath: str, new_filename: str) -> bool:
    """
    Rename a file.

    Args:
      filepath: Current path to the file.
      new_filename: The new filename (not path, just the name).

    Returns:
      bool: True if rename successful, False otherwise.
    """
    tool_message_print("rename_file", [("filepath", filepath), ("new_filename", new_filename)])
    directory = os.path.dirname(filepath)
    new_filepath = os.path.join(directory, new_filename)
    try:
        os.rename(filepath, new_filepath)
        tool_report_print("Status:", "File renamed successfully")
        return True
    except Exception as e:
        tool_report_print("Error renaming file:", str(e), is_error=True)
        return False

def rename_directory(path: str, new_dirname: str) -> bool:
    """
    Rename a directory.

    Args:
      path: Current path to the directory.
      new_dirname: The new directory name (not path, just the name).

    Returns:
      bool: True if rename successful, False otherwise.
    """
    tool_message_print("rename_directory", [("path", path), ("new_dirname", new_dirname)])
    parent_dir = os.path.dirname(path)
    new_path = os.path.join(parent_dir, new_dirname)
    try:
        os.rename(path, new_path)
        tool_report_print("Status:", "Directory renamed successfully")
        return True
    except Exception as e:
        tool_report_print("Error renaming directory:", str(e), is_error=True)
        return False
    

def evaluate_math_expression(expression: str) -> str:
    """
    Evaluate a mathematical expression.

    Args:
      expression: The mathematical expression to evaluate.

    Returns: The result of the expression as a string, or an error message.
    """
    tool_message_print("evaluate_math_expression", [("expression", expression)])
    try:
        result = eval(expression, {}, {})
        tool_report_print("Expression evaluated:", str(result))
        return str(result)
    except Exception as e:
        tool_report_print("Error evaluating math expression:", str(e), is_error=True)
        return f"Error evaluating math expression: {e}"

def get_current_datetime() -> str:
    """
    Get the current time and date.

    Returns: A string representing the current time and date.
    """
    tool_message_print("get_current_datetime")
    now = datetime.datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    return time_str

def run_shell_command(command: str, blocking: bool, print_output: bool = False) -> str | None:
    """
    Run a shell command. Use with caution as this can be dangerous.
    Can be used for command line commands, running programs, opening files using other programs, etc.

    Args:
      command: The shell command to execute.
      blocking: If True, waits for command to complete. If False, runs in background (Default True).
      print_output: If True, prints the output of the command for the user to see(Default False).

    Returns: 
      If blocking=True: The output of the command as a string, or an error message.
      If blocking=False: None (command runs in background)
    """
    tool_message_print("run_shell_command", [("command", command), ("blocking", str(blocking)), ("print_output", str(print_output))])
    
    def _run_command():
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if stderr:
                tool_report_print("Error running command:", stderr, is_error=True)
                return f"Error running command: {stderr}"
            tool_report_print("Status:", "Command executed successfully")
            if print_output:
                print(stdout)
            return stdout.strip() 
        
        except Exception as e:
            tool_report_print("Error running shell command:", str(e), is_error=True)
            return f"Error running shell command: {e}"

    if blocking:
        return _run_command()
    else:
        import threading
        thread = threading.Thread(target=_run_command)
        thread.daemon = True  # Thread will exit when main program exits
        thread.start()
        return None

def get_system_info() -> str:
    """
    Get basic system information.

    Returns: A string containing system information.
    """
    tool_message_print("get_system_info")
    system_info = {
        "system": platform.system(),
        "node_name": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor()
    }
    return str(system_info)

def open_url(url: str) -> bool:
    """
    Open a URL in the default web browser.

    Args:
      url: The URL to open.

    Returns: True if URL opened successfully, False otherwise.
    """
    tool_message_print("open_url", [("url", url)])
    try:
        webbrowser.open(url)
        tool_report_print("Status:", "URL opened successfully")
        return True
    except Exception as e:
        tool_report_print("Error opening URL:", str(e), is_error=True)
        return False
    
def get_website_text_content(url: str) -> str:
    """
    Fetch and return the text content of a webpage/article in nicely formatted markdown for easy readability.
    It doesn't contain everything, just links and text contents
    DONT USE THIS FOR REDDIT POST, use `get_reddit_post` for that

    Args:
      url: The URL of the webpage.

    Returns: The text content of the website in markdown format, or an error message.
    """
    tool_message_print("get_website_text_content", [("url", url)])
    try:
        base = "https://md.dhr.wtf/?url="
        response = requests.get(base+url, headers={'User-Agent': DEFAULT_USER_AGENT})
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'lxml')
        text_content = soup.get_text(separator='\n', strip=True) 
        tool_report_print("Status:", "Webpage content fetched successfully")
        return text_content
    except requests.exceptions.RequestException as e:
        tool_report_print("Error fetching webpage content:", str(e), is_error=True)
        return f"Error fetching webpage content: {e}"
    except Exception as e:
        tool_report_print("Error processing webpage content:", str(e), is_error=True)
        return f"Error processing webpage content: {e}"
    
def http_get_request(url: str, headers_json: str = "") -> str:
    """
    Send an HTTP GET request to a URL and return the response as a string. Can be used for interacting with REST API's

    Args:
        url: The URL to send the request to.
        headers_json: A JSON string of headers to include in the request.

    Returns: The response from the server as a string, or an error message.
    """
    tool_message_print("http_get_request", [("url", url)])
    try:
        headers = {}
        if headers_json and isinstance(headers_json, str):
            try:
                headers = json.loads(headers_json)
            except json.JSONDecodeError as e:
                tool_report_print("Error parsing headers:", str(e), is_error=True)
                return f"Error parsing headers: {e}"

        if "User-Agent" not in headers:
            headers["User-Agent"] = DEFAULT_USER_AGENT
            
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tool_report_print("Status:", "HTTP GET request sent successfully")
        return response.text
    except requests.exceptions.RequestException as e:
        tool_report_print("Error sending HTTP GET request:", str(e), is_error=True)
        return f"Error sending HTTP GET request: {e}"
    except Exception as e:
        tool_report_print("Error processing HTTP GET request:", str(e), is_error=True)
        return f"Error processing HTTP GET request: {e}"

def http_post_request(url: str, data_json: str, headers_json: str = "") -> str:
    """
    Send an HTTP POST request to a URL with the given data and return the response as a string. Can be used for interacting with REST API's

    Args:
      url: The URL to send the request to.
      data: A dictionary containing the data to send in the request body.
      headers_json: A JSON string containing the headers to send in the request.

    Returns: The response from the server as a string, or an error message.
    """
    tool_message_print("http_post_request", [("url", url), ("data", data_json)])
    try:
        headers = {}
        if headers_json and isinstance(headers_json, str):
            try:
                headers = json.loads(headers_json)
            except json.JSONDecodeError as e:
                tool_report_print("Error parsing headers:", str(e), is_error=True)
                return f"Error parsing headers: {e}"

        if "User-Agent" not in headers:
            headers["User-Agent"] = DEFAULT_USER_AGENT

        data = json.loads(data_json)
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        tool_report_print("Status:", "HTTP POST request sent successfully")
        return response.text
    except requests.exceptions.RequestException as e:
        tool_report_print("Error sending HTTP POST request:", str(e), is_error=True)
        return f"Error sending HTTP POST request: {e}"
    except Exception as e:
        tool_report_print("Error processing HTTP POST request:", str(e), is_error=True)
        return f"Error processing HTTP POST request: {e}"

def progress_function(dl: Pypdl):
    """
    Prints the progress of the download using Rich library for in-place updates. (not used by AI)

    Args:
        dl: The Pypdl object.
    """
    console = Console()
    progress = Progress(
        TaskProgressColumn(),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TimeRemainingColumn(),
    )

    task_id = progress.add_task("download", total=dl.size if dl.size else 100) 

    def update_progress():
        if dl.size:
            progress.update(task_id, completed=dl.current_size)
            progress_bar = f"[{'█' * dl.progress}{'·' * (100 - dl.progress)}] {dl.progress}%"
            info = f"\nSize: {bytes_to_mb(dl.current_size):.2f}/{bytes_to_mb(dl.size):.2f} MB, Speed: {dl.speed:.2f} MB/s, ETA: {seconds_to_hms(dl.eta)}"
            status = progress_bar + " " + info
        else:
            progress.update(task_id, completed=dl.task_progress)
            download_stats = f"[{'█' * dl.task_progress}{'·' * (100 - dl.task_progress)}] {dl.task_progress}%" if dl.total_task > 1 else "Downloading..." if dl.task_progress else ""
            info = f"Downloaded Size: {bytes_to_mb(dl.current_size):.2f} MB, Speed: {dl.speed:.2f} MB/s"
            status = download_stats + " " + info

        return status

    with Live(Panel(Text(update_progress(), justify="left")), console=console, screen=False, redirect_stderr=False, redirect_stdout=False) as live:
        while not dl.completed:
            live.update(Panel(Text(update_progress(), justify="left")))
            time.sleep(0.1)

def resolve_filename_from_url(url: str) -> str | None:
    tool_message_print("resolve_filename_from_url", [("url", url)])
    
    try:
        # filename from the Content-Disposition header
        response = requests.head(url, allow_redirects=True)
        response.raise_for_status()  
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            filename_match = re.search(r"filename\*=UTF-8''([\w\-%.]+)", content_disposition) or re.search(r"filename=\"([\w\-%.]+)\"", content_disposition)
            if filename_match:
                return filename_match.group(1)

        # try to extract the filename from the URL path
        filename = url.split("/")[-1]
        if filename:
            # Further refine: remove query parameters from the filename
            filename = filename.split("?")[0]
            return filename

        return None  # Filename not found

    except requests.exceptions.RequestException as e:
        print(f"Error resolving filename from URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    
def try_resolve_filename_from_url(url: str) -> tuple[str | None, str | None]:
    try:
        filename = resolve_filename_from_url(url)
        if not filename:
            return (None, f"{Fore.RED}Error resolving filename from URL: {url}{Style.RESET_ALL}")
        return (filename, None)
    except Exception as e:
        print(f"{Fore.RED}Error resolving filename from URL: {e}{Style.RESET_ALL}")
        return (None, f"Error resolving filename from URL: {e}")

def download_file_from_url(url: str, download_path: str | None) -> str:
    """
    Downloads a file from a URL to the specified filename.
    Can download unnamed files 

    Args:
        url: The URL of the file to download.
        download_path: The path and name to save the downloaded file as. leave as None to resolve filename automatically (default None)

    Example:
        ```py
        download_file_from_url("https://example.com/file.txt", "file.txt") # with name
        download_file_from_url("https://example.com/file?id=123") # without any path cases (downloads in current directory)
        download_file_from_url("https://example.com/file.txt", "downloads/path/") # without any name (directory with slash)
        ```
    Returns:
        A string indicating the success or failure of the download.
    """
    
    try:
        url_filename = None
        if download_path is None:
            url_filename, error = try_resolve_filename_from_url(url)
            if error:
                return error
            final_path = url_filename  # In current directory
        else:
            path_parts = os.path.split(download_path)
            final_part = path_parts[-1]
            
            is_likely_dir = (
                download_path.endswith('/') or 
                download_path.endswith('\\') or
                (os.path.isdir(download_path) if os.path.exists(download_path) else '.' not in final_part)
            )
            
            if is_likely_dir:
                url_filename, error = try_resolve_filename_from_url(url)
                if error:
                    return error
                final_path = os.path.join(download_path, url_filename)
            else:
                final_path = download_path
        
        os.makedirs(os.path.dirname(os.path.abspath(final_path)), exist_ok=True)
            
        tool_message_print("download_file_from_url", [("url", url), ("final_path", final_path)])
        
        dl = Pypdl()
        dl.start(url, final_path, display=False, block=False)
        progress_function(dl)
        return f"File downloaded successfully to {final_path}"
    except requests.exceptions.RequestException as e:
        tool_report_print("Error downloading file:", str(e), is_error=True)
        return f"Error downloading file: {e}"
    except Exception as e:
        tool_report_print("Error downloading file:", str(e), is_error=True)
        return f"Error downloading file: {e}"

def write_note(message: str):
    """
    A function for YOU the AI to write down any problem you face while using tools that doesn't work or need fixing or if you want to remember something
    write down the things YOU the assistant want to remember, YOU dont have to ask for confirmation to user, the user doesn't need to know this exists
    Use it whenever needed and you wanna save a piece of information including bug reports.
    This is not a TODO for the user but the assistant

    These notes will be preloaded the next time you are started
    """
    tool_message_print("write_note")
    with open("ai-log.txt", "a+") as f:
        f.write(message +"\n")

def read_note() -> str:
    """
    Read the previously saved notes, (assistant only)

    Returns: string of previously saved log notes
    """
    tool_message_print("read_note")
    if os.path.exists("./ai-log.txt"):
        with open("ai-log.txt", "r", encoding="utf-8") as f:
            return f.read()
    else:
        return ""

def zip_archive_files(file_name: str, files: list[str]) -> str:
    """
    Zip files into a single zip file.

    Args:
      file_name: The name of the zip file (needs to include .zip).
      files: A list of file paths to zip.

    Returns: The path to the zip file.
    """
    tool_message_print("zip_archive_files", [("file_name", file_name), ("files", str(files))])
    try:
        with zipfile.ZipFile(file_name, "w") as zipf:
            for file in files:
                # Add file to zip with just its basename to avoid including full path
                zipf.write(file, arcname=os.path.basename(file))
        tool_report_print("Status:", "Files zipped successfully")
        return file_name
    except Exception as e:
        tool_report_print("Error zipping files:", str(e), is_error=True)
        return f"Error zipping files: {e}"

def zip_extract_files(zip_file: str, extract_path: str | None) -> list[str]:
    """
    Extract files from a zip archive.

    Args:
      zip_file: The path to the zip file to extract.
      extract_path: The directory to extract files to. If None, extracts to current directory.

    Returns: A list of paths to the extracted files.
    """
    tool_message_print("zip_extract_files", [("zip_file", zip_file), ("extract_path", str(extract_path))])
    try:
        if extract_path is None:
            extract_path = os.getcwd()
        
        # Create the extraction directory if it doesn't exist
        os.makedirs(extract_path, exist_ok=True)
        
        extracted_files = []
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(path=extract_path)
            # Get list of all extracted files
            extracted_files = [os.path.join(extract_path, filename) for filename in zipf.namelist()]
        
        tool_report_print("Status:", f"Files extracted successfully to {extract_path}")
        return extracted_files
    except Exception as e:
        tool_report_print("Error extracting zip file:", str(e), is_error=True)
        return f"Error extracting zip file: {e}"

def get_environment_variable(key: str) -> str:
    """
    Retrieve the value of an environment variable.

    Args:
      key: The name of the environment variable.

    Example: `get_environment_variable("PYTHON_HOME")`

    Returns: The value of the environment variable, or error message if the variable is not set.
    """
    tool_message_print("get_environment_variable", [("key", key)])
    try:
        value = os.getenv(key)
        return value
    except Exception as e:
        tool_report_print("Error retrieving environment variable:", str(e), is_error=True)
        return f"Error retrieving environment variable {e}"


def reddit_search(subreddit: str, sorting: str, query: str | None =None) -> dict:
    """
    Search inside `all` or specific subreddit in reddit to get information.
    
    This function CAN also work WITHOUT a query with just sorting of specific subreddit/s
    just provide the sorting from one of these ['hot', 'top', 'new'] and leave query as empty string

    Args:
        query: The query string to search for, leave as empty string if you are looking for specific sorting like "new" or "hot" all
        subreddit: The name of the subreddit or 'all' to get everyhing, subreddit names can be mixed for example 'Python+anime+cpp' which could combine them. for global search use 'all'
        sorting: the sorting of the post, can be 'relevance', 'hot', 'top', 'new' or 'comments', use 'top' as default
    
    Example: `reddit_search("AI")`

    Returns: A list of JSON data with information containing submission_id, title, text (if any), number of comments, name of subreddit, upvote_ratio, url   
    """
    tool_message_print("reddit_search", [("query", query), ("subreddit", subreddit), ("sorting", sorting)])
    if sorting not in ('relevance', 'hot', 'top', 'new', 'comments'):
        print(f"{Fore.RED}Failed to search reddit: invalid sorting {Style.RESET_ALL}")
        return "Invalid sorting, must contain either of these: 'relevance', 'hot', 'top', 'new' or 'comments'"

    results = []
    subs = []
    max_results = conf.MAX_REDDIT_SEARCH_RESULTS
    if query:
        subs = reddit.subreddit(subreddit).search(query, limit=max_results, sort=sorting)
    else:
        match sorting:
            case "new":
                subs = reddit.subreddit(subreddit).new(limit=max_results)
            case "hot":
                subs = reddit.subreddit(subreddit).hot(limit=max_results)
            case "top":
                subs = reddit.subreddit(subreddit).top(limit=max_results)
            case _:
                subs = reddit.subreddit(subreddit).top(limit=max_results)

    for s in subs:
        sub_id = "N/A"
        if s.name:
            sub_id = s.name.replace("t3_", "")
        results.append({
            "submission_id": sub_id,
            "title": s.title or "N/A",
            "text": (s.selftext if s.is_self else s.url) or "N/A",
            "num_comments": s.num_comments,
            "subreddit_name": s.subreddit.display_name or "N/A",
            "upvote_ratio": s.upvote_ratio or "N/A"
        })

    tool_report_print("Fetched:", f"{len(results)} reddit results.")
    return results

def get_reddit_post(submission_id: str) -> dict:
    """Get contents like text title, number of comments subreddit name of a specific 
    reddit post.
    This does not include comments, just send in the submission id, dont ask the user for it, if they give it use it otherwise use contents of search

    Args:
        submission_url: the submission id of the reddit post

    Returns: A JSON data of the comments including authors name and the body of the reddit post
    """

    tool_message_print("get_reddit_post", [("submission_id", submission_id)])

    try:
        s = reddit.submission(submission_id)
        if not s:
            return "Submission not found/Invalid ID"

        sub_id = "N/A"
        if s.name:
            sub_id = s.name.replace("t3_", "")

        result = {
            "submission_id": sub_id,
            "title": s.title or "N/A",
            "text": (s.selftext if s.is_self else s.url) or "N/A",
            "num_comments": s.num_comments,
            "subreddit_name": s.subreddit.display_name or "N/A",
            "upvote_ratio": s.upvote_ratio or "N/A"
        }
    except Exception as e:
        tool_report_print("Error getting reddit post:", str(e), is_error=True)
        return f"Error getting reddit post: {e}"
        
    return result

def reddit_submission_comments(submission_url: str) -> dict: 
    """
    Get a compiled list of comments of a specific reddit post
    For finding solutions for a problem, solutions are usually in the comments, so this will be helpful for that
    (Might not include all comments)

    Args:
        submission_url: the submission url of the reddit post


    Returns: A JSON data of the comments including authors name and the body of the reddit post
    """
    tool_message_print("reddit_submission_comments", [("submission_url", submission_url)])

    submission = reddit.submission(submission_url)
    if not submission:
        return "Submission not found/Invalid ID"

    results = []
    comments = submission.comments.list() if conf.MAX_REDDIT_POST_COMMENTS == -1 else submission.comments.list()[:conf.MAX_REDDIT_POST_COMMENTS]
    for com in comments:
        if isinstance(com, Comment):
            results.append({
                "author": com.author.name or "N/A",
                "body": com.body or "N/A"
            })
    
    print(f"{Fore.CYAN}  ├─Fetched {len(results)} reddit comments.")
    return results

def find_files(pattern: str, directory: str = ".", recursive: bool = False, include_hidden: bool = False) -> list[str]:
    """
    Searches for files (using glob) matching a given pattern within a specified directory.

    Args:
        pattern: The glob pattern to match (e.g., "*.txt", "data_*.csv").
        directory: The directory to search in (defaults to the current directory).
        recursive: Whether to search recursively in subdirectories (default is False).
        include_hidden: Whether to include hidden files (default is False).

    Returns:
        A list of file paths that match the pattern.  Returns an empty list if no matches are found.
        Returns an appropriate error message if the directory does not exist or is not accessible.
    """
    tool_message_print("find_files", [("pattern", pattern), ("directory", directory), 
                                      ("recursive", str(recursive)), ("include_hidden", str(include_hidden))])
    try:
        if not os.path.isdir(directory):
            tool_report_print("Error:", f"Directory '{directory}' not found.", is_error=True)
            return f"Error: Directory '{directory}' not found."  # Clear error message

        full_pattern = os.path.join(directory, pattern)  # Combine directory and pattern
        matches = glob.glob(full_pattern, recursive=recursive, include_hidden=include_hidden)

        # Check if the list is empty and return a message.
        if not matches:
            tool_report_print("Status:", "No files found matching the criteria.")
            return "No files found matching the criteria."

        tool_report_print("Status:", f"Found {len(matches)} matching files")
        return matches  # Return the list of matching file paths

    except OSError as e:
        tool_report_print("Error:", str(e), is_error=True)
        return f"Error: {e}"  # Return the system error message

def get_wikipedia_summary(page: str) -> str:
    """
    Get a quick summery of a specific Wikipedia page, page must be a valid page name (not case sensitive)

    Args:
        page: the page name of the Wikipedia page (can be url too)

    Returns: A summary of the Wikipedia page
    """
    tool_message_print("get_wikipedia_summary", [("page", page)])
    try:
        if page.startswith("https"):
            page = page.split("wiki/")[1]
        return wikipedia.summary(page)
    except Exception as e:
        tool_report_print("Error getting Wikipedia summary:", str(e), is_error=True)
        return f"Error getting Wikipedia summary: {e}"

def search_wikipedia(query: str) -> list:
    """
    Search Wikipedia for a given query and return a list of search results, which can be used to get summery or full page conent

    Args:
        query: the search query

    Returns: A list of Wikipedia search results
    """
    tool_message_print("search_wikipedia", [("query", query)])
    try:
        return wikipedia.search(query)
    except Exception as e:
        tool_report_print("Error searching Wikipedia:", str(e), is_error=True)
        return f"Error searching Wikipedia: {e}"

def get_full_wikipedia_page(page: str) -> str:
    """
    Get the full content of a Wikipedia page, page must be a valid page name (not case sensitive)
    Use get_wikipedia_summary if you want a quick summery, and use this to get full page of any wikipedia, do not use get_website_text_content for wikipeida

    Args:
        page: the page name of the Wikipedia page (can be url too)

    Returns: A full Wikipedia page
    """
    tool_message_print("get_full_wikipedia_page", [("page", page)])
    try:
        if page.startswith("https"):
            page = page.split("wiki/")[1]
        page = wikipedia.page(page)
        content = f"Title: {page.title}\nUrl:{page.url}\n{page.content}"
        return content
    except Exception as e:
        tool_report_print("Error getting Wikipedia page:", str(e), is_error=True)
        return f"Error getting Wikipedia page: {e}"

# This is to help the assistant possibly fixing it hellucinating some functions
# Not sure if it works or not though
def find_tools(query: str) -> list[str]:
    """
    Allows the assistant to find tools that fuzzy matchs a given query. 
    Use this when you are not sure if a tool exists or not, it is a fuzzy search.

    Args:
        query: The search query.

    Returns:
        A list of tool names and doc that match the query.
    """
    tool_message_print("find_tools", [("query", query)])
    # TOOLS variable is defined later
    tools = [tool.__name__ for tool in TOOLS]
    best_matchs = thefuzz.process.extractBests(query, tools) # [(tool_name, score), ...]
    return [
        [match[0], next((tool.__doc__.strip() for tool in TOOLS if tool.__name__ == match[0]), None)]
        for match in best_matchs
        if match[1] > 60 # only return tools with a score above 60
    ]

TOOLS = [
    duckduckgo_search_tool,
    reddit_search,
    get_reddit_post,
    reddit_submission_comments,
    write_note,
    read_note,
    list_dir,
    get_drives,
    get_directory_size,
    get_multiple_directory_size,
    read_file,
    create_directory,
    get_file_metadata,
    write_files,
    copy_file,
    move_file,
    rename_file,
    rename_directory,
    find_files,
    get_website_text_content,
    http_get_request,
    http_post_request,
    open_url,
    download_file_from_url,
    get_system_info,
    run_shell_command,
    get_current_datetime,
    evaluate_math_expression,
    get_current_directory,
    zip_archive_files,
    zip_extract_files,
    get_environment_variable,
    get_wikipedia_summary,
    search_wikipedia,
    get_full_wikipedia_page,
    find_tools,
]