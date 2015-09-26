__author__ = 'tamas'
import dbus

def describe_dbus_dict(dbus_dict):
    s = []
    for key, value in dbus_dict:
        if isinstance(value, dbus.Array):
            s.append(key)
            for v in value:
                s.append('\t%s\n' % v)
        elif isinstance(value, dbus.Dictionary):
            s.append(key)
            for k, v in value.iteritems():
                s.append('\t%s=%s\n' % (k, v))
        else:
            s.append('%s = %s' % (key, value))
        s.append('\n')
    return "".join(s)
