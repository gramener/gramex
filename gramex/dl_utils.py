from torch.utils.data import Dataset
from torch import tensor


class SentimentDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)
