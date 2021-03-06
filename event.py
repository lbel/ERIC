import time, numpy

np = numpy

class Event:
    def __init__(self, eventID, actions, actors):
        self.eventID = eventID
        self.actions = actions
        self.actors = actors
        self.active_sensor = None
        self.current_sequence = []
        self.current_player = None
        self.is_hacking = False
        self.is_active = False
        self.timer_start = None
        self.timer_delay = None
        
    def start(self, player, sensor):
        print("Start")
        self.current_player = player
        self.active_sensor = sensor
        self.is_active = True
        self.current_sequence = self.__find_action_for_player(player)
        
    def tick(self):
        if self.is_hacking:
            return self.__hack_tick()
        elif self.__timer_is_done():
            if self.current_sequence:
                print(self.current_sequence)
                next_action = self.current_sequence.pop()
                try:
                    delay = int(next_action)
                    self.__start_timer(delay)
                except ValueError:
                    self.__run_action(next_action)
                    
                return True
            return False
        return True
                    
    def stop_hack(self):
        self.is_hacking = False
        self.__stop_timer()
        self.current_sequence = []
            
    def __find_action_for_player(self, player):
        action_list = list(set(player.skills).intersection(self.actions))
        if action_list:
            for action in action_list:
                if 'open' in self.actions[action].split(","):
                    return self.actions[action].split(",")
            return [None, self.actions[action]]
        return None

    def __start_timer(self, delay):
        self.timer_start = time.time()
        self.timer_delay = delay
        
    def __stop_timer(self):
        self.timer_start = None
        self.timer_delay = None
        
    def __timer_is_done(self):
        if self.timer_start is not None:
            if self.__check_timer():
                self.__stop_timer()
                return True
            else:
                return False
        return True
        
    def __check_timer(self):
        print ("Time elapsed: ",time.time() - self.timer_start)
        return time.time() - self.timer_start > self.timer_delay
        
    def __run_action(self, action):
        print(action)
        if action.startswith("hack"):
            self.hack_steen, self.hack_skill = action.split("hack(")[1].split(")")[0].split(",")
            self.__start_hack()
        else:
            if action == 'open':
                self.active_sensor.data = [0,100,0]
            else:
                self.active_sensor.data = [0,0,100]
            for actor in self.actors:
                actor.tell_oscar(action)

    def __start_hack(self):
        self.is_hacking = True
        self.__start_timer(300)
        self.active_sensor.data = self.__get_keystone_led(0)
        self.active_sensor.do_action("hack")
    
    def __hack_tick(self):
        delta = time.time() - self.timer_start
        self.active_sensor.data = self.__get_keystone_led(delta)
        self.active_sensor.do_action("hack")

        if delta > self.timer_delay:
            self.current_player.add_skill(self.hack_skill)
            self.current_sequence = ['sluit', '9', 'open']
            self.is_hacking = False
            self.__stop_timer()
            self.active_sensor.data = [200,200,200]
            self.active_sensor.do_action("hack")
        return True
                
    def __get_keystone_led(self, timebase):
        time_offset = [0,np.pi/2,np.pi/4]
        list = [0,0,0]
        if timebase < 100:
            fadespeed = 2
        elif timebase < 200:
            fadespeed = 3
        else:
            fadespeed = 4
        x = 0
        while x < 3:
            list[x] = int(100+100*np.sin(2*np.pi*fadespeed*(timebase+time_offset[x])/100))
            x = x + 1
        return list
        #for x in xrange(0,len(self.data)-1):
         #   self.data[x] = self.data[x] + fadespeed
          #  if (self.data[x] > 200):
           #     self.data[x] = fadespeed