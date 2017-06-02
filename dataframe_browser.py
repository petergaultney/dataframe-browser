#!/usr/bin/env python
from collections import defaultdict
import os
import pandas as pd
import numpy as np

from list_utils import *
from chunk_search_utils import *

import urwid_table_browser

from gui_debug import *

_global_urwid_browser_frame = None

def browse(df, name=None):
    return MultipleDataframeBrowser().add_df(df, name).browse()


def browse_dir(directory_of_csvs):
    mdb = MultipleDataframeBrowser()
    dataframes_and_names = list()
    for fn in os.listdir(directory_of_csvs):
        df = pd.read_csv(directory_of_csvs + os.sep + fn, index_col=False)
        name = fn[:-4]
        mdb.add_df(df, name)
    return mdb.browse()


class MultipleDataframeBrowser(object):
    """Create one of these to start browsing pandas Dataframes in a curses-style terminal interface."""
    def __init__(self, table_browser_frame=None):
        global _global_urwid_browser_frame
        if not table_browser_frame:
            if not _global_urwid_browser_frame:
                _global_urwid_browser_frame = urwid_table_browser.TableBrowserUrwidLoopFrame()
            self.urwid_frame = _global_urwid_browser_frame
        else:
            self.urwid_frame = table_browser_frame
        self.browsers = dict()
        self.active_browser_name = None

    def add_df(self, df, name=None):
        """Direct interface to adding a dataframe.

        Preferably provide your own name here, but if you don't, we'll assign one..."""
        i = len(self.browsers)
        while not name:
            name = 'df' + str(i)
            if name in self.browsers:
                i += 1
                name = None # keep trying til we find something valid
        if name not in self.browsers:
            print('making new table browser')
            self.browsers[name] = DataframeTableBrowser(df)
            # self.browsers[name].add_change_callback(self.update_view)
            # self.last_focused_column[name] = 0
        if not self.active_browser_name:
            self.active_browser_name = name
        return self # for chaining, e.g.

    def rename_current_browser(self, new_name):
        if new_name not in self.multibrowser:
            browser = self.browsers.pop(self.active_browser_name)
            self.browsers[new_name] = browser
            self.active_browser_name = new_name

    def copy_browser(self, name, new_name=None):
        pass

    def open_new_browser(self, **kwargs):
        pass

    def __getitem__(self, df_name):
        return self.browsers[df_name]
    @property
    def current_browser(self):
        return self.browsers[self.active_browser_name] if self.active_browser_name else None
    @property
    def current_browser_name(self):
        return self.active_browser_name
    @property
    def all_browser_names(self):
        return self.browsers.keys()

    def set_current_browser(self, name):
        if name in self.browsers:
            self.active_browser_name = name
        return self

    def browse(self):
        """This actually brings up the interface. Can be re-entered after it exits and returns."""
        self.urwid_frame.start(self)
        return self # for the ultimate chain, that returns itself so it can be started again.



