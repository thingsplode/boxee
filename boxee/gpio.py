__author__ = 'tamas'
import logging
import RPi.GPIO as GPIO

logger = logging.getLogger()

class GpioConnector():
    def __init__(self, out_channels=None, in_channels=None):
        logger.info('RPI board info: %s' % GPIO.RPI_INFO)
        GPIO.setmode(GPIO.BOARD)
        if GPIO.getmode() != GPIO.BOARD:
            logger.warn('Please note, could not set GPIO Mode to GPIO.BOARD, but %s; This might create troubles around the board numbering convention' % GPIO.getmode())
        chan_list = [11,12]
        #GPIO.setup(channel, GPIO.OUT)
        #GPIO.setup(channel, GPIO.OUT, initial=GPIO.HIGH)
        if in_channels is not None:
            GPIO.setup(out_channels, GPIO.OUT)


    def set_channel_high(self, channel):
        GPIO.output(channel, GPIO.HIGH)

    def set_channel_low(self, channel):
        GPIO.output(channel, GPIO.LOW)

    def cleanup(self):
        GPIO.cleanup()