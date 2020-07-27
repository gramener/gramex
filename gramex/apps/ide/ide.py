'''
 Gramex config editing through IDE
 Entry point is "ide_config_handler"
'''
import json
import yaml
from gramex.config import app_log

config_dict = []    # List to hold all the root node dicts (for GET/POST)
node_id = 0         # counter to generate node id's while creating JSON from YAML


def recursive_parse_dict_create_json(d, pid, new_d):
    global node_id, config_dict
    data_id = 1
    for k, v in d.items():
        if isinstance(v, dict):
            node_id += 1
            new_pd = {"id": '%d' % node_id, "text": "%s" % k, "parent": "%s" % pid, "data": {}}
            recursive_parse_dict_create_json(v, int(new_pd['id']), new_pd)
        else:
            new_d_element = {"%d" % data_id: {"key": k, "value": v}}
            data_id += 1
            if new_d:
                new_d['data'].update(new_d_element)
            else:
                app_log.error('No data element in dict', d)

    if new_d:
        config_dict.append(new_d)
    return


def recursive_pop_id(k, d):
    if k in d.keys():
        d.pop(k)
    for v in d.values():
        if isinstance(v, dict):
            recursive_pop_id(k, v)

    return None


def recursive_lookup(k, d):
    if k == d['id']:
        return d
    for v in d.values():
        if isinstance(v, dict):
            df = (recursive_lookup(k, v))
            if df:
                return df
        # else parse rest of the values, if available
    return None


def flatten_data(data):
    kv_dict = {}
    for item in data.items():
        values = item[1]     # item[0] will always be key (1,2,3....)
        kv_dict.update({values['key']: values['value']})
    return kv_dict


def append_under_parent(data):
    global config_dict
    for ld in config_dict:
        item = recursive_lookup(data['parent'], ld)
        if item:
            if data['data']:
                flat_data = flatten_data(data['data'])
                flat_data.update({"id": '%s' % (data['id'])})
            else:
                flat_data = {"id": '%s' % (data['id'])}

            item.update({"%s" % (data['text']): flat_data})
            return True

    return False


def parse_json_create_dict(json_data):
    global config_dict
    pop_list = []
    processed_yaml_dict = {}

    for item in json_data:
        # start with the root level nodes (parent#)
        # get the root nodes and remove them from the dict list
        if item['parent'] == "#":        # flatten data for all root nodes
            flat_data = flatten_data(item['data'])
            if flat_data:
                item.update(flat_data)
            item.pop('data')
            item.pop('parent')
            config_dict.append(item)
            pop_list.append(item)

    for pop_item in pop_list:
        del json_data[json_data.index(pop_item)]

    pop_list.clear()

    while True:
        for item in json_data:
            if append_under_parent(item):
                pop_list.append(item)    # for each successfully processed dict, add it to pop list for removal

        if len(pop_list) == len(json_data):
            break
        else:
            app_log.debug("Entire list not processed, making another pass")
            for pop_item in pop_list:
                del json_data[json_data.index(pop_item)]

            pop_list.clear()

    # Processed All, now remove all ids and create final dict for writing to file
    for li in config_dict:
        root_node_key = li.pop('text')
        recursive_pop_id('id', li)
        processed_yaml_dict.update({root_node_key: li})

    return processed_yaml_dict


def ide_config_handler(handler, _yaml_file='gramex.yaml'):
    global node_id, config_dict
    parsed_config = {}
    config_dict = []
    node_id = 0

    _yaml_file = handler.get_arg('filename')  # comment this line for testing with file
    # if handler == "GET":                    # with file
    if handler.request.method == "GET":    # using browser request
        with open(_yaml_file) as fin:
            cfg_data = yaml.safe_load(fin)
        try:
            recursive_parse_dict_create_json(cfg_data, "#", parsed_config)
        except Exception as ex:
            app_log.debug("Exception while creating json: " + format(ex))
            return json.dumps({"Result": [{"Failure": "true"}]})

        return json.dumps(config_dict)

    # if handler == 'POST':                   #with file
    #    with open(_yaml_file) as fin:
    #        body = _yaml.safe_load(fin)
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
                return(json.dumps({"Result": [{"Success": "true"}]}))
        else:
            app_log.debug("Failed to update file: "+_yaml_file)
            return(json.dumps({"Result": [{"Failure": "true"}]}))
    else:
        app_log.debug("Unrecognized http request :" + handler.request.method)
        return (json.dumps({"Result": [{"Failure": "true"}]}))


'''
if __name__ == "__main__":
    #test GET
    #ide_config_handler('GET', "C:/Users/sandeep.bhat/Desktop/Temp/gramex.yaml");
    #test POST # please make sure you have back-up of file as it will be overwritten
    #ide_config_handler('POST', "C:/Users/sandeep.bhat/Desktop/Temp/yaml_file2.yaml");
'''
