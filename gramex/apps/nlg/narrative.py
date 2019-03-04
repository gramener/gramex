#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""WIP: The Narrative class."""


class Narrative(object):
    def __init__(self, sentences=None, conditions=None):
        if sentences is None:
            sentences = []
        self.sentences = sentences
        if conditions is None:
            conditions = []
        self.conditions = conditions

    @property
    def sdict(self):
        return {k: i for i, k in enumerate(self.sentences)}

    def templatize(self, sep="\n\n"):
        newsents = []
        for i, sent in enumerate(self.sentences):
            if str(i) in self.conditions:
                newsent = """
                {{ % if df.eval(\'{expr}\').any() % }}
                    {sent}
                {{ % end % }}
                """.format(
                    expr=self.conditions[str(i)], sent=sent
                )
            else:
                newsent = sent
            newsents.append(newsent)
        return sep.join(newsents)

    def append(self, sent):
        self.sentences.append(sent)

    add = append

    def prepend(self, sent):
        self.sentences.insert(0, sent)

    def insert(self, sent, ix):
        self.sentences.insert(ix, sent)

    def _move(self, key, pos):
        if isinstance(key, str):
            key = self.sdict[key]
        self.sentences.insert(key + pos, self.sentences.pop(key))

    def move_up(self, key):
        self._move(key, 1)

    def move_down(self, key):
        self._move(key, -1)
