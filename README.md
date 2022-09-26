# TTL pulse timing for three lines in parallel over long duration

The provided code monitor three TTL lines and put a 32 bit timestamp
(+identifier of the corresponding line) each time a rising front is
detected. The 32 bit timing resolution, provides more than 2000
seconds of monitoring with 0.5μs resolution.

It is written for atmega 2560 and has been tested on an arduino Mega
2560 board. The arduino API being bypassed in many places to solve
performance issues, port to other microcontrollers may require some
work.

## Installation

The code comes in two parts: a firmware for the MCU and a python API
handling the custom communication with the MCU. Both live in the same directory than can be retrieve from github with:
```
git clone https://github.com/betoule/logic_timer
```

### MCU code

The MCU code can be compiled and uploaded using the usual arduino
IDE. Alternatively, we provide a makefile to compile and upload using
the Arduino-Makefile tool:

https://github.com/sudar/Arduino-Makefile

+ Install the arduino IDE
+ Install Arduino-Makefile
+ Adjust the following lines in the Makefile:
```
ARDUINO_DIR = /home/dice/soft/arduino-1.8.16
include ~/soft/Arduino-Makefile/Arduino.mk
```
to match your own installation.
+ Connect the board and compile and upload the firmware with:
```
make upload
```

### Python API

## Usage

Connect the TTL and ground lines to the corresponding PC interrupt
pins and ground pins on the arduino board. For the arduino Mega 2560
board the pins monitored are 

## Limitations


