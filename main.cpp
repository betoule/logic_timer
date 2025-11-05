// Copyright 2022 Marc Betoule
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, version 2 of the License.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

//#include <Arduino.h>
#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>
//#include <cstdio>
#include "bincoms.h"
#include <avr/eeprom.h>

extern struct Com client;

// Macros to start and stop the 16-bit timer
#define STOP_TIMER TCCR1B = 0b00000000
#define START_TIMER TCCR1B = 0b00000010
// External interupt lines
#define ENABLEINT EIMSK |= enabled_lines
#define DISABLEINT EIMSK &= ~enabled_lines
#define CLEARINT EIFR |= enabled_lines
#define CLEAR_TINT TIFR1 = _BV(OCF1A)

#if defined(ARDUINO_AVR_MEGA2560)
#define NLINES 6
const uint8_t line_correspondence[] = {4, 5, 3, 0, 1, 2};
#elif defined(ARDUINO_AVR_PRO)
#define NLINES 2
const uint8_t line_correspondence[] = {0, 1};
#else
  #error Unsupported board selection.
#endif

/* The assembly code in the MACRO below unrolls the writing of bytes
 * in the communication buffer, taking advantage on the 256 bit
 * alignment of the buffer to save time. It is roughly equivalent to:
 * client.write_buffer[client.we++] = 'b';
 * client.write_buffer[client.we++] = 0x00;
 * client.write_buffer[client.we++] = 5;
 * client.write_buffer[client.we++] = ((char*) &timeLB)[0];
 * client.write_buffer[client.we++] = ((char*) &timeLB)[1];
 * client.write_buffer[client.we++] = ((char*) &timeHB)[0];
 * client.write_buffer[client.we++] = ((char*) &timeHB)[1];
 * client.write_buffer[client.we++] = line;
 */
#define INTERRUPT_HANDLER(line)                                    \
  uint16_t timeLB = TCNT1;					   \
  if ((TIFR1 & 0b1) && (timeLB < 10)){				   \
    timeHB++;							   \
    TIFR1 |= _BV(TOV1);						   \
  }								   \
  volatile uint8_t * val_pointer = client.write_buffer + client.we;\
  asm volatile("ldi r24, 0x62" "\n\t"				   \
	       "st %a1, r24" "\n\t"				   \
	       "ldi r24, 0x00" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, r24" "\n\t"				   \
	       "ldi r24, 0x05" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, r24" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, %A0" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, %B0" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, %A2" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, %B2" "\n\t"				   \
	       "ldi r24, %3" "\n\t"				   \
	       "inc %A1" "\n\t"					   \
	       "st %a1, r24" "\n\t"				   \
	       : 						   \
	       : "r" (timeLB),					   \
		 "e" (val_pointer),				   \
		 "r" (timeHB),					   \
		 "I" (line)                                        \
	       :"r24"						   \
	       );						   \
  client.we += 8;                                                  \


void start(uint8_t rb);
void enable_line(uint8_t rb);
void get_enabled_lines(uint8_t rb);
void start_timer(uint8_t rb);
void get_time(uint8_t rb);
void get_clock_calibration(uint8_t rb);
void set_clock_calibration(uint8_t rb);
void read_adc(uint8_t rb);
void read_signature_row(uint8_t rb);

uint16_t duration;
uint16_t timeHB;
uint8_t enabled_lines = 0;

const uint8_t NFUNC = 2+9;
uint8_t narg[NFUNC];
// The exposed functions
void (*func[NFUNC])(uint8_t rb) =
  {// Communication protocol
   command_count,
   get_command_names,
   // user defined
   start,
   enable_line,
   get_enabled_lines,
   start_timer,
   get_time,
   get_clock_calibration,
   set_clock_calibration,
   read_adc,
   read_signature_row,
  };

const char* command_names[NFUNC*3] =
  {"command_count", "", "B",
   "get_command_names", "BB", "s",
   // user defined
   "start", "f", "H",
   "enable_line", "Bc", "",
   "get_enabled_lines", "", "B",
   "start_timer", "", "",
   "get_time", "", "I",
   "get_clock_calibration", "", "f",
   "set_clock_calibration", "f", "",
   "read_adc", "B", "H",
   "read_signature_row", "H", "B",
  };

