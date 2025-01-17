from src.lib.repo.source_file import TestFile
from src.lib.test_modules import TestModule

from pathlib import Path

initial_code = [
    "def test_function1():",
    "    return 42",
    "",
    "def test_function2():",
    "    return True"
    "",
    "def test_function3():",
    "    return True"
    ""
]
sample_test = TestFile(lines=initial_code, path=Path("test.py"))
test_tm = TestModule(sample_test, False, "test_file.py", "rand_hash")

def test_tm_serialization_with_deletes():
    test_tm.test_file.delete("test_function2")
    test_tm.test_file.delete("test_function3")

    assert len(test_tm.test_file.test_funcs()) == 1

