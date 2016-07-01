def update(content):
    if 'result' in content:
        content['gramex'] = '1.0.x'
    return content
