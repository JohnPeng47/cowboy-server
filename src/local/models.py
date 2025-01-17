import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path

from src.config import EVAL_DATA_ROOT
from src.utils import yaml
from src.test_gen.augment_test.composer import TestAugmentArgs
from src.lib.test_modules import TestModule
from src.lib.coverage import TestCoverage

from .db import get_tm, get_repo, persist_tm

@dataclass
class TestCase:
    name: str
    coverage_added: int
    code: str

    @classmethod
    def from_dict(cls, data: Dict) -> "TestCase":
        return cls(
            name=data["name"],
            coverage_added=data["coverage_added"],
            code=data["code"]
        )

@dataclass
class TestResults:
    repo_name: str
    git_hash: str
    tm_name: str
    tests: List[TestCase]

    @classmethod
    def from_file(cls, file_path: Path) -> "TestResults":
        with open(file_path, "r") as f:
            data = yaml.safe_load(f.read())
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TestResults":
        return cls(
            repo_name=data["repo_name"],
            git_hash=data["git_hash"],
            tm_name=data["tm_name"],
            tests=[TestCase.from_dict(t) for t in data["tests"]]
        )

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class TestModuleData:
    """
    TestModuleData used for regular test generation
    """
    name: str
    file_content: str
    repo_config: Dict
    # NOTE: have to include this field here because Braintrust expects a single
    # Dict as input
    run_args: TestAugmentArgs = None

    def get_tm(self) -> Optional[TestModule]:
        return get_tm(self.repo_config["repo_name"], self.name)

    @classmethod
    def from_json(cls, data):
        return cls(
            name=data["name"],
            file_content=data["file_content"],
            repo_config=data["repo_config"]
        )
    
    def to_json(self) -> Dict:
        return {
            "name": self.name,
            "file_content": self.file_content,
            "repo_config": self.repo_config,
        }
    
    def add_args(self, run_args: TestAugmentArgs):  
        self.run_args = run_args

    def persist(self, tm: TestModule):
        repo_name = self.repo_config["repo_name"]
        repo_dir = EVAL_DATA_ROOT / repo_name
        repo_dir.mkdir(exist_ok=True)

        # Write the row data
        file_path = repo_dir / f"{self.name}.json"
        with open(file_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

        persist_tm(repo_name, tm)
 
@dataclass
class RemovedTest:
    name: str
    content: str
    cov: TestCoverage

    def to_json(self) -> Dict:
        return {
            "name": self.name,
            "content": self.content,
            "cov": self.cov.serialize()
        }
    
    @classmethod
    def from_json(cls, data) -> "RemovedTest":
        return cls(
            name=data["name"],
            content=data["content"],
            cov=TestCoverage.deserialize(data["cov"])
        )

@dataclass
class TestModuleEvalData(TestModuleData):
    """
    TestModuleData used for evaluations that contains extra fields for scoring evaluation results
    """
    tags: List[str] = field(default_factory=list)
    removed_tests: List[RemovedTest] = field(default_factory=list)
    expected: TestCoverage = field(default=None) # unique coverage contributed by this test case
        
    def to_json(self) -> Dict:
        return {
            "name": self.name,
            "file_content": self.file_content,
            "repo_config": self.repo_config,
            "removed_tests": [t.to_json() for t in self.removed_tests],
            "tags": self.tags,
            "expected": self.expected.serialize() if self.expected else None
        }
    
    def to_json_braintrust(self) -> Dict:
        return {
            "input": {
                "name": self.name,
                "file_content": self.file_content,
                "repo_config": self.repo_config,
                "removed_tests": [t.to_json() for t in self.removed_tests],
            },
            "tags": self.tags,
            "expected": self.expected.serialize() if self.expected else None
        }
    
    @classmethod
    def from_json(cls, data) -> "TestModuleEvalData":
        if not data.get("expected", None):
            raise ValueError("This data is probably not generated from setup-eval-repo")

        return cls(
            name=data["name"],
            file_content=data["file_content"],
            repo_config=data["repo_config"],
            removed_tests=[RemovedTest.from_json(t) for t in data["removed_tests"]],
            tags=data["tags"],
            expected=TestCoverage.deserialize(data["expected"]) if data.get("expected") else None
        )
    
def read_rows(repo_name: str,
              braintrust: bool,
              list_tms: bool = False,
              selected_tms: List[str] = [],
              limit=0) -> List["TestModuleEvalData"]:
    """
    Read TestModuleRows from disks
    """
    repo_dir = EVAL_DATA_ROOT / repo_name
    if not repo_dir.exists():
        raise ValueError(f"Dataset directory {repo_dir} does not exist")
    
    if list_tms:
        print(f"Reading {repo_name} dataset from {repo_dir}")
        print("Available datasets:")
        for file_path in repo_dir.glob("*.json"):
            with open(file_path) as f:
                data = TestModuleEvalData.from_json(json.load(f))
                repo_path = Path(data.repo_config["source_folder"])
                for test in data.removed_tests:
                    print(f"{test.content}")

                # for t in data.removed_tests:
                #     t.cov.read_line_coverage(repo_path)
                    
                #     print(f"{t.name}")
                #     for cov in t.cov.cov_list:
                #         covered_lines = cov.print_lines()
                #         print(f"{covered_lines}")

        return []

    all_datafiles = list(repo_dir.glob("*.json"))
    limit = limit if limit > 0 else len(all_datafiles)

    rows = []
    for file_path in all_datafiles[:limit]:
        if selected_tms and file_path.stem not in selected_tms:
            continue

        with open(file_path) as f:
            data = json.load(f)

            if not braintrust:
                rows.append(TestModuleData.from_json(data))
            else:
                rows.append(TestModuleEvalData.from_json(data))


    if selected_tms:
        for tm in selected_tms:
            if tm not in [row.name for row in rows]:
                raise Exception(f"TM: {tm} not found")

    print(f"Successfully read {len(rows)} rows from {repo_dir}")
    return rows