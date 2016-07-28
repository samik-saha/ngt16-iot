## This script handle all user interaction and display

from RPLCD import CharLCD
from gpiozero import MotionSensor
import RPi.GPIO as GPIO
import time
import urllib, httplib
import json
import threading

# ========== Global variables ==========================
meeting_room_id = 100
server = 'runnerp13.codenvycorp.com:50456'
motion_detected_time = time.time()
meeting_room_state = 'free'
default_cancel_dur = 10 #minutes
default_cancel_pause_dur = 15 #minutes
# ======================================================


# ==========  Setup sensors ============================

# Set GPIO mode to BOARD (numbering by position)
GPIO.setmode(GPIO.BOARD)

# Setup LCD pins
lcd = CharLCD(pin_rs=26, pin_e=24,
              pins_data=[22, 18, 16, 12],
              numbering_mode=GPIO.BOARD)
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


# Setup motion sensor
pir = MotionSensor(4) # BCM mode pin

# ===========================================================


# Function to read nKeys no. of keys
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


# Read motion sensor data
def read_motion_sensor():
    global motion_detected_time
    while True:
        time.sleep (1)
        if pir.motion_detected:
            motion_detected_time=time.time()
            print("Motion detected!")
            time.sleep(30)
            # TODO Post data to server\
        else:
            no_motion_duration = time.time()- motion_detected_time
            if (no_motion_duration > 60 * default_cancel_pause_dur and meeting_room_state == 'break')\
                or (no_motion_duration > 60 * default_cancel_dur and meeting_room_state == 'active'):
                # TODO Send end req
                print ('Meeting will be ended by system')

            elif no_motion_duration > 60 * default_cancel_dur and meeting_room_state == 'booked':
                # TODO Send cancel req
                print ('The meeting will be cancelled')


# Activates a meeting room on valid user key
def activate_room(passcode):
    global meeting_room_state
    while True:
        print ('---------------------')                                                                                      
        print ('|Enter passcode:     |')                                                                                     
        print ('|                    |')                                                                                     
        print ('|                    |')                                                                                     
        print ('|                    |')                                                                                     
        print ('---------------------')
        # input_passcode = raw_input('Enter passcode: ')
        lcd.write_string('Enter passcode: ')
        input_passcode = read_keys(4)
        time.sleep(1)
        lcd.clear()
        lcd.write_string('Verifying... Please wait.')
        time.sleep(1)
        lcd.clear()
        if passcode == input_passcode:
            meeting_room_state = 'active'
            print ('---------------------')                                                                                  
            print ('|Meeting in Progress |')                                                                                 
            print ('|To end press "C"    |')                                                                                 
            print ('|For 15 min break    |')                                                                                 
            print ('|press "B"           |')
            print ('---------------------')
            lcd.write_string('Meeting in Progress')
            lcd.cursor_pos=(1,0)
            lcd.write_string('To end press "C"')
            lcd.cursor_pos=(2,0)
            lcd.write_string('For 15 min break press B')
            handle_user_options()
            break
    
        else:
            print ('---------------------')                                                                                  
            print ('|Invalid passcode!   |')                                                                                 
            print ('|Please try again.   |')                                                                                 
            print ('|                    |')                                                                                 
            print ('|                    |')                                                                                 
            print ('---------------------')
            lcd.write_string ('Invalid passcode. Please try again')
            time.sleep(2)  # wait for two seconds


# Handle Pause/Resume/End user inputs
def handle_user_options():
    global meeting_room_state
    while True:
        option = raw_input('Enter option:')
        if option == 'D':
            print 'meeting paused by user'
            meeting_room_state='break'
        elif option == 'C':
            print 'meeting ended by user'
            break


# Get a lock for user interface thread to run synchronously
threadLock = threading.Lock()


# Requests server for meeting details at the current time
def get_meeting_details():
    meeting_data = urllib.urlencode({
        'meetingroom_id':meeting_room_id,
        'action':'meeting_details'
    })

    h = httplib.HTTPConnection(server)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    # Request current meeting details from server
    h.request('POST', '/meeting_room', meeting_data, headers)
    r = h.getresponse()
    s = r.read()
    print s # Response format: {"booked": "yes", "meeting_id": "1001234" }
    meeting_details = json.loads(s)
    
    return meeting_details


# At a regular interval (1 min) calls the get_meeting_details method
# and if a meeting is booked starts the UserInterface Thread.
class BookingMonitorThread (threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.meeting_id = 0
        self.userInterfaceThread = None

    def run(self):
        global meeting_room_state

        print "Starting " + self.name
        while True:
            meeting_details=get_meeting_details()
            if meeting_details['booked'] == 'yes':
                # Check if meeting_id has changed
                if self.meeting_id != meeting_details['meeting_id']:
                    self.meeting_id = meeting_details['meeting_id']
                    meeting_room_state='booked'
                    # Check if a user interface thread is running
                    if self.userInterfaceThread is not None and self.userInterfaceThread.isAlive():
                        print 'User Interface Thread already running'
                    else:
                        # Set pass code as last 4 digits of meeting id
                        passcode = meeting_details['meeting_id'][-4:]
                        self.userInterfaceThread = UserInterfaceThread('UserInterface Thread', passcode)
                        self.userInterfaceThread.start()
                else:
                    print 'Current meeting in progress'
            
            # Wait for 1 minute before checking again      
            time.sleep(10)
            
        print "Exiting " + self.name


# Shows messages to the user and waits for input
class UserInterfaceThread (threading.Thread):
    def __init__(self, threadName, passcode):
        threading.Thread.__init__(self)
        self.passcode = passcode
        self.name=threadName
        
    def run(self):
        print "Starting " + self.name
        if threadLock.acquire(0) != 0:
            print 'Calling activate_room'
            activate_room(self.passcode)
        else:
            print 'could not acquire lock'
        
        print "Exiting " + self.name
        threadLock.release()


# Reads motion sensor data continuously and takes action
class MotionSensorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        read_motion_sensor()


bookingMonitorThread = BookingMonitorThread('BookingMonitor Thread')
bookingMonitorThread.start()

motionSensorThread = MotionSensorThread()
motionSensorThread.start()

