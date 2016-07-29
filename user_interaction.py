## This script handle all user interaction and display

from RPLCD import CharLCD
from gpiozero import MotionSensor
import RPi.GPIO as GPIO
import time
import urllib, httplib
import json
import threading
import xml.etree.ElementTree as ET

# ========== Global variables ==========================
enable_motion_sensor = True
enable_sound_sensor = True
meeting_room_id = 1
meeting_booking_id = 0
meeting_start_time = time.time()
meeting_end_time='00:00:00'
server = 'pc190961:80'
motion_detected_time = time.time()
meeting_room_state = 'free'
default_cancel_dur = 1 #minutes
default_cancel_pause_dur = 1.5 #minutes
kill_ui_thread=0
headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
# ======================================================
h = httplib.HTTPConnection(server)

# ==========  Setup sensors ============================

# Set GPIO mode to BOARD (numbering by position)
#print GPIO.BCM
#print GPIO.getmode()
GPIO.setmode(GPIO.BCM)

# Setup LCD pins
lcd = CharLCD(pin_rs=7, pin_e=8,
              pins_data=[25, 24, 23, 18],
              numbering_mode=GPIO.BCM)
lcd.clear()

# Setup Keypad pins
MATRIX = [[1, 2, 3, 'A'],
          [4, 5, 6, 'B'],
          [7, 8, 9, 'C'],
          ['*', 0, '#', 'D']]
ROW = [10, 9, 11, 5]
COL = [6, 13, 19, 26]

for j in range(4):
    GPIO.setup(COL[j], GPIO.OUT)
    GPIO.output(COL[j], 1)

for i in range(4):
    GPIO.setup(ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)


# Setup motion sensor
pir = MotionSensor(4) # BCM mode pin

# Setup sound sensor
GPIO.setup(17, GPIO.IN)

# ===========================================================


# Function to read nKeys no. of keys
def read_keys(nKeys):
    n = 0
    input_value = ''
    global kill_ui_thread

    try:
        while (True):
            if kill_ui_thread == 1:
                break
            for j in range(4):
                GPIO.output(COL[j], 0)
                for i in range(4):
                    if GPIO.input(ROW[i]) == 0:
                        input_char = str(MATRIX[i][j])
                        input_value = input_value + input_char
                        n += 1
                        print input_char
                        lcd.write_string(input_char)
                        while GPIO.input(ROW[i]) == 0:
                            pass
                GPIO.output(COL[j], 1)
            if (n >= nKeys):
                break

    except KeyboardInterrupt:
        GPIO.cleanup()

    return input_value


# Read motion sensor data
def read_sensor():
    global motion_detected_time
    global meeting_room_state
    global kill_ui_thread

    while True:
        time.sleep(1)
        if (enable_motion_sensor == True and pir.motion_detected) or\
            (enable_sound_sensor == True and GPIO.input(17) == GPIO.LOW):
            motion_detected_time=time.time()
            print(time.strftime('%H:%M:%S')+ '| Presence detected!')
            time.sleep(1)
            # TODO Post data to server\
        else:
            no_motion_duration = time.time()- motion_detected_time
            if (no_motion_duration > 60 * default_cancel_pause_dur and meeting_room_state == 'break')\
                or (no_motion_duration > 60 * default_cancel_dur and meeting_room_state == 'active'):
                kill_ui_thread = 1
                meeting_room_state = 'free'
                # TODO Send end req
                print ('Meeting will be ended by system')

                # ================= Post data to server ===============
                params = urllib.urlencode({
                    'meeting_booking_id': meeting_booking_id
                })
                h4 = httplib.HTTPConnection(server)
                h4.request('POST', '/NgtIotMetRockers/WebService.asmx/end_meeting', params, headers)
                r = h4.getresponse()



# Activates a meeting room on valid user key
def activate_room(passcode):
    global meeting_room_state
    global meeting_end_time
    while True:
        print ('---------------------')                                                                                      
        print ('|Enter passcode:     |')                                                                                     
        print ('|                    |')                                                                                     
        print ('|                    |')                                                                                     
        print ('|                    |')                                                                                     
        print ('---------------------')
        # input_passcode = raw_input('Enter passcode: ')
        lcd.clear()
        lcd.write_string('Enter passcode: ')
        input_passcode = read_keys(4)
        time.sleep(1)
        lcd.clear()
        if len(input_passcode) < 4:
            lcd.clear()
            lcd.write_string('Meeting room is available for booking')
            time.sleep(10)
            break
        elif passcode == input_passcode:
            meeting_room_state = 'active'
            print ('---------------------')
            print ('|Meeting in Progress |')
            lcd.write_string('Meeting in Progress')

            params = urllib.urlencode({
                'meeting_booking_id': meeting_booking_id
            })
            h2 = httplib.HTTPConnection(server)
            h2.request('POST', '/NgtIotMetRockers/WebService.asmx/activate_meeting', params, headers)
            r = h2.getresponse()
            s = r.read()
            root = ET.fromstring(s)
            for child in root:
                if child.tag == '{http://tempuri.org/}End_Time':
                    meeting_end_time = child.text

            print ('|To end: press "C"   |')
            print ('|For break: press "B"|')
            print ('|End Time: ' + meeting_end_time + '  |')
            print ('---------------------')

            lcd.cursor_pos=(1,0)
            lcd.write_string('To end: press "C"')
            lcd.cursor_pos=(2,0)
            lcd.write_string('For break: press "B"')
            lcd.cursor_pos=(3,0)
            lcd.write_string('End Time: ' + meeting_end_time)
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
        #option = raw_input('Enter option:')
        option = read_keys(1)
        if option == '':
            lcd.clear()
            lcd.write_string('Meeting room is available for booking')
            break
        elif option == 'B':
            print 'meeting paused by user'
            lcd.clear()
            lcd.write_string('On Break for 15 min')
            lcd.cursor_pos = (1,0)
            lcd.write_string('To Continue')
            lcd.cursor_pos = (2, 0)
            lcd.write_string('Press "D"')
            meeting_room_state = 'break'
        elif option == 'C':
            print 'meeting ended by user'
            lcd.clear()
            lcd.write_string('Meeting ended at '+time.strftime('%H:%M'))

            # ================= Post data to server ===============
            params = urllib.urlencode({
                'meeting_booking_id': meeting_booking_id
            })
            h.request('POST', '/NgtIotMetRockers/WebService.asmx/end_meeting', params, headers)
            r = h.getresponse()

            time.sleep(10)
            lcd.clear()
            lcd.write_string('Meeting room is available for booking')
            break
        elif option == 'D':
            print ('---------------------')
            print ('|Meeting in Progress   |')
            print ('|To end: press "C"   |')
            print ('|For break: press "B"|')
            print ('|End Time: ' + meeting_end_time + '  |')
            print ('---------------------')
            lcd.clear()
            lcd.write_string('Meeting in Progress')
            lcd.cursor_pos = (1, 0)
            lcd.write_string('To end: press "C"')
            lcd.cursor_pos = (2, 0)
            lcd.write_string('For break: press "B"')
            lcd.cursor_pos = (3, 0)
            lcd.write_string('End Time: ' + meeting_end_time)


