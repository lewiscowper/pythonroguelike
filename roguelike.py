import libtcodpy as libtcod
import math
import shelve
from constants import (MAP_WIDTH, MAP_HEIGHT,
                      SCREEN_WIDTH, SCREEN_HEIGHT,
                      ROOM_MAX_SIZE, ROOM_MIN_SIZE, MAX_ROOMS,
                      FOV_LIGHT_WALLS, FOV_ALGO,
                      MSG_X, BAR_WIDTH,
                      INVENTORY_WIDTH, LEVEL_SCREEN_WIDTH, CHARACTER_SCREEN_WIDTH,
                      PANEL_HEIGHT, PANEL_Y,
                      LEVEL_UP_BASE, LEVEL_UP_FACTOR,
                      LIMIT_FPS,
                      color_dark_wall, color_dark_ground, color_light_wall, color_light_ground,
                      TORCH_RADIUS)
from levelmap import Tile, Rect, create_room, create_h_tunnel, create_v_tunnel
from statics import Item, Equipment, make_item
from dynamics import Fighter, player_death, player_manaless, build_monster
from messages import Messaging


# Current global values

# game state
player = None
game_msgs = None
game_state = None

# map
objects = None
level_map = None
stairs = None
dungeon_level = None

# interface
key = None
mouse = None

# display
fov_map = None
fov_recompute = None


class GameObject(object):
    # this is a generic object: the player, a monster, an item, the stairs...
    # it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.always_visible = always_visible
        self.fighter = fighter
        self.inventory = []
        if self.fighter:  # let the fighter component know who owns it
            self.fighter.owner = self

        self.ai = ai
        if self.ai:  # let the AI component know who owns it
            self.ai.owner = self

        self.item = item
        if self.item:  # let the Item component know who owns it
            self.item.owner = self

        self.equipment = equipment
        if self.equipment: #  let the Equipment component know who owns it
            self.equipment.owner = self
            # there must be an Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self

    def move(self, dx, dy):
        # move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_towards(self, target_x, target_y):
        # vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        # normalize it to length 1 (preserving direction), then round it and
        # convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        # return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        # return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self):
        # make this object be drawn first, so all others appear above it if they're in the same tile.
        objects.remove(self)
        objects.insert(0, self)

    def draw(self):
        # only show if it's visible to the player; or it's set to "always visible" and on an explored tile
        if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
            (self.always_visible and level_map[self.x][self.y].explored)):
            # set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        # erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

def is_blocked(x, y):
    return level_map[x][y].blocked or any(o.blocks for o in objects if (o.x, o.y) == (x, y))


def make_map():
    global level_map, objects, stairs

    objects = [player]

    # fill map with "blocked" tiles
    level_map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    rooms = []

    for r in range(MAX_ROOMS):
        # random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        # random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
        new_room = Rect(x, y, w, h)

        if not any(new_room.intersect(other_room) for other_room in rooms):
            # this means there are no intersections, so this room is valid
            # "paint" it to the map's tiles
            create_room(level_map, new_room)
            # center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
            if not rooms:
                # this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
            else:
                place_objects(new_room)
                # connect it to the previous room with a tunnel
                prev_x, prev_y = rooms[-1].center()
                if libtcod.random_get_int(0, 0, 1) == 1:
                    create_h_tunnel(level_map, prev_x, new_x, prev_y)
                    create_v_tunnel(level_map, prev_y, new_y, new_x)
                else:
                    create_v_tunnel(level_map, prev_y, new_y, prev_x)
                    create_h_tunnel(level_map, prev_x, new_x, new_y)
            rooms.append(new_room)

    # create stairs at the centre of the last room
    stairs = GameObject(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back() # so it's drawn below the monsters

def random_choice_index(chances): # choose one option from the list of chances, returning it's index.
    # the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    # go through all the chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        # see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1

def random_choice(chances_dict):
    # choose one option from the dictionary of chances, returning it's key
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]

def from_dungeon_level(table):
    # returns a value that depends on level. The table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0

