from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.helpers import scan
from elasticsearch.exceptions import NotFoundError, RequestError

import json
import logging

from typing import Union, List, Dict


class ElasticIndex:
    """Represents a single Elastic Index on a host.

    Create one instance for each elasticsearch index you want to communicate with. Use wild-card index
    names to target multiple indexes at once.

    When initializing this will check if an index with the given name already exists. Otherwise
    a new index will be created.

    index:
        The name of the index. Wild-cards can be used to target multiple indexes.

    doc_type:
        The type of the document inside of this index.

    mapping:
        A mapping can be used to fix the data types of fields and control subfield generation. When no
        mapping is provided, one is dynamically generated by elasticsearch.

    settings:
        The settings for this index on the cluster. This is where analyzers & tokenizers can be added.

    url:
        The default url is http://localhost:9200. The url must be resolvable. If no port is given the default is 9200.

    timeout:
        Specify after how long the connection to the cluster should time out in seconds. Default is 300 seconds.

    replace:
        When True will replace an existing index, by deleting the old index. This is necessary when the mapping
        needs to be replaced.

    """

    def __init__(self, index, doc_type,
                 url='http://localhost:9200',
                 mapping=None,
                 settings=None,
                 timeout=300,
                 replace=False):
        self.instance = Elasticsearch([url], timeout=timeout)
        self.index = index
        self.mapping = mapping
        self.settings = settings
        if replace:
            self.instance.indices.delete(index)
        if not self.instance.indices.exists(index):
            self.create()
        self.doc_type = doc_type
        self.url = url
        self.timeout = timeout
        self.match_all = {"query": {"match_all": {}}}

    @staticmethod
    def _default_settings():
        return {
            'number_of_shards': 5,
            'number_of_replicas': 1,
            'auto_expand_replicas': True,
            'refresh_interval': '1s'

        }

    def create(self):
        """Create the corresponding index. Will overwrite existing indexes of the same name."""
        body = dict()
        if self.mapping is not None:
            body['mappings'] = self.mapping
        if self.settings is not None:
            body['settings'] = self.settings
        else:
            body['settings'] = self._default_settings()
        self.instance.indices.create(self.index, body)

    def delete(self):
        """Deletes this index from elasticsearch.

        IMPORTANT: This will delete all data. So use with caution!
        """
        self.instance.indices.delete(self.index)

    def search(self, query=None, size=100, unpack=True):
        """Search the index with a query.

        Can at most return 10'000 results from a search. If the search would yield more than 10'000 hits, only the first 10'000 are returned.
        The default number of hits returned is 100.
        """
        logging.info('Download all documents from index %s.', self.index)
        if query is None:
            query = self.match_all
        results = list()
        data = self.instance.search(index=self.index, doc_type=self.doc_type, body=query, size=size)
        if unpack:
            for items in data['hits']['hits']:
                if '_source' in items:
                    results.append(items['_source'])
                else:
                    results.append(items)
        else:
            results = data['hits']['hits']
        return results

    def scan_index(self, query: Union[Dict[str, str] | None] = None) -> List[Dict[str, str]]:
        """Scan the index with the query.

        Will return any number of results above 10'000. Important to note is, that
        all the data is loaded into memory at once and returned. This works only with small
        data sets. Use scroll otherwise which returns a generator to cycle through the resources
        in set chunks.

        :param query: The query used to scan the index. Default None will return the entire index.
        :returns list of dicts: The list of dictionaries contains all the documents without metadata.
        """
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

    def scroll(self, query=None, scroll='5m', size=100, unpack=True):
        """Scroll an index with the specified search query.

        Works as a generator. Will yield `size` results per iteration until all hits are returned.
        """
        query = self.match_all if query is None else query
        response = self.instance.search(index=self.index, doc_type=self.doc_type, body=query, size=size, scroll=scroll)
        while len(response['hits']['hits']) > 0:
            scroll_id = response['_scroll_id']
            logging.debug(response)
            if unpack:
                yield [source['_source'] if '_source' in source else source for source in response['hits']['hits']]
            else:
                yield response['hits']['hits']
            response = self.instance.scroll(scroll_id=scroll_id, scroll=scroll)

    def get(self, identifier):
        """Fetch document by _id.

        Returns None if it is not found. (Will log a warning if not found as well. Should not be used
        to search an id.)"""
        logging.info('Download document with id ' + str(identifier) + '.')
        try:
            record = self.instance.get(index=self.index, doc_type=self.doc_type, id=identifier)
            if '_source' in record:
                return record['_source']
            else:
                return record
        except NotFoundError:
            return None

    def index_into(self, document, id) -> bool:
        """Index a single document into the index."""
        try:
            self.instance.index(index=self.index, doc_type=self.doc_type, body=json.dumps(document, ensure_ascii=False), id=id)
        except RequestError as ex:
            logging.error(ex)
            return False
        else:
            return True

    def update(self, doc: dict, doc_id: str):
        """Partial update to a single document.

        Uses the Update API with the specified partial document.
        """
        body = {
            'doc': doc
        }
        self.instance.update(self.index, self.doc_type, doc_id, body=body)

    def script_update(self, script: str, params: Union[dict, None], doc_id: str):
        """Uses painless script to update a document."""
        body = {
            'script': {
                'source': script,
                'lang': 'painless'
            }
        }
        if params is not None:
            body['script']['params'] = params
        self.instance.update(self.index, self.doc_type, doc_id, body=body)

    def bulk(self, data: List[Dict[str, str]], identifier_key: str, op_type='index', upsert=False, keep_id_key=False) -> bool:
        """
        Takes a list of dictionaries and an identifier key and indexes everything into this index.

        :param data:            List of dictionaries containing the data to be indexed.
        :param identifier_key:  The name of the dictionary element which should be used as _id. This will be removed from
                                the body. Is ignored when None or empty string. This will cause elastic
                                to create their own _id.
        :param op_type:         What should be done: 'index', 'delete', 'update'.
        :param upsert:          The update op_type can be upserted, which will create a document if not already present.
        :param keep_id_key      Determines if the value designated as the identifier_key should be kept
                                as part of the document or removed from it.
        :returns                Returns True if all the messages were indexed without errors. False otherwise.
        """
        bulk_objects = []
        for document in data:
            bulk_object = dict()
            bulk_object['_op_type'] = op_type
            if identifier_key is not None and identifier_key != '':
                bulk_object['_id'] = document[identifier_key]
                if not keep_id_key:
                    document.pop(identifier_key)
                if bulk_object['_id'] == '':
                    bulk_object.pop('_id')
            if op_type == 'index':
                bulk_object['_source'] = document
            elif op_type == 'update':
                bulk_object['doc'] = document
                if upsert:
                    bulk_object['doc_as_upsert'] = True
            bulk_objects.append(bulk_object)
            logging.debug(str(bulk_object))
        logging.info('Start bulk index for ' + str(len(bulk_objects)) + ' objects.')
        errors = bulk(self.instance, actions=bulk_objects, index=self.index, doc_type=self.doc_type,
                      raise_on_error=False)
        logging.info(str(errors[0]) + ' documents were successfully indexed/updated/deleted.')
        if errors[0] - len(bulk_objects) != 0:
            logging.error(str(len(bulk_objects) - errors[0]) + ' documents could not be indexed/updated/deleted.')
            for error in errors[1]:
                logging.error(str(error))
            return False
        else:
            logging.debug('Finished bulk %s.', op_type)
            return True

    def reindex(self, new_index_name: str, identifier_key: str, **kwargs) -> 'ElasticIndex':
        """Reindex the entire index.

        Scrolls the old index and bulk indexes all data into the new index.

        :param new_index_name:
        :param identifier_key:
        :param kwargs:          Overwrite ElasticIndex __init__ params.
        :return:
        """
        if 'url' not in kwargs:
            kwargs['url'] = self.url
        if 'doc_type' not in kwargs:
            kwargs['doc_type'] = self.doc_type
        if 'mapping' not in kwargs:
            kwargs['mapping'] = self.mapping
        new_index = ElasticIndex(new_index_name, **kwargs)

        for results in self.scroll(size=500):
            new_index.bulk(results, identifier_key)
        return new_index

    def dump(self, path: str, file_name: str = "", **kwargs: dict):
        """
        Dumps the entire index into a json file. 

        :param path: The path to directory where the dump should be stored.
        :param file_name: Name of the file the dump should be stored in. If empty the index name is used.
        :param kwargs: Keyword arguments for the json converter. (ex. indent=4, ensure_ascii=False)
        """
        export = list()
        for results in self.scroll():
            export.extend(results)

        if not path.endswith('/'):
            path += '/'

        if file_name == '':
            file_name = self.index

        if not file_name.endswith('.json'):
            file_name += '.json'

        store = path + file_name
        with open(store, 'w') as fp:
            json.dump(export, fp, **kwargs)

        logging.info("Extracted %s records from the index %s and stored them in %s/%s.", len(export), self.index, path, file_name)
