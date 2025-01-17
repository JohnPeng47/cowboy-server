import pytest
from src.lib.coverage import Coverage, TestCoverage

@pytest.fixture
def setup_coverages():
    coverage1 = Coverage("file1.py", [1, 2, 3, 4, 5], [6, 7, 8])
    coverage2 = Coverage("file1.py", [1, 2, 3], [4, 5, 6, 7])
    coverage3 = Coverage("file2.py", [10, 11, 12], [13, 14, 15])
    coverage4 = Coverage("file2.py", [10, 11], [12, 13, 14, 15])

    test_coverage1 = TestCoverage([coverage1, coverage3])
    test_coverage2 = TestCoverage([coverage2, coverage4])

    return test_coverage1, test_coverage2

def test_subtraction_length(setup_coverages):
    test_coverage1, test_coverage2 = setup_coverages
    result = test_coverage1 - test_coverage2
    assert len(result.cov_list) == 2

def test_subtraction_file1_coverage(setup_coverages):
    test_coverage1, test_coverage2 = setup_coverages
    result = test_coverage1 - test_coverage2

    expected_coverage1 = Coverage("file1.py", [4, 5], [1, 2, 3, 6, 7, 8])
    assert result.cov_list[0].filename == expected_coverage1.filename
    assert result.cov_list[0].covered_lines == expected_coverage1.covered_lines
    assert result.cov_list[0].missing_lines == expected_coverage1.missing_lines

def test_subtraction_file2_coverage(setup_coverages):
    test_coverage1, test_coverage2 = setup_coverages
    result = test_coverage1 - test_coverage2

    expected_coverage2 = Coverage("file2.py", [12], [10, 11, 13, 14, 15])
    assert result.cov_list[1].filename == expected_coverage2.filename
    assert result.cov_list[1].covered_lines == expected_coverage2.covered_lines
    assert result.cov_list[1].missing_lines == expected_coverage2.missing_lines

def test_diff_cov_positive_total():
    # First test coverage with 3 files
    coverage1_a = Coverage("file1.py", [1, 2, 3, 4], [5, 6])
    coverage1_b = Coverage("file2.py", [1, 2, 3], [4, 5])
    coverage1_c = Coverage("file3.py", [1, 2, 3, 4, 5], [6, 7])
    test_cov1 = TestCoverage([coverage1_a, coverage1_b, coverage1_c])
    
    # Second test coverage with 3 files
    coverage2_a = Coverage("file1.py", [1, 2], [3, 4, 5, 6])
    coverage2_b = Coverage("file2.py", [1], [2, 3, 4, 5])
    coverage2_c = Coverage("file3.py", [1, 2, 3], [4, 5, 6, 7])
    test_cov2 = TestCoverage([coverage2_a, coverage2_b, coverage2_c])
    
    # Keep lines from first coverage
    result1 = TestCoverage.diff_cov(test_cov1, test_cov2, keep_line=1)
    assert result1.cov_list[0].covered_lines == [3, 4]
    assert result1.cov_list[1].covered_lines == [2, 3]
    assert result1.cov_list[2].covered_lines == [4, 5]
    assert result1.isdiff is True
    assert result1.total_cov.covered == 6  # Total positive coverage

def test_normal_subtraction():
    # First test coverage with 3 files
    coverage1_a = Coverage("file1.py", [1, 2, 3, 4], [5, 6])
    coverage1_b = Coverage("file2.py", [1, 2, 3], [4, 5])
    coverage1_c = Coverage("file3.py", [1, 2, 3, 4, 5], [6, 7])
    test_cov1 = TestCoverage([coverage1_a, coverage1_b, coverage1_c])
    
    # Second test coverage with 3 files
    coverage2_a = Coverage("file1.py", [1, 2], [3, 4, 5, 6])
    coverage2_b = Coverage("file2.py", [1], [2, 3, 4, 5])
    coverage2_c = Coverage("file3.py", [1, 2, 3], [4, 5, 6, 7])
    test_cov2 = TestCoverage([coverage2_a, coverage2_b, coverage2_c])
    
    # Normal subtraction
    result = test_cov1 - test_cov2
    
    # The difference should be the lines that are covered in test_cov1 but not in test_cov2
    assert result.cov_list[0].covered_lines == [3, 4]  # file1.py: [1,2,3,4] - [1,2] = [3,4]
    assert result.cov_list[1].covered_lines == [2, 3]  # file2.py: [1,2,3] - [1] = [2,3]
    assert result.cov_list[2].covered_lines == [4, 5]  # file3.py: [1,2,3,4,5] - [1,2,3] = [4,5]
    assert result.isdiff is True
    assert result.total_cov.covered == 6

