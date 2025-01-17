from typing import List, Tuple
import ast
from dataclasses import dataclass
from ..code import Function, Class, Decorator, Argument, ASTNode, NodeType

from logging import getLogger

logger = getLogger("test_results")
AST_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)

@dataclass
class Indentation:
    char: str
    size: int

# REFACTOR-AST: this whole function needs to be replaced by the Bloop/tree-sitter
# implementation
class PythonAST:
    def __init__(self, code: str):
        assert isinstance(code, str)

        self.classes: List[ASTNode] = []
        self.functions: List[ASTNode] = []

        self._code = code

    def _detect_indentation(self) -> Tuple[str, int]:
        """Detect the indentation character and size used in the code.
        
        Returns:
            Tuple[str, int]: (indent_char, indent_size) where indent_char is either
                            '\t' for tabs or ' ' for spaces, and indent_size is the
                            number of spaces (always 1 for tabs)
        """
        lines = self._code.split("\n")
        indents = []
        
        # Collect all indentations
        for line in lines:
            # Skip empty lines and lines with no indentation
            if not line or not line[0].isspace():
                continue
                
            # Get leading whitespace
            indent = ""
            for char in line:
                if char in (" ", "\t"):
                    indent += char
                else:
                    break
                    
            if indent:
                indents.append(indent)
        
        if not indents:
            return Indentation(" ", 4)  # Default to 4 spaces if no indentation found
            
        # Check first indent to determine if using tabs or spaces
        first_indent = indents[0]
        if "\t" in first_indent:
            return Indentation("\t", 1)
            
        # For spaces, find the most common indent size
        # Get the length of the shortest indent as that's likely one level
        min_indent = min(len(indent) for indent in indents)
        return Indentation(" ", min_indent)

    # Thank you GPT!
    def _parse_decorators(self, node):
        decorators = []
        for d in node.decorator_list:
            # Initialize d_name as None
            d_name = None

            # Handle direct attribute access or function call with attribute access
            if isinstance(d, ast.Attribute) or (
                isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            ):
                d_name_parts = []

                # If it's a Call, we start with d.func to get the Attribute node
                current_node = d.func if isinstance(d, ast.Call) else d

                # Traverse the Attribute nodes
                while isinstance(current_node, ast.Attribute):
                    d_name_parts.append(current_node.attr)
                    current_node = current_node.value

                # The loop ends at an ast.Name node, which gives us the root name
                if isinstance(current_node, ast.Name):
                    d_name_parts.append(current_node.id)

                # Combine the parts to form the full decorator name
                d_name = ".".join(reversed(d_name_parts))

            elif isinstance(d, ast.Name):
                d_name = d.id

            # Append the decorator name to the list if it was found
            if d_name:
                range = self._get_range(d)
                decorators.append(
                    Decorator(
                        d_name,
                        # bring range to 0-based indexing
                        (range[0], getattr(d, "end_lineno", range[0]) - 1),
                        None,
                        [],
                        self._get_lines(*range),
                        d,
                    )
                )

        return decorators

    def _parse_classes(self, child: ast.AST, parent: ast.AST):
        classes = []
        if isinstance(child, ast.ClassDef):
            range = self._get_range(child)
            decorators = self._parse_decorators(child)

            scope = None
            if isinstance(parent, AST_FUNCTIONS) and isinstance(parent, ast.ClassDef):
                scope = self.find_node(parent)

            classes.append(
                Class(
                    child.name, range, scope, decorators, self._get_lines(*range), child
                )
            )
        return classes

    def _parse_functions(self, child: ast.AST, parent: ast.AST):
        functions = []
        if isinstance(child, AST_FUNCTIONS):
            func_name = child.name
            child_range = self._get_range(child)
            decorators = self._parse_decorators(child)

            args = [
                Argument(arg.arg, getattr(arg.annotation, "id", None))
                for arg in child.args.args
            ]

            # rethink this loop when not hungover...
            # assign funcs and classes as parents
            scope = None
            if isinstance(parent, AST_FUNCTIONS) or isinstance(parent, ast.ClassDef):
                scope = self.find_node(parent)

            func = Function(
                func_name,
                child_range,
                scope,
                decorators,
                self._get_lines(*child_range),
                child,
                arguments=args,
            )

            # if a parent class contains a test function, then parent class is a test class
            if scope and isinstance(parent, ast.ClassDef):
                scope.add_func(func)
                if func.is_test:
                    scope.set_is_test(True)

            functions.append(func)

        return functions

    def find_node(self, node: ast.AST) -> ASTNode:
        return next(filter(lambda x: x.is_ast(node), self.classes + self.functions))

    def _get_range(self, node: ast.AST):
        """AST nodes are 1-indexed"""
        return (node.lineno - 1, node.end_lineno - 1)

    def _get_lines(self, start: int, end: int) -> List[str]:
        return self._code.split("\n")[start : end + 1]

    def parse(self) -> Tuple[List[Function], List[Class]]:
        def set_parents(node, parent=None):
            for child in ast.iter_child_nodes(node):
                child.parent = node
                set_parents(child, node)

        def parse_ast(node, parent=None):
            # classes guranteed to be parsed before their child methods right?
            for child in ast.iter_child_nodes(node):
                self.classes.extend(self._parse_classes(child, parent))
                self.functions.extend(self._parse_functions(child, parent))

                parse_ast(child, parent=child)

        tree = ast.parse(self._code)

        set_parents(tree)
        parse_ast(tree)

        indentation = self._detect_indentation()
        return self.functions, self.classes, indentation
