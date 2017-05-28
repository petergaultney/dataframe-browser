#!/usr/bin/env python
import urwid
import urwid_utils
import sys, re, os
import pandas as pd
import dataframe_browser

# debug stuff
import timeit

debug_file = open('debug.log', 'w+')
def myprint(x):
    debug_file.write(str(x) + '\n')
    debug_file.flush()
print = myprint

start_times = list()
def st():
    global start_times
    start_times.append(timeit.default_timer())

def end(name):
    global start_times
    elapsed_time = timeit.default_timer() - start_times.pop()
    if elapsed_time > 5:
        print('\n')
    print('{:20} {:10.2f} ms'.format(name, elapsed_time * 1000))
#end debug stuff

PAGE_SIZE = 20

# this stuff captures Ctrl-C
# ui = urwid.raw_display.RealTerminal()
# ui.tty_signal_keys('undefined', 'undefined', 'undefined', 'undefined',
#                    'undefined')

def generate_str_for_col(df, col_name, top_row=0, bot_row=None):
    if not bot_row:
        bot_row = len(df) # TODO
    string = df[[col_name]].iloc[top_row:bot_row].to_string(index=False)
    all_strs = string.split('\n')
    assert len(all_strs[0].strip()) != 0 # need a non-blank column label
    while len(all_strs[1].strip()) == 0:
        del all_strs[1]
    assert len(all_strs) - 1 == len(df)
    return all_strs

def _pack(columns): # this just exists to cut down code bloat
    return columns.options(width_type='pack')
def _given(columns, nc):
    return columns.options('given', nc)

# displays a dataframe either in the provided cols object, replacing the contents,
# or in a new object, if no cols object provided
def disp_df_in_cols(cols, df, display_cols, cached_col_strs, top_row, focus_row):
    end('kp to kp')
    st()
    st()
    # if focus_col is None:
    try:
        focus_col = cols.focus_position
    except:
        focus_col = 0
    del cols.contents[:]

    top_row += 1 # hack to display column name
    focus_row += 1
    for idx, col in enumerate(display_cols):
        disp_attr = 'def'
        if idx == focus_col:
            disp_attr = 'active_col'
        if col not in cached_col_strs:
            cached_col_strs[col] = generate_str_for_col(df, col)
        bot_row = top_row + 70 # TODO arbitrary constant

        col_strs = cached_col_strs[col]

        # not-focused rows at top
        max_col_width = len(col_strs[0])
        before_foc_str = col_strs[0] # header
        if top_row > 1 and idx == focus_col:
            before_foc_str += '\n' + ' ' * (max_col_width - 3) + '...'
        else:
            before_foc_str += '\n'
        if top_row < focus_row:
            before_foc_str += '\n' + '\n'.join(col_strs[top_row:focus_row])
        # focused row
        focus_row_str = col_strs[focus_row]
        max_col_width = max(max_col_width, len(focus_row_str))
        # after focused rows at bottom
        after_foc_str = '\n'.join(col_strs[focus_row + 1: bot_row])

        # three layer version
        pile = urwid.Pile([])
        pile.contents.append((urwid.AttrMap(SelectableText(before_foc_str), disp_attr), ('pack', None)))
        pile.contents.append((urwid.AttrMap(SelectableText(focus_row_str), 'active_row'), ('pack', None)))
        pile.contents.append((urwid.AttrMap(SelectableText(after_foc_str), disp_attr), ('pack', None)))
        pile.focus_position = 1
        cols.contents.append((pile, _given(cols, len(focus_row_str))))

        # one layer version - no active row
        # cols.contents.append(
        #     (urwid.AttrMap(SelectableText(before_foc_str + focus_row_str + after_foc_str),
        #                                   disp_attr),
        #                    _pack(cols)))

    try:
        cols.focus_position = focus_col
    except Exception as e:
        hint(str(e))
    end('df col')
    return cols


class HelpText(urwid.WidgetWrap):
    def __init__(self):
        self.text = urwid.Text('Help Area')
        urwid.WidgetWrap.__init__(self, self.text)
    def set_text(self, text):
        self.text.set_text(text)
    def keypress(self, size, key):
        raise urwid.ExitMainLoop('focus on help text!')

