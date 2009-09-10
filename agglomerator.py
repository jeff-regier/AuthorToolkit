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
import config
import utils
from cluster import Cluster


class Agglomerator():

    CLUSTERS = set()
    REF_TO_CLUSTER = {}
    INSTANCES = set()

    def __init__(self, author_refs):
        self.load_clusters(author_refs)
        self.INSTANCES.add(self)
        self.load_compat_mat(author_refs)

    def load_compat_mat(self, author_refs):
        self.compat_map = defaultdict(set)
        for a1 in author_refs:
            for a2 in author_refs:
                if utils.compatible_names(a1, a2):
                    self.compat_map[a1].add(a2)

    def get_partition_compat(self, part):
        compat_maps = [self.compat_map[a] for a in part]
        return reduce(set.intersection, compat_maps)

    def stricter_than(self, p_loose, p_strict):
        compat1 = self.get_partition_compat(p_loose)
        compat2 = self.get_partition_compat(p_strict)
        return compat1 > compat2

    def is_equivalent(self, p1, p2):
        compat1 = self.get_partition_compat(p1)
        compat2 = self.get_partition_compat(p2)
        return compat1 == compat2

    def load_clusters(self, author_refs):
        self.clusters = set()
        for r in author_refs:
            p = Cluster(r)
            self.clusters.add(p)
            self.CLUSTERS.add(p)
            self.REF_TO_CLUSTER[r] = p
            p.parent = self

    def distinct_authors(self, name_intersection):
        return 1

    @classmethod
    def do_static_merge(cls, p_source, p_target):
        """By the time we're just folding in clusters, there's no need to maintain
        self.INSTANCES and self.clusters, so we just call this method
        """
        p_target.extend(p_source)
        p_source.parent = p_target.parent
        cls.CLUSTERS.remove(p_source)
        for r in p_source.author_refs:
            cls.REF_TO_CLUSTER[r] = p_target

    def do_self_merge(self, p_source, p_target):
        self.clusters.remove(p_source)
        self.do_static_merge(p_source, p_target)

    def merge_obvious(self, similarity):
        clusters_list = list(self.clusters)
        for i in xrange(len(clusters_list)):
            for j in xrange(i + 1, len(clusters_list)):
                p1, p2 = clusters_list[i], clusters_list[j]
                if similarity(p1, p2) > config.instant_merge_threshold:
                    self.do_self_merge(p1, p2)
                    break

    def merge_best_one(self, similarity, threshold):
        greatest_likelihood = -1.0
        greatest_pair = None

        clusters_list = list(self.clusters)
        for i in xrange(len(clusters_list)):
            for j in xrange(i + 1, len(clusters_list)):
                p1, p2 = clusters_list[i], clusters_list[j]
                likeness = similarity(p1, p2)
                if likeness > greatest_likelihood:
                    greatest_likelihood = likeness
                    greatest_pair = (p1, p2)

        if greatest_likelihood > threshold:
            p1, p2 = greatest_pair
            self.do_self_merge(p1, p2)
            return True
        return False

    def run_merge(self, similarity, threshold):
        self.merge_obvious(similarity)
        while self.merge_best_one(similarity, threshold):
            pass

