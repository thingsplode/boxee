__author__ = 'tamas'
from boxee.core import Advertisement

class BoxAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.include_tx_power = True
