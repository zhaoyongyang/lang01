from enum import Enum

class RoleType(Enum):
    WEREWOLF = "Werewolf"
    VILLAGER = "Villager"
    SEER = "Seer"
    WITCH = "Witch"
    HUNTER = "Hunter"

class Team(Enum):
    GOOD = "Good"
    BAD = "Bad"

class Role:
    def __init__(self, role_type: RoleType):
        self.type = role_type
        self.team = Team.BAD if role_type == RoleType.WEREWOLF else Team.GOOD
        
    def __str__(self):
        return self.type.value
