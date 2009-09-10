#!/usr/bin/python

import sys, re, random, copy, math
from collections import defaultdict
from author_ref import AuthorRef, MalformedAuthorName
from speller import Speller
import utils
from cluster import Cluster


max_common = 4
num_samples = 100000
num_samples_inner = 10

author_refs = []
author_to_refs = defaultdict(set)
paper_to_refs = defaultdict(set)


def load_names(in_file):
    print "loading names"
    names_handle = open(in_file)

    for n in names_handle:
        paper, name, author = n.rstrip().split("\t")
        try:
            r = AuthorRef(name)
            r.author = author
            r.paper = paper

            author_refs.append(r)
            author_to_refs[author].add(r)
            paper_to_refs[paper].add(r)
        except MalformedAuthorName, e:
            pass


def compatible_pairs_iter():
    token_to_refs = defaultdict(set)
    for r in author_refs:
        token_to_refs[r.token()].add(r)

    for token, refs in token_to_refs.iteritems():
        for r1 in refs:
            for r2 in refs:
                if r1 >= r2 and utils.compatible_names(r1, r2):
                    yield r1, r2


def droppable_pairs_iter():
    token_to_refs = defaultdict(set)
    for r in author_refs:
        token_to_refs[r.token()].add(r)

    for token, refs in token_to_refs.iteritems():
        for r1 in refs:
            if not utils.drop_fn_source_candidate(r1):
                continue
            p1 = Cluster(copy.deepcopy(r1))
            p1.drop_fn()
            for r2 in token_to_refs[p1.token()]:
                if utils.drop_fn_target_candidate(r2) and utils.compatible_names(p1, r2):
                    yield r1, r2

def fn_stats():
    def drop_causes_compat(refs1, refs2):
        sources = [r for r in refs1 if utils.drop_fn_source_candidate(r)]
        targets = [r for r in refs2 if utils.drop_fn_target_candidate(r)]
        for s in sources:
            sc = copy.deepcopy(s)
            sc.drop_first_name()
            for t in targets:
                if s != t and utils.compatible_names(sc, t):
                    return True
        return False

    def would_be_compared(refs1, refs2):
        if min(refs1).ln() != min(refs2).ln():
            return False
        sources = [r for r in refs1 if utils.drop_fn_source_candidate(r)]
        targets = [r for r in refs2 if utils.drop_fn_target_candidate(r)]
        return sources and targets

    def match_fn_stats():
        """We assume that at the time this probability is used, all the references
        for this author will have been merged into one cluster if fn is always used,
        or two clusters if fn is sometimes dropped.
        """

        dropped_count, candidates = 0, 0

        for a_id, refs in author_to_refs.iteritems():
            if not would_be_compared(refs, refs):
                continue
            if drop_causes_compat(refs, refs):
                print ",".join([r.original_name for r in refs])
                dropped_count += 1
            candidates += 1

        print "Pr( mn_compat_fn | match ) = %d. / %d" % (dropped_count, candidates)

    def nonmatch_fn_stats():
        dropping_misleads, candidates = 0, 0

        # need to block refs by last name, middle initial, and then index iterate just through these
        for a1_id, refs1 in author_to_refs.iteritems():
            ar_list = author_to_refs.items()
            ar_sample = [ar_list[random.randint(0, len(ar_list) - 1)] for _ in xrange(num_samples_inner)]
            for a2_id, refs2 in ar_sample:
                if a1_id == a2_id or not would_be_compared(refs1, refs2):
                    print a1_id, a2_id, ",".join([r.original_name for r in refs1])
                    continue
                if drop_causes_compat(refs1, refs2):
                    print ",".join(set([r.original_name for r in refs1]))
                    print ",".join(set([r.original_name for r in refs2]))
                    print "--------"
                    dropping_misleads += 1
                candidates += 1
            print dropping_misleads, candidates

        print "Pr( mn_compat_fn | nonmatch ) = %d. / %d" % (dropping_misleads, candidates)

    match_fn_stats()
    nonmatch_fn_stats()
       

