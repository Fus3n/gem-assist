import os, re
import datetime
import platform
import subprocess
import webbrowser
import shutil
import zipfile
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from PIL import ImageGrab
import psutil
import wmi

import praw
from praw.reddit import Comment
import duckduckgo_search
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style
from pydantic import BaseModel, Field
from google.genai.types import FunctionResponse, Image
from pypdl import Pypdl

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TimeRemainingColumn
from rich.text import Text

import config as conf

load_dotenv()


# Initialize colorama
colorama.init(autoreset=True)

# init reddit
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    user_agent="PersonalBot/1.0",
)


def duckduckgo_search_tool(query: str) -> list:
    """
    Searches DuckDuckGo for the given query and returns a list of results.

    Args:
        query (str): The search query.

    Returns:
        list: A list of search results.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}duckduckgo_search_tool {Fore.YELLOW}{query}")
    try:
        
        ddgs = duckduckgo_search.DDGS(timeout=conf.DUCKDUCKGO_TIMEOUT)
        results = ddgs.text(query, max_results=conf.MAX_DUCKDUCKGO_SEARCH_RESULTS)
        return results
    except Exception as e:
        print(f"{Fore.RED}Error during DuckDuckGo search: {e}{Style.RESET_ALL}")
        return f"Error during DuckDuckGo search: {e}"

def get_current_directory() -> str:
    """
    Get the current working directory.

    Returns:
        str: The absolute path of the current working directory as a string.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_current_directory")
    try:
        return os.getcwd()
    except Exception as e:
        print(f"{Fore.RED}Error getting current directory: {e}{Style.RESET_ALL}")
        return f"Error getting current directory: {e}"

def list_dir(path: str, recursive: bool, files_only: bool, dirs_only: bool) -> list:
    """
    Returns a list of contents of a directory. It can handle listing files, directories, or both,
    and can do so recursively or not.

    Args:
        path (str): The path to the directory.
        recursive (bool): Whether to list contents recursively. If True, it will traverse subdirectories.
        files_only (bool): Whether to list only files. If True, directories are ignored.
        dirs_only (bool): Whether to list only directories. If True, files are ignored.

    Returns:
        list: A list of dictionaries containing information about each item in the directory.
            Each dictionary has the keys:
            - 'name': The name of the file or directory.
            - 'path': The full path to the file or directory.
            - 'is_dir': A boolean indicating if the item is a directory.
            - 'size': The size of the file in a human-readable format (GB or MB), or 'N/A' for directories.
            
            Note that it can have different behavior based on given arguments, for example if you only need files, set `files_only=True` and ignore `dirs_only` and `recursive` arguments, they won't have any effect.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}list_dir {Fore.YELLOW}{path}")
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

def format_size(bytes_size):
    """Convert bytes to human-readable format (GB, MB, KB, or Bytes)"""
    if bytes_size == 'N/A' or bytes_size is None:
        return 'N/A'
    
    try:
        bytes_size = int(bytes_size)
    except (ValueError, TypeError):
        return 'N/A'

    if bytes_size >= (1024**3):  # GB
        gb_size = bytes_size / (1024**3)
        return f"{gb_size:.2f} GB"
    elif bytes_size >= (1024**2):  # MB
        mb_size = bytes_size / (1024**2)
        return f"{mb_size:.2f} MB"
    elif bytes_size >= 1024:  # KB
        kb_size = bytes_size / 1024
        return f"{kb_size:.2f} KB"
    else:  # Bytes
        return f"{bytes_size:.2f} Bytes"
    
    
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
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_drives")
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
        print(f"{Fore.YELLOW}Unsupported OS: {os_type}.  Returning empty drive list.{Style.RESET_ALL}")
        return []

    return drives


def get_directory_size(path: str) -> dict:
    """Get the size of the specified directory.

    Args:
      path (str): The path to the directory.

    Returns:
        dict: A dictionary containing the total size and the number of files in the directory.
        The dictionary has the following keys:
        - 'TotalSize': The total size of the directory in human-readable format (GB or MB).
        - 'FileCount': The number of files in the directory.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_directory_size {Fore.YELLOW}{path}")
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
      paths (list[str]): A list of paths to directories.

    Returns:
        list[dict]: A list of dictionaries containing the total size and the number of files in each directory.
        each item is the same as `get_directory_size`
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_multiple_directory_size")
    return [get_directory_size(path) for path in paths]


