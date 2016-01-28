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

from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.component import JNTComponent
from janitoo.bus import JNTBus

from janitoo_raspberry_dht.dht import DHTComponent
from janitoo_raspberry_i2c.bus_i2c import I2CBus
from janitoo_raspberry_camera.camera import CameraBus
from janitoo_raspberry_1wire.bus_1wire import OnewireBus
from janitoo_raspberry_1wire.components_1wire import DS18B20

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
    return ambianceComponent(**kwargs)

def make_temperature(**kwargs):
    return temperatureComponent(**kwargs)

def make_moon(**kwargs):
    return moonComponent(**kwargs)

def make_sun(**kwargs):
    return sunComponent(**kwargs)

def make_tide(**kwargs):
    return sunComponent(**kwargs)

def make_airflow(**kwargs):
    return airflowComponent(**kwargs)

def make_timelapse(**kwargs):
    return timelapseComponent(**kwargs)

class FishtankBus(JNTBus):
    """A bus to manage Fishtank
    """
    def __init__(self, **kwargs):
        """
        :param kwargs: parameters transmitted to :py:class:`smbus.SMBus` initializer
        """
        JNTBus.__init__(self, **kwargs)
        self.owbus = OnewireBus(**kwargs)
        for value in self.owbus.values:
            self.values[value] = self.owbus.values[value]
        self.i2cbus = I2CBus(**kwargs)
        for value in self.i2cbus.values:
            self.values[value] = self.i2cbus.values[value]
        self.cambus = CameraBus(**kwargs)
        for value in self.cambus.values:
            self.values[value] = self.cambus.values[value]
        self._fishtank_lock =  threading.Lock()

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        return True

    def start(self, mqttc, trigger_thread_reload_cb=None):
        """Start the bus
        """
        JNTBus.start(self, mqttc, trigger_thread_reload_cb)

    def stop(self):
        """Stop the bus
        """
        JNTBus.stop(self)

class ambianceComponent(DHTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.ambiance')
        name = kwargs.pop('name', "Ambiance sensor")
        DHTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class temperatureComponent(DS18B20):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.temperature')
        name = kwargs.pop('name', "Temperature")
        DS18B20.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class moonComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.moon')
        name = kwargs.pop('name', "Moon")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        uuid="moon_cycle"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of days in the moon cycle',
            label='Days',
            default=21,
        )
        uuid="moon_current"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The current day in the moon cycle',
            label='Day',
            default=11,
        )
        uuid="moon_max_pwm"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max pwm value for the moon cycle',
            label='Day',
            default=14,
        )
        uuid="moon_max"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max hours the moon shine in a day',
            label='Max',
            default=14,
        )
        uuid="moon_min"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The min hours the moon shine i a day',
            label='Min',
            default=14,
        )
        uuid="moon_middle"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the middle hour in the day cycle ie 22:00',
            label='Mid.',
            default=14,
        )

class moonComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.sun')
        name = kwargs.pop('name', "Sun")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        uuid="sun_cycle"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of days in the sun cycle',
            label='Days',
            default=90,
        )
        uuid="sun_current"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The current day in the sun cycle',
            label='Day',
            default=14,
        )
        uuid="sun_max_pwm"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max pwm value for the sun cycle',
            label='Day',
            default=14,
        )
        uuid="sun_max"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max hours the sun shine in a day',
            label='Max',
            default=14,
        )
        uuid="sun_min"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The min hours the sun shine i a day',
            label='Min',
            default=14,
        )
        uuid="sun_middle"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the middle hour in the day cycle ie 16:00',
            label='Mid.',
            default=14,
        )

class tideComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.tide')
        name = kwargs.pop('name', "Tide")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        uuid="tide_cycle"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of days in the tide cycle',
            label='Days',
            default=90,
        )
        uuid="tide_current"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The current day in the tide cycle',
            label='Day',
            default=14,
        )
        uuid="tide_moon"
        self.values[uuid] = self.value_factory['config_boolean'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Take care of moon in tides calculation',
            label='Day',
            default=14,
        )
        uuid="tide_max_pwm"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max pwm value for the tide cycle',
            label='Day',
            default=14,
        )
        uuid="tide_max"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max hours the tide shine in a day',
            label='Max',
            default=14,
        )
        uuid="tide_min"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The min hours the tide shine i a day',
            label='Min',
            default=14,
        )
        uuid="tide_high"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the high waters in the day cycle ie 20:00',
            label='Mid.',
            default=14,
        )
        uuid="tide_low"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the low tide in the day cycle ie 12:00',
            label='Mid.',
            default=14,
        )

class airflowComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.airflow')
        name = kwargs.pop('name', "Air flow")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class timelapseComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.timelapse')
        name = kwargs.pop('name', "Timelapse")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

