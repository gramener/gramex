'''
Run `python search.py` to auto-update search.json from the README.md headers.
You can also manually add any page > heading-fragment > keyword with a value
other than -1. For example,

    "apps": {
      "creating-apps": {
        "Creating apps": -1,    // Already exists
        "Cloning apps": 2,      // Manually added with a value other than -1
      },

'''

import io
import os
import json
import logging
import markdown
from orderedattrdict import DefaultAttrDict
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class IndexerTreeProcessor(Treeprocessor):
    def run(self, root):
        self.markdown.index = []
        self.markdown.index.append(('', self.markdown.Meta['title'][0]))
        for el in root.findall('*'):
            if el.get('id'):
                text = el.text if el.text else el.findtext('*')[0]
                self.markdown.index.append((el.get('id'), text))


class IndexerExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors.add('indexer', IndexerTreeProcessor(md), '>toc')


def readme_files(folder):
    os.chdir(folder)
    for root, dirs, files in os.walk('.'):
        if '__pycache__' not in root and 'node_modules' not in root:
            for file in files:
                if file.lower() == 'readme.md':
                    yield root, file


def markdown_index(folder):
    result = DefaultAttrDict(set)
    for root, file in readme_files(folder):
        basename = os.path.basename(root)
        if basename == '.':
            continue
        with io.open(os.path.join(root, file), encoding='utf-8') as handle:
            md = markdown.Markdown(extensions=[
                'markdown.extensions.toc',
                'markdown.extensions.meta',
                IndexerExtension(),
            ])
            md.convert(handle.read())
            for frag, text in md.index:
                result[basename, frag].add(text)
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    folder = os.path.dirname(os.path.abspath(__file__))

    result = {}
    index_file = os.path.join(folder, 'search.json')
    if os.path.exists(index_file):
        with open(index_file, 'r') as handle:       # noqa: for Py2 & Py3 compatibility
            try:
                result = json.load(handle)
            except ValueError:
                pass

    found = set()
    default_val = -1
    # Add items from the Markdown files
    for (path, frag), texts in markdown_index(os.path.join(folder, '..')).items():
        base = result.setdefault(path, {}).setdefault(frag, {})
        for text in texts:
            base.setdefault(text, default_val)
            found.add((path, frag, text))

    # Remove default items not found
    for path in list(result.keys()):
        for frag in list(result[path].keys()):
            for text in list(result[path][frag].keys()):
                if (path, frag, text) not in found:
                    if result[path][frag][text] == default_val:
                        logging.info('Deleting %s - %s - %s', path, frag, text)
                        del result[path][frag][text]
                    else:
                        logging.info('Retaining %s - %s - %s', path, frag, text)

    # Save the search index. This only works in Python 3
    with io.open(index_file, 'w', encoding='utf-8', newline='') as handle:
        json.dump(result, handle, ensure_ascii=True, sort_keys=True, indent=2)
