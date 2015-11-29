#!/usr/bin/python

import dbus, dbus.mainloop.glib, dbus.service, gobject
from dbus.exceptions import DBusException
from boxee.exceptions import DoesNotExistException, FailedException, InvalidArgsException, InvalidValueLengthException, \
    NotPermittedException, NotSupportedException
import sys, os, getopt, logging, logging.handlers
from boxee import stypes
import boxee.core, boxee.io_service, boxee.advertisement, boxee.utils, boxee.gpio
from boxee.gpio import GpioConnector
from boxee.io_service import AutomationIOService
from boxee.system_service import SystemService
from boxee.advertisement import BoxAdvertisement

mainloop = None
logger = logging.getLogger(__name__)


class BoxeeServer:
    """
     The main server controlling the IO breakouts of the raspberry PI over bluetooth low energy connections (GATT)
    """

    def __init__(self, current_folder, log_level):

        self.setup_logging(current_folder, log_level)
        # GPIO configuration
        out_chs = [17, 18]
        self.gpio = GpioConnector(out_channels=out_chs)

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()

        self.gatt_adapter = self.find_adapter_for_interface(self.bus, boxee.core.GATT_MGR_IFACE)
        self.advertising_adapter = self.find_adapter_for_interface(self.bus, boxee.core.LE_ADVERTISING_MANAGER_IFACE)
        if self.gatt_adapter != self.advertising_adapter:
            err = ' the gatt adapter and the advertising adapters are not the same. Exiting application...'
            print(err)
            logger.error(err)
            sys.exit(-1)

        self.gatt_manager = dbus.Interface(
            self.bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, self.gatt_adapter),
            boxee.core.GATT_MGR_IFACE)

        self.advertising_manager = dbus.Interface(
            self.bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, self.gatt_adapter),
            boxee.core.LE_ADVERTISING_MANAGER_IFACE)

        self.hci0_props_manager = dbus.Interface(
            self.bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, self.gatt_adapter),
            boxee.core.DBUS_PROP_IFACE)

        # GATT service storage array
        self.services = []

        # Initialize bluetooth advertisement
        self.advertisement = BoxAdvertisement(self.bus, '0')

    def start_server(self):
        """
        Lifecycle method: is the first to be called in order to start the server;
        """
        start_msg = 'Starting boxee server'
        print(start_msg)
        logger.info(start_msg)

        global mainloop
        mainloop = gobject.MainLoop()

        if self.hci0_props_manager.Get(boxee.core.ADAPTER_IFACE, 'Powered') == dbus.Boolean(0):
            msg = 'Powering on the adapter [%s]' % self.hci0_props_manager.Get(boxee.core.ADAPTER_IFACE, 'Name')
            print(msg)
            logger.info(msg)
            self.hci0_props_manager.Set(boxee.core.ADAPTER_IFACE, 'Powered', dbus.Boolean(1))

        print('Adapter properties')
        print(boxee.utils.describe_dbus_dict(self.hci0_props_manager.GetAll(boxee.core.ADAPTER_IFACE).iteritems()))

        # print self.hci_props_manager.GetAll('org.bluez.GattManager1')

        self.bus.add_signal_receiver(self.signal_receiver_callback,
                                     signal_name=None,
                                     dbus_interface=None,
                                     bus_name=None,
                                     path=None,
                                     sender_keyword='sender',
                                     destination_keyword='destination',
                                     interface_keyword='interface',
                                     member_keyword='member',
                                     path_keyword='path')
        # Setup services
        self.services.append(AutomationIOService(self.bus, 0, write_callback_func=self.ble_service_write_cb))
        self.services.append(SystemService(self.bus, 1, write_callback_func=self.ble_service_write_cb))

        for srv in self.services:
            logger.info('Registering BLE service [%s]' % srv.get_path())
            self.gatt_manager.RegisterService(srv.get_path(), {},
                                              reply_handler=self.service_registration_cb,
                                              error_handler=self.service_registration_err_cb)

            # Add service info to the advertisement -> if many service it will result in
            # Failed to register advertisement: org.bluez.Error.InvalidLength: Advertising data too long.
            # self.advertisement.add_service_uuid(srv.get_properties()[boxee.core.GATT_SERVICE_IFACE]['UUID'])

        logger.info('Registering BLE advertisement [%s]' % self.advertisement.get_path())
        self.advertising_manager.RegisterAdvertisement(self.advertisement.get_path(), {},
                                                       reply_handler=self.adv_registration_cb,
                                                       error_handler=self.adv_registration_err_cb)

        mainloop.run()

    def stop_server(self):
        """
        Lifecycle method: the last to be called upon exit
        """
        exit_msg = 'Gracefully exiting boxee...'
        print(exit_msg)
        logger.info(exit_msg)

        logger.debug('Cleanup on GPIO')
        self.gpio.cleanup()

        logger.info('Unregistering advertisement...')
        try:
            logger.debug('Unregistering service adverstisement with path [%s]', self.advertisement.get_path())
            self.advertising_manager.UnregisterAdvertisement(self.advertisement.get_path())
            self.advertisement.Release()
        except (DBusException, DoesNotExistException, InvalidArgsException) as e:
            logger.error('Could not cleanly unregister advertisement: %s' % str(e))
        except BaseException as e:
            logger.error('Uncategorized exception caught while unregistering advertisment: %s' % str(e))
        for srv in self.services:
            logger.info('Unregistering service: %s' % srv.get_path())
            self.gatt_manager.UnregisterService(srv.get_path())

        logger.info('Boxee server is terminated...')

    def service_registration_cb(self):
        """
        Callback method called by DBus, once the original call was succesfully executed
        :return:
        """
        logger.debug('A GATT service got registered')

    def service_registration_err_cb(self, error):
        """
        Callback method called by DBus, once the original method call was executed with an error
            :param error: a DBusException
        """
        err_msg = 'Exiting. Failed to register service: ' + str(error)
        print(err_msg)
        logger.error(err_msg)
        mainloop.quit()

    @staticmethod
    def adv_registration_cb():
        logger.debug('Advertisement registered')

    @staticmethod
    def adv_registration_err_cb(error):
        err_msg = 'Failed to register advertisement: ' + str(error)
        print(err_msg)
        logger.error(err_msg)

    def ble_service_write_cb(self, signal_dictionary):
        """
        :param signal_dictionary: example: {'AutIODigitalChrc': dbus.Array([dbus.Byte(0), dbus.Byte(255)], signature=dbus.Signature('y'))}
        :return:
        """
        logger.debug('BLE service write callback with signal dictionary: %s',
                     signal_dictionary if signal_dictionary is not None else 'Undefined')
        try:
            if 'AutIODigitalChrc' in signal_dictionary:
                value_array = signal_dictionary['AutIODigitalChrc']
                if isinstance(value_array, dbus.Array):
                    self.gpio.handle_out_channel_control_array(value_array)
        except BaseException as e:
            print('Unexpected error: ', sys.exc_info()[0], str(e))
            logger.error('Error while handling bluetooth low energy callback')

    @staticmethod
    def signal_receiver_callback(*args, **kwargs):
        """
        Callback method registered for signals to be received on DBus
        :param args:
        :param kwargs:
        :return:
        """

        # Dictionary of arguments.
        # Example:
        #       member == PropertiesChanged
        #       path == /org/bluez/boxee/service0/char0
        #       destination == None
        #       interface == org.freedesktop.DBus.Properties
        #       sender == :1.8
        if logger.isEnabledFor(logging.DEBUG):
            # args_string = ''
            kwarg_string = ''
            # if args is not None:
            if kwargs is not None:
                for key, value in kwargs.iteritems():
                    kwarg_string += '{[%s] == [%s]}' % (key, value)
            # args_string = ''.join(args)
            logger.debug('Signal received: args: [%s] | Dictionary args: %s' % (args, kwarg_string))

        signal = {stypes.KEY_SIG_TYPE: stypes.SIG_TYPE_UNHANDLED}

        if len(args) > 0 and args[0].startswith('org.bluez.Device1'):
            signal[stypes.KEY_SIG_TYPE] = stypes.SIG_TYPE_BLUE_DEVICE
            if isinstance(args[1], dbus.Dictionary):
                signal[stypes.KEY_SIG_VALUE_TYPE] = 'dictionary'
                signal[stypes.KEY_SIG_VALUE] = args[1]

        logger.debug("Signal argument list:")
        # example value: signal_type == unhandled
        for key, value in signal.iteritems():
            logger.debug("\t %s == %s" % (key, value))

            # Signal types:
            # Signal argument list:
            #   signal_type == blue_device
            #   value_type == dictionary
            #   value == dbus.Dictionary({dbus.String(u'Connected'): dbus.Boolean(True, variant_level=1)}, signature=dbus.Signature('sv'))
        # -----------

        # Signal processing
        if signal[stypes.KEY_SIG_TYPE] is stypes.SIG_TYPE_BLUE_DEVICE and stypes.KEY_SIG_VALUE in signal:
            if stypes.TEST_CONNECTED in signal[stypes.KEY_SIG_VALUE]:
                if not signal[stypes.KEY_SIG_VALUE][stypes.TEST_CONNECTED]:
                    logger.info('Need to reconnect')
                else:
                    logger.info('no need to reconnect')

    @staticmethod
    def find_adapter_for_interface(bus, iface_name):
        """
        Returns the first bluetooth adapter which has a org.bluez.GattManager1 interface on it
            :param bus: the dbus handler instance
            :return: the bluetooth adapter
        """
        remote_om = dbus.Interface(bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, '/'),
                                   boxee.core.DBUS_OM_IFACE)
        objects = remote_om.GetManagedObjects()

        for o, props in objects.iteritems():
            if props.has_key(iface_name):
                return o

        err_msg = 'Adapter for interface [%s] not found. Exiting application...' % iface_name
        print(err_msg)
        logger.error(err_msg)
        sys.exit(-1)

    @staticmethod
    def setup_logging(current_folder, log_level):
        """
        Configures the logging subsystem. By default everything goes to the syslog.
        :param current_folder: the current program folder. where the debug log file shall be placed;
        :param log_level: the desired log level to be set for the root logger (eg. logging.DEBUG)
        :return:
        """
        logging.root.setLevel(log_level)

        formatter = logging.Formatter('%(levelname)s - %(module)s.%(funcName)s: %(message)s')
        syslog_handler = logging.handlers.SysLogHandler('/dev/log')
        syslog_handler.setFormatter(formatter)
        syslog_handler.setLevel(log_level)
        logging.root.addHandler(syslog_handler)

        # if log_level == 10:
        #     logfile = current_folder + '/debug.log'
        #     file_handler = logging.handlers.RotatingFileHandler(logfile)
        #     file_handler.setFormatter(formatter)
        #     file_handler.setLevel(log_level)
        #     logging.root.addHandler(file_handler)
        #     logger.info('Logging in: %s', logfile)

        logger.debug('Log level enabled for DEBUG: [%s]' % logger.isEnabledFor(logging.DEBUG))
        logger.debug('Log level enabled for INFO: [%s]' % logger.isEnabledFor(logging.INFO))
        logger.debug('Log level enabled for ERROR: [%s]' % logger.isEnabledFor(logging.ERROR))
        logger.debug('Log level enabled for WARNING: [%s]' % logger.isEnabledFor(logging.WARNING))
        logger.debug('Syslog handler level: %s', syslog_handler.level)
        logger.debug('Root logger level %s', logging.root.level)


def usage():
    print ('Usage:')
    print ('\t -h --help \t list all command line options')
    print ('\t -d --debug \t switches on the debug mode (more details in the syslog)')


def main(argv):
    boxee_server = None
    log_level = logging.INFO
    try:
        current_folder = os.path.dirname(os.path.realpath(sys.argv[0]))
        # more details on getopts: http://www.diveintopython.net/scripts_and_streams/command_line_arguments.html
        opts, args = getopt.getopt(argv, "hd", ["help", "debug"])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt == '-d':
                print ('\t :: activating debug mode')
                log_level = logging.DEBUG
        boxee_server = BoxeeServer(current_folder, log_level)
        boxee_server.start_server()
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    except BaseException as e:
        print('Base exception received: %s' % str(e))
    finally:
        if boxee_server is not None:
            boxee_server.stop_server()


if __name__ == '__main__':
    main(sys.argv[1:])  # chop off the sys.argv[0] which is the name of the script