def place_objects(room):
    # maximum numberof monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])

    # chances of each monster
    monster_chances = {}
    monster_chances['orc'] = 80 # orcs always show up, even if all other monsters have 0 chance
    monster_chances['troll'] = from_dungeon_level([[15,3], [30, 5], [60, 7]])

    # maximum number of items per room
    max_items = from_dungeon_level([[1, 1], [2, 4]])

    # chances of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances['heal'] = 35 # healing potions always show up, even if all other items have 0 chance
    item_chances['manabuff'] = 35
    item_chances['lightning'] = from_dungeon_level([[25, 4]])
    item_chances['fireball'] = from_dungeon_level([[25, 6]])
    item_chances['confuse'] = from_dungeon_level([[10, 2]])

    item_chances['sword'] = from_dungeon_level([[5, 3]])
    item_chances['shield'] = from_dungeon_level([[15, 5]])
    item_chances['helmet'] = from_dungeon_level([[15, 7]])

    # choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)

    for i in range(num_monsters):
        # choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        # only place it if the tile is not blocked, and it's not in the first room.
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            symbol, colour, fighter_component, ai_component = build_monster(choice)
            monster = GameObject(x, y, symbol, choice, colour, blocks=True, fighter=fighter_component, ai=ai_component)
            objects.append(monster)

    # choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        # choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        # only place it if the tile is not blocked, and it's not in the first room
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            symbol, name, colour, item_component, equipment_component = make_item(choice)
            item = GameObject(x, y, symbol,name, colour, item=item_component, equipment=equipment_component)
            objects.append(item)
            item.send_to_back()  # items appear below other objects
            item.always_visible = True # items are always visible even out of FOV, if in an explored area

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    # render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)

    # render the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    # now render the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # finally, some centered text with the values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
        name + ': ' + str(value) + '/' + str(maximum))

def get_names_under_mouse():
    # return a string with the names of all objects under the mouse
    (x, y) = (mouse.cx, mouse.cy)

    # create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
        if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

    names = ', '.join(names)  # join the names, separated by commas
    return names.capitalize()

def render_all():
    global fov_recompute

    if fov_recompute:
        # recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

        # go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = level_map[x][y].block_sight
                if not visible:
                    # if it's not visible right now, the player can only see it if it's explored
                    if level_map[x][y].explored:
                        if wall:
                            libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                else:
                    # it's visible
                    if wall:
                        libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET )
                    else:
                        libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET )
                    # since it's visible, explore it
                    level_map[x][y].explored = True

    # draw all objects in the list, except the player. we want it to
    # always appear over all other objects! so it's drawn later.
    for object in objects:
        if object != player:
            object.draw()
    player.draw()

    # blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)


    # prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)

    # print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs.tolist():
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    # show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.base_max_hp,
        libtcod.light_red, libtcod.darker_red)

    render_bar(1, 2, BAR_WIDTH, 'MP', player.fighter.mp, player.fighter.base_max_mp,
        libtcod.light_blue, libtcod.darker_blue)

    libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level ' + str(dungeon_level))

    # display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

    # blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def player_move_or_attack(dx, dy):
    global fov_recompute, game_state

    # the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    # try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break

    # attack if target found, move otherwise
    if target is not None:
        game_state = player.fighter.attack(target, game_msgs, player) or game_state
    else:
        player.move(dx, dy)
        fov_recompute = True
  