void enable_line(uint8_t rb){
  if (client.read_buffer[rb] >= NLINES)
    client.sndstatus(VALUE_ERROR);
  else{
    uint8_t sense_control_bit = 0;
    uint8_t int_num = line_correspondence[client.read_buffer[rb]];
    if (client.read_buffer[rb+1] == 'r')
      sense_control_bit = 0b11;
    else if (client.read_buffer[rb+1] == 'f')
      sense_control_bit = 0b10;
    else if (client.read_buffer[rb+1] == 'b')
      sense_control_bit = 0b01;
    else
      client.sndstatus(VALUE_ERROR);
    enabled_lines |= 1 << int_num;
    if (int_num < 4){
      EICRA = (EICRA & ~(0b11 << 2*int_num)) | (sense_control_bit << (2*int_num));
    }
    else{
      int_num -= 4;
      EICRB = (EICRB & ~(0b11 << 2*int_num)) | (sense_control_bit << (2*int_num)); 
    }
    client.sndstatus(STATUS_OK);
  }
}

void setup(){
  setup_bincom();

#if defined(ARDUINO_AVR_MEGA2560)
  // MEGA pin assignments
  // PORT B D and E setup
  // All pull-up inputs but for output on arduino pin 13
  DDRB   = 0b10000000;
  PORTB  = 0b01111111;
  DDRD   = 0b00000000;
  PORTD  = 0b11111111;
  DDRE   = 0b0;
  //PORTE  = 0b11111111;
  PORTE  = 0b0;
  PCMSK0 = 0b00000000;
  // Setup external interrupt rise for arduino pin 2 and 3 (PE4 and PE5)
  //PCICR |= _BV(PCIE0);
  EICRB |= _BV(ISC51) | _BV(ISC50) | _BV(ISC41) | _BV(ISC40);
  // Setup external interrupt falling for arduino pin 18 (PD3)
  EICRA |= _BV(ISC31);
  EICRA &= ~_BV(ISC30);
#elif defined(ARDUINO_AVR_PRO)
  // Pro Mini assignments
  // PORTB setup for output on arduino pin 13
  DDRB   = _BV(PB5);
  PORTB  = ~_BV(PB5);
  // PORTD PIN D2 and D3 
  PCMSK0 = 0b00000000;
  // Setup external interrupt rise for arduino pin 2 and 3 (INT0 and INT1)
  EICRA |= _BV(ISC11) | _BV(ISC10) | _BV(ISC01) | _BV(ISC00);  
#else
  #error Unsupported board selection.
#endif
  
  //SET_TIMER1_CLOCK(TIMER_CLOCK_1);
  // 16-bit TIMER1 settings
  // This timer is used to follow the clock count
  // TCCR1A: COM1A1:COM1A0:COM1B1:COM1B0:0:0:WGM11:WGM10
  // TCCR1B: ICNC1:ICES1:0:WGM13:WGM12:CS12:CS11:CS10
  // TIMSK1: 0:0:ICIE1:0:0:OCIE1B:OCIE1A:TOIE1
  // COM1A: 0b01 toggle on compare match
  // COM1B: 0b01 toggle on compare match
  // WGM: 0b0100 CTC
  // WGM: 0b0000 Normal
  // CS1: 0b000 STOP
  TCCR1A = 0b00000000;
  STOP_TIMER;
  //TCCR1B = 0b00000010;
  TIMSK1 = 0b00000001;

  // Make sure other timer are disabled
  TCCR0B = 0b0;
  TIMSK0 = 0b0;
  TCCR2B = 0b0;
  TIMSK2 = 0b0;
  EIMSK = 0b0;

  // Set global interrupt enable
  sei();
}

