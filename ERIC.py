#from kivy.logger import Logger
#log = Logger
import ConfigParser
config = ConfigParser.ConfigParser()

from event import Event
from hardware import HardwareInterface, OscarInterface, ArduinoInterface, TestActuator, TestSensor
from serial import SerialPool

class Actuator:
    def __init__(self, title, config):
        self.title = title
        self.actions = {}
        self.__readConfig(config)

    def __readConfig(self, config):
        for key in commands:
            if config.has_option(self.title, key):
                self.actions[key] = map(str.strip, config.get(self.title, key).split(','))

    def set_hardware(self, config, sensors_dict):
        if DEBUG:
            self.__hardware = TestActuator(self.title)
        elif config.has_option(self.title, 'hardware'):
            self.__hardware = sensors_dict[config.get(self.title, 'hardware')].get_hardware()
        else:
            self.__hardware = OscarInterface('http://localhost:5011/press/{}'.format(self.title))

    def connect(self):
        return self.__hardware.connect()

    def do_action(self, action_name):
        for action in self.actions.get(action_name, []):
            self.__hardware.send(action)

class ArdUniverse:
    def __init__(self, config_file):
        self.actors = []
        self.sensors = []
        self.events = []
        self.parseConfig(config_file)

    def parseConfig(self, config_file):
        config.read(config_file)

        port = config.get('common', 'ard_port', 'COM20')

        devices_dict = {}

        actor_names = map(str.strip, config.get('actors', 'devices').split(','))
        for actor_name in actor_names:
            actor = Actuator(actor_name, config)
            self.actors.append(actor)
            devices_dict[actor_name] = actor

        sensor_names = map(str.strip, config.get('sensors', 'devices').split(','))
        for sensor_name in sensor_names:
            if DEBUG:
                hardware = TestSensor(sensor_name)
            else:
                hardware = ArduinoInterface(serial_pool, port, int(config.get(sensor_name, 'ardaddr'), 0))
            sensor = Sensor(sensor_name, hardware, map(str.strip, config.get(sensor_name, 'events').split(',')))
            self.sensors.append(sensor)
            devices_dict[sensor_name] = sensor

        event_names = map(str.strip, config.get('events', 'devices').split(','))
        for event_name in event_names:
            actors =  map(lambda x: devices_dict[x.strip()], config.get(event_name, 'actors').split(','))
            actions = {}
            for item in config.items(event_name):
                if item[0] not in ['event_id', 'actors']:
                    actions[item[0]] = item[1]
            event = Event(config.get(event_name, 'event_id'), actions, actors)
            self.events.append(event)
            devices_dict[event_name] = event

        # Connect events to sensors
        for sensor in self.sensors:
            event_names = sensor.events
            sensor.events = []
            for event_name in event_names:
                sensor.events.append(devices_dict[event_name])

        # Connect hardware to actors
        for actor in self.actors:
            actor.set_hardware(config, devices_dict)

    def connect_all(self):
        for device in self.sensors + self.actors:
            device.connect()

commands = {
    'status': b'\x0b',
    'open': b'\x0c',
    'sluit': b'\x0d',
    'hack': b'\x0e'
}

wildcards = ['wildcard1', 'wildcard2', 'wildcard3', 'wildcard4']

class Sensor:
    def __init__(self, title, hardware, events):
        self.title = title
        self.__hardware = hardware
        self.events = events
        self.statuscode = None
        self.notfoundcounter = 0
        self.data = [0,0,0]

    def get_status(self):
        command = commands['status']
        newstatuscode = self.__hardware.send(command)

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

    def get_hardware(self):
        return self.__hardware

    def connect(self):
        return self.__hardware.connect()

    def do_action(self, action):
        if not action:
            action = None

        if action in commands:
            command = commands[action]
            return self.__hardware.send(command)

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
serial_pool = SerialPool()

DEBUG = True

def main():
    ardUniverse = ArdUniverse('ericconfig.txt')
    ardUniverse.connect_all()

    players = Players()

    while True:
        for sensor in ardUniverse.sensors:
            status = sensor.get_status()
            #if status:
                #print(status)
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
