#!/usr/bin/env python3
################################################################################
#                                   KEY MAP                                    #
#                                                                              #
#   q                       Quit game                                          #
#   Arrow keys              Turn towards the direction, or if already facing   #
#                           it drive forwards.                                 #
#   x                       Drive backwards given the current direction. Use   #
#                           arrow keys to turn if necessary.                   #
#   u                       Lift forks, picking up a giffel (@@) if the forks  #
#                           are in position                                    #
#   d                       Lower forks, dropping off the loaded giffel        #
#                                                                              #
#                                                                              #
#   OBJECTIVE:                                                                 #
#                                                                              #
#   Pick up all giffels (@@) and drive them to some goal position (..). The    #
#   truck or forks must not touch the walls. Although it doesn't kill you,     #
#   your boss will be unhappy.                                                 #
#                                                                              #
################################################################################

import curses
from enum import Enum
import math
import os
import pickle
import random
import string
import sys
import time
import zlib

def decode(x):
    return zlib.decompress(x).decode('ascii').split('\n')

HOME_SCREEN = decode(b"x\xda\x9dPA\x0e\xc2@\x08\xbc\xf3\n\x8ez)\x1f0\xbe\x84\x84h\xf4\xd6Sco<^\x18Xmb\xbd\x94l\xc2\xec0\x0c\xec\x121[\xc7d\xd6\x97O\xca\x98l\x1b\xbc\x17E\x13K7\x8a\x9b\xb9\x00k'\xf4:\xb3\x966EmX\xa7:S\xe1\x81(\x9cX\xc19@ \xed\x94\x86\xac\x10zZ\xc1\x14;h_0\x12\na\xa1l\x0bR\xe1\xe3\xe8\xe3\x9aS\x03$\xb1\r\xab\xae\x08\x80(\x16\xae\xe2%\x1e\xa8\xe3\x13by\xf7*TR\xd0W\x1b\x0f\xfbV\x1c\xdcF\xe1\xb1)\x8d\xaf\xcbI;\xf1\x87\xfeU\xa8\x10\xf1\xe18=\x9e/\xbe\xaf\xf3|[x]\xce\xf4\x06\xa0$z\xb2")
MAP_DATA = {
    "level0.gft": decode(b'x\xda}Q\xc9\r\xc00\x08\xfb3\x85%\xe7\xdd\x19\xba\xffTm\x028\xa0\x1eH\xad8\x1cc\x00|3,\x9b\x9ea\x06\x9cA\xe4f\xb4q\x05\x00\xc4\xaf\x19\x8d\x1b\xc0\xf4\xf5\xdd)#\xce$U6Z\xd2\x19\x92\xb7\xd4SL\x00"\xf4\x1e\x1a!)\x8d[{\x16T\xa6k\x90tA\xca\x83l\x01\xd4\xc6\x9ai\x04`\x11\xb2\xee\xc1\x9dA\xdf\x03;\x8b\xd8w\x0b-\x92\r\xb7T>\xc7\xd4^]\xea\x9a\xe28\xda\xae\xd8o\x81\x8f+\xe9\x16\xff\x06\xbb\x00\x86\xdfGe'),
}
MOTTOS = decode(b'x\xdaE\x8d;\x0e\x021\x0cD\xfb\x9cbr\x04\x04=t\\\x80\x0bdWv\xd6$\xc4h\xed\x14\xdc\x9ed)hFz\xf3\xd1T2\x83\x18^\xbaS\x0c,%M\xaa\xc2\x83\xa6N\x9an\x0cwa\xa6\xfa\xd8\xfbZB&\x87o\xc9\x91\x0f3\x86g7\x1f\xabB\xc8Z\x19K\xffGkj\xf8h\xc7B\xa3\x7f:_\xf0Vin\xd7\xdfF\x1b\x1d\xdf\xb8\xc5/\xed\x08.\xfa')
COLLISION_PENALTY_TIME = 0.5
COLLISION_PENALTY_SCORE = 10
HOME_SCREEN_ANIM_TIME = 2
COLLISION_ATTR = 0
DEFAULT_ATTR = 0
SCORE_ATTR = 0
LOWSCORE_LEN = 5
LOWSCORE_FILE = os.path.expanduser("~/.giffelscores")

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

    def opposite(self):
        return self.next().next()


unloaded = [
    ["   ", "=x ", "   "],
    [" | ", " x ", "   "],
    ["   ", " x=", "   "],
    ["   ", " x ", " | "]]
loaded = [
    ["   ", "@X ", "   "],
    [" @ ", " X ", "   "],
    ["   ", " X@", "   "],
    ["   ", " X ", " @ "]]


