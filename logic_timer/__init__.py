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
from typer import Typer, Option, Argument
from typing import List, Optional, Annotated

adc_pin_maps = {'A0': 0,
                'A1': 1,
                'A2': 2,
                'A3': 3,
                'A4': 4,
                'A5': 5,
                'A6': 6,
                'A7': 7,
                'MCU_TEMP': 8, # internal MCU temp sensor
                'VBG': 0b1110, # Internal voltage ref
                'GND': 0b1111, # Ground
                }

signature_bytes_map = {('0x1E', '0x95', '0x0F'): 'Atmega328P',
                       ('0x1E', '0x96', '0x08'): 'ATmega640',
                       ('0x1E', '0x97', '0x03'): 'ATmega1280',
                       ('0x1E', '0x97', '0x04'): 'ATmega1281',
                       ('0x1E', '0x98', '0x01'): 'ATmega2560',
                       ('0x1E', '0x98', '0x02'): 'ATmega2561',
                       }


# Main Typer app
app = Typer(
    name="logic-timer",
    help="High-resolution, long-duration timing device.",
    no_args_is_help=True,
    add_completion=True,  # Enable default typer completion
)

def list_methods(cls):
    # Get all attributes of the class
    all_attributes = dir(cls)
    
    # Filter out special Python methods, private methods, and non-callable attributes
    public_methods = [
        attr for attr in all_attributes 
        if callable(getattr(cls, attr)) 
        and not attr.startswith('__') 
        and not attr.startswith('_')
    ]    
    return public_methods

class LogicTimer(bincoms.SerialBC):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        self.signature_row = [self.read_signature_row(b) for b in [0x0, 0x1, 0x2]]
        # Read mcu temperature sensor calibration constants
        self._ts_offset = self.read_signature_row(0x0002)
        self._ts_gain = self.read_signature_row(0x0003)
        #
        self.duration = 1
        #
        self.frequency = self.get_frequency()

    def get_frequency(self):
        ''' Return the mcu clock frequency. Nominal or calibrated if avaialable'''
        freq = self.get_clock_calibration()
        if np.isnan(freq):
            import warnings
            warnings.warn('The mcu clock is not calibrated. If you need precise timings consider running "smartiris calibrate".')
            return 2e6
        else:
            return freq

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
        self.com._timeout = self.duration+1
        self.start(self.duration)
        while True:
            data.append(self.async_packet_read())
            if(data[-1][-1] == 0xFF):
                break
        return data

    def read_mcu_temperature(self):
        V_adc = self.read_adc(adc_pin_maps['MCU_TEMP'])
        return (V_adc - 273 + 100 - self._ts_offset)*128/self._ts_gain + 25

    def enable_lines(self, line_list):
        for l in line_list:
            if len(l) != 2:
                raise ValueError(f"Line identifier {l} does not comply with expected format [0-6][fr]")
            lid, front = int(l[0]), l[1].encode() 
            self.enable_line(lid, front)

        
@app.command(help='Print the device identification and status')
def status(
        tty: Annotated[str, Option('--tty', '-t', help='Specify a tty port for the device')] = '/dev/ttyACM0',
        verbose: Annotated[bool, Option('--verbose', '-v', help='Display communcation debuging messages')]=False,
        reset: Annotated[bool, Option('--reset', '-r', help='Reset the device')]=False,):
    '''
    '''
    d = LogicTimer(dev=tty, baudrate=1000000, debug=verbose, reset=reset)
    print(f'Logic timer: {d.signature_row}, MCU temperature: {d.read_mcu_temperature()}, frequency calibration constant: {d.frequency}')
    
@app.command(help='Record events for a given duration')
def record(
    duration: Annotated[float, Argument(help="Record duration in seconds")],
    tty: Annotated[str, Option('--tty', '-t', help='Specify a tty port for the device')] = '/dev/ttyACM0',
    verbose: Annotated[bool, Option('--verbose', '-v', help='Display communcation debuging messages')]=False,
    reset: Annotated[bool, Option('--reset', '-r', help='Reset the device')]=False,
    lines: Annotated[List[str], Option('--lines', '-l', help='Specify the lines to monitor. Each line identifier should be a line number followed by r (to timestamp rising fronts), f (to timestamp falling fronts) or b (to timestamp both fronts).')]=['0b', '1b'],
    output_file: Annotated[str, Option('--output-file', '-o', help='File name for the record')] = 'timing.npy',):
    d = LogicTimer(dev=tty, baudrate=1000000, debug=verbose, reset=reset)
    d.set_duration(duration)
    d.enable_lines(lines)
    print(f'Recording lines {lines} for {duration}s')
    data = d.get_data()
    data = [(r[0], r[0]/d.frequency, r[1]) for r in data]
    result = np.rec.fromrecords(data, names=['count', 'time', 'pinstate'])
    print(f'Record saved to file {output_file}')
    np.save(output_file, result)

@app.command(help='Plot the content of a record')
def display(filename: Annotated[str, Argument(help="Record duration in seconds")]):
    import matplotlib.pyplot as plt
    data = np.load(filename)
    pins = set(data['pinstate'])
    pins.remove(255)
    fig0 = plt.figure('records')
    ax = fig0.subplots(1, 1)
    fig = plt.figure('intervals')
    axes = fig.subplots(len(pins), 1, squeeze=False)
    
    def diff(x):
        return x[1:]-x[:-1]
    
    for i, pin in enumerate(pins):
        goods = data['pinstate'] == pin
        ax.plot(data['time'][goods], '.', label=pin)
        intervals = diff(data['time'][goods])
        emean = np.mean(intervals)
        rms = intervals.std()
        axes[i][0].plot(intervals, '.', label=pin)
        axes[i][0].axhline(emean, color='k', lw=0.5, label=f'{emean:.4e}s')
        axes[i][0].axhspan(emean-rms, emean+rms, color='k', label=f'±{rms:.3e}s', alpha=0.1)

        axes[i][0].legend()
    ax.legend()
    plt.show()
    
