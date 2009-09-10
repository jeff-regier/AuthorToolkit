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


class Output():
    def __init__(self, out_base, parts):
        self.out_base = out_base
        self.author_refs = set()
        self.parts = parts
        for p in parts: #hack
            name = p.full_name()
            for a in p:
                a.merged_name = name
                self.author_refs.add(a)

    def convert_names(self):
        print "outputing author names"
        out_test_handle = open(self.out_base, "w")
        ordered_parts = list(self.parts)
        ordered_parts.sort(key=lambda p: p.full_name())
        for pi in xrange(len(ordered_parts)):
            p = ordered_parts[pi]
            for a in sorted(p.author_refs, key=lambda r: r.original_name):
                out_test_handle.write("%d\t%s\t%s\n" % (pi + 1, a.original_name, a.paper))

    def output_need_merge(self):
        truth_to_authors = {}
        for a in self.author_refs:
            truth_to_authors.setdefault(a.truth, []).append(a)

        def all_same_prediction(authors):
            if not authors:
                return True #vacuously true
            prev = authors[0]
            for a in authors:
                if a.merged_name != prev.merged_name:
                    return False
            return True

        def unique_list(l):
            temp = {}
            for i in l:
                temp[i] = True
            return sorted(temp.keys())

        merges_needed = 0
        out_handle = open(self.out_base + ".nm", "w")
        for t, authors in truth_to_authors.items():
            if not all_same_prediction(authors):
                merges_needed += 1
                names = [a.merged_name for a in authors]
                out_handle.write("%s\n" % ", ".join(unique_list(names)))

        print "merges needed: %d" % merges_needed

    def output_need_split(self):
        prediction_to_authors = {}
        for a in self.author_refs:
            prediction_to_authors.setdefault(a.merged_name, []).append(a)

        def all_same_truth(authors):
            if not authors:
                return True #vacuously true
            prev = authors[0]
            for a in authors:
                if a.truth != prev.truth:
                    return False
            return True

        splits_needed = 0
        out_handle = open(self.out_base + ".ns", "w")
        for p, authors in prediction_to_authors.items():
            truths_to_authors = defaultdict(set)
            for a in authors:
                truths_to_authors[a.truth].add(a.full_name())
            if len(truths_to_authors.keys()) > 1:
                splits_needed += 1
                names = [max(author_set, key=len) for author_set in truths_to_authors.values()]
                out_handle.write("%s\n" % ", ".join(names))

        print "splits needed: %d" % splits_needed

    def compute_performance(self):
        me_to_doc = defaultdict(float)
        truth_to_doc = defaultdict(float)
        truth_to_me = {}

        for a in self.author_refs:
            me_to_doc[a.merged_name] += 1
            truth_to_doc[a.truth] += 1
            truth_to_me.setdefault(a.truth, defaultdict(float))[a.merged_name] += 1

        def get_f_cell(truth, me):
            n1 = truth_to_me[truth].get(me, [])
            n2 = me_to_doc[me]
            n3 = truth_to_doc[truth]
            precision = n1 / n2
            recall = n1 / n3
            return (2 * precision * recall) / (precision + recall)

        def get_f_best(truth):
            best_fscore = -1
            for me in truth_to_me[truth]:
                fscore = get_f_cell(truth, me)
                if fscore > best_fscore:
                    best_fscore = fscore
            return best_fscore

        total_true = 0.
        for truth, num_docs in truth_to_doc.items():
            total_true += num_docs

        overall_f = 0
        for truth, num_docs in truth_to_doc.items():
            def f_cell_bound(me):
                return get_f_cell(truth, me)
            fscore = max(truth_to_me[truth].keys(), key=f_cell_bound)
            fscore = get_f_best(truth)
            prop_true = num_docs / total_true
            overall_f += prop_true * fscore

        print "f-score: ", overall_f

    def output_all(self):
        self.convert_names()
        if config.truth_mode:
            self.compute_performance()
            self.output_need_merge()
            self.output_need_split()



