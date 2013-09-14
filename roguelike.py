# Using libtcodpy - here's the import

import libtcodpy as libtcod

# Some important values, first is the actual size of the window

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# 20 frames per second maximum

LIMIT_FPS = 20

def handle_keys():
    global playerx, playery

    key = libtcod.console_check_for_keypress()
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True # Exit game

    # Movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        playery -= 1

    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        playery += 1

    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        playerx -= 1

    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        playerx += 1

# Set the custom font we have in the games directory.

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

# Initialise the window, specifying the size, title, and the boolean at the end tells us if we want fullscreen or not

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python roguelike', False)

# Creating a new off screen console that occupies the whole screen

con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# Limit the FPS for real time rather than turn based, no effect if turn based

libtcod.sys_set_fps(LIMIT_FPS)

# Keeping track of the player's position - initialise the variables to the centre of the screen instead of top left

playerx = SCREEN_WIDTH/2
playery = SCREEN_HEIGHT/2

# Now for the main loop, this logic will keep running as long as the window is not closed.

while not libtcod.console_is_window_closed():
    
    # Set text colour to white, the zero being the console we're printing to, in this case the main screen.
    
    libtcod.console_set_default_foreground(con, libtcod.white)
    
    # Printing an '@' character to co-ordinates (1,1).

    libtcod.console_put_char(con, playerx, playery, '@', libtcod.BKGND_NONE)

    # Present changes to the screen, i.e. "flushing" the console.

    libtcod.console_flush()

    # Add a blank space to where the player's icon was previously to avoid the @@@@@ trail.

    # libtcod.console_put_char(con, playerx, playery, ' ', libtcod.BKGND_NONE)

    # handle keys and exit game if needed
    exit = handle_keys()
    if exit:
        break
