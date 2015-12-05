from binascii import unhexlify, hexlify
from core import Service, Characteristic, NotificationAbleCharacteristic, CharacteristicUserDescriptionDescriptor
import psutil
import boxee, logging, struct, gobject, dbus, dbus.service
from exceptions import NotSupportedException

__author__ = 'tamas'

logger = logging.getLogger(__name__)


class SystemService(Service):
    SYS_SRV_UUID = '5d2ade4e-5f83-4c49-b5c9-8d9e2f9db41a'

    def __init__(self, bus, index, write_callback_func):
        """
            :param bus: the dbus connection
            :param index: the index of the service
        """
        Service.__init__(self, write_callback_func, bus, index, self.SYS_SRV_UUID, True)
        self.add_characteristic(MemoryPercentageChrc(bus, 0, self))
        self.add_characteristic(CpuPercentageChrc(bus, 1, self))
        # self.add_characteristic(MemoryDataChrc(bus, 0, self))
        # self.add_characteristic(CpuDataChrc(bus, 2, self))
        # self.add_characteristic(DiskDataChrc(bus, 4, self))


class MemoryPercentageChrc(NotificationAbleCharacteristic):
    def __init__(self, bus, index, service):
        NotificationAbleCharacteristic.__init__(self, bus, index, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Memory Percentage"))

    def return_uuid(self):
        return 'b03eef61-bce5-4849-aaa3-9cc5f652cf03'

    def get_values(self):
        logger.debug('getting values in [%s]', __name__)
        values = []
        mem = psutil.virtual_memory()
        mem_percent_struct = struct.pack('!f', mem.percent)
        append_bytearray_to_array(values, mem_percent_struct)
        logger.debug('memory percent [%s], hex bytes [%s], structure byte length: [%s]', mem.percent,
                     hexlify(mem_percent_struct), len(mem_percent_struct))
        return values


class MemoryDataChrc(NotificationAbleCharacteristic):
    """
    TOTAL, AVAIL, PERCENT, USED, FREE
    Handles the virtual memory information
    # mem = psutil.virtual_memory()
    # print (mem.total/1024/1024) results in 973 M
    # svmem(total=1020764160L, available=957878272L, percent=6.2, used=273211392L, free=747552768L, active=94724096, inactive=148664320, buffers=24080384L, cached=186245120)
    """

    def __init__(self, bus, index, service):
        NotificationAbleCharacteristic.__init__(self, bus, index, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Memory Data"))

    def return_uuid(self):
        return '84c2a2ea-a8ea-45e0-8c29-a3134b0e973f'

    def get_values(self):
        values = []
        mem = psutil.virtual_memory()
        # s = struct.Struct('I 2s f')
        values.append(long_to_bytes(mem.total))
        values.append(long_to_bytes(mem.available))
        values.append(long_to_bytes(mem.used))
        values.append(dbus.ByteArray(mem.free))
        return values


class CpuPercentageChrc(NotificationAbleCharacteristic):
    """
        core 1: byte length
        core 1: percentage float (4 bytes)
        ...
        core x: byte length
        core x: percentage float (4 bytes)
    """

    def __init__(self, bus, index, service):
        NotificationAbleCharacteristic.__init__(self, bus, index, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "CPU Percentage"))

    def return_uuid(self):
        return 'b0cf5f03-e079-4c77-8e1b-7763e734e5f4'

    def get_values(self):
        logger.debug('getting values in [%s]', type(self).__name__)
        values = []
        try:
            for cpu_percent in psutil.cpu_percent(1, True):
                cpu_percent_struct = struct.pack('!f', cpu_percent)
                cpu_percent_struct_byte_length = len(cpu_percent_struct)
                values.append(dbus.Byte(cpu_percent_struct_byte_length))
                append_bytearray_to_array(values, cpu_percent_struct)
                logger.debug('cpu percent [%s], hex bytes [%s], structure byte length: [%s]', cpu_percent,
                             hexlify(cpu_percent_struct), cpu_percent_struct_byte_length)
        except BaseException as e:
            logger.error('General error in [%s]: %s', type(self).__name__, str(e))
        finally:
            logger.debug('returning byte array of size: [%s] and raw value: [%s]', len(values), repr(values))
            return values


class CpuDataChrc(NotificationAbleCharacteristic):
    """
    Returns the CPU count and load:
        first byte: cpu count
        following array of floats: cpu load
    # psutil.cpu_percent(3, True)
    # [2.4, 0.0, 0.0, 0.0]
    # psutil.cpu_count()
    # 4
    """

    def __init__(self, bus, index, service):
        NotificationAbleCharacteristic.__init__(self, bus, index, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "CPU Data"))

    def return_uuid(self):
        return '6ca3211a-0f51-440a-86fb-17a438ae33a5'

    def get_values(self):
        values = [dbus.Byte(psutil.cpu_count), dbus.Array(psutil.cpu_percent(1, True))]
        return values


