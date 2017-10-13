'''
Install and run Gramex as a Windows service
'''

import os
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
    # For multiple Gramex services, use multiple Anaconda installations.
    _svc_name_ = 'GramexApp'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        import gramex
        gramex.shutdown()
        win32event.SetEvent(self.hWaitStop)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STOPPED, (self._svc_name_, ''))

    def SvcDoRun(self):
        # Change to cwd registry option
        cwd = win32serviceutil.GetServiceCustomOption(self, 'cwd')
        if cwd is None:
            typ = servicemanager.EVENTLOG_INFORMATION_TYPE
            msg = ' at ' + os.getcwd() + ' by default'
        else:
            if os.path.exists(cwd):
                os.chdir(cwd)
                typ, msg = servicemanager.EVENTLOG_INFORMATION_TYPE, ' at ' + cwd
            else:
                typ = servicemanager.EVENTLOG_WARNING_TYPE
                msg = ' at ' + os.getcwd() + '. Missing directory: ' + cwd
        # Log start of service
        servicemanager.LogMsg(typ, servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, msg))
        # Run Gramex
        try:
            import gramex
            gramex.commandline()
        except Exception:
            # TODO: log traceback in event log
            pass


startup_map = {
    'manual': win32service.SERVICE_DEMAND_START,
    'auto': win32service.SERVICE_AUTO_START,
    'delayed': win32service.SERVICE_AUTO_START,
    'disabled': win32service.SERVICE_DISABLED,
}
default_desc = 'Gramex is a visualization and analytics engine by Gramener'


def setup(command, args, user=None, password=None, startup='manual',
          name='Gramex Application', desc=default_desc, cwd=None, wait=0):
    from gramex.config import app_log
    service_name = GramexService._svc_name_
    if cwd is None:
        cwd = os.getcwd()
    service_class = win32serviceutil.GetServiceClassString(GramexService)
    startup = startup_map[startup]
    running = win32service.SERVICE_RUNNING
    if command == 'install':
        win32serviceutil.InstallService(
            service_class, service_name, displayName=name, description=desc,
            startType=startup, userName=user, password=password)
        win32serviceutil.SetServiceCustomOption(service_name, 'cwd', cwd)
        app_log.info('Installed service. %s will run from %s' % (name, cwd))
    elif command == 'update':
        win32serviceutil.ChangeServiceConfig(
            service_class, service_name, displayName=name, description=desc,
            startType=startup, userName=user, password=password)
        win32serviceutil.SetServiceCustomOption(service_name, 'cwd', cwd)
        app_log.info('Updated service. %s will run from %s' % (name, cwd))
    elif command in {'remove', 'uninstall'}:
        try:
            win32serviceutil.StopService(service_name)
        except pywintypes.error as e:
            if e.args[0] != winerror.ERROR_SERVICE_NOT_ACTIVE:
                raise
        win32serviceutil.RemoveService(service_name)
        app_log.info('Removed service %s' % service_name)
    elif command == 'start':
        win32serviceutil.StartService(service_name, args)
        if wait:
            win32serviceutil.WaitForServiceStatus(service_name, running, wait)
        app_log.info('Started service %s' % service_name)
    elif command == 'restart':
        win32serviceutil.StartService(service_name, args)
        if wait:
            win32serviceutil.WaitForServiceStatus(service_name, running, wait)
        app_log.info('Restarted service %s' % service_name)
    elif command == 'stop':
        if wait:
            win32serviceutil.StopServiceWithDeps(service_name, waitSecs=wait)
        else:
            win32serviceutil.StopService(service_name)
        app_log.info('Stopped service %s' % service_name)
    elif command:
        app_log.error('Unknown command: %s' % command)
