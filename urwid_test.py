#!/usr/bin/env python
import urwid
import sys, re, os
import pandas as pd

class HelpText(urwid.WidgetWrap):
    def __init__(self):
        self.text = urwid.Text('Help Area')
        urwid.WidgetWrap.__init__(self, self.text)

class Minibuffer(urwid.WidgetWrap):
    def __init__(self, browser):
        self.browser = browser
        self.text = urwid.Edit(caption='cmd: ', multiline=False)
        urwid.WidgetWrap.__init__(self, self.text)
    def keypress(self, size, key):
        if key == 'enter':
            name = self.text.get_text()
            self.text.set_edit_text('')
            if name in list(self.browser.colview.df):
                self.browser.colview.dcols.insert(self.browser.colview.cols.focus_position, name)
                self.browser.frame.focus_position = 'body'
        elif key == 'esc':
            raise urwid.ExitMainLoop()
        else:
            return self.text.keypress(size, key)

class SelectableText(urwid.Text):
    def __init__(self, markup, align='left', wrap='space', layout=None):
        super(self.__class__, self).__init__(markup, align, wrap, layout)
    def selectable(self):
        return True
    def keypress(self, size, key):
        return None
        
class DFColumnView(urwid.WidgetWrap):
    def __init__(self, browser):
        self.browser = browser
        self.df = pd.DataFrame()
        self.cols = urwid.Columns([urwid.Edit('A DataFrame will be displayed here.')],
                                  dividechars=1)
        self.dcols = list(self.df)
        urwid.WidgetWrap.__init__(self, self.cols)
    def set_df(self, df):
        self.df = df
        self.dcols = list(df)
        self.disp_cols()
    def disp_cols(self, dcols=None):
        if dcols:
            self.dcols = dcols
        try:
            fp = self.cols.focus_position
        except:
            fp = 0
        del self.cols.contents[:]
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
        
    def _opt(self):
        return self.cols.options(width_type='pack')
    def set_focus(self, num):
        try:
            self.cols.focus_position = num
            self.browser.helper.text.set_text(str(num + 1))
        except:
            self.browser.helper.text.set_text('failed to set focus to '+ str(num + 1))
        self.disp_cols()
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
            del self.dcols[self.cols.focus_position]
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
    def start(self):
        self.loop = urwid.MainLoop(self.frame, palette, unhandled_input=self.unhandled_input)
        self.loop.run()
    def unhandled_input(self, key):
        if key == 'q' or key == 'Q':
            raise urwid.ExitMainLoop()
        elif key == 'p':
            self.set_df(pd.read_csv(sys.argv[1]))
        else:
            self.helper.text.set_text(str(self.colview.selectable()))

    def set_df(self, df):
        self.colview.set_df(df)

if __name__ == '__main__':
    pd.set_option('display.max_rows', 9999)
    pd.set_option('display.width', None)
    browser = DFBrowser()
    browser.start()
