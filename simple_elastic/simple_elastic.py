from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.helpers import scan
from elasticsearch.exceptions import NotFoundError

import json
import logging


class ElasticIndex:

    def __init__(self, index, doc_type, mapping=None, settings=None, url='http://localhost:9200', timeout=300):
        self.instance = Elasticsearch([url], timeout=timeout)
        self.index = index
        self.mapping = mapping
        self.settings = settings

        if not self.instance.indices.exists(index):
            self.create()
        self.doc_type = doc_type
        self.url = url
        self.timeout = timeout
        self.match_all = {"query": {"match_all": {}}}

    @staticmethod
    def _default_settings():
        return {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'auto_expand_replicas': False,
            'refresh_interval': '1s'

        }

    def create(self):
        """Create this index."""
        body = dict()
        if self.mapping is not None:
            body['mappings'] = self.mapping
        if self.settings is not None:
            body['settings'] = self.settings
        else:
            body['settings'] = self._default_settings()
        self.instance.indices.create(self.index, )

    def delete(self):
        """Delete this index."""
        self.instance.indices.delete(self.index)

    def search(self, query=None, size=100):
        """Search the index with a query. Can fetch at most 10'000 items. Use scan_index if more are needed."""
        logging.info('Download all documents from index %s.', self.index)
        if query is None:
            query = self.match_all
        results = list()
        data = self.instance.search(index=self.index, doc_type=self.doc_type, body=query, size=size)
        for items in data['hits']['hits']:
            if '_source' in items:
                results.append(items['_source'])
            else:
                results.append(items)
        return results

    def scan_index(self, query=None):
        """Scans the entire index end returns each result as a list."""
        if query is None:
            query = self.match_all
        logging.info('Download all documents from index %s with query %s.', self.index, query)
        results = list()
        data = scan(self.instance, index=self.index, doc_type=self.doc_type, query=query)
        for items in data:
            if '_source' in items:
                results.append(items['_source'])
            else:
                results.append(items)
        return results

    def scroll(self, query=None, scroll='5m', size=100):
        """Scroll an index with the specified search query."""
        query = self.match_all if query is None else query
        response = self.instance.search(index=self.index, doc_type=self.doc_type, body=query, size=size, scroll=scroll)
        while len(response['hits']['hits']) > 0:
            scroll_id = response['_scroll_id']
            yield [source['_source'] if '_source' in source else source for source in response['hits']['hits']]
            response = self.instance.scroll(scroll_id=scroll_id, scroll=scroll)

    def get(self, identifier):
        """Get a single document with an id. Returns None if it is not found."""
        logging.info('Download document with id ' + str(identifier) + '.')
        try:
            record = self.instance.get(index=self.index, doc_type=self.doc_type, id=identifier)
            if '_source' in record:
                return record['_source']
            else:
                return record
        except NotFoundError:
            return None

    def index_into(self, document, id):
        """Index a single document into the index."""
        self.instance.index(index=self.index, doc_type=self.doc_type, body=json.dumps(document, ensure_ascii=False), id=id)

    def bulk(self, data: list, identifier_key: str, op_type='index'):
        """
        Takes a list of dictionaries and an identifier key and indexes everything into this index.

        :param data:            List of dictionaries containing the data to be indexed.
        :param identifier_key:  The name of the dictionary element which should be used as _id.
        :param op_type:         What should be done: 'index', 'delete', 'update'.
        """
        bulk_objects = []
        for document in data:
            bulk_object = dict()
            bulk_object['_op_type'] = op_type
            bulk_object['_id'] = document[identifier_key]
            if op_type == 'index':
                bulk_object['_source'] = document
            elif op_type == 'update':
                bulk_object['doc'] = document
            bulk_objects.append(bulk_object)
            logging.debug(str(bulk_object))
        logging.info('Start bulk index for ' + str(len(bulk_objects)) + ' objects.')
        errors = bulk(self.instance, actions=bulk_objects, index=self.index, doc_type=self.doc_type, raise_on_error=False)
        logging.info(str(errors[0]) + ' documents were successfully indexed/updated/deleted.')
        if errors[0] - len(bulk_objects) != 0:
            logging.error(str(errors[0] - len(bulk_objects)) + ' documents could not be indexed/updated/deleted.')
            for error in errors[1]:
                logging.error(str(error))
        logging.debug('Finished bulk %s.', op_type)

    def reindex(self, new_index_name: str, identifier_key: str, **kwargs):
        """

        :param new_index_name:
        :param identifier_key:
        :return:
        """
        data = self.scan_index()
        if 'url' not in kwargs:
            kwargs['url'] = self.url
        new_index = ElasticIndex(new_index_name, doc_type=self.doc_type, timeout=self.timeout, **kwargs)
        new_index.bulk(data, identifier_key)
        return new_index
