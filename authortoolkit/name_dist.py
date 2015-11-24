import sys, re
from collections import defaultdict
from mention import Mention
import config, utils, speller


class Counter():
    def __init__(self):
        self.map = defaultdict(int)
        self.total = 0

    def incr(self, key):
        self.map[key] += 1
        self.total += 1

    def get_prop(self, key):
        return (1. + self.map[key]) / (1. + float(self.total))


class PriorNameDist():
    """Evaluates the mutual information between two authors, given a training dataset"""

    def __init__(self):
        self.fn_map, self.fl_map, self.ln_map = Counter(), Counter(), Counter()
        self.cache = {}

    def add_mention(self, r):
        self.fl_map.incr(r.fn()[0])
        if len(r.fn()) > 1:
            self.fl_map.incr(r.fn())
        for m in r.mns():
            self.fl_map.incr(m[0])
            if len(m) > 1:
                self.fn_map.incr(m)
        self.ln_map.incr(r.ln())

    def load_pieces(self, pieces):
        def piece_to_counter(piece):
            ret = Counter()
            ret.map = piece
            ret.total = reduce(lambda x,y: x + y, piece.values())
            return ret

        self.fn_map = piece_to_counter(pieces['fn'])
        self.fl_map = piece_to_counter(pieces['fl'])
        self.ln_map = piece_to_counter(pieces['ln'])

        self.fn_sp = speller.Speller(set(self.fn_map.map.keys()))
        self.ln_sp = speller.Speller(set(self.ln_map.map.keys()))

    def prob_gen(self, fn, mns, ln):
        f_map = self.fn_map if len(fn) > 1 else self.fl_map
        ret = f_map.get_prop(fn)
        ret *= self.ln_map.get_prop(ln)
        for mn in mns:
            f_map = self.fn_map if len(mn) > 1 else self.fl_map
            ret *= f_map.get_prop(mn)
        return ret

    def one_prob_gen(self, p):
        return self.prob_gen(p.fn(), p.mns(), p.ln())

    def common_prob_gen(self, p1, p2):
        fn = utils.shorter(p1.fn(), p2.fn())
        mns = []
        mns1, mns2 = p1.mns(), p2.mns()
        if len(mns1) == len(mns2):
            mns = [utils.shorter(mns1[mi], mns2[mi]) for mi in xrange(len(mns1))]

        return self.prob_gen(fn, mns, p1.ln())

    def prob_same(self, p1, p2):
        if not utils.compatible_names(p1, p2):
            return 0.

        cache_key = "%s|%s" % (p1.full_name(), p2.full_name())
        if cache_key in self.cache:
            return self.cache[cache_key]

        iname = Mention(p1, p2)
        gen_prob2 = self.prob_gen(iname.fn(), iname.mns(), iname.ln())
        gen_prob = self.common_prob_gen(p1, p2)

        print "should be the same:", gen_prob, gen_prob2        

        # c{expected_others} is the expected number of other authors sharing this name
        expected_others = config.expected_authors * gen_prob
        # c{prob_same} is the probability that both references were generated 
        # by the same authors
        prob_same = 1. / (1. + expected_others)

        self.cache[cache_key] = prob_same
        return prob_same

    def misspelled_common_prob_gen(self, p_right, p_wrong):
        mns_pairs = []
        if len(p_right.mns()) == len(p_wrong.mns()):
            mns_pairs = zip(p_right.mns(), p_wrong.mns())
        
        ret = 1.

        if utils.compatible_name_part(p_right.fn(), p_wrong.fn()):
            fn_intersection = utils.shorter(p_right.fn(), p_wrong.fn())
            f_map = self.fn_map if len(fn_intersection) > 1 else self.fl_map
            ret *= f_map.get_prop(fn_intersection)
        else:
            if len(p_right.fn()) != 1:
                neighborhood = set([p_right.fn()] + self.fn_sp.candidates(p_right.fn()))
                neighborhood = [c for c in neighborhood if c[0] == p_right.fn()[0]]
                ret *= sum([self.fn_map.get_prop(c) for c in neighborhood])
    
        for rw, ww in mns_pairs:
            if utils.compatible_name_part(rw, ww):
                mn_intersection = utils.shorter(rw, ww)
                f_map = self.fn_map if len(mn_intersection) > 1 else self.fl_map
                ret *= f_map.get_prop(mn_intersection)
            else:
                if len(rw) != 1: #an initial can be mutated into any initial
                    #TODO: watch out for 2-character names, that could be changed to initials
                    neighborhood = set([rw] + self.fn_sp.candidates(rw))
                    ret *= sum([self.fn_map.get_prop(c) for c in neighborhood])
        
        r_ln, w_ln = p_right.ln(), p_wrong.ln()
        if r_ln == w_ln:
            ret *= self.ln_map.get_prop(r_ln)
        else:
            neighborhood = set([r_ln] + self.ln_sp.candidates(r_ln))
            neighborhood = [c for c in neighborhood if c[0] == r_ln[0]]
            ret *= sum([self.ln_map.get_prop(c) for c in neighborhood])

        return ret

    def misspelled_prob_same(self, p_right, p_wrong):
        #TODO this should be (more) symmetric
        gen_prob = self.misspelled_common_prob_gen(p_right, p_wrong)

        # c{expected_others} is the expected number of other authors sharing this name
        expected_others = config.expected_authors * gen_prob
        # c{prob_same} is the probability that both references were generated 
        # by the same authors
        #TODO: should assume number of publications follows a power law, rather than
        #being equal
        prob_same = 1. / (1. + expected_others)

        return prob_same

