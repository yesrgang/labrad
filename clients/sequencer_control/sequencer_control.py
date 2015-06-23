from PyQt4 import QtGui, QtCore, Qt
#QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
from PyQt4.QtCore import pyqtSignal 
from client_tools import SuperSpinBox
from connection import connection
from twisted.internet.defer import inlineCallbacks
import numpy as np
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

sbwidth = 65
sbheight = 15
pbheight = 20
nlwidth = 30
acheight = 50
nlwidth = 100
pps = 1001

max_columns = 20

class Spacer(QtGui.QFrame):
    def __init__(self, height, width):
        super(Spacer, self).__init__(None)
        self.setFixedSize(width, height)
        self.setFrameShape(1)
        self.setLineWidth(0)

class BrowseAndSave(QtGui.QWidget):
    def __init__(self):
        super(BrowseAndSave, self).__init__(None)
        self.populate()

    def populate(self):
        self.location_box = QtGui.QLineEdit()
        self.browse_button = QtGui.QPushButton('Bro&wse')
        self.save_button = QtGui.QPushButton('&Save')
        self.layout = QtGui.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.location_box)
        self.layout.addWidget(self.browse_button)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)

class SequencerButton(QtGui.QFrame):
    def __init__(self, initial_state):
        super(SequencerButton, self).__init__(None)
        self.setFrameShape(2)
        self.setLineWidth(1)
        if initial_state:
            self.setChecked(1)
        else:
            self.setChecked(0)
    
    def setChecked(self, state):
        if state:
            self.setFrameShadow(0x0030)
            self.setStyleSheet('QWidget {background-color: #c9c9c9}')
            self.is_checked = True
        else:
            self.setFrameShadow(0x0020)
            self.setStyleSheet('QWidget {background-color: #ffffff}')
            self.is_checked = False

    def isChecked(self):
        if self.is_checked:
            return True
        else:
            return False

    def mousePressEvent(self, x):
        if self.is_checked:
            self.setChecked(False)
        else:
            self.setChecked(True)

class DigitalColumn(QtGui.QWidget):
    def __init__(self, channels):
        super(DigitalColumn, self).__init__(None)
        self.channels = channels
        self.populate()

    def populate(self):
        units =  [(0, 's'), (-3, 'ms'), (-6, 'us'), (-9, 'ns')]
        self.sequencer_buttons = {n: SequencerButton(0) for n in self.channels.values()}

        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        for i, (c, n) in enumerate(sorted(self.channels.items())):
            if not i%16 and i != 0:
                self.layout.addWidget(Spacer(sbheight/2, sbwidth))
            self.layout.addWidget(self.sequencer_buttons[n])
        self.layout.addWidget(QtGui.QWidget())
        self.setLayout(self.layout)
        height = 0
        for i in range(self.layout.count()):
            height += self.layout.itemAt(i).widget().height()

    def get_logic(self):
#        print {n: int(self.sequencer_buttons[n].isChecked()) for n in self.channels.values()}
        return {n: int(self.sequencer_buttons[n].isChecked()) for n in self.channels.values()}

    def set_logic(self, logic):
        for name, state in logic.items():
            if name in self.channels.values():
                self.sequencer_buttons[name].setChecked(state)

class DigitalArray(QtGui.QWidget):
    def __init__(self, channels):
        super(DigitalArray, self).__init__(None)
        self.channels = channels
        self.populate()

    def populate(self):
        self.digital_columns = [DigitalColumn(self.channels) for i in range(20)]
        self.layout = QtGui.QHBoxLayout()
        for lc in self.digital_columns:
            self.layout.addWidget(lc)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        height = self.digital_columns[0].height()
        width = self.digital_columns[0].width()*10

class NameBox(QtGui.QLabel):
    def __init__(self, name):
        super(NameBox, self).__init__(None)
        self.setText(name)
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter  )

class DigitalNameColumn(QtGui.QWidget):
    def __init__(self, channels):
        super(DigitalNameColumn, self).__init__(None)
        self.channels = channels
        self.populate()

    def populate(self):
        self.name_boxes = {n: NameBox(c+': '+n) for c, n in self.channels.items()}
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        for i, (c, n) in enumerate(sorted(self.channels.items())):
            if not i%16 and i != 0:
                self.layout.addWidget(Spacer(sbheight/2, nlwidth))
            self.layout.addWidget(self.name_boxes[n])
        self.layout.addWidget(QtGui.QWidget())
        self.setLayout(self.layout)

class DurationRow(QtGui.QWidget):
    def __init__(self):
        super(DurationRow, self).__init__(None)
        self.populate()

    def populate(self):
        units =  [(0, 's'), (-3, 'ms'), (-6, 'us'), (-9, 'ns')]
        self.duration_boxes = [SuperSpinBox([500e-9, 10], units) for i in range(20)]
        self.layout = QtGui.QHBoxLayout()
        for db in self.duration_boxes:
            self.layout.addWidget(db)
        self.setLayout(self.layout)
        
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

class AddDltButton(QtGui.QWidget):
    def __init__(self):
        super(AddDltButton, self).__init__(None)
        self.add = QtGui.QPushButton('+')
        self.dlt = QtGui.QPushButton('-')
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.add)
        self.layout.addWidget(self.dlt)
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

class AddDltRow(QtGui.QWidget):
    def __init__(self):
        super(AddDltRow, self).__init__(None)
        self.populate()

    def populate(self):
        self.add_dlt_buttons = [AddDltButton() for i in range(20)]
        self.layout = QtGui.QHBoxLayout()
        for ad in self.add_dlt_buttons:
            self.layout.addWidget(ad)
        self.setLayout(self.layout)
        
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

