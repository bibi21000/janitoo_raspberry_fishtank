# -*- coding: utf-8 -*-

"""Unittests for Janitoo Server.
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

import sys, os
import time, datetime
import unittest
import threading
import logging
from pkg_resources import iter_entry_points

from janitoo_nosetests.server import JNTTServer, JNTTServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon
from janitoo_nosetests.component import JNTTComponent, JNTTComponentCommon

from janitoo.utils import json_dumps, json_loads
from janitoo.utils import HADD_SEP, HADD
from janitoo.utils import TOPIC_HEARTBEAT
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_SYSTEM, TOPIC_VALUES_BASIC

import janitoo_raspberry_fishtank.thread_fishtank
import janitoo_raspberry_fishtank.fishtank

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
##############################################################


class TestAmbianceComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.ambiance"

class TestTemperatureComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.temperature"

class TestSunComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.sun"

class TestBiocycleComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.biocycle"

class TestMoonComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.moon"

class TestTideComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.tide"

class TestAirflowComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.airflow"

class TestTimelapseComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.timelapse"

class TestRemoteNodeComponent(JNTTComponent, JNTTComponentCommon):
    """Test the component
    """
    component_name = "fishtank.remote_node"
