from src.lib.repo import GitRepo, SourceRepo
from src.lib.repo.repository import ResetRemoteCommitContext
from pathlib import Path

TEST_REPO = "tests/data/repos/codecov-cli-neuteured"


def git_repo():
    return GitRepo(Path(TEST_REPO))


def src_repo():
    return SourceRepo(Path(TEST_REPO))


def test_git_delete_remote(git_repo: GitRepo, src_repo: SourceRepo):
    with ResetRemoteCommitContext(git_repo) as ctx:
        fake_test = """
    def fake_test():
        pass
"""
        test_file = src_repo.find_file("tests/ci_adapters/test_bitrise.py")
        test_file.append(fake_test, class_name="TestBitrise")
        src_repo.write_file(str(test_file.path))

        ctx.add_commit_push([str(test_file.path)], "test_git_delete_remote test commit")


test_git_delete_remote(git_repo(), src_repo())
