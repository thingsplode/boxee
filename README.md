# boxee
**Work in Progress**

Boxee is a Bluetooth Low Energy automation protoype for the Raspberyy PI. It relies on Dbus and Bluez and its target to expose GPIO control over the BLE, so that one can control device over the phone.

## Current Status

Creates a Bluetooth LE advertisement and publishes one service, which enables to set GPIO 17 and 18 to HIGH and LOW on a Raspberry PI, by writing a 2 byte value array:
* 0x00 0x00 => PIN 17 and 18 is LOW
* 0x00 0xFF => PIN 17 is LOW, PIN 18 is HIGH
* 0xFF 0xFF => PIN 17 and 18 are HIGH

### Other features
* The logging is made in syslog, some text is still printed on the standard ouput

## Current Limitations
* only GPIO 17 and 18 are initialized and can be controlled, however this limitation can easily be overcome by adding more channels in the BoxeeServer constructor (out_chs = [17, 18, xx, xx])
* sometimes the advertisement is restarted only after 15 seconds that the connection was removed (bluez problem?)
* there's no notification or read support, however the complete infrastructure implementation is finished
* the GATT server and the LE adverstisement are marked to be experimental features in the Bluez stack

## Current Issues
* the ERROR level is not logged in the syslog for some reason
* the LE Advertisement is not removed for some reason, once the server is shut down (bluez problem?)
* there are still come methods which are printing to the standard output some debug data
* the company data within the advertisement packages

# Setup and dependencies

## Dependencies
* The Boxee server is based on the most recent bluez 5.34
* Python 2.x
* Systemd (bluez requirement)

# Debugging and development

## Dbus Monitoring

The best done via dbus-monitor. First one needs to configure the Dbus in a way that can have an eye on every command/signal on the bus

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
Then: dbus-monitor --system --monitor

## Installation of Bluez
```bash
sudo apt-get install tmux libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libreadline-dev libical0 libical-dev rfkill libnss-myhostname
sudo mkdir bluez
cd bluez

sudo wget https://www.kernel.org/pub/linux/bluetooth/bluez-5.34.tar.gz
sudo tar xvf bluez-5.11.tar
sudo rfkill unblock all

LDFLAGS=-lrt

sudo ./configure --enable-experimental --enable-maintainer-mode --enable-library --sysconfdir=/etc --prefix=/usr --mandir=/usr/share/man --localstatedir=/var --enable-tools

sudo make
sudo make install
```

Then you need to edit /lib/systemd/system/bluetooth.service and add *-nE** to the bluetoothd. This will enables to start the experimental features of the bluetooth daemon.

Create a link in: /etc/systemd/system
```
dbus-org.bluez.service -> /lib/systemd/system/bluetooth.service
```
Than
```bash
systemctl --system daemon-reload
systemctl restart bluetooth.service
```

## Hints and tricks
You can connect to BLE enbaled devices by using:
* if the bluetooth address is not public
** hcitool lecc --random <MAC>
* if the bluetooth address is public
** hcitool lecc <MAC>

Same goes with the gatttool:
* gatttool -t random -b <MAC> -I or
* gatttool -b <MAC> -I

One can check if the address is public or not by running *hcidump -X* and checking the address type while running *hcitool lescan*;

In case one have various connection errors you might try:
```bash
bluez*/tools/btmgmt pairable on
bluez*/tools/btmgmt le on
```
Also sometimes the connection error is due to
