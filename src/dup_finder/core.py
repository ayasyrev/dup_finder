from collections import defaultdict
from pathlib import Path
from typing import Optional

from .helpers import (PathOrStr, bytes_human, get_dirs_files, hash_file,
                      hash_header)


class File:

    _hash: str | None = None
    _head_hash: str | None = None

    def __init__(self, path: PathOrStr) -> None:
        self.path = Path(path)
        self.size = self.path.stat().st_size

    @property
    def hash(self) -> str:
        if self._hash is None:
            self._hash = hash_file(self.path)
        return self._hash

    @property
    def head_hash(self) -> str:
        if self._head_hash is None:
            self._head_hash = hash_header(self.path)
        return self._head_hash

    def __repr__(self) -> str:
        return f"{self.path} size: {bytes_human(self.size)}"


class FileList:

    _file_list: list[File]
    _head_hash_candidates: dict[str, set[int]] = {}
    dup_size_candidates: list[int] = []
    _dups: dict[str, set[int]] = defaultdict(set)
    _dups_keys: list[str] = []

    def __init__(
        self,
        path: PathOrStr,
        recursive: bool = True,
    ) -> None:
        _, files = get_dirs_files(path, recursive=recursive)
        self._file_list: list[File] = [File(item) for item in files]
        self._file_list.sort(key=lambda item: item.size, reverse=True)
        self.size_file: dict[int, set[int]] = defaultdict(set)
        self.size_all = 0
        for idx, file in enumerate(self._file_list):
            self.size_file[file.size].add(idx)
            self.size_all += file.size
        self.sizes = sorted(self.size_file.keys(), reverse=True)
        self.dup_size_candidates = [
            size for size in self.sizes if len(self.size_file[size]) > 1
        ]
        print(
            f"Total {self.len} files, {bytes_human(self.size_all)}, "
            f"max size {bytes_human(self.sizes[0])} "
            f"max candid {bytes_human(self.dup_size_candidates[0])} "
            f"{len(self.dup_size_candidates)} candidates"
        )

    def __getitem__(self, index: int) -> File:
        return self._file_list[index]

    def __len__(self) -> int:
        return len(self._file_list)

    @property
    def len(self) -> int:
        """Length of file list."""
        return len(self._file_list)

    def show_size_id(self, idx: int):
        for item in self.size_file[self.dup_size_candidates[idx]]:
            print(self._file_list[item])

    def show_size(self, size: int):
        for item in self.size_file[size]:
            print(self._file_list[item])

    def find_head_hash_candidates(self, idx: int | None = None):
        idx = idx or len(self.dup_size_candidates)
        head_hash_candidates: dict[str, set[int]] = defaultdict(set)
        for size in self.dup_size_candidates[:idx]:
            for item in self.size_file[size]:
                head_hash_candidates[self._file_list[item].head_hash].add(item)
        # check sizes for candidates list
        self._head_hash_candidates = {
            k: v for k, v in head_hash_candidates.items() if len(v) > 1
        }
        print(
            f"len of head_hash candidates: {len(self._head_hash_candidates)}"
        )

    def find_dups(self, idx: Optional[int] = None):
        if len(self._head_hash_candidates) == 0:
            print("No head hash candidates to find from...")
        idx = idx or len(self._head_hash_candidates)
        hash_dict: dict[str, set[int]] = defaultdict(set)
        for _head_hash, idx_list in self._head_hash_candidates.items():
            for item in idx_list:
                hash_dict[self._file_list[item].hash].add(item)
        self._dups = {k: v for k, v in hash_dict.items() if len(v) > 1}
        self._dups_keys = list(self._dups.keys())
        print(f"Len of dups dict: {len(self._dups)}")
        dups_size = bytes_human(
            sum(
                self._file_list[next(iter(idx_set))].size * (len(idx_set) - 1)
                for idx_set in self._dups.values()
            )
        )
        print(f"size of dups {dups_size}")

    def dup(self, idx: int):
        return [
            self._file_list[file_id]
            for file_id in self._dups[self._dups_keys[idx]]
        ]

    def dup_list(self, idx: int) -> list[list[File]]:
        res: list[list[File]] = []
        for item in self._dups_keys[:idx]:
            res.append(
                list(
                    self._file_list[file_id]
                    for file_id in self._dups[item]
                )
            )
        return res
