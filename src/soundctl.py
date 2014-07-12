#!/usr/bin/python
from argparse import ArgumentTypeError
from dbusclient import DBusClient, bounded


percentage = bounded(int, 0, 100, exception_type=ArgumentTypeError)

client = DBusClient(item="br.ggazzi.soundctl",
                    path="/br/ggazzi/soundctl",
                    interface="br.ggazzi.soundctl")



client.add_method('notify_volume',
                  help='Issues a desktop notification with the current volume')


method = client.add_method('volume_up',
                           help='Increases the volume by a given amount')
method.add_argument('amt', metavar='INCR', type=percentage,
                    help='Amount being incremented to the volume percentage.')


client.add_method('volume_up_step',
                  help='Increases the volume by a fixed amount.')


method = client.add_method('volume_down',
                           help='Decreases the volume by a given amount')
method.add_argument('amt', metavar='INCR', type=percentage,
                    help='Amount being decremented from the volume percentage.')                    


client.add_method('volume_down_step',
                  help='Decreases the volume by a fixed amount.')


client.add_method('notify_outputs',
                  help='Issues a notification showing the currently active output mixers.')


client.add_method('cycle_outputs',
                  help='Cycles throught the output mixers, leaving only one of them active '
                  'at a time, and at the end of the cycle muting them all.')

if __name__ == '__main__': client.run()
