"""
Core domain objects for GATT Bluetooth Low Energy devices.

Glossary:
GAP Roles: central and peripheral
Peripheral (~ Server): can advertise; he Peripheral could be called a Slave; GATT Server; most common for a Peripheral to be a Server;
Central (~ Client): that can actually send a connection request to estalish a connection; Central is sometimes called a Master; GATT Client; most common for a Central to be a Client;

"""
import dbus.service
import dbus
import dbus.exceptions
import array
import logging
import gobject
from exceptions import InvalidArgsException, NotSupportedException, NotPermittedException

__author__ = 'tamas'

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MGR_IFACE = 'org.bluez.GattManager1'
ADAPTER_IFACE = 'org.bluez.Adapter1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'
logger = logging.getLogger(__name__)

class Service(dbus.service.Object):
    """
    Main GATT Service with path base: /org/bluez/example/service

    To avoid constantly transmitting 16 bytes which can be wasteful (Bluetooth is very limited in the amount of data and 16 bytes are significant), the Bluetooth SIG has adopted a standard UUID base. This base forms the first 96 bits (12 bytes)  of the 128-bit UUID. The rest of the bits are defined by the Bluetooth SIG:

    XXXXXXXX-0000-1000-8000-00805F9B34FB
    """
    PATH_BASE = '/org/bluez/boxee/service'

    def __init__(self, write_callback_func, bus, index, uuid, primary):
        """
            :param write_callback_func: the callback function when some results need to be passed
            :param bus: the dbus connection
            :param index: the GATT service index (handler)
            :param uuid: the service UUID
            :param primary: true or false, depending if primary or secondary service
        """
        self.callback_func = write_callback_func
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def callback(self, result_dic):
        self.callback_func(result_dic)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.get_characteristic_paths(),
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        """
        Get all properties from the bluez properies set;
        :param interface:
        :return:
        """
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties[GATT_SERVICE_IFACE]

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        logger.debug('GetManagedObjects')

        response[self.get_path()] = self.get_properties()
        chrcs = self.get_characteristics()
        for chrc in chrcs:
            response[chrc.get_path()] = chrc.get_properties()
            descs = chrc.get_descriptors()
            for desc in descs:
                response[desc.get_path()] = desc.get_properties()

        return response


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        """
            The constructor of a characteristics which is part of a Service
            :param bus: the dbus connection
            :param index: the characteristics index
            :param uuid: the unique id of this characteristics
            :param flags: possible values: read | write | notify | extended-properties | reliable-write | writable-auxiliaries
            :param service: the service reference (pointer)
        """
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_service(self):
        return self.service

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(
                    self.get_descriptor_paths(),
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, out_signature='ay')
    def ReadValue(self):
        logger.warn('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='ay')
    def WriteValue(self, value):
        # print('Default WriteValue called, returning error')
        # raise NotSupportedException()
        self.get_service().callback({self.__class__.__name__:value})

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        logger.warn('Default StartNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        logger.warn('Default StopNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        """
            Fires a property changed signal to the dbus
            :param interface: the GATT Characteristics Interface (org.bluez.GattCharacteristic1)
            :param changed: the dict object structure representing the signal data
            :param invalidated:
        """
        pass


class NotificationAbleCharacteristic(Characteristic):
    def __init__(self, bus, index, service, flags=['read', 'notify']):
        Characteristic.__init__(
            self, bus, index,
            self.return_uuid(),
            flags,
            service)
        self.notifying = False

    def return_uuid(self):
        logger.warn('Default return UUID is called. Please override this method.')
        raise NotSupportedException()

    def get_values(self):
        logger.warn('Default get_values is called. Please override this method.')
        raise NotSupportedException()

    def ReadValue(self):
        logger.debug('read value in read and notification characteristic')
        return self.get_values()

    def notify_cb(self):
        logger.debug('notifying in read and notification characteristic')
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': self.get_values()}, [])
        return self.notifying

    def StartNotify(self):
        if self.notifying:
            # Already notifying, nothing to do
            return

        self.notifying = True
        gobject.timeout_add(1000, self.notify_cb)

    def StopNotify(self):
        if not self.notifying:
            # Not notifying, nothing to do
            return
        self.notifying = False

class Descriptor(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE: {
                'Characteristic': self.chrc.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE, out_signature='ay')
    def ReadValue(self):
        logger.warn('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='ay')
    def WriteValue(self, value):
        logger.warn('Default WriteValue called, returning error')
        raise NotSupportedException()


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    The Characteristic User Description descriptor provides a textual user description for a characteristic value.
    """
    CUD_UUID = '2901'

    def __init__(self, bus, index, characteristic, description):
        """
            :param bus:
            :param index:
            :param characteristic:
            :param description: the User Description value

        """
        self.writable = 'writable-auxiliaries' in characteristic.flags
        self.value = array.array('B', description)
        self.value = self.value.tolist()
        Descriptor.__init__(
            self, bus, index,
            self.CUD_UUID,
            ['read', 'write'],
            characteristic)

    def ReadValue(self):
        return self.value

    def WriteValue(self, value):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


class Advertisement(dbus.service.Object):
    """
    Bluetooth Low Energy Advertisement
    """
    PATH_BASE = '/org/bluez/boxee/advertisement'

    def __init__(self, bus, index, advertising_type):
        """
        Initializes the GATT advertisement
        :param bus: the dbus connection reference
        :param index: the index of this advertisement
        :param advertising_type: possible values are: peripheral
        :return:
        """
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.include_tx_power = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qay')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='say')
        if self.include_tx_power is not None:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dict()
        self.manufacturer_data[manuf_code] = data

    def add_service_data(self, uuid, data):
        """

        :param uuid: the unique ID of the service
        :param data:
        :return:
        """
        if not self.service_data:
            self.service_data = dict()
        self.service_data[uuid] = data

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        logger.debug('GetAll :: returning props')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        logger.debug('%s: Released!', self.path)
