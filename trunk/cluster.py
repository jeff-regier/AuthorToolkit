# Copyright 2009, Jeffrey Regier, jeff [at] stat [dot] berkeley [dot] edu

# This file is part of the Badger Author Disambiguation Toolkit (Badger).
#
# Badger is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Badger is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Badger.  If not, see <http://www.gnu.org/licenses/>.


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
