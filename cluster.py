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


class Cluster():
    def __init__(self, seed_a):
        self.author_refs = set([seed_a])
        self.papers = set([seed_a.paper])
        self.first_name = seed_a.fn()
        self.middle_names = seed_a.mns()
        self.last_name = seed_a.ln()

    def __str__(self):
        return self.full_name()

    def __iter__(self):
        return self.author_refs.__iter__()

    def extend(self, source_part):
        self.author_refs.update(source_part.author_refs)
        self.papers.update(source_part.papers)
        self.first_name = max([r.fn() for r in self.author_refs], key=len)
        self.middle_names = max([r.mns() for r in self.author_refs], key=len)

    def fn(self):
        return self.first_name

    def mns(self):
        return self.middle_names

    def ln(self):
        return self.last_name

    def token(self):
        return "%s_%s" % (self.last_name, self.first_name[0])

    def full_name(self):
        all_names = [self.fn()] + self.mns() + [self.ln()]
        return " ".join(all_names)

    def name_length(self):
        return len(self.full_name())

    def change_last_name(self, new_last):
        self.last_name = new_last

    def backup_name(self):
        self.former_fn = self.fn()
        self.former_mns = self.mns()
        self.former_ln = self.ln()

    def restore_name(self):
        self.first_name = self.former_fn
        self.middle_names = self.former_mns
        self.last_name = self.former_ln

    def drop_first_name(self):
        self.backup_name()
        self.first_name = self.mns()[0]
        self.middle_names = self.mns()[1:]

    def drop_hyphenated_ln(self):
        self.backup_name()
        import re
        self.last_name = re.sub(r'-\w+$', '', self.ln())

    def fix_spelling(self, pc):
        self.backup_name()
        fn, mns, ln = pc.fn(), pc.mns(), pc.ln()
        if not utils.compatible_name_part(fn, self.fn()):
            self.first_name = fn
        if mns != self.mns():
            self.middle_names = mns
        if ln != self.ln():
            self.change_last_name(ln)

    def name_variants(self):
        ret = set([self.full_name()])
        m_string = " ".join(self.mns())
        ret.add("%s %s" % (self.fn(), self.ln()))
        ret.add("%s %s" % (self.fn()[0], self.ln()))
        if self.mns():
            ret.add("%s %s %s" % (self.fn(), m_string, self.ln()))
            ret.add("%s %s %s" % (self.fn()[0], m_string, self.ln()))
        return ret

    def truth(self):
        truth_count = defaultdict(int)
        for r in self.author_refs:
            truth_count[r.truth] += 1
        return max(truth_count.keys(), key=lambda x: truth_count[x])

    def num_refs(self):
        return len(self.author_refs)

    def shared_papers(self, p):
        return self.papers.intersection(p.papers)
