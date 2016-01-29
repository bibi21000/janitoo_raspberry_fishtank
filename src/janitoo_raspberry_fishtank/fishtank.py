# -*- coding: utf-8 -*-
"""The Raspberry http thread

Server files using the http protocol

"""

__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

import logging
logger = logging.getLogger(__name__)
import os, sys
import threading
import datetime

from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.component import JNTComponent
from janitoo.bus import JNTBus

from janitoo_raspberry_dht.dht import DHTComponent
from janitoo_raspberry_i2c.bus_i2c import I2CBus
#~ from janitoo_raspberry_camera.camera import CameraBus
from janitoo_raspberry_1wire.bus_1wire import OnewireBus
from janitoo_raspberry_1wire.components import DS18B20

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_WEB_CONTROLLER = 0x1030
COMMAND_WEB_RESOURCE = 0x1031
COMMAND_DOC_RESOURCE = 0x1032

assert(COMMAND_DESC[COMMAND_WEB_CONTROLLER] == 'COMMAND_WEB_CONTROLLER')
assert(COMMAND_DESC[COMMAND_WEB_RESOURCE] == 'COMMAND_WEB_RESOURCE')
assert(COMMAND_DESC[COMMAND_DOC_RESOURCE] == 'COMMAND_DOC_RESOURCE')
##############################################################

def make_ambiance(**kwargs):
    return AmbianceComponent(**kwargs)

def make_temperature(**kwargs):
    return TemperatureComponent(**kwargs)

def make_moon(**kwargs):
    return MoonComponent(**kwargs)

def make_sun(**kwargs):
    return SunComponent(**kwargs)

def make_tide(**kwargs):
    return TideComponent(**kwargs)

def make_biocycle(**kwargs):
    return BiocycleComponent(**kwargs)

def make_airflow(**kwargs):
    return AirflowComponent(**kwargs)

def make_timelapse(**kwargs):
    return TimelapseComponent(**kwargs)

class FishtankBus(JNTBus):
    """A bus to manage Fishtank
    """
    def __init__(self, **kwargs):
        """
        :param kwargs: parameters transmitted to :py:class:`smbus.SMBus` initializer
        """
        JNTBus.__init__(self, **kwargs)
        self.buses = {}
        self.buses['owbus'] = OnewireBus(**kwargs)
        self.buses['owbus'].export_values(self)
        self.buses['i2cbus'] = I2CBus(**kwargs)
        self.buses['i2cbus'].export_values(self)
        self._fishtank_lock =  threading.Lock()

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        return True

    def start(self, mqttc, trigger_thread_reload_cb=None):
        """Start the bus
        """
        #~ for bus in self.buses:
            #~ self.buses[bus].start(mqttc, trigger_thread_reload_cb=None)
        JNTBus.start(self, mqttc, trigger_thread_reload_cb)

    def stop(self):
        """Stop the bus
        """
        JNTBus.stop(self)
        for bus in self.buses:
            self.buses[bus].stop()

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        res = True
        for bus in self.buses:
            res = res and self.buses[bus].check_heartbeat()
        return res

