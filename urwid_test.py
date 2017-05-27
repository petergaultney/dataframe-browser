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
def disp_df_in_cols(cols, df, dcols, cached_col_strs, top_row, focus_row):
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
    for idx, col in enumerate(dcols):
        disp_attr = 'def'
        if idx == focus_col:
            disp_attr = 'active_col'
        if col not in cached_col_strs:
            cached_col_strs[col] = generate_str_for_col(df, col)
        bot_row = top_row + 70 # TODO arbitrary constant

        col_strs = cached_col_strs[col]

        # not-focused rows at top
        max_col_width = len(col_strs[0])
        before_foc_str = col_strs[0] + '\n' # this is the header
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
    def __init__(self, browser):
        self.browser = browser
        self.text = urwid_utils.AdvancedEdit(caption='browsing...', multiline=False)
        urwid.WidgetWrap.__init__(self, self.text)
    def add(self, completion_cb=None):
        if completion_cb is not None:
            self.text.setCompletionMethod(completion_cb)
        self.text.set_caption('add column: ')
        self.browser.frame.focus_position = 'footer'
        self.enter_cb = None
    def _get_focus(self):
        self.browser.frame.focus_position = 'footer'
    def merge(self, completion_cb=None):
        self.text.setCompletionMethod(completion_cb)
        self.text.set_caption('merge with: ')
        self.browser.frame.focus_position = 'footer'
    def keypress(self, size, key):
        if key == 'enter':
            name = self.text.get_edit_text()
            if self.browser.colview.add_col(name):
                # we accept this input
                self.text.set_edit_text('')
                self.browser.frame.focus_position = 'body'
            else:
                self.browser.helper.set_text(str(name) + ' not in df')
                # self.browser.helper.set_text(str(list(self.browser.colview.df)))
        elif key == 'esc':
            self.text.set_caption('browsing...')
            self.browser.frame.focus_position = 'body'
        elif key == 'ctrl c':
            raise urwid.ExitMainLoop()
        else:
            return self.text.keypress(size, key)

class SelectableText(urwid.Text):
    def __init__(self, markup, align='left', wrap='clip', layout=None):
        super(self.__class__, self).__init__(markup, align, wrap, layout)
    def selectable(self):
        return True # this allows us to assign focus to the columns of text
    # def keypress(self, size, key):
    #     return None


def add_column(columns, col_name, index):
    if col_name in columns and columns[index] == col_name:
        return columns # done. no new list, b/c no change happened.

    new_cols = columns[:] # make new list, b/c we're making a change
    if col_name in columns:
        cur_idx = columns.index(col_name)
        new_cols.insert(index, columns.pop(cur_idx))
    else:
        new_cols.insert(index, col_name)
    return new_cols

def remove_column(columns, col_name):
    if col_name not in columns:
        return columns
    else:
        return remove_column_by_index(columns, columns.index(col_name))

def remove_column_by_index(columns, index):
    if index < len(columns) and index >= 0:
        new_cols = columns[:]
        del new_cols[index]
        return new_cols
    return columns

class UrwidDFColumnView(urwid.WidgetWrap):
    def __init__(self, browser):
        self.browser = browser
        # self.col_viewer = col_viewer
        self.cols = urwid.Columns([], dividechars=1)
        self.top_row = 0
        self.focus_row = 0
        urwid.WidgetWrap.__init__(self, self.cols)
        self.cached_col_str_lists = dict()
        for col in self.browser.dcols:
            self.cached_col_str_lists[col] = generate_strs_for_col(browser.df, col)

    def update_view(self, browser=None):
        # ignore passed browser
        if browser is None:
            browser = self.browser
        disp_df_in_cols(self.cols, browser.df, browser.dcols,
                        self.cached_col_str_lists, self.top_row, self.focus_row)

    def scroll_down(self, num_rows=1):
        self.focus_row += num_rows
        if self.focus_row >= len(self.browser.df):
            self.focus_row = len(self.browser.df) - 1 # todo this should take into account the height of the widget
        while self.focus_row > self.top_row + 25: # TODO this is arbitrary
            self.top_row += 1
        self.update_view()
    def scroll_up(self, num_rows=1):
        self.focus_row -= num_rows
        if self.focus_row < 0:
            self.focus_row = 0
        while self.focus_row < self.top_row + 10:
            self.top_row -= 1
        self.update_view()

    def set_focus(self, num):
        if num < 0:
            num = 0
        if num >= len(self.cols.contents):
            num = len(self.cols.contents) - 1
        try:
            self.cols.focus_position = num
            self.update_view()
            return True
        except:
            hint('failed to set focus to '+ str(num + 1))
            return False

    def add_col(self, col_name, idx=None):
        try:
            if not idx or idx < 0 or idx > self.cols.focus_position:
                idx = self.cols.focus_position
        except: # if for some reason cols.focus_position doesn't exist at all...
            idx = 0
        return self.browser.add_col(col_name, idx)

    def remove_col(self):
        return self.browser.remove_col_by_index(self.cols.focus_position)

    def keypress(self, size, key):
        if key in '1234567890':
            num = int(key) - 1
            if num == -1:
                num = 9
            self.set_focus(num)
        elif key == 'm':
            urwid_browser.mini.merge(urwid_utils.ListCompleter(list(self.browser.smerge)))
        elif key == 'r':
            self.remove_col()
        elif key == 's':
            pass
        elif key == 'a':
            urwid_browser.mini.add(urwid_utils.ListCompleter(list(self.df), hint).complete)
        elif key == 'right' or key=='l':
            self.set_focus(self.cols.focus_position + 1)
        elif key == 'left' or key == 'h':
            self.set_focus(self.cols.focus_position - 1)
        elif key == 'down' or key == 'j':
            self.scroll_down()
        elif key == 'up' or key == 'k':
            self.scroll_up()
        elif key == 'u':
            self.undo()
        elif key == 'q':
            raise urwid.ExitMainLoop()
        elif key == 'page up':
            self.scroll_up(20)
        elif key == 'page down':
            self.scroll_down(20)
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

