import re
import yaml
import tornado.gen
import tornado.web
import pandas as pd
import sqlalchemy as sa
from gramex.services import info
from orderedattrdict import AttrDict
from .basehandler import BaseHandler

drivers = {}


class DataHandler(BaseHandler):
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
                pattern: /datastore/flags                 # Any URL starting with /datastore/flags
                handler: DataHandler                      # uses DataHandler
                kwargs:
                    driver: sqlalchemy                    # Using sqlalchemy driver
                    url: $YAMLPATH/tutorial.db            # Connects to database at this path/url
                    table: flags                          # to this table
                    parameters: {encoding: utf8}          # with additional parameters provided
                    default: {}                           # default query parameters
                    query: {}                             # query parameter overrides
                    headers:
                        Content-Type: text/csv            # and served as csv
                        # Content-Type: application/json  # or JSON
                        # Content-Type: text/html         # or HTML

    '''
    @classmethod
    def setup(cls, **kwargs):
        super(DataHandler, cls).setup(**kwargs)
        cls.params = AttrDict(kwargs)
        cls.driver_key = yaml.dump(kwargs)

        qconfig = {'query': cls.params.get('query', {}),
                   'default': cls.params.get('default', {})}
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
        cls.qconfig = qconfig

    def getq(self, key, default_value=None):
        return (self.qconfig['query'].get(key) or
                self.get_arguments(key) or
                self.qconfig['default'].get(key) or
                default_value)

    def _sqlalchemy(self, _selects, _wheres, _groups, _aggs, _offset, _limit, _sorts):
        if self.driver_key not in drivers:
            parameters = self.params.get('parameters', {})
            drivers[self.driver_key] = sa.create_engine(self.params['url'], **parameters)
        self.driver = drivers[self.driver_key]

        meta = sa.MetaData(bind=self.driver, reflect=True)
        table = meta.tables[self.params['table']]

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

        if _offset:
            query = query.offset(_offset)
        if _limit:
            query = query.limit(_limit)

        return pd.read_sql_query(query, self.driver)

    def _blaze(self, _selects, _wheres, _groups, _aggs, _offset, _limit, _sorts):
        # Import blaze on demand -- it's a very slow import
        import blaze as bz                      # noqa

        # TODO: Not caching blaze connections
        parameters = self.params.get('parameters', {})
        bzcon = bz.Data(self.params['url'] +
                        ('::' + self.params['table'] if self.params.get('table') else ''),
                        **parameters)
        table = bz.TableSymbol('table', bzcon.dshape)
        query = table

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
                elif oper == '~':
                    whr = (col.like('*' + val + '*'))
                elif oper == '!~':
                    whr = (~col.like('*' + val + '*'))
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

        if _offset:
            _offset = int(_offset)
        if _limit:
            _limit = int(_limit)
        if _offset and _limit:
            _limit += _offset
        if _offset or _limit:
            query = query[_offset:_limit]

        if _selects:
            query = query[_selects]

        # TODO: Improve json, csv, html outputs using native odo
        return bz.odo(bz.compute(query, bzcon.data), pd.DataFrame)

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        kwargs = dict(
            _selects=self.getq('select'),
            _wheres=self.getq('where'),
            _groups=self.getq('groupby'),
            _aggs=self.getq('agg'),
            _offset=self.getq('offset', [None])[0],
            _limit=self.getq('limit', [None])[0],
            _sorts=self.getq('sort'),
        )

        if self.params.driver == 'sqlalchemy':
            self.result = yield info.threadpool.submit(self._sqlalchemy, **kwargs)
        elif self.params.driver == 'blaze':
            self.result = yield info.threadpool.submit(self._blaze, **kwargs)
        else:
            raise NotImplementedError('driver=%s is not supported yet.' % self.params.driver)

        # Set content and type based on format
        formats = self.getq('format', ['json'])
        if 'json' in formats:
            self.set_header('Content-Type', 'application/json')
            self.content = self.result.to_json(orient='records')
        elif 'csv' in formats:
            self.set_header('Content-Type', 'text/csv')
            self.set_header("Content-Disposition", "attachment;filename=file.csv")
            self.content = self.result.to_csv(index=False, encoding='utf-8')
        elif 'html' in formats:
            self.set_header('Content-Type', 'text/html')
            self.content = self.result.to_html()
        else:
            raise NotImplementedError('format=%s is not supported yet.' % formats)

        # Allow headers to be overridden
        for header_name, header_value in self.params.get('headers', {}).items():
            self.set_header(header_name, header_value)

        self.write(self.content)
