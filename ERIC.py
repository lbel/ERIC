import serial, time
#from kivy.logger import Logger
#log = Logger

SERIAL_BAUD_RATE = 57600
START_BYTE = b'\x02'
END_BYTE   = b'\x03'

import ConfigParser
config = ConfigParser.ConfigParser()


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

class UnitUniverse:
    def __init__(self, config_file):
        self.parseConfig(config_file)

    def parseConfig(self, config_file):
        config.read(config_file)

        self.port = config.get('common', 'port', 'COM20')
        self.connect(self.port)

        devicenames = map(lambda x:x.strip(), config.get('common', 'devices').split(','))
        self.devices = []
        for device in devicenames:
            self.devices.append(Unit(device, int(config.get(device,'ardaddr'),0), self.arduino))

    def connect(self, port, timeout = 0.1):
        self.arduino = serial.Serial(port, SERIAL_BAUD_RATE, timeout = timeout)
        time.sleep(2)

    def getDevice(self, name):
        return self.devices[name]

commands = {
    'status': b'\x0b',
    'open': b'\x0c',
    'close': b'\x0d',
    'hack': b'\x0e'
}


class Unit:
    def __init__(self, title, address, arduino):
        self.title = title
        self.address = address
        self.arduino = arduino
        self.statuscode = None
        self.notfoundcounter = 0
        self.readConfig()
        self.hacklist = []
        self.timer = None
        self.ishacking = None
        self.data = [0,0,0]
        
    def readConfig(self):
        self.actions = {}
        for key in commands:
            if config.has_option(self.title, key):
                for level in [x.strip() for x in config.get(self.title, key).split(',')]:
                    self.actions[level] = key

    def what_happens(self, player):
        possibleactions = [key for value, key in self.actions.items() if value in player.skills]
        if 'open' in possibleactions:
            self.ishacking = None
            self.data = [0,200,0]
            return 'open'

        if 'hack' in possibleactions:
            if player.name in self.hacklist:
                self.ishacking = None
                self.data = [0,200,0]
                return 'open'
            else:
                if player.name == self.ishacking:
                    # timer loopt al
                    delta = time.time() - self.timer
                    self.set_keystone_led(delta)
                    print('Player ',player.name,' is now hacking for ',delta,'seconds')

                    if delta > 300:
                        self.hacklist.append(player.name)
                        self.ishacking = None
                        self.data = [200,200,200]
                        return 'open'
                else:
                    # star timer
                    self.timer = time.time()					
                    self.ishacking = player.name
                    self.data = [200,100,150]
                    #log.info('[ERIC run log: %f] Player %s started hacking',time.time(),player.name)
                    print('At ',time.time(),': Player ',player.name,' started hacking')
                    return 'hack'
                return 'hack'

        if 'close' in possibleactions:
            self.ishacking = None
            return 'close'

        return None

    def get_status(self):
        command = commands['status']
        self.send_command(command)
        newstatuscode = self.read_response()

        if not newstatuscode and self.statuscode:
            self.notfoundcounter += 1
            if self.notfoundcounter > 5:
                self.statuscode = None
                return None
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

    def set_keystone_led(self, timebase):
        if timebase < 100:
            fadespeed = 5
        elif timebase < 200:
            fadespeed = 10
        else:
            fadespeed = 15

        for x in xrange(0,len(self.data)-1):
            self.data[x] = self.data[x] + fadespeed
            if (self.data[x] > 200):
                self.data[x] = fadespeed


class Player:
    def __init__(self, name):
        self.name = name
        self.rfid = config.getint('spelers', name)
        self.skills = [x.strip() for x in config.get('skills', name).split(',')]


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
        if rfid in self.rfidmap:
            return self.rfidmap[rfid]
        return None

    def find_action_for_rfid_at_unit(self, rfid, u):
        player = self.find_player_for_rfid(rfid)
        if not player:
            u.ishacking = None
            return None

        action = u.what_happens(player)
        return action


def main():
    units = UnitUniverse('ericconfig.txt')#[Unit(b'\x0b', arduino), Unit(b'\x0f', arduino)]
    players = Players()

    previousactions = {}

    while True:
        for unit in units.devices:
            status = unit.get_status()
            if unit.title in previousactions:
                previousaction = previousactions[unit.title]
            else:
                previousaction = None

            action = players.find_action_for_rfid_at_unit(status, unit)
            confirm = unit.do_action(action)
            
            if action != previousaction:
                print(action)
                # state change! Yay!

                previousactions[unit.title] = action

                # do coole dingen met deze state change
                # if action == 'hack':
                #     oscar.call('/start/%s.open' % (unit.title))

if __name__ == '__main__':
    main()
