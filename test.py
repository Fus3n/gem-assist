import ast
import sys
from typing import List, Dict, Optional, Any, Union # For type hinting

# Define a type alias for the dictionary structure for clarity
FunctionDetails = Dict[str, Any] 

class FunctionInfoVisitor(ast.NodeVisitor):
    """
    An AST node visitor that collects detailed information about function
    and method definitions, including their name, line numbers, and
    the name of the class they belong to (if any).
    """
    def __init__(self):
        # List to store the dictionaries of function details
        self.functions_info: List[FunctionDetails] = []
        # Keep track of the current class context
        self._current_class_name: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        # Entering a class definition
        original_class_name = self._current_class_name # Handle nested classes
        self._current_class_name = node.name
        
        # Visit children (methods, nested classes, etc.) within this class context
        # Use generic_visit to ensure we process everything inside the class
        self.generic_visit(node) 
        
        # Exiting the class definition, restore previous context
        self._current_class_name = original_class_name

    def _record_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        """Helper method to record function details."""
        # Use getattr for end_lineno for compatibility with older Python versions
        # where it might not be present (though it's standard in >= 3.8)
        end_lineno = getattr(node, 'end_lineno', None)
        
        function_data: FunctionDetails = {
            'name': node.name,
            'lineno': node.lineno,
            'end_lineno': end_lineno,
            'class_name': self._current_class_name # Will be None if not in a class
        }
        self.functions_info.append(function_data)
        
        # Important: Also visit children of the function node to find 
        # nested functions. These nested functions will correctly inherit
        # the _current_class_name context from their parent scope.
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Found a synchronous function definition (def)
        self._record_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Found an asynchronous function definition (async def)
        self._record_function(node)

def get_function_details_from_file(filepath: str) -> Optional[List[FunctionDetails]]:
    """
    Parses a Python file and returns a list of dictionaries, each containing
    details about a function/method found (name, line numbers, class context).

    Args:
        filepath (str): The path to the Python file.

    Returns:
        Optional[List[FunctionDetails]]: A list of dictionaries with function info,
                                          or None if the file cannot be processed.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
        return None

    try:
        tree = ast.parse(source_code, filename=filepath)
    except SyntaxError as e:
        print(f"Error parsing file {filepath}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during parsing {filepath}: {e}", file=sys.stderr)
        return None

    # Create and run the visitor
    visitor = FunctionInfoVisitor()
    visitor.visit(tree) # Start the traversal
    
    return visitor.functions_info

# --- Example Usage ---
# Use the same 'my_script.py' from previous examples
file_to_inspect = 'assistant.py' # Replace with your 'assistant.py' or other file
details = get_function_details_from_file(file_to_inspect)

if details is not None:
    print(f"Functions found in {file_to_inspect}:")
    for func_info in details:
        print(f"- {func_info}") 
        # Or format it more nicely:
        # class_ctx = f"in class '{func_info['class_name']}'" if func_info['class_name'] else "top-level/nested"
        # print(f"  Name: {func_info['name']}, Lines: {func_info['lineno']}-{func_info['end_lineno']}, Context: {class_ctx}")