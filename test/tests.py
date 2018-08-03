from simple_elastic import ElasticIndex


class TestElasticIndex(object):

    def setup_class(self):
        self.index = ElasticIndex('test', 'document')
        self.index.index_into({'test': True}, 1)
        self.index.index_into({'test': False}, 2)
        self.index.index_into({'test': True}, 3)
        self.index.index_into({'test': False}, 4)

    def teardown_class(self):
        self.index.delete()

    def test_scroll(self):
        for i in self.index.scroll():
            assert isinstance(i, list)

    def test_index_into(self):
        self.index.index_into({'test': False}, 'HAN000827182')
