# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
import re

import six
from tornado.template import Template

from gramex.data import filter as grmfilter  # NOQA: F401

NP_RULES = {
    "NP1": [{"POS": "PROPN", "OP": "+"}],
    "NP2": [{"POS": "NOUN", "OP": "+"}],
    "NP3": [{"POS": "ADV", "OP": "+"}, {"POS": "VERB", "OP": "+"}],
    "NP4": [{"POS": "ADJ", "OP": "+"}, {"POS": "VERB", "OP": "+"}],
    "QUANT": [{"POS": "NUM", "OP": "+"}]
}

NARRATIVE_TEMPLATE = """
{% autoescape None %}
from nlg import grammar as G
from nlg import nlgutils as U
from tornado.template import Template as T
import pandas as pd

df = None  # set your dataframe here.
narrative = T(\"\"\"
              {{ tmpl }}
              \"\"\").generate(
              tornado_tmpl=True, orgdf=df, fh_args={{ fh_args }},
              G=G, U=U)
print(narrative)
"""

_spacy = {
    'model': False,
    'lemmatizer': False,
    'matcher': False
}


def load_spacy_model():
    """Load the spacy model when required."""
    if not _spacy['model']:
        from spacy import load
        nlp = load("en_core_web_sm")
        _spacy['model'] = nlp
    else:
        nlp = _spacy['model']
    return nlp


def get_lemmatizer():
    if not _spacy['lemmatizer']:
        from spacy.lang.en import LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES
        from spacy.lemmatizer import Lemmatizer
        lemmatizer = Lemmatizer(LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES)
        _spacy['lemmatizer'] = lemmatizer
    else:
        lemmatizer = _spacy['lemmatizer']
    return lemmatizer


def make_np_matcher(nlp, rules=NP_RULES):
    """Make a rule based noun phrase matcher.

    Parameters
    ----------
    nlp : `spacy.lang`
        The spacy model to use.
    rules : dict, optional
        Mapping of rule IDS to spacy attribute patterns, such that each mapping
        defines a noun phrase structure.

    Returns
    -------
    `spacy.matcher.Matcher`
    """
    if not _spacy['matcher']:
        from spacy.matcher import Matcher
        matcher = Matcher(nlp.vocab)
        for k, v in rules.items():
            matcher.add(k, None, v)
        _spacy['matcher'] = matcher
    else:
        matcher = _spacy['matcher']
    return matcher


def render_search_result(text, results, **kwargs):
    for token, tokenlist in results.items():
        tmpl = [t for t in tokenlist if t.get('enabled', False)][0]
        text = text.replace(token, '{{{{ {} }}}}'.format(tmpl['tmpl']))
    return Template(text).generate(**kwargs).decode('utf-8')


def join_words(x, sep=' '):
    return sep.join(re.findall(r'\w+', x, re.IGNORECASE))


class set_nlg_gramopt(object):  # noqa: class to be used as a decorator
    """Decorator for adding callables to grammar options of the webapp.
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, func):
        func.gramopt = True
        for k, v in self.kwargs.items():
            if not getattr(func, k, False):
                setattr(func, k, v)
        return func


def is_overlap(x, y):
    """Whether the token x is contained within any span in the sequence y."""
    if "NUM" in [c.pos_ for c in x]:
        return False
    return any([x.text in yy for yy in y])


def unoverlap(tokens):
    """From a set of tokens, remove all tokens that are contained within
    others."""
    textmap = {c.text: c for c in tokens}
    text_tokens = six.viewkeys(textmap)
    newtokens = []
    for token in text_tokens:
        if not is_overlap(textmap[token], text_tokens - {token}):
            newtokens.append(token)
    return [textmap[t] for t in newtokens]


def ner(doc, matcher, match_ids=False, remove_overlap=True):
    """Find all NEs and other nouns in a spacy doc.

    Parameters
    ----------
    doc: spacy.tokens.doc.Doc
        The document in which to search for entities.
    matcher: spacy.matcher.Matcher
        The rule based matcher to use for finding noun phrases.
    match_ids: list, optional
        IDs from the spacy matcher to filter from the matches.
    remove_overlap: bool, optional
        Whether to remove overlapping tokens from the result.

    Returns
    -------
    list
        List of spacy.token.span.Span objects.
    """
    entities = set()
    for span in doc.ents:
        newtokens = [c for c in span if not c.is_space]
        if newtokens:
            newspan = doc[newtokens[0].i: (newtokens[-1].i + 1)]
            entities.add(newspan)
    if not match_ids:
        entities.update([doc[start:end] for _, start, end in matcher(doc)])
    else:
        for m_id, start, end in matcher(doc):
            if matcher.vocab.strings[m_id] in match_ids:
                entities.add(doc[start:end])
    if remove_overlap:
        entities = unoverlap(entities)
    return entities


def sanitize_indices(shape, i, axis=0):
    n = shape[axis]
    if i <= n // 2:
        return i
    return -(n - i)


def sanitize_text(text, d_round=2):
    """All text cleaning and standardization logic goes here."""
    nums = re.findall(r"\d+\.\d+", text)
    for num in nums:
        text = re.sub(num, str(round(float(num), d_round)), text)
    return text


def sanitize_df(df, d_round=2, **options):
    """All dataframe cleaning and standardizing logic goes here."""
    for c in df.columns[df.dtypes == float]:
        df[c] = df[c].round(d_round)
    return df


def sanitize_fh_args(args, func=join_words):
    for k, v in args.items():
        args[k] = [join_words(x) for x in v]
    return args


def add_html_styling(template, style):
    """Add HTML styling spans to template elements.

    Parameters
    ----------
    template : str
        A tornado template
    style : dict or bool
        If False, no styling is added.
        If True, a default bgcolor is added to template variables.
        If dict, expected to contain HTML span styling elements.

    Returns
    -------
    str
        Modified template with each variabled stylized.

    Example
    -------
    >>> t = 'Hello, {{ name }}!'
    >>> add_html_styling(t, True)
    'Hello, <span style="background-color:#c8f442">{{ name }}</span>!'
    >>> add_html_styling(t, False)
    'Hello, {{ name }}!'
    >>> add_html_style(t, {'background-color': '#ffffff', 'font-family': 'monospace'})
    'Hello, <span style="background-color:#c8f442;font-family:monospace">{{ name }}</span>!'
    """

    if not style:
        return template
    pattern = re.compile(r'\{\{[^\{\}]+\}\}')
    if isinstance(style, dict):
        # convert the style dict into a stylized HTML span
        spanstyle = ";".join(['{}:{}'.format(k, v) for k, v in style.items()])
    else:
        spanstyle = "background-color:#c8f442"
    for m in re.finditer(pattern, template):
        token = m.group()
        repl = '<span style="{ss}">{token}</span>'.format(
            ss=spanstyle, token=token)
        template = re.sub(re.escape(token), repl, template, 1)
    return '<p>{template}</p>'.format(template=template)
