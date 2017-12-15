from hardware import OscarInterface, TestActuator

commands = {
    'status': b'\x0b',
    'open': b'\x0c',
    'sluit': b'\x0d',
    'hack': b'\x0e'
}

class Actuator:
    def __init__(self, title, config):
        self.title = title
        self.actions = {}
        self.__readConfig(config)

    def __str__(self):
        return 'Actuator {}'.format(self.title)

    def __readConfig(self, config):
        for key in commands:
            if config.has_option(self.title, key):
                self.actions[key] = frozenset(map(str.strip, config.get(self.title, key).split(',')))

    def set_hardware(self, config, sensors_dict):
        if __debug__:
            self.__hardware = TestActuator(self.title)
        elif config.has_option(self.title, 'hardware'):
            self.__hardware = sensors_dict[config.get(self.title, 'hardware')].get_hardware()
        else:
            self.__hardware = OscarInterface('http://localhost:5011/press/{}')

    def connect(self):
        return self.__hardware.connect()

    def do_action(self, action_name, data = None):
        for action in self.actions.get(action_name, []):
            self.__hardware.send(action, data)

class Sensor:
    def __init__(self, title, hardware, events):
        self.title = title
        self.__hardware = hardware
        self.events = events
        self.statuscode = None
        self.notfoundcounter = 0

    def __str__(self):
        return 'Sensor {}'.format(self.title)

    def get_status(self):
        command = commands['status']
        newstatuscode = self.__hardware.send(command, [0, 0, 0])
        print "status = ",self.statuscode
        print "new status = ",newstatuscode
        
        if self.statuscode and newstatuscode != self.statuscode:
            self.notfoundcounter += 1
            print self.notfoundcounter
            if self.notfoundcounter > 5:
                self.statuscode = newstatuscode
                return newstatuscode
            return self.statuscode
            
        self.statuscode = newstatuscode
        self.notfoundcounter = 0
        return self.statuscode

    def get_hardware(self):
        return self.__hardware

    def connect(self):
        return self.__hardware.connect()

    def do_action(self, action_name, data = None):
        if not action_name:
            action_name = None
        if not data:
            data = [0, 0, 0]

        if action_name in commands:
            command = commands[action_name]
            return self.__hardware.send(command, data)
