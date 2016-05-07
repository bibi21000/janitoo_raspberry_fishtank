# -*- coding: utf-8 -*-
"""The Raspberry fishtank

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
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

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
from janitoo_raspberry_spi.bus_spi import SPIBus
from janitoo_raspberry_i2c.bus_i2c import I2CBus
from janitoo_raspberry_i2c_pca9685.pca9685 import PwmComponent as Pca9685PwmComponent, DcMotorComponent as Pca9685DcMotorComponent
#~ from janitoo_raspberry_camera.camera import CameraBus
from janitoo_raspberry_1wire.bus_1wire import OnewireBus
from janitoo_raspberry_1wire.components import DS18B20
from janitoo_raspberry_spi_ili9341.ili9341 import ScreenComponent as IliScreenComponent
from janitoo_raspberry_gpio.gpio import GpioBus, OutputComponent, PirComponent as PirGPIOComponent, SonicComponent as SonicGPIOComponent
from janitoo_thermal.thermal import SimpleThermostatComponent, ThermalBus
from janitoo_events.component import BiocycleComponent
from janitoo_events.bus import EventsBus
from janitoo_factory.threads.remote import RemoteNodeComponent as RCNodeComponent

from janitoo_raspberry_fishtank.thread_fishtank import OID

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

def make_airflow(**kwargs):
    return AirflowComponent(**kwargs)

def make_timelapse(**kwargs):
    return TimelapseComponent(**kwargs)

def make_remote_node(**kwargs):
    return RemoteNodeComponent(**kwargs)

def make_dcmotor(**kwargs):
    return DcMotorComponent(**kwargs)

def make_led(**kwargs):
    return LedComponent(**kwargs)

def make_thermostat(**kwargs):
    return ThermostatComponent(**kwargs)

def make_switch_fullsun(**kwargs):
    return SwitchFullsunComponent(**kwargs)

def make_pir(**kwargs):
    return PirComponent(**kwargs)

def make_sonic(**kwargs):
    return SonicComponent(**kwargs)

def make_screen(**kwargs):
    return ScreenComponent(**kwargs)

class FishtankBus(JNTBus):
    """A bus to manage Fishtank
    """
    def __init__(self, **kwargs):
        """
        """
        JNTBus.__init__(self, **kwargs)
        self.buses = {}
        self.buses['owbus'] = OnewireBus(masters=[self], **kwargs)
        self.buses['gpiobus'] = GpioBus(masters=[self], **kwargs)
        self.buses['spibus'] = SPIBus(masters=[self], **kwargs)
        self.buses['i2cbus'] = I2CBus(masters=[self], **kwargs)
        self.buses['thermal'] = ThermalBus(masters=[self], **kwargs)
        self.buses['events'] = EventsBus(masters=[self], **kwargs)
        self._fishtank_lock =  threading.Lock()
        self.check_timer = None
        uuid="%s_timer_delay"%OID
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The delay between 2 checks',
            label='Timer.',
            default=45,
        )

    def stop_check(self):
        """Check that the component is 'available'

        """
        if self.check_timer is not None:
            self.check_timer.cancel()
            self.check_timer = None

    def on_check(self):
        """Make a check using a timer.

        """
        self.stop_check()
        if self.check_timer is None and self.is_started:
            self.check_timer = threading.Timer(self.values["%s_timer_delay"%OID].data, self.on_check)
            self.check_timer.start()
        state = True
        if self.nodeman.is_started:
            #Check the state of some "importants sensors
            try:
                temp1 = self.nodeman.find_value('surftemp', 'temperature')
                if temp1 is None or temp1.data is None:
                    logger.warning('temp1 problemm')
                temp2 = self.nodeman.find_value('deeptemp', 'temperature')
                if temp2 is None or temp2.data is None:
                    logger.warning('temp2 problem')
            except:
                logger.exception("[%s] - Error in on_check", self.__class__.__name__)
        if self.nodeman.is_started:
            #Update the cycles
            try:
                moon = self.nodeman.find_value('moon', 'factor_now')
                moonled = self.nodeman.find_value('ledmoon', 'level')
                max_moonled = self.nodeman.find_value('ledmoon', 'max_level')
                moonled.data = int(max_moonled.data * moon.data)
                sun = self.nodeman.find_value('sun', 'factor_now')
                sunled = self.nodeman.find_value('ledsun', 'level')
                max_sunled = self.nodeman.find_value('ledsun', 'max_level')
                sunled.data = int(max_sunled.data * sun.data)
            except:
                logger.exception("[%s] - Error in on_check", self.__class__.__name__)
        if self.nodeman.is_started:
            #Update the fullsun
            try:
                switch = self.nodeman.find_value('switch_fullsun', 'switch')
                sun = self.nodeman.find_value('sun', 'factor_now')
                if sun.data > 0.8:
                    #Set fullsun on
                    switch.data = 'on'
                elif sun.data < 0.79:
                    #Set fullsun off
                    switch.data = 'on'
            except:
                logger.exception("[%s] - Error in on_check", self.__class__.__name__)

    def start(self, mqttc, trigger_thread_reload_cb=None):
        """Start the bus
        """
        for bus in self.buses:
            self.buses[bus].start(mqttc, trigger_thread_reload_cb=None)
        JNTBus.start(self, mqttc, trigger_thread_reload_cb)
        self.on_check()

    def stop(self):
        """Stop the bus
        """
        self.stop_check()
        for bus in self.buses:
            self.buses[bus].stop()
        JNTBus.stop(self)

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        res = True
        #~ for bus in self.buses:
            #~ res = res and self.buses[bus].check_heartbeat()
        return res

    def loop(self, stopevent):
        """Retrieve data
        Don't do long task in loop. Use a separated thread to not perturbate the nodeman

        """
        for bus in self.buses:
            self.buses[bus].loop(stopevent)

class RemoteNodeComponent(RCNodeComponent):
    """ A remote component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.remote_node')
        name = kwargs.pop('name', "Remote node")
        RCNodeComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class AmbianceComponent(DHTComponent):
    """ A component for ambiance """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.ambiance')
        name = kwargs.pop('name', "Ambiance sensor")
        DHTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class DcMotorComponent(Pca9685DcMotorComponent):
    """ A component for a DC motor """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.dcmotor')
        name = kwargs.pop('name', "DC Motor")
        Pca9685DcMotorComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class LedComponent(Pca9685PwmComponent):
    """ A component for a Led driver (PWM) """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.led')
        name = kwargs.pop('name', "Led driver")
        Pca9685PwmComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class PirComponent(PirGPIOComponent):
    """ A Pir component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.pir')
        name = kwargs.pop('name', "PIR sensor")
        PirGPIOComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class SonicComponent(SonicGPIOComponent):
    """ A Sonic component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.sonic')
        name = kwargs.pop('name', "Sonic sensor")
        SonicGPIOComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class TemperatureComponent(DS18B20):
    """ A water temperature component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.temperature')
        name = kwargs.pop('name', "Temperature")
        DS18B20.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class MoonComponent(BiocycleComponent):
    """ A moon cycle component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.moon')
        name = kwargs.pop('name', "Moon")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class SunComponent(BiocycleComponent):
    """ A sun cycle component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.sun')
        name = kwargs.pop('name', "Sun")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class TideComponent(BiocycleComponent):
    """ A tide cycle component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.tide')
        name = kwargs.pop('name', "Tide")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class SwitchFullsunComponent(OutputComponent):
    """ A GPIO Output component for the full sun"""

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.switch_fullsun')
        name = kwargs.pop('name', "Fullsun")
        OutputComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class AirflowComponent(OutputComponent):
    """ A GPIO Output component for the air flow"""

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.airflow')
        name = kwargs.pop('name', "Air flow")
        OutputComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class TimelapseComponent(JNTComponent):
    """ A timelapse component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.timelapse')
        name = kwargs.pop('name', "Timelapse")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

    def check_heartbeat(self):
        """Check that the component is 'available'
        """
        return True

class ScreenComponent(IliScreenComponent):
    """ A timelapse component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.screen')
        name = kwargs.pop('name', "Screen")
        IliScreenComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

    def check_heartbeat(self):
        """Check that the component is 'available'
        """
        return True

class ThermostatComponent(SimpleThermostatComponent):
    """ A thermostat for water """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.thermostat')
        name = kwargs.pop('name', "Timelapse")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

    def get_sensors(self):
        """Return a list of all available sensors
        """
        return self._bus.find_values('fishtank.temperature', 'temperature')

    def get_heaters(self):
        """Return a list of all available heaters (relays)
        """
        values = self._bus.find_values('fishtank.external_heater', 'users_write')

    def get_sensors_temperature(self, sensors):
        """Return the temperature of the zone. Can be calculated from differents sensors.
        """
        nb = 0
        tt = None
        for t in sensors:
            temp = t.data
            if temp is not None:
                tt = tt + temp if tt is not None else temp
                nb += 1
        if tt is None:
            return None
        return tt / nb

    def activate_heaters(self, heaters):
        """Activate all heaters in the zone
        """
        state = heaters[0].get_cache(index=0)
        onstate = heaters[0].get_value_config(index=0)[3]
        if state != onstate:
            heaters[0].set_cache(index=0, data=onstate)
            logger.debug("[%s] - [%s] --------------------------------- Update heater to onstate.", self.__class__.__name__, self.uuid)

