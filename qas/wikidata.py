"""
Wikidata bindings.
Python 3.6.1 with grequests causes an error.
"""

import json
import time


from gevent import monkey
def stub(*args, **kwargs):  # pylint: disable=unused-argument
    pass
monkey.patch_all = stub
monkey.patch_ssl()

import grequests
import requests


MATCHING_TIMEOUT = 10
MATCHING_LIMIT = 20
MATCHING_PARALLELS = 15

TIMEOUT_IGNORE = True

DEFAULT_SPARQL_TIMEOUT = 10
SPARQL_PARALLELS = 2
TOO_MANY_REQUESTS_TIMEOUT = 20
TIMEOUT_MULTIPLIER = 3.0


class NoSPARQLResponse(Exception):
    pass


def get_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.exceptions.ReadTimeout:
        # print("10 seconds timeout")
        raise NoSPARQLResponse()
    try:
        response = response.json()
    except json.decoder.JSONDecodeError:
        # print(response, elapsed)
        raise NoSPARQLResponse()
    return response


class WikidataItemsNotFound(Exception):
    pass


CACHE = {
    "wikidata_search_by_label": {}
}


class Wikidata():

    @staticmethod
    def search_by_label_parallel(queries, entity_type="item"):

        # no queries => empty response
        if len(queries) == 0:
            return {}
        # result json query -> data
        result = {}
        not_cached = []
        for query in queries:
            if query in CACHE['wikidata_search_by_label']:
                result[query] = CACHE['wikidata_search_by_label'][query]
            else:
                not_cached.append(query)
        # prepare requests data
        request_attrs = []
        for query in not_cached:
            # known bug in grequests, at Python 3.6
            url = "http://www.wikidata.org/w/api.php"
            # multipagigng search with "continue"
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "search": str(query),
                "language": "en",
                "type": entity_type,  # item, property
                "limit": MATCHING_LIMIT
            }
            timeout = MATCHING_TIMEOUT  # fixed for entity search
            request_attrs.append((url, params, timeout, ))
        # prepare asynchronious get objects
        requests_ = [grequests.get(url, params=params, timeout=timeout)
                     for url, params, timeout in request_attrs]

        # timeout handler
        def timeout_handler(request, exception):
            # skip timeout exceptions
            try:
                raise exception
            except requests.exceptions.ReadTimeout:
                pass
        responses = grequests.map(requests_,
                                  size=MATCHING_PARALLELS,
                                  exception_handler=timeout_handler)
        # parse JSON, extend dictionary
        for query, response in zip(not_cached, responses):
            # requests exception skip
            if response is None:
                result[query] = None
                continue
            try:
                data = response.json()
            except json.decoder.JSONDecodeError:
                # JSON decoding skip
                result[query] = None
            else:
                if len(data['search']) == 0:
                    # zero results skip
                    result[query] = None
                else:
                    result[query] = data['search']
                    CACHE['wikidata_search_by_label'][query] = data['search']
        return result

    @staticmethod
    def search_by_label(query, entity_type="item"):
        if query in CACHE['wikidata_search_by_label']:
            return CACHE['wikidata_search_by_label'][query]
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "search": str(query),
            "language": "en",
            "type": entity_type,  # item, property
            "limit": 50  # 500 as a bot
            #  imlement multipage search with "continue"
        }
        # print("test")
        response = get_json(url, params)
        # print("test2")
        if len(response['search']) == 0:
            raise WikidataItemsNotFound()
        # print('teeest')
        CACHE['wikidata_search_by_label'][query] = response['search']
        return response['search']

    @classmethod
    def sparql_parallel(cls, queries, timeout=None):
        print(len(queries), "parallel sparql queries")
        # no queries => empty response
        if len(queries) == 0:
            return {}, timeout
        # result json query -> data
        result = {}
        # prepare requests data
        request_attrs = []
        for query in queries:
            url = "https://query.wikidata.org/sparql"
            params = {
                "query": query,
                "format": "json"
            }
            if not TIMEOUT_IGNORE:
                timeout = DEFAULT_SPARQL_TIMEOUT if timeout is None else timeout
            else:
                timeout = DEFAULT_SPARQL_TIMEOUT
            request_attrs.append((url, params, timeout, ))
        # prepare asynchronious get objects
        requests_ = [grequests.get(url, params=params, timeout=timeout)
                     for url, params, timeout in request_attrs]

        # timeout handler
        def timeout_handler(request, exception):
            # skip timeout exceptions
            try:
                raise exception
            except requests.exceptions.ReadTimeout:
                pass
        responses = grequests.map(requests_,
                                  size=SPARQL_PARALLELS,
                                  exception_handler=timeout_handler)

        # check too many requests
        statuses = [r.status_code if r is not None else None
                    for r in responses]
        if 429 in statuses:
            time.sleep(TOO_MANY_REQUESTS_TIMEOUT)
            print("= too many requests timeout ({}s) =".format(
                TOO_MANY_REQUESTS_TIMEOUT))
            cls.sparql_parallel(queries,
                                timeout=(timeout * TIMEOUT_MULTIPLIER))

        # parse JSON, extend dictionary
        for query, response in zip(queries, responses):
            # requests exception skip
            if response is None:
                result[query] = None
                continue
            try:
                data = response.json()
            except json.decoder.JSONDecodeError:
                # JSON decoding skip
                result[query] = None
            else:
                result[query] = data

        # response time in case of not None
        elapsed_times = [response.elapsed.total_seconds()
                         for response in responses
                         if response is not None]
        if len(elapsed_times) == 0:
            avg_elapsed_time = timeout
        else:
            avg_elapsed_time = sum(elapsed_times)/float(len(elapsed_times))
        # return result and avg elapsed for timeout calculation
        return result, avg_elapsed_time

    @staticmethod
    def sparql(query):
        url = "https://query.wikidata.org/sparql"
        params = {
            "query": query,
            "format": "json"
        }
        response = get_json(url, params)
        return response
        # return response['entities']

    # parallel get_items ??
    @classmethod
    def get_items(cls, ids, entity_type="item"):
        url = "https://www.wikidata.org/w/api.php"
        if entity_type == "item":
            ids = [id_ for id_ in ids if id_.startswith('Q')]
        chunk_limit = 50
        if len(ids) > chunk_limit:
            print('Warning, too much ids per request, working by chunks')
            entities = {}
            for chunk in [ids[i:i + chunk_limit]
                          for i in range(0, len(ids), chunk_limit)]:
                entities.update(cls.get_items(chunk, entity_type))
            return entities
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": "|".join(ids),
            "language": "en"
        }
        response = get_json(url, params)
        # if len(response['search']) == 0:
        #     raise WikidataItemsNotFound()
        return response['entities']

    @classmethod
    def update_claims(cls, items):
        data = {}
        # def grouped(iterable, num):
        #     return zip(*[iter(iterable)]*num)
        offset = 0
        while offset < len(items):
            batch = items[offset:offset+50]
            update = Wikidata.get_items([item.item_id for item in batch])
            data.update(update)
            offset += 50
        for item in items:
            item.claims = cls.extract_claims(data[item.item_id])

    @staticmethod
    def extract_claims(response):
        result = {}
        for key, value in response["claims"].items():
            try:
                result[key] = [item["mainsnak"]["datavalue"]["value"]["id"]
                               for item in value
                               if item["mainsnak"]["datavalue"]["value"]["id"].startswith('Q')]
            except:
                # print("is not regular item: ", [item["mainsnak"]["datatype"] for item in value])
                pass
        return result

    @classmethod
    def get_label_by_uri(cls, uri):
        item_id = uri.split("/")[-1]
        data = cls.get_items([item_id])
        return data[item_id]['labels']['en']['value']
