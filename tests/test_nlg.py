import os.path as op
import re
import unittest

import pandas as pd

from gramex.apps.nlg import grammar as g
from gramex.apps.nlg import nlgsearch as search, nlgutils as utils

nlp = utils.load_spacy_model()
matcher = utils.make_np_matcher(nlp)


class TestUtils(unittest.TestCase):

    def test_join_words(self):
        sent = 'The quick brown fox jumps over the lazy dog.'
        self.assertEqual(utils.join_words(sent), sent.rstrip('.'))
        self.assertEqual(utils.join_words(sent, ''), sent.rstrip('.').replace(' ', ''))
        self.assertEqual(utils.join_words('-Office supplies'), 'Office supplies')

    def test_sanitize_args(self):
        self.assertDictEqual(utils.sanitize_fh_args({'_sort': ['-Office supplies']}),
                             {'_sort': ['Office supplies']})

    @unittest.skip('NER is unstable.')
    def test_ner(self):
        nlp = utils.load_spacy_model()
        sent = nlp(
            u"""
            US President Donald Trump is an entrepreneur and
            used to run his own reality show named 'The Apprentice'."""
        )
        ents = utils.ner(sent, matcher)
        self.assertSetEqual(
            set([c.text for c in utils.unoverlap(ents)]),
            {
                "\'The Apprentice\'",
                "US President Donald Trump",
                "entrepreneur",
                "reality show"
            },
        )

    def test_sanitize_indices(self):
        self.assertEqual(utils.sanitize_indices((3, 3), 0), 0)
        self.assertEqual(utils.sanitize_indices((3, 3), 1), 1)
        self.assertEqual(utils.sanitize_indices((3, 3), 2), -1)
        self.assertEqual(utils.sanitize_indices((3, 3), 0, 1), 0)
        self.assertEqual(utils.sanitize_indices((3, 3), 1, 1), 1)
        self.assertEqual(utils.sanitize_indices((3, 3), 2, 1), -1)


class TestDFSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fpath = op.join(op.dirname(__file__), "actors.csv")
        cls.df = pd.read_csv(fpath, encoding='utf-8')
        cls.dfs = search.DFSearch(cls.df)

    def test__search_array(self):
        sent = u"The votes, names and ratings of artists."
        res = self.dfs._search_array(sent, self.df.columns, lemmatize=False)
        self.assertDictEqual(res, {'votes': 3})

        res = self.dfs._search_array(sent, self.df.columns)
        self.assertDictEqual(res, {'votes': 3, 'names': 1, 'ratings': 2})

        sent = u"The votes, NAME and ratings of artists."
        res = self.dfs._search_array(sent, self.df.columns,
                                     lemmatize=False)
        self.assertDictEqual(res, {'votes': 3, 'NAME': 1})
        res = self.dfs._search_array(sent, self.df.columns, lemmatize=False,
                                     case=True)
        self.assertDictEqual(res, {'votes': 3})

    def test_dfsearch_lemmatized(self):
        df = pd.DataFrame.from_dict(
            {
                "partner": ["Lata", "Asha", "Rafi"],
                "song": [20, 5, 15],
            }
        )
        sent = u"Kishore Kumar sang the most songs with Lata Mangeshkar."
        dfs = search.DFSearch(df)
        self.assertDictEqual(
            dfs.search(sent, lemmatize=True),
            {
                'songs': [{"location": "colname", "type": "token", "tmpl": "df.columns[1]"}],
                'Lata': [{'location': 'cell', 'tmpl': "df['partner'].iloc[0]", 'type': 'token'}],
            }
        )

    def test_search_df(self):
        self.df.sort_values("votes", ascending=False, inplace=True)
        self.df.reset_index(inplace=True, drop=True)
        dfs = search.DFSearch(self.df)
        sent = u"Spencer Tracy is the top voted actor."
        self.assertDictEqual(
            dfs.search(sent),
            {
                'Spencer Tracy': [
                    {'location': 'cell', 'tmpl': "df['name'].iloc[0]", 'type': 'ne'}
                ],
                'voted': [{'location': 'colname', 'tmpl': 'df.columns[-1]', 'type': 'token'}],
                'actor': [{'location': 'cell', 'tmpl': "df['category'].iloc[-4]", 'type': 'token'}]
            }
        )