class DiskDataChrc(NotificationAbleCharacteristic):
    """
    1st byte: # of partitions
    2nd byte: mountpoint length
    3...x byte: mount point as ASCII text
    x+1 double: percent

    # disk_partitions = psutil.disk_partitions()
    # print disk_partitions
    # [sdiskpart(device='/dev/root', mountpoint='/', fstype='ext4', opts='rw,noatime,data=ordered'), sdiskpart(device='/dev/mmcblk0p1', mountpoint='/boot', fstype='vfat', opts='rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=ascii,shortname=mixed,errors=remount-ro')]
    # print disk_partitions[1][0]
    # /dev/mmcblk0p1
    # disk_usage = psutil.disk_usage(disk_partitions[0][1])
    # print disk_usage
    # sdiskusage(total=15101038592L, used=7100243968L, free=7335792640L, percent=47.0)
    # print disk_usage[0]
    # 15101038592

    """

    def __init__(self, bus, index, service):
        NotificationAbleCharacteristic.__init__(self, bus, index, service)
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "Disk Characteristic"))

    def return_uuid(self):
        return 'fe10746c-880e-4d4d-8b40-2f2b84596ba9'

    def get_values(self):
        values = []
        disk_partitions = psutil.disk_partitions()
        values.append(dbus.Byte(len(disk_partitions)))
        if len(disk_partitions) > 0:
            for part in disk_partitions:
                mount_point = part[1]
                mount_point_array = [char.encode('hex') for char in mount_point]
                values.append(dbus.Byte(len(mount_point_array)))
                values.append(dbus.Array(mount_point_array))
                values.append(dbus.Double(psutil.disk_usage(mount_point)[3]))
        return values


def append_bytearray_to_array(input_array, appendable_bytestream):
    if input_array is None:
        input_array = []

    if appendable_bytestream is not None:
        for this_byte in appendable_bytestream:
            input_array.append(dbus.Byte(this_byte))
    return input_array


def long_to_bytes(val, endianness='big'):
    """
    Use :ref:`string formatting` and :func:`~binascii.unhexlify` to
    convert ``val``, a :func:`long`, to a byte :func:`str`.

    :param long val: The value to pack

    :param str endianness: The endianness of the result. ``'big'`` for
      big-endian, ``'little'`` for little-endian.

    If you want byte- and word-ordering to differ, you're on your own.

    Using :ref:`string formatting` lets us use Python's C innards.
    """

    # one (1) hex digit per four (4) bits
    width = val.bit_length()

    # unhexlify wants an even multiple of eight (8) bits, but we don't
    # want more digits than we need (hence the ternary-ish 'or')
    width += 8 - ((width % 8) or 8)

    # format width specifier: four (4) bits per hex digit
    fmt = '%%0%dx' % (width // 4)

    # prepend zero (0) to the width, to zero-pad the output
    s = unhexlify(fmt % val)

    if endianness == 'little':
        # see http://stackoverflow.com/a/931095/309233
        s = s[::-1]

    return s
