# Copyright 2022 Marc Betoule
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

import struct
import time
import numpy as np
import serial
import types
import os
import select
from serial.serialutil import Timeout
status_codes = ['STATUS_OK',
                'STATUS_BUSY',
                'STATUS_ERROR',
                'UNDEFINED_FUNCTION_ERROR',
                'BYTE_COUNT_ERROR',
                'COMMUNICATION_ERROR',
                'CHECKSUM_ERROR',
                'VALUE_ERROR']

status_message = ['Action performed successfully',
                  'Device is busy with another action',
                  'Action failed for undefined cause',
                  'Unknown function code (check command_count)',
                  'Incorrect size for the provided data buffer (check get_command_names({f},1) for the requested number of arguments',
                  'Ill-formed message on the communication port',
                  'Not used for now',
                  'The provided arguments are outside the allowed range']

def lookup():
    import glob

def _command_factory(self, f, s, a):
    def func(self, *args):
        data = struct.pack(b'<B' + s, f, *args)
        if self.debug:
            print(f'Encoding request with arguments {args} according to format {b"B"+s} as: {data}')
        r = self.snd(data)
        if a == b's':
            if self.debug:
                print(f'data: {r}')
            return r.decode()
        else:
            try:
                answer = struct.unpack(a, r)
                if self.debug:
                    print(f'data: {answer}')
                if len(answer) == 1:
                    return answer[0]
                else:
                    return answer
            except:
                buffer = self.flush()
                raise ValueError(f'Received answer "{r}" does not match the expected argument format: "{a}", trailing bytes:{buffer}')
    return types.MethodType(func, self)

class SerialBC(object):
    def __init__(self, dev='/dev/ttyUSB0', baudrate=115200, debug=True):
        self.com = serial.Serial(dev, baudrate=baudrate, timeout=3)
        #self.com.set_low_latency_mode(True)
        self.debug=debug
        #time.sleep(5)
        #self.com.flush()
        for i in range(2):
            try:
                self._register_commands()
                break
            except ValueError:
                self.com.flush()
    def _read(self, size):
        read = bytearray()
        #timeout = Timeout(self.com._timeout)
        for i in range(10000):
            buf = os.read(self.com.fd, size - len(read))
            read.extend(buf)
            if len(read) == size:
                break
            time.sleep(0.0001)
        return bytes(read)
    
    def _register_commands(self):
        self._get_nfunc = _command_factory(self, 0x00, b'', b'B')
        self._get_func_name = _command_factory(self, 0x01, b'BB', b's')
        for i in range(2, self._get_nfunc()):
            name, arg_format, answer_format = [self._get_func_name(i, a) for a in range(3)]
            if self.debug:
                print(f'Registering user function "{name}"')
            setattr(self, name, _command_factory(self, i, arg_format.encode(), answer_format.encode()))
                    
    def rcv(self):
        b = self.com.read(3)
        if self.debug:
            print(f'Received: {b}')
        try:
            m, a, l = struct.unpack(b'ccB', b)
        except:
            raise ValueError(f'Answer header: "{b}" does not match expected format "bcB"')
        a = int.from_bytes(a, byteorder='little', signed=False)
        if self.debug:
            print(f'header: {m.decode()},{status_codes[a]},{l}')  
        if (m == b'b' ) and (a == 0):
            data = self.com.read(l)
        elif (m == b'b') and (a < len(status_codes)):
            raise ValueError(f'{status_codes[a]}, {status_message[a]}')
        else:
            self.com.flush()
            raise ValueError (f'Answered string not understood: {b}')
        return data

    def snd(self, data):
        b = struct.pack(b'ccB', b'b', b'\x00', len(data))
        #print(b+data)
        if self.debug:
            print(f'Send: {b+data}')
        self.com.write(b+data)
        return self.rcv()

    def flush(self):
        return self.com.read_all()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Communicate with device implementing the generic bincoms protocol')
    parser.add_argument(
        '-t', '--tty', action='append', default=[],
        help='link to a specific tty port')
    args = parser.parse_args()
    
    for dev in args.tty:
        d = SerialBC(dev)
