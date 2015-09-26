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

mainloop = None


class BoxeeServer():
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()

        self.gatt_adapter = self.find_adapter_for_interface(self.bus, boxee.core.GATT_MGR_IFACE)
        self.advertising_adapter = self.find_adapter_for_interface(self.bus, boxee.core.LE_ADVERTISING_MANAGER_IFACE)

        if self.gatt_adapter != self.advertising_adapter:
            print('Warning: the gatt adapter and the advertising adapters are not the same. Exiting application...')
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
        print('Starting boxee server\n')
        global mainloop
        mainloop = gobject.MainLoop()

        if self.hci0_props_manager.Get(boxee.core.ADAPTER_IFACE, 'Powered') == dbus.Boolean(0):
            print('Powering on the adapter [%s]' % self.hci0_props_manager.Get(boxee.core.ADAPTER_IFACE, 'Name'))
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
        print('Gracefully exiting boxee...')
        for srv in self.services:
            print('Unregistering service: %s' % srv.get_path())
            self.gatt_manager.UnregisterService(srv.get_path())

    def service_registration_cb(self):
        print('GATT service registered')

    def service_registration_err_cb(self, error):
        """
        Callback method called by DBus, once the original method call was executed
            :param error: a DBusException
        """
        print('Exiting. Failed to register service: ' + str(error))
        mainloop.quit()

    def adv_registration_cb(self):
        print 'Advertisement registered'

    def adv_registration_err_cb(self, error):
        print 'Failed to register advertisement: ' + str(error)

    # def register_catchall_handler(*args, **kwargs):
    #     if kwargs is not None:
    #         for key, value in kwargs.iteritems():
    #             print("%s == %s" % (key, value))
    #     for arg in args:
    #         print("ARG>        " + str(arg))

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

        print('Adapter for interface [%s] not found. Exiting application...' % iface_name)
        sys.exit(-1)


def main():
    boxee = BoxeeServer()
    try:
        boxee.start_server()
    finally:
        boxee.stop_server()


if __name__ == '__main__':
    main()
