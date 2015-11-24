from collections import defaultdict
import config
import utils
from cluster import Cluster


class Agglomerator():

    CLUSTERS = set()
    MENTION_TO_CLUSTER = {}
    INSTANCES = set()

    def __init__(self, mentions):
        self.load_clusters(mentions)
        self.INSTANCES.add(self)
        self.load_compat_mat(mentions)

    def pairs_iter(self):
        clusters_list = sorted(list(self.clusters), key=lambda c: c.full_name())
        for i in xrange(len(clusters_list)):
            for j in xrange(i + 1, len(clusters_list)):
                c1, c2 = clusters_list[i], clusters_list[j]
                if utils.compatible_names(c1, c2):
                    yield (c1, c2)

    def safe_pairs_iter(self):
        for c1, c2 in self.pairs_iter():
            if utils.compatible_names(c1, c2):
                if self.stricter_than(c1, c2) or self.stricter_than(c2, c1)\
                    or self.is_equivalent(c1, c2):
                    yield (c1, c2)

    def load_compat_mat(self, mentions):
        self.compat_map = defaultdict(set)
        for m1 in mentions:
            for m2 in mentions:
                if utils.compatible_names(m1, m2):
                    self.compat_map[m1].add(m2)

    def get_partition_compat(self, c):
        compat_maps = [self.compat_map[m] for m in c]
        return reduce(set.intersection, compat_maps)

    def stricter_than(self, c_loose, c_strict):
        compat1 = self.get_partition_compat(c_loose)
        compat2 = self.get_partition_compat(c_strict)
        return compat1 > compat2

    def is_equivalent(self, c1, c2):
        compat1 = self.get_partition_compat(c1)
        compat2 = self.get_partition_compat(c2)
        return compat1 == compat2

    def load_clusters(self, mentions):
        self.clusters = set()
        for m in mentions:
            c = Cluster(m)
            c.parent = self
            self.clusters.add(c)
            self.CLUSTERS.add(c)
            self.MENTION_TO_CLUSTER[m] = c

    def distinct_authors(self, name_intersection):
        return 1

    @classmethod
    def do_static_merge(cls, c_source, c_target):
        """By the time we're just folding in clusters, there's no need to maintain
        self.INSTANCES and self.clusters, so we just call this method
        """
        c_target.extend(c_source)
        c_source.parent = c_target.parent
        cls.CLUSTERS.remove(c_source)
        for m in c_source.mentions:
            cls.MENTION_TO_CLUSTER[m] = c_target

    def do_self_merge(self, c_source, c_target):
        self.clusters.remove(c_source)
        self.do_static_merge(c_source, c_target)

    def run_merge(self, similarity, threshold):
        clusters_list = sorted(list(self.clusters), key=lambda c: c.full_name())
        for i in xrange(len(clusters_list)):
            for j in xrange(i + 1, len(clusters_list)):
                c1, c2 = clusters_list[i], clusters_list[j]
                if similarity(c1, c2) > threshold:
                    self.do_self_merge(c1, c2)
                    break

