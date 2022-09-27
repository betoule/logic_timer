#!/usr/bin/python

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

import datetime
import os
import stardice.daemon_servers
import logic_timer

if __name__ == "__main__":
    import argparse 
    parser = argparse.ArgumentParser(description="Logical analyser")
    parser.add_argument('-d', '--daemon', default=False, 
                        action='store_true', 
                        help='Run as a background daemon')
    parser.add_argument('-p', '--port', default=7912, 
                        action='store', type=int, 
                        help='Listen on port')
    parser.add_argument('-H', '--hostname', default='0.0.0.0', 
                        action='store', 
                        help='server address')
    parser.add_argument('-t', '--tty', default='/dev/ttyACM0', 
                        dest='tty', action='store', 
                        help='specify the serial port')
    args = parser.parse_args()
    
    SERVER_HOSTNAME = args.hostname
    SERVER_PORT = args.port
    
    name = 'logic_timer'
    stardice.daemon_servers.setup_logging(name)

    analyserserver = logic_timer.LogicTimer(dev=args.tty, baudrate=1000000, debug=not args.daemon)
    
    server = stardice.daemon_servers.BasicServer((SERVER_HOSTNAME, SERVER_PORT), name, analyserserver)
    
    if args.daemon:
        stardice.daemon_servers.daemonize(args, None, server)
    else:
        server.main(args, None)
