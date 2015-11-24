# -*- coding: utf-8 -*-

import sys, re, random, copy
from cPickle import load
from collections import defaultdict
from cluster import Cluster
from agglomerator import Agglomerator
from mention import Mention, MalformedAuthorName
import name_dist
import speller
import output
import config
import utils


mentions = set()
article_to_mentions = defaultdict(set)

name_dist = name_dist.PriorNameDist()


def load_name_dist(name_dist_file):
    print "loading name_dist"
    name_dist_fh = open(name_dist_file)
    pieces = load(name_dist_fh)
    name_dist_fh.close()
    name_dist.load_pieces(pieces)


def load_mentions(in_file):
    print "loading mentions"
    pickle_handle = open(in_file, "r")
    local_mentions = load(pickle_handle)
    for m in local_mentions:
        mentions.add(m)


def name_sameness(p1, p2):
    if not utils.compatible_names(p1, p2):
        return 0.

    gen_prob = name_dist.common_prob_gen(p1, p2)
    expected_others = config.expected_authors * gen_prob

    distinct_names = 1
#    if p1.parent == p2.parent:
#        agg = p1.parent
#        intersected_name = Mention.intersected_name(p1, p2)
#        distinct_names = agg.distinct_authors(intersected_name)

    prob_same = 1. / (distinct_names + expected_others)

    return prob_same


def bootstrap_merge():
    print "bootstrap merge [%d clusters]" % len(mentions)

    token_to_mentions = defaultdict(set)
    for r in mentions:
        token_to_mentions[r.token()].add(r)

    print "  loading agglomerators"
    for t, local_mentions in token_to_mentions.iteritems():
        agg = Agglomerator(local_mentions)

    print "  running merge"
    for agg in Agglomerator.INSTANCES:
        agg.run_merge(name_sameness, config.bootstrap_threshold)


def bayesian_update(prior, p_given_match, p_given_not):
    posterior1 = prior * p_given_match
    posterior0 = (1 - prior) * p_given_not
    return posterior1 / (posterior1 + posterior0)


def coauthor_likelihoods(p1, p2):
    """returns the likelihoods of observing the actual number coauthors shared 
    by c{p1} and c{p2}, conditioned on whether or not p1 and p2 are a match
    """
    def get_coauthors(p):
        ret = set()
        for m in p.mentions:
            for co_m in article_to_mentions[m.article_id]:
                if m != co_m:
                    co_p = Agglomerator.MENTION_TO_CLUSTER[co_m]
                    ret.add(co_p)
        return ret

    def num_common_coauthors(p1, p2):
        return len(set.intersection(get_coauthors(p1), get_coauthors(p2)))

    num_common = num_common_coauthors(p1, p2)
    if num_common >= len(config.p_coauthor[0]):
        num_common = len(config.p_coauthor[0]) - 1
    likelihood0 = config.p_coauthor[0][num_common]
    likelihood1 = config.p_coauthor[1][num_common]
    
    return likelihood1, likelihood0


def collective_sameness(p1, p2):
    if not utils.compatible_names(p1, p2):
        return 0.
    prior = name_sameness(p1, p2)
    (likelihood1, likelihood0) = coauthor_likelihoods(p1, p2)
    return bayesian_update(prior, likelihood1, likelihood0)


def collective_merge():
    print "collective merge [%d clusters]" % len(Agglomerator.CLUSTERS)

    for m in mentions:
        article_to_mentions[m.article_id].add(m)

    for agg in Agglomerator.INSTANCES:
        agg.run_merge(collective_sameness, config.merge_threshold)


def attempt_merge(source_p, possible_targets, likelihoods):
    max_prob, max_pp = -1, None
    for pp in possible_targets:
        base_prob = collective_sameness(source_p, pp)
        revised_prob = bayesian_update(base_prob, likelihoods[1], likelihoods[0])
        if revised_prob > max_prob:
            max_prob, max_pp = revised_prob, pp

    if max_prob > config.merge_threshold:
        Agglomerator.do_static_merge(source_p, max_pp)
    else:
        source_p.restore_name()


def run_fold_in(mutation, source_criterion, target_criterion, likelihood):
    token_to_clusters = defaultdict(set)
    for p in Agglomerator.CLUSTERS:
        token_to_clusters[p.token()].add(p)
       
    for p in Agglomerator.CLUSTERS.copy():
        if not source_criterion(p):
            continue
        mutation(p)
        targets = [t for t in token_to_clusters[p.token()]\
            if t in Agglomerator.CLUSTERS and utils.compatible_names(p, t)\
            and p != t and target_criterion(p)]
        attempt_merge(p, targets, likelihood)


def drop_first_names():
    print "dropping first names"
    run_fold_in(
        Cluster.drop_first_name, 
        utils.drop_fn_source_candidate, 
        utils.drop_fn_target_candidate,
        config.p_drop_fn)


def drop_hyphenated_last_names():
    print "dropping hyphenated last names"
    run_fold_in(
        Cluster.drop_hyphenated_ln,
        utils.drop_ln_source_candidate,
        lambda x: True,
        config.p_drop_hyphenated_ln)


#TODO: implement this method by calling a generalized version of c{run_fold_in}
def correct_spellings():
    print "correcting misspellings"

    vocab = defaultdict(int)
    name_to_parts = defaultdict(set)
    for p in Agglomerator.CLUSTERS:
        for name in p.name_variants():
            vocab[name] += 1
            name_to_parts[name].add(p)

    print "  speller loaded"

    sp = speller.Speller(vocab)

    for p in Agglomerator.CLUSTERS.copy():
        if p not in Agglomerator.CLUSTERS:
            continue
        candidates = sp.candidates(p.full_name())
        p_name = p.full_name()
        candidates = [c for c in candidates if utils.same_fl_initials(c, p_name)]
        targets = set()
        for c in candidates:
            for p2 in name_to_parts[c]:
                if p != p2 and p2 in Agglomerator.CLUSTERS:
                    try:
                        c_author = Mention()
                        c_author.load_author_alias(c) #speed up by loading clean name
                        if utils.compatible_names(p2, c_author):
                            targets.add(p2)
                    except MalformedAuthorName, e:
                        pass
        #TODO: we should consider misspellings with multiple targets
        if len(targets) != 1:
            continue
   
        # Now p meets the preliminary criterion for spelling correction.
        # Next we will evaluate the probabilisticly determine whether to
        # proceed with the spelling correction.

        p2 = min(targets)

        (p_wrong, p_right) = (p, p2) \
            if p.num_mentions() < p2.num_mentions() else (p2, p)

        if p_right.shared_articles(p_wrong):
            continue

        prior1 = name_dist.misspelled_prob_same(p_right, p_wrong)
        #TODO: figure out the real likelihood vector
        prior2 = bayesian_update(prior1, config.p_misspelling, 1)
        (likelihood1, likelihood0) = coauthor_likelihoods(p_right, p_wrong)
        prior3 = bayesian_update(prior2, likelihood1, likelihood0)
       
        if prior3 > config.merge_threshold:
            old_token = p_wrong.token()
            p_wrong.fix_spelling(p_right)
            Agglomerator.do_static_merge(p_wrong, p_right)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "usage: %s <name_dist> <names_in_file> <names_out_file>" % sys.argv[0]
    else:
        load_name_dist(sys.argv[1])
        load_mentions(sys.argv[2])

        bootstrap_merge()
        collective_merge()

#        drop_first_names()
#        drop_hyphenated_last_names()
#        correct_spellings()

        output.Output(sys.argv[3], Agglomerator.CLUSTERS).output_all()

