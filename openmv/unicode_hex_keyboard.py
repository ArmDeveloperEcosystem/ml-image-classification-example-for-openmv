#
# SPDX-FileCopyrightText: Copyright 2022 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: MIT
#

# MicroPython imports
import pyb

#
# Constants
#
LINUX = const(1)
MACOS = const(2)
WINDOWS = const(3)


class UnicodeHexKeyboard:
    def __init__(self, mode):
        self.hid = pyb.USB_HID()
        self.buffer = bytearray(8)
        self.mode = mode

    def utf8_to_utf16(self, input):
        result = 0

        input -= 0x10000

        result |= input & 0x3FF
        result |= (input << 6) & 0x03FF0000
        result |= 0xD800DC00

        return result

    def hid_send(self, modifiers, key_code, modifier_up=True):
        # key down
        self.buffer[0] = modifiers
        self.buffer[2] = key_code

        self.hid.send(self.buffer)
        pyb.delay(20)

        # key up
        if modifier_up:
            self.buffer[0] = 0
        self.buffer[2] = 0

        self.hid.send(self.buffer)
        pyb.delay(20)

    def send_hex_digit(self, modifier, digit):
        if digit >= 10:
            key_code = (digit - 10) + 4
        elif digit > 0:
            key_code = (digit - 1) + 30
        else:
            key_code = 39

        self.hid_send(modifier, key_code)

    def send_linux(self, utf):
        self.hid_send(3, 0x18)  # ctrl + shift + u

        hex_utf_str = hex(utf)[2:]

        for char in hex_utf_str:
            hex_digit = int(char, 16)

            self.send_hex_digit(0, hex_digit)

        self.hid_send(0, 0x2C)  # space

    def send_macos(self, utf):
        if utf >= 0x10000:
            utf = self.utf8_to_utf16(utf)

        hex_utf_str = hex(utf)[2:]

        for char in hex_utf_str:
            hex_digit = int(char, 16)

            self.send_hex_digit(4, hex_digit)  # alt/option

    def send_windows(self, utf):
        utf_str = str(utf)

        self.hid_send(4, 0x57, False)  # alt +

        for char in utf_str:
            digit = int(char, 10)
            if digit == 0:
                digit = 10

            self.hid_send(4, digit + 0x58, False)

        self.hid_send(0, 0x00, False)

    def send(self, s):
        for c in s:
            utf = ord(c)

            if self.mode is LINUX:
                self.send_linux(utf)
            elif self.mode is MACOS:
                self.send_macos(utf)
            elif self.mode is WINDOWS:
                self.send_windows(utf)
