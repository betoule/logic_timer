# Copyright 2021-2022 Marc Betoule
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bincoms
import struct
import time
import numpy as np

class LogicTimer(bincoms.SerialBC):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        self.duration = 1
        
    def async_packet_read(self):
        ans = self.rcv()
        answer = struct.unpack('<IB', ans)
        return answer

    def set_duration(self, duration):
        self.duration = duration

    def get_duration(self):
        return self.duration
    
    def get_data(self):
        data = []
        self.start(self.duration)
        #self.com.timeout = self.duration+1
        while True:
            data.append(self.async_packet_read())
            if(data[-1][-1] == 0xFF):
                break
        return data


def test():
    ''' Monitor TTL lines and record timestamps for detected fronts'''
    import argparse
    parser = argparse.ArgumentParser(
        description='Timing of fronts dectected in TTL lines.')
    parser.add_argument(
        '-t', '--tty', default='/dev/ttyACM0',
        help='link to a specific tty port')
    parser.add_argument(
        '-d', '--duration', default=20, type=float,
        help='link to a specific tty port')
    parser.add_argument(
        '-l', '--enabled-lines', default=["0r", "1r", "2f"], nargs='*',
        help='Identifiers of the lines to monitor. Each id should be a line number followed by r (to stamp the rising front) or f (to stamp the falling front).')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Print communication debugging info')
    parser.add_argument(
        '-o', '--output-file', default='timing.npy',
        help='Filename for the record')
    
    args = parser.parse_args()

    d = LogicTimer(dev=args.tty, baudrate=1000000, debug=args.verbose)
    d.set_duration(args.duration)
    for l in args.enabled_lines:
        if len(l) != 2:
            raise ValueError(f"Line identifier {l} does not comply with expected format [0-6][fr]")
        lid, front = int(l[0]), l[1].encode() 
        d.enable_line(lid, front)
    import numpy as np
    print(f'Recording lines {args.enabled_lines} for {args.duration}s')
    result = np.rec.fromrecords(d.get_data(), names=['time', 'pinstate'])
    print(f'Record saved to file {args.output_file}')
    np.save(args.output_file, result)
