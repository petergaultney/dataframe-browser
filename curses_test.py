#!/usr/bin/env python
import random, sys, math, curses, os
import curses

# stdscr = curses.initscr()
# curses.noecho()
# curses.cbreak()
# curses.start_color()
# stdscr.keypad(1)
# curses.curs_set(0)



class RelativePad:
    def __init__(self, y0, x0, y1, x1, dy, dx):
        self.y0 = y0
        self.x0 = x0
        self.y1 = term_y + y1
        self.x1 = term_x + x1
        self.dy = dy # delta y
        self.dx = dx # delta x
        self.pad = curses.newpad(self.y1 + self.dy, self.x1 + self.dx)
        self._refresh()
    def update(string, y=0, x=0):
        self.y1 = term_y + self.dy
        self.x1 = term_x + self.dx
        self.pad.resize(self.y1 + self.dy, self.x1 + self.dx)
        self.pad.addstr(y,x, string, curses.A_REVERSE)
        self._refresh()
    def _refresh(self):
        self.pad.refresh(0,0, self.y0,self.x0, self.y1, self.x1)
        
def curses_loop(stdscr):
    # Clear screen
    stdscr.clear()
    stdscr.refresh()
    
    # main_pad = RelativePad(stdscr, lambda:stdscr,0, lambda:-5,0, 0,9999)
    # input_pad = RelativePad(stdscr, main_pad)
    newp = curses.newpad(20, 20)
    
    try:
        while True:
            key = stdscr.getkey()
            stdscr.clear()
            stdscr.addstr('testing, testing\n123\n' + key)
            stdscr.refresh()
            newp.addstr(0,0, key, curses.A_REVERSE)
            newp.refresh(0,0, 10, 10, 20, 20)
            # main_pad.update('testing, testing\n123\n' + key)
            # input_pad.update(key)
    except EOFError:
        pass
        



    
if __name__ == '__main__':
    from curses import wrapper
    wrapper(curses_loop)
