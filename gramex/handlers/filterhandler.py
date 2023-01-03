import gramex.data
from .formhandler import FormHandler


class FilterHandler(FormHandler):
    def data_filter_method(self, *args, **kwargs):
        return gramex.data.filtercols(*args, **kwargs)
