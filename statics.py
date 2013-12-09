import libtcodpy as libtcod
from constants import CONFUSE_RANGE, HEAL_AMOUNT, LIGHTNING_RANGE, LIGHTNING_DAMAGE, MANABUFF_AMOUNT, FIREBALL_DAMAGE, FIREBALL_RADIUS
from dynamics import ConfusedMonster


class Item(object):
    # an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function

    def pick_up(self, inventory, message, objects):
        # add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)

        # special case: automatically equip, if the corresponding equipment slot is unused
            equipment = self.owner.equipment
            if equipment and get_equipped_in_slot(equipment.slot, inventory) is None:
                equipment.equip(inventory)

    def drop(self, message, objects, player):
        # special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip(message)
        # add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        player.inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)

    def use(self, message, player, objects, target_monster, closest_monster, target_tile):
        # special case: if the object has the Equipment component, the "use" action is to equip/dequip
        if self.owner.equipment:
            self.owner.equipment.toggle_equip(player, message)
            return
        # just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function(message, player, objects, target_monster, closest_monster, target_tile) != 'cancelled':
                player.inventory.remove(self.owner)  # destroy after use, unless it was cancelled for some reason

class Equipment(object):
    # an object that can be equipped, yielding bonuses. Automatically adds the Item component.
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0, max_mp_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
        self.max_mp_bonus = max_mp_bonus

        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self, player, message):     # toggle equip/dequip status
        if self.is_equipped:
            self.dequip(message)
        else:
            self.equip(player.inventory, message)

    def equip(self, inventory, message):
        # if the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot, inventory)
        if old_equipment is not None:
            old_equipment.dequip(message)

        # equip object and show a message about it
        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)

    def dequip(self, message):
        # dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        message('Dequipped ' + self.owner.name+ ' from ' + self.slot + '.', libtcod.light_yellow)

def cast_confuse(message, player, objects, target_monster, closest_monster, target_tile):
    # ask the player for a target to confuse
    message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None: return 'cancelled'

    # replace the monster's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster  # tell the new component who owns it
    message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)
    player.fighter.manadecrease(8)

def cast_heal(message, player, objects, target_monster, closest_monster, target_tile):
    # heal the player
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'

    message('Your wounds start to feel better!', libtcod.light_violet)
    player.fighter.heal(HEAL_AMOUNT)
    player.fighter.manadecrease(1)

def cast_mana(message, player, objects, target_monster, closest_monster, target_tile):
    # restore the player's mana
    if player.fighter.mp == player.fighter.max_mp:
        message('You are already at full mana.', libtcod.red)
        return 'cancelled'

    message('Your magic feels a bit refreshed!', libtcod.light_violet)
    player.fighter.manabuff(MANABUFF_AMOUNT)

def cast_lightning(message, player, objects, target_monster, closest_monster, target_tile):
    # find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(LIGHTNING_RANGE)
    if monster is None:  # no enemy found within maximum range
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'

    # zap it!
    message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
        + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
    monster.fighter.take_damage(LIGHTNING_DAMAGE)
    player.fighter.manadecrease(3)

def cast_fireball(message, player, objects, target_monster, closest_monster, target_tile):
    # ask the player for a target tile to throw a fireball at
    message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)

    for obj in objects:  # damage every fighter in range, including the player
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
            obj.fighter.take_damage(FIREBALL_DAMAGE)
    player.fighter.manadecrease(5)

def get_equipped_in_slot(slot, inventory): # returns the item in a slot, or None if it's empty
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None


def make_item(choice):
    if choice == 'heal':
        return '!', 'healing potion', libtcod.violet, Item(use_function=cast_heal), None
    elif choice == 'manabuff':
        return '!', 'mana potion', libtcod.azure, Item(use_function=cast_mana), None
    elif choice == 'lightning':
        return '#', 'scroll of lightning bolt', libtcod.light_yellow, Item(use_function=cast_lightning), None
    elif choice == 'fireball':
        return '#', 'scroll of fireball', libtcod.light_yellow, Item(use_function=cast_fireball), None
    elif choice == 'confuse':
        return '#', 'scroll of confusion', libtcod.light_yellow, Item(use_function=cast_confuse), None
    elif choice == 'sword':
        return '/', 'sword', libtcod.sky, None, Equipment(slot='right hand', power_bonus=3)
    elif choice == 'shield':
        return '[', 'shield', libtcod.darker_orange, None, Equipment(slot='left hand', defense_bonus=1)
    elif choice == 'helmet':
        return '^', 'helmet', libtcod.darker_han, None, Equipment(slot='head', max_hp_bonus=1)