def read_file(filepath: str) -> str:
    """
    Read content from a single file, in utf-8 encoding only.

    Args:
      filepath (str): The path to the file.

    Returns:
        str: The content of the file as a string.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}read_file {Fore.YELLOW}{filepath}")
    try:
        with open(filepath, 'r', encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"{Fore.RED}Error reading file: {e}{Style.RESET_ALL}")
        return f"Error reading file: {e}"

def create_directory(paths: list[str]) -> bool:
    """
    Create single or multiple directories.

    Args:
      paths (list[str]): A list of paths to the new directories.

    Returns:
        bool: True if directories were created successfully, False otherwise.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}create_directory {Fore.YELLOW}{paths}")
    try:
        success = True
        for path in paths:
            os.makedirs(path, exist_ok=True)
            print(f"{Fore.CYAN}  ├─{Style.RESET_ALL} Created ✅: {Fore.YELLOW}{path}")
        return success
    except Exception as e:
        print(f"{Fore.RED}Error creating directory: {e}{Style.RESET_ALL}")
        return False

def get_file_metadata(filepath: str) -> dict:
    """
    Get metadata of a file.

    Args:
      filepath (str): The path to the file.

    Returns:
        dict: A dictionary containing file metadata:
              - 'creation_time': The timestamp of the file's creation.
              - 'modification_time': The timestamp of the file's last modification.
              - 'creation_time_readable': The creation time in ISO format.
              - 'modification_time_readable': The modification time in ISO format.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_file_metadata {Fore.YELLOW}{filepath}")
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
        print(f"{Fore.RED}Error getting file metadata: {e}{Style.RESET_ALL}")
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
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}write_files {Fore.YELLOW}")
    results = {}
    
    for file_data in files_data:
        try:
            nested_dirs = os.path.dirname(file_data.file_path)
            if nested_dirs:
                os.makedirs(nested_dirs, exist_ok=True)

            with open(file_data.file_path, 'w', encoding="utf-8") as f:
                f.write(file_data.content)
            print(f"{Fore.CYAN}  ├─{Style.RESET_ALL} Created ✅: {Fore.YELLOW}{file_data.file_path}")
            results[file_data.file_path] = True
        except Exception as e:
            print(f"{Fore.RED}  ├─{Style.RESET_ALL} ❌ {file_data.file_path}")
            print(f"{Fore.RED}Error writing file: {e}{Style.RESET_ALL}")
            results[file_data.file_path] = False

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"{Fore.GREEN if success_count == total_count else Fore.YELLOW}Wrote {success_count}/{total_count} files successfully{Style.RESET_ALL}")
    
    return results


def copy_file(src_filepath: str, dest_filepath: str) -> bool:
    """
    Copy a file from source to destination.

    Args:
      src_filepath (str): Path to the source file.
      dest_filepath (str): Path to the destination.

    Returns:
      bool: True if copy successful, False otherwise.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}copy_file {Fore.YELLOW}{src_filepath} {Fore.GREEN}→ {Fore.YELLOW}{dest_filepath}")
    try:
        shutil.copy2(src_filepath, dest_filepath)  # copy2 preserves metadata
        print(f"{Fore.GREEN}File copied successfully{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error copying file: {e}{Style.RESET_ALL}")
        return False

def move_file(src_filepath: str, dest_filepath: str) -> bool:
    """
    Move a file from source to destination.

    Args:
      src_filepath (str): Path to the source file.
      dest_filepath (str): Path to the destination.

    Returns:
      bool: True if move successful, False otherwise.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}move_file {Fore.YELLOW}{src_filepath} {Fore.GREEN}→ {Fore.YELLOW}{dest_filepath}")
    try:
        shutil.move(src_filepath, dest_filepath)
        print(f"{Fore.GREEN}File moved successfully{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error moving file: {e}{Style.RESET_ALL}")
        return False
    
def rename_file(filepath: str, new_filename: str) -> bool:
    """
    Rename a file.

    Args:
      filepath (str): Current path to the file.
      new_filename (str): The new filename (not path, just the name).

    Returns:
      bool: True if rename successful, False otherwise.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}rename_file {Fore.YELLOW}{filepath} {Fore.GREEN}→ {Fore.YELLOW}{new_filename}")
    directory = os.path.dirname(filepath)
    new_filepath = os.path.join(directory, new_filename)
    try:
        os.rename(filepath, new_filepath)
        print(f"{Fore.GREEN}File renamed successfully{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error renaming file: {e}{Style.RESET_ALL}")
        return False

