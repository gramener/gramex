import io
import os
import requests
from gramex import cache
from tornado.web import HTTPError
from gramex.config import variables
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem.porter import PorterStemmer

sheet_id = '1HLndjr3jpbDbGFoJ8e3fF26ib4ES_2glKpmm78j5YuQ'
file_name = 'speech.xlsx'
guide_dir = os.path.join(variables['GRAMEXDATA'], 'apps', 'guide')
file_path = os.path.join(guide_dir, file_name)
stemmer = PorterStemmer()
vectorizer = TfidfVectorizer(stop_words='english')


def reload(handler):
    '''download latest excel data'''
    url = 'https://docs.google.com/spreadsheets/d/{0}/export?format=xlsx'.format(sheet_id)
    r = requests.get(url)
    if not os.path.isdir(guide_dir):
        os.mkdir(guide_dir)
    try:
        with io.open(file_path, 'wb') as f:
            f.write(r.content)
        handler.redirect('.?refreshed')
    except IOError:
        raise HTTPError("Couldn't open or write to file (%s)." % file_path)


def suggestion(handler):
    '''first 3 questions as suggestion'''
    return cache.open(file_path).sample(3)['Question'].to_json(orient='values')


def get_answer(handler):
    '''getting answer '''
    text = handler.get_arg('q', '')
    df = cache.open(file_path)
    tfidf = vectorizer.fit_transform(stem(s) for s in [text] + df['Question'].values.tolist())
    similarity = cosine_similarity(tfidf[0:1], tfidf[1:])[0]
    top_index = similarity.argmax()
    return {
        'similarity': similarity[top_index],
        'question': df['Question'][top_index],
        'answer': df['Answer'][top_index]
    }


def stem(sentence):
    return ' '.join(stemmer.stem(word) for word in sentence.split())
