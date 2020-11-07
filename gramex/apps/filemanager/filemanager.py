from gramex import conf
from gramex.config import app_log


def get_drive_urls(handler):
    '''
    Return tuple of ((drive_name, drive_config)) requested by filemanager app.
    If no drives are requested, returns all DriveHandlers.
    '''
    fm_kwargs = handler.kwargs.get('filemanager_kwargs', '') or {}
    drives = []
    if 'drives' not in fm_kwargs:
        for key, config in conf.url.items():
            if config.get('handler', '') == 'DriveHandler':
                drives.append((key, config))
    else:
        for drive in fm_kwargs['drives']:
            if drive not in conf.url:
                app_log.error(f'filemanager: No url: "{drive}" in gramex.yaml')
            elif conf.url[drive].get('handler', '') != 'DriveHandler':
                app_log.error(f'filemanager: rl: "{drive}" is not a DriveHandler')
            else:
                drives.append((drive, conf.url[drive]))
    return drives
