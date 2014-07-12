#!/usr/bin/python
"""Simple daemon for controlling the audio options and displaying notifications of the change.

This daemon allows simple control of audio parameters, while
triggering notifications (through dbus, using freedesktop's
Desktop Notifications Specification) of the changes made.
"""

import logging

import alsaaudio as alsa

import dbus
import dbus.service

import daemon


# DBus variables for this service
NOTIF_DBUS_ITEM = "org.freedesktop.Notifications"
NOTIF_DBUS_PATH = "/org/freedesktop/Notifications"
NOTIF_DBUS_INTERFACE = "org.freedesktop.Notifications"


def is_active(output):
    """True iff any channel of the given mixer is not muted.
    """
    return any( mute==0 for mute in alsa.Mixer(output).getmute() )

def index_when(elements, condition):
    """Return the first index xof the given list whose element satisfies the condition.
    """
    for idx, el in enumerate(elements):
        if condition(el):
            return idx
    return None

def mean(numbers):
    return sum(numbers)/len(numbers)


class SoundCtlDBusService(dbus.service.Object):
    """Service providing the sound-controlling functions with change notifications.
    """

    @property
    def notifier(self):
        return dbus.Interface( dbus.SessionBus().get_object(NOTIF_DBUS_ITEM, NOTIF_DBUS_PATH),
                               NOTIF_DBUS_INTERFACE)

    def __init__(self, master_mixer, output_mixers, num_volume_steps):
        self.master = master_mixer
        self.outputs = output_mixers
        self.volume_increment = 100 // num_volume_steps
        logging.debug('Initialized with master='+repr(self.master)+
                      ', outputs='+repr(self.outputs)+
                      ', vol-steps='+repr(num_volume_steps))

        bus_name = dbus.service.BusName('br.ggazzi.soundctl',
                                        bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
                                     '/br/ggazzi/soundctl')
        self.volume_notif_id = 0
        self.output_notif_id = 0

    @dbus.service.method('br.ggazzi.soundctl')
    def notify_volume(self):
        try:
            self.volume_notif_id = self.notify( "Volume %d%%" % alsa.Mixer(self.master).getvolume()[0],
                                                id_num=self.volume_notif_id )
        except Exception as e:
            logging.exception('')

    @dbus.service.method('br.ggazzi.soundctl', in_signature='n')
    def volume_up(self, amt):
        """Increases the volume by the given amount and issues a notification of the current volume.
        """
        try:
            mixer = alsa.Mixer(self.master)

            curr_volume = int(mean(mixer.getvolume()))
            next_volume = min(curr_volume+amt, 100)

            mixer.setvolume(next_volume)
            self.notify_volume()

        except Exception as e:
            logging.exception('')

    @dbus.service.method('br.ggazzi.soundctl', in_signature='n')
    def volume_down(self, amt):
        """Decreases the volume by the given amount and issues a notification of the current volume.
        """
        self.volume_up(-amt)

    @dbus.service.method('br.ggazzi.soundctl')
    def volume_up_step(self):
        """Increases the volume by the default step and issues a notification of the current volume.
        """
        self.volume_up(self.volume_increment)

    @dbus.service.method('br.ggazzi.soundctl')
    def volume_down_step(self):
        """Decreases the volume by the default step and issues a notification of the current volume.
        """
        self.volume_down(self.volume_increment)

    @dbus.service.method('br.ggazzi.soundctl')
    def notify_outputs(self):
        """Issues a notification showing which output mixers are currently active.
        """
        try:
            active = [ o for o in self.outputs if is_active(o) ]
            self.output_notif_id = self.notify( ', '.join(active) if len(active) > 0 else 'Mute',
                                                id_num=self.output_notif_id )
        except Exception as e:
            logging.exception('')

    @dbus.service.method('br.ggazzi.soundctl')
    def cycle_outputs(self):
        """Cycle through the interesting outputs, keeping at most one non-muted.

        Each of the output mixers configured gets a turn for being active,
        plus a turn for muting them all.
        """
        try:
            idx_curr = index_when(self.outputs, is_active)
            idx_next = 0 if idx_curr is None else idx_curr+1

            for out in self.outputs:
                alsa.Mixer(out).setmute(1)

            if idx_next < len(self.outputs):
                alsa.Mixer(self.outputs[idx_next]).setmute(0)

            self.notify_outputs()

        except Exception as e:
            logging.exception('')


    def notify(self, summary, text='', id_num=0, time=1000, icon='volume-knob'):
        """Issue a notification using the freedesktop's specification.

        This function is a helper, using a single instance of the notifier
        interface stup, and already providing some appropriate default arguments.
        """
        return self.notifier.Notify("soundctl", id_num, icon, summary, text, '', '', time)


class SoundCtlDaemon(daemon.Daemon):
    """Daemon class for running the service.
    """

    def run(self, args):
        logging.basicConfig(filename=args.log_file, level=logging.DEBUG)
        logging.info("Daemon started.")

        try:
            from gi.repository import Gtk
            from dbus.mainloop.glib import DBusGMainLoop

            DBusGMainLoop(set_as_default=True)
            service = SoundCtlDBusService(args.master_mixer,
                                          args.output_mixers,
                                          args.num_volume_steps)

            logging.info('Starting GTK loop.')
            Gtk.main()
        except:
          import traceback
          logging.error(traceback.format_exc())

    def add_command_line_arguments_to(self, group):
        import os

        def mixer_list(argument):
            return argument.split(':')

        group.add_argument('--log-file', dest='log_file', metavar='FILE',
                           default='/tmp/soundctld_'+str(os.getuid())+'.log')

        group.add_argument('--master', dest='master_mixer', metavar='MIXER',
                           default='Master')

        group.add_argument('--outputs', dest='output_mixers', metavar='MIXERS',
                           type=mixer_list, default='Speaker:Headphone',
                           help='Colon-separated list of output mixers.')

        group.add_argument('--vol-steps', dest='num_volume_steps', metavar='N',
                           type=int, default='25',
                           help='Number of possible volume configurations, used'
                                 ' to define the volume increments and'
                                 ' decrements [default=25]')

if __name__ == '__main__': daemon.main( SoundCtlDaemon('/tmp/soundctld.pid') )
