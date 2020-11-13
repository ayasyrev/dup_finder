import os
from pathlib import Path
from tests import PACKAGE_ROOT, TEST_DATA_PATH

def test_needsfiles():
    print('...tst')
    print(Path('.'))
    print(Path(os.curdir))
    assert Path(TEST_DATA_PATH).exists()
    assert os.path.isdir(PACKAGE_ROOT)