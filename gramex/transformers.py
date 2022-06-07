import os.path as op
import pandas as pd
import transformers as trf
from datasets import Dataset
from gramex.config import app_log
from gramex import cache
from sklearn.metrics import roc_auc_score


DEFAULT_MODEL = DEFAULT_TOKENIZER = "distilbert-base-uncased-finetuned-sst-2-english"


def load_pretrained(klass, path, default, **kwargs):
    if op.isdir(path):
        try:
            app_log.info(f"Attempting to load {klass.__name__} from {path}")
            model = cache.open(path, klass.from_pretrained, **kwargs)
        except:  # NOQA: E722
            app_log.info(f"Falling back to default {klass.__name__}: {default}.")
            model = cache.open(default, klass.from_pretrained, **kwargs)
    else:
        app_log.info(f"{path} not found on disk; loading default...")
        model = klass.from_pretrained(default, **kwargs)
    return model


class BaseTransformer(object):
    def __init__(self, model=DEFAULT_MODEL, tokenizer=DEFAULT_TOKENIZER, **kwargs):
        self._model = model
        self._tokenizer = tokenizer
        self.model = load_pretrained(
            trf.AutoModelForSequenceClassification, model, DEFAULT_MODEL
        )
        self.tokenizer = load_pretrained(
            trf.AutoTokenizer, tokenizer, DEFAULT_TOKENIZER
        )
        self.pipeline = trf.pipeline(
            self.task, model=self.model, tokenizer=self.tokenizer
        )


class SentimentAnalysis(BaseTransformer):
    task = "sentiment-analysis"

    def fit(self, text, labels, model_path, **kwargs):
        if pd.api.types.is_object_dtype(labels):
            labels = labels.map(self.model.config.label2id.get)
        ds = Dataset.from_dict({"text": text, "label": labels})
        tokenized = ds.map(
            lambda x: self.tokenizer(x["text"], padding="max_length", truncation=True),
            batched=True,
        )
        train_args = trf.TrainingArguments(save_strategy="no", output_dir=model_path)
        trainer = trf.Trainer(
            model=self.model, train_dataset=tokenized, args=train_args
        )
        trainer.train()
        self.model.to("cpu")
        self.model.save_pretrained(op.join(model_path, "model"))
        self.tokenizer.save_pretrained(op.join(model_path, "tokenizer"))
        self.pipeline = trf.pipeline(
            self.task,
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def predict(self, text, **kwargs):
        text = text.tolist()
        predictions = self.pipeline(text)
        return [k["label"] for k in predictions]

    def score(self, X, y_true, **kwargs):   # noqa: N803
        y_true = [self.model.config.label2id[x] for x in y_true]
        y_pred = self.predict(X.squeeze("columns"))
        y_pred = [self.model.config.label2id[x] for x in y_pred]
        return roc_auc_score(y_true, y_pred)
