"""
 Gramex config editing through IDE
 Entry point is "ide_config_handler"
"""
import json
import yaml
from functools import reduce
import operator
from gramex.config import app_log

node_id = 0         # counter to generate node id's while creating JSON from YAML

def recursive_parse_dict_create_json(d, pid, new_d, config_list):
    global node_id
    data_id = 0
    for k, v in d.items():
        if isinstance(v, dict):
            node_id += 1
            new_pd = {"id": '%d' % node_id, "text": "%s" % k, "parent": "%s" % pid, "data": {}}
            recursive_parse_dict_create_json(v, int(new_pd['id']), new_pd, config_list)
        elif new_d:
            data_id += 1
            new_d['data'].update({"%d" % data_id: {"key": k, "value": v}})
        else:
            app_log.error('No data element in dict: ', d)

    if new_d:config_list.append(new_d)
    return config_list


def parse_json_create_dict(src):
    objs = {node['id']: {v['key']: v['value'] for k, v in node['data'].items()} for node in src}
    root = {}
    for node in src:
        el = root if node['parent'] == '#' else objs[node['parent']]
        el[node['text']] = objs[node['id']]
    return root

def ide_config_handler(handler, _yaml_file='gramex.yaml'):
    global node_id
    parsed_config = {}
    final_list = []
    node_id = 0

    _yaml_file = handler.get_arg('filename')  # comment this line for testing with file
    # if handler == "GET":                    # with file
    if handler.request.method == "GET":    # using browser request
        with open(_yaml_file) as fin:
            cfg_data = yaml.safe_load(fin)
        try:
            final_list = recursive_parse_dict_create_json(cfg_data, "#", parsed_config, final_list)
        except Exception as ex:
            app_log.debug("Exception while creating json: " + format(ex))
            return json.dumps({"Result": [{"Failure": "true"}]})

        return json.dumps(final_list)

    # elif handler == 'POST':                   #with file
    #    with open(_yaml_file) as fin:
    #        body = yaml.safe_load(fin)
    elif handler.request.method == 'POST':   # using browser request
        body = json.loads(handler.request.body)  # comment this line for testing with file
        try:
            yaml_out = parse_json_create_dict(body)
        except Exception as ex:
            app_log.debug("Exception while parsing json: " + format(ex))
            return json.dumps({"Result": [{"Failure": "true"}]})
        if yaml_out:
            with open(_yaml_file, 'w') as fout:
                yaml.dump(yaml_out, fout)
                app_log.info("Updated file: "+_yaml_file)
                return json.dumps({"Result": [{"Success": "true"}]})
        else:
            app_log.debug("Failed to update file: "+_yaml_file)
            return json.dumps({"Result": [{"Failure": "true"}]})
    else:
        app_log.debug("Unrecognized http request :" + handler.request.method)
        return json.dumps({"Result": [{"Failure": "true"}]})
"""
if __name__ == "__main__":
    # test GET
    # ide_config_handler('GET', "C:/Users/sandeep.bhat/Desktop/Temp/gramex.yaml");
    # test POST # please make sure you have back-up of file as it will be overwritten
    # ide_config_handler('POST', "C:/Users/sandeep.bhat/Desktop/Temp/yaml_file2.yaml");
"""
