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

uint8_t buff[BUFFSIZE];
#if defined(HAVE_HWSERIAL0)
struct Com<HardwareSerial>  client(&Serial);
#else
extern struct Com<Serial_> client(&Serial);
#endif


void command_count(uint8_t rb){
  uint8_t nfunc =  NFUNC;
  client.snd(&nfunc, sizeof(uint8_t));
}

void get_command_names(uint8_t rb){
  uint8_t nfunc = client.read_buffer[rb++];
  uint8_t par = client.read_buffer[rb++];
  if (nfunc >= NFUNC)
    client.sndstatus(UNDEFINED_FUNCTION_ERROR);
  else if (par > 2)
    client.sndstatus(VALUE_ERROR);
  else
    client.sndstr(command_names[nfunc * 3 + par]);
}

void setup_bincom(){
  //Serial.begin(115200);
  Serial.begin(1000000);
  for (uint8_t i =0; i < NFUNC; i++){
    narg[i] = 0;
    for (char * c = command_names[i*3+1]; *c != 0; c++){
      switch (*c){
      case 'B':
      case 'b':
      case 'c':
	narg[i] += 1;
	break;
      case 'h':
      case 'H':
	narg[i] += 2;
	break;
      case 'i':
      case 'I':
      case 'f':
	narg[i] += 4;
	break;
      case 'd':
      case 'l':
      case 'L':
	narg[i] += 8;
	break;
      default:
	break;
      }
    }
  }
  //disable interrupt Data register empty
  UCSR0B &= ~_BV(UDRIE0);
  //disable interrupt receive complete
  UCSR0B &= ~_BV(RXCIE0);
}
