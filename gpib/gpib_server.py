"""
### BEGIN NODE INFO
[info]
name = gpib
version = 1
description =
instancename = %LABRADNODE%_gpib

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys

import visa

from labrad.server import LabradServer, setting

from server_tools.hardware_interface_server import HardwareInterfaceServer


class GPIBServer(HardwareInterfaceServer):
    """Provides direct access to GPIB-enabled hardware."""
    name = '%LABRADNODE%_gpib'

    def refresh_available_interfaces(self):
        """ fill self.interfaces with available connections """
        rm = visa.ResourceManager()
        addresses = rm.list_resources()
        additions = set(addresses) - set(self.interfaces.keys())
        deletions = set(self.interfaces.keys()) - set(addresses)
        for address in additions:
            if address.startswith('GPIB'):
                inst = rm.get_instrument(address)
                inst.write_termination = ''
                inst.clear()
                self.interfaces[address] = inst
                print 'connected to GPIB device ' + address
        for addr in deletions:
            del self.interfaces[addr]

    @setting(3, data='s', returns='')
    def write(self, c, data):
        """Write a string to the GPIB bus."""
        connection = self.get_connection(c)
        self.call_if_available('write', c, data)

    @setting(4, n_bytes='w', returns='s')
    def read(self, c, n_bytes=None):
        """Read from the GPIB bus.

        If specified, reads only the given number of bytes.
        Otherwise, reads until the device stops sending.
        """
        ans = self.call_if_available('read_raw', c)
        return str(ans).strip()

    @setting(5, data='s', returns='s')
    def query(self, c, data):
        """Make a GPIB query, a write followed by a read.

        This query is atomic.  No other communication to the
        device will occur while the query is in progress.
        """
        connection = self.get_connection(c)
        self.call_if_available('write', data)
        ans = self.call_if_available('read_raw')
        return str(ans).strip()

if __name__ == '__main__':
    from labrad import util
    util.runServer(GPIBServer())
