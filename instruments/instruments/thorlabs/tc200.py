#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# lcc25.py: class for the Thorlabs LCC25 Liquid Crystal Controller
##
# © 2014 Steven Casagrande (scasagrande@galvant.ca).
#
# This file is a part of the InstrumentKit project.
# Licensed under the AGPL version 3.
##
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##
# TC200 Class contributed by Catherine Holloway
#
## IMPORTS #####################################################################

import quantities as pq
from flufl.enum import IntEnum

from instruments.abstract_instruments import Instrument
from instruments.util_fns import assume_units

## CLASSES #####################################################################

class TC200(Instrument):
    """
    The TC200 is is a controller for the voltage across a heating element. It can also read in the temperature off of a
    thermistor and implements a PID control to keep the temperature at a set value.
    The user manual can be found here:
    http://www.thorlabs.com/thorcat/12500/TC200-Manual.pdf
    """
    def __init__(self, filelike):
        super(TC200, self).__init__(filelike)
        self.terminator = "\r"
        self.end_terminator = ">"

    ## ENUMS ##

    class Mode(IntEnum):
        normal = 0
        cycle = 1

    class Sensor(IntEnum):
        ptc100 = 0
        ptc1000 = 1
        th10k = 2

    ## PROPERTIES ##

    def name(self):
        """
        gets the name and version number of the device
        """
        response = self.check_command("*idn?")
        if response is "CMD_NOT_DEFINED":
            self.name()
        else:
            return response

    @property
    def frequency(self):
        """
        Gets/sets the frequency at which the LCC oscillates between the
        two voltages.

        :units: As specified (if a `~quantities.Quantity`) or assumed to be
            of units Hertz.
        :type: `~quantities.Quantity`
        """
        response = self.check_command("freq?")
        if not response is "CMD_NOT_DEFINED":
            return float(response)*pq.Hz
    @frequency.setter
    def frequency(self, newval):
        newval = assume_units(newval, pq.Hz).rescale(pq.Hz).magnitude
        if newval < 5:
            raise ValueError("Frequency is too low.")
        if newval >150:
            raise ValueError("Frequency is too high")
        self.sendcmd("freq={}".format(newval))

    @property
    def mode(self):
        """
        Gets/sets the output mode of the TC200

        :type: `TC200.Mode`
        """
        response = self.check_command("stat?")
        if not response is "CMD_NOT_DEFINED":
            response_code = (int(response) << 1) % 2
            return TC200.Mode[response_code]

    @mode.setter
    def mode(self, newval):
        if newval.enum is not TC200.Mode:
            raise TypeError("Mode setting must be a `TC200.Mode` value, "
                "got {} instead.".format(type(newval)))
        response = self.query("mode={}".format(newval.name))

    @property
    def enable(self):
        """
        Gets/sets the heater enable status.

        If output enable is on (`True`), there is a voltage on the output.

        :rtype: `bool`
        """
        response = self.check_command("stat?")
        if not response is "CMD_NOT_DEFINED":
            return True if int(response) % 2 is 1 else False

    @enable.setter
    def enable(self, newval):
        if not isinstance(newval, bool):
            raise TypeError("TC200 enable property must be specified with a "
                            "boolean.")
        # the "ens" command is a toggle, we need to track two different cases, when it should be on and it is off,
        # and when it is off and should be on
        if newval and not self.enable:
            self.sendcmd("ens")
        elif not newval and self.enable:
            self.sendcmd("ens")

    @property
    def p(self):
        """
        Gets/sets the pgain

        :return: the gain (in nnn)
        :rtype: int
        """
        response = self.check_command("pid?")
        if not response is "CMD_NOT_DEFINED":
            return int(response.split(",")[0])

    @p.setter
    def p(self, newval):
        if newval < 1:
            raise ValueError("P-Value is too low.")
        if newval > 250:
            raise ValueError("P-Value is too high")
        self.sendcmd("pvalue={}".format(newval))

    @property
    def i(self):
        """
        Gets/sets the igain

        :return: the gain (in nnn)
        :rtype: int
        """
        response = self.check_command("pid?")
        if not response is "CMD_NOT_DEFINED":
            return int(response.split(",")[1])

    @i.setter
    def i(self, newval):
        if newval < 0:
            raise ValueError("I-Value is too low.")
        if newval > 250:
            raise ValueError("I-Value is too high")
        self.sendcmd("ivalue={}".format(newval))

    @property
    def d(self):
        """
        Gets/sets the dgain

        :return: the gain (in nnn)
        :rtype: int
        """
        response = self.check_command("pid?")
        if not response is "CMD_NOT_DEFINED":
            return int(response.split(",")[2])

    @d.setter
    def d(self, newval):
        if newval < 0:
            raise ValueError("D-Value is too low.")
        if newval > 250:
            raise ValueError("D-Value is too high")
        self.sendcmd("dvalue={}".format(newval))

    @property
    def degrees(self):
        """
        Gets/sets the mode of the temperature measurement.

        :type: `~quantities.unitquantity.UnitTemperature`
        """
        response = self.check_command("stat?")
        if not response is "CMD_NOT_DEFINED":
            if (response << 4 ) % 2:
                return pq.degC
            elif (response << 5) % 2:
                return pq.degF
            else:
                return pq.degK

    @degrees.setter
    def degrees(self, newval):
        if newval is pq.degC:
            self.sendcmd("unit=c")
        elif newval is pq.degF:
            self.sendcmd("unit=f")
        elif newval is pq.degK:
            self.sendcmd("unit=k")
        else:
            raise TypeError("Invalid temperature type")

    @property
    def sensor(self):
        """
        Gets/sets the current thermistor type. Used for converting resistances to temperatures.

        :rtype: TC200.Sensor

        """
        response = self.check_command("sns?")
        if not response is "CMD_NOT_DEFINED":
            return TC200.Sensor(response)

    @sensor.setter
    def sensor(self, newval):
        if newval.enum is not TC200.Sensor:
            raise TypeError("Sensor setting must be a `TC200.Sensor` value, "
                "got {} instead.".format(type(newval)))
        self.sendcmd("sns={}".format(newval.name))

    @property
    def beta(self):
        """
        Gets/sets the beta value of the thermistor curve.

        :return: the gain (in nnn)
        :rtype: int
        """
        response = self.check_command("beta?")
        if not response is "CMD_NOT_DEFINED":
            return int(response)

    @beta.setter
    def beta(self, newval):
        if newval < 2000:
            raise ValueError("Beta Value is too low.")
        if newval > 6000:
            raise ValueError("Beta Value is too high")
        self.sendcmd("beta={}".format(newval))

    @property
    def max_power(self):
        """
        Gets/sets the maximum power

        :return: the maximum power (in Watts)
        :rtype: `~quantities.Quantity`
        """
        response = self.check_command("PMAX?")
        if not response is "CMD_NOT_DEFINED":
            return float(response)*pq.W

    @max_power.setter
    def max_power(self, newval):
        newval = assume_units(newval, pq.W).rescale(pq.W).magnitude
        if newval < 0.1:
            raise ValueError("Power is too low.")
        if newval > 18.0:
            raise ValueError("Power is too high")
        self.sendcmd("PMAX={}".format(newval))

    @property
    def max_temperature(self):
        """
        Gets/sets the maximum temperature

        :return: the maximum temperature (in deg C)
        :rtype: `~quantities.Quantity`
        """
        response = self.check_command("TMAX?")
        if not response is "CMD_NOT_DEFINED":
            return float(response)*pq.degC

    @max_temperature.setter
    def max_power(self, newval):
        newval = assume_units(newval, pq.degC).rescale(pq.degC).magnitude
        if newval < 20:
            raise ValueError("Temperature is too low.")
        if newval > 205.0:
            raise ValueError("Temperature is too high")
        self.sendcmd("TMAX={}".format(newval))

    # The Cycles functionality of the TC200 is currently unimplemented, as it is complex, and its functionality is
    # redundant given a python interface to TC200

    ## METHODS ##

    def check_command(self, command):
        """
        Checks for the \"Command error CMD_NOT_DEFINED\" error, which can
        sometimes occur if there were incorrect terminators on the previous
        command. If the command is successful, it returns the value, if not,
        it returns CMD_NOT_DEFINED

        check_command will also clear out the query string
        """
        response = self.query(command)
        response = self.read()
        cmd_find = response.find("CMD_NOT_DEFINED")
        if cmd_find ==-1:
            error_find = response.find("CMD_ARG_INVALID")
            if error_find ==-1:
                output_str = response.replace(command,"")
                output_str = output_str.replace(self.terminator,"")
                output_str = output_str.replace(self.end_terminator,"")
            else:
                output_str = "CMD_ARG_INVALID"
        else:
            output_str = "CMD_NOT_DEFINED"
        return output_str

