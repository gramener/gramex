import os.path as op
from typing import List
import pandas as pd
import spacy
import transformers as trf
from datasets import Dataset, load_metric
from gramex.config import app_log
from gramex import cache
from sklearn.metrics import roc_auc_score


_CACHE = {}


def biluo2iob(tags: List[str]) -> List[str]:
    """Convert BILOU tags to IOB tags.

    spaCy insists on BILOU tags, but most transformers models use IOB tags.

    Parameters
    ----------
    tags : list
        List of BILOU tags

    Returns
    -------
    list
        List of IOB tags.

    Example
    -------
    >>> #      "Joe       R       Biden    is   President of  the  United   States   ."
    >>> tags = ['B-PER', 'I-PER', 'L-PER', 'O', 'U-PER', 'O', 'O', 'B-LOC', 'L-LOC', 'O']
    >>> biluo2iob(tags)
    ['B-PER', 'I-PER', 'I-PER', 'O', 'B-PER', 'O', 'O', 'B-LOC', 'I-LOC', 'O']
    """
    # Replace L
    tags = [t.replace("L-", "I-") for t in tags]
    # Replace U
    tags = [t.replace("U-", "B-") for t in tags]
    return tags


def offsets2iob(text: spacy.tokens.Doc, entities: List[dict]) -> List[str]:
    """Convert named entity offsets to a sequence of IOB tags.

    Parameters
    ----------
    text : spacy.tokens.Doc
        spaCy document of the original text
    entities : list
        Named entities present in the document as a list of dicts.
        Each dict represents one named entity and must contain three keys:
        1. "start": the start offset of the entity
        2. "end": the end offset of the entity
        3. "label": the label of the entity

    Returns
    -------
    list
        A list of IOB tags for the document.

    Example
    -------
    >>> import spacy
    >>> nlp = load('en')
    >>> doc = nlp('Narendra Modi is the PM of India.')
    >>> entities = [{'start': 0, 'end': 13, 'label': 'PER'},
    ...             {'start': 27, 'end': 32, 'label': 'LOC'}]
    >>> offsets2iob(doc, entities)
    ['B-PER', 'I-PER', 'O', 'O', 'O', 'O', 'B-LOC', 'O']
    """
    entities = [(ent["start"], ent["end"], ent["label"]) for ent in entities]
    tags = spacy.training.offsets_to_biluo_tags(text, entities)
    return biluo2iob(tags)


def tokenize_and_align_labels(examples, tokenizer):
    tokenized_inputs = tokenizer(examples["text"], truncation=True, is_split_into_words=True)

    labels = []
    for i, label in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)  # Map tokens to their respective word.
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:  # Set the special tokens to -100.
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:  # Only label the first token of a given word.
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs


def load_pretrained(klass, path, default, **kwargs):
    if op.isdir(path):
        try:
            app_log.info(f"Attempting to load {klass.__name__} from {path}")
            model = cache.open(path, klass.from_pretrained, **kwargs)
        except Exception:
            app_log.info(f"Falling back to default {klass.__name__}: {default}.")
            model = cache.open(default, klass.from_pretrained, **kwargs)
    else:
        app_log.info(f"{path} not found on disk; loading default...")
        key = klass.__name__ + default
        if key in _CACHE:
            model = _CACHE[key]
        else:
            model = _CACHE[key] = klass.from_pretrained(default, **kwargs)
    return model


class BaseTransformer:
    def __init__(self, model=None, tokenizer=None, **kwargs):
        if model is None:
            model = self.DEFAULT_MODEL
        if tokenizer is None:
            tokenizer = self.DEFAULT_TOKENIZER
        self._model = model
        self._tokenizer = tokenizer
        self.model = load_pretrained(self.AUTO_CLASS, model, self.DEFAULT_MODEL)
        self.tokenizer = load_pretrained(trf.AutoTokenizer, tokenizer, self.DEFAULT_TOKENIZER)
        self.pipeline_kwargs = kwargs
        self.pipeline = trf.pipeline(
            self.task, model=self.model, tokenizer=self.tokenizer, **kwargs
        )

    def post_train(self, model_path):
        """Move the model to the CPU, save it with the tokenizer, recreate the pipeline."""
        self.model.to("cpu")
        self.model.save_pretrained(op.join(model_path, "model"))
        self.tokenizer.save_pretrained(op.join(model_path, "tokenizer"))
        self.pipeline = trf.pipeline(
            self.task,
            model=self.model,
            tokenizer=self.tokenizer,
            **self.pipeline_kwargs,
        )