class Sequencer(QtGui.QWidget):
    def __init__(self, digital_channels, analog_channels):
        super(Sequencer, self).__init__(None)
        self.digital_channels = digital_channels
        self.analog_channels = analog_channels
        self.populate()
        self.connect_widgets()

    def populate(self):
        self.browse_and_save = BrowseAndSave()
        self.duration_row = DurationRow()
        self.digital_name_column = DigitalNameColumn(self.digital_channels)
        self.digital_array = DigitalArray(self.digital_channels)
        self.analog_name_column = AnalogNameColumn(self.analog_channels)
        self.analog_array = AnalogArray(self.analog_channels)
        self.add_dlt_row = AddDltRow()

        self.duration_scroll = QtGui.QScrollArea()
        self.duration_scroll.setWidget(self.duration_row)
        self.duration_scroll.setWidgetResizable(True)
        self.duration_scroll.setHorizontalScrollBarPolicy(1)
        self.duration_scroll.setVerticalScrollBarPolicy(1)
        self.duration_scroll.setFrameShape(0)
        self.digital_name_scroll = QtGui.QScrollArea()
        self.digital_name_scroll.setWidget(self.digital_name_column)
        self.digital_name_scroll.setWidgetResizable(True)
        self.digital_name_scroll.setHorizontalScrollBarPolicy(1)
        self.digital_name_scroll.setVerticalScrollBarPolicy(1)
        self.digital_name_scroll.setFrameShape(0)
        self.digital_scroll = QtGui.QScrollArea()
        self.digital_scroll.setWidget(self.digital_array)
        self.digital_scroll.setWidgetResizable(True)
        self.digital_scroll.setHorizontalScrollBarPolicy(1)
        self.digital_scroll.setVerticalScrollBarPolicy(1)
        self.digital_scroll.setFrameShape(0)
        self.analog_name_scroll = QtGui.QScrollArea()
        self.analog_name_scroll.setWidget(self.analog_name_column)
        self.analog_name_scroll.setWidgetResizable(True)
        self.analog_name_scroll.setHorizontalScrollBarPolicy(1)
        self.analog_name_scroll.setVerticalScrollBarPolicy(1)
        self.analog_name_scroll.setFrameShape(0)
        self.analog_array_scroll = QtGui.QScrollArea()
        self.analog_array_scroll.setWidget(self.analog_array)
        self.analog_array_scroll.setWidgetResizable(True)
        self.analog_array_scroll.setHorizontalScrollBarPolicy(1)
        self.analog_array_scroll.setVerticalScrollBarPolicy(1)
        self.analog_array_scroll.setFrameShape(0)
        self.add_dlt_scroll = QtGui.QScrollArea()
        self.add_dlt_scroll.setWidget(self.add_dlt_row)
        self.add_dlt_scroll.setWidgetResizable(True)
        self.add_dlt_scroll.setHorizontalScrollBarPolicy(1)
        self.add_dlt_scroll.setVerticalScrollBarPolicy(1)
        self.add_dlt_scroll.setFrameShape(0)
        self.digital_vscroll = QtGui.QScrollArea()
        self.digital_vscroll.setWidget(QtGui.QWidget())
        self.digital_vscroll.setWidgetResizable(True)
        self.analog_vscroll = QtGui.QScrollArea()
        self.analog_vscroll.setWidget(QtGui.QWidget())
        self.analog_vscroll.setWidgetResizable(True)
        self.hscroll = QtGui.QScrollArea()
        self.hscroll.setWidget(QtGui.QWidget())
        self.hscroll.setWidgetResizable(True)
        self.name_hscroll = QtGui.QScrollArea()
        self.name_hscroll.setWidget(QtGui.QWidget())
        self.name_hscroll.setWidgetResizable(True)

        self.north_layout = QtGui.QGridLayout()
        self.northwest_widget = QtGui.QWidget()
        self.northeast_widget = QtGui.QWidget()
        self.north_layout.addWidget(self.northwest_widget, 0, 0, 2, 1)
        self.north_layout.addWidget(self.browse_and_save, 0, 1)
        self.north_layout.addWidget(self.duration_scroll, 1, 1)
        self.north_layout.addWidget(self.northeast_widget, 0, 2, 2, 1)
        self.north_layout.setContentsMargins(0, 0, 0, 0)
        self.north_layout.setSpacing(0)
        self.north_widget = QtGui.QWidget()
        self.north_widget.setLayout(self.north_layout)
        self.digital_layout = QtGui.QHBoxLayout()
        self.digital_layout.addWidget(self.digital_name_scroll)
        self.digital_layout.addWidget(self.digital_scroll)
        self.digital_layout.addWidget(self.digital_vscroll)
        self.digital_layout.setContentsMargins(0, 0, 0, 0)
        self.digital_layout.setSpacing(0)
        self.digital_widget = QtGui.QWidget()
        self.digital_widget.setLayout(self.digital_layout)
        self.analog_layout = QtGui.QHBoxLayout()
        self.analog_layout.addWidget(self.analog_name_scroll)
        self.analog_layout.addWidget(self.analog_array_scroll)
        self.analog_layout.addWidget(self.analog_vscroll)
        self.analog_layout.setContentsMargins(0, 0, 0, 0)
        self.analog_layout.setSpacing(0)
        self.analog_widget = QtGui.QWidget()
        self.analog_widget.setLayout(self.analog_layout)
        self.south_layout = QtGui.QGridLayout()
        self.southwest_widget = QtGui.QWidget()
        self.southeast_widget = QtGui.QWidget()
        self.south_layout.addWidget(self.name_hscroll, 1, 0)
        self.south_layout.addWidget(self.southwest_widget, 0, 0, 1, 1)
        self.south_layout.addWidget(self.add_dlt_scroll, 0, 1)
        self.south_layout.addWidget(self.hscroll, 1, 1)
        self.south_layout.addWidget(self.southeast_widget, 0, 2, 2, 1)
        self.south_layout.setContentsMargins(0, 0, 0, 0)
        self.south_layout.setSpacing(0)
        self.south_widget = QtGui.QWidget()
        self.south_widget.setLayout(self.south_layout)

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.digital_widget)
        self.splitter.addWidget(self.analog_widget)
        
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.north_widget)
        self.layout.addWidget(self.splitter)
        self.layout.addWidget(self.south_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        self.set_sizes()

    def set_sizes(self):
        self.northwest_widget.setFixedWidth(nlwidth)
        self.northeast_widget.setFixedWidth(20)
        self.southwest_widget.setFixedWidth(nlwidth)
        self.southeast_widget.setFixedWidth(20)
        self.browse_and_save.setFixedSize(10*sbwidth, 40)

        for db in self.duration_row.duration_boxes:
            db.setFixedSize(sbwidth, 20)
        dr_width = sum([db.width() for db in self.duration_row.duration_boxes if not db.isHidden()])
        self.duration_row.setFixedSize(dr_width, 20)
        
        for lc in self.digital_array.digital_columns:
            for b in lc.sequencer_buttons.values():
                b.setFixedSize(sbwidth, sbheight)
            height = sum([lc.layout.itemAt(i).widget().height() for i in range(lc.layout.count()-1)]) # -1 because there is a generic widget in the last spot
            lc.setFixedSize(sbwidth, height)
        la_width = sum([lc.width() for lc in self.digital_array.digital_columns if not lc.isHidden()])
        la_height = self.digital_array.digital_columns[0].height()
        self.digital_array.setFixedSize(la_width, la_height)

        for nb in self.digital_name_column.name_boxes.values():
            nb.setFixedHeight(sbheight)
#            nb.setFixedSize(nlwidth, sbheight)
        nc_width = nlwidth
        nc_height = self.digital_array.height()

        for adb in self.add_dlt_row.add_dlt_buttons:
            adb.setFixedSize(sbwidth, 15)
        ad_width = sum([adb.width() for adb in self.add_dlt_row.add_dlt_buttons if not adb.isHidden()])
        self.add_dlt_row.setFixedSize(ad_width, 15)
        
        self.digital_vscroll.widget().setFixedHeight(self.digital_array.height())
        self.digital_widget.setMaximumHeight(self.digital_array.height())
        self.digital_vscroll.setFixedWidth(20)
        self.hscroll.widget().setFixedWidth(self.digital_array.width())
        self.hscroll.setFixedHeight(20)
        
        self.duration_scroll.setFixedHeight(25)
        self.add_dlt_scroll.setFixedHeight(15)
        
        self.digital_name_column.setFixedHeight(self.digital_array.height())
        self.digital_name_scroll.setFixedWidth(nlwidth)
        
        for anl in self.analog_name_column.labels.values():
            anl.setFixedHeight(acheight)
#            anl.setFixedSize(nlwidth, acheight))

        self.analog_name_column.setFixedSize(nlwidth, self.analog_array.height())
        self.analog_name_scroll.setFixedWidth(nlwidth)
        self.analog_array.setFixedSize(la_width, acheight*len(self.analog_channels.items()))
        self.analog_vscroll.widget().setFixedHeight(self.analog_array.height())
        self.analog_vscroll.setFixedWidth(20)
        
        self.name_hscroll.widget().setFixedWidth(self.analog_name_scroll.width())
        self.name_hscroll.setFixedWidth(nlwidth)
        self.name_hscroll.setFixedHeight(20)
        max_height = self.north_widget.height()+self.digital_array.height()+self.analog_array.height()+self.add_dlt_row.height()+self.hscroll.height()

        self.setMaximumHeight(max_height)
        
    def connect_widgets(self):
        self.digital_vscroll.verticalScrollBar().valueChanged.connect(self.adjust_for_dvscroll)
        self.analog_vscroll.verticalScrollBar().valueChanged.connect(self.adjust_for_avscroll)
        self.hscroll.horizontalScrollBar().valueChanged.connect(self.adjust_for_hscroll)
        self.name_hscroll.horizontalScrollBar().valueChanged.connect(self.adjust_for_nhscroll)

        self.browse_and_save.save_button.clicked.connect(self.save_sequence)
        self.browse_and_save.browse_button.clicked.connect(self.browse)
#
#        for i, adb in enumerate(self.add_dlt_row.add_dlt_buttons):
#            adb.add.clicked.connect(self.add_column(i))
#            adb.dlt.clicked.connect(self.dlt_column(i))

    def adjust_for_dvscroll(self):
        val = self.digital_vscroll.verticalScrollBar().value()
        self.digital_name_scroll.verticalScrollBar().setValue(val)
        self.digital_scroll.verticalScrollBar().setValue(val)
    
    def adjust_for_avscroll(self):
        val = self.analog_vscroll.verticalScrollBar().value()
        self.analog_name_scroll.verticalScrollBar().setValue(val)
        self.analog_array_scroll.verticalScrollBar().setValue(val)

    def adjust_for_hscroll(self):
        val = self.hscroll.horizontalScrollBar().value()
        self.duration_scroll.horizontalScrollBar().setValue(val)
        self.digital_scroll.horizontalScrollBar().setValue(val)
        self.analog_array_scroll.horizontalScrollBar().setValue(val)
        self.add_dlt_scroll.horizontalScrollBar().setValue(val)
    
    def adjust_for_nhscroll(self):
        val = self.name_hscroll.horizontalScrollBar().value()
        self.digital_name_scroll.horizontalScrollBar().setValue(val)
        self.analog_name_scroll.horizontalScrollBar().setValue(val)

    def get_sequence(self):
        digital_sequence = [(db.value(), lc.get_logic()) for db, lc in zip(self.duration_row.duration_boxes, self.digital_array.digital_columns) if not lc.isHidden()]
        analog_sequence = self.analog_array.sequence
        print sorted(digital_sequence[0])
        for i, (t, d) in enumerate(digital_sequence):
            for ac in self.analog_array.channels.values():
                d.update((ac, self.analog_array.sequence[i][1][ac]))
        print sorted(digital_sequence[0])

        return digital_sequence

    def save_sequence(self):
        sequence = [str(seq) + '\n' for seq in self.get_sequence()]
        outfile = open(self.browse_and_save.location_box.text(), 'w')
        outfile.write(''.join(sequence))

    def browse(self):
        file_name = QtGui.QFileDialog().getOpenFileName()
        self.browse_and_save.location_box.setText(file_name)
        self.load_sequence(file_name)

    def load_sequence(self, file_name):
        infile = open(file_name, 'r')
        sequence = [eval(line.split('\n')[:-1][0]) for line in infile.readlines()]
        self.set_sequence(sequence)

    def set_sequence(self, sequence):
        self.analog_array.load_sequence(sequence)
        for db, lc, ad in zip(self.duration_row.duration_boxes, self.digital_array.digital_columns, self.add_dlt_row.add_dlt_buttons)[::-1]:
            db.hide()
            lc.hide()
            ad.hide()
        for info, db, lc, ad in zip(sequence, self.duration_row.duration_boxes, self.digital_array.digital_columns, self.add_dlt_row.add_dlt_buttons):
            t, l = info
            db.show()
            lc.show()
            ad.show()
            db.display(t)
            lc.set_logic(l)

        self.set_sizes()




#class DigitalSequencer0(QtGui.QWidget):
#    def __init__(self, channels):
#        super(DigitalSequencer, self).__init__(None)
#        self.channels = channels
#        self.populate()
#        self.connect_widgets()
#
#    def populate(self):
#        self.browse_and_save = BrowseAndSave()
#        self.duration_row = DurationRow()
#        self.name_column = DigitalNameColumn(self.channels)
#        self.digital_array = DigitalArray(self.channels)
#        self.add_dlt_row = AddDltRow()
#
#        self.name_scroll = QtGui.QScrollArea()
#        self.name_scroll.setWidget(self.name_column)
#        self.name_scroll.setWidgetResizable(True)
#        self.logic_scroll = QtGui.QScrollArea()
#        self.logic_scroll.setWidget(self.digital_array)
#        self.logic_scroll.setWidgetResizable(True)
#        self.duration_scroll = QtGui.QScrollArea()
#        self.duration_scroll.setWidget(self.duration_row)
#        self.duration_scroll.setWidgetResizable(True)
#        self.add_dlt_scroll = QtGui.QScrollArea()
#        self.add_dlt_scroll.setWidget(self.add_dlt_row)
#        self.add_dlt_scroll.setWidgetResizable(True)
#
#        self.vscroll = QtGui.QScrollArea()
#        self.vscroll.setWidget(QtGui.QWidget())
#        self.vscroll.setWidgetResizable(True)
#        
#        self.hscroll = QtGui.QScrollArea()
#        self.hscroll.setWidget(QtGui.QWidget())
#        self.hscroll.setWidgetResizable(True)
#
#        self.layout = QtGui.QGridLayout()
#        self.layout.addWidget(self.browse_and_save, 0, 1)
#        self.layout.addWidget(self.duration_scroll, 1, 1)
#        self.layout.addWidget(self.name_scroll, 2, 0)
#        self.layout.addWidget(self.logic_scroll, 2, 1)
#        self.layout.addWidget(self.add_dlt_scroll, 3, 1)
#        self.layout.addWidget(self.vscroll, 2, 2)
#        self.layout.addWidget(self.hscroll, 4, 1)
#        self.setLayout(self.layout)
#        
#        self.duration_scroll.setHorizontalScrollBarPolicy(1)
#        self.duration_scroll.setVerticalScrollBarPolicy(1)
#        self.duration_scroll.setFrameShape(0)
#
#        self.name_scroll.setHorizontalScrollBarPolicy(1)
#        self.name_scroll.setVerticalScrollBarPolicy(1)
#        self.name_scroll.setMaximumWidth(100)
#        self.name_scroll.setFrameShape(0)
#        
#        self.logic_scroll.setHorizontalScrollBarPolicy(1)
#        self.logic_scroll.setVerticalScrollBarPolicy(1)
#        self.logic_scroll.setFrameShape(0)
#        
#        self.add_dlt_scroll.setHorizontalScrollBarPolicy(1)
#        self.add_dlt_scroll.setVerticalScrollBarPolicy(1)
#        self.add_dlt_scroll.setFrameShape(0)
#        
#        self.vscroll.setHorizontalScrollBarPolicy(1)
#        self.vscroll.setVerticalScrollBarPolicy(2)
#        self.vscroll.setFrameShape(0)
#        
#        self.hscroll.setHorizontalScrollBarPolicy(2)
#        self.hscroll.setVerticalScrollBarPolicy(1)
#        self.hscroll.setFrameShape(0)
#        
#        self.layout.setSpacing(0)
#        #self.layout.setContentsMargins(10, 10, 10, 10)
#        self.set_sizes()
#
#    def set_sizes(self):
#        self.browse_and_save.setFixedSize(10*sbwidth, 40)
#
#        for db in self.duration_row.duration_boxes:
#            db.setFixedSize(sbwidth, 20)
#        dr_width = sum([db.width() for db in self.duration_row.duration_boxes if not db.isHidden()])
#        self.duration_row.setFixedSize(dr_width, 20)
#        
#        for lc in self.digital_array.digital_columns:
#            for b in lc.sequencer_buttons.values():
#                b.setFixedSize(sbwidth, sbheight)
#            height = sum([lc.layout.itemAt(i).widget().height() for i in range(lc.layout.count()-1)]) # -1 because there is a generic widget in the last spot
#            lc.setFixedSize(sbwidth, height)
#        la_width = sum([lc.width() for lc in self.digital_array.digital_columns if not lc.isHidden()])
#        la_height = self.digital_array.digital_columns[0].height()
#        self.digital_array.setFixedSize(la_width, la_height)
#
#        for nb in self.name_column.name_boxes.values():
#            nb.setFixedSize(nlwidth, sbheight)
#        nc_width = nlwidth
#        nc_height = self.digital_array.height()
#
#        for adb in self.add_dlt_row.add_dlt_buttons:
#            adb.setFixedSize(sbwidth, 15)
#        ad_width = sum([adb.width() for adb in self.add_dlt_row.add_dlt_buttons if not adb.isHidden()])
#        self.add_dlt_row.setFixedSize(ad_width, 15)
#        
#        self.vscroll.widget().setFixedHeight(self.digital_array.height())
#        self.vscroll.setFixedWidth(20)
#        self.hscroll.widget().setFixedWidth(self.digital_array.width())
#        self.hscroll.setFixedHeight(20)
#        
#        self.duration_scroll.setFixedHeight(25)
#        self.add_dlt_scroll.setFixedHeight(15)
#        
#        self.name_column.setFixedHeight(self.digital_array.height())
#        self.name_scroll.setFixedWidth(100)
#        
#        height = self.duration_scroll.height() + self.digital_array.height() + self.add_dlt_scroll.height() + self.hscroll.height()
#        self.setMaximumHeight(1000)
#
#    def connect_widgets(self):
#        self.vscroll.verticalScrollBar().valueChanged.connect(self.adjust_for_vscroll)
#        self.hscroll.horizontalScrollBar().valueChanged.connect(self.adjust_for_hscroll)
#
#        self.browse_and_save.save_button.clicked.connect(self.save_sequence)
#        self.browse_and_save.browse_button.clicked.connect(self.browse)
#
#        for i, adb in enumerate(self.add_dlt_row.add_dlt_buttons):
#            adb.add.clicked.connect(self.add_column(i))
#            adb.dlt.clicked.connect(self.dlt_column(i))
#
#    def adjust_for_vscroll(self):
#        val = self.vscroll.verticalScrollBar().value()
#        self.name_scroll.verticalScrollBar().setValue(val)
#        self.logic_scroll.verticalScrollBar().setValue(val)
#
#    def adjust_for_hscroll(self):
#        val = self.hscroll.horizontalScrollBar().value()
#        self.duration_scroll.horizontalScrollBar().setValue(val)
#        self.logic_scroll.horizontalScrollBar().setValue(val)
#        self.add_dlt_scroll.horizontalScrollBar().setValue(val)
#
#    def get_sequence_info(self):
#        infos = [(db.value(), lc.get_logic()) for db, lc in zip(self.duration_row.duration_boxes, self.digital_array.digital_columns) if not lc.isHidden()]
#        return infos
#
#    def save_sequence(self):
#        infos = [str(info) + '\n' for info in self.get_sequence_info()]
#        outfile = open(self.browse_and_save.location_box.text(), 'w')
#        outfile.write(''.join(infos))
#
#    def browse(self):
#        file_name = QtGui.QFileDialog().getOpenFileName()
#        self.browse_and_save.location_box.setText(file_name)
#        self.load_sequence(file_name)
#
#    def load_sequence(self, file_name):
#        infile = open(file_name, 'r')
#        infos = [eval(line.split('\n')[:-1][0]) for line in infile.readlines()]
#        self.set_sequence_info(infos)
#
#    def set_sequence_info(self, infos):
#        for db, lc, ad in zip(self.duration_row.duration_boxes, self.digital_array.digital_columns, self.add_dlt_row.add_dlt_buttons)[::-1]:
#            db.hide()
#            lc.hide()
#            ad.hide()
#        for info, db, lc, ad in zip(infos, self.duration_row.duration_boxes, self.digital_array.digital_columns, self.add_dlt_row.add_dlt_buttons):
#            t, l = info
#            db.show()
#            lc.show()
#            ad.show()
#            db.display(t)
#            lc.set_logic(l)
#
#        self.set_sizes()
#
#    def add_column(self, i):
#        def ar():
#            infos = self.get_sequence_info()
#            infos.insert(i, infos[i])
#            self.set_sequence_info(infos)
#        return ar
#
#    def dlt_column(self, i):
#        def dr():
#            infos = self.get_sequence_info()
#            infos.pop(i)
#            self.set_sequence_info(infos)
#        return dr

class DigitalSequencer(QtGui.QWidget):
    def __init__(self, channels):
        super(DigitalSequencer, self).__init__(None)
        self.channels = channels
        self.populate()
        self.connect_widgets()

    def populate(self):
        self.name_column = DigitalNameColumn(self.channels)
        self.digital_array = DigitalArray(self.channels)

        self.name_scroll = QtGui.QScrollArea()
        self.name_scroll.setWidget(self.name_column)
        self.name_scroll.setWidgetResizable(True)
        self.logic_scroll = QtGui.QScrollArea()
        self.logic_scroll.setWidget(self.digital_array)
        self.logic_scroll.setWidgetResizable(True)

        self.vscroll = QtGui.QScrollArea()
        self.vscroll.setWidget(QtGui.QWidget())
        self.vscroll.setWidgetResizable(True)
        

        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.name_scroll, 0, 0)
        self.layout.addWidget(self.logic_scroll, 0, 1)
        self.layout.addWidget(self.vscroll, 0, 2)
        self.setLayout(self.layout)
        
        self.name_scroll.setHorizontalScrollBarPolicy(1)
        self.name_scroll.setVerticalScrollBarPolicy(1)
        self.name_scroll.setMaximumWidth(100)
        self.name_scroll.setFrameShape(0)
        
        self.logic_scroll.setHorizontalScrollBarPolicy(1)
        self.logic_scroll.setVerticalScrollBarPolicy(1)
        self.logic_scroll.setFrameShape(0)
        
        self.vscroll.setHorizontalScrollBarPolicy(1)
        self.vscroll.setVerticalScrollBarPolicy(2)
        self.vscroll.setFrameShape(0)
        
        self.layout.setSpacing(0)
        #self.layout.setContentsMargins(10, 10, 10, 10)
        self.set_sizes()

    def set_sizes(self):
        for lc in self.digital_array.digital_columns:
            for b in lc.sequencer_buttons.values():
                b.setFixedSize(sbwidth, sbheight)
            height = sum([lc.layout.itemAt(i).widget().height() for i in range(lc.layout.count()-1)]) # -1 because there is a generic widget in the last spot
            lc.setFixedSize(sbwidth, height)
        la_width = sum([lc.width() for lc in self.digital_array.digital_columns if not lc.isHidden()])
        la_height = self.digital_array.digital_columns[0].height()
        self.digital_array.setFixedSize(la_width, la_height)

        for nb in self.name_column.name_boxes.values():
            nb.setFixedSize(nlwidth, sbheight)
        nc_width = nlwidth
        nc_height = self.digital_array.height()

        self.vscroll.widget().setFixedHeight(self.digital_array.height())
        self.vscroll.setFixedWidth(20)
        
        self.name_column.setFixedHeight(self.digital_array.height())
        self.name_scroll.setFixedWidth(100)
        
        height = self.digital_array.height() 
        self.setMaximumHeight(1000)

    def connect_widgets(self):
        self.vscroll.verticalScrollBar().valueChanged.connect(self.adjust_for_vscroll)

    def adjust_for_vscroll(self):
        val = self.vscroll.verticalScrollBar().value()
        self.name_scroll.verticalScrollBar().setValue(val)
        self.logic_scroll.verticalScrollBar().setValue(val)

    def get_sequence_info(self):
        infos = [(db.value(), lc.get_logic()) for db, lc in zip(self.duration_row.duration_boxes, self.digital_array.digital_columns) if not lc.isHidden()]
        return infos

    def save_sequence(self):
        infos = [str(info) + '\n' for info in self.get_sequence_info()]
        outfile = open(self.browse_and_save.location_box.text(), 'w')
        outfile.write(''.join(infos))

    def browse(self):
        file_name = QtGui.QFileDialog().getOpenFileName()
        self.browse_and_save.location_box.setText(file_name)
        self.load_sequence(file_name)

    def load_sequence(self, file_name):
        infile = open(file_name, 'r')
        infos = [eval(line.split('\n')[:-1][0]) for line in infile.readlines()]
        self.set_sequence_info(infos)

    def set_sequence_info(self, infos):
        for db, lc, ad in zip(self.duration_row.duration_boxes, self.digital_array.digital_columns, self.add_dlt_row.add_dlt_buttons)[::-1]:
            db.hide()
            lc.hide()
            ad.hide()
        for info, db, lc, ad in zip(infos, self.duration_row.duration_boxes, self.digital_array.digital_columns, self.add_dlt_row.add_dlt_buttons):
            t, l = info
            db.show()
            lc.show()
            ad.show()
            db.display(t)
            lc.set_logic(l)

        self.set_sizes()

    def add_column(self, i):
        def ar():
            infos = self.get_sequence_info()
            infos.insert(i, infos[i])
            self.set_sequence_info(infos)
        return ar

    def dlt_column(self, i):
        def dr():
            infos = self.get_sequence_info()
            infos.pop(i)
            self.set_sequence_info(infos)
        return dr