class TestSearch(unittest.TestCase):
    def test_dfsearches(self):
        x = search.DFSearchResults()
        x['hello'] = 'world'
        x['hello'] = 'world'
        self.assertDictEqual(x, {'hello': ['world']})
        x = search.DFSearchResults()
        x['hello'] = 'world'
        x['hello'] = 'underworld'
        self.assertDictEqual(x, {'hello': ['world', 'underworld']})

    def test_search_args(self):
        args = {u"_sort": [u"-votes"]}
        nlp = utils.load_spacy_model()
        doc = nlp(u"James Stewart is the top voted actor.")
        ents = utils.ner(doc, matcher)
        self.assertDictEqual(
            search.search_args(ents, args),
            {
                "voted": {
                    "tmpl": "fh_args['_sort'][0]",
                    "type": "token",
                    "location": "fh_args"
                }
            }
        )

    def test_search_args_literal(self):
        args = {u"_sort": [u"-rating"]}
        nlp = utils.load_spacy_model()
        doc = nlp(u"James Stewart has the highest rating.")
        ents = utils.ner(doc, matcher)
        self.assertDictEqual(search.search_args(ents, args, lemmatized=False),
                             {'rating': {
                                 "tmpl": "fh_args['_sort'][0]",
                                 "location": "fh_args",
                                 "type": "token"}})

    def test_templatize(self):
        fpath = op.join(op.dirname(__file__), "actors.csv")
        df = pd.read_csv(fpath, encoding='utf-8')
        df.sort_values("votes", ascending=False, inplace=True)
        df.reset_index(inplace=True, drop=True)

        doc = """
        Spencer Tracy is the top voted actor, followed by Cary Grant.
        The least voted actress is Bette Davis, trailing at only 14 votes, followed by
        Ingrid Bergman at a rating of 0.29614.
        """
        ideal = """
        {{ df['name'].iloc[0] }} is the top {{ fh_args['_sort'][0] }}
        {{ df['category'].iloc[-4] }}, followed by {{ df['name'].iloc[1] }}.
        The least {{ fh_args['_sort'][0] }} {{ df['category'].iloc[-1] }} is
        {{ df['name'].iloc[-1] }}, trailing at only {{ df['votes'].iloc[-1] }}
        {{ df.columns[-1] }}, followed by {{ df['name'].iloc[-2] }} at a {{ df.columns[2] }}
        of {{ df['rating'].iloc[-2] }}.
        """
        args = {"_sort": ["-votes"]}
        tokenmap, text, inflections = search.templatize(doc, args, df)
        actual = text
        for token, tmpls in tokenmap.items():
            tmpl = [t for t in tmpls if t.get('enabled', False)][0]
            actual = actual.replace(token, '{{{{ {} }}}}'.format(tmpl['tmpl']))
        cleaner = lambda x: re.sub(r"\s+", " ", x)  # NOQA: E731
        self.assertEqual(*map(cleaner, (ideal, actual)))
        self.assertDictEqual(
            inflections,
            {
                'actor': [{'fe_name': 'Singularize', 'source': 'G', 'func_name': 'singular'}],
                'actress': [{'source': 'G', 'fe_name': 'Singularize', 'func_name': 'singular'}]
            }
            # Don't detect inflections until they can be processed without intervention
            # 'voted': [{'source': 'G', 'fe_name': 'Lemmatize', 'func_name': 'lemmatize'}]}
        )

    def test_search_sort(self):
        results = [
            {'tmpl': 'df.loc[0, "name"]', 'type': 'ne', 'location': 'cell'},
            {'tmpl': 'df.columns[0]', 'type': 'token', 'location': 'colname'},
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'fh_args'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[:1])

        results = [
            {'tmpl': 'df.columns[0]', 'type': 'token', 'location': 'colname'},
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'fh_args'},
            {'tmpl': 'df["foo"].iloc[0]', 'type': 'token', 'location': 'cell'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[1:2])

        results = [
            {'tmpl': 'df.columns[0]', 'type': 'token', 'location': 'colname'},
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'cell'},
            {'tmpl': 'df["foo"].iloc[0]', 'type': 'quant', 'location': 'cell'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[:1])

        results = [
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'cell'},
            {'tmpl': 'df["foo"].iloc[0]', 'type': 'quant', 'location': 'cell'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[1:])


class TestGrammar(unittest.TestCase):

    def test_is_plural(self):
        self.assertTrue(g.is_plural_noun(u"languages"))
        self.assertTrue(g.is_plural_noun(u"bacteria"))
        self.assertTrue(g.is_plural_noun(u"Office supplies"))

    def test_concatenate_items(self):
        self.assertEqual(g.concatenate_items("abc"), "a, b and c")
        self.assertEqual(g.concatenate_items([1, 2, 3], sep=""), "123")
        self.assertFalse(g.concatenate_items([]))

    def test_pluralize(self):
        self.assertEqual(g.plural(u"language"), "languages")
        self.assertEqual(g.plural(u"languages"), "languages")
        self.assertEqual(g.plural(u"bacterium"), "bacteria")
        self.assertEqual(g.plural(u"goose"), "geese")

    def test_singular(self):
        self.assertEqual(g.singular(u"languages"), "language")
        self.assertEqual(g.singular(u"language"), "language")
        self.assertEqual(g.singular(u"bacteria"), "bacterium")
        # self.assertEqual(g.singular("geese"), "goose"

    def test_pluralize_by(self):
        self.assertEqual(g.pluralize_by(u"language", [1, 2]), "languages")
        self.assertEqual(g.pluralize_by(u"languages", [1]), "language")
        self.assertEqual(g.pluralize_by(u"language", []), "language")
        self.assertEqual(g.pluralize_by(u"language", 1), "language")
        self.assertEqual(g.pluralize_by(u"language", 2), "languages")


if __name__ == '__main__':
    unittest.main()
