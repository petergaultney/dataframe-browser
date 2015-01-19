#!/usr/bin/env python
import random, sys, math, curses, os
import curses

# stdscr = curses.initscr()
# curses.noecho()
# curses.cbreak()
# curses.start_color()
# stdscr.keypad(1)
# curses.curs_set(0)

from curses import wrapper

def main(stdscr):
    # Clear screen
    stdscr.clear()
    
    # This raises ZeroDivisionError when i == 10.
        
    stdscr.refresh()
    try:
        while True:
            stdscr.getkey()
            stdscr.addstr('p')
    except EOFError:
        pass
        
    
wrapper(main)
