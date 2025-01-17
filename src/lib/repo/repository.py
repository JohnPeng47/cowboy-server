from src.lib.utils import gen_random_name
from src.lib.repo.diff import CommitDiff

import os
import tempfile
import hashlib
from pathlib import Path
from logging import getLogger
from git import Repo, GitCommandError
from dataclasses import dataclass
import shutil
import random
from typing import List, Union, Tuple
from pydantic import BaseModel

log = getLogger(__name__)


class NoRemoteException(Exception):
    pass


class NoMainBranch(Exception):
    pass


def del_file(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat

    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


class GitRepo:
    """
    Used to manage git operations on a git repo
    """

    def __init__(self, repo_path: Path, remote: str = "origin", main: str = ""):
        if not repo_path.exists():
            # test suite may be renamed or deleted
            raise Exception("GitRepo does not exist: ", repo_path)

        # used for reversing patches
        self.patched_files = {}
        self.repo_folder = repo_path
        self.repo = Repo(repo_path)
        self.head = self.repo.head

        if main:
            if not self.branch_exists(main):
                raise NoMainBranch(main)
        else:
            potential = ["master", "main"]
            for branch in potential:
                main = branch if self.branch_exists(branch) else ""
                if main:
                    break
            if not main:
                raise NoMainBranch(main)

        self.main = main
        try:
            self.origin = self.repo.remotes.__getattr__(remote)
        except AttributeError:
            raise NoRemoteException(remote)

        self.username = self.origin.url.split("/")[-2]
        self.repo_name = self.origin.url.split("/")[-1]

        self.branch_prefix = "cowboy_"

    @classmethod
    def clone_repo(cls, clone_dst: Path, url: str) -> Path:
        """
        Creates a clone of the repo locally
        """
        if not os.path.exists(clone_dst):
            os.makedirs(clone_dst)  # Ensure the destination folder exists

        Repo.clone_from(url, clone_dst)
        return cls(clone_dst)

    @classmethod
    def delete_repo(cls, repo_dst: Path):
        """
        Deletes a repo from the db and all its cloned folders
        """
        import platform

        if not repo_dst.exists():
            return

        if platform.system() == "Windows":
            shutil.rmtree(repo_dst, onerror=del_file)
        else:
            shutil.rmtree(repo_dst)

    def reset_to_commit(self, commit_sha, parent=None, head: int = 0):
        """
        Resets the index of the repository to a specific commit.
        """
        self.repo.git.reset(f"--hard", commit_sha)
        return f"Successfully reset to commit {commit_sha}"

    def reset_to_commit_head(self, head: int = 0):
        head = f"HEAD~{str(head)}" if head else ""

        self.repo.git.reset(f"--hard", head)
        return f"Successfully reset to commit {head}"

    def commit_exists(self, commit_sha: str) -> bool:
        """
        Checks if a commit exists in the repo
        """
        try:
            self.repo.commit(commit_sha)
            return True
        except Exception:
            return False

    def get_curr_commit(self):
        """
        Returns the current commit sha
        """
        return self.head.commit.hexsha

    def get_prev_commit(self, commit_sha):
        """
        Returns the previous commit of a given commit sha
        """
        return self.repo.commit(commit_sha).parents[0]

    def apply_patch(self, patch: str) -> None:
        """
        Applies a patch from a .diff file to a single file in the repository
        """
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as patch_file:
            patch_file.write(patch.encode("utf-8") + b"\n")
            patch_file.flush()

        patch_hash = hashlib.md5(patch.encode("utf-8")).hexdigest()
        self.repo.git.apply(patch_file.name, whitespace="nowarn")
        self.patched_files[patch_hash] = patch_file.name

    def reverse_patch(self, patch: str) -> None:
        """
        Reverses a patch from a .diff
        """
        patch_hash = hashlib.md5(patch.encode()).hexdigest()
        patch_file = self.patched_files[patch_hash]

        self.repo.git.apply(patch_file, reverse=True)
        self.patched_files.pop(patch_hash)

    def branch_exists(self, branch: str):
        """
        Checks if a branch exists in the repo
        """
        # print(f"Branch: {branch}")
        # print(f"Branches {[str(br) for br in self.repo.heads]} in {self.repo_folder}")
        if branch in [str(br) for br in self.repo.heads]:
            print(
                branch,
                [str(br) for br in self.repo.heads],
                branch in [str(br) for br in self.repo.heads],
            )
            return True

        return False

    def checkout(self, branch_name: str, new=False):
        """
        Checks out an existing branch in the repo
        """
        if new:
            branch = self.repo.create_head(branch_name)
        else:
            branch = self.repo.heads[branch_name]

        print(f"Checking out: {branch}")
        branch.checkout()

    def clean_branches(self, branch_prefix: str):
        """
        Deletes all branches with a specific prefix
        """
        removed = []
        for branch in self.repo.branches:
            if branch.name.startswith(branch_prefix):
                removed.append(branch.name)
                self.repo.delete_head(branch)

        return removed

    @property
    def remote_commit(self) -> str:
        """
        Gets the sha of latest commit on origin
        """
        self.repo.remotes.origin.fetch()
        remote_sha = self.repo.remotes.origin.refs.__getattr__(self.main).commit.hexsha

        return remote_sha

    @property
    def local_commit(self) -> str:
        return self.repo.head.commit.hexsha

    # TODO: move this into sync_repo
    def fetch_diffs(self) -> Tuple[CommitDiff, str]:
        """
        Diffs the remote with our local repo
        """
        try:
            if self.local_commit == self.remote_commit:
                print("No updates available.")
                return None, None
            else:
                print("Updates found!")

                # Get the diff between the old commit and the new HEAD
                diff = self.repo.git.diff(self.local_commit, self.remote_commit)
                commit_diff = CommitDiff(diff)

                return commit_diff, self.remote_commit
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def pull(self):
        self.repo.remotes.origin.pull()

    def add_n_commit(self, files: List[str], msg: str):
        self.repo.index.add(files)
        self.repo.index.commit(msg)

    def push(self, branch_name: str = "", force: bool = False):
        if not branch_name:
            branch_name = self.main
        self.origin.push(refspec=f"{branch_name}:{branch_name}", force=True)

    def checkout_and_push(
        self,
        name: str,
        commit_message: str,
        files_to_commit: list,
    ):
        """
        Checks out a new branch, commits changes, and pushes to the remote. Returns the
        URL for the merge request of our new branch against main

        Args:
        - name: The "suggested" name
        - commit_message: The commit message to use.
        - files_to_commit: List of file paths (relative to the repo root) to commit.

        Returns:
        - None
        """
        branch_name = name
        if self.branch_exists(name):
            branch_name = self.branch_prefix + name + "_" + gen_random_name()

        # Check out a new branch
        try:
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            # Add and commit changes
            self.repo.index.add(files_to_commit)
            self.repo.index.commit(commit_message)
            self.push(branch_name=branch_name)
            origin_url = self.origin.url.replace(".git", "")
        except Exception as e:
            log.error(f"Exception in {self.repo_name}: {str(e)}")
            pass
        finally:
            self.checkout(self.main)
            log.info(f"Resetting to branch {self.main}")

        # url for branch merge request
        return f"{origin_url}/compare/{self.main}...{self.username}:{self.repo_name}:{branch_name}?expand=1"


class PatchApplyExcepion(Exception):
    pass


class IncompatibleCommit(Exception):
    pass


class PatchFile(BaseModel):
    path: Path
    patch: str
    original: str = ""


class PatchFileContext:
    """
    Context manager for applying and reversing patches
    """

    def __init__(
        self, repo: GitRepo, patches: List[PatchFile], revert: bool = True
    ):
        self.repo = repo
        # Convert single patch to list for uniform handling
        uniq_files = set([p.path for p in patches])
        if len(uniq_files) != len(patches):
            raise Exception("Multiple patches for same file is not supported")

        self.patches = patches
        self.head_commit = self.repo.head.commit if self.patches else None
        self.failed_id = random.randint(0, 1000000)
        self.revert = revert
        # Track which string patches were applied for reversal
        self.applied_string_patches = []

    def __enter__(self):
        if not self.patches:
            return
        try:
            for patch in self.patches:
                if not isinstance(patch, PatchFile):
                    raise Exception("Invalid patch type, not type PatchFile")
                with open(patch.path, "w", encoding="utf-8") as f:
                    # print("Applying patch to file: ", patch.path)
                    # print(patch.patch)
                    f.write(patch.patch)

        except GitCommandError as e:
            raise PatchApplyExcepion(e)

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.patches:
            return

        try:
            if self.revert:
                # First reverse any string patches that were applied
                for patch in reversed(self.applied_string_patches):
                    self.repo.reverse_patch(patch)

                # NEWTODO: think we should get rid of this ... relying on git commit reset 
                # means that effectively running this after any file changes will reset the changes even
                # if they are outside of the PatchFileContext
                # Then reset any PatchFile changes
                if any(isinstance(p, PatchFile) for p in self.patches):
                    self.repo.reset_to_commit(self.head_commit)

        except GitCommandError as e:
            log.info("Error reversing patch")
            raise PatchApplyExcepion(e)


class ResetLocalCommitContext:
    """
    Resets the repository to a specific commit
    """

    def __init__(self, repo: GitRepo, fd_reset: bool = False, revert: bool = True):
        self.repo = repo
        self.revert = revert
        self.fd_reset = fd_reset

    def __enter__(self):
        """
        Saves the current commit hash when entering the context.
        """
        self.original_commit = self.repo.head.commit.hexsha
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Restores the repository to the original commit when exiting the context.
        """
        if exc_type is not None:
            print(f"An exception occurred: {exc_type.__name__}: {exc_value}")
            # Optionally, log the traceback here

        if self.fd_reset:
            self._add_files()

        if self.original_commit and self.revert:
            self.repo.reset_to_commit(self.original_commit)

        # reset the patched files in GitRepo
        self.repo.patched_files = {}

    def _add_files(self):
        """
        Adds all files in repo so that they are tracked by git and can be resetted
        when the context is exited
        """
        self.repo.repo.git.add(".")
        print(self.repo.repo.git.status())

    def reset_to_commit(self, commit_sha: str, parent=None):
        """
        Resets the index of the repository to a specific commit.
        """
        return self.repo.reset_to_commit(commit_sha, parent)


class ResetRemoteCommitContext:
    """
    Pushes a single commit to remote repo and then reverts it in the remote
    by pushing HEAD~1. Used for unit tests
    """

    def __init__(self, repo: GitRepo):
        self.repo = repo
        self._called = False

    def __enter__(self):
        """
        Saves the current commit hash when entering the context.
        """
        self.original_commit = self.repo.head.commit.hexsha
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Restores remote repo to HEAD~1
        """
        if not self._called:
            # reset local repo state if we dont end up pushing
            self.repo.reset_to_commit(self.original_commit)
            print("Resetting to og state")
            return

        self.repo.reset_to_commit_head(head=1)
        self.repo.push()

    def add_commit_push(self, files: List[str], msg: str):
        """
        Adds a commit to the repo and pushes it to the remote
        """
        try:
            self.repo.add_n_commit(files, msg)
            self.repo.push()
        except Exception as e:
            print("Error adding commit")
            self.repo.reset_to_commit(self.original_commit)
            raise e
        finally:
            self._called = True
