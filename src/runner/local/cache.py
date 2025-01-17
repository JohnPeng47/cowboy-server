import sqlite3
import hashlib
import json
import pickle
from functools import wraps
from pathlib import Path
from typing import Any, Optional, List
import inspect

from src.lib.test_modules import TestModule
from src.lib.coverage import CoverageResult
from src.lib.repo.repository import PatchFile

from src.utils import green_text
from src.logger import buildtm_logger as log

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
DB_PATH = CACHE_DIR / "test_cache.db"

def init_cache():
    """Initialize the SQLite cache database"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_cache (
            hash TEXT PRIMARY KEY,
            result BLOB
        )
    """)
    conn.commit()
    conn.close()

def compute_hash(repo_name: str, 
                 exclude_tests: list, 
                 include_tests: TestModule, 
                 patch_file: Optional[PatchFile]) -> str:
    """Compute a hash of the input arguments"""
    hash_input = {
        "repo_name": repo_name,
        "exclude_tests": exclude_tests,
        "include_tests": include_tests.to_str() if include_tests else None,
        "patch": patch_file.patch if patch_file else None
    }

    # janky, idk why sometimes I pass string and sometimes Function
    if hash_input["exclude_tests"] and not isinstance(hash_input["exclude_tests"][0][0], str):
        hash_input["exclude_tests"] = [(func[0].to_json(), str(func[1])) for func in hash_input["exclude_tests"]]

    hash_str = json.dumps(hash_input, sort_keys=True)
    return hashlib.sha256(hash_str.encode()).hexdigest()

def read_cache(hash_key: str) -> Optional[CoverageResult]:
    """Read a result from the cache"""
    print("read: ", hash_key)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT result FROM test_cache WHERE hash = ?", (hash_key,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return pickle.loads(row[0])
    return None

def save_cache(hash_key: str, result: CoverageResult):
    """Save a result to the cache"""
    print("save: ", hash_key, result)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO test_cache (hash, result) VALUES (?, ?)",
        (hash_key, pickle.dumps(result))
    )
    conn.commit()
    conn.close()

def cache_test_run(func):
    """Decorator to cache test run results"""
    @wraps(func)
    async def wrapper(
        repo_name: str,
        service_args: Any,
        exclude_tests: list = [],
        include_tests: TestModule = None,
        patch_file: Optional[PatchFile] = None,
        stream = False,
        use_cache = True,
        delete_last = False,
    ) -> CoverageResult:        
        if use_cache:
            init_cache()
            cache_key = compute_hash(repo_name, exclude_tests, include_tests, patch_file)
            if delete_last:
                # Delete the last existing entry for the computed hash
                delete_cache_entry(cache_key)
            
            cached_result = read_cache(cache_key)
            if cached_result is not None:
                caller = inspect.stack()[1]  # Get immediate caller
                print(green_text(f"Returning from cache[Coverage]: {(repo_name, exclude_tests, include_tests)}"))
                print(green_text(f"|---> Called from {caller.filename}:{caller.lineno} in {caller.function}"))
                return cached_result
            
        # collecting basecov for the first time, we will stream the result to the console
        if not exclude_tests and not include_tests and not patch_file:
            log.info("First time running base coverage, streaming to console")
            stream = True

        result = await func(repo_name, service_args, exclude_tests, include_tests, patch_file, stream)
        if use_cache and not cached_result:
            log.info(f"Saving to cache: {(repo_name, exclude_tests, include_tests)}")
            save_cache(cache_key, result)

        return result
    return wrapper

def delete_cache_entry(hash_key: str):
    """Delete a cache entry by hash key"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM test_cache WHERE hash = ?", (hash_key,))
    conn.commit()
    conn.close()