#!/usr/bin/env python
import urwid
import urwid_utils
import sys, re, os
import pandas as pd
import dataframe_browser
from dataframe_browser import print, st, end


PAGE_SIZE = 20

# this stuff captures Ctrl-C
# ui = urwid.raw_display.RealTerminal()
# ui.tty_signal_keys('undefined', 'undefined', 'undefined', 'undefined',
#                    'undefined')

def generate_str_for_col(df, col_name, top_row=0, bot_row=None):
    if not bot_row:
        bot_row = len(df) # TODO
    string = df[[col_name]].iloc[top_row:bot_row].to_string(index=False) # slower - makes a copy
    # string = col_name + '\n\n'
    # string += df.ix[top_row:bot_row,col_name].to_string(index=False) # faster
    all_strs = string.split('\n')
    assert len(all_strs[0].strip()) != 0 # need a non-blank column label
    while len(all_strs[1].strip()) == 0 or all_strs[1] == 'itemName':
        del all_strs[1]
    # assert len(all_strs) - 1 == len(df)
    return all_strs

def _pack(columns): # this just exists to cut down code bloat
    return columns.options(width_type='pack')
def _given(columns, nc):
    return columns.options('given', nc)

def new_display_df_in_cols(urwid_cols, df_view):
    end('kp to kp') # DEBUG
    st() # DEBUG
    st() # DEBUG
    try:
        focus_col = urwid_cols.focus_position
    except:
        focus_col = 0
    del urwid_cols.contents[:]

    for idx, col_name in enumerate(df_view.df_history.display_cols):
        pile = create_column_pile(urwid_cols, df_view, col_name, idx == focus_col)
        column_width = df_view.width(col_name)
        # col_disp_attr = 'def' if not idx == focus_col else 'active_col'
        # column_header = df_view.header(col_name)
        # column_strings = df_view.lines(col_name)
        # column_width = df_view.width(col_name)
        # part_one = column_header
        # part_one += '\n...\n' if df_view.top_row > 1 and idx == focus_col else '\n\n'
        # part_one += '\n'.join(column_strings[0:selected_row])
        # part_two =  '\n'.join(column_strings[selected_row + 1: len(column_strings)])
        # if idx == focus_col:
        #     selected_row_attr = 'active_element'
        #     urwid_browser.helper.set_text(str(df_view.selected_row_content(col_name))) # TODO this breaks encapsulation
        # else:
        #     selected_row_attr = 'active_row'
        # pile = urwid.Pile([])
        # pile.contents.append((urwid.AttrMap(SelectableText(part_one), col_disp_attr), ('pack', None)))
        # pile.contents.append((urwid.AttrMap(SelectableText(column_strings[selected_row]), selected_row_attr), ('pack', None)))
        # pile.contents.append((urwid.AttrMap(SelectableText(part_two), col_disp_attr), ('pack', None)))
        # pile.focus_position = 1
        urwid_cols.contents.append((pile, _given(urwid_cols, column_width)))
    try:
        urwid_cols.focus_position = focus_col
    except Exception as e:
        hint(str(e))
    end('df col')

def create_column_pile(urwid_cols, df_view, col_name, is_focus_col):
    col_disp_attr = 'def' if not is_focus_col else 'active_col'
    selected_row_attr = 'active_element' if is_focus_col else 'active_row'
    selected_row = df_view.selected_relative

    column_header = df_view.header(col_name)
    column_strings = df_view.lines(col_name)
    part_one = column_header
    assert not part_one.endswith('\n')
    part_one += '\n...\n' if df_view.top_row > 1 and is_focus_col else '\n\n'
    part_one += '\n'.join(column_strings[0:selected_row])
    part_two =  '\n'.join(column_strings[selected_row + 1: len(column_strings)])
    return create_column_from_text_and_attrib(part_one, column_strings[selected_row], part_two,
                                              col_disp_attr, selected_row_attr)


def create_column_from_text_and_attrib(part_one, selected_row_text, part_two, col_attrib, selected_row_attrib):
    pile = urwid.Pile([])
    pile.contents.append((urwid.AttrMap(SelectableText(part_one), col_attrib), ('pack', None)))
    pile.contents.append((urwid.AttrMap(SelectableText(selected_row_text), selected_row_attrib), ('pack', None)))
    pile.contents.append((urwid.AttrMap(SelectableText(part_two), col_attrib), ('pack', None)))
    pile.focus_position = 1
    return pile


def set_attrib_on_col_pile(pile, is_focus_col):
    pile.contents[0][0].set_attr_map({None: 'active_col' if is_focus_col else 'def'})
    pile.contents[1][0].set_attr_map({None: 'active_element' if is_focus_col else 'active_row'})
    pile.contents[2][0].set_attr_map({None: 'active_col' if is_focus_col else 'def'})

