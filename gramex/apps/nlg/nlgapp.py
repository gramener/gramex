# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Module for gramex exposure. This shouldn't be imported anywhere, only for use
with gramex.
"""
import json
import os
import os.path as op
from six.moves.urllib import parse

import pandas as pd
from tornado.template import Template

from gramex.config import variables
from gramex.apps.nlg import grammar
from gramex.apps.nlg import templatize
from gramex.apps.nlg import nlgutils as utils

DATAFILE_EXTS = {'.csv', '.xls', '.xlsx', '.tsv'}

grx_data_dir = variables['GRAMEXDATA']
nlg_path = op.join(grx_data_dir, 'nlg')

if not op.isdir(nlg_path):
    os.mkdir(nlg_path)



def get_user_dir(handler):
    if getattr(handler, 'current_user', False):
        dirpath = op.join(nlg_path, handler.current_user.id)
    else:
        dirpath = op.join(nlg_path, 'anonymous')
    return dirpath


def render_live_template(handler):
    """Given a narrative ID and df records, render the template."""
    orgdf = get_original_df(handler)
    nrid = handler.args['nrid'][0]
    if not nrid.endswith('.json'):
        nrid += '.json'
    data = json.loads(handler.args['data'][0])
    df = pd.DataFrame.from_records(data)
    nrpath = op.join(nlg_path, handler.current_user.id, nrid)
    with open(nrpath, 'r') as fout:  # noqa: No encoding for json
        templates = json.load(fout)
    narratives = []
    style = json.loads(handler.args['style'][0])
    for t in templates['config']:
        tmpl = utils.add_html_styling(t['template'], style)
        s = Template(tmpl).generate(df=df, fh_args=t.get('fh_args', {}),
                                    G=grammar, U=utils, orgdf=orgdf)
        rendered = s.decode('utf8')
        narratives.append(rendered)
    return '\n'.join(narratives)


def get_original_df(handler):
    """Get the original dataframe which was uploaded to the webapp."""
    data_dir = get_user_dir(handler)
    with open(op.join(data_dir, 'meta.cfg'), 'r') as fout:  # noqa: No encoding for json
        meta = json.load(fout)
    dataset_path = op.join(data_dir, meta['dsid'])
    return pd.read_csv(dataset_path, encoding='utf-8')


def render_template(handler):
    """Render a set of templates against a dataframe and formhandler actions on it."""
    orgdf = get_original_df(handler)
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    if not payload:
        payload = json.loads(handler.request.body.decode("utf8"))
        fh_args = payload['args']
        templates = payload['template']
        df = pd.DataFrame.from_records(payload['data'])
    else:
        payload = dict(payload)
        fh_args = json.loads(payload.get("args", {}))
        templates = json.loads(payload["template"])
        df = pd.read_json(payload["data"], orient="records")
    # fh_args = {k: [x.lstrip('-') for x in v] for k, v in fh_args.items()}
    resp = []
    for t in templates:
        rendered = Template(t).generate(
            orgdf=orgdf, df=df, fh_args=fh_args, G=grammar, U=utils).decode('utf8')
        rendered = rendered.replace('-', '')
        # grmerr = utils.check_grammar(rendered)
        resp.append({'text': rendered})  # , 'grmerr': grmerr})
    return json.dumps(resp)


def process_template(handler):
    """Process English text in the context of a df and formhandler arguments
    to templatize it."""
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    payload = dict(payload)
    text = json.loads(payload["text"])
    df = pd.read_json(payload["data"], orient="records")
    args = json.loads(payload.get("args", {}))
    if args is None:
        args = {}
    resp = []
    for t in text:
        # grammar_errors = yield utils.check_grammar(t)
        replacements, t, infl = templatize(t, args.copy(), df)
        resp.append({
            "text": t, "tokenmap": replacements, 'inflections': infl,
            "fh_args": args, "setFHArgs": False,
            # "grmerr": json.loads(grammar_errors.decode('utf8'))['matches']
        })
    return json.dumps(resp)


def read_current_config(handler):
    """Read the current data and narrative IDs written to the session file."""
    user_dir = get_user_dir(handler)
    meta_path = op.join(user_dir, 'meta.cfg')
    if not op.isdir(user_dir):
        os.mkdir(user_dir)
    if not op.isfile(meta_path):
        return {}
    with open(meta_path, 'r') as fout:  # noqa: No encoding for json
        meta = json.load(fout)
    return meta


def get_dataset_files(handler):
    """Get all filenames uploaded by the user.

    Parameters
    ----------
    handler : tornado.RequestHandler

    Returns
    -------
    list
        List of filenames.
    """
    files = []
    if getattr(handler, 'current_user', None):
        user_dir = op.join(nlg_path, handler.current_user.id)
        if op.isdir(user_dir):
            allfiles = os.listdir(user_dir)
            files = [f for f in allfiles if op.splitext(f)[-1].lower() in DATAFILE_EXTS]
    return files


def get_narrative_config_files(handler):
    """Get list of narrative config files generated by the user.

    Parameters
    ----------
    handler : tornado.RequestHandler

    Returns
    -------
    list
        List of narrative configurations.
    """
    files = []
    if getattr(handler, 'current_user', None):
        user_dir = op.join(nlg_path, handler.current_user.id)
        if op.isdir(user_dir):
            files = [f for f in os.listdir(user_dir) if f.endswith('.json')]
    return files


def download_config(handler):
    """Download the current narrative config as JSON."""
    payload = {}
    payload['config'] = json.loads(parse.unquote(handler.args['config'][0]))
    payload['data'] = json.loads(parse.unquote(handler.args.get('data', [None])[0]))
    payload['name'] = parse.unquote(handler.args['name'][0])
    return json.dumps(payload, indent=4)


def save_config(handler):
    """Save the current narrative config.
    (to $GRAMEXDATA/{{ handler.current_user.id }})"""
    payload = {}
    payload['config'] = json.loads(parse.unquote(handler.args['config'][0]))
    payload['name'] = parse.unquote(handler.args['name'][0])
    nname = payload['name']
    if not nname.endswith('.json'):
        nname += '.json'
    payload['dataset'] = parse.unquote(handler.args['dataset'][0])
    fpath = op.join(nlg_path, handler.current_user.id, nname)
    with open(fpath, 'w') as fout:  # noqa: No encoding for json
        json.dump(payload, fout, indent=4)


def get_gramopts(handler):
    """Find all Grammar and token inflection options from the NLG library.

    Primarily used for creating the select box in the template settings dialog."""
    funcs = {}
    for attrname in dir(grammar):
        obj = getattr(grammar, attrname)
        if getattr(obj, 'gramopt', False):
            funcs[obj.fe_name] = {'source': obj.source, 'func_name': attrname}
    return funcs


def init_form(handler):
    """Process input from the landing page and write the current session config."""
    meta = {}
    data_dir = get_user_dir(handler)
    if not op.isdir(data_dir):
        os.makedirs(data_dir)

    # handle dataset
    data_file = handler.request.files.get('data-file', [{}])[0]
    if data_file:
        # TODO: Unix filenames may not be valid Windows filenames.
        outpath = op.join(data_dir, data_file['filename'])
        with open(outpath, 'wb') as fout:
            fout.write(data_file['body'])
    else:
        dataset = handler.args['dataset'][0]
        outpath = op.join(data_dir, dataset)
    # shutil.copy(outpath, fh_fpath)
    meta['dsid'] = op.basename(outpath)

    # handle config
    config_name = handler.get_argument('narrative', '')
    if config_name:
        config_path = op.join(data_dir, config_name)
        # shutil.copy(config_path, op.join(local_data_dir, 'config.json'))
        meta['nrid'] = op.basename(config_path)

    # write meta config
    with open(op.join(data_dir, 'meta.cfg'), 'w') as fout:  # NOQA
        json.dump(meta, fout, indent=4)


def edit_narrative(handler):
    """Set the handler's narrative and dataset ID to the current session."""
    user_dir = op.join(nlg_path, handler.current_user.id)
    dataset_name = handler.args.get('dsid', [''])[0]
    narrative_name = handler.args.get('nrid', [''])[0] + '.json'
    with open(op.join(user_dir, 'meta.cfg'), 'w') as fout:  # NOQA: no encoding for JSON
        json.dump({'dsid': dataset_name, 'nrid': narrative_name}, fout, indent=4)


def get_init_config(handler):
    """Get the initial default configuration for the current user."""
    user_dir = get_user_dir(handler)
    metapath = op.join(user_dir, 'meta.cfg')
    if op.isfile(metapath):
        with open(metapath, 'r') as fout:  # NOQA: no encoding for JSON
            meta = json.load(fout)
        config_file = op.join(user_dir, meta.get('nrid', ''))
        if op.isfile(config_file):
            with open(config_file, 'r') as fout:  # NOQA: no encoding for JSON
                meta['config'] = json.load(fout)
        return meta
    return {}
