"""
Graph exploration module.
"""

import itertools
import time

from qas.wikidata import Wikidata, NoSPARQLResponse

MAX_PATH_LENGTH = 5
DISABLE_PARALLEL = True
RETRY_PARALLEL_SPARQL = False


class Path(object):
    def __init__(self, path, config, item_from, item_to):
        self.length = len(path) // 2 + 1
        # filter statements to calculate length
        for element in path:
            if element.startswith('http://www.wikidata.org/entity/statement/'):
                self.length -= 1
        self.path = path
        self.config = config
        self.item_from = item_from
        self.item_to = item_to

    def __str__(self):
        if self.item_from is not None:
            text_from = "[{}]".format(self.item_from.wikidata_item.item_id)
        else:
            text_from = "[__]"
        if self.item_to is not None:
            text_to = "[{}]".format(self.item_to.wikidata_item.item_id)
        else:
            text_to = "[__]"
        nodes = []
        for idx, node in enumerate(self.path):
            if idx % 2 == 0:  # property
                prop_direction = self.config[int(idx/2)]
                if prop_direction == 0:
                    nodes.append("= {} =>".format(node))
                else:
                    nodes.append("<= {} =".format(node))
            else:  # item
                nodes.append("{}".format(node))
        nodes.insert(0, text_from)
        nodes.append(text_to)
        return "@{} ".format(self.length) + " ".join(nodes)

    def is_symetric(self):
        return len(set(self.path)) != len(self.path)

    def is_pp(self):
        item_types = [item[0] for item in self.path]
        for idx in range(1, len(item_types)):
            if item_types[idx] == item_types[idx-1] == "P":
                return True
        return False

    def is_similar(self, other):
        for item_a, item_b in zip(self.path, other.path):
            if item_a == item_b:
                return True
        return False

    def similatiy_to_others(self, others):
        similatiy = [0] * (len(self.path) // 2 + 1)
        for other in others:
            for idx, item_a, item_b in zip(range(len(self.path)),
                                           self.path,
                                           other.path):
                if idx % 2 == 0:
                    pos = idx // 2
                    if item_a == item_b:
                        similatiy[pos] += 1
        return similatiy

    @property
    def items(self):
        return [element
                for element in self.path
                if element.startswith('Q')]

    def construct_sparql(self):
        # print(self.path)
        path_wo_statements = [(idx, element)
                              for (idx, element) in enumerate(self.path)
                              if element.startswith('Q') or
                              element.startswith('P')]
        # print(path_wo_statements)
        triples = ""
        from_item = None
        to_item = None
        for real_idx, (idx, node) in enumerate(path_wo_statements):
            if idx % 2 == 0:  # property
                prop_direction = self.config[int(idx/2)]
                item_before = "?item{}".format(real_idx)
                if from_item is None:
                    from_item = item_before
                item_after = "?item{}".format(real_idx+2)
                to_item = item_after
                template = "{} wdt:{} {} .\n"
                triples += template.format(
                    item_before if prop_direction == 0 else item_after,
                    node,
                    item_after if prop_direction == 0 else item_before,
                    )
        return from_item, to_item, triples

    def substitutes(self, strict=False):
        if strict:
            from_item, to_item, triples = self.construct_sparql_strict()
        else:
            from_item, to_item, triples = self.construct_sparql()
        template = """
        SELECT  {} {}Label {} {}Label WHERE {{
            {}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }} LIMIT 500
        """
        query = template.format(from_item,
                                from_item,
                                to_item,
                                to_item,
                                triples)
        # print(query)
        try:
            response = Wikidata.sparql(query)
        except NoSPARQLResponse:
            return None, []
        count = len(response['results']['bindings'])
        substitutes = []
        for path in response['results']['bindings']:
            question = path[from_item[1:]+'Label']['value']
            answer = path[to_item[1:]+'Label']['value']
            substitutes.append((question, answer, ))
        return count, substitutes

    def apply_path(self, from_item):
        from_item = "wd:{}".format(from_item)
        _, to_item, triples = self.construct_sparql()
        template = """
        SELECT {} {}Label WHERE {{
            {}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }} LIMIT 5
        """
        query = template.format(to_item,
                                to_item,
                                triples)
        query = query.replace("?item0", from_item)
        # print(query)
        try:
            response = Wikidata.sparql(query)
        except NoSPARQLResponse:
            return None, []
        count = len(response['results']['bindings'])
        answers = []
        for path in response['results']['bindings']:
            answer = path[to_item[1:]+'Label']['value']
            answers.append(answer)
        return count, answers

    def construct_sparql_strict(self):
        # print(self.path)
        path_wo_statements = [(idx, element)
                              for (idx, element) in enumerate(self.path)
                              if element.startswith('Q') or
                              element.startswith('P')]
        # print(path_wo_statements)
        triples = ""
        from_item = "?from"
        to_item = "?to"
        for real_idx, (idx, node) in enumerate(path_wo_statements):
            if idx % 2 == 0:  # property
                prop_direction = self.config[int(idx/2)]
                if (real_idx - 1) == -1:
                    item_before = from_item
                else:
                    item_before = "wd:{}".format(
                        path_wo_statements[real_idx-1][1])
                if (real_idx + 1) == len(path_wo_statements):
                    item_after = to_item
                else:
                    item_after = "wd:{}".format(
                        path_wo_statements[real_idx+1][1])
                template = "{} wdt:{} {} .\n"
                triples += template.format(
                    item_before if prop_direction == 0 else item_after,
                    node,
                    item_after if prop_direction == 0 else item_before,
                    )
        return from_item, to_item, triples

    def pp_links(self):
        result = "-----------------\n"
        result += " Links to items: \n"
        result += "-----------------\n"
        for element in self.path:
            if element.startswith('Q'):
                result += "https://www.wikidata.org/wiki/{}".format(
                    element) + '\n'
            elif element.startswith('P'):
                result += "https://www.wikidata.org/wiki/Property:{}".format(
                    element) + '\n'
            else:
                result += element + '\n'
        return result[:-1]


class Graph():
    def __init__(self, labeled_enitites):
        self.entities = {}
        for label, entity in labeled_enitites:
            if label not in self.entities:
                self.entities[label] = []
            # filter entities without assigned items (too filtered)
            if len(entity.items):
                self.entities[label].append(entity)

    def construct_query(self, config, item_from, item_to):
        length = len(config)
        select = []
        for idx in range(1, length+1):
            select.append("?prop{}".format(idx))
            if idx != len(config):
                select.append("?item{}".format(idx+1))
        select = " ".join(select)
        # print(select)
        statement = ""
        for idx in range(1, length+1):
            subject = "?item{}".format(idx)
            predicate = "?prop{}".format(idx)
            object_ = "?item{}".format(idx+1)
            if idx == 1:
                subject = "wd:{}".format(item_from.wikidata_item.item_id)
            if idx == length:
                object_ = "wd:{}".format(item_to.wikidata_item.item_id)
            line = "{} {} {}.\n"
            if config[idx-1] == 0:
                statement += line.format(subject, predicate, object_)
            else:
                statement += line.format(object_, predicate, subject)
        # print(statement)
        filters = ""
        for idx, element in enumerate(select.split(" ")):
            startswith = 'http://www.wikidata.org/prop/' \
                         if (idx % 2) == 0 else \
                         'http://www.wikidata.org/entity/'
            filter_template = 'FILTER ( strstarts(str({}), "{}") )\n'
            filters += filter_template.format(element, startswith)
        # TODO: Filters
        query = 'SELECT {}\nWHERE {{\n{}\n{}\nSERVICE wikibase:label {{ bd:serviceParam wikibase:language "en"}}\n}}'
        return query.format(select, statement, filters)

    @staticmethod
    def process_response(response):
        if len(response['results']['bindings']) == 0:
            return []
        fields = response['head']['vars']
        pathes = []
        for result in response['results']['bindings']:
            path = []
            for field in fields:
                item = result[field]['value']
                # .split('/')[-1]
                if item.startswith('http://www.wikidata.org/prop/') and \
                   not item.startswith('http://www.wikidata.org/prop/statement/'):
                    item = item.split('/')[-1]
                if item.startswith('http://www.wikidata.org/entity/') and \
                   not item.startswith('http://www.wikidata.org/entity/statement/'):
                    item = item.split('/')[-1]
                path.append(item)
            pathes.append(path)
        return pathes

    @staticmethod
    def filter_pathes(pathes):
        pathes = [path
                  for path in pathes
                  if not path.is_symetric()]
        if len([path
               for path in pathes
               if path.is_symetric()]):
            print("FILTERED SYMMETRICAL:",
                  [path
                   for path in pathes
                   if path.is_symetric()])
        pathes = [path
                  for path in pathes
                  if not path.is_pp()]
        return pathes

    @staticmethod
    def extract_shared(solutions):
        items = {}
        for key, pathes in solutions.items():
            items[key] = []
            for path in pathes:
                items[key] += path.items
            items[key] = list(set(items[key]))
        print(items)
        score = {}
        for key1, value1 in items.items():
            for key2, value2 in items.items():
                if key1 != key2:
                    for item1 in value1:
                        if item1 not in score:
                            score[item1] = 0
                        for item2 in value2:
                            if item1 == item2:
                                score[item1] += 1
        print(score)
        results = list(score.items())
        if len(results) == 0:
            return results
        max_score = max([result[1] for result in results])
        results = [result
                   for result in results
                   if result[1] == max_score]
        return results


    @staticmethod
    def get_directions(length):
        list(itertools.product(range(2), repeat=3))

    def skip_direction(self, path_length, direction):
        # if solution for direction is found
        # skip this direction at length more than
        # min length + 1 (to include deductive)
        if frozenset(direction) in self.solutions:
            pathes = self.solutions[frozenset(direction)]
            min_length = min([path.length for path in pathes])
            if path_length <= (min_length + 1):
                print("Solution found, last level attempt.")
                return False  # do NOT skip
            else:
                print("Solution found. {} -> {}".format(
                    direction[0], direction[1]))
                return True

    def items_comb(self, direction):
        # create sets of items
        set_from = []
        for entity in self.entities[direction[0]]:
            set_from += entity.items
        set_to = []
        for entity in self.entities[direction[1]]:
            set_to += entity.items
        # for each possible direction between items
        return list(itertools.product(set_from, set_to))

    @staticmethod
    def dir_comb(path_length):
        return list(itertools.product(range(2), repeat=path_length))

    @staticmethod
    def pp_link_config(link_config):
        result = "{ "
        for direction in link_config:
            if direction == 0:
                result += "-> "
            else:
                result += "<- "
        return result + "}"

    def path_comb(self, direction, path_length):
        return zip(self.items_comb(direction), self.dir_comb(path_length))

    def connect(self, *labels, interrupt="first"):

        print("==== CONNECTION OVER GRAPH ====")

        # directions of search
        # for a basic example: [['question', 'answer']]
        directions = [list(pair)
                      for pair in itertools.combinations(labels, 2)]

        # dictionary for final solutions
        # frozenset is a key, path is a value
        self.solutions = {}

        timeout = None
        # for path length until maximum
        path_length_at_times = []
        for path_length in range(1, MAX_PATH_LENGTH):
            # save processing time measure
            path_length_at_times.append(time.time())

            if timeout is not None:
                timeout = (timeout + 5.0) ** 2

            # optimization step, async SPARQL querying
            if not DISABLE_PARALLEL:
                sparql_queries = []
                for direction in directions:
                    if self.skip_direction(path_length, direction):
                        continue
                    for (item_from, item_to), link_config in \
                            self.path_comb(direction, path_length):
                        query = self.construct_query(link_config,
                                                     item_from,
                                                     item_to)
                        sparql_queries.append(query)
                print("Timeout for path length", path_length, ":", timeout)
                sparql_responses, timeout = Wikidata.sparql_parallel(
                    sparql_queries,
                    timeout=timeout)
                print("Elapsed at path length", path_length, ":", timeout)
            else:
                # print("parallel querying is disabled")
                sparql_responses, timeout = {}, None

            # for direction between labels (question -> answer)
            for direction in directions:
                print("Length: {}, Labels: {} -> {}:".format(
                    path_length, direction[0], direction[1]))

                if self.skip_direction(path_length, direction):
                    continue

                pathes_at_length = []

                for (item_from, item_to), link_config in \
                        self.path_comb(direction, path_length):
                    query = self.construct_query(link_config, item_from, item_to)
                    response = None
                    # use preloaded parallel results
                    if query in sparql_responses:
                        response = sparql_responses[query]
                        if response is None:
                            if RETRY_PARALLEL_SPARQL or DISABLE_PARALLEL:
                                try:
                                    response = Wikidata.sparql(query)
                                except NoSPARQLResponse:
                                    print("RTRETIME @",
                                          self.pp_link_config(link_config))
                                    continue
                            else:
                                print("PARNONE @",
                                      self.pp_link_config(link_config))
                                continue
                    else:
                        try:
                            response = Wikidata.sparql(query)
                        except NoSPARQLResponse:
                            print("TIMEOUT @",
                                  self.pp_link_config(link_config))
                            continue
                    pathes = self.process_response(response)
                    pathes = [Path(path, link_config, item_from, item_to)
                              for path in pathes]
                    pathes = self.filter_pathes(pathes)
                    if len(pathes) == 0:
                        print("NO_CONN @",
                              self.pp_link_config(link_config))
                        continue
                    print("SUCCESS @",
                          self.pp_link_config(link_config))
                    if len(pathes) <= 3:
                        for path in pathes:
                            print(path)
                    else:
                        print("[ ... {} paths found ... ]".format(
                            len(pathes)))
                    pathes_at_length += pathes
                if len(pathes_at_length):
                    if frozenset(direction) in self.solutions:
                        self.solutions[frozenset(direction)] += pathes_at_length
                    else:
                        self.solutions[frozenset(direction)] = pathes_at_length
        # print processing time info
        path_length_at_times.append(time.time())
        print("-" * 20)
        for idx, timestamp in list(enumerate(path_length_at_times))[1:]:
            processing_time = timestamp - path_length_at_times[idx-1]
            print('TIME AT LENGTH {}: {:.4f}'.format(idx, processing_time, ))

        for direction, pathes in self.solutions.items():
            # print(direction)
            min_length = min([path.length for path in pathes])
            pathes = [path
                      for path in pathes
                      if path.length == min_length]
            # pathes = sorted(pathes, key=lambda x: x.length)
            # for path in pathes:
            #     print(path)
        # print(self.solutions)
        return self.solutions
        # print("==== RESULTS ====")
        # results = self.extract_shared(solutions)
        # print(results)

        # for query_length in range(6):
        #     for 
        # res = Wikidata.sparql(query)
        # print(res)

    @staticmethod
    def evaluate_solutions(solutions):
        k = 3

        pathes = []
        for _, solution_pathes in solutions.items():
            pathes += solution_pathes
        directions = []
        for path in pathes:
            directions.append((path.item_from.wikidata_item.item_id,
                               path.item_to.wikidata_item.item_id, ))
        directions = list(set(directions))  # unique directions

        evaluated_pathes = []
        for direction in directions:
            item_from, item_to = direction
            pathes_for_direction = \
                [path
                 for path in pathes
                 if path.item_from.wikidata_item.item_id == item_from and
                    path.item_to.wikidata_item.item_id == item_to]
            # filter not shortest pathes
            min_length = min([path.length for path in pathes_for_direction])
            pathes_for_direction = [path
                                    for path in pathes_for_direction
                                    if path.length == min_length]
            # calculate score
            if len(pathes_for_direction) == 1:
                score = 1.0 / float(k ** min_length)
                evaluated_pathes.append((score, pathes_for_direction[0], ))
                continue
            else:
                for idx1, path1 in enumerate(pathes_for_direction):
                    other_pathes = [
                        path2
                        for idx2, path2 in enumerate(pathes_for_direction)
                        if idx1 != idx2]
                    occurance_score = path1.similatiy_to_others(other_pathes)
                    avg_occurance = sum(occurance_score) / \
                        float(len(occurance_score))
                    score = 1.0 / float(k ** min_length) / (avg_occurance + 1)
                    evaluated_pathes.append((score, path1, ))
        evaluated_pathes = sorted(evaluated_pathes, key=lambda x: x[0])
        return evaluated_pathes