"""analog voltages"""

class AnalogNameColumn(QtGui.QWidget):
    def __init__(self, channels):
        super(AnalogNameColumn, self).__init__(None)
        self.channels = channels
        self.populate()

    def populate(self):
        self.labels = {n: NameBox(c+': '+n) for c, n in self.channels.items()}
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 5, 0)

        for i, (c, n) in enumerate(sorted(self.channels.items())):
            self.layout.addWidget(self.labels[n])
        self.layout.addWidget(QtGui.QWidget())
        self.setLayout(self.layout)

class AnalogArray(FigureCanvas):
    def __init__(self, channels):
        self.channels = channels
        self.fig = Figure()#facecolor='white'

        self.axes = self.fig.add_subplot(111)
        self.sequence = [(1, {name: {'type': 'linear', 'v': 0, 'length': (1, 1)} for name in self.channels.values()}) for i in range(20)]
        voltages = [3, 2, 1, 2]

        FigureCanvas.__init__(self, self.fig)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['bottom'].set_visible(False)
        self.axes.spines['left'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.fig.subplots_adjust(left=0, bottom = 0, right=1, top=1)
        self.plot_sequence()
        
#        self.make_figure(voltages)
#        
#    def make_figure(self, voltages=None):
#        self.axes.plot(voltages)

    def get_sequence(self):
        return self.sequence
    
    def load_sequence(self, sequence):
        self.sequence = sequence
        self.plot_sequence()

    def plot_sequence(self):
        S = sum([t for t, r in self.sequence])
#        T = [0] + [sum([t for t, r in sequence][:i+1]) for i in range(len(sequence))]
#        T = [np.linspace(T[i], T[i+1], 11)[:-1] for i in range(len(sequence)-1)]
#        T = [t for tt in T for t in tt] #??? we wanted a list with 10 pts between each time specified in sequence
#
#        T = [np.linspace(0, t, 11) for t, r in sequence]
#        T = [t for tt in T for t in tt]
        X = self.get_points(self.sequence)
        self.axes.cla()
#        self.axes.axhline(-10, color='k')
        for i, (c, n) in enumerate(sorted(self.channels.items())):
#            self.axes.axhline(i*20 +10, color='k')
            x = np.array(X[n]) - i*20
            self.axes.plot(x)
        self.axes.set_ylim(-20*len(self.channels.items())+10, 10)
        self.axes.set_xlim(0, len(self.sequence)*pps)
        self.draw()
    
    def get_points(self, sequence):
        ramp_parameters = [{name: dict(d[name].items() + [('t', t)]) for name in self.channels.values()} for t, d in sequence] # throw t into dict
        for name in self.channels.values():
            ramp_parameters[0][name]['vi'] = 0
            for i in range(1, len(sequence)):
                ramp_parameters[i][name]['vi'] = ramp_parameters[i-1][name]['v']
            for rp in ramp_parameters:
                rp[name]['vf'] = rp[name]['v']
        T = [np.linspace(0, t, pps) for t, r in sequence]
        return {name: [v for vv in [self.get_continuous(rp[name])(t) for t, rp in zip(T, ramp_parameters)] for v in vv] for name in self.channels.values()}

    def get_continuous(self, p):
        if p['type'] == 'linear':
            return lambda t: G(0, p['t'])(t)*(p['vi']+(p['vf']-p['vi'])/p['t']*t)
        elif p['type'] == 'linear2':
            return lambda t: G2(0, p['t'])(t)*(p['vi']+(p['vf']-p['vi'])/p['t']*t)
        elif p['type'] == 'exp':
            A = (p['vf'] - p['vi'])/(np.exp(p['t']/p['tau']) - 1)
            C = p['vi'] - A
            continuous = lambda t: G(0, p['t'])(t)*(A * np.exp(t/p['tau']) + C)
            T = np.linspace(0, p['t'], p['pts'])
            V = continuous(T)
            lp2 = [{'vf': V[i+1], 'vi': V[i], 't': p['t']/float(p['pts']-1), 'type': 'linear2'} for i in range(p['pts']-1)]
            lp2[-1]['type'] = 'linear'
            return lambda t: sum([self.get_continuous(p2)(t-T[i]) for i, p2 in enumerate(lp2)])
        elif p['type'] == 'step':
            return lambda t: G(0, p['t'])(t)*p['v']

def H(x):
    return 0.5*(np.sign(x)+1)

def G(t1, t2):
    return lambda t: H(t2-t+1e-9) - H(t1-t-1e-9) 

def G2(t1, t2):
    return lambda t: H(t2-t-1e-9) - H(t1-t-1e-9) 

class AnalogSequencer(QtGui.QWidget):
    def __init__(self, channels):
        super(AnalogSequencer, self).__init__(None)
        self.channels = channels
        self.populate()

    def populate(self):
        self.canvas = AnalogArray(self.channels)
        self.name_column = AnalogNameColumn(self.channels)
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.name_column)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)
        self.set_sizes()

    def set_sizes(self):
