"""
### BEGIN NODE INFO
[info]
name = okfpga
version = 1.0
description = 
instancename = %LABRADNODE%_okfpga

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import json
import numpy as np

import ok
from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue

class OKFPGAServer(LabradServer):
    name = '%LABRADNODE%_okfpga'
    @setting(1, device_id='s', returns='b')
    def open(self, c, device_id):
        fp = ok.FrontPanel()
        module_count = fp.GetDeviceCount()
        print "found {} unused devices".format(module_count)
        for i in range(module_count):
            serial = fp.GetDeviceListSerial(i)
            tmp = ok.FrontPanel()
            tmp.OpenBySerial(serial)
            iden = tmp.GetDeviceID()
            if iden == device_id:
                c['xem'] = tmp
                print 'connected to {}'.format(iden)
                c['xem'].LoadDefaultPLLConfiguration() 
                return True
        return False

    @setting(2, returns='b')
    def close(self, c):
        if c.has_key('xem'):
            xem = c.pop('xem')
#            xem = None
        return True
    
    @setting(3, filename='s')
    def program_bitfile(self, c, filename):
        error = c['xem'].ConfigureFPGA(filename)
        if error:
            print "unable to program sequencer"
            return False
        return True
    
    @setting(11, wire='i', byte_array='*i')
    def write_to_pipe_in(self, c, wire, byte_array):
        c['xem'].WriteToPipeIn(wire, bytearray(byte_array))

    @setting(12, wire='i', value='i')
    def set_wire_in(self, c, wire, value):
        c['xem'].SetWireInValue(wire, value)
    
    @setting(13)
    def update_wire_ins(self, c):
        c['xem'].UpdateWireIns()

if __name__ == "__main__":
    __server__ = OKFPGAServer()