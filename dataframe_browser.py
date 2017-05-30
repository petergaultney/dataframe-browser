from collections import defaultdict
import pandas as pd
import numpy as np
from smartmerge import DataframeSmartMerger

# UI debug printing
import timeit

debug_file = open('debug.log', 'w+')
def myprint(*args):
    strs = [str(x) for x in args]
    debug_file.write(' '.join(strs) + '\n')
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

def find_and_remove_list_item(lst, item):
    try:
        return remove_list_index(lst, lst.index(item))
    except:
        return lst

def remove_list_index(lst, index):
    try:
        new_lst = lst[:]
        del new_lst[index]
        return new_lst
    except:
        return lst

def shift_list_item(lst, idx, to_right):
    if idx < len(lst) and idx >= 0:
        new_idx = idx + to_right
        if new_idx < len(lst) and new_idx >= 0 and idx != new_idx:
            item = lst[idx]
            new_lst = lst[:]
            del new_lst[idx]
            new_lst.insert(new_idx, item)
            return new_lst
    return lst # no change

# the DFBrowser basically maintains an undo history
# and helps provide a basic API for how a dataframe can be viewed.
class DFBrowser(object):
    def __init__(self, smart_merger=None):
        self.df = None
        self.display_cols = list()
        self.df_hist = list()
        self.display_cols_hist = list()
        self.undo_hist = list()
        self.smerge = smart_merger
        self.change_cbs = list()

    def __len__(self):
        return len(self.df)

    def _msg_cbs(self):
        for cb in self.change_cbs:
            cb(self)

    def sort_cols(self, columns):
        pass

    def merge_df(self, new_df):
        if self.df is None:
            self.df = new_df
            self.display_cols = list(new_df)
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

    def shift_column(self, col_idx, num_cols_to_right):
        new_dcols = shift_list_item(self.display_cols, col_idx, num_cols_to_right)
        return self._change_display_cols(self.display_cols, new_dcols)

    def _change_display_cols(self, old_cols, new_cols):
        if old_cols != new_cols:
            self.display_cols_hist.append(old_cols)
            self.undo_hist.append(self.display_cols_hist)
            self.display_cols = new_cols
            self._msg_cbs()
            return True
        return False

    def add_col(self, col_name, index):
        if col_name in list(self.df):
            new_dcols = add_column(self.display_cols, col_name, index)
            return self._change_display_cols(self.display_cols, new_dcols)
        return False

    def hide_col_by_name(self, col_name):
        new_cols = find_and_remove_list_item(self.display_cols, col_name)
        return self._change_display_cols(self.display_cols, new_dcols)

    def hide_col_by_index(self, index):
        new_cols = remove_list_index(self.display_cols, index)
        return self._change_display_cols(self.display_cols, new_cols)

    def undo(self, n=1):
        while n > 0 and len(self.undo_hist) > 0:
            change_type = self.undo_hist.pop()
            if change_type == self.df_hist:
                self.df = self.df_hist.pop()
            elif change_type == self.display_cols_hist:
                self.display_cols = self.display_cols_hist.pop()
            else:
                break
            n -= 1
        self._msg_cbs()

    # TODO add redo functionality, to undo an undo.
    # would only allow redos immediately after undos.

    @property
    def columns(self):
        return self.display_cols

    def add_change_callback(self, cb):
        if cb not in self.change_cbs:
            self.change_cbs.append(cb)

# class DataframeColumnCache(object):
#     def __init__(self, column_name, strings):
#         self.column_name = column_name # also header
#         self.strings = strings
#         self.max_width = len(column_name)
#         for s in self.strings:
#             self.max_width = max(self.max_width, len(s))

def get_dataframe_strings_for_column(df, column_name, top_row, bottom_row, justify='right'):
    print('refreshing cache', top_row, bottom_row)
    # data_string = df.ix[top_row:bottom_row,[df.columns.get_loc(column_name)]].to_string(index=False, index_names=False, header=False)
    data_string = df.ix[top_row:bottom_row].to_string(index=False, index_names=False, header=False,
                                                      columns=[column_name], justify=justify)
    strs = data_string.split('\n')
    assert len(strs) == bottom_row - top_row
    # while len(strs[0]) < len(strs[1]):
    #     strs[0] = ' ' + strs[0]
    return strs

