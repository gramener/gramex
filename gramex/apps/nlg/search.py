#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Search tools.
"""

import re
from itertools import chain

import numpy as np
import pandas as pd
from spacy import load
from spacy.matcher import PhraseMatcher

from gramex.apps.nlg import utils
from gramex.apps.nlg.grammar import concatenate_items, find_inflections

default_nlp = load("en_core_web_sm")

SEARCH_PRIORITIES = [
    {'type': 'ne'},  # A match which is an NE gets the higest priority
    {'location': 'fh_args'},  # then one that is a formhandler arg
    {'location': 'colname'},  # then one that is a column name
    {'type': 'quant'},  # etc
    {'location': 'cell'}
]


def _sort_search_results(items, priorities=SEARCH_PRIORITIES):
    """Sort a list of search results by `priorities`."""
    match_ix = [[p.items() <= item.items() for p in priorities] for item in items]
    min_match = [m.index(True) for m in match_ix]
    items[min_match.index(min(min_match))]['enabled'] = True
    return items


class DFSearchResults(dict):
    """A convenience wrapper around `dict` to collect search results."""

    def __setitem__(self, key, value):
        if key not in self:
            super(DFSearchResults, self).__setitem__(key, [value])
        elif self[key][0] != value:
            self[key].append(value)

    def update(self, other):
        # Needed because the default update method doesn't seem to use setitem
        for k, v in other.items():
            self[k] = v

    def clean(self):
        """Sort the search results for each token by priority and un-overlap tokens."""
        for k, v in self.items():
            _sort_search_results(v)
        # unoverlap the keys
        to_remove = []
        for k in self:
            if any([k in c for c in self.keys() - {k}]):
                to_remove.append(k)
        for i in to_remove:
            del self[i]


class DFSearch(object):

    def __init__(self, df, nlp=default_nlp, **kwargs):
        self.df = df
        # What do results contain?
        # A map of tokens to pandas slices
        self.results = DFSearchResults()
        self.nlp = nlp

    def search(self, text, colname_fmt="df.columns[{}]",
               cell_fmt="df['{}'].iloc[{}]", **kwargs):
        self.search_nes(text)

        for token, ix in self.search_columns(text, **kwargs).items():
            ix = utils.sanitize_indices(self.df.shape, ix, 1)
            self.results[token] = {'location': 'colname', 'tmpl': colname_fmt.format(ix),
                                   'type': 'token'}

        for token, (x, y) in self.search_table(text, **kwargs).items():
            x = utils.sanitize_indices(self.df.shape, x, 0)
            y = utils.sanitize_indices(self.df.shape, y, 1)
            self.results[token] = {
                'location': "cell", 'tmpl': cell_fmt.format(self.df.columns[y], x),
                'type': 'token'}
        self.search_quant([c.text for c in self.doc if c.pos_ == 'NUM'])
        return self.results

    def search_nes(self, text, colname_fmt="df.columns[{}]", cell_fmt="df['{}'].iloc[{}]"):
        self.doc = self.nlp(text)
        self.ents = utils.ner(self.doc)
        ents = [c.text for c in self.ents]
        for token, ix in self.search_columns(ents, literal=True).items():
            ix = utils.sanitize_indices(self.df.shape, ix, 1)
            self.results[token] = {
                'location': "colname",
                'tmpl': colname_fmt.format(ix), 'type': 'ne'
            }
        for token, (x, y) in self.search_table(ents, literal=True).items():
            x = utils.sanitize_indices(self.df.shape, x, 0)
            y = utils.sanitize_indices(self.df.shape, y, 1)
            self.results[token] = {
                'location': "cell",
                'tmpl': cell_fmt.format(self.df.columns[y], x), 'type': 'ne'}

    def search_table(self, text, **kwargs):
        kwargs['array'] = self.df.copy()
        return self._search_array(text, **kwargs)

    def search_columns(self, text, **kwargs):
        kwargs['array'] = self.df.columns
        return self._search_array(text, **kwargs)

    def search_quant(self, quants, nround=2, cell_fmt="df['{}'].iloc[{}]"):
        dfclean = utils.sanitize_df(self.df, nround)
        quants = np.array(quants)
        n_quant = quants.astype('float').round(2)
        for x, y in zip(*dfclean.isin(n_quant).values.nonzero()):
            x = utils.sanitize_indices(dfclean.shape, x, 0)
            y = utils.sanitize_indices(dfclean.shape, y, 1)
            tk = quants[n_quant == dfclean.iloc[x, y]][0].item()
            self.results[tk] = {
                'location': "cell", 'tmpl': cell_fmt.format(self.df.columns[y], x),
                'type': 'quant'}

    def _search_array(self, text, array, literal=False,
                      case=False, lemmatize=True, nround=2):
        """Search for tokens in text within a pandas array.
        Return {token: array_int_index}"""
        if literal:
            # Expect text to be a list of strings, no preprocessing on anything.
            if not isinstance(text, list):
                raise TypeError('text is expected to be list of strs when literal=True.')
            if not set([type(c) for c in text]).issubset({str, float, int}):
                raise TypeError('text can contain only strings or numbers when literal=True.')
            tokens = {c: str(c) for c in text}
        elif lemmatize:
            tokens = {c.lemma_: c.text for c in self.nlp(text)}
            if array.ndim == 1:
                array = [self.nlp(c) for c in array]
                array = pd.Series([token.lemma_ for doc in array for token in doc])
            else:
                for col in array.columns[array.dtypes == np.dtype('O')]:
                    s = [self.nlp(c) for c in array[col]]
                    try:
                        array[col] = [token.lemma_ for doc in s for token in doc]
                    except ValueError:
                        # You cannot lemmatize columns that have multi-word values
                        if not case:  # still need to respect the `case` param
                            array[col] = array[col].str.lower()
        else:
            if not case:
                tokens = {c.text.lower(): c.text for c in self.nlp(text)}
                if array.ndim == 1:
                    array = array.str.lower()
                else:
                    for col in array.columns[array.dtypes == np.dtype('O')]:
                        array[col] = array[col].str.lower()
            else:
                tokens = {c.text: c.text for c in self.nlp(text)}
        mask = array.isin(tokens.keys())
        if mask.ndim == 1:
            if mask.any():
                ix = mask.nonzero()[0]
                return {tokens[array[i]]: i for i in ix}
            return {}
        else:
            if mask.any().any():
                ix, iy = mask.values.nonzero()
                return {tokens[array.iloc[x, y]]: (x, y) for x, y in zip(ix, iy)}
        return {}


def search_concatenations(text, df):
    doc = default_nlp(text)
    matcher = PhraseMatcher(default_nlp.vocab)
    patterns = []
    for _, series in df.items():
        if series.dtype == np.dtype('O'):
            patterns.extend([default_nlp(x) for x in series])
    matcher.add("cell", None, *patterns)
    spans = []
    for _, start, end in matcher(doc):
        spans.append(doc[start:end].text)
    ideal = concatenate_items(spans)
    if ideal not in text:
        return ''
    mask = df.isin(spans)
    if mask.sum().sum() < 2:
        return ''
    # search for columns:
    col = df.columns[mask.any(0)][0]
    y = mask[col].nonzero()[0]
    if set(np.diff(y)) == {1}:
        return {ideal: "df.iloc[{}:{}, '{}']".format(y.min(), y.max(), col)}


def lemmatized_df_search(x, y, fmt_string="df.columns[{}]"):
    search_res = {}
    tokens = list(chain(*x))
    colnames = list(chain(*[default_nlp(c) for c in y]))
    for i, xx in enumerate(colnames):
        for yy in tokens:
            if xx.lemma_ == yy.lemma_:
                search_res[yy.text] = fmt_string.format(i)
    return search_res


def search_args(entities, args, lemmatized=True, fmt="fh_args['{}'][{}]",
                argkeys=('_sort', '_by')):
    """
    Search formhandler arguments.

    Parameters
    ----------
    entities : list
        list of spacyy entities
    args : Formhandler args
        [description]
    lemmatized : bool, optional
        whether to lemmatize search (the default is True, which [default_description])
    fmt : str, optional
        format used in the template (the default is "args['{}'][{}]", which [default_description])
    argkeys : list, optional
        keys to be considered for the search (the default is None, which [default_description])

    Returns
    -------
    [type]
        [description]
    """
    args = {k: v for k, v in args.items() if k in argkeys}
    search_res = {}
    ent_tokens = list(chain(*entities))
    for k, v in args.items():
        # key = k.lstrip("?")
        argtokens = list(chain(*[re.findall(r"\w+", f) for f in v]))
        argtokens = list(chain(*[default_nlp(c) for c in argtokens]))
        for i, x in enumerate(argtokens):
            for y in ent_tokens:
                if lemmatized:
                    if x.lemma_ == y.lemma_:
                        search_res[y.text] = {
                            'type': 'token', 'tmpl': fmt.format(k, i),
                            'location': 'fh_args'}
                else:
                    if x.text == y.text:
                        search_res[y.text] = {
                            'type': 'token', 'tmpl': fmt.format(k, i),
                            'location': 'fh_args'}
    return search_res


def search_df(tokens, df):
    """Search a dataframe for tokens and return the coordinates."""
    search_res = {}
    txt_tokens = np.array([c.text for c in tokens])
    coltype = df.columns.dtype
    ixtype = df.index.dtype

    # search in columns
    column_ix = np.arange(df.shape[1])[df.columns.astype(str).isin(txt_tokens)]
    for ix in column_ix:
        token = df.columns[ix]
        ix = utils.sanitize_indices(df.shape, ix, 1)
        search_res[token] = "df.columns[{}]".format(ix)

    # search in index
    index_ix = df.index.astype(str).isin(txt_tokens)
    for token in df.index[index_ix]:
        if token not in search_res:
            if ixtype == np.dtype("O"):
                indexer = "df.loc['{}']".format(token)
            else:
                indexer = "df.loc[{}]".format(token)
            search_res[token] = indexer

    # search in table
    for token in txt_tokens:
        if token not in search_res:
            mask = df.values.astype(str) == token
            try:
                column = df.columns[mask.sum(0).astype(bool)][0]
                # don't sanitize column
                index = df.index[mask.sum(1).astype(bool)][0]
                index = utils.sanitize_indices(df.shape, index, 0)
            except IndexError:
                continue
            if coltype == np.dtype("O"):
                col_indexer = "'{}'".format(column)
            else:
                col_indexer = str(column)
            if ixtype == np.dtype("O"):
                ix_indexer = "'{}'".format(index)
            else:
                ix_indexer = str(index)
            search_res[token] = "df.iloc[{}][{}]".format(ix_indexer, col_indexer)

    unfound = [token for token in tokens if token.text not in search_res]
    search_res.update(lemmatized_df_search(unfound, df.columns))
    return search_res


def templatize(text, args, df):
    """Process a piece of text and templatize it according to a dataframe."""
    clean_text = utils.sanitize_text(text)
    args = utils.sanitize_fh_args(args)
    dfs = DFSearch(df)
    dfix = dfs.search(clean_text)
    dfix.update(search_args(dfs.ents, args))
    dfix.clean()
    inflections = find_inflections(clean_text, dfix, args, df)
    _infl = {}
    for token, funcs in inflections.items():
        _infl[token] = []
        for func in funcs:
            _infl[token].append({
                'source': func.source,
                'fe_name': func.fe_name,
                'func_name': func.__name__
            })
    return dfix, clean_text, _infl
