import re
from unidecode import unidecode
import nick_names
import utils


class MalformedAuthorName(Exception):
    pass

class Mention():
    def __init__(self):
        pass

    def load_author_alias(self, name_str):
        self.original_name = name_str
        self.merged_name = name_str #this gets overwritten
        self.first_name, self.middle_names, self.last_name, self.suffix = self.split_name()
        if len(self.middle_names) > 4:
            msg = "Too many middle names in '%s'" % self
            raise MalformedAuthorName(msg)

    def load_clean_name(self, fn, mns, ln, suffix):
        self.first_name, self.middle_names, self.last_name, self.suffix = \
            (fn, mns, ln, suffix)

        name_str = " ".join([fn] + mns + [ln])
        self.original_name = name_str
        self.merged_name = name_str #this gets overwritten

    @classmethod
    def intersected_name(cls, e1, e2):
        fn = utils.shorter(e1.fn(), e2.fn())

        mns = []
        mns1, mns2 = e1.mns(), e2.mns()
        if len(mns1) == len(mns2):
            mns = [utils.shorter(mns1[mi], mns2[mi]) for mi in xrange(len(mns1))]

        ln = e1.ln()

        a = cls()
        a.load_clean_name(fn, mns, ln, "")
        return a

    def __str__(self):
        return self.original_name

    def clean_name(self):
        name_str = self.original_name.decode('utf-8')
        name_str = unidecode(name_str)
        name_str = re.sub(r'\s+', ' ', name_str)
        name_str = re.sub(r'[^a-zA-Z .,-]', '', name_str)
        name_str = re.sub(r' -|- ', ' ', name_str)
        name_str = re.sub(r'--+', '-', name_str)
        name_str = re.sub(r'(?i)^(Dr|Mr|Mrs|Ms)\. ', '', name_str)
        name_str = re.sub('^([A-Z])([A-Z]) ', r'\1. \2. ', name_str)
        name_str = re.sub('^([A-Z][a-z]+)\. ', r'\1 ', name_str)
        name_str = re.sub('\. *', ' ', name_str)
        name_str = re.sub('(:? |^)((van|de|del|da|do|el|la|di|von|der) )+', ' ', name_str)
        name_str = re.sub(r'^ +| +$', '', name_str)
        name_str = re.sub(r'\s+', ' ', name_str)
        return name_str.lower()

    def split_name(self):
        cname = self.clean_name()

        suffix = ""
        m_suffix = re.search(r'(?i)^(.*) (jr|iii|iv)$', cname)
        if m_suffix:
            cname, suffix = m_suffix.group(1), m_suffix.group(2)

        not_last_name, last_name = "", ""

        # smith, john c
        m = re.match('(?P<last>.+), (?P<first>.+)', cname)
        if not m:
            # smith j c
            m = re.match('^(?P<last>\S{2,}) (?P<first>(?:[a-z] )*[a-z])$', cname)
        if not m:
            # j c smith
            m = re.match('^(?P<first>.+?) (?P<last>\S+)$', cname)
        if not m:
            msg = "Cannot split '%s' into first and last names" % self
            raise MalformedAuthorName(msg)

        not_last_name, last_name = m.group("first"), m.group("last")

        name_parts = re.split(r'[ -]+', not_last_name)
        name_parts = [n for n in name_parts if n]
        first_name = nick_names.nick_names.get(name_parts[0], name_parts[0])
        middle_names = name_parts[1:]

        return first_name, middle_names, last_name, suffix
 
    def full_name(self):
        return " ".join([self.first_name] + self.middle_names + [self.last_name])

    def last_first(self):
        return " ".join([self.last_name + ","] + [self.first_name] + self.middle_names)

    def fn(self):
        return self.first_name

    def mns(self):
        return self.middle_names

    def ln(self):
        return self.last_name

    def name_variants(self):
        ret = set([self.full_name()])
        m_string = " ".join(self.mns())
        ret.add("%s %s" % (self.fn(), self.ln()))
        ret.add("%s %s" % (self.fn()[0], self.ln()))
        if self.mns():
            ret.add("%s %s %s" % (self.fn(), m_string, self.ln()))
            ret.add("%s %s %s" % (self.fn()[0], m_string, self.ln()))
        return ret

    def token(self):
        return "%s_%s" % (self.last_name, self.first_name[0])

    def drop_first_name(self):
        self.first_name = self.middle_names[0]
        self.middle_names = self.middle_names[1:]

    def repr_tsv(self):
        mn = " ".join(self.mns())
        name_tsv = "\t".join([self.fn(), mn, self.ln()])
        return "\t".join([self.article_id, self.author_id, name_tsv,])

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