# the DFBrowser basically maintains an undo history
# and helps provide a basic API for how a dataframe can be viewed.
class DFBrowser(object):
    def __init__(self, smart_merger=None):
        self.df = None
        self.dcols = list()
        self.df_hist = list()
        self.dcols_hist = list()
        self.undo_hist = list()
        self.smerge = smart_merger
        self.change_cbs = list()

    def _msg_cbs(self):
        for cb in self.change_cbs:
            cb(self)

    def sort_cols(self, columns):
        pass

    def merge_df(self, new_df):
        if self.df is None:
            print('adding new df!')
            self.df = new_df
            self.dcols = list(new_df)
            self._msg_cbs()
            return True

        # assume i already have columns. then get the difference between
        # my currently displays columns and the columns that this dataframe will add.
        # if columns are going to change names, it should preferably be
        # only the new columns that get new names. This allows me to ignore
        # any name conflicts.
        # do merge
        if self.smerge is not None:
            try:
                merged_df = self.smerge(self.df, new_df)
                self.df_hist.append(self.df)
                self.undo_hist.append(self.df_hist)
                self.df = merged_df
                self._msg_cbs()
                return True
            except:
                pass
        return False

    def add_col(self, col_name, index):
        if col_name in list(self.df):
            new_cols = add_column(self.dcols, col_name, index)
            if new_cols is not self.dcols:
                self.dcols_hist.append(self.dcols)
                self.undo_hist.append(self.dcols_hist)
                self.dcols = new_cols
                self._msg_cbs()
                return True
        return False

    def remove_col(self, col_name):
        new_cols = remove_column(self.dcols, col_name)
        return self._after_remove_col(new_cols)

    def remove_col_by_index(self, index):
        new_cols = remove_column_by_index(self.dcols, index)
        return self._after_remove_col(new_cols)

    def _after_remove_col(self, new_cols):
        if new_cols is not self.dcols:
            self.dcols_hist.append(self.dcols) # shallow copy
            self.dcols = new_cols
            self._msg_cbs()
            return True
        return False

    def undo(self, n=1):
        while n > 0 and len(self.undo_hist) > 0:
            change_type = self.undo_hist.pop()
            if change_type == self.df_hist:
                self.df = self.df_hist.pop()
            elif change_type == self.dcol_hist:
                self.dcols = self.dcol_hist.pop()
            else:
                break
        self._msg_cbs()

    def add_change_callback(self, cb):
        if cb not in self.change_cbs:
            self.change_cbs.append(cb)

class UrwidDFBrowser:
    def __init__(self, smart_merger=None):
        self.browser = DFBrowser(smart_merger)
        self.helper = HelpText()
        self.mini = Minibuffer(self)
        self.colview = UrwidDFColumnView(self.browser)
        self.browser.add_change_callback(self.colview.update_view)
        self.inner_frame = urwid.Frame(urwid.Filler(self.colview, valign='top'),
                                       footer=urwid.AttrMap(self.helper, 'help'))
        self.frame = urwid.Frame(self.inner_frame, footer=self.mini)
    def start(self):
        self.loop = urwid.MainLoop(self.frame, palette, # input_filter=self.input,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()

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
    urwid_browser.browser.merge_df(df_c[df_name])
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
