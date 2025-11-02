# === CONFIG ===
#MCU       = atmega328p
MCU       = atmega2560
F_CPU     = 16000000
PORT      = /dev/ttyACM0  # Linux/macOS: ls /dev/tty* | grep ACM
# PORT    = COM3          # Windows
BAUD      = 115200
#PROGRAMMER = arduino      # or wiring, stk500v1
PROGRAMMER = wiring      # or wiring, stk500v1

# === TOOLS ===
CC      = avr-g++
OBJCOPY = avr-objcopy
AVRDUDE = avrdude

# === FILES ===
TARGET  = main
SOURCES = main.cpp bincoms.cpp
OBJECTS = $(SOURCES:.cpp=.o)

# === FLAGS ===
CFLAGS = -Os -g -mmcu=$(MCU) -DF_CPU=$(F_CPU)UL -Wall -DARDUINO_AVR_MEGA2560
LDFLAGS = -mmcu=$(MCU)

# === RULES ===
all: $(TARGET).hex

$(TARGET).elf: $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $^

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

%.o: %.cpp
	$(CC) $(CFLAGS) -c $< -o $@

flash: $(TARGET).hex
	$(AVRDUDE) -F -V -c$(PROGRAMMER) -p$(MCU) -P $(PORT) -b$(BAUD) -U flash:w:$<

clean:
	rm -f $(TARGET).elf $(TARGET).hex *.o

.PHONY: all flash clean
