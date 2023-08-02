'''
Install and run Gramex as a Windows service
'''

import io
import os
import sys
import traceback
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import pywintypes
import winerror


class GramexService(win32serviceutil.ServiceFramework):
    # https://stackoverflow.com/a/32440/100904

    # Only one instance of a PythonService.exe can run at a time.
    # https://github.com/tjguk/pywin32/blob/master/win32/src/PythonService.cpp#L1080
    # For multiple Gramex services, subclass this
    _svc_name_ = 'GramexApp'
    _svc_display_name_ = 'Gramex Application'
    _svc_description_ = 'Gramex is a visualization and analytics engine by Gramener'
    _svc_port_ = None

    startup_map = {
        'manual': win32service.SERVICE_DEMAND_START,
        'auto': win32service.SERVICE_AUTO_START,
        'delayed': win32service.SERVICE_AUTO_START,
        'disabled': win32service.SERVICE_DISABLED,
    }

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        import gramex

        gramex.shutdown()
        win32event.SetEvent(self.hWaitStop)
        cwd = win32serviceutil.GetServiceCustomOption(self, 'cwd')
        exe = win32serviceutil.GetServiceCustomOption(self, 'exe')
        gramexpath = win32serviceutil.GetServiceCustomOption(self, 'py')
        msg = f'\nPath: {cwd}. Python: {exe}. Gramex: {gramexpath}'
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, msg),
        )

    def SvcDoRun(self):
        # Change to cwd registry option
        cwd = win32serviceutil.GetServiceCustomOption(self, 'cwd')
        exe = win32serviceutil.GetServiceCustomOption(self, 'exe')
        gramexpath = win32serviceutil.GetServiceCustomOption(self, 'py')
        # Run the app in the cwd (source directory)
        if os.path.exists(cwd):
            typ, err = servicemanager.EVENTLOG_INFORMATION_TYPE, ''
        else:
            typ, err = servicemanager.EVENTLOG_WARNING_TYPE, f'Missing directory: {cwd}.'
            cwd = os.getcwd()
        os.chdir(cwd)
        # Write all print / log messages to service.log in the source directory.
        servicelogfile = os.path.join(cwd, 'service.log')
        sys.stdout = sys.stderr = io.open(servicelogfile, 'a', encoding='utf-8')
        # Log start of service
        servicemanager.LogMsg(
            typ,
            servicemanager.PYS_SERVICE_STARTING,
            (self._svc_name_, f'\n{err}Path: {cwd}. Python: {exe}. Gramex: {gramexpath}'),
        )
        # See https://github.com/tornadoweb/tornado/issues/2608
        if sys.version_info >= (3, 8):
            import asyncio

            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # On Conda, we can't import NumPy because Library\bin is not in PATH. Add it
        try:
            import numpy  # noqa
        except ImportError:
            import re

            conda_path = re.sub(r'\\lib\\site-packages\\win32\\.*', '', sys.executable)
            os.environ['PATH'] = f'{conda_path}\\Library\\bin;{os.environ["PATH"]}'
        # Run Gramex
        try:
            port = self._svc_port_
            import gramex

            gramex.commandline(None if port is None else [f'--listen.port={port}'])
        except Exception:
            typ = servicemanager.EVENTLOG_ERROR_TYPE
            msg = '\n' + ''.join(traceback.format_exc())
            servicemanager.LogMsg(typ, servicemanager.PYS_SERVICE_STOPPED, (self._svc_name_, msg))

    @classmethod
    def setup(cls, cmd, user=None, password=None, startup='manual', cwd=None, wait=0):
        import gramex
        from gramex.config import app_log

        name, service_name = cls._svc_display_name_, cls._svc_name_
        port = getattr(cls, '_svc_port_', None)
        if cwd is None:
            cwd = os.getcwd()
        exe = sys.executable
        gramexpath = os.path.dirname(gramex.__file__)
        path = f'Path: {cwd}. Python: {exe}. Gramex: {gramexpath}. Port {port or "NA"}'
        service_class = win32serviceutil.GetServiceClassString(cls)
        startup = cls.startup_map[startup]
        running = win32service.SERVICE_RUNNING
        if cmd[0] == 'install':
            win32serviceutil.InstallService(
                service_class,
                service_name,
                displayName=name,
                description=cls._svc_description_,
                startType=startup,
                userName=user,
                password=password,
            )
            win32serviceutil.SetServiceCustomOption(cls._svc_name_, 'cwd', cwd)
            win32serviceutil.SetServiceCustomOption(cls._svc_name_, 'exe', exe)
            win32serviceutil.SetServiceCustomOption(cls._svc_name_, 'py', gramexpath)
            app_log.info(f'Installed service. {name} will run from {path}')
        elif cmd[0] in {'update', 'change'}:
            win32serviceutil.ChangeServiceConfig(
                service_class,
                service_name,
                displayName=name,
                description=cls._svc_description_,
                startType=startup,
                userName=user,
                password=password,
            )
            win32serviceutil.SetServiceCustomOption(cls._svc_name_, 'cwd', cwd)
            win32serviceutil.SetServiceCustomOption(cls._svc_name_, 'exe', exe)
            win32serviceutil.SetServiceCustomOption(cls._svc_name_, 'py', gramexpath)
            app_log.info(f'Updated service. {name} will run from {path}')
        elif cmd[0] in {'remove', 'uninstall'}:
            try:
                win32serviceutil.StopService(service_name)
            except pywintypes.error as e:
                if e.args[0] != winerror.ERROR_SERVICE_NOT_ACTIVE:
                    raise
            win32serviceutil.RemoveService(service_name)
            app_log.info(f'Removed service. {name} ran from {path}')
        elif cmd[0] == 'start':
            app_log.info(f'Starting service {name} at {path}')
            win32serviceutil.StartService(service_name, cmd[1:])
            if wait:
                win32serviceutil.WaitForServiceStatus(service_name, running, wait)
        elif cmd[0] == 'stop':
            app_log.info(f'Stopping service {name} at {path}')
            if wait:
                win32serviceutil.StopServiceWithDeps(service_name, waitSecs=wait)
            else:
                win32serviceutil.StopService(service_name)
        elif cmd[0]:
            app_log.error(f'Unknown command: {cmd[0]}')
