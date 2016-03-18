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
from janitoo_raspberry_i2c_hat.bus_hat import MotorHatBus
from janitoo_raspberry_i2c_hat.hat import DcMotorComponent as HatDcMotorComponent, LedComponent as HatLedComponent
#~ from janitoo_raspberry_camera.camera import CameraBus
from janitoo_raspberry_1wire.bus_1wire import OnewireBus
from janitoo_raspberry_1wire.components import DS18B20
from janitoo_raspberry_gpio.gpio import GpioBus, OutputComponent, PirComponent as PirGPIOComponent, SonicComponent as SonicGPIOComponent
from janitoo_thermal.thermal import SimpleThermostatComponent, ThermalBus
from janitoo.threads.remote import RemoteNodeComponent as RCNodeComponent

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
        self.buses['i2cbus'] = I2CBus(masters=[self], **kwargs)
        self.buses['i2chatbus'] = MotorHatBus(masters=[self], **kwargs)
        self.buses['thermal'] = ThermalBus(masters=[self], **kwargs)
        self._fishtank_lock =  threading.Lock()
        self.check_timer = None
        uuid="timer_delay"
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
        if self.check_timer is None:
            self.check_timer = threading.Timer(self.values['timer_delay'].data, self.on_check)
            self.check_timer.start()
        state = True
        if self.nodeman.is_started:
            #Check the state of some "importants sensors
            try:
                temp1 = self.nodeman.find_value('surftemp', 'temperature')
                if temp1 is None or temp1.data is None:
                    logger.warning('temp1 problemm')
                temp2 = self.nodeman.find_value('deeptemp', 'temperature').data
                if temp2 is None or temp2.data is None:
                    logger.warning('temp2 problem')
            except:
                logger.exception("[%s] - Error in on_check", self.__class__.__name__)
            #Update the cycles
            try:
                moon = self.nodeman.find_value('moon', 'factor_now')
                moonled = self.nodeman.find_value('ledmoon', 'level')
                max_moonled = self.nodeman.find_value('ledmoon', 'max_level')
                moonled.data = max_moonled.data * moon.data
                sun = self.nodeman.find_value('sun', 'factor_now')
                sunled = self.nodeman.find_value('ledsun', 'level')
                max_sunled = self.nodeman.find_value('ledsun', 'max_level')
                sunled.data = max_sunled.data * sun.data
            except:
                logger.exception("[%s] - Error in on_check", self.__class__.__name__)
            #Update the fullsun
            try:
                switch = self.nodeman.find_value('switch_fullsun', 'state')
                sun = self.nodeman.find_value('sun', 'factor_now')
                if sun.data > 0.8:
                    #Set fullsun on
                    switch.data = True
                elif sun.data < 0.79:
                    #Set fullsun off
                    switch.data = False
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

class DcMotorComponent(HatDcMotorComponent):
    """ A component for a DC motor """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.dcmotor')
        name = kwargs.pop('name', "DC Motor")
        HatDcMotorComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

class LedComponent(HatLedComponent):
    """ A component for a Led driver (PWM) """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.led')
        name = kwargs.pop('name', "Led driver")
        HatLedComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
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
        oid = kwargs.pop('oid', 'fishtank.pir')
        name = kwargs.pop('name', "PIR sensor")
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

class BiocycleComponent(JNTComponent):
    """ A 'bio' cyclecomponent"""

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.biocycle')
        name = kwargs.pop('name', "Bio cycle")
        product_name = kwargs.pop('product_name', "Bio cycle simulator")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name, hearbeat=60,
                product_name=product_name, **kwargs)
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
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="max"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max minutes for the cycle in a day',
            label='Max',
            default=kwargs.pop('max', 60),
        )
        uuid="min"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The min minutes for the cycle in a day',
            label='Min',
            default=kwargs.pop('min', 0),
        )
        uuid="last_rotate"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The last date of rotation',
            label='Last',
        )
        poll_value = self.values[uuid].create_poll_value(default=1800)
        self.values[poll_value.uuid] = poll_value
        uuid="midi"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the midi for the cycle',
            label='Mid.',
            default=kwargs.pop('midi', '16:30'),
        )
        uuid="duration"
        self.values[uuid] = self.value_factory['sensor_basic_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The duration in minutes of the cycle for the current day',
            label='Duration',
            get_data_cb=self.duration,
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="factor_day"
        self.values[uuid] = self.value_factory['sensor_basic_float'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The factor for today. A value for -1 to 1',
            label='Today',
            get_data_cb=self.factor_day,
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="factor_now"
        self.values[uuid] = self.value_factory['sensor_basic_float'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The factor for now. A value for -1 to 1',
            label='Now',
            get_data_cb=self.factor_now,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

    def current_rotate(self):
        """Rotate the current day to go ahead in the cycle
        """
        self.values['last_rotate'].set_data_index(index=0, data=datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
        nextd = self.values['current'].get_data_index(index=0)+1
        if nextd >= self.values['cycle'].data:
            self.values['current'].set_data_index(index=0, data=0)
        else:
            self.values['current'].set_data_index(index=0, data=nextd)
        if self.node is not None:
            self._bus.nodeman.publish_poll(self.mqttc, self.values['current'])
            self._bus.nodeman.publish_poll(self.mqttc, self.values['last_rotate'])

    def check_heartbeat(self):
        """Check that the component is 'available'
        """
        return True

    def factor_day(self, node_uuid, index):
        """Return the day factor
        """
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

    def start(self, mqttc):
        """Start the component. Can be used to start a thread to acquire data.

        """
        self._bus.nodeman.add_daily_job(self.current_rotate)
        return JNTComponent.start(self, mqttc)

    def stop(self):
        """Stop the component.

        """
        self._bus.nodeman.remove_daily_job(self.current_rotate)
        return JNTComponent.stop(self)

    def factor_now(self, node_uuid, index):
        """Return the instant factor
        """
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
        '''Return the cycle duration in the day
        '''
        data = None
        try:
            data = int(self.get_cycle_duration(index=index))
        except :
            logger.exception('Exception when calculationg duration')
        return data

    def _get_factor(self, current, cycle):
        """Calculate the factor"""
        return 2.0 * (current - (cycle / 2.0)) / cycle

    def get_cycle_factor(self, index=0):
        """Get the factor related to day cycle
        """
        return self._get_factor(self.values['current'].get_data_index(index=index), self.values['cycle'].get_data_index(index=index))

    def get_cycle_duration(self, index=0):
        """Get the duration in minutes of the cycle for today"""
        dfact = abs(self.get_cycle_factor())
        dlen = self.values['min'].get_data_index(index=index) + ( self.values['max'].get_data_index(index=index) - self.values['min'].get_data_index(index=index)) * dfact
        return dlen

    def get_hour_factor(self, index=0, nnow=None):
        """Get the factor
        """
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
        """Get the current status
        """
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
    """ A moon cycle component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.moon')
        name = kwargs.pop('name', "Moon")
        BiocycleComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)

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

class AirflowComponent(JNTComponent):
    """ A GPIO Output component for the air flow"""

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fishtank.airflow')
        name = kwargs.pop('name', "Air flow")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
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

