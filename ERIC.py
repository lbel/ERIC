#from kivy.logger import Logger
#log = Logger
import ConfigParser
config = ConfigParser.ConfigParser()

from device import Actuator, Sensor
from event import Event
from hardware import HardwareInterface, OscarInterface, ArduinoInterface, TestActuator, TestSensor
from player import Players
from serial_pool import SerialPool

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
            if __debug__:
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

active_events = set()
serial_pool = SerialPool()

def main():
    ardUniverse = ArdUniverse('ericconfig.txt')
    ardUniverse.connect_all()

    players = Players(config)

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