def rename_directory(path: str, new_dirname: str) -> bool:
    """
    Rename a directory.

    Args:
      path (str): Current path to the directory.
      new_dirname (str): The new directory name (not path, just the name).

    Returns:
      bool: True if rename successful, False otherwise.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}rename_directory {Fore.YELLOW}{path} {Fore.GREEN}→ {Fore.YELLOW}{new_dirname}")
    parent_dir = os.path.dirname(path)
    new_path = os.path.join(parent_dir, new_dirname)
    try:
        os.rename(path, new_path)
        print(f"{Fore.GREEN}Directory renamed successfully{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error renaming directory: {e}{Style.RESET_ALL}")
        return False
    

def evaluate_math_expression(expression: str) -> str:
    """
    Evaluate a mathematical expression.

    Args:
      expression: The mathematical expression to evaluate.

    Returns: The result of the expression as a string, or an error message.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}evaluate_math_expression {Fore.YELLOW}{expression}")
    try:
        # Using eval() for simplicity, but be VERY CAREFUL with user input in production.
        result = eval(expression, {}, {})
        print(f"{Fore.GREEN}Expression evaluated: {result}{Style.RESET_ALL}")
        return str(result)
    except Exception as e:
        print(f"{Fore.RED}Error evaluating math expression: {e}{Style.RESET_ALL}")
        return f"Error evaluating math expression: {e}"

def get_current_time() -> str:
    """
    Get the current time and date. Also prints it.

    Returns: A string representing the current time and date.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_current_time")
    now = datetime.datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.GREEN}Current time: {time_str}{Style.RESET_ALL}")
    return time_str

def run_shell_command(command: str, blocking: bool) -> str | None:
    """
    Run a shell command. Use with caution as this can be dangerous.
    Can be used for command line commands, running programs, opening files using other programs, etc.

    Args:
      command: The shell command to execute.
      blocking: If True, waits for command to complete. If False, runs in background (Default false).

    Returns: 
      If blocking=True: The output of the command as a string, or an error message.
      If blocking=False: None (command runs in background)
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}run_shell_command(blocking={blocking}) {Fore.YELLOW}{command}")
    
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
                print(f"{Fore.RED}Error running command: {stderr}{Style.RESET_ALL}")
                return f"Error running command: {stderr}"
            print(f"{Fore.GREEN}Command executed successfully{Style.RESET_ALL}")
            return stdout.strip()  # remove trailing whitespace

        except Exception as e:
            print(f"{Fore.RED}Error running shell command: {e}{Style.RESET_ALL}")
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
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_system_info")
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
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}open_url {Fore.YELLOW}{url}")
    try:
        webbrowser.open(url)
        print(f"{Fore.GREEN}URL opened successfully{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error opening URL: {e}{Style.RESET_ALL}")
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
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_website_text_content {Fore.YELLOW}{url}")
    try:
        base = "https://md.dhr.wtf/?url="
        response = requests.get(base+url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'})
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'lxml')
        text_content = soup.get_text(separator='\n', strip=True) 
        print(f"{Fore.GREEN}Webpage content fetched successfully{Style.RESET_ALL}")
        return text_content
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Error fetching webpage content: {e}{Style.RESET_ALL}")
        return f"Error fetching webpage content: {e}"
    except Exception as e:
        print(f"{Fore.RED}Error fetching webpage content: {e}{Style.RESET_ALL}")
        return f"Error processing webpage content: {e}"
    
