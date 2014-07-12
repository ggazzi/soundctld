soundctld
=========

Linux utility for controlling alsa output and notifying the user of changes.
Useful for those who use minimal Window Managers (e.g. XMonad, Awesome, i3)
instead of full-blown Desktop Environments (e.g. GNOME, KDE, XFCE), but still
want to use multimedia keys to control the volume.

The whole implementation is based on the following behavior:
 * The "Volume Up" key should increment the current (master) volume by a fixed amount
 * The "Volume Down" key should decrement the current (master) volume by a fixed amount
 * Only one of the outputs should be active at a time, therefore the "Mute" key 
   rotates between the outputs (plus a mute state)

The implementation consists of two parts: a daemon, which listens on D-Bus for
commands, and a corresponding command-line client. For more information on how
to use those programs, call them on the command line with option `--help`.

The recommended usage is then to bind your multimedia keys to the appropriate commands,
e.g. the "Mute" key to `soundctl cycle_outputs`.

#### Dependencies

The only supported OS is currently Linux. Users should have ALSA and D-Bus
installed. This is __not__ compatible with PulseAudio.

The following python libraries are used:

 * [PyAlsaAudio](http://pyalsaaudio.sourceforge.net)/
 * [dbus-python](http://www.freedesktop.org/wiki/Software/DBusBindings/#Python) version 1.0.*
