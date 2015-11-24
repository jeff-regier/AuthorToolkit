#!/usr/bin/python -u

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

