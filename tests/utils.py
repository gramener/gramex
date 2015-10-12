import json


def args_as_json(handler):
    return json.dumps({arg: handler.get_arguments(arg) for arg in handler.request.arguments})
