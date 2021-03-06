# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_dup_finder.ipynb (unless otherwise specified).

__all__ = ['ls', 'ls_print']

# Cell
#hide
import datetime, hashlib, os, sys, time, shutil
from pathlib import Path
# from shutil import copyfile, copytree, move, rmtree

# Cell
ls = lambda x: list(x.iterdir())
Path.ls = ls
Path.lf = lambda x: [i for i in x.iterdir() if i.is_file()]
Path.ld = lambda x: [i for i in x.iterdir() if i.is_dir()]

# Cell
def ls_print(path):
    print(path)
    for i in os.scandir(path):
        print('|____', i.name)