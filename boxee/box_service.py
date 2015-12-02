from core import Service, Characteristic, ReadAndNotificationCharacteristic, CharacteristicUserDescriptionDescriptor

__author__ = 'tamas'
logger = logging.getLogger(__name__)


class BoxService(Service):
    BOX_SRV_UUID = ''

    def __init__(self, bus, index, write_callback_func):
        """
            :param bus: the dbus connection
            :param index: the index of the service
        """
        Service.__init__(self, write_callback_func, bus, index, self.BOX_SRV_UUID, True)
        # self.add_characteristic(MemoryDataChrc(bus, 0, self))
        # self.add_characteristic(MemoryPercentageChrc(bus, 1, self))


class ParcelStoreCharacteristic(ReadAndNotificationCharacteristic):
    def __init__(self, bus, index, service):
        ReadAndNotificationCharacteristic.__init__(self, bus, index, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Parcel Store Characteristic"))

    def return_uuid(self):
        return ''

    def get_values(self):
        logger.debug('getting values in [%s]', __name__)
        values = []

        return values
