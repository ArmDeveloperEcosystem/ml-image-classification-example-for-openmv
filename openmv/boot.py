#
# SPDX-FileCopyrightText: Copyright 2022 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: MIT
#

import pyb

pyb.usb_mode("VCP+MSC+HID", hid=pyb.hid_keyboard)
