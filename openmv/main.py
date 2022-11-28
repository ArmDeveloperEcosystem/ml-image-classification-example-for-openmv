#
# SPDX-FileCopyrightText: Copyright 2022 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: MIT
#

# MicroPython imports
import math
import pyb
import time

# OpenMV imports
import image
import sensor
import tf

# Custom imports
import unicode_hex_keyboard

#
# Utility functions
#


def softmax(input):
    result = []

    numerator = []
    denominator = 0
    for i, item in enumerate(input):
        numerator.append(math.exp(item))
        denominator += math.exp(item)

    for i, item in enumerate(numerator):
        result.append(numerator[i] / denominator)

    return result


def set_rgb_leds(color):
    red_led.on() if "r" in color else red_led.off()
    green_led.on() if "g" in color else green_led.off()
    blue_led.on() if "b" in color else blue_led.off()


def exponential_smooth(x, s_in, alpha):
    s_out = [0] * len(s_in)

    for i in range(len(s_in)):
        s_out[i] = alpha * x[i] + (1 - alpha) * s_in[i]

    return s_out


#
# Constants
#

# used to map model classification outputs to an emoji
LABELS = ["🚫", "✋", "👎", "👍", "👊"]

# used to map model classification outputs to a RGB LED value
LED_LABELS = ["rgb", "rg", "r", "g", "b"]

# per class activation and margin of confidence thresholds
ACTIVATION_THRESHOLDS = [0, 5, 2, 2, 2]
MOC_THRESHOLDS = [0, 5, 3, 3, 3]

# alpha value for exponential smoothing
ALPHA = 0.20

# threshold for determining when a gesture is present
SMOOTHED_THRESHOLD = 0.80


#
# Global variables
#

# used to store the exponentially smoothed value
smoothed_softmax_model_output = [0] * len(LABELS)

# use to track the last classified output
last_output = -1

# objects to access the boards RGB LEDs
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

# keyboard instance to use to type emojis
#  - to use with a Linux PC pass in: unicode_hex_keyboard.LINUX
#  - to use with a Mac pass in: unicode_hex_keyboard.MACOS
#  - to use with a Windows PC pass in: unicode_hex_keyboard.WINDOWS
keyboard = unicode_hex_keyboard.UnicodeHexKeyboard(unicode_hex_keyboard.MACOS)

#
# App start
#

# Load the TensorFlow Lite model from the SD card
model = tf.load("model.tflite", load_to_fb=True)

# setup the camera sensor
sensor.reset()

# Set pixel format to GRAYSCALE
sensor.set_pixformat(sensor.GRAYSCALE)

# Set frame size to QQVGA (160x120)
sensor.set_framesize(sensor.QQVGA)

# Wait 2s for settings take effect
sensor.skip_frames(time=2000)

# main loop
while True:
    # get an image from the camera sensor
    img = sensor.snapshot()

    # get the model output for the image
    classification_result = model.classify(img)
    model_output = classification_result[0].output()

    # calculate the softmax outputs for the model
    softmax_model_output = softmax(model_output)

    # sort the model output and calculate the margin of confidence using the two highest values
    sorted_model_output = model_output.copy()
    sorted_model_output.sort(reverse=True)

    margin_of_confidence = sorted_model_output[0] - sorted_model_output[1]

    # use the output index with the highest value as the classification
    classification = model_output.index(max(model_output))

    # use activation and margin of confidence thresholds to determine the certainty of the model
    # output
    above_activation_threshold = (
        sorted_model_output[0] > ACTIVATION_THRESHOLDS[classification]
    )
    above_moc_threshold = margin_of_confidence > MOC_THRESHOLDS[classification]

    if above_activation_threshold and above_moc_threshold:
        # high certainty output, print, and update RGB LED
        print(
            model_output,
            softmax_model_output,
            margin_of_confidence,
            LABELS[classification],
        )
        set_rgb_leds(LED_LABELS[classification])
    else:
        # low certainty output, print, and update RGB LED to no gesture color
        print(model_output, softmax_model_output, margin_of_confidence)
        set_rgb_leds(LED_LABELS[0])

        # override the softmax model output value to be no gesture
        softmax_model_output = [0] * len(softmax_model_output)
        softmax_model_output[0] = 1

    # exponentially smooth the new softmax model output
    smoothed_softmax_model_output = exponential_smooth(
        softmax_model_output, smoothed_softmax_model_output, ALPHA
    )

    # use the smoothed output index with the highest value as the smoothed classification
    smoothed_classification = smoothed_softmax_model_output.index(
        max(smoothed_softmax_model_output)
    )

    if (
        smoothed_softmax_model_output[smoothed_classification] > SMOOTHED_THRESHOLD
        and last_output is not smoothed_classification
    ):
        # the smoothed classification is above the desired threshold and has a new value
        if smoothed_classification is not 0:
            print(f"Ready to send {LABELS[smoothed_classification]} emoji")

            # "type" the emoji value using USB HID
            keyboard.send(LABELS[smoothed_classification])

        # update last output value with the new value
        last_output = smoothed_classification
