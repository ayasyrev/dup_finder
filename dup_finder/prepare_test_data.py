import os
from pathlib import Path
import shutil


LIB_ROOT = Path(os.path.realpath(os.path.dirname(__file__)))
PACKAGE_ROOT = Path(os.path.dirname(LIB_ROOT))
TEST_ROOT = PACKAGE_ROOT / 'tests'
TEST_DATA_PATH = PACKAGE_ROOT / 'test_data'


test_dir = TEST_DATA_PATH / 'test_dir'
test_dir_copy = Path(test_dir.name + '_copy')
# path for duplicats
test_dir_dups = TEST_DATA_PATH / 'test_dir_dups'

# Number of files, originals and subfolders
NUM_FILES = 10
NUM_ORIGIN = int(NUM_FILES * 0.8)
NUM_SUB_DIR = 2




def remove_test_data():
    shutil.rmtree(test_dir_dups, ignore_errors=True)



if __name__ == '__main__':
    pass