#        for l in self.name_column.labels.values():
#            l.setFixedSize(nlwidth, acheight)
#        self.canvas.setFixedSize(sbwidth*max_columns, len(self.channels.items())*acheight)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def load_sequence(self, sequence):
        self.sequence = sequence
        S = sum([t for t, r in sequence])
        T = [0] + [sum([t for t, r in sequence][:i+1]) for i in range(len(sequence))]
        T = [np.linspace(T[i], T[i+1], 11)[:-1] for i in range(len(sequence)-1)]
        T = [t for tt in T for t in tt] #??? we wanted a list with 10 pts between each time specified in sequence

        T = [np.linspace(0, t, 11) for t, r in sequence]
        T = [t for tt in T for t in tt]
        X = self.get_points(sequence)

        self.canvas.axes.cla()
#        self.canvas.axes.axhline(-10, color='k')
        for i, (c, n) in enumerate(sorted(self.channels.items())):
#            self.canvas.axes.axhline(i*20 +10, color='k')
            x = np.array(X[n]) - i*20
            self.canvas.axes.plot(x)
        self.canvas.axes.set_ylim(-20*len(self.channels.items())+10, 10)
        self.canvas.axes.set_xlim(0, len(sequence)*pps)
        self.canvas.draw()
        self.set_sizes()

    def get_points(self, sequence):
        ramp_parameters = [{name: dict(d[name].items() + [('t', t)]) for name in self.channels.values()} for t, d in sequence] # throw t into dict
        for name in self.channels.values():
            ramp_parameters[0][name]['vi'] = 0
            for i in range(1, len(sequence)):
                ramp_parameters[i][name]['vi'] = ramp_parameters[i-1][name]['v']
            for rp in ramp_parameters:
                rp[name]['vf'] = rp[name]['v']
        T = [np.linspace(0, t, pps) for t, r in sequence]
