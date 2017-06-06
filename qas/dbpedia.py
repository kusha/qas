"""
DBpedia bindings.
"""

from urllib.parse import quote_plus
import urllib.request
import re

from qas.wikidata import get_json

RESOURCE_URI = "http://dbpedia.org/resource/{}"
ENTITY_URI = "http://dbpedia.org/data/{}.json"

SAME_AS = "http://www.w3.org/2002/07/owl#sameAs"
RESOURCE_REGEX = r'<a class=\"uri\" rel=\"owl:sameAs\" href=\"(http:\/\/www\.wikidata\.org\/entity\/Q.+)\">'


class InvalidDBpediaLink(Exception):
    pass


class DBpedia():
    """
    DBpedia trivial bindings.
    """
    @staticmethod
    def wd_from_link(dbpedia_link):
        """
        Transform DBpedia URI to Wikidata URI.
        """
        if not dbpedia_link.startswith('http://dbpedia.org/'):
            raise InvalidDBpediaLink()
        item_label = dbpedia_link.split('/')[-1]
        uri = ENTITY_URI.format(item_label)
        resource = RESOURCE_URI.format(item_label)
        encoded = quote_plus(uri, safe='/:')
        if uri == encoded:
            data = get_json(uri, {})
            if resource in data:
                data = data[resource]
                if SAME_AS in data:
                    data = data[SAME_AS]
                    for interlink in data:
                        if interlink['value'].startswith(
                                "http://www.wikidata.org/"):
                            return interlink['value']
        else:
            page = urllib.request.urlopen(quote_plus(dbpedia_link, safe='/:'))
            data = page.read().decode('utf-8')
            occurance = re.findall(RESOURCE_REGEX, data)
            if len(occurance):
                return occurance[0]
        return None
