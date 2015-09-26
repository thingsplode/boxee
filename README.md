# boxee
**Work in Progress**

Boxee is a Bluetooth Low Energy automation protoype for the Raspberyy PI. It relies on Dbus and Bluez and its target to expose GPIO control over the BLE, so that one can control device over the phone.

# Monitoring

The best done via dbus-monitor

cat /etc/dbus-1/system-local.conf
```bash
<!DOCTYPE busconfig PUBLIC
"-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
"http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
    <policy user="root">
        <allow eavesdrop="true"/>
        <allow eavesdrop="true" send_destination="*"/>
    </policy>
</busconfig>
```