#        T = np.array([t for tt in T for t in tt])
        #return {name: [v for vv in [make_ramp(rp[name]) for rp in ramp_parameters] for v in vv] for name in self.channels.values()}
        return {name: [v for vv in [self.get_continuous(rp[name])(t) for t, rp in zip(T, ramp_parameters)] for v in vv] for name in self.channels.values()}

    def get_continuous(self, p):
        if p['type'] == 'linear':
            return lambda t: G(0, p['t'])(t)*(p['vi']+(p['vf']-p['vi'])/p['t']*t)
        elif p['type'] == 'linear2':
            return lambda t: G2(0, p['t'])(t)*(p['vi']+(p['vf']-p['vi'])/p['t']*t)
        elif p['type'] == 'exp':
            A = (p['vf'] - p['vi'])/(np.exp(p['t']/p['tau']) - 1)
            C = p['vi'] - A
            continuous = lambda t: G(0, p['t'])(t)*(A * np.exp(t/p['tau']) + C)
            T = np.linspace(0, p['t'], p['pts'])
            V = continuous(T)
            lp2 = [{'vf': V[i+1], 'vi': V[i], 't': p['t']/float(p['pts']-1), 'type': 'linear2'} for i in range(p['pts']-1)]
            lp2[-1]['type'] = 'linear'
            return lambda t: sum([self.get_continuous(p2)(t-T[i]) for i, p2 in enumerate(lp2)])
        elif p['type'] == 'step':
            return lambda t: G(0, p['t'])(t)*p['v']

