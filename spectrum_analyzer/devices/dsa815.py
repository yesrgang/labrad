import re

from twisted.internet.defer import inlineCallbacks, returnValue

from spectrum_analyzer import SpectrumAnalyzer

class DSA815(SpectrumAnalyzer):
    servername = ''
    @inlineCallbacks
    def set_trace(self, value):
        yield None

    @inlineCallbacks
    def get_trace(self):
        command = ':TRACe:DATA? TRACE{}'.format(self.trace_index)
        ans = yield self.connection.query(command)
        trace = re.compile('^#[0-9]+\s(.+)$').match(ans).group(1).split(', ')
        returnValue([float(s) for s in trace])
   
    @inlineCallbacks
    def get_frequency_range(self):
        start = yield self.connection.query(':SENSe:FREQuency:STARt?')
        stop = yield self.connection.query(':SENSe:FREQuency:STOP?')
        returnValue([float(start), float(stop)])

    @inlineCallbacks
    def set_frequency_range(self, value):
        start_command = ':SENSe:FREQuency:STARt {}'.format(min(value))
        stop_command = ':SENSe:FREQuency:STOP {}'.format(max(value))
        yield self.connection.write(start_command)
        yield self.connection.write(stop_command)

    @inlineCallbacks
    def get_amplitude_scale(self):
        scale = yield self.connection.query(':DISPlay:WINdow:TRACe:Y:SCALe:PDIVision?')
        returnValue(float(scale))
 
    @inlineCallbacks
    def set_amplitude_scale(self, value):
        scale_command = ':DISPlay:WINdow:TRACe:Y:SCALe:PDIVision {}'.format(value)
        yield self.connection.write(scale_command)
    
    @inlineCallbacks
    def get_amplitude_offset(self):
        offset = yield self.connection.query(':DISPlay:WINdow:TRACe:Y:SCALe:RLEVel?')
        returnValue(float(offset))
 
    @inlineCallbacks
    def set_amplitude_offset(self, value):
        offset_command = ':DISPlay:WINdow:TRACe:Y:SCALe:RLEVel {}'.format(value)
        yield self.connection.write(offset_command)
   
    @inlineCallbacks
    def set_resolution_bandwidth(self, value):
        command = ':SENSe:BANDwidth:RESolution {}'.format(value)
        yield self.connection.write(command)

    @inlineCallbacks
    def get_resolution_bandwidth(self):
        command = ':SENSe:BANDwidth:RESolution?'
        resolution_bandwidth = yield self.connection.query(command)
        returnValue(resolution_bandwidth)

