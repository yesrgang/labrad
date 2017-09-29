class ControlConfig(object):
    def __init__(self):
        self.servername = 'rf'
        self.name = 'alpha'
        self.update_id = 461013

        self.frequency_display_units = [(9, 'GHz')]
        self.frequency_digits = 6
        self.amplitude_display_units = [(0, 'dBm')]
        self.amplitude_digits = 2
        self.update_time = 100

        # widget sizes
        self.spinbox_width = 100

if __name__ == '__main__':
    import sys
    sys.path.append('../../client_tools')
    from PyQt4 import QtGui
    from rf_control import RFControl
    a = QtGui.QApplication([])
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    widget = RFControl('alpha_rf_control', reactor)
    widget.show()
    reactor.run()
