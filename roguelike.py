# Using libtcodpy - here's the import

import libtcodpy as libtcod

# Some important values, first is the actual size of the window

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# Setting size of map

MAP_WIDTH = 80
MAP_HEIGHT = 45

# Parameters for the dungeon generator

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

FOV_ALGO = 0 # Default FOV algorithm
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

# 20 frames per second maximum

LIMIT_FPS = 20

# Colours of tiles when dark

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

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

        # Now we make sure that objects only show if they're in the player's FOV

        if libtcod.map_is_in_fov(fov_map, self.x, self.y):

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

        # All tiles start unexplored
        self.explored = False

        # By default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

class Rect:

    # A rectangle on the map, used to characterise a room.

    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):

        # Returns true if this rectangle intersects with another one

        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

def create_room(room):
    global map

    # Go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
    global map

    # Horizontal tunnel

    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
    global map

    # Vertical tunnel

    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def make_map():
    global map

    # Fill map with "blocked" tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT)  ]
            for x in range(MAP_WIDTH)   ]

    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):

        # Random width and height

        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)

        # Random position without going out the boundaries of the map

        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        # "Rect" class makes rectangles easier to work with in generation
        new_room = Rect(x, y, w, h)

        # Iterate through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:

            # This means there are no intersections, so this room is valid

            #"paint" it to the map's tiles

            create_room(new_room)

            # Add some objects to this room, such as monsters

            place_objects(new_room)

            # Find center co-ordinates of neww , will be useful later.

            (new_x, new_y) = new_room.center()

            if num_rooms ==0:

                # This is the first room, where the player starts

                player.x = new_x
                player.y = new_y

            else:
                # all rooms after the first - connect it to the previous room with a tunnel

                # Get centre of the previous room

                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                #Draw a coin (random number that is either 0 or 1)

                if libtcod.random_get_int(0, 0, 1) == 1:

                    # First move horizontally, then vertically

                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)

                else:

                    # First move vertically, then horizontally

                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            # Finally append the new room to our list of rooms

            rooms.append(new_room)
            num_rooms += 1

def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute

    if fov_recompute:

        # Recomputes FOV if needed (eg the player moves)

        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)



        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if not visible:

                    # If it's not visible right now, the player can only see it if it's explored

                    if map[x][y].explored:
                        if wall:
                            libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)

                else:

                    # It's visible
                    
                    if wall:
                        libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)

                    # Since it's visible, explore it

                    map[x][y].explored = True

    # Draw all objects in the list
    for object in objects:
        object.draw()

    # Blitting contents of new console to the root console, in order to display them.

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

def place_objects(room):

    # Choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    for i in range(num_monsters):

        # Choose random spot for this monster

        x = libtcod.random_get_int(0, room.x1, room.x2)
        y = libtcod.random_get_int(0, room.y1, room.y2)

        if libtcod.random_get_int(0, 0, 100) < 80: #80% chance of getting an orc

            # Create an orc

            monster = Object(x, y, 'o', libtcod.desaturated_green)

        else:

            # Create a troll

            monster = Object(x, y, 'T', libtcod.darker_green)

        objects.append(monster)


def handle_keys():
    global fov_recompute

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
        fov_recompute = True

    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        player.move(0, 1)
        fov_recompute = True

    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        player.move(-1, 0)
        fov_recompute = True

    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        player.move(1, 0)
        fov_recompute = True

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


# The list of objects

objects = [npc, player]

# Generate map (for now it's not drawn to the screen)
make_map()

# Create the FOV map, according to the generated map

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

#FOV will only need to be recomputed if the player moves, or a tile changes.

fov_recompute = True

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
