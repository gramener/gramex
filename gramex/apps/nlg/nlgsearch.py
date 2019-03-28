# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Search tools.
"""

from itertools import chain

import numpy as np
import pandas as pd
import six

from gramex.apps.nlg import nlgutils as utils
from gramex.apps.nlg.grammar import find_inflections

SEARCH_PRIORITIES = [
    {'type': 'ne'},  # A match which is a named entity gets the higest priority
    {'location': 'fh_args'},  # than one that is a formhandler arg
    {'location': 'colname'},  # than one that is a column name
    {'type': 'quant'},  # etc
    {'location': 'cell'}
]


def _sort_search_results(items, priorities=SEARCH_PRIORITIES):
    """
    Sort a list of search results by `priorities`.

    Parameters
    ----------
    items : dict
        Dictionary containing search results, where keys are tokens and values
        are lists of locations where the token was found. Preferably this should
        be a `DFSearchResults` object.
    priorities : list, optional
        List of rules that allow sorting of search results. A `rule` is any
        subset of a search result dictionary. Lower indices indicate higher priorities.

    Returns
    -------
    dict
        Prioritized search results - for each {token: search_matches} pair, sort
        search_matches such that a higher priority search result is enabled.
    """
    match_ix = [[six.viewitems(p) <= six.viewitems(item) for p in priorities] for item in items]
    min_match = [m.index(True) for m in match_ix]
    items[min_match.index(min(min_match))]['enabled'] = True
    return items


class DFSearchResults(dict):
    """A convenience wrapper around `dict` to collect search results.

    Different from `dict` in that values are always lists, and setting to
    existing key appends to the list."""

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
            if any([k in c for c in six.viewkeys(self) - {k}]):
                to_remove.append(k)
        for i in to_remove:
            del self[i]


class DFSearch(object):
    """Make a dataframe searchable."""

    def __init__(self, df, nlp=None, **kwargs):
        """Default constrictor.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to search.
        nlp : A `spacy.lang` model, optional
        """
        self.df = df
        # What do results contain?
        # A map of tokens to list of search results.
        self.results = DFSearchResults()
        if not nlp:
            nlp = utils.load_spacy_model()
        self.nlp = nlp
        self.matcher = kwargs.get('matcher', utils.make_np_matcher(self.nlp))

    def search(self, text, colname_fmt="df.columns[{}]",
               cell_fmt="df['{}'].iloc[{}]", **kwargs):
        """
        Search the dataframe.

        Parameters
        ----------
        text : str
            The text to search.
        colname_fmt : str, optional
            String format to describe dataframe columns in the search results,
            can be one of "df.columns[{}]" or "df[{}]".
        cell_fmt : str, optional
            String format to describe dataframe values in the search results.
            Can be one of "df.iloc[{}, {}]", "df.loc[{}, {}]", "df[{}][{}]", etc.

        Returns
        -------
        dict
            A dictionary who's keys are tokens from `text` found in
            the source dataframe, and values are a list of locations in the df
            where they are found.
        """
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
        """Find named entities in text, and search for them in the dataframe.

        Parameters
        ----------
        text : str
            The text to search.
        """
        self.doc = self.nlp(text)
        self.ents = utils.ner(self.doc, self.matcher)
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
        """Search the `.values` attribute of the dataframe for tokens in `text`."""
        kwargs['array'] = self.df.copy()
        return self._search_array(text, **kwargs)

    def search_columns(self, text, **kwargs):
        """Search df columns for tokens in `text`."""
        kwargs['array'] = self.df.columns
        return self._search_array(text, **kwargs)

    def search_quant(self, quants, nround=2, cell_fmt="df['{}'].iloc[{}]"):
        """Search the dataframe for a set of quantitative values.

        Parameters
        ----------
        quants : list / array like
            The values to search.
        nround : int, optional
            Numeric values in the dataframe are rounded to these many
            significant digits before searching.
        """
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
        """Search for tokens in text within an array.

        Parameters
        ----------
        text : str or spacy document
            Text to search
        array : array-like
            Array to search in.
        literal : bool, optional
            Whether to match tokens to values literally.
        case : bool, optional
            If true, run a case sensitive search.
        lemmatize : bool, optional
            If true (default), search on lemmas of tokens and values.
        nround : int, optional
            Significant digits used to round `array` before searching.

        Returns
        -------
        dict
            Mapping of tokens to a sequence of indices within `array`.

        Example
        -------
        >>> _search_array('3', np.arange(5))
        {'3': [2]}
        >>> df = pd.DataFrame(np.eye(3), columns='one punch man'.split())
        >>> _search_array('1', df.values)
        {'1': [(0, 0), (1, 1), (2, 2)]}
        >>> _search_array('punched man', df.columns)
        {'punched': [1], 'man': [2]}
        >>> _search_array('1 2 buckle my shoe', df.index)
        {'1': [1], '2': [2]}
        """
        if literal:
            # Expect text to be a list of strings, no preprocessing on anything.
            if not isinstance(text, list):
                raise TypeError('text is expected to be list of strs when literal=True.')
            valid_types = {float, int, six.text_type}
            if not set([type(c) for c in text]).issubset(valid_types):
                raise TypeError('text can contain only strings or numbers when literal=True.')
            tokens = {c: str(c) for c in text}
        elif lemmatize:
            tokens = {c.lemma_: c.text for c in self.nlp(text)}
            if array.ndim == 1:
                array = [c if isinstance(c, six.text_type) else six.u(c) for c in array]
                array = [self.nlp(c) for c in array]
                array = pd.Series([token.lemma_ for doc in array for token in doc])
            else:
                for col in array.columns[array.dtypes == np.dtype('O')]:
                    s = [c if isinstance(c, six.text_type) else six.u(c) for c in array[col]]
                    s = [self.nlp(c) for c in s]
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


def search_args(entities, args, lemmatized=True, fmt="fh_args['{}'][{}]",
                argkeys=('_sort', '_by', '_c')):
    """
    Search formhandler arguments, as parsed by g1, for a set of tokens.

    Parameters
    ----------
    entities : list
        list of named entities found in the source text
    args : dict
        FormHandler args as parsed by g1.url.parse(...).searchList
    lemmatized : bool, optional
        whether to search on lemmas of text values
    fmt : str, optional
        String format used to describe FormHandler arguments in the template
    argkeys : list, optional
        Formhandler argument keys to be considered for the search. Any key not
        present in this will be ignored.
        # TODO: Column names can be keys too!!

    Returns
    -------
    dict
        Mapping of entities / tokens to objects describing where they are found
        in Formhandler arguemnts. Each search result object has the following
        structure:
        {
            "type": "some token",
            "location": "fh_args",
            "tmpl": "fh_args['_by'][0]"  # The template that gets this token from fh_args
        }
    """
    nlp = utils.load_spacy_model()
    args = {k: v for k, v in args.items() if k in argkeys}
    search_res = {}
    ent_tokens = list(chain(*entities))
    for k, v in args.items():
        v = [t.lstrip('-') for t in v]
        # argtokens = list(chain(*[re.findall(r"\w+", f) for f in v]))
        argtokens = list(chain(*[nlp(c) for c in v]))
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


def templatize(text, args, df):
    """Construct a tornado template which regenerates some
    text from a dataframe and formhandler arguments.

    The pipeline consists of:
    1. cleaning the text and the dataframe
    2. searching the dataframe and FH args for tokens in the text
    3. detecting inflections on the tokens.

    Parameters
    ----------
    text : str
        Input text
    args : dict
        Formhandler arguments
    df : pd.DataFrame
        Source dataframe.

    Returns
    --------
    tuple
        of search results, cleaned text and token inflections. The webapp uses
        these to construct a tornado template.
    """
    text = six.u(text)
    args = {six.u(k): [six.u(c) for c in v] for k, v in args.items()}
    utils.load_spacy_model()
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