#class Sequencer(QtGui.QWidget):
#    def __init__(self, digital_channels, analog_channels):
#        super(Sequencer, self).__init__(None)
#        self.digital_channels = digital_channels
#        self.analog_channels = analog_channels
#
#        self.populate()
#
#    def populate(self):
#        self.digital_sequencer = DigitalSequencer(self.digital_channels)
#        self.analog_sequencer = AnalogSequencer(self.analog_channels)
#
#        self.layout = QtGui.QGridLayout()
#        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
#        self.splitter.addWidget(self.digital_sequencer)
#        self.splitter.addWidget(self.analog_sequencer)
#        self.layout.addWidget(self.splitter)
#        self.setLayout(self.layout)



digital_channels = {
            'A00': 'TTLA00',
            'A01': 'TTLA01',
            'A02': 'TTLA02',
            'A03': 'TTLA03',
            'A04': 'TTLA04',
            'A05': 'TTLA05',
            'A06': 'TTLA06',
            'A07': 'TTLA07',
            'A08': 'TTLA08',
            'A09': 'TTLA09',
            'A10': 'TTLA10',
            'A11': 'TTLA11',
            'A12': 'TTLA12',
            'A13': 'TTLA13',
            'A14': 'TTLA14',
            'A15': 'TTLA15',

            'B00': 'TTLB00',
            'B01': 'TTLB01',
            'B03': 'TTLB02',
            'B03': 'TTLB03',
            'B04': 'TTLB04',
            'B05': 'TTLB05',
            'B06': 'TTLB06',
            'B07': 'TTLB07',
            'B08': 'TTLB08',
            'B09': 'TTLB09',
            'B10': 'TTLB10',
            'B11': 'TTLB11',
            'B12': 'TTLB12',
            'B13': 'TTLB13',
            'B14': 'TTLB14',
            'B15': 'TTLB15',

            'C00': 'TTLC00',
            'C01': 'TTLC01',
            'C02': 'TTLC02',
            'C03': 'TTLC03',
            'C04': 'TTLC04',
            'C05': 'TTLC05',
            'C06': 'TTLC06',
            'C07': 'TTLC07',
            'C08': 'TTLC08',
            'C09': 'TTLC09',
            'C10': 'TTLC10',
            'C11': 'TTLC11',
            'C12': 'TTLC12',
            'C13': 'TTLC13',
            'C14': 'TTLC14',
            'C15': 'TTLC15',
            
            'D00': 'TTLD00',
            'D01': 'TTLD01',
            'D02': 'TTLD02',
            'D03': 'TTLD03',
            'D04': 'TTLD04',
            'D05': 'TTLD05',
            'D06': 'TTLD06',
            'D07': 'TTLD07',
            'D08': 'TTLD08',
            'D09': 'TTLD09',
            'D10': 'TTLD10',
            'D11': 'TTLD11',
            'D12': 'TTLD12',
            'D13': 'TTLD13',
            'D14': 'TTLD14',
            'D15': 'TTLD15',
            }

analog_channels = {
            'A00': 'DACA00',
            'A01': 'DACA01',
            'A02': 'DACA02',
            'A03': 'DACA03',
            'A04': 'DACA04',
            'A05': 'DACA05',
            'A06': 'DACA06',
            'A07': 'DACA07',
            }

test_ramp = [(1, {name: {'type': 'exp', 'v': 10, 'tau': .5, 'pts': 10} for name in analog_channels.values()})] + [(1, {name: {'type': 'step', 'v': 0, 'length': (1, 1)} for name in analog_channels.values()})] + [(1, {name: {'type': 'linear', 'v': 10, 'length': (1, 1)} for name in analog_channels.values()})]*3 + [(.1, {name: {'type': 'linear', 'v': 0, 'length': (1, 1)} for name in analog_channels.values()})]*3

if __name__ == '__main__':
    a = QtGui.QApplication([])
    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
#    widget = DigitalSequencer(channels)
#    widget = AnalogColumn()
#    widget = AnalogArray()
#    widget = AnalogNameColumn(analog_channels)
#    widget = AnalogSequencer(analog_channels)
    widget = Sequencer(digital_channels, analog_channels)
    widget.show()
#    widget.load_sequence(test_ramp)
    reactor.run()
