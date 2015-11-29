import logging
import gobject
from random import randint
from exceptions import InvalidValueLengthException, FailedException
import boxee
from core import Service, Characteristic, CharacteristicUserDescriptionDescriptor

__author__ = 'tamas'
logger = logging.getLogger(__name__)


class AutomationIOService(Service):
    """
    GATT SIG Automation IO Service 0x1815
    The Automation IO service is used to expose the analog inputs/outputs and digital input/outputs of a generic IO module (IOM).
    This service has no dependencies on other GATT-based services.
    """
    AUTIO_UUID = '1815'

    def __init__(self, bus, index, write_callback_func):
        """
            :param bus: the dbus connection
            :param index: the index of the service
        """
        Service.__init__(self, write_callback_func, bus, index, self.AUTIO_UUID, True)
        self.add_characteristic(AutIODigitalChrc(bus, 0, self))
        self.energy_expended = 0


class AutIODigitalChrc(Characteristic):
    AUT_IO_DIG_CHRC_UUID = '2A56'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index,
            self.AUT_IO_DIG_CHRC_UUID,
            ['write', 'notify', 'reliable-write'],
            service)
        self.notifying = False
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Automation Digital IO"))
        self.hr_ee_count = 0

    def hr_msrmt_cb(self):
        # psutil.swap_memory()
        # sswap(total=2061496320L, used=0L, free=2061496320L, percent=0.0, sin=0, sout=0)

        value = []
        value.append(dbus.Byte(0x06))
        value.append(dbus.Byte(randint(90, 130)))

        if self.hr_ee_count % 10 == 0:
            value[0] = dbus.Byte(value[0] | 0x08)
            value.append(dbus.Byte(self.service.energy_expended & 0xff))
            value.append(dbus.Byte((self.service.energy_expended >> 8) & 0xff))

        self.service.energy_expended = \
            min(0xffff, self.service.energy_expended + 1)
        self.hr_ee_count += 1

        print('Updating value: ' + repr(value))

        self.PropertiesChanged(boxee.core.GATT_CHRC_IFACE, {'Value': value}, [])

        return self.notifying

    def _update_hr_msrmt_simulation(self):
        logger.debug('Update HR Measurement Simulation')

        if not self.notifying:
            return

        gobject.timeout_add(1000, self.hr_msrmt_cb)

    def StartNotify(self):
        if self.notifying:
            logger.debug('Already notifying, nothing to do')
            return

        self.notifying = True
        self._update_hr_msrmt_simulation()

    def StopNotify(self):
        if not self.notifying:
            logger.debug('Not notifying, nothing to do')
            return

        self.notifying = False
        self._update_hr_msrmt_simulation()