class Player():
    def __init__(self, world, x = 20, y = 15):
        self.world = world
        self.x = x
        self.y = y
        self.direction = Dir.LEFT
        self.load_id = None
        self.loads = None
        self.collision = False
        self.move_counter = 0

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
        had_load = self.loaded()
        if up:
            self.load_id = self.find_load()
        else:
            self.load_id = None
        self.moved(self.loaded() and not had_load)

    def paint(self, scr):
        graphic = (loaded if self.loaded() else unloaded)[self.direction.value]
        for dy,s in enumerate(graphic):
            for dx,c in enumerate(s):
                if c != ' ':
                    scr.addstr(self.y - 1 + dy, 2 * (self.x - 1 + dx), c + c)

    def moved(self, flag = True):
        if flag: self.move_counter += 1

    def would_collide_at(self, x, y):
        return self.world.has_wall_at(x, y)

    def turn_or_move(self, dir):
        if dir == self.direction:
            x, y = dir.move(self.x, self.y)
            if self.would_collide_at(x, y) or \
               self.would_collide_at(*dir.move(x, y)) or \
               self.load_id is None and (x,y) in self.loads:
                self.collision = True
            else:
                self.x, self.y = x, y
                self.moved()
        else:
            dir2 = self.direction.interpolate(dir)
            # Check fork collision after turn and refuse
            # TODO Check for collision with stationary loads (except our own)
            if self.would_collide_at(*dir2.move(self.x, self.y)):
                self.collision = True
            else:
                self.direction = dir2
                self.moved()
        if self.load_id is not None:
            self.loads[self.load_id] = self.fork_pos()

    def reverse(self):
        # Collision detection on the new truck position (move opposite), and
        # then the new fork position is forward from the new truck position.
        x, y = self.direction.opposite().move(self.x, self.y)
        if self.would_collide_at(x, y) or \
           self.would_collide_at(*self.direction.move(x, y)):
            self.collision = True
        else:
            self.x, self.y = x, y
            self.moved()
        if self.load_id is not None:
            self.loads[self.load_id] = self.fork_pos()

    def fork_pos(self):
        return self.direction.move(self.x, self.y)

    def pos(self):
        return self.x, self.y

def load_map_data(path):
    if path in MAP_DATA:
        return MAP_DATA[path]
    else:
        return open(path, "r").read().split('\n')

class World():
    def __init__(self, path):
        self.data = load_map_data(path)
        self.width = max(len(s) for s in self.data)
        self.height = len(self.data)
        self.loads = []
        self.goals = []
        for y,s in enumerate(self.data):
            if len(s) < self.width:
                self.data[y] = s + ' ' * (self.width - len(s))
            for x,c in enumerate(s):
                if c == '@':
                    self.player = Player(self, x, y)
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
        for y,s in enumerate(self.data):
            for x,c in enumerate(s):
                if c == '#' or c == '.':
                    scr.addstr(y, 2 * x, c)
                    scr.addstr(y, 2 * x + 1, c)
        self.player.paint(scr)
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

    def has_wall_at(self, x, y):
        return self.data[y][x] == '#'

    def have_won(self):
        # All load positions match goal positions
        return sorted(self.loads) == sorted(self.goals)

    def collision(self):
        return self.player.collision

class Game:
    def __init__(self, scr, level = 0, last_level = 0):
        self.screen = scr
        self.worldwin = scr.subwin(1, 0)

        self.level = level
        self.last_level = last_level
        self.bumps = 0
        self.world = World(f"level{level}.gft")
        self.player = self.world.player
        self.width = 2 * self.world.width
        self.height = self.world.height
        self.motto = random.choice(MOTTOS)

    def paint(self, collision = False):
        global COLLISION_ATTR, DEFAULT_ATTR
        if collision:
            self.player.collision = False
            self.bumps += 1
            self.screen.bkgdset(' ', COLLISION_ATTR)
            self.worldwin.bkgdset(' ', COLLISION_ATTR)
        else:
            self.screen.bkgdset(' ', DEFAULT_ATTR)
            self.worldwin.bkgdset(' ', DEFAULT_ATTR)

        self.paint_score(collision)
        self.world.paint(self.worldwin)

    def paint_score(self, collision):
        global COLLISION_ATTR, SCORE_ATTR
        attr = COLLISION_ATTR if collision else SCORE_ATTR
        self.screen.addstr(0, 0, ' ' * self.width, attr)
        self.screen.addstr(0, 0, self.motto, attr)
        loaded = len(set(self.world.loads) & set(self.world.goals))
        loads = len(self.world.loads)
        self.screen.addstr(0, self.width - 30,
                           f"Giffels: {loaded}/{loads}", attr)
        self.screen.addstr(0, self.width - 10,
                           f"Score:{self.score():4d}", attr)

    def have_won(self):
        # TODO And level == last_level, otherwise go to next level
        return self.world.have_won()

    def collision(self):
        return self.player.collision

    def score(self):
        global COLLISION_PENALTY_SCORE
        return self.bumps * COLLISION_PENALTY_SCORE + self.player.move_counter

