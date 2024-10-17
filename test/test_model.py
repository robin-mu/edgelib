import os
import glob

from model.model import ESO

def test_model():
    for file in glob.glob('test/*.eso'):
        model = ESO.read(file)
        model.write('test/test.eso')
        test = ESO.read('test/test.eso')
        assert model == test

    os.remove('test/test.eso')