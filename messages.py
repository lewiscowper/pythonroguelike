import textwrap
import libtcodpy as libtcod
from constants import MSG_WIDTH, MSG_HEIGHT


class Messaging(object):
    def __init__(self, *msg):
        self.messages = [m for m in msg]

    def __call__(self, new_msg, color = libtcod.white):
        # split the message if necessary, among multiple lines
        new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

        for line in new_msg_lines:
            # if the buffer is full, remove the first line to make room for the new one
            if len(self.messages) == MSG_HEIGHT:
                del self.messages[0]
            # add the new line as a tuple, with the text and the color
            self.messages.append((line, color))

    def tolist(self):
        return self.messages