class Minibuffer(urwid.WidgetWrap):
    def __init__(self, urwid_browser):
        self.urwid_browser = urwid_browser
        self.edit_text = urwid_utils.AdvancedEdit(caption='browsing... ', multiline=False)
        urwid.WidgetWrap.__init__(self, self.edit_text)
    def add(self, completion_cb=None):
        if completion_cb is not None:
            self.edit_text.setCompletionMethod(completion_cb)
        self.edit_text.set_caption('add column: ')
        self.urwid_browser.frame.focus_position = 'footer'
        self.enter_cb = None
    def focus_granted(self):
        self.edit_text.set_caption('add: ')
    def focus_removed(self):
        self.edit_text.set_caption('browsing... ')
    def give_away_focus(self):
        self.urwid_browser.focus_browser()
    def merge(self, completion_cb=None):
        # TODO this looks bad
        self.edit_text.setCompletionMethod(completion_cb)
        self.edit_text.set_caption('merge with: ')
        self.urwid_browser.frame.focus_position = 'footer'
    def keypress(self, size, key):
        if key == 'enter':
            name = self.edit_text.get_edit_text()
            print(name)
            if self.urwid_browser.colview.add_col(name):
                # we accept this input
                self.edit_text.set_edit_text('')
                self.urwid_browser.frame.focus_position = 'body'
            else:
                self.urwid_browser.helper.set_text(str(name) + ' not in df')
                # self.browser.helper.set_text(str(list(self.browser.colview.df)))
        elif key == 'esc':
            self.give_away_focus()
        elif key == 'ctrl c':
            # raise urwid.ExitMainLoop()
            self.give_away_focus()
        else:
            return self.edit_text.keypress(size, key)

class SelectableText(urwid.Text):
    def __init__(self, markup, align='left', wrap='clip', layout=None):
        super(self.__class__, self).__init__(markup, align, wrap, layout)
    def selectable(self):
        return True # this allows us to assign focus to the columns of text
    # def keypress(self, size, key):
    #     return None


class UrwidDFColumnView(urwid.WidgetWrap):
    def __init__(self, urwid_browser, df_browser):
        self.urwid_browser = urwid_browser
        self.df_browser = df_browser
        # self.col_viewer = col_viewer
        self.urwid_cols = urwid.Columns([], dividechars=1)
        self.top_row = 0
        self.focus_row = 0
        urwid.WidgetWrap.__init__(self, self.urwid_cols)
        self.cached_col_str_lists = dict()
        for col in self.df_browser.display_cols:
            self.cached_col_str_lists[col] = generate_strs_for_col(self.df_browser.df, col)

    def update_view(self, browser=None):
        if not browser:
            browser = self.df_browser
        print(str(self.top_row) + ' ' + str(self.focus_row))
        disp_df_in_cols(self.urwid_cols, browser.df, browser.display_cols,
                        self.cached_col_str_lists, self.top_row, self.focus_row)

    def scroll_down(self, num_rows=1):
        self.focus_row += num_rows
        if self.focus_row >= len(self.df_browser.df):
            self.focus_row = len(self.df_browser.df) - 1 # todo this should take into account the height of the widget
        while self.focus_row > self.top_row + 25: # TODO this is arbitrary
            self.top_row += 1
        self.update_view()

    def scroll_up(self, num_rows=1):
        self.focus_row -= num_rows
        if self.focus_row < 0:
            self.focus_row = 0
        while self.focus_row < self.top_row + 10 and self.top_row > 0: # TODO this is arbitrary
            self.top_row -= 1
        self.update_view()

    def set_focus(self, num):
        if num < 0:
            num = 0
        if num >= len(self.urwid_cols.contents):
            num = len(self.urwid_cols.contents) - 1
        try:
            self.urwid_cols.focus_position = num
            self.update_view()
            return True
        except:
            hint('failed to set focus to '+ str(num + 1))
            return False

    def undo(self):
        self.df_browser.undo()

    def add_col(self, col_name, idx=None):
        try:
            if not idx or idx < 0 or idx > self.urwid_cols.focus_position:
                idx = self.urwid_cols.focus_position
        except: # if for some reason cols.focus_position doesn't exist at all...
            idx = 0
        return self.df_browser.add_col(col_name, idx)

    def hide_current_col(self):
        return self.df_browser.remove_col_by_index(self.urwid_cols.focus_position)

    def keypress(self, size, key):
        if key in '1234567890':
            # directly select the column #
            num = int(key) - 1
            if num == -1:
                num = 9
            self.set_focus(num)
        elif key == 'm':
            urwid_browser.minibuffer.merge(urwid_utils.ListCompleter(list(self.df_browser.smerge)))
        elif key == 'h':
            self.hide_current_col()
        elif key == 's':
            pass
        elif key == 'a':
            urwid_browser.minibuffer.add(urwid_utils.ListCompleter(list(self.df_browser.df), hint).complete)
        elif key == 'right' or key=='l':
            self.set_focus(self.urwid_cols.focus_position + 1)
        elif key == 'left' or key == 'h':
            self.set_focus(self.urwid_cols.focus_position - 1)
        elif key == 'down' or key == 'j':
            self.scroll_down()
        elif key == 'up' or key == 'k':
            self.scroll_up()
        elif key == 'u':
            self.undo()
        elif key == 'q':
            raise urwid.ExitMainLoop()
        elif key == 'page up':
            self.scroll_up(PAGE_SIZE)
        elif key == 'page down':
            self.scroll_down(PAGE_SIZE)
        elif key == '/':
            self.urwid_browser.focus_minibuffer()
        elif key == ',':
            if self.df_browser.shift_col(self.urwid_cols.focus_position, -1):
                self.urwid_cols.focus_position -= 1
                self.update_view() # TODO this incurs a double update penalty
        elif key == '.':
            if self.df_browser.shift_col(self.urwid_cols.focus_position, 1):
                self.urwid_cols.focus_position += 1
                self.update_view()
        else:
            hint('CV: ' + key)
            return None
    # def mouse_event(self, size, event, button, col, row, focus):
    #     return None

