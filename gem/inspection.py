"""
A set of functions to help inspect python files
"""
import ast
import sys
from typing import List, Dict, Optional, Any, Union

ImportInfo = Dict[str, Any]
ClassInfo = Dict[str, Any]
FunctionInfo = Dict[str, Any]
InspectionResults = Dict[str, List[Union[ImportInfo, ClassInfo, FunctionInfo]]]

class ScriptInspectorVisitor(ast.NodeVisitor):
    """
    An AST node visitor that collects details about imports, class definitions,
    and function/method definitions within a Python script.
    """
    def __init__(self):
        self.imports: List[ImportInfo] = []
        self.classes: List[ClassInfo] = []
        self.functions: List[FunctionInfo] = []
        self._current_class_name: Optional[str] = None

    def _get_end_lineno(self, node: ast.AST) -> Optional[int]:
        return getattr(node, 'end_lineno', None)


    def visit_Import(self, node: ast.Import):
        """Handles 'import module' or 'import module as alias'."""
        details = {
            'type': 'import',
            'lineno': node.lineno,
            'end_lineno': self._get_end_lineno(node),
            'names': []
        }
        for alias in node.names:
            details['names'].append({
                'name': alias.name,           # the actual module name
                'asname': alias.asname        # the alias (None if no 'as')
            })
        self.imports.append(details)
        self.generic_visit(node) 

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Handles 'from module import name' or 'from .module import name'."""
        details = {
            'type': 'import_from',
            'lineno': node.lineno,
            'end_lineno': self._get_end_lineno(node),
            'module': node.module,         
            'level': node.level,          
            'names': []
        }
        for alias in node.names:
            details['names'].append({
                'name': alias.name,          
                'asname': alias.asname       
            })
        self.imports.append(details)
        self.generic_visit(node) 


    def visit_ClassDef(self, node: ast.ClassDef):
        """Handles class definitions."""
        class_data: ClassInfo = {
            'name': node.name,
            'lineno': node.lineno,
            'end_lineno': self._get_end_lineno(node),
            'bases': [ast.dump(b) for b in node.bases], 
            'decorator_list': [ast.dump(d) for d in node.decorator_list] 
        }
        self.classes.append(class_data)

        original_class_name = self._current_class_name
        self._current_class_name = node.name

        self.generic_visit(node)
        self._current_class_name = original_class_name

    def _record_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        """Helper method to record function/method details."""
        function_data: FunctionInfo = {
            'name': node.name,
            'lineno': node.lineno,
            'end_lineno': self._get_end_lineno(node),
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'class_name': self._current_class_name 
        }
        self.functions.append(function_data)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._record_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._record_function(node)


def inspect_script(filepath: str) -> Optional[InspectionResults]:
    """
    Parses a Python file without importing it and returns details about
    its imports, classes, and functions/methods.

    Args:
        filepath (str): The path to the Python file.

    Returns:
        Optional[InspectionResults]: A dictionary containing lists of details
                                       for 'imports', 'classes', and 'functions',
                                       or None if the file cannot be processed.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
            source_code = f.read()

    tree = ast.parse(source_code, filename=filepath)
    visitor = ScriptInspectorVisitor()
    visitor.visit(tree) 

    results: InspectionResults = {
        'imports': visitor.imports,
        'classes': visitor.classes,
        'functions': visitor.functions,
    }
    return results

def get_func_source_code(filepath: str, function_name: str) -> Optional[str]:
    """
    Returns the source code of a function in a Python file.

    Args:
        filepath (str): The path to the Python file.
        function_name (str): The name of the function.

    Returns:
        Optional[str]: The source code of the function, or None if not found.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
            source_code = f.read()

    tree = ast.parse(source_code, filename=filepath)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            lines = source_code.split('\n')
            return ''.join(lines[node.lineno - 1:node.end_lineno])

    return None