class HelpText(urwid.WidgetWrap):
    def __init__(self):
        self.text = urwid.Text('Help Area')
        urwid.WidgetWrap.__init__(self, self.text)
    def set_text(self, text):
        self.text.set_text(text)
    def show_basic_commands(self):
        self.set_text('(hjkl) move focus; (H)ide; (u)ndo; (m)erge; (+-) adjust col size; (,.) shift col; / enter command mode')
    def show_command_options(self):
        self.set_text('type column name to add, then press enter. Press Esc to return to browsing.')
    def keypress(self, size, key):
        raise urwid.ExitMainLoop('somehow put focus on help text!')

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
        self.df_view = dataframe_browser.DataframeView(self.df_browser)
        # self.col_viewer = col_viewer
        self.urwid_cols = urwid.Columns([], dividechars=1)
        # self.top_row = 0
        # self.focus_row = 0
        urwid.WidgetWrap.__init__(self, self.urwid_cols)
        # self.cached_col_str_lists = dict()
        # for col in self.df_browser.display_cols:
        #     self.cached_col_str_lists[col] = generate_strs_for_col(self.df_browser.df, col)

    def update_view(self, browser=None):
        if not browser:
            browser = self.df_browser
        # print(str(self.top_row) + ' ' + str(self.focus_row))
        # disp_df_in_cols(self.urwid_cols, browser.df, browser.display_cols,
        #                 self.cached_col_str_lists, self.top_row, self.focus_row)
        new_display_df_in_cols(self.urwid_cols, self.df_view)
        self.update_text()

    def update_text(self):
        self.urwid_browser.helper.set_text(str(self.df_view.selected_row_content(
            self.df_browser.display_cols[self.urwid_cols.focus_position]))) # TODO this breaks encapsulation
    # # TODO move everything having to do with focus position and 'view'
    # # out of this class and into either the class containing the undo history,
    # # or into another class that would wrap that class.
    # # The question is basically, is keeping track of which columns are hidden
    # # and the dataframe history itself strongly related to what is currently being
    # # viewed in a limited window?
    # # Either way, this class should simply provide an extension of that code
    # # into the Urwid world, and should not itself keep track of any state.

    def scroll(self, num_rows):
        self.df_view.scroll_rows(num_rows)
        self.update_view()

    def set_focus(self, num):
        if num < 0:
            num = 0
        if num >= len(self.urwid_cols.contents):
            num = len(self.urwid_cols.contents) - 1
        try:
            focus_pos = self.urwid_cols.focus_position
            if self.urwid_cols.focus_position != num:
                set_attrib_on_col_pile(self.urwid_cols.contents[focus_pos][0], False)
                set_attrib_on_col_pile(self.urwid_cols.contents[num][0], True)
                self.urwid_cols.focus_position = num
                self.update_text()
            return True
        except Exception as e:
            hint('failed to set focus to '+ str(num + 1))
            print(e)
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
        return self.df_browser.hide_col_by_index(self.urwid_cols.focus_position)

    def keypress(self, size, key):
        if key in '1234567890':
            # directly select the column #
            num = int(key) - 1
            if num == -1:
                num = 9
            self.set_focus(num)
        elif key == 'm':
            urwid_browser.minibuffer.merge(urwid_utils.ListCompleter(list(self.df_browser.smerge)))
        elif key == 'H':
            self.hide_current_col()
        elif key == 's':
            pass # sort? search?
        elif key == 'f':
            pass # filter?
        elif key == 'a':
            urwid_browser.minibuffer.add(urwid_utils.ListCompleter(list(self.df_browser.df), hint).complete)
        elif key == 'right' or key=='l':
            self.set_focus(self.urwid_cols.focus_position + 1)
        elif key == 'left' or key == 'h':
            self.set_focus(self.urwid_cols.focus_position - 1)
        elif key == 'down' or key == 'j':
            self.scroll(+1)
        elif key == 'up' or key == 'k':
            self.scroll(-1)
        elif key == 'u':
            self.undo()
        elif key == 'q':
            raise urwid.ExitMainLoop()
        elif key == 'page up':
            self.scroll(-PAGE_SIZE)
        elif key == 'page down':
            self.scroll(PAGE_SIZE)
        elif key == '/':
            self.urwid_browser.focus_minibuffer()
        elif key == '?':
            self.urwid_browser.helper.show_basic_commands()
        elif key == ',' or key == '>':
            if self.df_browser.shift_column(self.urwid_cols.focus_position, -1):
                self.urwid_cols.focus_position -= 1
                self.update_view() # TODO this incurs a double update penalty
        elif key == '.' or key == '<':
            if self.df_browser.shift_column(self.urwid_cols.focus_position, 1):
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
    ('active_element', 'yellow', 'black'),
    ]


class UrwidDFBrowser:
    def __init__(self, smart_merger=None):
        self.df_browser = dataframe_browser.DFBrowser(smart_merger)
        self.helper = HelpText()
        self.helper.show_basic_commands()
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
        self.helper.show_command_options()
    def focus_browser(self):
        self.frame.focus_position = 'body'
        self.minibuffer.focus_removed()
        self.helper.show_basic_commands()
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

def start_browser(df_sm, df_name='dubois_mathlete_identities'):
    st()
    global urwid_browser
    urwid_browser = UrwidDFBrowser(df_sm)
    urwid_browser.df_browser.merge_df(df_sm[df_name])
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
