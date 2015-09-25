import json


def total(*items):
    'Calculate total of all items and render as JSON: value and string'
    total = sum(float(item) for item in items)
    return json.dumps({
        'display': '${:,.2f}'.format(total),
        'value': total,
    })
