""" 
NanoPyMataCore class.

This class is based on:
  - pymata_core.py developed by Alan Yorinks.
  - circuitplayground.py developed by Tony DiCola.

Copyright (c) 2015-16 Alan Yorinks All rights reserved.
Copyright (C) 2016 Tony DiCola.  All rights reserved.
Copyright (C) 2016 Jose Juan Sanchez.  All rights reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU  General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.
"""

import struct
import asyncio
from pymata_aio.pymata_core import PymataCore
from pymata_aio.private_constants import PrivateConstants
from nanoplayboard.nano_constants import NanoConstants


class NanoPymataCore(PymataCore):

    def __init__(self):
        super().__init__()

        self.command_dictionary = {PrivateConstants.REPORT_VERSION:
                                   self._report_version,
                                   PrivateConstants.REPORT_FIRMWARE:
                                       self._report_firmware,
                                   PrivateConstants.CAPABILITY_RESPONSE:
                                       self._capability_response,
                                   PrivateConstants.ANALOG_MAPPING_RESPONSE:
                                       self._analog_mapping_response,
                                   PrivateConstants.PIN_STATE_RESPONSE:
                                       self._pin_state_response,
                                   PrivateConstants.STRING_DATA:
                                       self._string_data,
                                   PrivateConstants.ANALOG_MESSAGE:
                                       self._analog_message,
                                   PrivateConstants.DIGITAL_MESSAGE:
                                       self._digital_message,
                                   PrivateConstants.I2C_REPLY:
                                       self._i2c_reply,
                                   PrivateConstants.SONAR_DATA:
                                       self._sonar_data,
                                   PrivateConstants.ENCODER_DATA:
                                       self._encoder_data,
                                   PrivateConstants.PIXY_DATA:
                                       self._pixy_data,
                                   NanoConstants.POTENTIOMETER_READ:
                                       self._potentiometer_data}

        # report query results are stored in this dictionary
        self.query_reply_data = {PrivateConstants.REPORT_VERSION: '',
                                 PrivateConstants.STRING_DATA: '',
                                 PrivateConstants.REPORT_FIRMWARE: '',
                                 PrivateConstants.CAPABILITY_RESPONSE: None,
                                 PrivateConstants.ANALOG_MAPPING_RESPONSE: None,
                                 PrivateConstants.PIN_STATE_RESPONSE: None,
                                 NanoConstants.POTENTIOMETER_READ: None}

        self._potentiometer_callback = None

    '''
    Rgb led
    '''

    async def _rgb_set_color(self, r, g, b):
        d1 = r >> 1
        d2 = ((r & 0x01) << 6) | (g >> 2)
        d3 = ((g & 0x03) << 5) | (b >> 3)
        d4 = (b & 0x07) << 4
        data = [NanoConstants.RGB_SET_COLOR, d1, d2, d3, d4]
        await self._send_sysex(NanoConstants.COMMAND, data)

    async def _rgb_on(self):
        data = [NanoConstants.RGB_ON]
        await self._send_sysex(NanoConstants.COMMAND, data)

    async def _rgb_off(self):
        data = [NanoConstants.RGB_OFF]
        await self._send_sysex(NanoConstants.COMMAND, data)

    async def _rgb_toggle(self):
        data = [NanoConstants.RGB_TOGGLE]
        await self._send_sysex(NanoConstants.COMMAND, data)

    async def _rgb_set_intensity(self, intensity):
        data = [NanoConstants.RGB_SET_INTENSITY, intensity & 0x7F]
        await self._send_sysex(NanoConstants.COMMAND, data)

    '''
    Potentiometer
    '''

    async def _potentiometer_read(self):
        if self.query_reply_data.get(NanoConstants.POTENTIOMETER_READ) == None:
            data = [NanoConstants.POTENTIOMETER_READ]
            await self._send_sysex(NanoConstants.COMMAND, data)
            while self.query_reply_data.get(
                    NanoConstants.POTENTIOMETER_READ) == None:
                await asyncio.sleep(self.sleep_tune)
            value = self.query_reply_data.get(
                NanoConstants.POTENTIOMETER_READ)
            self.query_reply_data[
                NanoConstants.POTENTIOMETER_READ] = None
            return value

    async def _potentiometer_data(self, data):
        pot_value = self._parse_firmata_uint16(data[3:-1])
        self.query_reply_data[
            NanoConstants.POTENTIOMETER_READ] = pot_value
        if self._potentiometer_callback is not None:
            self._potentiometer_callback(pot_value)

    '''
    Buzzer
    '''

    async def _buzzer_play_tone(self, frequency_hz, duration_ms):
        f1 = frequency_hz & 0x7F
        f2 = frequency_hz >> 7
        d1 = duration_ms & 0x7F
        d2 = duration_ms >> 7
        data = [NanoConstants.BUZZER_PLAY_TONE, f1, f2, d1, d2]
        await self._send_sysex(NanoConstants.COMMAND, data)

    async def _buzzer_stop_tone(self):
        data = [NanoConstants.BUZZER_STOP_TONE]
        await self._send_sysex(NanoConstants.COMMAND, data)

    '''
    Utilities
    '''

    def _parse_firmata_byte(self, data):
        """Parse a byte value from two 7-bit byte firmata response bytes."""
        if len(data) != 2:
            raise ValueError(
                'Expected 2 bytes of firmata repsonse for a byte value!')
        return (data[0] & 0x7F) | ((data[1] & 0x01) << 7)

    def _parse_firmata_uint16(self, data):
        """Parse a 2 byte unsigned integer value from a 7-bit byte firmata response
        byte array.  Each pair of firmata 7-bit response bytes represents a single
        byte of int data so there should be 4 firmata response bytes total.
        """
        if len(data) != 4:
            raise ValueError(
                'Expected 4 bytes of firmata response for int value!')
        # Convert 2 7-bit bytes in little endian format to 1 8-bit byte for each
        # of the two unsigned int bytes.
        raw_bytes = bytearray(2)
        for i in range(2):
            raw_bytes[i] = self._parse_firmata_byte(data[i * 2:i * 2 + 2])
        # Use struct unpack to convert to unsigned short value.
        return struct.unpack('<H', raw_bytes)[0]