// Handle interrupt on arduino Pin3
#if defined(ARDUINO_AVR_MEGA2560)
ISR(INT5_vect){
#elif defined(ARDUINO_AVR_PRO)
ISR(INT1_vect){  
#endif
  INTERRUPT_HANDLER(0x02)
}

// Handle interrupt on arduino pin2
#if defined(ARDUINO_AVR_MEGA2560)
ISR(INT4_vect){
#elif defined(ARDUINO_AVR_PRO)
ISR(INT0_vect){
#endif
  INTERRUPT_HANDLER(0x01)
}

#if defined(ARDUINO_AVR_MEGA2560)
// Handle interrupt on arduino pin 18
ISR(INT3_vect){
  INTERRUPT_HANDLER(0x04)
}
// Handle interrupt on arduino pin 21
ISR(INT0_vect){
  INTERRUPT_HANDLER(0b1000)
}
// Handle interrupt on arduino pin 20
ISR(INT1_vect){
  INTERRUPT_HANDLER(0b10000)
}
// Handle interrupt on arduino pin 19
ISR(INT2_vect){
  INTERRUPT_HANDLER(0b100000)
}

#endif
// Update high bytes of the timer counter
ISR(TIMER1_OVF_vect){
  timeHB++;
}

void start_timer(uint8_t rb){
  /* Start the timer execution without program
    (Usually used for clock calibration purpose)
   */
  // Disable interrupts
  DISABLEINT;
  // Reset the timer
  timeHB=0;
  TCNT1=0;
  CLEAR_TINT;
  // Enable timer overflow but not the other instructions
  TIMSK1 = 0b00000001;
  START_TIMER;
  client.sndstatus(STATUS_OK);
}

void get_time(uint8_t rb){
  uint32_t timestamp = timeHB;
  timestamp <<= 16;
  timestamp += TCNT1;
  client.snd((uint8_t*) &timestamp, 4, STATUS_OK);
}

void get_enabled_lines(uint8_t rb){
  client.snd((uint8_t*) &enabled_lines, 1, STATUS_OK);
}

void start(uint8_t rb){
  // We receive the duration as a floating point in seconds
  // Compute the corresponding value for the low resolution timer
  float secduration = *((float *) (client.read_buffer+rb));
  duration = secduration/0.032768; // time resolution 0.5e-6*2**16
  client.snd((uint8_t*) &duration, 2);
  // Reset the timer
  START_TIMER;
  timeHB=0;
  TCNT1=0;
  // Clear the interrupt vectors
  CLEARINT;
  // Enable interrupt handling
  ENABLEINT;
}

void stop(){
  // Disable interrupts
  DISABLEINT;
  STOP_TIMER;
  // Send the end packet
  uint16_t timeLB = TCNT1;
  client.write_buffer[client.we++] = 'b';
  client.write_buffer[client.we++] = 0x00;
  client.write_buffer[client.we++] = 5;
  client.write_buffer[client.we++] = ((char*) &timeLB)[0];
  client.write_buffer[client.we++] = ((char*) &timeLB)[1];
  client.write_buffer[client.we++] = ((char*) &timeHB)[0];
  client.write_buffer[client.we++] = ((char*) &timeHB)[1];
  client.write_buffer[client.we++] = 255;
  // Reset duration
  duration = 0;
}

void get_clock_calibration(uint8_t rb){
  float calibration_constant = eeprom_read_float((float*)0);
  //EEPROM.get(0, calibration_constant);
  client.snd((uint8_t*) &calibration_constant, 4, STATUS_OK);
}

void set_clock_calibration(uint8_t rb){
  float calibration_constant = 2e6;
  client.readn(&rb, (uint8_t*) &calibration_constant, 4);
  eeprom_write_float((float*)0, calibration_constant);
  //EEPROM.put(0, calibration_constant);
  client.sndstatus(STATUS_OK);
}


void read_adc(uint8_t rb){
  uint8_t channel = *((uint8_t *) (client.read_buffer + rb));
  // ADCSRA reference:
  // ADEN-ADSC-ADATE-ADIF-ADIE-ADPS2-ADPS1-ADPS0
  
  // Configure ADMUX: Internal 1.1V reference, right-adjusted result, select channel
  ADMUX = _BV(REFS1) | _BV(REFS0) | (channel & 0x0F);

  // Start first conversion
  ADCSRA |= (1 << ADSC);

  // Wait for conversion to complete
  while(ADCSRA & _BV(ADSC));// ADSC is cleared when conversion finishes

  // Read ADC result (read ADCL first, then ADCH)
  uint16_t result = ADCL; // Read low byte first
  result += (ADCH<<8); // Read high byte and combine
  
  client.snd((uint8_t *) &result, 2, STATUS_OK);
}

/** The mcu signature contains calibration constants for the MCU temperature sensor
 */
void read_signature_row(uint8_t rb) {
    uint8_t result;
    uint16_t address;
    client.readn(&rb, (uint8_t*) &address, 2);
    
    // Disable interrupts to ensure atomic operation
    cli();

    // Wait for any ongoing SPM/EEPROM operations to complete
    while (SPMCSR & (1 << SPMEN));

    // Set SIGRD and SPMEN to enable signature row read
    SPMCSR = (1 << SIGRD) | (1 << SPMEN);
    
    // Load the address into Z register (R31:R30) and read using LPM
    asm volatile("lpm %1, Z" "\n\t"    // Read byte from program memory at Z into result
		 : "=r" (result)        // Output: result
		 : "z" (address)   // Input: address (shifted left by 1 for word addressing)
		 );

    // Clear SPMCSR
    SPMCSR = 0;

    // Re-enable interrupts
    sei();

    client.snd(&result, 1, STATUS_OK);
}

 
int main(void) {
  setup();
  client.serve_serial();
}
