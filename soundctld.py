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


# Name of the master ALSA mixer
MASTER = 'Master'

# Name of the other interesting ALSA output mixers
OUTPUTS = ("Headphone", "Speaker")

# DBus variables for this service
NOTIF_DBUS_ITEM = "org.freedesktop.Notifications"
NOTIF_DBUS_PATH = "/org/freedesktop/Notifications"
NOTIF_DBUS_INTERFACE = "org.freedesktop.Notifications"

# Number of volume steps when using the default step width
NUM_VOLUME_STEPS = 25


LOG_FILE = '/home/arch-sda7/ggazzi/.local/share/soundctld/soundctld.log'


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

    def __init__(self):
        logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

        bus_name = dbus.service.BusName('br.ggazzi.soundctl', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/br/ggazzi/soundctl')

        self.notifier = dbus.Interface( dbus.SessionBus().get_object(NOTIF_DBUS_ITEM, NOTIF_DBUS_PATH),
                                        NOTIF_DBUS_INTERFACE )

        self.volume_notif_id = 0
        self.output_notif_id = 0

    @dbus.service.method('br.ggazzi.soundctl')
    def notify_volume(self):
        try:
            self.volume_notif_id = self.notify( "Volume %d%%" % alsa.Mixer(MASTER).getvolume()[0],
                                                id_num=self.volume_notif_id )
        except Exception as e:
            logging.exception('')

    @dbus.service.method('br.ggazzi.soundctl', in_signature='n')
    def volume_up(self, amt):
        """Increases the volume by the given amount and issues a notification of the current volume.
        """
        try:
            mixer = alsa.Mixer(MASTER)

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
        self.volume_up(100 // NUM_VOLUME_STEPS)

    @dbus.service.method('br.ggazzi.soundctl')
    def volume_down_step(self):
        """Decreases the volume by the default step and issues a notification of the current volume.
        """
        self.volume_down(100 // NUM_VOLUME_STEPS)

    @dbus.service.method('br.ggazzi.soundctl')
    def notify_outputs(self):
        """Issues a notification showing which output mixers are currently active.
        """
        try:
            active = [ o for o in OUTPUTS if is_active(o) ]
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
            idx_curr = index_when(OUTPUTS, is_active)
            idx_next = 0 if idx_curr is None else idx_curr+1

            for out in OUTPUTS:
                alsa.Mixer(out).setmute(1)

            if idx_next < len(OUTPUTS):
                alsa.Mixer(OUTPUTS[idx_next]).setmute(0)

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

    def run(self):
        log("Daemon started.")

        from gi.repository import Gtk
        from dbus.mainloop.glib import DBusGMainLoop

        DBusGMainLoop(set_as_default=True)
        service = SoundCtlDBusService()

        log('Starting GTK loop...')
        Gtk.main()
        

if __name__ == '__main__': daemon.main( SoundCtlDaemon('/tmp/soundctld.pid') )
