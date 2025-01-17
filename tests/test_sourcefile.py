import pytest
from pathlib import Path
from src.lib.repo.source_file import TestFile, SourceFile, NodeType, NodeNotFound
from src.lib.ast import PythonAST

def test_source_file_basic_operations():
    """Test basic SourceFile operations and properties"""

    # NOTE: these are spaces not tabs
    sample_code = [
        "def test_function():",
        "    return 42",
        "",
        "",
        "class TestClass:",
        "    def method(self):",
        "        pass",
        ""
    ]
    
    source = SourceFile(lines=sample_code, path=Path("test.py"))
    
    # Test basic properties
    assert str(source.path) == "test.py"
    assert source.lines == sample_code
    
    # Test function finding
    func = source.find_function("test_function")
    assert func.name == "test_function"
    assert func.type == NodeType.Function
    
    # Test class finding
    cls = source.find_class("TestClass")
    assert cls.name == "TestClass"
    assert cls.type == NodeType.Class
    
    # Test non-existent node
    with pytest.raises(NodeNotFound):
        source.find_function("nonexistent_function")
        
    # Test to_code
    assert source.to_code() == "\n".join(sample_code)

def test_source_file_append_meth():
    """Test appending code to SourceFile"""
    initial_code = [
        "class TestClass:",
        "    def method1(self):",
        "        pass",
        ""
    ]
    
    source = SourceFile(lines=initial_code, path=Path("test.py"))
    
    # Test appending to class
    new_method = """    
def method2(self):
    return "test\""""
    
    source.append(new_method, class_name="TestClass")
    
    # Verify the new method was added
    new_method = source.find_function("TestClass.method2")
    assert new_method is not None
    assert source.find_indent(new_method.lines) == 1

def test_source_file_delete():
    """Test deleting nodes from SourceFile"""
    initial_code = [
        "def function1():",
        "    return 42",
        "",
        "class TestClass:",
        "    def method1(self):",
        "        pass",
        "",
        "def function2():",
        "    return True"
    ]
    
    source = SourceFile(lines=initial_code, path=Path("test.py"))
    
    # Test deleting a function
    source.delete("function1", node_type=NodeType.Function)
    with pytest.raises(NodeNotFound):
        source.find_function("function1")
        
    # Test deleting a class
    source.delete("TestClass", node_type=NodeType.Class)
    with pytest.raises(NodeNotFound):
        source.find_class("TestClass")
    
    # Verify remaining code structure
    assert len(source.classes) == 0
    assert len(source.functions) == 1
    assert len(source.lines) == 3
    assert source.find_function("function2") is not None


def test_detect_indentation():
    """Test detection of different indentation styles"""
    # Test tabs
    tab_code = [
        "def function1():",
        "\treturn 42",
        "",
        "class TestClass:",
        "\tdef method1(self):",
        "\t\tpass",
    ]
    parser = PythonAST("\n".join(tab_code))
    _, _, indent = parser.parse()
    assert indent.char == "\t"
    assert indent.size == 1

    # Test 2-space indentation
    two_space_code = [
        "def function1():",
        "  return 42",
        "",
        "class TestClass:", 
        "  def method1(self):",
        "    pass",
    ]
    parser = PythonAST("\n".join(two_space_code))
    _, _, indent = parser.parse()
    assert indent.char == " "
    assert indent.size == 2

    # Test 4-space indentation
    four_space_code = [
        "def function1():",
        "    return 42",
        "",
        "class TestClass:",
        "    def method1(self):",
        "        pass",
    ]
    parser = PythonAST("\n".join(four_space_code))
    _, _, indent = parser.parse()
    assert indent.char == " "
    assert indent.size == 4


    initial_code = [
        "class TestClass:",
        "    def method1(self):",
        "        pass",
        ""
    ]
    parser = PythonAST("\n".join(four_space_code))
    _, _, indent = parser.parse()
    print(indent)
    # assert indent.char == " "
    # assert indent.size == 4

# def test_scope_class():
#     """Test that test functions have correct scope assignment"""
#     sample_code = [
#         "def test_something():",
#         "    return True",
#         "",
#         "class TestClass:",
#         "    def test_method(self):",
#         "        pass",
#         ""
#     ]

#     source = TestFile(lines=sample_code, path=Path("test.py"))
    
#     # Test standalone test function scope
#     func = source.find_function("test_something")
#     assert func.scope is None  # Top-level functions have no scope
    
#     # Test method within class scope
#     method = source.find_function("TestClass.test_method")
#     assert method.scope.name == "TestClass"