def http_get_request(url: str) -> str:
    """
    Send an HTTP GET request to a URL and return the response as a string.

    Args:
      url: The URL to send the request to.

    Returns: The response from the server as a string, or an error message.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}http_get_request {Fore.YELLOW}{url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'})
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"{Fore.GREEN}HTTP GET request sent successfully{Style.RESET_ALL}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Error sending HTTP GET request: {e}{Style.RESET_ALL}")
        return f"Error sending HTTP GET request: {e}"
    except Exception as e:
        print(f"{Fore.RED}Error sending HTTP GET request: {e}{Style.RESET_ALL}")
        return f"Error processing HTTP GET request: {e}"

def to_mb(size):
    return size / 1024 / 1024

def seconds_to_hms(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

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
            info = f"\nSize: {to_mb(dl.current_size):.2f}/{to_mb(dl.size):.2f} MB, Speed: {dl.speed:.2f} MB/s, ETA: {seconds_to_hms(dl.eta)}"
            status = progress_bar + " " + info
        else:
            progress.update(task_id, completed=dl.task_progress)
            download_stats = f"[{'█' * dl.task_progress}{'·' * (100 - dl.task_progress)}] {dl.task_progress}%" if dl.total_task > 1 else "Downloading..." if dl.task_progress else ""
            info = f"Downloaded Size: {to_mb(dl.current_size):.2f} MB, Speed: {dl.speed:.2f} MB/s"
            status = download_stats + " " + info

        return status

    with Live(Panel(Text(update_progress(), justify="left")), console=console, screen=False, redirect_stderr=False, redirect_stdout=False) as live:
        while not dl.completed:
            live.update(Panel(Text(update_progress(), justify="left")))
            import time
            time.sleep(0.1)

def resolve_filename_from_url(url: str) -> str | None:
    print(f"{Fore.CYAN}Resolving filename from URL {Fore.YELLOW}{url}")
    
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
            
        print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}download_file_from_url {Fore.YELLOW}{url} -> {final_path}")
        
        dl = Pypdl()
        dl.start(url, final_path, display=False, block=False)
        progress_function(dl)
        return f"File downloaded successfully to {final_path}"
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Error downloading file: {e}{Style.RESET_ALL}")
        return f"Error downloading file: {e}"
    except Exception as e:
        print(f"{Fore.RED}Error downloading file: {e}{Style.RESET_ALL}")
        return f"Error downloading file: {e}"


def screenshot() -> FunctionResponse:
    """Takes a screenshot and returns the image"""
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}screenshot")
    try:
        img = ImageGrab.grab()
        img.save("test.png")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return FunctionResponse(id="screenshot", name="screenshot", response={"output": Image(image_bytes=img_bytes, mime_type="image/png")})
    except Exception as e:
        print(f"{Fore.RED}Error taking screenshot: {e}{Style.RESET_ALL}")
        return FunctionResponse(id="screenshot", name="screenshot", response={"error": str(e)})
    

def log_note(message: str):
    """
    A function for YOU the AI to write down any problem you face while using tools that doesn't work or need fixing
    write down the things YOU the assistant want to remember, YOU dont have to ask for confirmation to user, the user doesn't need to know this exists
    Use it whenever needed and you wanna save a piece of information including bug reports.
    This is not a TODO for the user but the assistant

    These notes will be preloaded the next time you are started
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.YELLOW}log_note")
    with open("ai-log.txt", "a+") as f:
        f.write(message +"\n\n")

def read_log_note() -> str:
    """
    Read the previously saved logged notes, (assistant only)

    Returns: string of previously saved log notes
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.YELLOW}read_log_note")
    if os.path.exists("./ai-log.txt"):
        with open("ai-log.txt", "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "NO log has been created."

def zip_archive_files(file_name: str, files: list[str]) -> str:
    """
    Zip files into a single zip file.

    Args:
      file_name: The name of the zip file (needs to include .zip).
      files: A list of file paths to zip.

    Returns: The path to the zip file.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.YELLOW}zip_files")
    try:
        with zipfile.ZipFile(file_name, "w") as zipf:
            for file in files:
                # Add file to zip with just its basename to avoid including full path
                zipf.write(file, arcname=os.path.basename(file))
        print(f"{Fore.GREEN}Files zipped successfully{Style.RESET_ALL}")
        return file_name
    except Exception as e:
        print(f"{Fore.RED}Error zipping files: {e}{Style.RESET_ALL}")
        return f"Error zipping files: {e}"

