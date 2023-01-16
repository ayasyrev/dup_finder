from pathlib import Path
from typing import Optional, Union
from .helpers import PathOrStr, bytes_human, hash_file, get_dirs_files, hash_header


class File:

    _hash: str | None = None
    _head_hash: str | None = None

    def __init__(self, path: PathOrStr) -> None:
        self.path = Path(path)
        self.size = self.path.stat().st_size

    @property
    def hash(self):
        if self._hash is None:
            self._hash = hash_file(self.path)
        return self._hash

    @property
    def head_hash(self):
        if self._head_hash is None:
            self._head_hash = hash_header(self.path)
        return self._head_hash

    def __eq__(self, file: "File") -> bool:
        return self.path.name == file.path.name and self.size == file.size

    def __repr__(self) -> str:
        return f"{self.path} size: {bytes_human(self.size)}"


def append2item(dict2app: dict[Union[str, int], list[int]], key: Union[str, int], value: int) -> None:
    if key in dict2app:
        if value not in dict2app[key]:
            dict2app[key].append(value)
    else:
        dict2app[key] = [value]


class FileList:

    _file_list: list[File]
    _head_hash_candidates: dict[str, list[int]] = {}
    dup_size_candidates: list[int] = []
    dups: dict[str, list[int]] = {}

    def __init__(
        self,
        path: PathOrStr,
        recursive: bool = True,
    ) -> None:
        _, files = get_dirs_files(path, recursive=recursive)
        self._file_list: list[File] = [File(item) for item in files]
        self._file_list.sort(key=lambda item: item.size, reverse=True)
        self.size_file: dict[int, list[int]] = {}
        for idx, file in enumerate(self._file_list):
            append2item(self.size_file, file.size, idx)
        self.sizes = sorted(self.size_file.keys(), reverse=True)
        self.dup_size_candidates = [size for size in self.sizes if len(self.size_file[size]) > 1]

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
        for size in self.dup_size_candidates[:idx]:
            for item in self.size_file[size]:
                append2item(self._head_hash_candidates, self._file_list[item].head_hash, item)
        # check sizes for candidates list
        self._head_hash_candidates = {k: v for k, v in self._head_hash_candidates.items() if len(v) > 1}
        print(f"len of head_hash candidates: {len(self._head_hash_candidates)}")

    def find_dups(self, idx: Optional[int] = None):
        if len(self._head_hash_candidates) == 0:
            print("No head hash candidates to find from...")
        idx = idx or len(self._head_hash_candidates)
        hash_dict: dict[str, list[int]] = {}
        for _head_hash, idx_list in self._head_hash_candidates.items():
            for item in idx_list:
                append2item(hash_dict, self._file_list[item].hash, item)
        self.dups = {k: v for k, v in hash_dict.items() if len(v) > 1}
        print(f"Len of dups dict: {len(self.dups)}")