class DataframeColumnCache(object):
    MIN_WIDTH = 2
    MAX_WIDTH = 50
    DEFAULT_CACHE_SIZE = 200
    def __init__(self, src_df_func, column_name, std_cache_size=200, min_cache_on_either_side=50):
        self.get_src_df = src_df_func
        self.column_name = column_name
        self.is_numeric = np.issubdtype(self.get_src_df()[self.column_name].dtype, np.number)
        self.native_width = None
        self.assigned_width = None
        self.top_of_cache = 0
        self.row_strings = list()
        self._min_cache_on_either_side = min_cache_on_either_side
        self._std_cache_size = std_cache_size
    def _update_native_width(self):
        self.native_width = len(self.column_name)
        for idx, s in enumerate(self.row_strings):
            self.native_width = max(self.native_width, len(s))
            self.row_strings[idx] = s.strip()
            if not self.is_numeric and self.row_strings[idx] == 'NaN':
                self.row_strings[idx] = ''

    def change_width(self, n):
        if not self.assigned_width:
            if not self.native_width:
                self._update_native_width()
            self.assigned_width = self.native_width
        self.assigned_width += n
        self.assigned_width = max(DataframeColumnCache.MIN_WIDTH,
                                  min(DataframeColumnCache.MAX_WIDTH, self.assigned_width))
    @property
    def justify(self):
        return 'right' if self.is_numeric else 'left'
    @property
    def header(self):
        return self.column_name
    @property
    def width(self):
        return self.assigned_width if self.assigned_width else self.native_width
    @property
    def bottom_of_cache(self):
        return self.top_of_cache + len(self.row_strings)
    def rows(self, top_row, bottom_row):
        df = self.get_src_df()
        new_top_of_cache = max(top_row - self._min_cache_on_either_side, 0)
        new_bottom_of_cache = min(len(df), max(bottom_row + self._min_cache_on_either_side,
                                               new_top_of_cache + self._std_cache_size))
        new_cache = None
        if self.top_of_cache > top_row or self.bottom_of_cache < bottom_row:
            new_cache = get_dataframe_strings_for_column(df, self.column_name, new_top_of_cache,
                                                         new_bottom_of_cache, justify=self.justify)
        if new_cache:
            print('new cache from', new_top_of_cache, 'to', new_bottom_of_cache,
                  len(self.row_strings), len(new_cache))
            self.top_of_cache = new_top_of_cache
            self.row_strings = new_cache
            self._update_native_width()
        return self.row_strings[top_row-self.top_of_cache : bottom_row-self.top_of_cache]

    def _set_cache(self, string_cache, new_top_of_cache):
        self.top_of_cache = new_top_of_cache
        self.row_strings = string_cache
        self._update_native_width()

    def invalidate_cache(self):
        self.top_of_cache = 0
        self.row_strings = list()

class dfcol_defaultdict(defaultdict):
    def __init__(self, get_df):
        self.get_df = get_df
    def __missing__(self, column_name):
        assert column_name != None
        cc = DataframeColumnCache(lambda : self.get_df(), column_name)
        self[column_name] = cc
        return cc

class DataframeView(object):
    DEFAULT_VIEW_HEIGHT = 100
    def __init__(self, df_history, normal_cache_size=200, cache_above_top=50):
        self.df_history = df_history
        self._top_row = 0 # the top row in the dataframe that's in view
        self._selected_row = 0
        # self._normal_cache_size = normal_cache_size
        # self._normal_cache_above_top = cache_above_top
        self._view_height = DataframeView.DEFAULT_VIEW_HEIGHT
        self._column_cache = dfcol_defaultdict(lambda: self.df)
        # assert self._view_height <= self._normal_cache_size - cache_above_top
        self.scroll_margin_up = 10
        self.scroll_margin_down = 30

    # def column_cache(self, column_name):
    #     if column_name not in self._column_cache:
    #         self._column_cache[column_name] = DataframeColumnCache(lambda : self.df_history.df, column_name)
    #     return self._column_cache[column_name]

    # TODO : jump to row, jump to df fraction, jump to column, insert column at point, sort, search, filter

    @property
    def df(self):
        return self.df_history.df
    @property
    def top_row(self):
        return self._top_row
    @property
    def selected_relative(self):
        assert self._selected_row >= self._top_row and self._selected_row <= self._top_row + self._view_height
        return self._selected_row - self._top_row

    def header(self, column_name):
        return self._column_cache[column_name].header
    def width(self, column_name):
        return self._column_cache[column_name].width
    def lines(self, column_name, top_row=None, bottom_row=None):
        top_row = top_row if top_row != None else self._top_row
        bottom_row = bottom_row if bottom_row != None else min(top_row + self._view_height, len(self.df))
        return self._column_cache[column_name].rows(top_row, bottom_row)
    def selected_row_content(self, column_name):
        return self.df.ix[self._selected_row,column_name]
    def change_column_width(self, column_name, n):
        self._column_cache[column_name].change_width(n)
    def justify(self, column_name):
        return self._column_cache[column_name].justify

    # this method will have to be clever.
    # it will continually print out more and more lines of
    # the single column until it either finds a match or reaches the end of the
    # dataframe column. If it finds a match, it must return the row number
    # where the item was found.
    def search(self, column_name, search_string, down=True):
        pass

    def scroll_rows(self, n):
        """ positive numbers are scroll down; negative are scroll up"""
        self._selected_row = max(0, min(self._selected_row + n, len(self.df) - 1))
        if n > 0:
            while self._selected_row > self._top_row + self.scroll_margin_down:
                self._top_row += 1
        elif n < 0:
            while self._selected_row < self._top_row + self.scroll_margin_up and self._top_row > 0:
                self._top_row -= 1
        assert self._selected_row >= self._top_row and self._selected_row <= self._top_row + self._view_height

    def sort(self, column_name, reverse=False):
        self.df_history.sort(column_name, reverse)


class DFView(object):
    # this object contains the cached strings for displaying,
    # as well as the column titles, etc.
    # searches happen here, because we are simply iterating through the strings
    # for the next match.
    # sorts, filters, etc. also happen here, because they modify the dataframe and therefore
    # require re-computation of the viewing strings.
    # The history object can be responsible for maintaining the history
    # of dataframes and column hides/shifts
    def __init__(self, df_browser):
        pass