def zip_extract_files(zip_file: str, extract_path: str | None) -> list[str]:
    """
    Extract files from a zip archive.

    Args:
      zip_file: The path to the zip file to extract.
      extract_path: The directory to extract files to. If None, extracts to current directory.

    Returns: A list of paths to the extracted files.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}zip_extract_files {Fore.YELLOW}{zip_file}")
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
        
        print(f"{Fore.GREEN}Files extracted successfully to {extract_path}{Style.RESET_ALL}")
        return extracted_files
    except Exception as e:
        print(f"{Fore.RED}Error extracting zip file: {e}{Style.RESET_ALL}")
        return f"Error extracting zip file: {e}"

def get_environment_variable(key: str) -> str:
    """
    Retrieve the value of an environment variable.

    Args:
      key: The name of the environment variable.

    Example: `get_environment_variable("PYTHON_HOME")`

    Returns: The value of the environment variable, or error message if the variable is not set.
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_environment_variable")
    try:
        value = os.getenv(key)
        return value
    except Exception as e:
        print(f"{Fore.RED}Error retrieving environment variable '{key}': {e}{Style.RESET_ALL}")
        return f"Error retrieving environment variable {e}"


def reddit_search(subreddit: str, query: str, sorting: str) -> dict:
    """
    Search inside `all` or specific subreddit in reddit to get information.
    This function CAN also work WITHOUT a query with just sorting of specific subreddit/s
    just provide the sorting from one of these ['hot', 'top', 'new'] and leave query as empty string

    Args:
        query: The query string to search for, leave as empty string if you are looking for specific sorting like "new" or "hot" all
        subreddit: The name of the subreddit or 'all' to get everyhing, subreddit names can be mixed for example 'Python+anime+cpp' which could combine them.
        for global search use 'all'
        sorting: the sorting of the post, can be 'relevance', 'hot', 'top', 'new' or 'comments', use 'top' as default
    
    Example: `reddit_search("AI")`

    Returns: A list of JSON data with information containing submission_id, title, text (if any), number of comments, name of subreddit, upvote_ratio, url   
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}reddit_search {Fore.YELLOW} [query={query}] [subreddit={subreddit}] [sort={sorting}]")
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
        results.append({
            "submission_id": s.name or "N/A",
            "title": s.title or "N/A",
            "text": (s.selftext if s.is_self else s.url) or "N/A",
            "num_comments": s.num_comments,
            "subreddit_name": s.subreddit.display_name or "N/A",
            "upvote_ratio": s.upvote_ratio or "N/A"
        })

    print(f"{Fore.CYAN}  ├─Fetched {len(results)} reddit results.")
    return results

def get_reddit_post(submission_id: str) -> dict:
    """Get contents like text title, number of comments subreddit name of a specific 
    reddit post.
    This does not include comments

    Args:
        submission_id: the submission id of the reddit post
        
    Usage Example: 
        if you have a link of a subreddit like so: `https://www.reddit.com/r/Python/comments/1iyc8qb/excel_formulas_to_python_code_using_llms/`
        use the id like: 1iyc8qb
        so: `reddit_submission_contents("1iyc8qb")`

    Returns: A JSON data of the comments including authors name and the body of the reddit post
    """

    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}get_reddit_post")

    s = reddit.submission(submission_id)
    if not s:
        return "Submission not found/Invalid ID"

    result = {
        "submission_id": s.name or "N/A",
        "title": s.title or "N/A",
        "text": (s.selftext if s.is_self else s.url) or "N/A",
        "num_comments": s.num_comments,
        "subreddit_name": s.subreddit.display_name or "N/A",
        "upvote_ratio": s.upvote_ratio or "N/A"
    }
    
    return result

def reddit_submission_comments(submission_id: str) -> dict: 
    """
    Get a compiled list of comments of a specific reddit post
    For finding solutions for a problem, solutions are usually in the comments, so this will be helpful for that
    (Might not include all comments)

    Args:
        submission_id: the submission id of the reddit post

    Example: `reddit_submission_comments("xnobgz")`

    Returns: A JSON data of the comments including authors name and the body of the reddit post
    """
    print(f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}reddit_submission_comments")

    submission = reddit.submission(submission_id)
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

TOOLS = [
    reddit_search,
    get_reddit_post,
    reddit_submission_comments,
    log_note,
    read_log_note,
    list_dir,
    duckduckgo_search_tool,
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
    get_website_text_content,
    http_get_request,
    open_url,
    download_file_from_url,
    get_system_info,
    run_shell_command,
    get_current_time,
    evaluate_math_expression,
    get_current_directory,
    zip_archive_files,
    zip_extract_files,
    get_environment_variable,
]