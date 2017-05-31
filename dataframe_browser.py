from collections import defaultdict
import pandas as pd
import numpy as np
from smartmerge import DataframeSmartMerger

from _debug import *

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
# TODO provide separate callbacks for when the dataframe itself has changed
# vs when the column order/set has changed.
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

    def sort_columns(self, columns, ascending=True, algorithm='mergesort'): # we use mergesort to stay stable
        sorted_df = self.df.sort_values(columns, ascending=ascending, kind=algorithm)
        self._change_df(self.df, sorted_df)

    def merge_df(self, new_df):
        if self.df is None:
            self.df = new_df
            self.display_cols = list(new_df)
            self._msg_cbs()
            return True
        # do merge
        if self.smerge is not None:
            try:
                merged_df = self.smerge(self.df, new_df)
                return self._change_df(self.df, merged_df)
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

    def _change_df(self, old_df, new_df):
        self.df_hist.append(old_df)
        self.undo_hist.append(self.df_hist)
        self.df = new_df
        self._msg_cbs()

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
                print('attempting to undo df change')
                self.df = self.df_hist.pop()
            elif change_type == self.display_cols_hist:
                self.display_cols = self.display_cols_hist.pop()
            else:
                print('cannot undo this unknown operation')
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


class DataframeColumnSliceToStringList(object):
    def __init__(self, df, column, justify):
        self.df = df
        self.column = column
        self.justify = justify
    def __getitem__(self, val):
        return self.df.iloc[val].to_string(index=False, index_names=False, header=False,
                                           columns=[self.column], justify=self.justify).split('\n')
    def __len__(self):
        return len(self.df)

# chunk search utils
def not_at_end(lengthable, position, down):
    return position < len(lengthable) if down else position > 0

def get_next_chunk(sliceable, start_position, chunk_size, down):
    """includes start_position, of size chunk_size"""
    if not down:
        chunk_beg = max(0, start_position - chunk_size + 1)
        print('yielding chunk upwards from ', chunk_beg, 'to', start_position + 1)
        return sliceable[chunk_beg:start_position + 1], chunk_beg
    else:
        chunk_end = min(len(sliceable), start_position+chunk_size)
        print('yielding chunk downwards from', start_position, 'to', chunk_end)
        return sliceable[start_position:chunk_end], start_position

def search_chunk_yielder(sliceable, start_location, down=True, chunk_size=100):
    start_of_next_chunk = start_location
    while not_at_end(sliceable, start_of_next_chunk, down):
        yield get_next_chunk(sliceable, start_of_next_chunk, chunk_size, down)
        start_of_next_chunk = start_of_next_chunk + chunk_size if down else start_of_next_chunk - chunk_size
    raise StopIteration


# TODO allow this class to register directly with the dataframe owner
# for notification of when the backing dataframe has changed (and therefore the cache is invalid)
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
            sliceable_df = DataframeColumnSliceToStringList(df, self.column_name, self.justify)
            new_cache = sliceable_df[new_top_of_cache:new_bottom_of_cache]
            assert len(new_cache) == new_bottom_of_cache - new_top_of_cache
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

    def clear_cache(self):
        self.top_of_cache = 0
        self.row_strings = list()

    def search_cache(self, search_string, starting_row, down, case_insensitive):
        """Returns absolute index where search_string was found; otherwise -1"""
        # TODO this code 100% works, but could it be cleaner?
        print('***** NEW SEARCH', self.column_name, search_string, starting_row, down, case_insensitive)
        starting_row_in_cache = starting_row - self.top_of_cache
        print('running search on current cache, starting at row ', starting_row_in_cache)
        row_idx = search_list_for_str(self.row_strings, search_string, starting_row_in_cache, down, case_insensitive)
        if row_idx != None:
            print('found item at row_idx', row_idx + self.top_of_cache)
            return row_idx + self.top_of_cache
        else:
            print('failed local cache search - moving on to iterate through dataframe')
            # search by chunk through dataframe starting from current search position in cache
            end_of_cache_search = self.top_of_cache + len(self.row_strings) if down else self.top_of_cache
            df_sliceable = DataframeColumnSliceToStringList(self.get_src_df(), self.column_name, self.justify)
            for chunk, chunk_start_idx in search_chunk_yielder(df_sliceable, end_of_cache_search, down):
                chunk_idx = search_list_for_str(chunk, search_string, 0 if down else len(chunk) - 1, down, case_insensitive)
                if chunk_idx != None:
                    actual_idx = chunk_idx + chunk_start_idx
                    print('found', search_string, 'at chunk idx', chunk_idx, 'in chunk starting at', chunk_start_idx,
                          'which makes real idx', actual_idx, 'with result proof:', self.get_src_df().ix[actual_idx,self.column_name])
                    return actual_idx
                else:
                    print('not found in this chunk...')
            return None


