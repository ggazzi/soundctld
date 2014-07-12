import dbus
import argparse

def verifying(cast, pre_condition=None, pre_message=None, post_condition=None, 
              post_message=None, exception_type=None):
    """Create a version of the given 'type-cast' with added constraints.

    The pre_condition is applied to the value before 'casting', and
    the post_condition after casting. If either of them fails, an
    exception is raised with an appropriate message.

    The message arguments may use string formatting syntax,
    and the invalid value will be included as 'value'.

    The raised exception is ValueError by default, but may be
    specified by the 'exception_type' parameter.
    """
    exception_type = exception_type or ValueError
    pre_message = pre_message or ("value {value} did not satisfy constraints "
                                  "for being converted.")
    post_message = post_message or ("value {value} did not satisfy constraints "
                                    "after conversion.")

    def new_cast(value):
        if pre_condition and not pre_condition(value):
            msg = pre_message.format(value=value)
            raise exception_type(msg)

        converted = cast(value)

        if post_condition and not post_condition(converted):
            msg = post_message.format(value=converted)
            raise exception_type(msg)

        return converted

    return new_cast

def bounded(cast, min, max, exception_type=None):
    """Creates a version of the given type-cast bounding the result.
    """
    return verifying(cast, post_condition=lambda x: min<=x and x<=max,
                     post_message="Value {value} out of bounds [%r, %r]" % (min, max),
                     exception_type=exception_type)

def str_bool(string):
    """Tries to interpret a string as a boolean value, sensibly.
    """
    lowstring = string.lower()
    if truestr == lowstring:
        return True
    elif falsestr == lowstring:
        return False
    else:
        msg = "'%s' is neither '%s' nor '%s'." % (string, truestr, falsestr)
        raise argparse.ArgumentTypeError(msg)


DBUS_TYPES = {
    'b':  str_bool,
    'y':  bounded(int, -2**7, 2**7-1),
    'n':  bounded(int, -2**15, 2**15-1),
    'i':  bounded(int, -2**31, 2**31-1),
    'x':  bounded(int, -2**63, 2**63-1),
    'q':  bounded(int, 0, 2**16-1),
    'u':  bounded(int, 0, 2**32-1),
    't':  bounded(int, 0, 2**64-1),
    'd':  float,
    's':  str
}

class DBusClient:

    def __init__(self, item, path, interface, *args, **kwargs):
        self.item = item
        self.path = path
        self.interface = interface

        parser = argparse.ArgumentParser(*args, **kwargs)
        self.arg_parser = parser
        self.method_subparsers = parser.add_subparsers(title='commands',
                                                       dest='method', 
                                                       metavar='COMMAND',
                                                       description="Possible commands to call. Invoke "
                                                       "them with the '-h' or '--help' option for "
                                                       "more information.")

    def add_method(self, name, **kwargs):
        if 'help' not in kwargs:
            kwargs['help'] = ''
        if 'description' not in kwargs:
            kwargs['description'] = kwargs['help']
        parser = self.method_subparsers.add_parser(name, **kwargs)
        return DBusMethod(parser)

    def parse_args(self, args=None, namespace=None):
        namespace = namespace or argparse.Namespace(method_args=[])
        return self.arg_parser.parse_args(args, namespace)

    def run(self, argv=None):
        args = self.parse_args(argv)

        bus = dbus.SessionBus()
        obj = bus.get_object(self.item, self.path)
        getattr(obj, args.method)(*args.method_args, dbus_interface=self.interface)


class DBusMethod:

    def __init__(self, parser):
        self.arg_parser = parser    

    def add_argument(self, name, **kwargs):
        if 'type' in kwargs and isinstance(kwargs['type'], str):
            kwargs['type'] = DBUS_TYPES[kwargs['type']]

        kwargs['action'] = DBusMethod.ArgAction

        self.arg_parser.add_argument(name, **kwargs)

    @staticmethod
    def validating(type, is_valid, invalid_msg):
        def fn(value):
            value = type(value)
            if not is_valid(value):
                msg = invalid_msg.format(value=value)
                raise argparse.ArgumentTypeError(msg)
            return value
        return fn

    class ArgAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string):
            namespace.method_args.append(values)
            setattr(namespace, self.dest, values)
            
