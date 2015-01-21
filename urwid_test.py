#!/usr/bin/env python
import urwid
import sys, re, os
import pandas as pd

ui = urwid.raw_display.RealTerminal()
ui.tty_signal_keys('undefined', 'undefined', 'undefined', 'undefined',
                   'undefined')

class HelpText(urwid.WidgetWrap):
    def __init__(self):
        self.text = urwid.Text('Help Area')
        urwid.WidgetWrap.__init__(self, self.text)
    def set_text(self, text):
        self.text.set_text(text)

class Minibuffer(urwid.WidgetWrap):
    def __init__(self, browser):
        self.browser = browser
        self.text = urwid.Edit(caption='cmd: ', multiline=False)
        urwid.WidgetWrap.__init__(self, self.text)
    def keypress(self, size, key):
        if key == 'enter':
            name = self.text.get_edit_text()
            if self.browser.colview.add_col(name):
                self.text.set_edit_text('')
                self.browser.frame.focus_position = 'body'
            else:
                self.browser.helper.set_text(str(name) + ' not in df')
                # self.browser.helper.set_text(str(list(self.browser.colview.df)))
        elif key == 'esc':
            self.browser.frame.focus_position = 'body'
        elif key == 'ctrl c':
            raise urwid.ExitMainLoop()
        else:
            return self.text.keypress(size, key)

class SelectableText(urwid.Text):
    def __init__(self, markup, align='left', wrap='space', layout=None):
        super(self.__class__, self).__init__(markup, align, wrap, layout)
    def selectable(self):
        return True # this allows us to assign focus to the columns of text
    def keypress(self, size, key):
        return None
        
class DFColumnView(urwid.WidgetWrap):
    def __init__(self, browser, df=pd.DataFrame(), dcols=None):
        self.browser = browser
        self.df = None
        self.dcols_hist = list()
        self.df_hist = list()
        self.set_df(df)
        self.cols = urwid.Columns([urwid.Edit('A DataFrame will be displayed here.')],
                                  dividechars=1)
        urwid.WidgetWrap.__init__(self, self.cols)
        self.disp_cols()
    def set_df(self, df, dcols=None):
        if self.df:
            self.df_hist.append((self.df, self.dcols_hist))
        self.dcols_hist = list()
        self.df = df
        if not dcols:
            self.dcols = list(df)
        self.disp_cols()
    def disp_cols(self):
        try:
            fp = self.cols.focus_position
        except:
            fp = 0
        del self.cols.contents[:] # clear existing columns
        for idx, col in enumerate(self.dcols):
            attr = 'def'
            try:
                if idx == fp:
                    attr = 'active_col'
            except:
                pass
            self.cols.contents.append(
                (urwid.AttrMap(SelectableText(self.df[[col]].to_string(index=False)),
                               attr), self._opt())
            )
        try:
            self.cols.focus_position = fp
        except Exception as e:
            self.browser.helper.text.set_text(str(e))
            if len(self.cols.contents) > 0:
                self.cols.focus_position = 0
    def undo(self, n=1):
        if n <= len(self.dcols_hist):
            for i in range(n):
                self.dcols = self.dcols_hist.pop()
            self.disp_cols()
    def _opt(self):
        return self.cols.options(width_type='pack')
    def set_focus(self, num):
        if num < 0:
            num = 0
        if num >= len(self.cols.contents):
            num = len(self.cols.contents) - 1
        try:
            self.cols.focus_position = num
            self.browser.helper.text.set_text(str(num + 1))
        except:
            self.browser.helper.text.set_text('failed to set focus to '+ str(num + 1))
        self.disp_cols()
    def add_col(self, col_name, idx=None):
        if not idx:
            idx = self.cols.focus_position
        if col_name in list(self.df):
            self.dcols_hist.append(self.dcols[:]) # shallow copy
            self.dcols.insert(self.browser.colview.cols.focus_position, col_name)
            self.disp_cols()
            return True
        else:
            return False
    def hide_col(self, col_name):
        if col_name in list(self.df) and col_name in self.dcols:
            self.dcols_hist.append(self.dcols[:]) # shallow copy
            self.dcols.remove(col_name)
            self.disp_cols()
            return True
        else:
            return False
    def keypress(self, size, key):
        if key in '1234567890':
            num = int(key) - 1
            if num == -1:
                num = 9
            self.set_focus(num)
        elif key == 'p':
            self.set_df(pd.read_csv(sys.argv[1]))
        elif key == 'h':
            self.browser.helper.text.set_text(str(self.cols.focus_position))
            del self.dcols[self.cols.focus_position] # hide column
            self.disp_cols()
        elif key == 's':
            self.browser.frame.focus_position = 'footer'
        elif key == 'right':
            self.set_focus(self.cols.focus_position + 1)
        elif key == 'left':
            self.set_focus(self.cols.focus_position - 1)
        else:
            return None

def trace_keyp(size, key):
    if key == 'p':
        raise urwid.ExitMainLoop()
    else:
        return None

palette = [
    ('active_col', 'light blue', 'black'),
    ('def', 'white', 'black'),
    ('help', 'black', 'light gray'),
    ]
    
class DFBrowser:
    def __init__(self):
        # self.control = Controller()
        self.helper = HelpText()
        self.mini = Minibuffer(self)
        self.colview = DFColumnView(self)
        self.inner_frame = urwid.Frame(urwid.Filler(self.colview, valign='top'),
                                       footer=urwid.AttrMap(self.helper, 'help'))
        self.frame = urwid.Frame(self.inner_frame, footer=self.mini)
        #self.colview.keypress = trace_keyp
        #self.frame.keypress = trace_keyp
        #self.inner_frame.keypress = trace_keyp
        # self.dftxt = urwid.Text('the dataframe\ndisplays here', wrap='clip')
        # self.dffiller = urwid.Filler(self.dftxt, valign='top', height=('relative', 100))                                     
        # self.frame = urwid.Frame(
        # self.frame = urwid.Frame(urwid.Filler(self.dftxt, valign='top'), footer=urwid.BoxAdapter(self.control, 5))
        # self.frame.focus_position = 'body'
        self.helper.text.set_text(str(self.colview.selectable()))
        self.flag = False
    def start(self):
        self.loop = urwid.MainLoop(self.frame, palette, input_filter=self.input, 
                                   unhandled_input=self.unhandled_input)
        self.loop.run()
    def input(self, inpt, raw):
        return inpt
    def unhandled_input(self, key):
        if key == 'q' or key == 'Q':
            raise urwid.ExitMainLoop()
        elif key == 'ctrl c':
            if self.flag:
                raise urwid.ExitMainLoop()
            self.helper.set_text('got Ctrl-C')
            self.flag = True
        else:
            self.flag = False
            self.helper.text.set_text(str(self.colview.selectable()))

    def set_df(self, df):
        self.colview.set_df(df)

browser = None

def help(text):
    if browser:
        browser.helper.set_text(text)

if __name__ == '__main__':
    pd.set_option('display.max_rows', 9999)
    pd.set_option('display.width', None)
    browser = DFBrowser(pd.read_csv(sys.argv[1]))
    browser.start()
