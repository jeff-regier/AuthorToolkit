#!/usr/bin/python

import sys, re, pickle
from collections import defaultdict
import mention
from name_dist import PriorNameDist


def run(in_file, out_file):
    in_handle = open(in_file)
    out_handle = open(out_file, "w")

    pnd = PriorNameDist()

    i = 0
    for line in in_handle:
        try:
            m = mention.Mention(line.rstrip())
            pnd.add_mention(m)
            i += 1
            if (i % 10000) == 0:
                print "loaded author %d" % i
        except:
            pass

    pnd_dump = {
        "fn": pnd.fn_map.map,
        "fl": pnd.fl_map.map,
        "ln": pnd.ln_map.map,
    }
        
    pickle.dump(pnd_dump, out_handle, 2)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "usage: %s <names_txt_in> <name_dat_out>" % sys.argv[0]
    else:
        run(sys.argv[1], sys.argv[2])