def center_str(scr, y, xmid, s, attr = 0):
    x = xmid - len(s) // 2
    scr.addstr(y, x, s, attr)

def get_lowscores():
    try:
        return pickle.load(open(LOWSCORE_FILE, "rb"))
    except:
        # Default high-score list
        return [(134, "GOD"), (170, "SMB"), (234, "GFL"), (764, "NEW"), (999, "BAD")]

def draw_home_screen(scr, dt = 1, score = None):
    scr.clear()
    h, w = scr.getmaxyx()
    x = int((1 - dt) * w)
    for y,s in enumerate(HOME_SCREEN):
        # TODO Check if this is off-by-one or something. Or maybe it's just not
        # really legal/possible to draw up to the edge of the screen with the
        # usual addstr? See also https://stackoverflow.com/a/54412404
        try:
            scr.addstr(y, x, s[:w - x])
        except curses.error:
            pass

    y = len(HOME_SCREEN)
    w = max(len(s) for s in HOME_SCREEN)

    if x == 0:
        if score is not None:
            center_str(scr, y, w // 2, f"FINAL SCORE: {score}", curses.A_BOLD)

        y += 2
        for lowscore,name in get_lowscores():
            scr.addstr(y, w // 2 - 9, f"{name:14s} {lowscore:4d}")
            y += 1

        if score is not None:
            center_str(scr, y + 1, w // 2, "TRY AGAIN? PRESS ANY KEY!")
        else:
            center_str(scr, y + 1, w // 2, "PRESS ANY KEY TO START")

    return y + 1

def win_screen(scr, score):
    t0 = time.time()
    anim_length = HOME_SCREEN_ANIM_TIME
    frame_interval = 1 / 50
    for i in range(math.ceil(anim_length / frame_interval)):
        dt = time.time() - t0
        scr.erase()
        draw_home_screen(scr, dt=smoothstep(dt / anim_length), score=score)
        scr.refresh()
        time.sleep(frame_interval)

    draw_home_screen(scr, score=score)

def save_score(scr, score, cheat=False):
    w = max(len(s) for s in HOME_SCREEN)
    x = w // 2 - len(f"TRY AGAIN? PRESS ANY KEY!") // 2
    lowscores = get_lowscores()

    y = draw_home_screen(scr, score=score)

    if len(lowscores) < LOWSCORE_LEN or score < lowscores[-1][0]:
        scr.addstr(y, 0, " " * w)
        scr.addstr(y, x, "NEW LOWSCORE> _ _ _")
        name = ""
        while len(name) < 3:
            ch = scr.getkey()
            if ch in string.printable:
                name += ch.upper()
            for i,c in enumerate(name):
                scr.addstr(y, x + 14 + 2 * i, c)

        lowscores.append((score, name))
        lowscores = sorted(lowscores)[:LOWSCORE_LEN]

        if not cheat:
            pickle.dump(lowscores, open(LOWSCORE_FILE, "wb"))

    draw_home_screen(scr, score=score)


def run_one_game(scr):
    g = Game(scr)
    w = g.world
    p = g.player
    while True:
        scr.erase()
        g.paint()

        key = scr.getch()

        QUIT_KEYS = { ord('q') }
        DIR_KEYS = { curses.KEY_UP: Dir.UP, curses.KEY_DOWN: Dir.DOWN,
                     curses.KEY_LEFT: Dir.LEFT, curses.KEY_RIGHT: Dir.RIGHT }
        LIFT_KEYS = { ord('u'): True, ord('d'): False }
        REVERSE_KEYS = { ord('x') }

        if key in QUIT_KEYS:
            return False
        elif key in DIR_KEYS:
            p.turn_or_move(DIR_KEYS[key])
        elif key in LIFT_KEYS:
            p.lift(LIFT_KEYS[key])
        elif key in REVERSE_KEYS:
            p.reverse()

        if g.have_won() or ("ALLOW_CHEAT" in os.environ and key == ord('w')):
            win_screen(scr, g.score())
            save_score(scr, g.score(), cheat=not g.have_won())
            key = scr.getch()
            return key not in QUIT_KEYS

        if g.collision():
            scr.erase()
            g.paint(collision=True)
            scr.refresh()
            global COLLISION_PENALTY_TIME
            time.sleep(COLLISION_PENALTY_TIME)
            scr.bkgdset(' ')

def main(scr):
    curses.start_color()
    global COLLISION_ATTR, DEFAULT_ATTR, SCORE_ATTR
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN)
    DEFAULT_ATTR = curses.color_pair(1)
    COLLISION_ATTR = curses.color_pair(2)
    SCORE_ATTR = curses.color_pair(3) | curses.A_BOLD
    draw_home_screen(scr)
    scr.getch()
    while run_one_game(scr):
        pass

if __name__=="__main__":
    sys.exit(curses.wrapper(main))