class AmbianceComponent(DHTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.ambiance')
        name = kwargs.pop('name', "Ambiance sensor")
        DHTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class TemperatureComponent(DS18B20):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.temperature')
        name = kwargs.pop('name', "Temperature")
        DS18B20.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class BiocycleComponent(JNTComponent):
    """ A 'bio' cyclecomponent"""

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.biocycle')
        name = kwargs.pop('name', "Bio cycle")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name, hearbeat=60,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        uuid="cycle"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of days in the cycle',
            label='Days',
            default=kwargs.pop('cycle', 28),
        )
        uuid="current"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The current day in the cycle',
            label='Day',
            default=kwargs.pop('current', 11),
        )
        uuid="max"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max hours for the cycle in a day',
            label='Max',
            default=kwargs.pop('max', 1),
        )
        uuid="min"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The min hours for the cycle in a day',
            label='Min',
            default=kwargs.pop('min', 0),
        )
        uuid="midi"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the midi for the cycle',
            label='Mid.',
            default=kwargs.pop('midi', '16:30'),
        )
        uuid="duration"
        self.values[uuid] = self.value_factory['sensor_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The duration in minutes of the cycle for the current day',
            label='Duration',
            get_data_cb=self.duration,
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="factor_day"
        self.values[uuid] = self.value_factory['sensor_float'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The factor for today. A value for -1 to 1',
            label='Today',
            get_data_cb=self.factor_day,
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="factor_now"
        self.values[uuid] = self.value_factory['sensor_float'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The factor for now. A value for -1 to 1',
            label='Now',
            get_data_cb=self.factor_now,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

    def factor_day(self, node_uuid, index):
        data = None
        try:
            data = float(self.get_cycle_factor(index=index))
            if data<-1:
                data = -1.0
            elif data>1:
                data = 1.0
        except :
            logger.exception('Exception when calculationg day factor')
        return data

    def factor_now(self, node_uuid, index):
        data = None
        try:
            data = float(self.get_hour_factor(index=index))
            if data<-1:
                data = -1.0
            elif data>1:
                data = 1.0
        except :
            logger.exception('Exception when calculationg now factor')
        return data

    def duration(self, node_uuid, index):
        data = None
        try:
            data = int(self.get_cycle_duration(index=index))
        except :
            logger.exception('Exception when calculationg duration')
        return data

    def _get_factor(self, current, cycle):
        """Calculate the factor"""
        return 2.0 * (current - (cycle / 2)) / cycle

    def get_cycle_factor(self, index=0):
        """Get the factor related to day cycle"""
        return self._get_factor(self.values['current'].get_data_index(index=index), self.values['cycle'].get_data_index(index=index))

    def get_cycle_duration(self, index=0):
        """Get the duration in minutes of the cycle for today"""
        dfact = abs(self.get_cycle_factor())
        dlen = self.values['min'].get_data_index(index=index)*60.0 + ( self.values['max'].get_data_index(index=index)*60.0 - self.values['min'].get_data_index(index=index)*60.0) * dfact
        return dlen

    def get_hour_factor(self, index=0, nnow=None):
        """Get the factor according"""
        if nnow is None:
            nnow = datetime.datetime.now()
        hh, mm = self.values['midi'].get_data_index(index=index).split(':')
        midd = nnow.replace(hour=int(hh), minute=int(mm))
        tdur = self.get_cycle_duration()
        cdur = int(tdur/2)
        start = midd - datetime.timedelta(minutes=cdur)
        stop = midd + datetime.timedelta(minutes=cdur)
        if nnow<start or nnow>stop:
            return 0
        elapsed = (nnow - start).total_seconds()/60
        return 1-abs(self._get_factor(int(elapsed), int(tdur)))

    def get_status(self, index=0, nnow=None):
        """Get the factor according"""
        if nnow is None:
            nnow = datetime.datetime.now()
        hh, mm = self.values['midi'].get_data_index(index=index).split(':')
        midd = nnow.replace(hour=int(hh), minute=int(mm))
        cdur = int(self.get_cycle_duration()/2)
        start = midd - datetime.timedelta(minutes=cdur)
        stop = midd + datetime.timedelta(minutes=cdur)
        if nnow<start or nnow>stop:
            return False
        return True

class MoonComponent(BiocycleComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.moon')
        name = kwargs.pop('name', "Moon")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)

class SunComponent(BiocycleComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.sun')
        name = kwargs.pop('name', "Sun")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class TideComponent(BiocycleComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.tide')
        name = kwargs.pop('name', "Tide")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class AirflowComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.airflow')
        name = kwargs.pop('name', "Air flow")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class TimelapseComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.timelapse')
        name = kwargs.pop('name', "Timelapse")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