def trace_keyp(size, key):
    if key == 'p':
        raise urwid.ExitMainLoop()
    else:
        return None

palette = [
    ('active_col', 'light blue', 'black'),
    ('def', 'white', 'black'),
    ('help', 'black', 'light gray'),
    ('moving', 'light red', 'black'),
    ('active_row', 'dark red', 'black'),
    ]


class UrwidDFBrowser:
    def __init__(self, smart_merger=None):
        self.df_browser = dataframe_browser.DFBrowser(smart_merger)
        self.helper = HelpText()
        self.minibuffer = Minibuffer(self)
        self.colview = UrwidDFColumnView(self, self.df_browser)
        self.df_browser.add_change_callback(self.colview.update_view)
        self.inner_frame = urwid.Frame(urwid.Filler(self.colview, valign='top'),
                                       footer=urwid.AttrMap(self.helper, 'help'))
        self.frame = urwid.Frame(self.inner_frame, footer=self.minibuffer)
    def start(self):
        self.loop = urwid.MainLoop(self.frame, palette, # input_filter=self.input,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()
    def focus_minibuffer(self):
        self.frame.focus_position = 'footer'
        self.minibuffer.focus_granted()
    def focus_browser(self):
        self.frame.focus_position = 'body'
        self.minibuffer.focus_removed()
    def keypress(self, size, key):
        raise urwid.ExitMainLoop('keypress in DFbrowser!')
    # def input(self, inpt, raw):
    #     print('ipt')
    #     return inpt
    def unhandled_input(self, key):
        if key == 'q' or key == 'Q':
            raise urwid.ExitMainLoop()
        elif key == 'ctrl c':
            self.helper.set_text('got Ctrl-C')
        else:
            hint('unhandled input ' + str(key))

urwid_browser = None

def hint(text):
    if urwid_browser:
        urwid_browser.helper.set_text(text)

def read_all_dfs_from_dir(directory):
    df_merger = dataframe_browser.DataFrameSmartMerger()
    for fn in os.listdir(directory):
        df = pd.DataFrame.from_csv(directory + os.sep + fn)
        df_merger.add(df, fn[:-4])
    return df_merger

def start_browser(df_c, df_name='dubois_mathlete_identities'):
    st()
    urwid_browser = UrwidDFBrowser(df_c)
    urwid_browser.df_browser.merge_df(df_c[df_name])
    urwid_browser.start()

if __name__ == '__main__':
    # pd.set_option('display.max_rows', 9999)
    # pd.set_option('display.width', None)

    # import dubois
    # conn = dubois.get_admin_conn()

    # import datetime_utils
    # print('Welcome to the DuBois Project Data Explorer!')
    # print('Press TAB twice at any time to view the available commands or options.')
    # print('Use Ctrl-C to return to previous level, and Ctrl-D to quit.')
    # # start readline
    # import readline
    # readline.parse_and_bind('tab: complete')

    try:
        local_data = sys.argv[1]
        start_browser(read_all_dfs_from_dir(local_data))
    except (KeyboardInterrupt, EOFError) as e:
        print('\nLeaving the DuBois Project Data Explorer.')

# if __name__ == '__main__':
#     start_interactive_query_loop(conn)
