#!/usr/bin/python

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import boxee.core
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
            boxee.core.LEADV_MGR_IFACE)

        self.services = []

    def start_server(self):
        global mainloop
        mainloop = gobject.MainLoop()

        self.bus.add_signal_receiver(self.register_catchall_handler,
                                     signal_name=None,
                                     dbus_interface=None,
                                     bus_name=None,
                                     path=None,
                                     sender_keyword='sender',
                                     destination_keyword='destination',
                                     interface_keyword='interface',
                                     member_keyword='member',
                                     path_keyword='path')

        self.services.append(automation_service=boxee.io_service.AutomationIOService(self.bus, 0))

        for srv in self.services:
            self.gatt_manager.RegisterService(srv.get_path(), {},
                                              reply_handler=self.register_service_callback,
                                              error_handler=self.register_service_error_callback)

        # self.gatt_manager.RegisterService(automation_service.get_path(), {},
        #                                   reply_handler=self.register_service_callback,
        #                                   error_handler=self.register_service_error_callback)
        mainloop.run()

    def stop_server(self):
        print('Gracefully exiting boxee...')

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

    def register_signal_callback(*args, **kwargs):
        print 'callback'

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
