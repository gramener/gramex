'''

'''

import io
import os
import json
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
    folder = os.path.dirname(os.path.abspath(__file__))

    result = {}
    index_file = os.path.join(folder, 'search.json')
    if os.path.exists(index_file):
        with open(index_file, 'r') as handle:       # noqa: for Py2 & Py3 compatibility
            try:
                result = json.load(handle)
            except ValueError:
                pass

    for (path, frag), texts in markdown_index(folder).items():
        base = result.setdefault(path, {}).setdefault(frag, {})
        for text in texts:
            base.setdefault(text, 1)

    with open(index_file, 'w') as handle:           # noqa: for Py2 & Py3 compatibility
        json.dump(result, handle, ensure_ascii=True, sort_keys=True, indent=2)
