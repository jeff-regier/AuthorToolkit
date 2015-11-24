from collections import defaultdict
import utils
from mention import Mention


class Cluster (Mention):
    def __init__(self, seed_m):
        self.mentions = set([seed_m])
        self.articles = set([seed_m.article_id])
        self.first_name = seed_m.fn()
        self.middle_names = seed_m.mns()
        self.last_name = seed_m.ln()

    def __str__(self):
        return self.full_name()

    def __iter__(self):
        return self.mentions.__iter__()

    def extend(self, source_c):
        self.mentions.update(source_c.mentions)
        self.articles.update(source_c.articles)
        self.first_name = max(self.fn(), source_c.fn(), key=len)
        self.middle_names = max(self.mns(), source_c.mns(), key=len)

    def truth(self):
        truth_count = defaultdict(int)
        for m in self.mentions:
            truth_count[m.author_id] += 1
        return max(truth_count.keys(), key=lambda x: truth_count[x])

    def num_mentions(self):
        return len(self.mentions)

    def shared_articles(self, c):
        return self.articles.intersection(c.articles)
