import libtcodpy as libtcod
from constants import CONFUSE_NUM_TURNS


def do_nothing(*args, **kwargs):
    pass


class Fighter(object):
    # combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, mp, defense, power, xp, death_function=None, manaless_function=None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_max_mp = mp
        self.mp = mp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function or do_nothing
        self.manaless_function = manaless_function or do_nothing

    @property
    def power(self): # return actual power, by summing up the bonuses from all equipped items
        return self.base_power + sum(e.power_bonus for e in get_all_equipped(self.owner))

    @property
    def defense(self): # return actual defence, by summing up the bonuses from all equipped items
        return self.base_defense + sum(e.defense_bonus for e in get_all_equipped(self.owner))

    @property
    def max_hp(self): # return actual max_hp, by summing up the bonuses from all equipped items
        return self.base_max_hp + sum(e.max_hp_bonus for e in get_all_equipped(self.owner))

    @property
    def max_mp(self): # return actual max_hp, by summing up the bonuses from all equipped items
        return self.base_max_mp + sum(e.max_mp_bonus for e in get_all_equipped(self.owner))

    def attack(self, target, message, player):
        # a simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            # make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            return target.fighter.take_damage(damage, message, player)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')
            return ""

    def take_damage(self, damage, message, player):
        # apply damage if possible
        if damage > 0:
            self.hp -= damage

            # check for death. if there's a death function, call it
            if self.hp <= 0:
                return self.death_function(self.owner, message)
            if self.owner != player: # yield experience to the player
                player.fighter.xp += self.xp

    def heal(self, amount):
        # heal by the given amount, without going over the maximum
        self.hp = min(self.hp+amount, self.max_hp)

    def manabuff(self, amount):
        # heal by the given amount, without going over the maximum
        self.mp = min(self.mp+amount, self.max_mp)

    def manadecrease(self, mana):
        # decrease mana by the given amount
        self.mp = max(0, self.mp-mana)
        if self.mp == 0:
            self.manaless_function(self.owner)

class BasicMonster(object):
    # AI for a basic monster.
    def take_turn(self, message, fov_map, player):
        # a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):

            # move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)

            # close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                return monster.fighter.attack(player, message, player)

class ConfusedMonster(object):
    # AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self, message, fov_map, player):
        if self.num_turns > 0:  # still confused...
            # move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1

        else:  # restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)

class BasicNPC(object):
    # AI for a basic npc.
    def take_turn(self, message, fov_map, player):
        # a basic npc takes its turn, it wanders toward the player, if the player can see it.
        npc = self.owner
        if libtcod.map_is_in_fov(fov_map, npc.x, npc.y):
            npc.move_towards(player.x, player.y)

def monster_death(monster, message):
    # transform it into a nasty corpse! it doesn't block, can't be
    # attacked and doesn't move
    message('The %s is dead! You gain %i experience points.'%(monster.name.capitalize(), monster.fighter.xp), libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
    return ""

def player_death(player, message):
    # the game ended!
    message('You died!', libtcod.red)

    # for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red
    return "dead"

def player_manaless(player):
    player.color = libtcod.lightest_grey

def get_all_equipped(obj): # returns a list of equipped items
    return [item.equipment for item in obj.inventory if item.equipment and item.equipment.is_equipped]

def build_monster(choice):
    if choice  == 'orc': # create an orc
        fighter_component = Fighter(hp=20, mp=0, defense=0, power=4, xp=35, death_function=monster_death)
        return ('o', libtcod.desaturated_green, fighter_component, BasicMonster())
    elif choice == 'troll': # create a troll
        fighter_component = Fighter(hp=30, mp=0, defense=2, power=8, xp=100, death_function=monster_death)
        return ('T', libtcod.darker_green, fighter_component, BasicMonster())