# should me moved to dynamics once properly untangled
def check_level_up():
    # see if the player's experience is enough to level up.
    level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
    if player.fighter.xp >= level_up_xp:
        # it is! level up
        player.level += 1
        player.fighter.xp -= level_up_xp
        game_msgs('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)

        choice = None
        while choice == None: #  Keep asking until choice is made.
            choice = menu('Level up! Choose a stat to raise:\n',
                ['Constitution (+20 HP, from ' + str(player.fighter.base_max_hp) + ')',
                'Strength (+1 attack, from ' + str(player.fighter.base_power) + ')',
                'Agility (+1 defence, from ' + str(player.fighter.base_defense) + ')'], LEVEL_SCREEN_WIDTH)
        if choice == 0:
            player.fighter.base_max_hp += 20
            player.fighter.hp += 20
        elif choice == 1:
            player.fighter.base_power += 1
        elif choice == 2:
            player.fighter.base_defense += 1

def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

    # calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    # create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    # print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    # print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    # blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    # present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    if key.vk == libtcod.KEY_ENTER and key.lalt:  # (special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    # convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

def inventory_menu(header):
    # show a menu with each item of the inventory as an option
    if len(player.inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in player.inventory:
            text = item.name
            # show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, INVENTORY_WIDTH)

    # if an item was chosen, return it
    if index is None or len(player.inventory) == 0: return None
    return player.inventory[index].item

def msgbox(text, width=50):
    menu(text, [], width)  # use menu() as a sort of "message box"

def handle_keys():
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  # exit game

    if game_state == 'playing':
        # movement keys
        if key.vk == libtcod.KEY_UP:
            player_move_or_attack(0, -1)

        elif key.vk == libtcod.KEY_DOWN:
            player_move_or_attack(0, 1)

        elif key.vk == libtcod.KEY_LEFT:
            player_move_or_attack(-1, 0)

        elif key.vk == libtcod.KEY_RIGHT:
            player_move_or_attack(1, 0)
        else:
            # test for other keys
            key_char = chr(key.c)

            if key_char == 'g':
                # pick up an item
                for object in objects:  # look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up(player.inventory, game_msgs, objects)
                        break
            elif key_char == 'i':
                # show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use(game_msgs, player, objects, target_monster, closest_monster, target_tile)
            elif key_char == 'd':
                # show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop(game_msgs, objects, player)
            elif key_char == '<':
                # go down stairs, if the player is on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()
            elif key_char == 'c':
                # show character information
                level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                    '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
                    '\nAttack: ' + str(player.fighter.power) + '\nDefence: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)

            return 'didnt-take-turn'

def next_level():
    global dungeon_level

    # advance to the next level
    game_msgs('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp / 2) #  Heal the player by 50%

    game_msgs('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
    dungeon_level += 1
    make_map() #  Create a fresh new level!
    initialize_fov()

def save_game():
    # open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = level_map
    file['objects'] = objects
    file['player_index'] = objects.index(player)  # index of player in objects list
    file['stairs_index'] = objects.index(stairs)
    file['inventory'] = player.inventory
    file['game_msgs'] = game_msgs.tolist()
    file['game_state'] = game_state
    file['dungeon_level'] = dungeon_level
    file.close()

def load_game():
    # open the previously saved shelve and load the game data
    global level_map, objects, player, game_msgs, game_state, dungeon_level, stairs

    file = shelve.open('savegame', 'r')
    level_map = file['map']
    objects = file['objects']
    player = objects[file['player_index']]  # get index of player in objects list and access it
    stairs = objects[file['stairs_index']]
    player.inventory = file['inventory']
    game_msgs = Messaging(*file['game_msgs'])
    game_state = file['game_state']
    dungeon_level = file['dungeon_level']
    file.close()

    initialize_fov()

def new_game():
    global player, game_msgs, game_state, dungeon_level, npc

    fighter_component = Fighter(hp=30, mp=30, defense=2, power=2, xp=0, death_function=player_death, manaless_function=player_manaless)
    player = GameObject(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)
#    ai_component = BasicNPC()
#    npc = GameObject(player.x, player.y-2, '@', 'npc', libtcod.dark_red, blocks=True, ai=ai_component)

    player.level = 1
    dungeon_level = 1
    make_map()
    initialize_fov()
    game_state = 'playing'
    game_msgs = Messaging()
    game_msgs('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.', libtcod.red)

    # initial equipment: a dagger
    equipment_component = Equipment(slot='right hand', power_bonus=2)
    obj = GameObject(0,0, '-', 'dagger', libtcod.sky, equipment=equipment_component)
    player.inventory.append(obj)
    equipment_component.equip(player.inventory, game_msgs)
    obj.always_visible = True

def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    # create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not level_map[x][y].block_sight, not level_map[x][y].blocked)

    libtcod.console_clear(con)  # unexplored areas start black (which is the default background color)

def target_tile(max_range=None):
    # return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    while True:
        # render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
        render_all()
        x, y = mouse.cx, mouse.cy

        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return None, None  # cancel if the player right-clicked or pressed Escape

        # accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
            (max_range is None or player.distance(x, y) <= max_range)):
            return x, y

def target_monster(max_range=None):
    # returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  # player cancelled
            return None

        # return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj

def closest_monster(max_range):
    # find closest enemy, up to a maximum range, and in the player's FOV
    fighters = ((player.distance_to(o), o) for o in objects if o.fighter and not o == player)
    visible_fighters = [(d, o) for d, o in fighters if d <= max_range if libtcod.map_is_in_fov(fov_map, o.x, o.y)]
    if visible_fighters:
        return min(visible_fighters)[1]
    else:
        return None

def play_game():
    global key, mouse, game_state

    player_action = None

    mouse = libtcod.Mouse()
    key = libtcod.Key()
    while not libtcod.console_is_window_closed():
        # render the screen
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
        render_all()

        libtcod.console_flush()

        # check for levelling up
        if game_state == 'playing':
            check_level_up()

        # erase all objects at their old locations, before they move
        for object in objects:
            object.clear()

        # handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        # let monsters take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    game_state = object.ai.take_turn(game_msgs, fov_map, player) or game_state

def main_menu():
    img = libtcod.image_load('menu_background.png')

    while not libtcod.console_is_window_closed():
        # show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)

        # show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.light_yellow)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
            'TOMBS OF THE ANCIENT KINGS')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER,
            'By Lewis Cowper')

        # show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

        if choice == 0:  # new game
            new_game()
            play_game()
        elif choice == 1:  # load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
            else:
                play_game()
        elif choice == 2:  # quit
            break


if __name__ == "__main__":
    libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
    libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'roguelike', False)
    libtcod.sys_set_fps(LIMIT_FPS)
    con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
    panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
    main_menu()
