import gramex.cache

# A global mapping of cid: to filenames
cidmap = {}


def cid(handler):
    cid = handler.path_args[0] if len(handler.path_args) else None
    if cid in cidmap:
        return gramex.cache.open(cidmap[cid], 'bin')
    return 'NA'
