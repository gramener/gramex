from gramex import conf


def get_drive_urls(handler):
    """Find the drives requested by the filemanager app. By default, return all."""
    fm_kwargs = handler.kwargs.get('filemanager_kwargs', '') or {}
    drives = []
    if 'drives' not in fm_kwargs:
        for key, config in conf.url.items():
            if config.get('handler', '') == 'DriveHandler':
                drives.append((key, config))
    else:
        for d in fm_kwargs['drives']:
            drives.append((d, conf.url.get(d, '')))
    return drives
