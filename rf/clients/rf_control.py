import json
import numpy as np
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('../../client_tools')
from connection import connection
from widgets import SuperSpinBox

class RFControl(QtGui.QGroupBox):
    def __init__(self, config, reactor, cxn=None):
        QtGui.QDialog.__init__(self)
        self.reactor = reactor
        self.cxn = cxn 
        self.load_config(config)
        self.connect()

    def load_config(self, config=None):
        if type(config).__name__ == 'str':
            config = __import__(config).ControlConfig()
        if config is not None:
            self.config = config
        for key, value in self.config.__dict__.items():
            setattr(self, key, value)

    @inlineCallbacks
    def connect(self):
        if self.cxn is None:
            self.cxn = connection()
            yield self.cxn.connect()
        self.context = yield self.cxn.context()
        yield self.select_device()
        self.populateGUI()
        yield self.connectSignals()
        yield self.requestValues()

    @inlineCallbacks
    def select_device(self):
        server = yield self.cxn.get_server(self.servername)
        config = yield server.select_device(self.name)
        for key, value in json.loads(config).items():
            setattr(self, key, value)
        self.load_config()
    
    def populateGUI(self):
        self.state_button = QtGui.QPushButton()
        self.state_button.setCheckable(1)
        
        self.frequency_box = SuperSpinBox(self.frequency_range, 
                                          self.frequency_display_units, 
                                          self.frequency_digits)
        self.frequency_box.setFixedWidth(self.spinbox_width)
        self.frequency_box.display(0)
        
        self.amplitude_box = SuperSpinBox(self.amplitude_range, 
                                          self.amplitude_display_units, 
                                          self.amplitude_digits)
        self.amplitude_box.setFixedWidth(self.spinbox_width)
        self.amplitude_box.display(0)

        self.layout = QtGui.QGridLayout()
        
        row = 0
        self.layout.addWidget(QtGui.QLabel('<b>'+self.name+'</b>'), 
                              0, 0, 1, 1, QtCore.Qt.AlignHCenter)
        if 'state' in self.update_parameters:
            self.layout.addWidget(self.state_button, 0, 1)
        else:
            self.layout.addWidget(QtGui.QLabel('always on'), 
                                  0, 0, 1, 1, QtCore.Qt.AlignHCenter)
        if 'frequency' in self.update_parameters:
            row += 1
            self.layout.addWidget(QtGui.QLabel('Frequency: '), 
                                  row, 0, 1, 1, QtCore.Qt.AlignRight)
            self.layout.addWidget(self.frequency_box, row, 1)
        if 'amplitude' in self.update_parameters:
            row += 1
            self.layout.addWidget(QtGui.QLabel('Amplitude: '), 
                                  row, 0, 1, 1, QtCore.Qt.AlignRight)
            self.layout.addWidget(self.amplitude_box, row, 1)

        self.setWindowTitle(self.name + '_control')
        self.setLayout(self.layout)
        self.setFixedSize(100 + self.spinbox_width, 100)

    @inlineCallbacks
    def connectSignals(self):
        self.hasNewState = False
        self.hasNewFrequency = False
        self.hasNewAmplitude = False
        server = yield self.cxn.get_server(self.servername)
        yield server.signal__update(self.update_id)
        yield server.addListener(listener=self.receive_update, source=None, 
                                 ID=self.update_id)
        yield self.cxn.add_on_connect(self.servername, self.reinitialize)
        yield self.cxn.add_on_disconnect(self.servername, self.disable)

        self.state_button.released.connect(self.onNewState)
        self.frequency_box.returnPressed.connect(self.onNewFrequency)
        self.amplitude_box.returnPressed.connect(self.onNewAmplitude)
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.writeValues)
        self.timer.start(self.update_time)

    @inlineCallbacks
    def requestValues(self, c=None):
        server = yield self.cxn.get_server(self.servername)
        for parameter in self.update_parameters:
            yield getattr(server, parameter)()
 
    def receive_update(self, c, signal):
        signal = json.loads(signal)
        for name, d in signal.items():
            self.free = False
            if name == self.name:
                if 'state' in self.update_parameters:
                    if d['state']:
                        self.state_button.setChecked(1)
                        self.state_button.setText('On')
                    else:
                        self.state_button.setChecked(0)
                        self.state_button.setText('Off')
                
                if 'frequency' in self.update_parameters:
                    self.frequency_box.display(d['frequency'])
    
                if 'amplitude' in self.update_parameters:
                    self.amplitude_box.display(d['amplitude'])
        self.free = True
    
    @inlineCallbacks
    def onNewState(self):
        if self.free:
            server = yield self.cxn.get_server(self.servername)
            is_on = yield server.state()
            yield server.state(not is_on)

    def onNewFrequency(self):
        if self.free:
            self.hasNewFrequency = True
   
    def onNewAmplitude(self):
        if self.free:
            self.hasNewAmplitude = True

    @inlineCallbacks
    def writeValues(self):
        if self.hasNewFrequency:
            server = yield self.cxn.get_server(self.servername)
            yield server.frequency(self.frequency_box.value())
            self.hasNewFrequency = False
        elif self.hasNewAmplitude:
            server = yield self.cxn.get_server(self.servername)
            yield server.amplitude(self.amplitude_box.value())
            self.hasNewAmplitude = False
           
    def reinitialize(self):
        self.setDisabled(False)

    def disable(self):
        self.setDisabled(True)

    def closeEvent(self, x):
        self.reactor.stop()

class MultipleRFControl(QtGui.QWidget):
    def __init__(self, config_list, reactor, cxn=None):
        QtGui.QDialog.__init__(self)
        self.config_list = config_list
        self.reactor = reactor
        self.cxn = cxn
        self.connect()
 
    @inlineCallbacks
    def connect(self):
        if self.cxn is None:
            self.cxn = connection()
            yield self.cxn.connect()
        self.context = yield self.cxn.context()
        self.populateGUI()

    def populateGUI(self):
        self.layout = QtGui.QHBoxLayout()
        for config in self.config_list:
            widget = RFControl(config, self.reactor)
            self.layout.addWidget(widget)
        self.setFixedSize(650, 120)
        self.setLayout(self.layout)

    def closeEvent(self, x):
        self.reactor.stop()
