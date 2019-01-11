from simple_elastic import ElasticIndex

import sys
import logging


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class TestElasticIndex(object):

    def setup_class(self):
        self.index = ElasticIndex('test', 'document')

    def teardown_class(self):
        self.index.delete()

    def test_scroll(self):
        self.index.index_into({'test': True}, 1)
        self.index.index_into({'test': False}, 2)
        self.index.index_into({'test': True}, 3)
        self.index.index_into({'test': False}, 4)
        for i in self.index.scroll():
            assert isinstance(i, list)

    def test_index_into(self):

        result = self.index.index_into({'test': True, 'object': "This is a string"}, 5)
        assert result == True
        result = self.index.index_into({'test': True, 'object': {'sub-object': "another string"}}, 6)
        assert result == False
        result = self.index.index_into({'test': False}, 'HAN000827182')
        assert result == True

    
