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

#ifndef __BINARYCOMMANDS_H__
#define __BINARYCOMMANDS_H__
#include <string.h>

#define BUFFSIZE 256 // Do not change that allows to use roling of uint8_t
#define STATUS_OK 0x00
#define STATUS_BUSY 0x01
#define STATUS_ERROR 0x02
#define UNDEFINED_FUNCTION_ERROR 0x03
#define BYTE_COUNT_ERROR 0x04
#define COMMUNICATION_ERROR 0X05
#define CHECKSUM_ERROR 0x06
#define VALUE_ERROR 0x07

#define SERIAL_8N1 0x06 // The default serial port config 8bit + 1sto

//#define PING PORTD |= 0b100000
//#define PONG PORTD &= ~0b100000


extern uint8_t narg[];
extern const char* command_names[];
extern void (*func[])(uint8_t rb);
extern const uint8_t NFUNC;
extern uint16_t timeHB;
extern uint16_t duration;
void stop();


struct Com{
  uint8_t write_buffer[BUFFSIZE] __attribute__ ((aligned(BUFFSIZE)));
  uint8_t read_buffer[BUFFSIZE];

  uint8_t wb, we, rb, re;
  uint8_t wait;
  bool message;
  
  Com(){
    wb = 0;
    we = 0;
    rb = 0;
    re = 0;
    wait=3;
    message=false;
  }

  void serve_serial(){
    while(1){ // Bypass slow serial polling 
      if (UCSR0A & (1 << RXC0)){ // a bit is available
	read_buffer[re++] = UDR0; //This clear RXC0
	//if (re == BUFFSIZE) re=0; //This is not necessary if BUFFSIZE==256
      }
      if ((wb != we) && ((UCSR0A & (1 << UDRE0)) != 0)){
	UDR0 = write_buffer[wb++];
	//if (wb == BUFFSIZE) wb=0; //This is not necessary if BUFFSIZE==256
      }
      uint8_t avail = re - rb;
      if (avail >= wait){
	if(message)
	  process_message();
	else
	  rcv_header();
      }
      if ((duration > 0) && (timeHB > duration))
	stop();
    }
  }

  void readn(uint8_t * rb, uint8_t * data, uint8_t n){
    for (uint8_t i=0; i < n; i++){
      data[i] = read_buffer[*rb];
      (*rb)++;
    }
  }

  void write(uint8_t octet){
    write_buffer[we++] = octet;
    //if (we == BUFFSIZE) we=0; // This is not necessary if BUFFSIZE == 256
  }
  
  void snd(uint8_t * address, uint8_t len, uint8_t status=STATUS_OK){
    write('b');
    write(status);
    write(len);
    for(int i=0; i < len; i++)
      write(address[i]);
  }


  void sndstr(const char * str){
    uint8_t len = strlen(str);
    snd((uint8_t *) str, len); 
  }

  void sndstatus(uint8_t status){
    snd(write_buffer, 0, status);
  }
  
  void rcv_header(){
    if (read_buffer[rb++] != 'b'){
      rb = re; //flushing
      sndstatus(COMMUNICATION_ERROR);
    }
    if (read_buffer[rb++] != STATUS_OK){
      rb = re; //flushing
      sndstatus(COMMUNICATION_ERROR);
    }
    uint8_t len = read_buffer[rb++];
    if (len > 0){
      wait = len;
      message = true;
    }
    else{
      sndstatus(STATUS_OK);
    }
  }

  void process_message(){
    uint8_t f = read_buffer[rb++];
    if (f >= NFUNC)
      sndstatus(UNDEFINED_FUNCTION_ERROR);
    else if (wait != 1 + narg[f])
      sndstatus(BYTE_COUNT_ERROR);
    else
      (*func[f])(rb);
    message = false;
    wait = 3;
    rb = re;
  }
  
};

// Function definition
void command_count(uint8_t rb);
void get_command_names(uint8_t rb);

void setup_bincom(long int baud=1000000);
/* These global variables need to be defined to match the needs of the application
*/
#endif
