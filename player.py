wildcards = ['wildcard1', 'wildcard2', 'wildcard3', 'wildcard4']

class Player:
    def __init__(self, name, rfid, skills):
        self.name = name
        self.rfid = rfid
        self.skills = skills

    def add_skill(self, new_skill):
        for skill_name in wildcards:
            if skill_name in self.skills:
                self.skills.remove(skill_name)
        self.skills.append(new_skill)

class Players:
    def __init__(self, config):
        self.players = []
        self.rfidmap = {}
        playernames = map(str.strip, config.get('common','spelers').split(','))
        for playername in playernames:
            rfid = config.getint('spelers', playername)
            skills = map(str.strip, config.get('skills', playername).split(','))
            player = Player(playername, rfid, skills)
            self.players.append(player)
            self.rfidmap[player.rfid] = player

    def find_player_for_rfid(self, rfid):
        return self.rfidmap.get(rfid, None)

