import pathlib
from dup_finder.prepare_test_data import TEST_DATA_PATH, TEST_ROOT, PACKAGE_ROOT, LIB_ROOT

def test_path_names():
    assert type(TEST_ROOT) == pathlib.PosixPath
    assert type(TEST_DATA_PATH) == pathlib.PosixPath
    assert type(PACKAGE_ROOT) == pathlib.PosixPath
    assert type(LIB_ROOT) == pathlib.PosixPath