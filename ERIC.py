import serial, time
#from kivy.logger import Logger
#log = Logger
import urllib2
import ConfigParser
config = ConfigParser.ConfigParser()

from event import Event

def send_to_oscar(name):
    pass
    #urllib2.urlopen('http://localhost:5011/press/%s' % (name))
    
SERIAL_BAUD_RATE = 57600
START_BYTE = b'\x02'
END_BYTE   = b'\x03'

def parse_status_response(data):
    i = 0
    crc = 0
    tag = 0
    startFound = False
    endFound = False
    value = 0

    while (i < 8):
        dataByte = data[i]

        if dataByte == START_BYTE:
            startIndex = i
            startFound = True

        elif ((dataByte == END_BYTE) and (endFound == False)):
            endFound = True

        else:
            if (startFound == True) and (endFound == False):
                crc ^= ord(dataByte)
                if (i >= (startIndex + 2)):
                    value = value << 8
                    value ^= ord(dataByte)

            if endFound == True:
                checksum = ord(dataByte)
                if checksum == crc:
                    return value
                else:
                    return 0

        i = i + 1
    return 0

class Actuator:
    def __init__(self, title):
        self.title = title
        self.actions = {}
        self.readConfig()
        
    def readConfig(self):
        for key in commands:
            if config.has_option(self.title, key):
                for level in [x.strip() for x in config.get(self.title, key).split(',')]:
                    self.actions[key] = level
        
    def tell_oscar(self, action_name):
        if self.hardware:
            self.hardware.do_action(action_name)
        else:
            for action in self.actions[action_name]:
                send_to_oscar(action)
    
    
class ArdUniverse:
    def __init__(self, config_file):
        self.parseConfig(config_file)

    def parseConfig(self, config_file):
        config.read(config_file)

        self.port = config.get('common', 'ard_port', 'COM20')
        self.connect(self.port)

        roomnames = map(lambda x:x.strip(), config.get('common', 'ard_rooms').split(','))
        self.rooms = {}
        devices_dict = {}

        for room in roomnames:
            devicenames = map(lambda x:x.strip(), config.get(room, 'devices').split(','))
            devices = []
            events = []
            for device in devicenames:
                if room == 'actors':
                    actuator = Actuator(device)
                    devices.append(actuator)
                    devices_dict[device] = actuator
                elif room == 'sensors':
                    sensor = Sensor(device, int(config.get(device,'ardaddr'),0), self.arduino, map(lambda x:x.strip(), config.get(device, 'events').split(',')))
                    devices.append(sensor)
                    devices_dict[device] = sensor
                elif room == 'events':
                    actors =  map(lambda x: devices_dict[x.strip()], config.get(device,'actors').split(','))
                    actions = {}
                    for item in config.items(device):
                        actions[item[0]] = item[1]
                    event = Event(config.get(device,'event_id'), actions, actors)
                    events.append(event)
                    devices_dict[device] = event
            self.rooms[room] = ArdRooms(room, devices)
        
        
        for sensor in self.rooms['sensors'].devices:
            event_names = sensor.events
            sensor.events = []
            for event_name in event_names:
                sensor.events.append(devices_dict[event_name])
        
        # TEMPORARY PATCH
        for actor in self.rooms['actors'].devices:
            sensor_name = None
            actor.hardware = None
            if config.has_option(actor.title,'hardware'):
                sensor_name = config.get(actor.title,'hardware')
            for sensor in self.rooms['sensors'].devices:
                if sensor_name == sensor.title:
                    actor.hardware = sensor   
        

    def connect(self, port, timeout = 0.1):
        self.arduino = serial.Serial(port, SERIAL_BAUD_RATE, timeout = timeout)
        time.sleep(2)

        
class ArdRooms:
    def __init__(self, title, devices):
        self.title = title
        self.devices = devices
        
    def get_number_of_devices(self):
        return len(self.devices)
        
    def get_device_status(self, title):
        return self.devices[title].statuscode
        
commands = {
    'status': b'\x0b',
    'open': b'\x0c',
    'sluit': b'\x0d',
    'hack': b'\x0e'
}

wildcards = ['wildcard1', 'wildcard2', 'wildcard3', 'wildcard4']

class Sensor:
    def __init__(self, title, address, arduino, events):
        self.title = title
        self.address = address
        self.arduino = arduino
        self.events = events
        self.statuscode = None
        self.notfoundcounter = 0
        self.hacklist = []
        self.timer = None
        self.ishacking = None
        self.data = [0,0,0]

    def get_status(self):
        command = commands['status']
        self.send_command(command)
        newstatuscode = self.read_response()

        if newstatuscode != self.statuscode:
            self.notfoundcounter += 1
            if self.notfoundcounter > 5:
                self.statuscode = newstatuscode
                return newstatuscode
            return self.statuscode

        if newstatuscode:
            self.statuscode = newstatuscode
            self.notfoundcounter = 0

            return self.statuscode

        return None

    def do_action(self, action):
        if not action:
            action = None

        if action in commands:
            command = commands[action]
            self.send_command(command)
            return self.wait_for_confirm()

    def send_command(self, command):
        crc = (self.address ^ ord(command) ^ self.data[0] ^ self.data[1] ^ self.data[2])
        n = self.arduino.write(self.format_msg(self.address, command, self.data[0], self.data[1], self.data[2], crc))

    def format_msg(self, address, command, data0, data1, data2, data3):
        return b''.join([START_BYTE, chr(address), command, chr(data0), chr(data1), chr(data2), END_BYTE, chr(data3)])

    def wait_for_confirm(self):
        return self.read_response()

    def read_response(self):
        time.sleep(.000001)
        if self.arduino.readable():
            data = self.arduino.readline()
            if not data:
                return None
            else:
                retValue = parse_status_response(data)
                return retValue
                

class Player:
    def __init__(self, name):
        self.name = name
        self.rfid = config.getint('spelers', name)
        self.skills = [x.strip() for x in config.get('skills', name).split(',')]
    
    def add_skill(self, new_skill):
        for skill_name in wildcards:
            if skill_name in self.skills:
                self.skills.remove(skill_name)
        self.skills.append(new_skill)


class Players:
    def __init__(self):
        self.load_players()

    def load_players(self):
        self.players = []
        self.rfidmap = {}
        playernames = [x.strip() for x in config.get('common','spelers').split(',')]
        for playername in playernames:
            player = Player(playername)
            self.players.append(player)
            self.rfidmap[player.rfid] = player

    def find_player_for_rfid(self, rfid):	
        return self.rfidmap.get(rfid,None)

        
active_events = set()
        
def main():
    ardUniverse = ArdUniverse('ericconfig.txt')
    players = Players()

    while True:
        for sensor in ardUniverse.rooms['sensors'].devices:
            status = sensor.get_status()
            # if status:
                # print(status)
            player = players.find_player_for_rfid(status)
            for event in sensor.events:
                handle_event(event, player, sensor)
            

def handle_event(event, player, sensor):
    is_active = event.eventID in active_events
    running = False
    if is_active:
        if event.active_sensor == sensor and player != event.current_player and event.is_hacking:
            print(event.active_sensor)
            print(event.current_player)
            print(player)
            print("Stopping the Hack")
            event.stop_hack()
        
        running = event.tick()
        if not running:
            active_events.remove(event.eventID)
    else:
        if player:
            print(set(player.skills).intersection(event.actions))
            if bool(set(player.skills).intersection(event.actions)):
                event.start(player, sensor)
                active_events.add(event.eventID)
            else:
                sensor.data = [100,0,0]
                sensor.do_action('sluit')
        
        
if __name__ == '__main__':
    main()
