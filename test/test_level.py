import os
import glob

from level.level import Level

def test_level():
    for file in glob.glob('test/*.bin'):
        l = Level.read(file)
        l.write('test/test.bin')
        l.write('test/test2.bin')

        test = Level.read('test/test.bin')
        test2 = Level.read('test/test2.bin')
        assert l == test
        assert l == test2

    os.remove('test/test.bin')
    os.remove('test/test2.bin')