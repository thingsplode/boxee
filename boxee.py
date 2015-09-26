#!/usr/bin/python

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from boxee import stypes
import boxee.core
import boxee.io_service
from boxee.io_service import AutomationIOService
import boxee.advertisement
from boxee.advertisement import BoxAdvertisement
import gobject
import sys
import boxee.utils
import logging
import logging.handlers


mainloop = None
logger = logging.getLogger()

class BoxeeServer():
    def __init__(self):
        syslog_handler = logging.handlers.SysLogHandler('/dev/log')
        formatter = logging.Formatter('%(levelname)s - %(module)s.%(funcName)s: %(message)s')
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)
        logger.setLevel(logging.DEBUG)

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

        self.services = []

    def start_server(self):
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
        self.services.append(AutomationIOService(self.bus, 0))

        # Initialize bluetooth advertisement
        advertisement = BoxAdvertisement(self.bus, '0')

        for srv in self.services:
            self.gatt_manager.RegisterService(srv.get_path(), {},
                                              reply_handler=self.service_registration_cb,
                                              error_handler=self.service_registration_err_cb)
            advertisement.add_service_uuid(srv.get_properties()[boxee.core.GATT_SERVICE_IFACE]['UUID'])


        self.advertising_manager.RegisterAdvertisement(advertisement.get_path(), {},
                                                       reply_handler=self.adv_registration_cb,
                                                       error_handler=self.adv_registration_err_cb)

        mainloop.run()

    def stop_server(self):
        exit_msg = 'Gracefully exiting boxee...'
        print(exit_msg)
        logger.info(exit_msg)
        for srv in self.services:
            print('Unregistering service: %s' % srv.get_path())
            self.gatt_manager.UnregisterService(srv.get_path())

    def service_registration_cb(self):
        logger.debug('A GATT service got registered')

    def service_registration_err_cb(self, error):
        """
        Callback method called by DBus, once the original method call was executed
            :param error: a DBusException
        """
        err_msg = 'Exiting. Failed to register service: ' + str(error)
        print(err_msg)
        logger.error(err_msg,error)
        mainloop.quit()

    def adv_registration_cb(self):
        logger.debug('Advertisement registered')

    def adv_registration_err_cb(self, error):
        err_msg = 'Failed to register advertisement: ' + str(error)
        print(err_msg)
        logger.error(err_msg,error)

    def signal_receiver_callback(self, *args, **kwargs):
        if kwargs is not None:
            print '\n=== kwargs ==='
            for key, value in kwargs.iteritems():
                print("%s == %s" % (key, value))
            print '==============\n'

        signal = {stypes.KEY_SIG_TYPE: stypes.SIG_TYPE_UNHANDLED}
        if args[0].startswith('org.bluez.Device1'):
            signal[stypes.KEY_SIG_TYPE] = stypes.SIG_TYPE_BLUE_DEVICE
            if isinstance(args[1], dbus.Dictionary):
                signal[stypes.KEY_SIG_VALUE_TYPE] = 'dictionary'
                signal[stypes.KEY_SIG_VALUE] = args[1]

        print("Signal")

        for key, value in signal.iteritems():
            print("%s == %s" % (key, value))

        # Signal processing
        if signal[stypes.KEY_SIG_TYPE] is stypes.SIG_TYPE_BLUE_DEVICE and stypes.KEY_SIG_VALUE in signal:
            if stypes.TEST_CONNECTED in signal[stypes.KEY_SIG_VALUE]:
                if not signal[stypes.KEY_SIG_VALUE][stypes.TEST_CONNECTED]:
                    print "Need to reconnect"
                else:
                    print 'no need to reconnect'

    def find_adapter_for_interface(self, bus, iface_name):
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


def main():
    boxee = BoxeeServer()
    try:
        boxee.start_server()
    finally:
        boxee.stop_server()


if __name__ == '__main__':
    main()
