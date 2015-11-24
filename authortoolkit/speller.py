import re
import collections
import utils


class Speller():
    alphabet = 'abcdefghijklmnopqrstuvwxyz-'

    def __init__(self, vocabulary):
        self.nwords = vocabulary

    def edits1(self, word):
        s = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [a + b[1:] for a, b in s if b]
        transposes = [a + b[1] + b[0] + b[2:] for a, b in s if len(b)>1]
        replaces = [a + c + b[1:] for a, b in s for c in self.alphabet if b]
        inserts = [a + c + b for a, b in s for c in self.alphabet]
        return set(deletes + transposes + replaces + inserts)

    def known(self, words):
        return set(w for w in words if w in self.nwords)

    def candidates(self, word):
        candidates = self.known(self.edits1(word))
        return [c for c in candidates if c!= word]


class SpaceSpeller(Speller):
    def __init__(self, vocabulary):
        Speller.__init__(self, vocabulary)
        self.alphabet += ' '

