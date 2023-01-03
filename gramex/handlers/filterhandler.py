import gramex.data
from .formhandler import FormHandler


class FilterHandler(FormHandler):
    def data_filter_method(*args, **kwargs):
        gramex.data.filtercols(*args, **kwargs)
