# This script handle all user interaction and display
meeting_room_id = 100

from RPLCD import CharLCD
import RPi.GPIO as GPIO
import time
import urllib, urllib2

GPIO.setmode(GPIO.BOARD)

# Setup LCD pins
lcd = CharLCD(pin_rs=26, pin_e=24, pins_data=[22, 18, 16, 12], numbering_mode=GPIO.BOARD)
lcd.clear()

# Setup Keypad pins
MATRIX = [[1, 2, 3, 'A'],
          [4, 5, 6, 'B'],
          [7, 8, 9, 'C'],
          ['*', 0, '#', 'D']]
ROW = [19, 21, 23, 29]
COL = [31, 33, 35, 37]

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
                        input_value = input_value + input_char
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

    return input_value


url = 'http://runnerp11.codenvycorp.com:62744/meeting_room'
data = ({
    'meetingroom_id': '100'
})


def activate_room(passcode):
    lcd.write_string('Enter passcode: ')
    input_passcode = read_keys(4)
    time.sleep(1)
    lcd.clear()
    lcd.write_string('Verifying... Please wait.')
    time.sleep(1)
    lcd.clear()
    if passcode == input_passcode:
        lcd.write_string('Meeting in Progress')
        lcd.cursor_pos=(2,0)
        lcd.write_string('For 10 min break press B')
    else:
        lcd.write_string ('Invalid passcode. Please try again')
        return False

    return True


activate_room('1234')