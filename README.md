# Arduino Mega Code to record precise TTL pulse timing for several lines in parallel over long duration

The provided code monitors TTL lines and put a 32 bit timestamp (+ a
one byte flag for identification of the lines) each time a rising
front is detected. The 32 bit timing resolution, provides more than
2000 seconds of monitoring with 0.5μs resolution.

The code is written for atmega 2560 (monitoring up to 6 lines in
parallel) and 326P (up to 2 lines) and has been tested on Arduino Mega
2560 and Arduino Nano boards. The Arduino API being bypassed in
several places to solve performance and timing issues, port to other
microcontrollers may require a bit of work.

## Installation

The code comes in two parts: a firmware for the MCU and a python API
handling the custom communication with the MCU. Both live in the same
directory than can be retrieve from github with:

```
git clone https://github.com/betoule/logic_timer
```

### MCU code

The MCU code can be compiled and uploaded using the usual Arduino
IDE. Alternatively, we provide a makefile to compile and upload using
the Arduino-Makefile tool:

https://github.com/sudar/Arduino-Makefile

+ Install the arduino IDE
+ Install Arduino-Makefile
+ Adjust the following lines in the Makefile to match your own
  installation:

```
ARDUINO_DIR = /home/dice/soft/arduino-1.8.16
include ~/soft/Arduino-Makefile/Arduino.mk
```

+ Connect the board, compile and upload the firmware with:
```
make upload
```

### Python API

Installation of the python API using pip is obtained as:

```
pip install .
```

## Usage

Connect the TTL and ground lines to the corresponding external
interrupt pins and ground pins on the Arduino board. The
correspondence between line identifiers and board pins is given for
the two implemented boards in the following table:

| Flag   | Interrupt 2560 | Arduino Mega pin | Interrupt 326P | Arduino Nano pin |
| 1 << 0 | INT4           | 2                | INT0           | D2               |
| 1 << 1 | INT5           | 3                | INT1           | D3               |
| 1 << 2 | INT3           | 18               |                |                  |
| 1 << 3 | INT0           | 21               |                |                  |
| 1 << 4 | INT1           | 20               |                |                  |
| 1 << 5 | INT2           | 19               |                |                  |

The following picture display a 3 lines implementation using an Arduino Mega.

Assuming that the path to the serial device corresponding to the
arduino is /dev/ttyACM0, the following command will trigger a 20 second
record of the rising edges of pin 2 and 3 and of the falling edge
of pin 18 and store the result to timing.npy: 
```
logic-timer -t /dev/ttyACM0 -d 20 -l 0,1,2 -e rrf -o timing.npy
```

## Limitations

+ The code is intended to record events occurring at random times. As
  such, it generates 5 bytes of data per detected pulses (4 bytes for
  timing and 1 byte for line identification). It can only be used for
  timing events occurring with moderate frequency in average. It is
  not suited to record digital communications on a regular clock.

+ Handling of synchronous events. The interrupt handling routine takes
  about TX μs to complete. Simultaneous events will therefore be
  reported as separated by at least TX μs and ordered by the interrupt
  priority. This sets the worst case scenario for the timing
  precision. For non conflicting events the timing precision is
  limited by the clock resolution of 500 ns.

+ The maximal average frequency of events is limited by the bandwidth
  of the serial communication. The data is send encapsulated in
  packets of 8 bytes fed to a 256 bytes buffer (32 events). The buffer
  is emptied as fast as possible through the serial link. 1Mbps
  communication have been found to be reliable for the tested boards
  so that the theoretical maximum for the event frequency in a sliding
  window of 32 events is about 15kevents/s. In practice overflowing
  the buffer will results in crashing the microcode beyond recovery,
  therefore a solid margin should be considered so that this cannot
  occur.

+ Oscillating frequencies of the ceramic resonators (CSTCE16M0V53-R0)
  clocking the Arduino Mega boards are only accurate at the ~10⁻³
  level. The resulting inaccuracy in the clock scale does not matter
  when the device is solely used to synchronize the different
  lines. However comparison to external clocks are likely to be
  affected by the error in the MCU clock calibration and temperature
  shift. For applications requiring external references, the simplest
  work-around is to add the external reference as an additional
  line. It might be interesting to add functionalities to calibrate
  the MCU clock so that timestamps can be accurately converted to
  seconds for application where the time scale matters. Reaching
  acceptable accuracy would however likely require additional hardware
  to monitor the MCU temperature, or replacement of the ceramic
  oscillator with a temp controlled Xtal oscillator (TCXO such as
  DS3231). Nano boards ship with a quartz resonator from which better
  accuracy might be expected.
