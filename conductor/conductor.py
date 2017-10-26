"""
### BEGIN NODE INFO
[info]
name = conductor
version = 1.0
description = 
instancename = conductor

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import json
import os

from collections import deque
from copy import deepcopy
from time import time, strftime

from labrad.server import LabradServer
from labrad.server import setting
from labrad.server import Signal
from labrad.wrappers import connectAsync
from twisted.internet.reactor import callLater, callInThread
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import returnValue
from twisted.internet.threads import deferToThread

from lib.helpers import import_parameter
from lib.helpers import remaining_points
from lib.exceptions import ParameterAlreadyRegistered
from lib.exceptions import ParameterNotImported
from lib.exceptions import ParameterNotRegistered

# TODO remote save parameter files locally
# TODO get available parameters

class ConductorServer(LabradServer):
    """ coordinate setting and saving experiment parameters.
    
    parameters are classes defined in ./devices/...
        parameters hold values representing real world attributes.
        typically send/receive data to/from hardware.
        see ./devices/conductor_device/conductor_parameter.py for documentation
    
    experiments specify parameter values to be iterated over 
        and a filename for saving data.
    """

    name = 'conductor'
    parameters_updated = Signal(698124, 'signal: parameters_updated', 'b')

    def __init__(self, config_path='./config.json'):
        self.parameters = {}
        self.experiment_queue = deque([])
        self.data = {}
        self.data_path = None
        self.do_print_delay = False

        self.load_config(config_path)
        LabradServer.__init__(self)
    
    def load_config(self, path=None):
        """ set instance attributes defined in json config """
        if path is not None:
            self.config_path = path
        with open(self.config_path, 'r') as infile:
            config = json.load(infile)
            for key, value in config.items():
                setattr(self, key, value)

    def initServer(self):
        # register default parameters after connected to labrad
        callLater(.1, self.register_parameters, None, json.dumps(self.default_parameters))

    @setting(2, parameters='s', generic_parameter='b', value_type='s', returns='b')
    def register_parameters(self, c, parameters, generic_parameter=False, value_type=None):
        """ 
        load parameters into conductor
        
        parameters are defined in conductor/devices/device_name/parameter_name.py
        view defined parameters with conductor.available_parameters
        
        Args:
            parameters: json.dumps(...) of
                {
                    device_name: {
                        parameter_name: {
                            parameter_config
                        }
                }.
                device_name: string e.g. "dds1"
                parameter_name: string e.g. "frequency"
                parameter_config: passed to parameter's __init__
            generic_parameter: bool. If true and no defined parameter is found,
                will create generic_parameter for holding values.AA
            value_type: string. e.g. "single", "list", "data"
        Returns:
            bool. true if no errors.
        """
        for device_name, device_parameters in json.loads(parameters).items():
            for parameter_name, parameter_config in device_parameters.items():
                yield self.register_parameter(device_name, parameter_name, 
                        parameter_config, generic_parameter, value_type)

        returnValue(True)
    
    @inlineCallbacks
    def register_parameter(self, device_name, parameter_name, parameter_config,
                           generic_parameter, value_type):
        """ populate self.parameters with specified parameter

        look in ./devices/ for specified parameter
        if no suitable parameter is found and generic_parameter is True, 
        create generic parameter for holding values.

        Args:
            device_name: string e.g. "dds1"
            parameter_name: string e.g. "frequency"
            parameter_config: passed to parameter's __init__
            generic_parameter: bool. specifies whether or not to use 
                devices/conductor_device/conductor_parameter.py if 
                devices/device_name/parameter_name.py is not found.
            value_type: string. e.g. "single", "list", "data"
        Returns:
            None
        Raises:
            ParameterAlreadyRegistered: if specified parameter is already in 
                self.parameters
            ParameterNotImported: if import of specified parameter fails.
        """
        if not self.parameters.get(device_name):
            self.parameters[device_name] = {}

        if self.parameters[device_name].get(parameter_name):
            raise ParameterAlreadyRegistered(device_name, parameter_name)
        else:
            try:
                Parameter = import_parameter(device_name, parameter_name, 
                                             generic_parameter)
                if not Parameter:
                    raise ParameterNotImported(device_name, parameter_name)
                else:
                    if not parameter_config:
                        parameter_config = self.default_parameters.get(
                                            device_name, {}).get(parameter_name, {})
                    parameter = Parameter(parameter_config)
                    parameter.device_name = device_name
                    parameter.name = parameter_name
                    parameter.conductor = self
                    if value_type is not None:
                        parameter.value_type = value_type
                    self.parameters[device_name][parameter_name] = parameter
                    yield parameter.initialize()
                    yield self.update_parameter(parameter)
            except Exception, e:
                print e
                print 'error registering parameter {} {}'.format(device_name, parameter_name)

    @setting(3, parameters='s', returns='b')
    def remove_parameters(self, c, parameters):
        """ 
        remove specified parameters

        Args:
            parameters: json dumped string [json.dumps(...)] of dict
                {
                    device_name: {
                        parameter_name: None
                    }
                }
        """
        for device_name, device_parameters in json.loads(parameters).items():
            for parameter_name, _ in device_parameters.items():
                yield self.remove_parameter(device_name, parameter_name)
        returnValue(True)
    
    @inlineCallbacks
    def remove_parameter(self, device_name, parameter_name):
        """ remove specified parameter from self.parameters

        Args:
            device_name: string e.g. "dds1"
            parameter_name: string e.g. "frequency"
        Returns:
            None
        Raises:
            ParameterNotRegistered: if specified parameter not in self.parameters
        """
        try:
            parameter = self.parameters[device_name][parameter_name]
        except:
            raise ParameterNotRegistered(device_name, parameter_name)
        del self.parameters[device_name][parameter_name]
        if not self.parameters[device_name]:
            del self.parameters[device_name]
        yield parameter.stop()

    @setting(4, parameters='s', generic_parameter='b', returns='b')
    def set_parameter_values(self, c, parameters, generic_parameter=False, 
                             value_type=None):
        """  set specified parameter values

        parameters = {
            device_name: {
                parameter_name: value
            }
        }
        """
        for device_name, device_parameters in json.loads(parameters).items():
            for parameter_name, parameter_value in device_parameters.items():
                yield self.set_parameter_value(device_name, parameter_name, 
                                               parameter_value, 
                                               generic_parameter, value_type)
        returnValue(True)

    @inlineCallbacks
    def set_parameter_value(self, device_name, parameter_name, parameter_value,
                            generic_parameter=False, value_type=None):
        """ assign parameter value to specified parameter.value

        register parameter if not already in self.parameters

        Args:
            device_name: string e.g. "dds1"
            parameter_name: string e.g. "frequency"
            parameter_value: anything e.g. 20e6
        Returns:
            None
        Raises:
            ParameterNotImported: if import of specified parameter fails.
        """
        try:
            self.parameters[device_name][parameter_name]
        except KeyError:
            if parameter_name[0] == '*':
                generic_parameter = True
            yield self.register_parameter(device_name, parameter_name, {}, 
                                          generic_parameter, value_type)

        self.parameters[device_name][parameter_name].value = parameter_value

    @setting(5, parameters='s', use_registry='b', returns='s')
    def get_parameter_values(self, c, parameters=None, use_registry=False):
        """ get specified parameter values

        parameters = {
            device_name: {
                parameter_name: None
            }
        }
        """
        if parameters is None:
            parameters = {dn: dp.keys() for dn, dp in self.parameters.items()}
        else:
            parameters = json.loads(parameters)

        parameter_values = {}
        for device_name, device_parameters in parameters.items():
            parameter_values[device_name] = {}
            for parameter_name in device_parameters:
                parameter_values[device_name][parameter_name] = \
                        yield self.get_parameter_value(device_name, 
                                                       parameter_name,
                                                       use_registry)
        returnValue(json.dumps(parameter_values))

    @inlineCallbacks
    def get_parameter_value(self, device_name, parameter_name, use_registry=False):
        message = None
        value = 0
        try:
            try: 
                parameter = self.parameters[device_name][parameter_name]
                value = parameter.value
            except:
                parameters_filename = self.parameters_directory + 'current_parameters.json'
                with open(parameters_filename, 'r') as infile:
                    old_parameters = json.load(infile)
                    value = old_parameters[device_name][parameter_name]
                    yield self.set_parameter_value(device_name, parameter_name, value, True)
        except:
            if use_registry:
                print 'looking in registry for parameter {}'.format(device_name + parameter_name)
                print 'this feature will be depreciated'
                try: 
                    yield self.client.registry.cd(self.registry_directory
                                                  + [device_name])
                    value = yield self.client.registry.get(parameter_name)
                    config = json.dumps({device_name: {parameter_name: value}})
                    yield self.set_parameter_values(None, config, True)
                except Exception, e:
                    print e
                    message = 'unable to get most recent value for\
                               {} {}'.format(device_name, parameter_name)
            else:
                message = '{} {} is not an active parameter'.format(device_name,
                                                                 parameter_name)
        if message:
            raise Exception(message)
        returnValue(value)
    
    @setting(8, experiment='s', run_next='b', returns='i')
    def queue_experiment(self, c, experiment, run_next=False):
        """ load experiment into queue

        experiments are json object 
        keys...
            'name': some string. required.

            'parameter_values': {name: value}. optional.
            'append data': bool, save data to previous file? optional.
            'loop': bool, inserts experiment back into begining of queue optional.
        """
        if run_next:
            self.experiment_queue.appendleft(json.loads(experiment))
        else:
            self.experiment_queue.append(json.loads(experiment))
        return len(self.experiment_queue)

    @setting(9, experiment_queue='s', returns='i')
    def set_experiment_queue(self, c, experiment_queue=None):
        self.experiment_queue = deque([])
        if experiment_queue:
            experiment_queue = json.loads(experiment_queue)
            for experiment in experiment_queue:
                self.experiment_queue.append(experiment)
        return len(self.experiment_queue)

    @setting(10, returns='b')
    def stop_experiment(self, c):
        # replace parameter value lists with single value.
        for device_name, device_parameters in self.parameters.items():
            for parameter_name, parameter in device_parameters.items():
                parameter.value = parameter.value
        self.data = {}
        self.data_path = None

        self.experiment_name = None
        self.experiment_number = None
        self.point_number = None

        return True

    @setting(13, returns='s')
    def get_data(self, c):
        return json.dumps(self.data)
    
    @inlineCallbacks
    def advance_experiment(self):
        if len(self.experiment_queue):
            # get next experiment from queue and keep a copy
            experiment = self.experiment_queue.popleft()
            experiment_copy = deepcopy(experiment)
            
            parameter_values = experiment.get('parameter_values')
            if parameter_values:
                yield self.set_parameter_values(None, json.dumps(parameter_values))

            # if this experiment should loop, append to begining of queue
            if experiment.get('loop'):
                # now we require appending data
                experiment_copy['append_data'] = True
                # add experiment to begining of queue
                self.experiment_queue.appendleft(experiment_copy)
            
            if not experiment.get('append_data'):
                self.data = {}

                # determine data path
                timestr = strftime('%Y%m%d')
                data_directory = self.data_directory.format(timestr)
                data_path = lambda i: str(data_directory 
                                          + experiment['name'] 
                                          + '#{}'.format(i))
                iteration = 0 
                while os.path.isfile(data_path(iteration)):
                    iteration += 1
                self.data_path = data_path(iteration)
                self.experiment_name = experiment["name"]
                self.experiment_number = iteration
                self.point_number = 0
                
                print 'saving data to {}'.format(self.data_path)
                if not os.path.exists(data_directory):
                    os.mkdir(data_directory)

            returnValue(True)
        else:
            self.data = {}
            if self.data_path:
                print 'experiment queue is empty'
            self.data_path = None
            returnValue(False)

    @inlineCallbacks
    def advance_parameters(self):
        """ get new parameter values then send to devices """
        advanced = False
        # check if we need to load next experiment
        pts = remaining_points(self.parameters)
        if not pts:
            # no active experiment, check queue
            advanced = yield self.advance_experiment()
            if not advanced:
                yield self.stop_experiment(None)
        else:
            # we are continuing an active experiment
            print 'remaining points: ', pts

        # sort by priority. higher priority is called first. 
        priority_parameters = [parameter for device_name, device_parameters
                                         in self.parameters.items()
                                         for parameter_name, parameter 
                                         in device_parameters.items()
                                         if parameter.priority]

        # advance parameter values if parameter has priority
        if not advanced:
            for parameter in priority_parameters:
                parameter.advance()
        
        # call parameter updates in order of priority. 
        # 1 is called last. 0 is never called.
        for parameter in sorted(priority_parameters, key=lambda x: x.priority)[::-1]:
            if self.do_print_delay:
                ti = time()
            yield self.update_parameter(parameter)
            if self.do_print_delay:
                print '{} delay: {}'.format(parameter.name, time() - ti)

        # signal update
        if not pts:
            if advanced:
                self.point_number += 1
        else:
            self.point_number += 1
        yield self.parameters_updated(True)

    @inlineCallbacks
    def update_parameter(self, parameter):
        """ have device update parameter value """
        try:
            yield parameter.update()
        except Exception, e:
            # remove parameter is update failed.
            print e
            print 'could not update {}\'s {}. removing parameter'.format(
                    parameter.device_name, parameter.name)
            yield self.remove_parameter(parameter.device_name, parameter.name)
    
    def save_data(self, data, data_path):
        # save data to disk
        if data:
            data_length = max([len(p) for dp in data.values()
                                      for p in dp.values()])
        else:
            data_length = 0
        
        for device_name, device_parameters in self.parameters.items():
            if not data.get(device_name):
                data[device_name] = {}
            for parameter_name, parameter in device_parameters.items():
                if not data[device_name].get(parameter_name):
                    data[device_name][parameter_name] = []
                parameter_data = data[device_name][parameter_name] 
                while len(parameter_data) < data_length:
                    parameter_data.append(None)
                new_value = parameter.value
                parameter_data.append(new_value)
        
        if data_path:
            with open(data_path, 'w+') as outfile:
                json.dump(data, outfile, default=lambda x: None)

    @inlineCallbacks
    def stopServer(self):
        yield self.backup_parameters(None)

    @setting(17, returns='b')
    def backup_parameters(self, c):
        parameters_filename = self.parameters_directory + 'current_parameters.json'
        if os.path.isfile(parameters_filename):
            with open(parameters_filename, 'r') as infile:
                old_parameters = json.load(infile)
        else:
            old_parameters = {}

        parameters = deepcopy(old_parameters)
        for device_name, device_parameters in self.parameters.items():
            if not parameters.get(device_name):
                parameters[device_name] = {}
            for parameter_name, parameter in device_parameters.items():
                parameters[device_name][parameter_name] = parameter.value
        
        parameters_filename = self.parameters_directory + 'current_parameters.json'
        with open(parameters_filename, 'w') as outfile:
            json.dump(parameters, outfile)

        parameters_filename = self.parameters_directory + '{}.json'.format(
                                  strftime(self.time_format))
        with open(parameters_filename, 'w') as outfile:
            json.dump(parameters, outfile)
        print 'parameters backed up'

        return True

    @setting(15)
    def advance(self, c, delay=0):
        if delay:
            callLater(delay, self.advance, c)
        else:
            callInThread(self.save_data, self.data, self.data_path) # maybe better to have callInThread f, not class method, make sure nothing strange happens
            ti = time()
            yield self.advance_parameters()
            tf = time()
            if self.do_print_delay:
                print 'total delay: ', tf-ti

    @setting(16, do_print_delay='b', returns='b')
    def print_delay(self, c, do_print_delay=None):
        if do_print_delay is not None:
            self.do_print_delay = do_print_delay
        return self.do_print_delay

if __name__ == "__main__":
    from labrad import util
    server = ConductorServer()
    util.runServer(server)