def change_letter_stats():
    name_counts = defaultdict(int)
    for a in author_refs:
        for nv in a.name_variants():
            name_counts[nv] += 1

    sp = Speller(name_counts)

    helps, hurts = defaultdict(int), defaultdict(int)
    already_seen = set()
    for a in author_refs:
        seen_token = a.author + "|" + a.full_name()
        if seen_token in already_seen:
            continue
        already_seen.add(seen_token)

        alen = len(a.full_name())

        candidates = sp.candidates(a.full_name())
        candidates2 = [c for c in candidates if utils.same_fl_initials(a.full_name(), c)]
        for a_correct in author_to_refs[a.author]:
            if utils.compatible_names(a, a_correct):
                continue #we already would have gotten this one
            if a_correct.full_name() in candidates2:
                helps[alen] += 1
                hurts[alen] -= 1
        for c_name in candidates2:
            hurts[alen] += name_counts[c_name]

    for alen in hurts.keys():
        prop = float(helps[alen]) / (helps[alen] + hurts[alen])
        print "changing 1 letter of %d-character name: %d / %d [%f]"\
            % (alen, helps[alen], hurts[alen], prop)


def papers_per_author_stats():
    num_p_to_num_a = defaultdict(int)
    num_ap = 0.
    for t, authors in author_to_refs.iteritems():
        num_p_to_num_a[len(authors)] += 1
        num_ap += len(authors)
    num_a = float(len(author_to_refs.keys()))
    exp_val = num_ap / num_a
    print "avg papers per author:", exp_val
    ways_to_match = 0
#    print "papers per author distribution:"
    for cur_num_p, cur_num_a in sorted(num_p_to_num_a.items()):
        ways_to_match += (cur_num_a * cur_num_p) * (cur_num_p - 1)
#        print "\t%d: %d [%f]" % (cur_num_p, cur_num_a, cur_num_a / num_a)
    print "prob same author:", float(ways_to_match) / (num_ap ** 2.)


def match_coauthor_stats():
    print "match coauthor stats"

    author_to_papers = defaultdict(set)
    paper_to_authors = defaultdict(set)
    for r in author_refs:
        author_to_papers[r.author].add(r.paper)
        paper_to_authors[r.paper].add(r.author)

    counter = [0 for _ in range(max_common + 1)]
    total = 0.

    for r in author_refs:
        papers = author_to_papers[r.author]
        other_papers = [p for p in papers if p != r.paper]
        other_coauthors = set()
        for p in other_papers:
            these_coauthors = paper_to_authors[p]
            other_coauthors.update(these_coauthors)
        if other_coauthors:
            other_coauthors.remove(r.author)
        cur_coauthors = paper_to_authors[r.paper]
        num_common = len(other_coauthors.intersection(cur_coauthors))
        if num_common > max_common:
            num_common = max_common
        counter[num_common] += 1
        total += 1
    
    for i in xrange(max_common + 1):
        print "p(%d common coauthor | match): %f" % (i, counter[i] / total)


def nonmatch_coauthor_stats():
    print "nonmatch coauthor stats"

    author_to_papers = defaultdict(set)
    paper_to_authors = defaultdict(set)
    for r in author_refs:
        author_to_papers[r.author].add(r.paper)
        paper_to_authors[r.paper].add(r.author)

    author_to_coauthors = defaultdict(set)
    for a, papers in author_to_papers.iteritems():
        for p in papers:
            author_to_coauthors[a].update(paper_to_authors[p])
        author_to_coauthors[a].remove(a)

    authors_list = author_to_coauthors.keys()
    num_authors = len(authors_list)

    def rand_coauthor_set():
        i = random.randint(0, num_authors - 1)
        a = authors_list[i]
        return author_to_coauthors[a]

    counter = [0 for _ in range(max_common + 1)]
    for i in xrange(num_samples):
        co1, co2 = rand_coauthor_set(), rand_coauthor_set()
        num_common = len(co1.intersection(co2))
        if num_common > max_common:
            num_common = max_common
        counter[num_common] += 1

    for i in xrange(max_common + 1):
        print "p(%d common coauthor | nonmatch): %f" % (i, float(counter[i]) / num_samples)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: %s <in_file>" % sys.argv[0]
    else:
        load_names(sys.argv[1])
#        change_letter_stats()
        fn_stats()
#        papers_per_author_stats()
#        match_coauthor_stats()
#        nonmatch_coauthor_stats()
