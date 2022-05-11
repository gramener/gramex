import gramex
import spacy
from typing import Optional


def load(model="en_core_web_sm") -> spacy.lang:
    return gramex.cache.open(model, spacy.load)


def remove_punctutation(doc: spacy.tokens.Doc) -> list[spacy.tokens.Token]:
    return [token for token in doc if not token.is_punct]


def remove_stopwords(doc: spacy.tokens.Doc) -> list[spacy.tokens.Token]:
    return [token for token in doc if not token.is_stop]


def lemmatize(doc: spacy.tokens.Doc) -> list[str]:
    return [token.lemma_ for token in doc]


def ner(doc: spacy.tokens.Doc, filter_labels: Optional[list[str]] = None) -> list[tuple[str, str]]:
    if not filter_labels:
        return [(ent.label_, ent.text) for ent in doc.ents]
    return [(ent.label_, ent.text) for ent in doc.ents if ent.label_ in filter_labels]


def noun_chunks(
    doc: spacy.tokens.Doc,
    matcher: Optional[spacy.matcher.Matcher] = None,
    matcher_label: Optional[str] = "ENTITY",
) -> list[spacy.tokens.Span]:
    if not matcher:
        return [c for c in doc.noun_chunks]
    spans = [
        spacy.tokens.Span(doc, start, end, label=matcher_label)
        for _, start, end in matcher(doc)
    ]
    spans = spacy.utils.filter_spans(spans)
    doc.set_ents(spans)
    return spans
