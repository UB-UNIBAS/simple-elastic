from simple_elastic import ElasticIndex


class TestElasticIndex(object):

    def setup(self):
        self.index = ElasticIndex('test', 'document')
        self.index.index_into({'test': True}, 1)
        self.index.index_into({'test': False}, 2)
        self.index.index_into({'test': True}, 3)
        self.index.index_into({'test': False}, 4)

    def test_scroll(self):
        for i in self.index.scroll():
            assert isinstance(i, list)
