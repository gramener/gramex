import os
import re
import yaml
import tornado.gen
import tornado.web
import gramex
import pandas as pd
import sqlalchemy as sa
from tornado.web import HTTPError
from orderedattrdict import AttrDict
from gramex.data import download
from gramex.http import NOT_FOUND
from gramex.transforms import build_transform
from .basehandler import BaseHandler

drivers = {}
folder = os.path.dirname(os.path.abspath(__file__))


class DataMixin(object):
    @classmethod
    def setup_data(cls, kwargs):
        cls.params = AttrDict(kwargs)
        cls.thread = kwargs.get('thread', True)

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
                self.get_arguments(key, strip=False) or
                self.qconfig['default'].get(key) or
                default_value)

    def _engine(self):
        '''Initialise self.engine. Must be called before self.engine is used.'''
        url, parameters = self.params['url'], self.params.get('parameters', {})
        driver_key = yaml.dump([url, parameters])
        if driver_key not in drivers:
            drivers[driver_key] = sa.create_engine(url, **parameters)
        self.engine = drivers[driver_key]

    def write_headers(self, **headers):
        # Allow headers to be overridden
        headers.update(self.params.get('headers', {}))
        for header_name, header_value in headers.items():
            self.set_header(header_name, header_value)

    def renderdata(self):
        # Set content and type based on format
        if 'count' in self.result:
            self.set_header('X-Count', self.result['count'])
        fmt = self.getq('format', [None])[0]
        kwargs = {}
        if fmt == 'template':
            kwargs.update(template=self.params.get('template', self._template), handler=self)
        self.write(download(self.result['data'], fmt, **kwargs))

    _FORMAT_HEADERS = {
        '': {'Content-Type': 'application/json'},
        'csv': {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment;filename=file.csv'},
        'html': {'Content-Type': 'text/html'},
        'json': {'Content-Type': 'application/json'},
        'template': {'Content-Type': 'text/html'},
        'xlsx': {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment;filename=file.xlsx'
        },
    }

    def _write_format_headers(self):
        '''Write the Content-Type / Content Disposition headers based on format'''
        formats = self.getq('format', [])
        for fmt in self._FORMAT_HEADERS:
            if fmt in formats:
                headers = dict(self._FORMAT_HEADERS[fmt])
                break
        else:
            if len(formats) == 0:
                headers = dict(self._FORMAT_HEADERS['json'])
            else:
                raise NotImplementedError('format=%s is not supported yet.' % formats)
        filename = self.getq('filename', [])
        if len(filename) > 0:
            headers['Content-Disposition'] = 'attachment;filename=%s' % filename[0]
        self.write_headers(**headers)


class DataHandler(BaseHandler, DataMixin):
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
                    thread: false                         # Run in synchronous mode
                    headers:
                        Content-Type: text/csv            # and served as csv
                        # Content-Type: application/json  # or JSON
                        # Content-Type: text/html         # or HTML

    '''
    _template = os.path.join(folder, 'datahandler.template.html')

    @classmethod
    def setup(cls, **kwargs):
        super(DataHandler, cls).setup(**kwargs)
        cls.setup_data(kwargs)

        driver = kwargs.get('driver')
        cls.driver_name = driver
        if driver == 'sqlalchemy':
            cls.driver_method = cls._sqlalchemy
            # Create a cached metadata store for SQLAlchemy engines
            cls.meta = sa.MetaData()
        elif driver == 'blaze':
            cls.driver_method = cls._blaze
        else:
            raise NotImplementedError('driver=%s is not supported yet.' % driver)

        posttransform = kwargs.get('posttransform', {})
        cls.posttransform = []
        if 'function' in posttransform:
            cls.posttransform.append(
                build_transform(
                    posttransform, vars=AttrDict(content=None),
                    filename='url:%s' % cls.name))

    def _sqlalchemy_gettable(self):
        self._engine()
        return sa.Table(self.params['table'], self.meta, autoload=True, autoload_with=self.engine)

    def _sqlalchemy_wheres(self, _wheres, table):
        wh_re = re.compile(r'([^=><~!]+)([=><~!]{1,2})([\s\S]+)')
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
        return wheres

    def _sqlalchemy(self, _selects, _wheres, _groups, _aggs, _offset, _limit,
                    _sorts, _count, _q):
        table = self._sqlalchemy_gettable()
        columns = table.columns.keys()

        if _wheres:
            wheres = self._sqlalchemy_wheres(_wheres, table)

        alias_cols = []
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
                alias_cols.append(name)
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

        if _q:
            query = query.where(sa.or_(
                column.ilike('%' + _q + '%') for column in table.columns
                if isinstance(column.type, sa.types.String)
            ))

        # Create a query that returns the count before we sort, offset or limit.
        # .alias() prevents "Every derived table must have its own alias" error.
        count_query = query.alias('count_table').count()

        if _sorts:
            order = {'asc': sa.asc, 'desc': sa.desc}
            sorts = []
            for sort in _sorts:
                col, odr = sort.partition(':')[::2]
                if col not in columns + alias_cols:
                    continue
                sorts.append(order.get(odr, sa.asc)(col))
            query = query.order_by(*sorts)

        if _offset:
            query = query.offset(_offset)
        if _limit:
            query = query.limit(_limit)

        result = {
            'query': query,
            'data': pd.read_sql_query(query, self.engine),
        }
        if _count:
            result['count'] = self.engine.execute(count_query).fetchone()[0]
        return result

    def _sqlalchemy_post(self, _vals):
        table = self._sqlalchemy_gettable()
        content = dict(x.split('=', 1) for x in _vals)
        for posttransform in self.posttransform:
            for value in posttransform(content):
                content = value
        query = table.insert()
        self.engine.execute(query, **content)
        return {'query': query, 'data': pd.DataFrame()}

    def _sqlalchemy_delete(self, _wheres):
        if not _wheres:
            raise HTTPError(NOT_FOUND, log_message='WHERE is required in DELETE method')
        table = self._sqlalchemy_gettable()
        wheres = self._sqlalchemy_wheres(_wheres, table)
        query = table.delete().where(wheres)
        self.engine.execute(query)
        return {'query': query, 'data': pd.DataFrame()}

    def _sqlalchemy_put(self, _vals, _wheres):
        if not _vals:
            raise HTTPError(NOT_FOUND, log_message='VALS is required in PUT method')
        if not _wheres:
            raise HTTPError(NOT_FOUND, log_message='WHERE is required in PUT method')
        table = self._sqlalchemy_gettable()
        content = dict(x.split('=', 1) for x in _vals)
        for posttransform in self.posttransform:
            for value in posttransform(content):
                content = value
        wheres = self._sqlalchemy_wheres(_wheres, table)
        query = table.update().where(wheres).values(content)
        self.engine.execute(query)
        return {'query': query, 'data': pd.DataFrame()}

    def _blaze(self, _selects, _wheres, _groups, _aggs, _offset, _limit, _sorts,
               _count, _q):
        import blaze as bz
        import datashape
        # TODO: Not caching blaze connections
        parameters = self.params.get('parameters', {})
        bzcon = bz.Data(self.params['url'] +
                        ('::' + self.params['table'] if self.params.get('table') else ''),
                        **parameters)
        table = bz.Symbol('table', bzcon.dshape)
        columns = table.fields
        query = table

        if _wheres:
            wh_re = re.compile(r'([^=><~!]+)([=><~!]{1,2})([\s\S]+)')
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
            query = query if wheres is None else query[wheres]

        alias_cols = []
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
                alias_cols.append(name)
                aggs[name] = byaggs[oper](query[col])
            query = bz.by(grps, **aggs)

        if _q:
            wheres = None
            for col in columns:
                if isinstance(table[col].dshape.measure.ty, datashape.coretypes.String):
                    whr = table[col].like('*' + _q + '*')
                    wheres = whr if wheres is None else wheres | whr
            if wheres is not None:
                query = query[wheres]

        count_query = query.count()

        if _sorts:
            order = {'asc': True, 'desc': False}
            sorts = []
            for sort in _sorts:
                col, odr = sort.partition(':')[::2]
                if col not in columns + alias_cols:
                    continue
                sorts.append(col)
            if sorts:
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
        result = {
            'query': query,
            'data': bz.odo(bz.compute(query, bzcon.data), pd.DataFrame),
        }
        if _count:
            count = bz.odo(bz.compute(count_query, bzcon.data), pd.DataFrame)
            result['count'] = count.iloc[0, 0]
        return result

    def prepare(self):
        super(DataHandler, self).prepare()
        self._write_format_headers()

    @tornado.gen.coroutine
    def get(self):
        self.query = dict(
            _selects=self.getq('select'),
            _wheres=self.getq('where'),
            _groups=self.getq('groupby'),
            _aggs=self.getq('agg'),
            _offset=self.getq('offset', [None])[0],
            _limit=self.getq('limit', [100])[0],
            _sorts=self.getq('sort'),
            _count=self.getq('count', [''])[0],
            _q=self.getq('q', [''])[0]
        )

        if self.thread:
            self.result = yield gramex.service.threadpool.submit(self.driver_method, **self.query)
        else:
            self.result = self.driver_method(**self.query)
        self.renderdata()

    @tornado.gen.coroutine
    def post(self):
        if self.driver_name != 'sqlalchemy':
            raise NotImplementedError('driver=%s is not supported yet.' % self.driver_name)
        kwargs = {'_vals': self.getq('val', [])}
        if self.thread:
            self.result = yield gramex.service.threadpool.submit(self._sqlalchemy_post, **kwargs)
        else:
            self.result = self._sqlalchemy_post(**kwargs)
        self.renderdata()

    @tornado.gen.coroutine
    def delete(self):
        if self.driver_name != 'sqlalchemy':
            raise NotImplementedError('driver=%s is not supported yet.' % self.driver_name)
        kwargs = {'_wheres': self.getq('where')}
        if self.thread:
            self.result = yield gramex.service.threadpool.submit(self._sqlalchemy_delete, **kwargs)
        else:
            self.result = self._sqlalchemy_delete(**kwargs)
        self.renderdata()

    @tornado.gen.coroutine
    def put(self):
        if self.driver_name != 'sqlalchemy':
            raise NotImplementedError('driver=%s is not supported yet.' % self.driver_name)
        kwargs = {'_vals': self.getq('val', []), '_wheres': self.getq('where')}
        if self.thread:
            self.result = yield gramex.service.threadpool.submit(self._sqlalchemy_put, **kwargs)
        else:
            self.result = self._sqlalchemy_put(**kwargs)
        self.renderdata()


class QueryHandler(BaseHandler, DataMixin):
    '''
    Exposes parameterized SQL queries via a REST API.

    Sample configuration::

        pattern: /$YAMLURL/query
        handler: QueryHandler
        kwargs:
            url: sqlite:///database.db
            sql: SELECT * FROM table ORDER BY :key
            default:
                key: ...
                limit:
                format:
                filename:
            query:
                limit:
                format:
            columns:
                col: type
            headers:
                ...
            redirect:
                ...
    '''
    _template = os.path.join(folder, 'queryhandler.template.html')

    @classmethod
    def setup(cls, **kwargs):
        super(QueryHandler, cls).setup(**kwargs)
        cls.setup_data(kwargs)
        from sqlalchemy import text
        if isinstance(kwargs['sql'], dict):
            cls.query = AttrDict([(key, text(val)) for key, val in kwargs['sql'].items()])
        else:
            cls.query = text(kwargs['sql'])
        cls.post = cls.delete = cls.update = cls.get

    def run(self, stmt, limit):
        self._engine()
        import pandas as pd
        if self.request.method.lower() == 'get':
            try:
                result = next(pd.read_sql(stmt, self.engine, chunksize=limit))
            except StopIteration:
                result = pd.DataFrame()
        else:
            self.engine.execute(stmt)
            result = pd.DataFrame()
        return {
            'query': stmt,
            'data': result
        }

    def renderdatas(self):
        '''Render multiple datasets'''
        fmt = self.getq('format', [None])[0]
        kwargs = {}
        if fmt == 'template':
            kwargs.update(template=self.params.get('template', self._template), handler=self)
        else:
            self.result = {key: val['data'] for key, val in self.result.items()}
        self.write(download(self.result, fmt, **kwargs))
        # csv: 'QUERY: %s\n%s' % (key, result['data'].to_csv(index=False, encoding='utf-8'))

    def prepare(self):
        super(QueryHandler, self).prepare()
        self._write_format_headers()

    @tornado.gen.coroutine
    def get(self):
        limit = int(self.getq('limit', [100])[0])
        if isinstance(self.query, dict):
            # Bind all queries and run them in parallel
            args = {
                key: self.getq(key, [''])[0]
                for name, query in self.query.items()
                for key, _bindparams in query._bindparams.items()
            }
            stmts = AttrDict([
                (key, q.bindparams(**{k: v for k, v in args.items() if k in q._bindparams}))
                for key, q in self.query.items()
            ])
            if self.thread:
                futures = AttrDict([
                    (key, gramex.service.threadpool.submit(self.run, stmt, limit))
                    for key, stmt in stmts.items()
                ])
                self.result = AttrDict()
                for key, future in futures.items():
                    self.result[key] = yield future
            else:
                self.result = AttrDict([
                    (key, self.run(stmt, limit)) for key, stmt in stmts.items()])
            self.renderdatas()
        else:
            # Bind query and run it
            args = {key: self.getq(key, [''])[0] for key in self.query._bindparams}
            stmt = self.query.bindparams(**{k: v for k, v in args.items()
                                            if k in self.query._bindparams})
            if self.thread:
                self.result = yield gramex.service.threadpool.submit(self.run, stmt, limit)
            else:
                self.result = self.run(stmt, limit)
            self.renderdata()
