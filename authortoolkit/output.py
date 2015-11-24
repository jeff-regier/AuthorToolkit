from collections import defaultdict
import config


class Output():
    def __init__(self, out_base, parts):
        self.out_base = out_base
        self.mentions = set()
        self.parts = parts
        for p in parts: #hack
            name = p.full_name()
            for a in p:
                a.merged_name = name
                self.mentions.add(a)

    def convert_names(self):
        print "outputing author names"
        out_test_handle = open(self.out_base, "w")
        ordered_parts = list(self.parts)
        ordered_parts.sort(key=lambda p: p.full_name())
        for pi in xrange(len(ordered_parts)):
            p = ordered_parts[pi]
            for a in sorted(p.mentions, key=lambda r: r.original_name):
                out_test_handle.write("%d\t%s\t%s\n" % (pi + 1, a.original_name, a.article_id))

    def output_need_merge(self):
        author_to_mentions = {}
        for a in self.mentions:
            author_to_mentions.setdefault(a.author_id, []).append(a)

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
        for t, authors in author_to_mentions.items():
            if not all_same_prediction(authors):
                merges_needed += 1
                names = [a.merged_name for a in authors]
                out_handle.write("%s\n" % ", ".join(unique_list(names)))

        print "merges needed: %d" % merges_needed

    def output_need_split(self):
        prediction_to_authors = {}
        for a in self.mentions:
            prediction_to_authors.setdefault(a.merged_name, []).append(a)

        def all_same_author_id(authors):
            if not authors:
                return True #vacuously true
            prev = authors[0]
            for a in authors:
                if a.author_id != prev.author_id:
                    return False
            return True

        splits_needed = 0
        out_handle = open(self.out_base + ".ns", "w")
        for p, authors in prediction_to_authors.items():
            author_to_aliases = defaultdict(set)
            for a in authors:
                author_to_aliases[a.author_id].add(a.full_name())
            if len(author_to_aliases.keys()) > 1:
                splits_needed += 1
                names = [max(author_set, key=len) for author_set in author_to_aliases.values()]
                out_handle.write("%s\n" % ", ".join(names))

        print "splits needed: %d" % splits_needed

    def compute_performance(self):
        me_to_num_articles = defaultdict(float)
        author_to_num_articles = defaultdict(float)
        truth_to_me = {}

        for a in self.mentions:
            me_to_num_articles[a.merged_name] += 1
            author_to_num_articles[a.author_id] += 1
            truth_to_me.setdefault(a.author_id, defaultdict(float))[a.merged_name] += 1

        def get_f_cell(truth, me):
            n1 = truth_to_me[truth].get(me, [])
            n2 = me_to_num_articles[me]
            n3 = author_to_num_articles[truth]
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
        for truth, num_docs in author_to_num_articles.items():
            total_true += num_docs

        overall_f = 0
        for truth, num_docs in author_to_num_articles.items():
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



