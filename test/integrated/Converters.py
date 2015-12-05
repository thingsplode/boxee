import logging
import sys
import binascii
import struct
import dbus
import traceback

__author__ = 'tamas'

logger = logging.getLogger(__name__)


def main(argv):
    try:
        FORMAT = '%(levelname)s - %(module)s.%(funcName)s: %(message)s'
        logging.basicConfig(format=FORMAT)
        print ('===== Hexlified ==== \n')
        s = 'some barcode'
        print ('string length %s' % len(s))
        byte_array = binascii.hexlify(s)
        print ('hexlified byte array [%s]' % byte_array)
        print ('len byte array [%s]' % len(byte_array))
        print ('ascii decoded byte array> %s' % byte_array.decode('ascii'))
        print ('ascii decoded byte array> %s' % byte_array.decode('utf-8'))

        print ('===== ELEM BY ELEM ==== \n')
        #######################################
        # s = 'some other barcode'
        print ('string length %s' % len(s))
        # byte_array = [elem.encode("hex") for elem in s]
        byte_array = [dbus.Byte(elem) for elem in s]
        print ('elem by elem encoded byte array %s' % byte_array)
        print ('len byte array [%s]' % len(byte_array))
        print ('ascii decoded byte array> %s' % "".join(map(chr, byte_array)))

        print ('===== STRUCT ==== \n')
        # s = 'yet another barcode'
        print ('string length %s' % len(s))
        fmt = '!%ss' % len(s)
        structure = struct.pack(fmt, s)
        print('packed structure [%s]' % structure)
        an_array = [dbus.Byte(elem) for elem in structure]
        print ('array of packed strcuture %s' % an_array)
        print ('len structure [%s]' % len(structure))
        print ('len of array [%s]' % len(an_array))
        print ('ascii decoded byte array> %s' % structure.decode('ascii'))
        print ('unpacked structure> %s' % struct.unpack(fmt, structure))
        msg = bytearray()
        print ('unpacked array> %s' % struct.unpack('!12s', "".join([chr(elem) for elem in an_array])))

    except BaseException as e:
        print e
        # traceback.print_exc()
    finally:
        pass


if __name__ == '__main__':
    main(sys.argv[1:])  # chop off the sys.argv[0] which is the name of the script
