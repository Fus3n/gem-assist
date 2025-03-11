from colorama import Back, Fore, Style

def print_header(title: str, width: int = 60):
    
    title = f" {title} "
    padding = (width - len(title)) // 2
    print(f"\n{Back.BLUE}{Fore.WHITE}┌{'─' * width}┐{Style.RESET_ALL}")
    print(
        f"{Back.BLUE}{Fore.WHITE}│{' ' * padding}{title}{' ' * (width - len(title) - padding)}│{Style.RESET_ALL}"
    )
    print(f"{Back.BLUE}{Fore.WHITE}└{'─' * width}┘{Style.RESET_ALL}\n")

def bytes_to_mb(size: int):
    """Convert bytes to megabytes"""
    return size / 1024 / 1024

def seconds_to_hms(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

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