class SentimentAnalysis(BaseTransformer):
    task = "sentiment-analysis"
    DEFAULT_MODEL = DEFAULT_TOKENIZER = "distilbert-base-uncased-finetuned-sst-2-english"
    AUTO_CLASS = trf.AutoModelForSequenceClassification

    def fit(self, text, labels, model_path, **kwargs):
        if pd.api.types.is_object_dtype(labels):
            labels = labels.map(self.model.config.label2id.get)
        ds = Dataset.from_dict({"text": text, "label": labels})
        tokenized = ds.map(
            lambda x: self.tokenizer(x["text"], padding="max_length", truncation=True),
            batched=True,
        )
        train_args = trf.TrainingArguments(save_strategy="no", output_dir=model_path)
        trainer = trf.Trainer(model=self.model, train_dataset=tokenized, args=train_args)
        trainer.train()
        self.post_train(model_path)

    def predict(self, text, **kwargs):
        text = text.tolist()
        predictions = self.pipeline(text)
        return [k["label"] for k in predictions]

    def score(self, X, y_true, **kwargs):  # noqa: N803
        y_true = [self.model.config.label2id[x] for x in y_true]
        y_pred = self.predict(X.squeeze("columns"))
        y_pred = [self.model.config.label2id[x] for x in y_pred]
        return roc_auc_score(y_true, y_pred)


class NER(BaseTransformer):
    task = "ner"
    DEFAULT_TOKENIZER = DEFAULT_MODEL = "dbmdz/bert-large-cased-finetuned-conll03-english"
    AUTO_CLASS = trf.AutoModelForTokenClassification

    def __init__(self, model=None, tokenizer=None, **kwargs):
        self.nlp = spacy.blank("en")
        super(NER, self).__init__(
            model=model, tokenizer=tokenizer, aggregation_strategy="first", **kwargs
        )

    @property
    def labels(self):
        return {k.split("-")[-1] for k in self.model.config.label2id}

    def predict(self, text, **kwargs):
        text = text.tolist()
        return self.pipeline(text)

    def score(self, X, y_true, **kwargs):
        try:
            metric = load_metric("seqeval")
        except ImportError:
            app_log.error("Could not load the seqeval metric. Scoring not supported.")
            return 0
        # Get references and predictions
        X = X.squeeze("columns")
        predictions = self.predict(X)
        for pred in predictions:
            for ent in pred:
                ent.update({"label": ent.pop("entity_group")})
        preds = []
        refs = []
        for doc, pred, ref in zip(self.nlp.pipe(X.tolist()), predictions, y_true):
            preds.append(offsets2iob(doc, pred))
            refs.append(offsets2iob(doc, ref))
        metrics = metric.compute(references=refs, predictions=preds)
        return pd.DataFrame({k: v for k, v in metrics.items() if k in self.labels}).reset_index()

    def fit(self, text, labels, model_path, **kwargs):
        texts = []
        ner_tags = []
        for doc, ents in zip(self.nlp.pipe(text.tolist()), labels):
            texts.append([t.text for t in doc])
            ner_tags.append(offsets2iob(doc, ents))

        label2id = self.model.config.label2id
        ner_tags = [[label2id.get(k, 0) for k in tags] for tags in ner_tags]

        dataset = Dataset.from_dict({"text": texts, "ner_tags": ner_tags})
        tokenized = dataset.map(
            lambda x: tokenize_and_align_labels(x, self.tokenizer), batched=True
        )
        collator = trf.DataCollatorForTokenClassification(tokenizer=self.tokenizer)
        args = trf.TrainingArguments(
            save_strategy="no", output_dir=model_path, evaluation_strategy="epoch"
        )
        trainer = trf.Trainer(
            model=self.model,
            args=args,
            train_dataset=tokenized,
            eval_dataset=tokenized,
            tokenizer=self.tokenizer,
            data_collator=collator,
        )
        trainer.train()
        self.post_train(model_path)
