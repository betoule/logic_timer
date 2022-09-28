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

#include <Arduino.h>
#include "bincoms.h"


#if defined(ARDUINO_AVR_MEGA2560)
#define ENABLEINT EIMSK |= _BV(INT5) | _BV(INT4) | _BV(INT3)
#define DISABLEINT EIMSK &= (~(_BV(INT5)) & (~_BV(INT4)) & (~_BV(INT3)))
#define CLEARINT EIFR |= _BV(INTF5) | _BV(INTF4) | _BV(INTF3)
#elif defined(ARDUINO_AVR_PRO)
#define ENABLEINT EIMSK |= _BV(INT1) | _BV(INT0)
#define DISABLEINT EIMSK &= (~(_BV(INT1)) & (~_BV(INT0)))
#define CLEARINT EIFR |= _BV(INTF1) | _BV(INTF0)
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

uint16_t duration;
uint16_t timeHB;

const uint8_t NFUNC = 2+1;
uint8_t narg[NFUNC];
// The exposed functions
void (*func[NFUNC])(uint8_t rb) =
  {// Communication protocol
   command_count,
   get_command_names,
   // user defined
   start,
  };

const char* command_names[NFUNC*3] =
  {"command_count", "", "B",
   "get_command_names", "BB", "s",
   // user defined
   "start", "f", "H",
  };


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
  PORTE  = 0b11111111;
  PCMSK0 = 0b00000000;  
  // Setup external interrupt rise for arduino pin 2 and 3 (PE4 and PE5)
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
  TCCR1B = 0b00000010;
  TIMSK1 = 0b00000001;

  // We disable the awful clock of the arduino IDE
  TCCR0B = 0b0;
  TIMSK0 = 0b0;
  TCCR2B = 0b0;
  TIMSK2 = 0b0;
  EIMSK = 0b0;
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

void loop(){
  client.serve_serial();
}

void start(uint8_t rb){
  // We receive the duration as a floating point in seconds
  // Compute the corresponding value for the low resolution timer
  float secduration = *((float *) (client.read_buffer+rb));
  duration = secduration/0.032768; // time resolution 0.5e-6*2**16
  client.snd((uint8_t*) &duration, 2);
  // Reset the timer
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