# Get a lock for user interface thread to run synchronously
threadLock = threading.Lock()


# Requests server for meeting details at the current time
def get_meeting_details():
    global meeting_booking_id
    meeting_data = urllib.urlencode({
        'meeting_room_id':meeting_room_id
    })
    # Request current meeting details from server
    h1 = httplib.HTTPConnection(server)
    h1.request('POST', '/NgtIotMetRockers/WebService.asmx/check_availability', meeting_data, headers)
    time.sleep(1)
    r = h1.getresponse()
    s = r.read()
    root = ET.fromstring(s)
    meeting_details={};
    for child in root:
        if child.tag == '{http://tempuri.org/}Booked':
            meeting_details['booked']=child.text
            print 'booked: '+child.text
        elif child.tag == '{http://tempuri.org/}meeting_booking_id':
            meeting_details['meeting_id']=child.text
            meeting_booking_id = child.text
            print 'meeting_id: '+child.text
        elif child.tag == '{http://tempuri.org/}next_meeting_start_time':
            meeting_details['next_meeting'] = child.text
            print 'Next meeting: ' + child.text
    #meeting_details = json.loads('{"booked":"yes","meeting_id":"1001234"}')
    
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
        global kill_ui_thread
        global motion_detected_time
        global meeting_start_time

        print "Starting " + self.name
        while True:
            meeting_details=get_meeting_details()
            if meeting_details['booked'] == 'Yes':
                # Check if meeting_id has changed
                if self.meeting_id != meeting_details['meeting_id']:
                    self.meeting_id = meeting_details['meeting_id']
                    meeting_room_state='booked'
                    motion_detected_time = time.time()
                    meeting_start_time=time.time()
                    # Check if a user interface thread is running
                    if self.userInterfaceThread is not None and self.userInterfaceThread.isAlive():
                        print 'User Interface Thread already running'
                        kill_ui_thread=1
                        time.sleep(2)

                    # Set pass code as last 4 digits of meeting id
                    passcode = meeting_details['meeting_id'][-4:]
                    kill_ui_thread=0
                    self.userInterfaceThread = UserInterfaceThread('UserInterface Thread', passcode)
                    self.userInterfaceThread.start()
                else:
                    if (time.time() - meeting_start_time > default_cancel_dur*60) and (meeting_room_state == 'booked'):
                        kill_ui_thread = 1
                        meeting_room_state = 'free'
                        # TODO Send cancel req
                        print ('The meeting will be cancelled')

                        # ================= Post data to server ===============
                        params = urllib.urlencode({
                            'meeting_booking_id': meeting_booking_id
                        })
                        h3 = httplib.HTTPConnection(server)
                        h3.request('POST', '/NgtIotMetRockers/WebService.asmx/cancel_meeting', params, headers)
                        r = h3.getresponse()
                    print time.strftime('%H:%M:%S') +'| Current meeting in progress'
            else:
                if self.userInterfaceThread is not None and self.userInterfaceThread.isAlive():
                    kill_ui_thread = 1
                time.sleep (2)
                if meeting_details['next_meeting'] != '0':
                    lcd.clear()
                    lcd.write_string('Meeting room is available for booking')
                    lcd.cursor_pos = (3,0)
                    lcd.write_string('Next meeting: '+meeting_details['next_meeting'][0:5])
                else:
                    lcd.clear()
                    lcd.write_string('Meeting room is available for booking')

                print time.strftime('%H:%M:%S') + '| Meeting room is available '


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
        global meeting_booking_id
        print "Starting " + self.name
        if threadLock.acquire(0) != 0:
            print 'Calling activate_room'
            activate_room(self.passcode)
            threadLock.release()
        else:
            print 'could not acquire lock'
        
        print "Exiting " + self.name
        meeting_booking_id = 0


# Reads motion sensor data continuously and takes action
class MotionSensorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        read_sensor()

lcd.clear()
lcd.write_string('Meeting room is available for booking')

bookingMonitorThread = BookingMonitorThread('BookingMonitor Thread')
bookingMonitorThread.start()

motionSensorThread = MotionSensorThread()
motionSensorThread.start()

