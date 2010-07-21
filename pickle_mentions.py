#!/usr/bin/python -u

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


import sys, re
from cPickle import dump
from collections import defaultdict
from mention import Mention, MalformedAuthorName


mentions = set()


def load_mentions(in_file):
    print "loading mentions"

    names_handle = open(in_file)
    for n in names_handle:
        try:
            vals = n.rstrip().split("\t")
            if len(vals) == 2: #for prediction mode
                vals.append(False)
            [article_id, author_alias, author_id] = vals
            try:
                m = Mention()
                m.load_author_alias(author_alias)
                m.article_id = article_id
                m.author_id = author_id

                mentions.add(m)
            except MalformedAuthorName, e:
                print e
        except ValueError, e:
            print "Cannot split line '%s'" % n.rstrip()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: %s <names_in_file>" % sys.argv[0]
    else:
        load_mentions(sys.argv[1])
        pickle_handle = open("%s.pickled" % sys.argv[1], "w")
        dump(mentions, pickle_handle, 2)

