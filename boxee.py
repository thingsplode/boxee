#!/usr/bin/python

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from boxee import stypes
import boxee.core
import boxee.io_service
import gobject

mainloop = None


class BoxeeServer():
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()

        self.adapter = self.find_adapter(self.bus)
        if not self.adapter:
            print('GattManager1 interface not found')
            return

        self.gatt_manager = dbus.Interface(
            self.bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, self.adapter),
            boxee.core.GATT_MGR_IFACE)

        self.advertising_manager = dbus.Interface(
            self.bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, self.adapter),
            boxee.core.LE_ADVERTISING_MANAGER_IFACE)

        self.hci0_props_manager = dbus.Interface(
            self.bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, self.adapter),
            boxee.core.DBUS_PROP_IFACE)

        self.services = []

    def start_server(self):
        print('Starting boxee server\n')
        global mainloop
        mainloop = gobject.MainLoop()

        print('Adapter properties');
        for key, value in self.hci0_props_manager.GetAll('org.bluez.Adapter1').iteritems():
            if isinstance(value, dbus.Array):
                print (key)
                for v in value:
                    print('\t%s' % v)
            elif isinstance(value, dbus.Dictionary):
                print(key)
                for k, v in value.iteritems():
                    print('\t%s=%s' % (k,v))
            else:
                print('%s = %s' % (key, value))
        print '\n'

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

        self.services.append(boxee.io_service.AutomationIOService(self.bus, 0))

        for srv in self.services:
            self.gatt_manager.RegisterService(srv.get_path(), {},
                                              reply_handler=self.register_service_callback,
                                              error_handler=self.register_service_error_callback)

        mainloop.run()

    def stop_server(self):
        print('Gracefully exiting boxee...')
        for srv in self.services:
            print('Unregistering service: %s' % srv.get_path())
            self.gatt_manager.UnregisterService(srv.get_path())

    def register_service_callback(self):
        print('GATT service registered')

    def register_service_error_callback(self, error):
        """
        Callback method called by DBus, once the original method call was executed
            :param error: a DBusException
        """
        print('Exiting. Failed to register service: ' + str(error))
        mainloop.quit()

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

    def find_adapter(self, bus):
        """
        Returns the first bluetooth adapter which has a org.bluez.GattManager1 interface on it
            :param bus: the dbus handler instance
            :return: the bluetooth adapter
        """
        remote_om = dbus.Interface(bus.get_object(boxee.core.BLUEZ_SERVICE_NAME, '/'),
                                   boxee.core.DBUS_OM_IFACE)
        objects = remote_om.GetManagedObjects()

        for o, props in objects.iteritems():
            if props.has_key(boxee.core.GATT_MGR_IFACE):
                return o

        return None


def main():
    boxee = BoxeeServer()
    try:
        boxee.start_server()
    finally:
        boxee.stop_server()


if __name__ == '__main__':
    main()
