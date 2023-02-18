from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Optional

from rich.progress import Progress

from .helpers import (PathOrStr, bytes_human, get_dirs_files, hash_file,
                      hash_header)


def count_items(dict_size_hash: dict[int, dict[str, list[int]]]) -> int:
    """Count items in dict"""
    return sum(
        len(idx_list)
        for size in dict_size_hash
        for idx_list in dict_size_hash[size].values()
    )


def count_size(dict_size_hash: dict[int, dict[str, list[int]]]) -> int:
    """Calculate size of elements"""
    return sum(
        len(idx_list) * size
        for size in dict_size_hash
        for idx_list in dict_size_hash[size].values()
    )


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

    file_list: list[File]

    def __init__(
        self,
        path: PathOrStr,
        recursive: bool = True,
    ) -> None:
        self.path = Path(path)
        _, files = get_dirs_files(path, recursive=recursive)
        self.file_list: list[File] = [File(item) for item in files]
        self.file_list.sort(key=lambda item: item.size, reverse=True)
        self.size2idx: dict[int, list[int]] = defaultdict(list)
        self.size_all = 0
        for idx, file in enumerate(self.file_list):
            self.size2idx[file.size].append(idx)
            self.size_all += file.size
        self.sizes: list[int] = sorted(self.size2idx.keys(), reverse=True)
        self._size_candidates: list[int] = []
        self._size_head_hash_candidates: dict[int, dict[str, list[int]]] = {}
        self._dups: dict[str, list[int]] = defaultdict(list)
        self._dups_hashes: list[str] = []
        self.size_candidates_other: dict[int, list[int]] = defaultdict(list)
        self.size_head_hash_candidates_other: dict[int, dict[str, list[int]]] = {}
        self.dups_other: dict[int, dict[str, list[int]]] = {}
        self.dups_sizes_other: list[int] = []
        self._common_sizes: list[int] = []
        print(self.__repr__())

    def __repr__(self) -> str:
        return (
            f"{self.path.name}: {self.len} files, {bytes_human(self.size_all)}, "
            f"max size {bytes_human(self.sizes[0])} "
        )

    def __getitem__(self, index: int) -> File:
        return self.file_list[index]

    def __len__(self) -> int:
        return len(self.file_list)

    @property
    def len(self) -> int:
        """Length of file list."""
        return len(self.file_list)

    def show_size(self, size: int) -> None:
        """print files with given size."""
        if size in self.size2idx:
            for item in self.size2idx[size]:
                print(self.file_list[item])
        else:
            print(f"no files with size: {size}")

    def check_sizes(self) -> None:
        self._size_candidates = [
            size for size in self.sizes if len(self.size2idx[size]) > 1
        ]
        if self._size_candidates:
            print(f"found {len(self._size_candidates)} size candidates.")
        else:
            print("No files with same sizes.")

    def find_dups_candidates(
        self,
        num: int | None = None,
        min_size: int = 1048576,
    ):
        """Find dups candidates limited by num or min size."""
        self.check_sizes()
        num = num or len(self._size_candidates)
        if self._size_candidates[-1] < min_size:
            sizes_to_check = [
                size
                for size in self._size_candidates[:num]
                if size >= min_size
            ]
        else:
            sizes_to_check = self._size_candidates[:num]
        self._size_head_hash_candidates = OrderedDict()
        num_files = sum(len(self.size2idx[size]) for size in sizes_to_check)
        with Progress(transient=True) as progress:
            task = progress.add_task("Files:", total=num_files)
            for size in sizes_to_check:
                hashes: dict[str, list[int]] = defaultdict(list)
                for idx in self.size2idx[size]:
                    hashes[self.file_list[idx].head_hash].append(idx)
                    progress.advance(task)
                hashes = {
                    hash_val: idx_list
                    for hash_val, idx_list in hashes.items()
                    if len(idx_list) > 1
                }
                if hashes:
                    self._size_head_hash_candidates[size] = hashes
        len_candid = count_items(self._size_head_hash_candidates)
        if len_candid:
            size_candid = count_size(self._size_head_hash_candidates)
            print(
                f"Found {len_candid} candidates. "
                f"Potential {bytes_human(size_candid)} dups."
            )
        else:
            print("No candidates.")

    def find_dups(
        self,
        num: int | None = None,
        min_size: int = 0,
        max_size: int | None = None,
    ):
        if len(self._size_head_hash_candidates) == 0:
            print("No head hash candidates to find from...")
        else:
            num = num or len(self._size_head_hash_candidates)
            size_list = list(self._size_head_hash_candidates.keys())[:num]
            if min_size or max_size is not None:
                max_size = max_size or size_list[0]
                size_list = [size for size in size_list if size > min_size and size < max_size]
            full_size_to_check = count_size(self._size_head_hash_candidates)
            num_files = count_items(self._size_head_hash_candidates)
            print(f"To hash: {bytes_human(full_size_to_check)} in {num_files} files.")
            hash_dict: dict[str, list[int]] = defaultdict(list)
            with Progress(transient=True) as progress:
                task = progress.add_task("Hashing", total=full_size_to_check)
                task_num_files = progress.add_task("files:", total=num_files)
                for size in size_list:
                    for idx_list in self._size_head_hash_candidates[size].values():
                        for idx in idx_list:
                            hash_dict[self.file_list[idx].hash].append(idx)
                            progress.advance(task, advance=self.file_list[idx].size)
                            progress.advance(task_num_files)

            self._dups = {k: v for k, v in hash_dict.items() if len(v) > 1}
            self._dups_hashes = list(self._dups.keys())
            print(f"Len of dups dict: {len(self._dups)}")
            dups_size = bytes_human(
                sum(  # expecting all same size
                    self.file_list[idx_list[0]].size * (len(idx_list) - 1)
                    for idx_list in self._dups.values()
                )
            )
            print(f"size of dups {dups_size}")

    def dup(self, idx: int = 0) -> list[File]:
        """return dups at indexed size"""
        return [
            self.file_list[file_idx]
            for file_idx in self._dups[self._dups_hashes[idx]]
        ]

    def dup_list(self, num: int | None = None) -> list[list[File]]:
        """return list of dups, if num - limited to num items"""
        num = num or len(self._dups_hashes)
        return [
            [self.file_list[idx] for idx in self._dups[hash_val]]
            for hash_val in self._dups_hashes[:num]
        ]

    def move_dups(self, dest: PathOrStr | None = None) -> None:
        """move duplicates to dest dir."""
        dest_path = dest or self.path / "dups" / self.path.name
        if not isinstance(dest_path, Path):
            dest_path = Path(dest_path)
        dest_path.mkdir(exist_ok=True, parents=True)
        print(f"Dest dir: {dest_path}")
        dups_list = self.dup_list()
        for pair in dups_list:
            pair.sort(key=lambda item: len(str(item.path)))  # sort by path length
            pair.pop(0)  # leave shortest
            for file in pair:
                new_name = dest_path / file.path.relative_to(self.path)
                new_name.parent.mkdir(exist_ok=True, parents=True)
                file.path.rename(new_name)

    def check_sizes_with(self, other: "FileList") -> None:
        """find files with same sizes at both dirs."""
        self._common_sizes = list(set(self.sizes).intersection(other.sizes))
        if self._common_sizes:
            print(
                f"{len(self._common_sizes)} intersections, "
                f"max size {bytes_human(next(iter(self._common_sizes)))}"
            )
        else:
            print("No intersections.")

    def find_dups_candidates_with(self, other: "FileList") -> None:
        """Check header hash for candidates"""
        if not self._common_sizes:
            self.check_sizes_with(other)
        if not self._common_sizes:
            print("No files with same sizes in both dirs.")
            return
        self.size_head_hash_candidates_other = OrderedDict()
        other.size_head_hash_candidates_other = OrderedDict()
        num_files_self = sum(
            len(self.size2idx[size])
            for size in self._common_sizes
        )
        num_files_out = sum(
            len(other.size2idx[size])
            for size in self._common_sizes
        )
        with Progress(transient=True) as progress:
            task_self = progress.add_task("self:", total=num_files_self)
            task_out = progress.add_task("other:", total=num_files_out)
            for size in self._common_sizes:
                head_hash: dict[str, list[int]] = defaultdict(list)
                head_hash_out: dict[str, list[int]] = defaultdict(list)
                for idx in self.size2idx[size]:
                    head_hash[self.file_list[idx].head_hash].append(idx)
                    progress.advance(task_self)
                for idx in other.size2idx[size]:
                    head_hash_out[other.file_list[idx].head_hash].append(idx)
                    progress.advance(task_out)
                hash_intersection = set(head_hash.keys()).intersection(head_hash_out.keys())
                if hash_intersection:
                    self.size_head_hash_candidates_other[size] = {
                        hash_val: head_hash[hash_val] for hash_val in hash_intersection
                    }
                    other.size_head_hash_candidates_other[size] = {
                        hash_val: head_hash_out[hash_val] for hash_val in hash_intersection
                    }
        if self.size_head_hash_candidates_other:
            num_inters = count_items(self.size_head_hash_candidates_other)
            size_inters = count_size(self.size_head_hash_candidates_other)
            num_inters_out = count_items(other.size_head_hash_candidates_other)
            size_inters_out = count_size(other.size_head_hash_candidates_other)
            print(f"intersect: {len(self.size_head_hash_candidates_other)}")
            print(f"{self.path.name}: {num_inters} files, {bytes_human(size_inters)}")
            print(f"{other.path.name}: {num_inters_out} files, {bytes_human(size_inters_out)}")
        else:
            print("No intersection.")

    def find_dups_with(self, other: "FileList", num: Optional[int] = None):
        """Check for duplicates"""
        if not self.size_head_hash_candidates_other:
            print("No candidates for find...")
        else:
            num = num or len(self.size_head_hash_candidates_other)
            size_list = list(self.size_head_hash_candidates_other)[:num]
            self_dict = {size: self.size_head_hash_candidates_other[size] for size in size_list}
            other_dict = {size: self.size_head_hash_candidates_other[size] for size in size_list}
            files_size_self = count_size(self_dict)
            files_size_other = count_size(other_dict)
            num_files_self = count_items(self_dict)
            num_files_other = count_items(other_dict)
            print(
                f"To hash:\n"
                f"{self.path.name}: {bytes_human(files_size_self)}, {num_files_self} files\n"
                f"{other.path.name}: {bytes_human(files_size_other)}, {num_files_other} files"
            )
            self.dups_other = {}
            other.dups_other = {}
            with Progress(transient=True) as progress:
                task_self_files = progress.add_task("self files", total=num_files_self)
                task_self_size = progress.add_task("self size", total=files_size_self)
                task_other_files = progress.add_task("other files", total=num_files_other)
                task_other_size = progress.add_task("other size", total=files_size_other)
                for size in size_list:
                    hash_dict: dict[str, list[int]] = defaultdict(list)
                    hash_dict_other: dict[str, list[int]] = defaultdict(list)
                    for hash_val, idx_list in self_dict[size].items():
                        for idx in idx_list:
                            hash_dict[self.file_list[idx].hash].append(idx)
                            progress.advance(task_self_files)
                            progress.advance(task_self_size, advance=self.file_list[idx].size)
                        for idx in other_dict[size][hash_val]:
                            hash_dict_other[other.file_list[idx].hash].append(idx)
                            progress.advance(task_other_files)
                            progress.advance(task_other_size, advance=other.file_list[idx].size)
                    intersection = set(hash_dict.keys()).intersection(hash_dict_other)
                    if intersection:
                        self.dups_other[size] = {
                            hash_val: hash_dict[hash_val]
                            for hash_val in intersection
                        }
                        other.dups_other[size] = {
                            hash_val: hash_dict_other[hash_val]
                            for hash_val in intersection
                        }
            if self.dups_other:
                num_pairs = sum(len(item) for item in self.dups_other.values())
                num_files_self = count_items(self.dups_other)
                files_size_self = count_size(self.dups_other)
                num_files_other = count_items(other.dups_other)
                files_size_other = count_size(other.dups_other)
                self.dups_sizes_other = list(self.dups_other.keys())
                other.dups_sizes_other = list(other.dups_other.keys())
                print(
                    f"Got {num_pairs} duplicates pairs.\n"
                    f"{self.path.name}: {num_files_self} files {bytes_human(files_size_self)}\n"
                    f"{other.path.name}: {num_files_other} files {bytes_human(files_size_other)}"
                )
            else:
                print("Didn't find any duplicates.")

    def dup_other(self, idx: int = 0) -> dict[str, list[File]]:
        return {
            hash_val: [
                self.file_list[file_id]
                for file_id in idx_list]
            for hash_val, idx_list in self.dups_other[self.dups_sizes_other[idx]].items()
        }

    def dup_list_other(self, idx: int | None) -> list[dict[str, list[File]]]:
        idx = idx or len(self.dups_sizes_other)
        return [
            self.dup_other(size_id)
            for size_id in range(idx)
        ]

    def move_dups_other(self, dest: PathOrStr | None = None):
        """Move duplicates to dest folder"""
        dest_path = dest or self.path.parent / "dups" / self.path.name
        if not isinstance(dest_path, Path):
            dest_path = Path(dest_path)
        dest_path.mkdir(exist_ok=True, parents=True)
        print(f"Dest dir: {dest_path}")
        for size in self.dups_sizes_other:
            for idx_list in self.dups_other[size].values():
                for idx in idx_list:
                    file_path = self.file_list[idx].path
                    new_name = dest_path / file_path.relative_to(self.path)
                    new_name.parent.mkdir(exist_ok=True, parents=True)
                    file_path.rename(new_name)
