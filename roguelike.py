# Using libtcodpy - here's the import

import libtcodpy as libtcod

# Some important values, first is the actual size of the window

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# 20 frames per second maximum

LIMIT_FPS = 20

# Set the custom font we have in the games directory.

libtcod.console_set_custom_font('consolas_unicode_16x16.png' libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

# Initialise the window, specifying the size, title, and the boolean at the end tells us if we want fullscreen or not

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python roguelike', False)

# Limit the FPS for real time rather than turn based, no effect if turn based

libtcod.sys_set_fps(LIMIT_FPS)

# Now for the main loop, this logic will keep running as long as the window is not closed.

while not libtcod.console_is_window_closed():
	
	# Set text colour to white, the zero being the console we're printing to, in this case the main screen.
	
	libtcod.console_set_default_foreground(0, libtcod.white)
	
	# Printing an '@' character to co-ordinates (1,1).

	libtcod.console_put_char(0, 1, 1, '@', libtcod.BKGND_NONE)

	# Present changes to the screen, i.e. "flushing" the console.

    libtcod.console_flush()