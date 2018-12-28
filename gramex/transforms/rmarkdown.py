import tornado.gen


@tornado.gen.coroutine
def rmarkdown(content, handler=None, **kwargs):
    '''
    A transform that converts Rmarkdown files to HTML.

    HTML file is placed at path: $YAMLPATH location.
    '''
    import gramex.ml
    import gramex.cache
    import gramex.services

    rmdfilepath = str(handler.file)
    htmlpath = yield gramex.services.info.threadpool.submit(
        gramex.ml.r,
        '''
        library(rmarkdown)
        rmarkdown::render("{}", output_format="html_document", quiet=TRUE)
        '''.format(rmdfilepath.replace('\\', '/'))
    )
    raise tornado.gen.Return(
        gramex.cache.open(htmlpath[0], 'bin').decode('utf-8'))
