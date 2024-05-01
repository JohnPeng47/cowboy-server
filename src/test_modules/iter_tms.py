from cowboy_lib.utils import get_current_git_commit
from cowboy_lib.repo.source_repo import SourceRepo

from src.test_modules.models import TestModule

from typing import List


# TODO: move this code into a TestModule service
def iter_test_modules(src_repo: SourceRepo) -> List[TestModule]:
    from collections import Counter

    """
    Generator for TestModules
    TestModules can be either be:
    1. All the individual functions inside a TestFile
    2. All the functions inside a class inside a TestFile
    3. Some of the individual functions inside a TestFile
    4. Some of the functions inside a class inside a TestFile
    """
    test_modules: List[TestModule] = []
    for test_file in src_repo.test_files:
        ind_funcs = [f for f in test_file.test_funcs() if not f.scope]
        if ind_funcs:
            func_module = TestModule(
                test_file, ind_funcs, get_current_git_commit(src_repo.repo_path)
            )
            test_modules.append(func_module)

        for test_class in test_file.test_classes():
            class_module = TestModule(
                test_file, [test_class], get_current_git_commit(src_repo.repo_path)
            )
            test_modules.append(class_module)

    # NOTE: literally dont work and literally dont need
    # name_counter = Counter([tm.name for tm in test_modules])
    # while any([count > 1 for count in name_counter.values()]):
    #     for tm in test_modules:
    #         if name_counter[tm.name] > 1:
    #             tm.name = get_new_name(tm.name, tm.test_file.path)
    #             name_counter = Counter([tm.name for tm in test_modules])

    return test_modules
