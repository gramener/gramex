import re
import yaml
import blaze as bz
import pandas as pd
import sqlalchemy as sa
from orderedattrdict import AttrDict
from tornado.web import RequestHandler

drivers = {}


class DataHandler(RequestHandler):
    '''
    Serves data in specified format from datasource. It accepts these parameters:

    :arg dict kwargs: keyword arguments to be passed to the function.
    :arg string url: The path at which datasource (db, csv) is located.
    :arg string driver: Connector to be used to connect to datasource
        Like -(sqlalchemy, pandas.read_csv, blaze).
        Currently supports sqlalchemy, blaze.
    :arg dict parameters: Additional keyword arguments for driver.
    :arg dict headers: HTTP headers to set on the response.
        Currently supports csv, json, html table

    Here's a simple use -- to return a csv file as a response to a URL. This
    configuration renders `flags` table in `tutorial.db` database as `file.csv`
    at the URL `/datastore/flags`::

        url:
            flags:
                pattern: /datastore/flags               # Any URL starting with /datastore/flags
                handler: gramex.handlers.DataHandler    # uses DataHandler
                kwargs:
                    driver: sqlalchemy                  # Using sqlalchemy driver
                    url: sqlite:///C:/path/tutorial.db  # Connects to database at this path/url
                    table: flags                        # to this table
                    parameters: {encoding: utf8}        # with additional parameters provided
                    headers:
                        Content-Type: text/csv            # and served as csv
                        # Content-Type: application/json  # or JSON
                        # Content-Type: text/html         # or HTML

    '''
    def initialize(self, **kwargs):
        self.params = kwargs

    def get(self):
        args = AttrDict(self.params)
        key = yaml.dump(args)

        qconfig = {'query': args.get('query', {}),
                   'default': args.get('default', {})}
        delims = {'agg': ':', 'sort': ':', 'where': ''}
        nojoins = ['select', 'groupby']

        for q in qconfig:
            if qconfig[q]:
                tmp = AttrDict()
                for key in qconfig[q].keys():
                    val = qconfig[q][key]
                    if isinstance(val, list):
                        tmp[key] = val
                    elif isinstance(val, dict):
                        tmp[key] = [k if key in nojoins
                                    else k + delims[key] + v
                                    for k, v in val.items()]
                    elif isinstance(val, (str, int)):
                        tmp[key] = [val]
                qconfig[q] = tmp

        def getq(key):
            return (qconfig['query'].get(key) or
                    self.get_arguments(key) or
                    qconfig['default'].get(key))

        _selects, _wheres = getq('select'), getq('where')
        _groups, _aggs = getq('groupby'), getq('agg')
        _offsets, _limits = getq('offset'), getq('limit')
        _sorts = getq('sort')

        if args.driver == 'sqlalchemy':
            if key not in drivers:
                parameters = args.get('parameters', {})
                drivers[key] = sa.create_engine(args['url'], **parameters)
            self.driver = drivers[key]

            meta = sa.MetaData(bind=self.driver, reflect=True)
            table = meta.tables[args['table']]

            if _wheres:
                wh_re = re.compile(r'([^=><~!]+)([=><~!]{1,2})([^=><~!]+)')
                wheres = []
                for where in _wheres:
                    match = wh_re.search(where)
                    if match is None:
                        continue
                    col, oper, val = match.groups()
                    col = table.c[col]
                    if oper in ['==', '=']:
                        wheres.append(col == val)
                    elif oper == '>=':
                        wheres.append(col >= val)
                    elif oper == '<=':
                        wheres.append(col <= val)
                    elif oper == '>':
                        wheres.append(col > val)
                    elif oper == '<':
                        wheres.append(col < val)
                    elif oper == '!=':
                        wheres.append(col != val)
                    elif oper == '~':
                        wheres.append(col.ilike('%' + val + '%'))
                    elif oper == '!~':
                        wheres.append(col.notlike('%' + val + '%'))
                wheres = sa.and_(*wheres)

            if _groups and _aggs:
                grps = [table.c[c] for c in _groups]
                aggselects = grps[:]
                safuncs = {'min': sa.func.min, 'max': sa.func.max,
                           'sum': sa.func.sum, 'count': sa.func.count,
                           'mean': sa.func.avg, 'nunique': sa.func.count}
                agg_re = re.compile(r'([^:]+):([aA-zZ]+)\(([^:]+)\)')
                for agg in _aggs:
                    match = agg_re.search(agg)
                    if match is None:
                        continue
                    name, oper, col = match.groups()
                    if oper == 'nunique':
                        aggselects.append(sa.func.count(table.c[col].distinct()).label(name))
                    else:
                        aggselects.append(safuncs[oper](table.c[col]).label(name))

                if _selects:
                    aggselects = [grp for grp in aggselects if grp.key in _selects]

                query = sa.select(aggselects)
                if _wheres:
                    query = query.where(wheres)
                query = query.group_by(*grps)
            else:
                if _selects:
                    query = sa.select([table.c[c] for c in _selects])
                else:
                    query = sa.select([table])
                if _wheres:
                    query = query.where(wheres)

            if _sorts:
                order = {'asc': sa.asc, 'desc': sa.desc}
                sorts = []
                for sort in _sorts:
                    col, odr = sort.partition(':')[::2]
                    sorts.append(order.get(odr, sa.asc)(col))
                query = query.order_by(*sorts)

            if _offsets:
                query = query.offset(_offsets[0])
            if _limits:
                query = query.limit(_limits[0])

            self.result = pd.read_sql_query(query, self.driver)

        elif args.driver == 'blaze':
            '''TODO: Not caching blaze connections
            '''
            parameters = args.get('parameters', {})
            bzcon = bz.Data(args['url'] +
                            ('::' + args['table'] if args.get('table') else ''),
                            **parameters)
            table = bz.TableSymbol('table', bzcon.dshape)
            query = table

            # hack
            _offsets = _offsets or [None]
            _limits = _limits or [None]

            if _wheres:
                wh_re = re.compile(r'([^=><~!]+)([=><~!]{1,2})([^=><~!]+)')
                wheres = None
                for where in _wheres:
                    match = wh_re.search(where)
                    if match is None:
                        continue
                    col, oper, val = match.groups()
                    col = table[col]
                    if oper in ['==', '=']:
                        whr = (col == val)
                    elif oper == '>=':
                        whr = (col >= val)
                    elif oper == '<=':
                        whr = (col <= val)
                    elif oper == '>':
                        whr = (col > val)
                    elif oper == '<':
                        whr = (col < val)
                    elif oper == '!=':
                        whr = (col != val)
                    wheres = whr if wheres is None else wheres & whr
                query = query[wheres]

            if _groups and _aggs:
                byaggs = {'min': bz.min, 'max': bz.max,
                          'sum': bz.sum, 'count': bz.count,
                          'mean': bz.mean, 'nunique': bz.nunique}
                agg_re = re.compile(r'([^:]+):([aA-zZ]+)\(([^:]+)\)')
                grps = bz.merge(*[query[group] for group in _groups])
                aggs = {}
                for agg in _aggs:
                    match = agg_re.search(agg)
                    if match is None:
                        continue
                    name, oper, col = match.groups()
                    aggs[name] = byaggs[oper](query[col])
                query = bz.by(grps, **aggs)

            if _sorts:
                order = {'asc': True, 'desc': False}
                sorts = []
                for sort in _sorts:
                    col, odr = sort.partition(':')[::2]
                    sorts.append(col)
                query = query.sort(sorts, ascending=order.get(odr, True))

            offset = _offsets[0]
            limit = _limits[0]
            if offset:
                offset = int(offset)
            if limit:
                limit = int(limit)
            if offset and limit:
                limit += offset
            if offset or limit:
                query = query[offset:limit]

            if _selects:
                query = query[_selects]

            # TODO: Improve json, csv, html outputs using native odo
            self.result = bz.odo(bz.compute(query, bzcon.data), pd.DataFrame)

        else:
            raise NotImplementedError('driver=%s is not supported yet.' % args.driver)

        for header_name, header_value in args['headers'].items():
            self.set_header(header_name, header_value)

        if args['headers']['Content-Type'] == 'application/json':
            self.content = self.result.to_json(orient='records')
        if args['headers']['Content-Type'] == 'text/html':
            self.content = self.result.to_html()
        if args['headers']['Content-Type'] == 'text/csv':
            self.content = self.result.to_csv(index=False)
            self.set_header("Content-Disposition", "attachment;filename=file.csv")

        self.write(self.content)
        self.flush()