# the DataframeTableBrowser implements an interface of sorts that
# the Urwid table browser uses to display a table.
# It maintains history and implements the API necessary for viewing a dataframe as a table.
# TODO provide separate callbacks for when the dataframe itself has changed
# vs when the column order/set has changed.
class DataframeTableBrowser(object):
    """Implements the table browser contract for a single pandas Dataframe."""
    def __init__(self, df):
        self.df_hist = [df]
        self.browse_columns_history = [list(df.columns)]
        self.undo_hist = list()
        self.change_cbs = list()
        self.view = DataframeRowView(lambda: self.df)
        self.add_change_callback(self.view.df_changed)
        self._focused_column = 0

    # TODO Join
    # TODO support displaying index as column.

    @property
    def df(self):
        return self.df_hist[-1]
    @property
    def original_df(self):
        return self.df_hist[0]
    @property
    def browse_columns(self):
        return self.browse_columns_history[-1]
    @property
    def all_columns(self):
        return list(self.original_df.columns)
    @property
    def focused_column(self):
        return self._focused_column
    @focused_column.setter
    def focused_column(self, new_focus_col):
        assert new_focus_col < len(self.browse_columns) and new_focus_col >= 0
        self._focused_column = new_focus_col

    def __len__(self):
        return len(self.df)

    def _msg_cbs(self):
        for cb in self.change_cbs:
            cb(self)

    def sort_on_columns(self, columns, ascending=True, algorithm='mergesort', na_position=None): # we default to mergesort to stay stable
        na_position = na_position if na_position != None else ('last' if ascending else 'first')
        sorted_df = self.df.sort_values(columns, ascending=ascending, kind=algorithm, na_position=na_position)
        self._change_df(self.df, sorted_df)

    # TODO shouldn't this technically be by name?
    def shift_column(self, col_idx, num_cols_to_right):
        new_dcols = shift_list_item(self.browse_columns, col_idx, num_cols_to_right)
        return self._change_display_cols(self.browse_columns, new_dcols)

    def _change_display_cols(self, old_cols, new_cols):
        if old_cols != new_cols:
            print('changing display cols')
            self.browse_columns_history.append(new_cols)
            self.undo_hist.append(self.browse_columns_history)
            self._msg_cbs()
            return True
        return False

    def _change_df(self, old_df, new_df):
        self.df_hist.append(new_df)
        self.undo_hist.append(self.df_hist)
        self._msg_cbs()

    def insert_column(self, col_name, index):
        if col_name in list(self.df):
            new_dcols = insert_item_if_not_present(self.browse_columns, col_name, index)
            return self._change_display_cols(self.browse_columns, new_dcols)
        return False

    def hide_col_by_name(self, col_name):
        new_cols = find_and_remove_list_item(self.browse_columns, col_name)
        return self._change_display_cols(self.browse_columns, new_dcols)

    def hide_col_by_index(self, index):
        new_cols = remove_list_index(self.browse_columns, index)
        return self._change_display_cols(self.browse_columns, new_cols)

    def undo(self, n=1):
        while n > 0 and len(self.undo_hist) > 0:
            change_type = self.undo_hist.pop()
            if change_type == self.df_hist:
                self.df_hist.pop()
            elif change_type == self.browse_columns_history:
                self.browse_columns_history.pop()
            else:
                print('cannot undo this unknown operation')
                break
            n -= 1
        assert len(self.df_hist) > 0
        assert len(self.browse_columns_history) > 0
        self._msg_cbs()

    def search_column(self, column, search_string, down=True, skip_current=False):
        """This is delegated to the view because it maintains a convenient string cache."""
        return self.view.search(column, search_string, down, skip_current)

    # TODO add redo functionality, to undo an undo.
    # would only allow redos immediately after undos.

    def add_change_callback(self, cb):
        if cb not in self.change_cbs:
            self.change_cbs.append(cb)

    def query(self, query_str):
        new_df = self.df.query(query_str)
        return self._change_df(self.df, new_df)


class defaultdict_of_DataframeColumnSegmentCache(defaultdict):
    def __init__(self, get_df):
        self.get_df = get_df
    def __missing__(self, column_name):
        assert column_name != None
        cc = DataframeColumnSegmentCache(lambda : self.get_df(), column_name)
        self[column_name] = cc
        return cc

# Note that DataframeTableBrowser is responsible for the columns of the dataframe and the dataframe itself
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
class DataframeRowView(object):
    DEFAULT_VIEW_HEIGHT = 100
    def __init__(self, get_df):
        self._get_df = get_df
        self._top_row = 0 # the top row in the dataframe that's in view
        self._selected_row = 0
        self._column_cache = defaultdict_of_DataframeColumnSegmentCache(lambda: self.df)
        self.view_height = DataframeRowView.DEFAULT_VIEW_HEIGHT
        self.scroll_margin_up = 10 # TODO these are very arbitrary and honestly it might be better
        self.scroll_margin_down = 30 # if they didn't exist inside this class at all.
        # However, it's worth noting that search functionality requires the idea of a row-wise 'point'
        # from which the search should begin.

    # TODO: str.contains/match

    @property
    def df(self):
        return self._get_df()
    @property
    def top_row(self):
        return self._top_row
    @property
    def selected_relative(self):
        assert self._selected_row >= self._top_row and self._selected_row <= self._top_row + self.view_height
        return self._selected_row - self._top_row

    def header(self, column_name):
        return self._column_cache[column_name].header
    def width(self, column_name):
        return self._column_cache[column_name].width
    def lines(self, column_name, top_row=None, bottom_row=None):
        top_row = top_row if top_row != None else self._top_row
        bottom_row = bottom_row if bottom_row != None else min(top_row + self.view_height, len(self.df))
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
        assert self._selected_row >= self._top_row and self._selected_row <= self._top_row + self.view_height

    def df_changed(self, browser=None):
        for col_name, cache in self._column_cache.items():
            cache.clear_cache()


class DataframeColumnSegmentCache(object):
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
        self.assigned_width = max(DataframeColumnSegmentCache.MIN_WIDTH,
                                  min(DataframeColumnSegmentCache.MAX_WIDTH, self.assigned_width))
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


if __name__ == '__main__':
    import sys
    browse_dir(sys.argv[1])
