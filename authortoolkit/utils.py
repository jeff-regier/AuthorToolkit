import re
from collections import defaultdict


re_ss = re.compile(r'^.* (\S)\S*$')


def compatible_name_part(w1, w2):
    if w1 == w2:
        return True
    elif len(w1) != 1 and len(w2) != 1:
        return False
    else:
        return w1[0] == w2[0]


def compatible_names(e1, e2):
    """This function takes either PartitionParts or Mentions as arguments
    """

    if e1.ln() != e2.ln():
        return False

    short, long = list(e1.mns()), e2.mns()
    if len(short) > len(long):
        return compatible_names(e2, e1)

    # the front first names must be compatible
    if not compatible_name_part(e1.fn(), e2.fn()):
        return False

    # try finding each middle name of long in short, and remove the
    # middle name from short if found
    for wl in long:
        if not short:
            break
        ws = short.pop(0)
        if not compatible_name_part(ws, wl):
            short.insert(0, ws)

    # true iff short is a compatible substring of long
    return short == []


def drop_fn_source_candidate(p):
    return len(p.mns()) == 1 and\
        len(p.mns()[0]) == 1 and\
        p.mns()[0][0] != p.fn()[0]

def drop_fn_target_candidate(p):
    return len(p.mns()) == 0


def drop_ln_source_candidate(p):
    return re.match(r'\w{4,}-\w{4,}', p.ln())


def shorter(s1, s2):
    return s1 if len(s1) < len(s2) else s2


def same_fl_initials(name1, name2):
    if name1[0] != name2[0]:
        return False
    li1 = re_ss.sub(r'\1', name1)
    li2 = re_ss.sub(r'\1', name2)
    return li1 == li2

