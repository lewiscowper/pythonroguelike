# Using libtcodpy - here's the import

import libtcodpy as libtcod

# Some important values, first is the actual size of the window

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# Setting size of map

MAP_WIDTH = 80
MAP_HEIGHT = 45

# 20 frames per second maximum

LIMIT_FPS = 20

# Colours of tiles when dark

color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)

class Object:
    
    # This is a generic object; the player, a monster, an item, the stairs...
    # it's always represented by a character on the screen.

    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color

    def move(self, dx, dy):

        # Make blocked tiles impassable

        if not map[self.x + dx][self.y + dy].blocked:

            # Move by the given amount

            self.x += dx
            self.y += dy

    def draw(self):

        # set the colour and then draw the character that represents this object at it's position.

        libtcod.console_set_default_foreground(con, self.color)
        libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):

        # Erase the character that represents this object

        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Tile:

    # A tile of the map and it's properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked

        # By default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

def make_map():
    global map

    # Fill map with "unblocked" tiles
    map = [[ Tile(False)
        for y in range(MAP_HEIGHT)  ]
            for x in range(MAP_WIDTH)   ]

    # Place two pillars to test the map

    map[30][22].blocked = True
    map[30][22].block_sight = True
    map[50][22].blocked = True
    map[50][22].block_sight = True

def render_all():
    global color_light_wall
    global color_light_ground

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            wall = map[x][y].block_sight
            if wall:
                libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
            else:
                libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )

    # Draw all objects in the list
    for object in objects:
        object.draw()

    # Blitting contents of new console to the root console, in order to display them.

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

def handle_keys():

    key = libtcod.console_check_for_keypress()
    if key.vk == libtcod.KEY_ENTER and key.lalt:

        # Alt+Enter: toggle fullscreen

        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True 

        # Exit game

    # Movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        player.move(0, -1)

    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        player.move(0, 1)

    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        player.move(-1, 0)

    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        player.move(1, 0)

# Initialisation and Main Loop

# Set the custom font we have in the games directory.

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

# Initialise the window, specifying the size, title, and the boolean at the end tells us if we want fullscreen or not

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python roguelike', False)

# Limit the FPS for real time rather than turn based, no effect if turn based

libtcod.sys_set_fps(LIMIT_FPS)

# Creating a new off screen console that occupies the whole screen

con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# Creating the object representing the player

player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)

# Creating an NPC

npc = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2, '@', libtcod.yellow)

# The list of objects

objects = [npc, player]

# Generate map (for now it's not drawn to the screen)
make_map()

# Now for the main loop, this logic will keep running as long as the window is not closed.

while not libtcod.console_is_window_closed():

    # Render the screen
    render_all()

    # Present changes to the screen, i.e. "flushing" the console.

    libtcod.console_flush()

    # Erase all objects at old locations, before they move
    for object in objects:
        object.clear()

    # handle keys and exit game if needed
    exit = handle_keys()
    if exit:
        break