@app.command(help='Run the clock calibration routine for the given duration')
def calibrate(duration_min: Annotated[float, Option('--duration', '-d', help='Duration of the procedure in minutes')]=1,
              output_file: Annotated[str, Option('--output-file', '-o', help='Record the clock calibration data to the provided file')] = '',
              tty: Annotated[str, Option('--tty', '-t', help='Specify a tty port for the device')] = '/dev/ttyACM0',
              verbose: Annotated[bool, Option('--verbose', '-v', help='Display communcation debuging messages')]=False,
              reset: Annotated[bool, Option('--reset', '-r', help='Reset the device')]=False,):
    import logic_timer.clock_calibration
    device = LogicTimer(dev=tty, baudrate=1000000, debug=verbose, reset=reset)
    mcu_data, ntp_data = logic_timer.clock_calibration.acquire_clock_data(device, duration=duration_min*60)
    slope, eslope = logic_timer.clock_calibration.clock_calibration_fit(mcu_data['start'], mcu_data['mcu'])
    print(f'Measured a time scale difference of {(slope-1) * 100:.4f}% (±{eslope*100:.4f}%)')
    if output_file:
        logic_timer.clock_calibration.save(mcu_data, ntp_data, output_file)
        print(f'Calibration data saved in {output_file}. Clock scale not adjusted')
    else:
        calibrated_frequency = device.frequency * slope
        print(f'Adjusting frequency from {device.frequency * 1e-6:.6f} MHz to {calibrated_frequency * 1e-6:.6f} MHz')
        device.set_clock_calibration(calibrated_frequency)
        device.frequency = calibrated_frequency

@app.command(help='Call a raw function of the device and print the returned value')
def raw(action: Annotated[str, Argument(help="Record duration in seconds")],
        tty: Annotated[str, Option('--tty', '-t', help='Specify a tty port for the device')] = '/dev/ttyACM0',
        verbose: Annotated[bool, Option('--verbose', '-v', help='Display communcation debuging messages')]=False,
        reset: Annotated[bool, Option('--reset', '-r', help='Reset the device')]=False):
    d = LogicTimer(dev=tty, baudrate=1000000, debug=verbose, reset=reset)
    if not hasattr(d, action):
        print(f'Unknown command {action}')
        print(f'known: {list_methods(d)}')
    else:
        print(getattr(d, action)())

@app.command(help='Start an xmlrpc server to expose the device functionalities')
def start_server(
        hostname: Annotated[str, Option('--hostname', '-H', help='Specify the address to listen')] = '0.0.0.0',
        port: Annotated[int, Option('--port', '-p', help='Specify a port for the server')] = 7912,
        tty: Annotated[str, Option('--tty', '-t', help='Specify a tty port for the device')] = '/dev/ttyACM0',
        verbose: Annotated[bool, Option('--verbose', '-v', help='Display communcation debuging messages (inhibit daemonisation)')]=False,
        reset: Annotated[bool, Option('--reset', '-r', help='Reset the device')]=False):
    d = LogicTimer(dev=tty, baudrate=1000000, debug=verbose, reset=reset)
    import logic_timer.daemon_servers
    server = daemon_servers.BasicServer((hostname, port), 'logic-timer', d)
    print(f"Listening on http://{hostname}:{port}")
    if not verbose:
        daemon_servers.daemonize(server)
    else:
        server.main()
        
def main():
    """The main entry point for the Cosmologix command-line interface."""
    app()


#def test():
#    ''' Monitor TTL lines and record timestamps for detected fronts'''
#    import argparse
#    parser = argparse.ArgumentParser(
#        description='Timing of fronts dectected in TTL lines.')
#    parser.add_argument(
#        '-t', '--tty', default='/dev/ttyACM0',
#        help='link to a specific tty port')
#    parser.add_argument(
#        '-d', '--duration', default=20, type=float,
#        help='link to a specific tty port')
#    parser.add_argument(
#        '-l', '--enabled-lines', default=["0r", "1r", "2f"], nargs='*',
#        help='Identifiers of the lines to monitor. Each id should be a line number followed by r (to stamp the rising front) or f (to stamp the falling front).')
#    parser.add_argument(
#        '-v', '--verbose', action='store_true',
#        help='Print communication debugging info')
#    parser.add_argument(
#        '-r', '--reset', action='store_true',
#        help='Hard reset the device at startup')
#    parser.add_argument(
#        '-o', '--output-file', default='timing.npy',
#        help='Filename for the record')
#    
#    args = parser.parse_args()
#
#    d = LogicTimer(dev=args.tty, baudrate=1000000, debug=args.verbose, reset=args.reset)
#    d.set_duration(args.duration)
#    for l in args.enabled_lines:
#        if len(l) != 2:
#            raise ValueError(f"Line identifier {l} does not comply with expected format [0-6][fr]")
#        lid, front = int(l[0]), l[1].encode() 
#        d.enable_line(lid, front)
#    import numpy as np
#    print(f'Recording lines {args.enabled_lines} for {args.duration}s')
#    result = np.rec.fromrecords(d.get_data(), names=['time', 'pinstate'])
#    print(f'Record saved to file {args.output_file}')
#    np.save(args.output_file, result)

