# This script handle all user interaction and display
meeting_room_id=100

from RPLCD import CharLCD, BacklightMode
import RPi.GPIO as GPIO

#Setup LCD pins
lcd = CharLCD(pin_rs=26, pin_e=24, pins_data=[22, 18, 16, 12])

# Setup Keypad pins 
GPIO.setmode(GPIO.BOARD)
MATRIX = [ [1,2,3,'A'],
           [4,5,6,'B'],
           [7,8,9,'C'],
           ['*',0,'#','D'] ]
ROW = [19,21,23,29]
COL = [31,33,35,37]

for j in range(4):
        GPIO.setup(COL[j], GPIO.OUT)
        GPIO.output(COL[j], 1)

for i in range(4):
        GPIO.setup(ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
def read_keys(nKeys):
    n = 0
    input_value = ""
    
    try:
        while (True):
            for j in range(4):
                GPIO.output(COL[j], 0)
                for i in range(4):
                    if GPIO.input(ROW[i]) == 0:
                        input_char = str(MATRIX[i][j])
                        input_value=input_value + input_char
                        n += 1
                        print input_char
                        lcd.write_string(input_char)
                        while (GPIO.input(ROW[i]) == 0):
                            pass
                GPIO.output(COL[j], 1)
            if (n >= nKeys):
                break

    except KeyboardInterrupt:
            GPIO.cleanup()

    GPIO.cleanup()
    return input_value


def activate_room():
    lcd.write_string("Enter passcode: ")
    passcode = read_keys(4)
    print (passcode)
    # check key with server
    # if does not match try again
