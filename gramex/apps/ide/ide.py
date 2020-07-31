"""
 Gramex config editing through IDE
 Entry point is "ide_config_handler"
"""
import json
import yaml
from gramex.config import app_log


def parse_dict_create_json(cfg):
    node_id = 0
    new_d = {}
    config_list = []
    pid = "#"

    def recursive_parse(cfg, pid, new_d):
        nonlocal node_id, config_list
        data_id = 0
        for k, v in cfg.items():
            if isinstance(v, dict):
                node_id += 1
                new_pd = {"id": '%d' % node_id, "text": k, "parent": "%s" % pid, "data": {}}
                recursive_parse(v, node_id, new_pd)
            elif isinstance(v, (list, tuple)):
                raise Exception("Yet to be implemented")
            elif new_d:
                data_id += 1
                new_d['data'].update({"%d" % data_id: {"key": k, "value": v}})
            else:
                node_id += 1
                row = {"id": '%d' % node_id, "text": pid, "parent": pid, "data": {1: {"key": k, "value": v}}}
                config_list.append(row)

        if new_d:
            config_list.append(new_d)

    recursive_parse(cfg, pid, new_d)

    return config_list


def parse_json_create_dict(src):
    objs = {node['id']: {v['key']: v['value'] for k, v in node['data'].items()} for node in src}
    root = {}
    for node in src:
        el = root if node['parent'] == '#' else objs[node['parent']]
        if node['text'] == '#':
            el.update(objs[node['id']])
        else:
            el[node['text']] = objs[node['id']]
    return root


def ide_config_handler(handler, _yaml_file='gramex.yaml'):
    final_list = []
    _yaml_file = handler.get_arg('filename')  # comment this line for testing with file
    # if handler == "GET":                    # with file
    if handler.request.method == "GET":    # using browser request
        with open(_yaml_file) as fin:
            cfg_data = yaml.safe_load(fin)
        try:
            final_list = parse_dict_create_json(cfg_data)
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
                yaml.safe_dump(yaml_out, fout)
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
    # ide_config_handler('GET', "C:/Users/sandeep.bhat/Desktop/Temp/test_ide.yaml");
    # test POST ----- please make sure you have back-up of file as it will be overwritten
    # ide_config_handler('POST', "C:/Users/sandeep.bhat/Desktop/Temp/yaml_file2.yaml");
    # ide_config_handler('POST', "C:/Users/sandeep.bhat/Desktop/Temp/new.json");
"""
