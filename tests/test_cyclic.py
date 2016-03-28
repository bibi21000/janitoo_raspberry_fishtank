# -*- coding: utf-8 -*-

"""Unittests for Janitoo-Roomba Server.
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

import warnings
warnings.filterwarnings("ignore")

import sys, os
import time, datetime
import unittest
import threading
import logging
from logging.config import fileConfig as logging_fileConfig
from pkg_resources import iter_entry_points
import datetime
import mock

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.server import JNTTServer, JNTTServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon
from janitoo_nosetests.thread import JNTTThreadRun, JNTTThreadRunCommon
from janitoo_nosetests.component import JNTTComponent, JNTTComponentCommon

from janitoo.utils import json_dumps, json_loads
from janitoo.utils import HADD_SEP, HADD
from janitoo.utils import TOPIC_HEARTBEAT
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.options import JNTOptions
from janitoo.runner import jnt_parse_args

from janitoo_raspberry_fishtank.fishtank import FishtankBus, MoonComponent

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
##############################################################

class FakeNodeman(object):
    section='fishtank'

class TestCyclicEvent(JNTTBase):
    """Test
    """
    conf_file = "tests/data/janitoo_raspberry_fishtank.conf"
    prog = 'test'

    def test_021_rotate_cycle(self):
        logging_fileConfig(self.conf_file)
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=%s'%self.conf_file]):
            options = vars(jnt_parse_args())
        self.options = JNTOptions(options)
        bus = FishtankBus(options=self.options)
        bus.nodeman=FakeNodeman()
        #~ bus.start(None)
        bc = MoonComponent(bus=bus, cycle=28, current=0, min=0, max=60, options=self.options, node_uuid='fishtank__moon')
        print bc.values['current'].get_data_index(node_uuid='moon', index=0)
        bc.current_rotate()
        print bc.values['current'].get_data_index(node_uuid='moon', index=0)
