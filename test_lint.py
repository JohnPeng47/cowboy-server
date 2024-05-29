import subprocess

TEST_CODE = """
import pytest

from codecov_cli.fallbacks import FallbackFieldEnum
from codecov_cli.helpers.ci_adapters.bitbucket_ci import BitbucketAdapter


class BitbucketEnvEnum(str, Enum):
    BITBUCKET_BUILD_NUMBER = "BITBUCKET_BUILD_NUMBER"
    BITBUCKET_BRANCH = "BITBUCKET_BRANCH"
    BITBUCKET_PR_ID = "BITBUCKET_PR_ID"
    BITBUCKET_COMMIT = "BITBUCKET_COMMIT"
    BITBUCKET_REPO_FULL_NAME = "BITBUCKET_REPO_FULL_NAME"
    CI = "CI"


class TestBitbucket(object):







    @pytest.mark.parametrize(
        "env_dict,expected",
        [
            ({}, None),
            ({BitbucketEnvEnum.BITBUCKET_BRANCH: "abc"}, "abc"),
        ],
    )
    def test_branch(self, env_dict, expected, mocker):
        mocker.patch.dict(os.environ, env_dict)
        actual = BitbucketAdapter().get_fallback_value(FallbackFieldEnum.branch)

        assert actual == expected

    def test_service(self):
        assert (
            BitbucketAdapter().get_fallback_value(FallbackFieldEnum.service)
            == "bitbucket"
        )

    def test_get_job_code(self, mocker):
        expected_job_number = "42"
        mocker.patch.dict(os.environ, {"BITBUCKET_BUILD_NUMBER": expected_job_number})
        assert BitbucketAdapter()._get_job_code() == expected_job_number
    def test_get_pull_request_number(self, mocker):
        expected_pr_id = "10"
        mocker.patch.dict(os.environ, {"BITBUCKET_PR_ID": expected_pr_id})
        assert BitbucketAdapter()._get_pull_request_number() == expected_pr_id
"""


def to_linted_code(lines) -> str:
    """
    Lint generated code file
    """
    black_cmd_str = "python3 -m black "
    tmp_file = f"/tmp/test.py"
    with open(tmp_file, mode="w+t", encoding="utf-8") as temp_file:
        # temp_file_name = temp_file.name
        temp_file.write("\n".join(lines))
        temp_file.flush()

        process = subprocess.Popen(
            black_cmd_str + tmp_file,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        if stderr:
            stderr = stderr.decode("utf-8")
            if "python" in stderr:
                raise Exception(f"Error while linting: {stderr}")
            if "error:" in stderr:
                raise Exception(f"Error while linting: {stderr}")

        with open(tmp_file, "r") as temp_file:
            linted_code = temp_file.read()

    return linted_code


print(to_linted_code(TEST_CODE.split("\n")))
