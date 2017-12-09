import multiprocessing, time

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
        self.current_sequence = self.__find_action_for_player(player).split(",")
        
    def tick(self):
        if self.is_hacking:
            return self.__hack_tick()
        elif self.__timer_is_done():
            if self.current_sequence:
                next_action = self.current_sequence.pop()
                try:
                    delay = int(next_action)
                    self.__start_timer(delay)
                except ValueError:
                    if next_action == 'open':
                        self.active_sensor.data = [0,100,0]
                    else:
                        self.active_sensor.data = [0,0,100]
                    self.__run_action(next_action)
                    
                return True
            return False
        return True
                    
    def stop_hack(self):
        if self.is_hacking:
            self.is_hacking = False
            self.__stop_timer()
            self.current_sequence = []
            
    def __find_action_for_player(self, player):
        for action in self.actions:
            if action in player.skills:
                return self.actions[action]
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
        if action.startswith("hack"):
            self.hack_steen, self.hack_skill = action.split("hack(")[1].split(")")[0].split(",")
            self.__start_hack()
        else:            
            for actor in self.actors:
                actor.tell_oscar(action)

    def __start_hack(self):
        self.is_hacking = True
        self.__start_timer(300)
        self.active_sensor.data = [200,100,150]
        print('At ',time.time(),': Player ',player.name,' started hacking')
    
    def __hack_tick(self):
        delta = time.time() - self.timer_start
        self.active_sensor.data = self.__get_keystone_led(delta)
        print('Player ',self.current_player.name,' is now hacking for ',delta,'seconds')

        if delta > 300:
            player.add_skill(self.hack_skill)
            self.current_sequence += ['open', '15', 'close']
            self.is_hacking = False
            self.active_sensor.data = [200,200,200]   
        return True
                
    def __get_keystone_led(self, timebase):
        if timebase < 100:
            fadespeed = 5
        elif timebase < 200:
            fadespeed = 10
        else:
            fadespeed = 15
        return [100, 200, 100]
        #for x in xrange(0,len(self.data)-1):
         #   self.data[x] = self.data[x] + fadespeed
          #  if (self.data[x] > 200):
           #     self.data[x] = fadespeed