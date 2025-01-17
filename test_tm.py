from src.lib.repo import SourceRepo
from src.local.models import read_rows
from src.local.db import get_tm

from pathlib import Path
import asyncio

repo_names = [
    "codecovapi-neutered2",
    "textual-neutered",
    "requests"
]
src_repo = SourceRepo(Path("/home/ubuntu/codecov-api"))

async def main():
    for repo_name in repo_names:
        rows = read_rows(repo_name, True)

        print("Covered file for: ", repo_name)
        for row in rows:
            try:
                tm = get_tm(repo_name, row.name)

                target_files = set([str(f) for f in tm.targeted_files()])
                target_files_chunks = set([str(f) for f in tm.targeted_files_from_chunks()])

                print(f"TM: {tm.name}")
                print("LLM: ", target_files)
                print("Chunks: ", target_files_chunks)
                print("Intersection: ", target_files.intersection(target_files_chunks))
                print("Intersect len: ", len(target_files.intersection(target_files_chunks)))

            except Exception as e:
                continue

if __name__ == "__main__":
    asyncio.run(main())