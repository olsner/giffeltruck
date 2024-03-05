#!/usr/bin/env python3

import curses
from enum import Enum
import math
import sys
import time

def smoothstep(x):
    x = min(x, 1)
    x = max(x, 0)
    return x * x * (3 - 2 * x)

class Dir(Enum):
    LEFT = 0
    UP = 1
    RIGHT = 2
    DOWN = 3

    def next(self):
        return Dir((self.value + 1) % 4)

    def prev(self):
        return Dir((self.value + 3) % 4)

    def interpolate(self, destination):
        if self == destination: return self
        if self.next() == destination or self.prev() == destination:
            return destination
        return self.next()

    def move(self, x, y):
        dx = { Dir.LEFT: -1, Dir.RIGHT: 1 }
        dy = { Dir.UP: -1, Dir.DOWN: 1 }
        return x + dx.get(self, 0), y + dy.get(self, 0)


unloaded = [
    ["      ",
     "==xx  ",
     "      "],
    ["  ||  ",
     "  xx  ",
     "      "],
    ["      ",
     "  xx==",
     "      "],
    ["      ",
     "  xx  ",
     "  ||  "]]
loaded = [
    ["      ",
     "@@XX  ",
     "      "],
    ["  @@  ",
     "  XX  ",
     "      "],
    ["      ",
     "  XX@@",
     "      "],
    ["      ",
     "  XX  ",
     "  @@  "]]


class Player():
    def __init__(self, x = 20, y = 15):
        self.direction = Dir.LEFT
        self.x = x
        self.y = y
        self.load_id = None
        self.loads = None

    def loaded(self):
        return self.load_id is not None

    def at_load(self):
        return (self.x, self.y) in self.loads

    def find_load(self):
        try:
            return self.loads.index(self.fork_pos())
        except ValueError:
            return None

    def lift(self, up = True):
        if up:
            self.load_id = self.find_load()
        else:
            self.load_id = None

    def paint(self, scr):
        graphic = (loaded if self.loaded() else unloaded)[self.direction.value]
        scr.addstr(self.y - 1, 2 * (self.x - 1), graphic[0])
        scr.addstr(self.y    , 2 * (self.x - 1), graphic[1])
        scr.addstr(self.y + 1, 2 * (self.x - 1), graphic[2])

    def turn_or_move(self, dir):
        if dir == self.direction:
            self.x, self.y = dir.move(self.x, self.y)
        else:
            self.direction = self.direction.interpolate(dir)
        if self.load_id is not None:
            self.loads[self.load_id] = self.fork_pos()

    def fork_pos(self):
        return self.direction.move(self.x, self.y)

    def pos(self):
        return self.x, self.y

class World():
    def __init__(self, path):
        self.data = open(path).read().split("\n")
        self.width = max(len(s) for s in self.data)
        self.height = len(self.data)
        self.loads = []
        self.goals = []
        for y,s in enumerate(self.data):
            if len(s) < self.width:
                self.data[y] = s + ' ' * (self.width - len(s))
            for x,c in enumerate(s):
                if c == '@':
                    self.player = Player(x, y)
                elif c == '$':
                    self.loads.append((x, y))
                elif c == '.':
                    self.goals.append((x, y))

        assert self.player
        self.player.loads = self.loads

        # Input data is Sokoban format, so:
        # ' ' = blank, '#' = wall
        # '@' = player start position
        # '$' = box position
        # '.' = goal position
        #
        # Display will double each character for slightly better aspect ratio.
        # boxes will be shown as '@', player as a forklift.

    def paint(self, scr):
        self.player.paint(scr)
        for y,s in enumerate(self.data):
            for x,c in enumerate(s):
                if c == '#' or c == '.':
                    scr.addstr(y, 2 * x, c)
                    scr.addstr(y, 2 * x + 1, c)
        for x,y in self.loads:
            self.paint_load(scr, x, y)

        if False:
            scr.addstr(20, 0, str(self.player.pos()))
            scr.addstr(20, 10, str(self.player.fork_pos()))
            scr.addstr(21, 0, str(self.player.load_id))
            scr.addstr(21, 10, str(self.loads))
            scr.addstr(22, 0, str(self.player.find_load()))

    def paint_load(self, scr, x, y):
        scr.addstr(y, 2 * x, "@@")

    def have_won(self):
        # All load positions match goal positions
        return sorted(self.loads) == sorted(self.goals)

WIN_SCREEN = open("win.txt").read().split("\n")

def draw_win_screen(scr, dt):
    scr.clear()
    h, w = scr.getmaxyx()
    x = int((1 - dt) * w)
    for y,s in enumerate(WIN_SCREEN):
        scr.addstr(y, x, s[:w - x])

def win_screen(scr):
    t0 = time.time()
    anim_length = 2
    frame_interval = 1 / 50
    for i in range(math.ceil(anim_length / frame_interval)):
        dt = time.time() - t0
        scr.erase()
        draw_win_screen(scr, smoothstep(dt / anim_length))
        scr.refresh()
        time.sleep(frame_interval)

def run_one_game(scr):
    # TODO Take argument
    w = World("big_map.gft")
    p = w.player
    while True:
        scr.erase()
        w.paint(scr)

        key = scr.getch()

        QUIT_KEYS = { ord('q') }
        DIR_KEYS = { curses.KEY_UP: Dir.UP, curses.KEY_DOWN: Dir.DOWN,
                     curses.KEY_LEFT: Dir.LEFT, curses.KEY_RIGHT: Dir.RIGHT }
        LIFT_KEYS = { ord('u'): True, ord('d'): False }

        if key in QUIT_KEYS:
            return False
        elif key in DIR_KEYS:
            p.turn_or_move(DIR_KEYS[key])
        elif key in LIFT_KEYS:
            p.lift(LIFT_KEYS[key])

        if w.have_won() or key == ord('w'):
            win_screen(scr)
            key = scr.getch()
            return key not in QUIT_KEYS

def main(scr):
    while run_one_game(scr):
        pass

if __name__=="__main__":
    sys.exit(curses.wrapper(main))