def test_get_covered():
    # First test coverage with 2 files
    coverage1_a = Coverage("file1.py", [1, 2, 3, 4], [5, 6])
    coverage1_b = Coverage("file2.py", [1, 2, 3], [4, 5, 6]) 
    test_cov1 = TestCoverage([coverage1_a, coverage1_b])

    # Second test coverage with 2 files
    coverage2_a = Coverage("file1.py", [1, 2, 3, 4, 5], [6])
    coverage2_b = Coverage("file2.py", [1, 2, 3, 6], [4, 5])
    test_cov2 = TestCoverage([coverage2_a, coverage2_b])

    # Test get_covered() which returns number of lines in test_cov2 that are also in test_cov1
    covered = test_cov1.get_covered(test_cov2)
    
    # test_cov2 has [1,2] covered in file1.py and [1] covered in file2.py
    # All of these lines are also covered in test_cov1
    # So total covered lines = 3
    assert covered == 7

def test_get_covered2():
    # First test coverage with 2 files
    coverage1_a = Coverage("file1.py", [1], [5, 6])
    coverage1_b = Coverage("file2.py", [1, 2, 3], [4, 5, 6]) 
    test_cov1 = TestCoverage([coverage1_a, coverage1_b])

    # Second test coverage with 2 files
    coverage2_a = Coverage("file1.py", [2], [6])
    coverage2_b = Coverage("file2.py", [1, 2, 3, 6], [4, 5])
    test_cov2 = TestCoverage([coverage2_a, coverage2_b])

    # Test get_covered() which returns number of lines in test_cov2 that are also in test_cov1
    covered = test_cov1.get_covered(test_cov2)
    
    # test_cov2 has [1,2] covered in file1.py and [1] covered in file2.py
    # All of these lines are also covered in test_cov1
    # So total covered lines = 3
    assert covered == 3

def test_add_coverage():
    # Create empty base coverage
    test_cov1 = TestCoverage([], isdiff=True)

    # First test coverage with 2 files
    coverage1_a = Coverage("file1.py", [1, 2], [3, 4])
    coverage1_b = Coverage("file2.py", [1], [2, 3])
    test_cov2 = TestCoverage([coverage1_a, coverage1_b], isdiff=True)

    # Second test coverage with 2 files 
    coverage2_a = Coverage("file1.py", [3, 4], [1, 2])
    coverage2_b = Coverage("file2.py", [2, 3], [1])
    test_cov3 = TestCoverage([coverage2_a, coverage2_b], isdiff=True)

    test_cov1 += test_cov2

    assert test_cov1.total_cov.stmts == 7
    assert test_cov1.total_cov.covered == 3
    assert test_cov1.total_cov.misses == 4
    assert test_cov1.get_file_cov("file1.py", "").covered_lines == [1,2]
    assert test_cov1.get_file_cov("file2.py", "").covered_lines == [1]

    test_cov1 += test_cov3

    assert test_cov1.total_cov.stmts == 7
    assert test_cov1.total_cov.covered == 7
    assert test_cov1.total_cov.misses == 0
    assert test_cov1.get_file_cov("file1.py", "").covered_lines == [1,2,3,4]
    assert test_cov1.get_file_cov("file2.py", "").covered_lines == [1,2,3]


