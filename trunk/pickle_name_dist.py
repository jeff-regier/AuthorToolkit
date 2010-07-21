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
