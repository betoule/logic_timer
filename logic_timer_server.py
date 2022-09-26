#!/usr/bin/python

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
