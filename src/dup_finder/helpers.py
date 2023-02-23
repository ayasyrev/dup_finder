import hashlib
import os

from pathlib import Path, PosixPath
from typing import Callable, List, Union


PathOrStr = Union[Path, str, os.DirEntry[str]]
ListDirEntry = List[os.DirEntry[str]]


def ls(path: PathOrStr) -> List[str]:
    """Return directory contetnt as list."""
    return [item.name for item in os.scandir(path)]


def lf(path: PathOrStr) -> List[str]:
    """Return list of files in directory."""
    return [item.name for item in os.scandir(path) if item.is_file()]


def ld(path: Union[str, PosixPath]) -> List[str]:
    """Return list of directory's in directory."""
    return [item.name for item in os.scandir(path) if item.is_dir()]


def _get_dirs_files(path: PathOrStr) -> tuple[ListDirEntry, ListDirEntry]:
    d_f: dict[bool, ListDirEntry] = {True: [], False: []}
    for dir_entry in os.scandir(path):
        try:
            d_f[dir_entry.is_dir()].append(dir_entry)
        except:
            pass
    return d_f[True], d_f[False]


def get_dirs_files(
    path: PathOrStr,
    recursive: bool = False,
) -> tuple[ListDirEntry, ListDirEntry]:
    """return list of dirs and list of files, option - recursive"""
    dirs, files = _get_dirs_files(path)
    if recursive:
        for dir_name in dirs.copy():
            ds, fs = get_dirs_files(dir_name, recursive=True)
            dirs.extend(ds)
            files.extend(fs)
    return dirs, files


def bytes_human(size: int) -> str:
    "Return human readable memory size. Limited to terrabytes."
    f_size = float(size)
    for symbol in ["B", "Kb", "Mb", "Gb", "Tb"]:
        if abs(f_size) < 1024.0:
            return f"{f_size:3.2f}{symbol}"
        f_size /= 1024.0
    return f"{f_size * 1024:.2f}Tb"


BUF_SIZE = 65536
HEADER_SIZE = 32768  # may be 16384


def hash_file(
    filename: PathOrStr,
    hash_func: Callable = hashlib.md5,
    buf_size: int = BUF_SIZE,
) -> str:
    result = hash_func()
    with open(filename, "rb") as file:
        while True:
            data = file.read(buf_size)
            if data:
                result.update(data)
            else:
                return result.hexdigest()


def hash_header(
    filename: PathOrStr,
    hash_func: Callable = hashlib.md5,
    header_size: int = HEADER_SIZE,
) -> str:
    result = hash_func()
    with open(filename, "rb") as file:
        data = file.read(header_size)
    result.update(data)
    return result.hexdigest()
