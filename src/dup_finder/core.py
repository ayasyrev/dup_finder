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
        self.dup_size_candidates: list[int] = [
            size for size in self.sizes if len(self.size2idx[size]) > 1
        ]
        self._size_head_hash_candidates: dict[int, dict[str, list[int]]] = {}
        self._dups: dict[str, list[int]] = defaultdict(list)
        self._dups_hashes: list[str] = []
        self._out_size_candidates: dict[int, list[int]] = defaultdict(list)
        self._out_size_head_hash_candidates: dict[int, dict[str, list[int]]] = {}
        self._out_dups: dict[int, dict[str, list[int]]] = {}
        self._out_dups_sizes: list[int] = []
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

    # def show_size_id(self, idx: int):
    #     for item in self.size2idx[self.dup_size_candidates[idx]]:
    #         print(self.file_list[item])

    def show_size(self, size: int) -> None:
        """print files with given size."""
        if size in self.size2idx:
            for item in self.size2idx[size]:
                print(self.file_list[item])
        else:
            print(f"no files with size: {size}")

    def find_head_hash_candidates(
        self,
        num: int | None = None,
        min_size: int = 1048576,
    ):
        """Find dups candidates limited by num or min size."""
        num = num or len(self.dup_size_candidates)
        if self.dup_size_candidates[-1] < min_size:
            sizes_to_check = [
                size
                for size in self.dup_size_candidates[:num]
                if size >= min_size
            ]
        else:
            sizes_to_check = self.dup_size_candidates[:num]
        # head_hash_candidates: dict[str, set[int]] = defaultdict(set)
        self._size_head_hash_candidates = OrderedDict()
        num_files = sum(len(self.size2idx[size]) for size in sizes_to_check)
        # size_all = sum(len(self.size2idx[size]) * size for size in sizes_to_check)
        with Progress(transient=True) as progress:
            task = progress.add_task("Files:", total=num_files)
            # task_size = progress.add_task("Size:", total=size_all)
            for size in sizes_to_check:
                hashes: dict[str, list[int]] = defaultdict(list)
                for idx in self.size2idx[size]:
                    # head_hash_candidates[self.file_list[idx].head_hash].add(idx)
                    hashes[self.file_list[idx].head_hash].append(idx)
                    progress.advance(task)
                hashes = {
                    hash_val: idx_list
                    for hash_val, idx_list in hashes.items()
                    if len(idx_list) > 1
                }
                if hashes:
                    self._size_head_hash_candidates[size] = hashes
        # check sizes for candidates list
        # self._head_hash_candidates = {
        #     k: v for k, v in head_hash_candidates.items() if len(v) > 1
        # }
        len_candid = count_items(self._size_head_hash_candidates)
        # sum(
        #     len(idx_list)
        #     for hash_dict in self._size_head_hash_candidates.values()
        #     for idx_list in hash_dict.values()
        # )
        if len_candid:
            size_cand = count_size(self._size_head_hash_candidates)
            # size_cand = sum(
            #     len(idx_list) * (size - 1)
            #     for size, hash_dict in self._size_head_hash_candidates.items()
            #     for idx_list in hash_dict.values()
            # )
            print(
                f"len of head_hash candidates: {len_candid} "
                f"potential {bytes_human(size_cand)} dups."
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
            full_size_to_check = sum(
                self.file_list[idx].size
                for size in size_list
                for idx_list in self._size_head_hash_candidates[size].values()
                for idx in idx_list
            )
            num_files = sum(
                len(idx_list)
                for size in size_list
                for idx_list in self._size_head_hash_candidates[size].values()
            )
            print(f"To hash: {bytes_human(full_size_to_check)} in {num_files}")
            hash_dict: dict[str, list[int]] = defaultdict(list)
            with Progress(transient=True) as progress:
                task = progress.add_task("Hashing", total=full_size_to_check)
                task_num_files = progress.add_task("files:", total=num_files)
            # for _head_hash, idx_list in self._head_hash_candidates.items():
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
                sum(
                    self.file_list[idx_list[0]].size * (len(idx_list) - 1)  # expecting all same size
                    for idx_list in self._dups.values()
                )
            )
            print(f"size of dups {dups_size}")

    def dup(self, idx: int = 0) -> list[File]:
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

    def move_dups(self, dest: PathOrStr | None = None):
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

    def check_sizes(self, other: "FileList"):
        """find files with same sizes at both dirs."""
        self._common_sizes = list(set(self.sizes).intersection(other.sizes))
        if self._common_sizes:
            print(
                f"{len(self._common_sizes)} intersections, "
                f"max size {bytes_human(next(iter(self._common_sizes)))}"
            )

    def check_headers(self, other: "FileList"):
        self._out_size_head_hash_candidates = OrderedDict()
        other._out_size_head_hash_candidates = OrderedDict()
        # header_hash: dict[str, set[int]] = defaultdict(set)
        # header_hash_out: dict[str, set[int]] = defaultdict(set)
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
                    self._out_size_head_hash_candidates[size] = {
                        hash_val: head_hash[hash_val] for hash_val in hash_intersection
                    }
                    other._out_size_head_hash_candidates[size] = {
                        hash_val: head_hash_out[hash_val] for hash_val in hash_intersection
                    }
        if self._out_size_head_hash_candidates:
            num_inters = count_items(self._out_size_head_hash_candidates)
            size_inters = count_size(self._out_size_head_hash_candidates)
            num_inters_out = count_items(other._out_size_head_hash_candidates)
            size_inters_out = count_size(other._out_size_head_hash_candidates)
            print(f"intersect: {len(self._out_size_head_hash_candidates)}")
            print(f"{self.path.name}: {num_inters} files, {bytes_human(size_inters)}")
            print(f"{other.path.name}: {num_inters_out} files, {bytes_human(size_inters_out)}")
        else:
            print("No intersection.")

    def find_dups_with(self, other: "FileList", num: Optional[int] = None):
        if not self._out_size_head_hash_candidates:
            print("No candidates for find...")
        else:
            num = num or len(self._out_size_head_hash_candidates)
            # hash_list = list(self._out_size_head_hash_candidates)[:num]
            size_list = list(self._out_size_head_hash_candidates)[:num]
            self_dict = {size: self._out_size_head_hash_candidates[size] for size in size_list}
            other_dict = {size: self._out_size_head_hash_candidates[size] for size in size_list}
            # hash_dict: dict[str, set[int]] = defaultdict(set)
            # hash_dict_out: dict[str, set[int]] = defaultdict(set)
            files_size_self = count_size(self_dict)
            files_size_other = count_size(other_dict)
            num_files_self = count_items(self_dict)
            num_files_other = count_items(other_dict)
            print(
                f"To hash:\n{self.path.name}: {bytes_human(files_size_self)}, {num_files_self} files\n"
                f"{other.path.name}: {bytes_human(files_size_other)}, {num_files_other} files"
            )
            self._out_dups = {}
            other._out_dups = {}
            with Progress(transient=True) as progress:
                task_self_files = progress.add_task("self files", total=num_files_self)
                task_self_size = progress.add_task("self size", total=files_size_self)
                task_other_files = progress.add_task("other files", total=num_files_other)
                task_other_size = progress.add_task("other", total=files_size_other)
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
                        self._out_dups[size] = {
                            hash_val: hash_dict[hash_val]
                            for hash_val in intersection
                        }
                        other._out_dups[size] = {
                            hash_val: hash_dict_other[hash_val]
                            for hash_val in intersection
                        }
            if self._out_dups:
                num_pairs = sum(len(item) for item in self._out_dups.values())
                num_files_self = count_items(self._out_dups)
                files_size_self = count_size(self._out_dups)
                num_files_other = count_items(other._out_dups)
                files_size_other = count_size(other._out_dups)
                self._out_dups_sizes = list(self._out_dups.keys())
                other._out_dups_sizes = list(other._out_dups.keys())
                print(
                    f"Got {num_pairs} duplicates pairs.\n"
                    f"{self.path.name}: {num_files_self} files {bytes_human(files_size_self)}\n"
                    f"{other.path.name}: {num_files_other} files {bytes_human(files_size_other)}"
                )
            else:
                print("Didn't find any duplicates.")

    def out_dup(self, idx: int = 0) -> dict[str, list[File]]:
        return {
            hash_val: [
                self.file_list[file_id]
                for file_id in idx_list]
            for hash_val, idx_list in self._out_dups[self._out_dups_sizes[idx]].items()
        }

    def out_dup_list(self, idx: int | None) -> list[dict[str, list[File]]]:
        idx = idx or len(self._out_dups_sizes)
        return [
            self.out_dup(size_id)
            for size_id in range(idx)
        ]

    def move_out_dups(self, dest: PathOrStr | None = None):
        """Move duplicates to dest folder"""
        dest_path = dest or self.path.parent / "dups" / self.path.name
        if not isinstance(dest_path, Path):
            dest_path = Path(dest_path)
        dest_path.mkdir(exist_ok=True, parents=True)
        print(f"Dest dir: {dest_path}")
        for size in self._out_dups_sizes:
            for idx_list in self._out_dups[size].values():
                for idx in idx_list:
                    file_path = self.file_list[idx].path
                    new_name = dest_path / file_path.relative_to(self.path)
                    new_name.parent.mkdir(exist_ok=True, parents=True)
                    file_path.rename(new_name)
