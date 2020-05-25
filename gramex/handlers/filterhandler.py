import gramex.data
from .formhandler import FormHandler


class FilterHandler(FormHandler):
    data_filter_method = staticmethod(gramex.data.filtercols)