def search_list_for_str(lst, search_string, starting_item, down, case_insensitive):
    """returns index into list representing string found, or None if not found"""
    search_string = search_string.lower() if case_insensitive else search_string
    search_slice_end = len(lst) if down else 0
    search_list = lst[starting_item:] if down else reversed(lst[:starting_item+1])
    print('searching list of size', len(lst), 'down' if down else 'up', 'from', starting_item, 'to', search_slice_end, 'for:', search_string)
    for idx, s in enumerate(search_list):
        s = s.lower() if case_insensitive else s
        if s.find(search_string) != -1:
            print('found! ', s, 'at', idx, 'starting from', starting_item, 'in list of len', len(lst), 'down?', down)
            return starting_item + idx if down else starting_item - idx
    return None

class dfcol_defaultdict(defaultdict):
    def __init__(self, get_df):
        self.get_df = get_df
    def __missing__(self, column_name):
        assert column_name != None
        cc = DataframeColumnCache(lambda : self.get_df(), column_name)
        self[column_name] = cc
        return cc

# Note that DataframeBrowser (i.e. history) is responsible for the columns of the dataframe and the dataframe itself
# whereas this class is responsible for the view into the rows.
# This decision is based on the fact that scrolling up and down through a dataset
# is not considered to be a useful 'undo' operation, since it is immediately reversible,
# whereas column operations (re-order, hide, etc) are reversible with extra work (they require typing column names)
# A counterpoint to this is 'jumping' through the rows - some users might find it handy to be able
# to return to their previous row position after a jump. But as of now, it's hard to see
# what the right way of handling that would be.
# searches happen here, because we are simply iterating through the strings
# for the next match.
# sorts, filters, etc. also happen here, because they modify the dataframe and therefore
# require re-computation of the viewing strings. This eventually could change
# if the individual column views could register for callbacks during dataframe changes.
# The history object can be responsible for maintaining the history
# of dataframes and column hides/shifts
class DataframeView(object):
    DEFAULT_VIEW_HEIGHT = 100
    def __init__(self, df_history, normal_cache_size=200, cache_above_top=50):
        self.df_history = df_history
        self._top_row = 0 # the top row in the dataframe that's in view
        self._selected_row = 0
        self._view_height = DataframeView.DEFAULT_VIEW_HEIGHT
        self._column_cache = dfcol_defaultdict(lambda: self.df)
        self.scroll_margin_up = 10 # TODO these are very arbitrary and honestly it might be better
        self.scroll_margin_down = 30 # if they didn't exist inside this class at all.
        # However, it's worth noting that search functionality requires the idea of a row-wise 'point'
        # from which the search should begin.

    # TODO : jump to column, insert column at point, filter/where

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

    def search(self, column_name, search_string, down=True, skip_current=False, case_insensitive=False):
        """search downward or upward in the current column for a string match.
        Can exclude the current row in order to search 'farther' in the dataframe."""
        case_insensitive = case_insensitive if case_insensitive != None else search_string.islower()
        starting_row = self._selected_row + int(skip_current) if down else self._selected_row - int(skip_current)
        df_index = self._column_cache[column_name].search_cache(search_string, starting_row, down, case_insensitive)
        if df_index != None:
            self.scroll_rows(df_index - self._selected_row)
            return True
        return False

    def jump(self, fraction=None, pos=None):
        if fraction != None:
            assert fraction >= 0.0 and fraction <= 1.0
            pos = fraction * len(self.df)
        self.scroll_rows(pos - self._selected_row)

    def scroll_rows(self, n):
        """ positive numbers are scroll down; negative are scroll up"""
        self._selected_row = max(0, min(self._selected_row + n, len(self.df) - 1))
        if n > 0:
            while self._selected_row > self._top_row + self.scroll_margin_down:
                self._top_row += 1 # TODO this could be faster
        elif n < 0:
            while self._selected_row < self._top_row + self.scroll_margin_up and self._top_row > 0:
                self._top_row -= 1
        assert self._selected_row >= self._top_row and self._selected_row <= self._top_row + self._view_height

    def _clear_cache(self):
        for col_name, cache in self._column_cache.items():
            cache.clear_cache()

    def sort(self, column_names, ascending=True):
        self._clear_cache()
        self.df_history.sort_columns(column_names, ascending)

    def undo(self, n=1):
        self._clear_cache()
        self.df_history.undo(n)
