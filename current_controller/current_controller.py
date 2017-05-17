"""
### BEGIN NODE INFO
[info]
name = current_controller
version = 1.0
description = 
instancename = current_controller

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""
import sys

from labrad.server import Signal, setting
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.reactor import callLater
from twisted.internet import reactor

sys.path.append('../')
from server_tools.device_server import DeviceServer
from server_tools.decorators import quickSetting

UPDATE_ID = 698027
reactor.suggestThreadPoolSize(30)

class CurrentControllerServer(DeviceServer):
    """ Provides basic control for current controllers """
    update = Signal(UPDATE_ID, 'signal: update', 's')
    name = 'current_controller'

    @quickSetting(10, 'b')
    def state(self, c, state=None):
        """ get or update state """

    @quickSetting(11, 'b')
    def shutter_state(self, c, state=None):
        """ get or update shutter state """

    @quickSetting(12, 'v')
    def current(self, c, current=None):
        """ get or update current """

    @quickSetting(13, 'v')
    def power(self, c, power=None):
        """ get or update power """

    @setting(14, warmup='b', returns='b')
    def warmup(self, c, warmup=True):
        device = self.get_device(c)
        if warmup:
            update_delay = yield device.warmup()
        callLater(update_delay, self.send_update, c)
        returnValue(warmup)

    @setting(15, delta_day='i', hour='i', returns='i')
    def queue_warmup(self, c, delta_day=0, hour=10):
        device = self.get_device(c)
        delay = seconds_til_start(delta_day, hour)
        warmup_call = callLater(delay, self.warmup, c)
        device.delayed_calls.append(warmup_call)
        return delay

    @setting(16, shutdown='b', returns='b')
    def shutdown(self, c, shutdown=True):
        device = self.get_device(c)
        if shutdown:
            update_delay = yield device.shutdown()
        callLater(update_delay, self.send_update, c)
        returnValue(shutdown)

 #   @inlineCallbacks
#    def get_power(self):
#        yield self.connection.write_line('Power?')
#        ans = yield self.connection.read_lines()
#        print ans
#        returnValue(float(ans[0]))





if __name__ == '__main__':
    from labrad import util
    util.runServer(CurrentControllerServer())
