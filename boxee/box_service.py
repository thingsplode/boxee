from core import Service, Characteristic, CharacteristicUserDescriptionDescriptor
import logging
import dbus
import core
import persistence
import gpio
from exceptions import NotSupportedException

__author__ = 'tamas'
logger = logging.getLogger(__name__)
result_codes = None


def enum(**enums):
    return type('Enum', (), enums)


class BoxManager:
    def __init__(self, box_dao, gpio_connector):
        """
        :param box_dao:
        :return:
        :type box_dao: persistence.BoxDao
        :type gpio_connector: gpio.GpioConnector
        """
        global result_codes
        result_codes = enum(STORED=0x00, SLOTS_NOT_AVAILABLE=0x01, PARCEL_RELEASED=0x02, PARCEL_NOT_FOUND=0x03,
                            INVALID_DATA=0x04, GENERIC_FAILURE=0x255)
        self.box_dao = box_dao
        self.gpio = gpio_connector

    def store_parcel(self, barcode):
        try:
            logger.debug('preparing to store parcel identified by barcode [%s]', barcode)
            empty_slots = self.box_dao.fetch_empty_slots()
            if empty_slots is None or len(empty_slots) == 0:
                logger.warn('there are no free slots available for storing parcel')
                return result_codes.SLOTS_NOT_AVAILABLE, 0
            else:
                slot_id = empty_slots[0][0]
                self.gpio.open_slot(slot_id)
                self.box_dao.update_box(slot_id, True, barcode)
                logger.debug('parcel stored at slot id [%s] with barcode [%s]', slot_id, barcode)
                return result_codes.STORED, slot_id
        except BaseException as ex:
            logger.error('Error while storing parcel: %s', str(ex))
            return result_codes.GENERIC_FAILURE, 0

    def release_parcel(self, barcode):
        try:
            logger.debug('searching for parcel with barcode [%s] for release', barcode)
            slot_id = self.box_dao.fetch_slot_by_barcode(barcode)
            if slot_id <= 0:
                logger.warn('required parcel [%s] is not found.', barcode)
                return result_codes.PARCEL_NOT_FOUND, 0
            else:
                self.box_dao.update_box(slot_id, False, '')
                self.gpio.open_slot(slot_id)
                logger.debug('parcel identified by [%s] is released from slot [%s]', barcode, slot_id)
                return result_codes.PARCEL_RELEASED, slot_id
        except BaseException as ex:
            logger.error('Error while releasing parcel: %s', str(ex))
            return result_codes.GENERIC_FAILURE, 0


class BoxService(Service):
    BOX_SRV_UUID = '8fad8bdd-d619-4bd9-b3c1-816129f417ca'

    def __init__(self, box_dao, gpio_connector, bus, index):
        """
            :param bus: the dbus connection
            :param index: the index of the service
            :type box_dao: persistence.BoxDao
            :type gpio_connector: gpio.GpioConnector
        """
        Service.__init__(self, self.service_write_cb, bus, index, self.BOX_SRV_UUID, True)
        self.box_manager = BoxManager(box_dao, gpio_connector)
        self.add_characteristic(ParcelStoreCharacteristic(bus, 0, self.box_manager, self))
        self.add_characteristic(ParcelReleaseCharacteristic(bus, 1, self.box_manager, self))

    def service_write_cb(self, signal_dictionary):
        pass
        # characteristic.notify_cb()


class ParcelCharacteristic(Characteristic):
    def __init__(self, bus, index, box_manager, service):
        """
        Parcel storage bluetooth low enegergy characteristic
        :param bus:
        :param index:
        :param box_manager:
        :param service:
        :type box_manager: BoxManager
        :return:
        """
        Characteristic.__init__(self, bus, index, self.return_uuid(), ['read', 'notify', 'write'], service)
        self.box_manager = box_manager
        self.notifying = False

    def return_uuid(self):
        logger.warn('Default return UUID is called  (not implemented). Please override this method.')
        raise NotSupportedException()

    def write_action(self, value):
        logger.warn('Default write is called  (not implemented). Please override this method.')
        raise NotSupportedException()

    def WriteValue(self, value):
        # self.get_service().callback({self.__class__.__name__:value})
        if len(value) == 0:
            # no barcode value is sent
            self.notify(result_codes.INVALID_DATA, 0)
        else:
            # barcode value is available
            self.write_action(value)

    def StartNotify(self):
        if self.notifying:
            # Already notifying, nothing to do
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            # Not notifying, nothing to do
            return
        self.notifying = False

    def notify(self, code, slot):
        """
        :param code: the result code of the completion
        :param slot: the slot where the
        :return:
        """
        if self.notifying:
            logger.debug('Notifying with response code [%s] and slot [%s]', code, slot)
            value_array = [dbus.Byte(code), dbus.Byte(slot)]
            self.PropertiesChanged(core.GATT_CHRC_IFACE, {'Value': value_array}, [])
        else:
            logger.warn('notification is not enabled')


class ParcelStoreCharacteristic(ParcelCharacteristic):
    def __init__(self, bus, index, box_manager, service):
        ParcelCharacteristic.__init__(self, bus, index, box_manager, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Parcel Store Characteristic"))

    def return_uuid(self):
        return 'f76e76fc-a36a-49ab-85d3-9ac389b12ef8'

    def write_action(self, value):
        try:
            res = self.box_manager.store_parcel("".join(map(chr, value)))
            self.notify(res[0], res[1])
        except BaseException as e:
            logger.error('notification failed during write due to: %s', str(e))


class ParcelReleaseCharacteristic(ParcelCharacteristic):
    def __init__(self, bus, index, box_manager, service):
        ParcelCharacteristic.__init__(self, bus, index, box_manager, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Parcel Release Characteristic"))

    def return_uuid(self):
        return 'e8dbd220-6391-4498-a19b-33adb3543a33'

    def write_action(self, value):
        try:
            res = self.box_manager.release_parcel("".join(map(chr, value)))
            print ('notification results: %s and %s ', res[0], res[1])
            self.notify(res[0], res[1])
        except BaseException as e:
            logger.error('notification failed during write due to: %s', str(e))
