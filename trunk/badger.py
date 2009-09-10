#!/usr/bin/python

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

import sys, re, random, pickle, copy
from collections import defaultdict
from cluster import Cluster
from agglomerator import Agglomerator
from author_ref import AuthorRef, MalformedAuthorName
import name_dist
import speller
import output
import config
import utils


author_refs = set()
paper_to_refs = defaultdict(set)

name_dist = name_dist.PriorNameDist()


def load_name_dist(name_dist_file):
    print "loading name_dist"
    name_dist_fh = open(name_dist_file)
    pieces = pickle.load(name_dist_fh)
    name_dist_fh.close()
    name_dist.load_pieces(pieces)


def load_names(in_file):
    print "loading names"

    names_handle = open(in_file)
    for n in names_handle:
        try:
            vals = n.rstrip().split("\t")
            if not config.truth_mode:
                vals.append(False)
            [paper, names, truth] = vals
            for name in names.split(","):
                try:
                    r = AuthorRef(name)
                    r.paper = paper
                    r.truth = truth

                    author_refs.add(r)
                    paper_to_refs[paper].add(r)
                except MalformedAuthorName, e:
                    print e
        except ValueError, e:
            print "Cannot split line '%s'" % n.rstrip()


def name_sameness(p1, p2):
    if not utils.compatible_names(p1, p2):
        return 0.

    gen_prob = name_dist.common_prob_gen(p1, p2)
    expected_others = config.expected_authors * gen_prob

    assert p1.parent == p2.parent
    agg = p1.parent
    intersected_name = AuthorRef.intersected_name(p1, p2)
    distinct_names = agg.distinct_authors(intersected_name)

    prob_same = 1. / (distinct_names + expected_others)

    return prob_same


def bootstrap_merge():
    print "bootstrap merge"

    token_to_refs = defaultdict(set)
    for r in author_refs:
        token_to_refs[r.token()].add(r)

    for t, local_refs in token_to_refs.iteritems():
        agg = Agglomerator(local_refs)
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
        for r in p.author_refs:
            for co_r in paper_to_refs[r.paper]:
                if r != co_r:
                    co_p = Agglomerator.REF_TO_CLUSTER[co_r]
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
    print "collective merge"

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

    print "\tspeller loaded"

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
                if p != p2 and p2 in Agglomerator.CLUSTERS and\
                    utils.compatible_names(p2, AuthorRef(c)):
                    targets.add(p2)
        #TODO: we should consider misspellings with multiple targets
        if len(targets) != 1:
            continue
   
        # Now p meets the preliminary criterion for spelling correction.
        # Next we will evaluate the probabilisticly determine whether to
        # proceed with the spelling correction.

        p2 = min(targets)

        (p_wrong, p_right) = (p, p2) if p.num_refs() < p2.num_refs() else (p2, p)

        if p_right.shared_papers(p_wrong):
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
        load_names(sys.argv[2])

        bootstrap_merge()
        collective_merge()

        drop_first_names()
        drop_hyphenated_last_names()
        correct_spellings()

        output.Output(sys.argv[3], Agglomerator.CLUSTERS).output_all()

