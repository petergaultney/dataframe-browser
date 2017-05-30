from collections import defaultdict
import pandas as pd

# debug stuff
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


# smart frame functions (to make dataframes themselves 'smart')
def is_smart_frame(df):
    return hasattr(df, '__sf_is_smart_frame')
def make_df_smart(df, suffix):
    try:
        if is_smart_frame(df):
            print('WHOA THIS DATAFRAME IS ALREADY SMART')
            return df
    except:
        pass
    # okay, so it isn't already a 'smart' frame.
    df.__sf_suffix = suffix
    df.__sf_foreign_keys = dict()
    df.__sf_is_smart_frame = True
    df._metadata.append('__sf_suffix')
    df._metadata.append('__sf_foreign_keys')
    df._metadata.append('__sf_is_smart_frame')
    return df

def suffix(smart_df):
    return smart_df.__sf_suffix
def fkeys(smart_df): # foreign key
    return smart_df.__sf_foreign_keys

def get_fkey_for_dfid(smart_df, target_df_id):
    return fkeys(smart_df)[target_df_id]
def get_fkey(smart_df, target_df):
    return get_fkey_for_dfid(smart_df, id(target_df))

def add_fkey_for_dfid(smart_df, target_df_id, fkey):
    fkeys(smart_df)[target_df_id] = fkey
def add_fkey(smart_df, target_df, fkey): # gets id and passes along
    add_fkey_for_dfid(smart_df, id(target_df), fkey)

def sf_has_target(smart_df, target_df):
    if id(target_df) in fkeys(smart_df):
        return True
    return False

class DataFrameSmartMerger(object):
    def __init__(self):
        self._smart_frames = dict()
        self._names_of_dfs_known_to_be_smart = dict()
        self._smart_frames_which_have_a_foreign_key_for_this_dfid = dict()
    def add(self, df, name, suffix=None):
        print('adding dataframe ' + name)
        if not suffix:
            suffix = name
        df_id = id(df)
        # print('df {} has id {}'.format(name, df_id))
        if name in self._smart_frames:
            print('WARNING: Overwriting known smart frame!!!!!')
            # TODO: fix up all references and/or disallow this
        self._smart_frames[name] = make_df_smart(df, suffix)
        self._names_of_dfs_known_to_be_smart[id(df)] = name
        # print('Adding smart frame ' + name + ' with id ' + str(id(df)))
    # this just gets a dataframe by name
    def __getitem__(self, name):
        return self._smart_frames[name]
    def __iter__(self):
        return iter(self._smart_frames.keys())
    def _convert_to_name(self, df_or_name):
        # if it isn't a name, it's a dataframe and can be reverse-lookuped
        try:
            return self._names_of_dfs_known_to_be_smart[id(df_or_name)]
        except:
            return df_or_name # it needs to already be a name if it's not a dataframe
    def _get_best_printable_name(self, df):
        # this might already be a name
        try:
            # first guess is that it's a dataframe
            return self.get_known_name(df)
        except:
            try:
                # next guess is that it's an id
                return self._names_of_dfs_known_to_be_smart[df]
            except:
                # last guess is that it is a dataframe that we don't know about
                # print('couldnt return known name of id ' + str(id(df)))
                return str(id(df))
    def _get_smart_frame(self, df):
        # this might be a name, or it might be an actual dataframe
        df_name = self._convert_to_name(df)
        try:
            return self._smart_frames[df_name]
        except KeyError:
            return None
    def _get_df_if_known_name(self, df):
        try:
            return self._smart_frames[df]
        except:
            # hopefully this is already a dataframe
            return df
    def _add_reverse_smart_merge(self, df_id, smart_frame):
        df_name = self._get_best_printable_name(df_id)
        if df_id not in self._smart_frames_which_have_a_foreign_key_for_this_dfid:
            # print('creating reverse lookup smart frame list for ' + df_name)
            self._smart_frames_which_have_a_foreign_key_for_this_dfid[df_id] = list()
        # print('noting that df {} is known (a foreign key is possessed) by smart frame {}'.format(
        #     df_name,
        #     self._get_best_printable_name(smart_frame.df)))
        sf_list = self._smart_frames_which_have_a_foreign_key_for_this_dfid[df_id]
        sf_id = id(smart_frame)
        contains = False
        for item in sf_list:
            iid = id(item)
            if iid == sf_id:
                contains = True
        if contains:
            self._smart_frames_which_have_a_foreign_key_for_this_dfid[df_id].append(smart_frame)
        else:
            # it's possible that two dataframes which can both be merged
            # into the same other dataframe may get merged together.
            # if this happens, there will be two foreign keys for a single
            # dataframe.
            # we don't need to record two instances of this, because we're just
            # a convenience for notifying that other dataframe that the new
            # merged dataframe exists and that it knows how to merge into it.
            # Since they presumably shared the exact same key name, one of those
            # key names will have been destroyed by the merge process,
            # leaving the other one to be merged into.
            # I *believe* that only adding one suffix at merge time
            # should always preserve a valid foreign key for these sorts of
            # situations. However, in cases where two foreign keys share
            # the same name but don't refer to the same table, this will
            # cause breakage. In this case, which is of course based on
            # unfortunate data naming that could potentially be avoided,
            # we could maybe check every time we do a merge to see if
            # the columns have been renamed. If they have been renamed,
            # we could add a new foreign key record to all SmartFrames
            # with the new merged name. But for now we'll leave this as-is.

            # print("WARNING - this smart frame {} has already been added for df {}".format(
            #     self._get_best_printable_name(smart_frame), df_name))
            pass

    # Registering a smart merge means declaring that the first dataframe
    # has a foreign key that corresponds to the primary index of other_df.
    # Smart merges will be performed between dataframes based on these declarations.
    # Since the merge is performed by definition on the primary key of one dataframe,
    # it is not currently supported to have more than one column that is a foreign
    # key for a given other dataframe. Future versions may or may not support this
    # additional semantic.
    # NB: These may be names or dataframes, but the first one at least must
    # be a known smart frame, or this will fail.
    def register_smart_merge(self, df, foreign_key, other_df):
        smart_frame = self._get_smart_frame(df)
        other_df = self._get_df_if_known_name(other_df) # if it's just a name but we already know about it
        self._register_smart_merge(smart_frame, foreign_key, id(other_df))

    def _register_smart_merge(self, smart_frame, foreign_key, df_id):
        # print('I declare that df ' + self._get_best_printable_name(smart_frame.df)
        #       + ' has an attribute ' + foreign_key + ' that allows it to join to '
        #       + self._get_best_printable_name(df_id) + '\'s primary key')
        add_fkey_for_dfid(smart_frame, df_id, foreign_key)
        self._add_reverse_smart_merge(df_id, smart_frame)

    def get_known_names(self):
        return self._smart_frames.keys()
    def get_known_name(self, df):
        return self._names_of_dfs_known_to_be_smart[id(df)]

    # As long as one of these is a dataframe or dataframe name that is known
    # by the DataFrameBrowser, and as long as that smart frame has a
    # registered smart merge for the other dataframe, this should return
    # a merged dataframe.
    def smart_merge(self, df1, df2, name_callback=None,
                    id_callback=None, suffix_callback=None, preferred_df_to_suffix=None):
        if df1 is None or df1 is None:
            # just die immediately. it's not worth dealing with this later
            self[df1]
            self[df2]

        # when we get to a merge, we assume unless told otherwise that
        # the caller wants df columns with matching names to be suffixed
        # only in the names of df2.
        if preferred_df_to_suffix is None or (id(preferred_df_to_suffix) != id(df1) and
                                              id(preferred_df_to_suffix) != id(df2)):
            preferred_df_to_suffix = df2

        smart_frame_1 = self._get_smart_frame(df1)
        smart_frame_2 = self._get_smart_frame(df2)
        # we expect df1 to be a smart frame and therefore possibly the foreign key holder
        if smart_frame_2 is not None and smart_frame_1 is None:
            # print('### performing swap, because df1 is not "smart" at all')
            # if it isn't a smart frame at all, but df2 is, we swap
            temp = smart_frame_1
            smart_frame_1 = smart_frame_2
            smart_frame_2 = temp
        elif smart_frame_1 is None and smart_frame_2 is None:
            # TODO: we don't even have a smart frame. use new smart frame callbacks!
            # (for now, we just die by trying and failing to 'get' df1)
            print(df1, df2)
            print('we can\'t find either of these as smart frames')
            self._smart_frames[self.get_name(df1)]
            # EARLY DEATH

        #
        # at this point we have ensured that at least one smart frame (smart_frame_1) exists
        #
        # Therefore we should not be using 'df1' anymore
        df1 = None
        if smart_frame_2 is not None:
            # df2 may have been a known name instead of a df, so assign the actual dataframe
            df2 = smart_frame_2

        # we give preference to the first smart frame, if there are two
        if sf_has_target(smart_frame_1, df2):
            smart_frame_w_fkey = smart_frame_1
            df_w_primkey = df2
            if smart_frame_2 is not None:
                smart_frame_w_primkey = smart_frame_2
        elif smart_frame_2 is not None and sf_has_target(smart_frame_2, smart_frame_1):
            smart_frame_w_fkey = smart_frame_2
            smart_frame_w_primkey = smart_frame_1
            df_w_primkey = smart_frame_w_primkey
        else:
            # we don't know how to merge these either direction
            # TODO: so perform 'merge clarification callback'
            # (but for now we just raise an exception)
            print('we dont know how to merge these in either direction')
            get_fkey(smart_frame_1, df2)
            # EARLY DEATH

        # get shortcut names for easier printing
        df_w_primkey_name = self._get_best_printable_name(df_w_primkey)
        df_w_fkey_name = self._get_best_printable_name(smart_frame_w_fkey)

        #
        # past here, we should not refer to anything except in terms of w_primkey and w_fkey
        #
        smart_frame_1 = None
        smart_frame_2 = None
        df2 = None

        # this would be the place to precheck column names and do my own
        # column renaming. and then we'd need a reverse-lookup by foreign key
        # in the smart frames, so that we can add the updated foreign key.
        # and maybe also check to see if this already has the one,
        # because if it does we should eliminate the duplicate column.
        # but is it really a duplicate? maybe not...

        # now that we KNOW which direction to merge and how, so DO MERGE!
        foreign_key = get_fkey(smart_frame_w_fkey, df_w_primkey)
        # print('### merging {} with {}\'s primary key using fkey {}'.format(
        #     df_w_fkey_name, df_w_primkey_name, foreign_key))

        if id(preferred_df_to_suffix) == id(smart_frame_w_fkey):
            merged = smart_frame_w_fkey.merge(df_w_primkey,
                                              left_on=foreign_key, right_index=True,
                                              suffixes=(suffix(smart_frame_w_fkey), ''))
        elif id(preferred_df_to_suffix) == id(df_w_primkey) and is_smart_frame(df_w_primkey):
            merged = smart_frame_w_fkey.merge(df_w_primkey,
                                              left_on=foreign_key, right_index=True,
                                              suffixes=('', suffix(df_w_primkey)))
        else:
            merged = smart_frame_w_fkey.merge(df_w_primkey,
                                              left_on=foreign_key, right_index=True,
                                              suffixes=(suffix(smart_frame_w_fkey),
                                                        suffix(df_w_primkey)))

        # now we need to do bookkeeping and record any new known smart merges
        # add the new merged dataframe as a smart frame, since it's based on at least one smart frame
        merged_name = df_w_fkey_name + '+' + df_w_primkey_name
        self.add(merged, merged_name)
        merged_smart_frame = self._get_smart_frame(merged_name)

        # print('add available foreign keys of foreign_key df to merged df smart frame')
        # add available foreign keys of component dfs to merged df
        for df_id in fkeys(smart_frame_w_fkey).keys():
            fkey = fkeys(smart_frame_w_fkey)[df_id]
            if fkey == foreign_key:
                continue # we just merged on this, so it can't be merged on for the new df
            self._register_smart_merge(merged_smart_frame, fkey, df_id)
        # print('add available foreign keys of primary key df to merged df')
        if smart_frame_w_primkey is not None:
            for df_id in fkeys(smart_frame_w_primkey).keys():
                fkey = fkeys(smart_frame_w_primkey)[df_id]
                # we shouldn't have reuse in here, because we didn't use these
                self._register_smart_merge(merged_smart_frame, fkey, df_id)
        # now add available foreign keys of  smart frames
        # that know how to merge into the component dfs
        merged_id = id(merged)
        df_primkey_id = id(df_w_primkey)
        # print('STEP TWO {}'.format(df_primkey_id))
        # print('add available foreign keys of smart frames that know how to merge into the primkey df')
        if df_primkey_id in self._smart_frames_which_have_a_foreign_key_for_this_dfid:
            smart_frames_which_know_this_df_id = self._smart_frames_which_have_a_foreign_key_for_this_dfid[df_primkey_id]
            for smart_frame in smart_frames_which_know_this_df_id:
                the_fkey = get_fkey_for_dfid(smart_frame, df_primkey_id)
                if the_fkey == foreign_key:
                    # print('skipping fkey {} possessed by {} because it disappeared in this merge'.format(
                    #     the_fkey, self._get_best_printable_name(smart_frame)))
                    continue
                self._register_smart_merge(smart_frame,
                                           the_fkey,
                                           merged_id)
        df_fkey_id = id(smart_frame_w_fkey)
        # print('add available foreign keys of smart frames that know how to merge into the foreignkey df')
        if df_fkey_id in self._smart_frames_which_have_a_foreign_key_for_this_dfid:
            smart_frames_which_know_this_df_id = self._smart_frames_which_have_a_foreign_key_for_this_dfid[df_fkey_id]
            for smart_frame in smart_frames_which_know_this_df_id:
                the_fkey = get_fkey_for_dfid(smart_frame, df_fkey_id)
                if the_fkey == foreign_key:
                    # print('skipping fkey {} possessed by {} because it disappeared in this merge'.format(
                    #     the_fkey, self._get_best_printable_name(smart_frame)))
                    continue
                self._register_smart_merge(smart_frame,
                                           the_fkey,
                                           merged_id)

        return merged


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
            print('adding new df!')
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

def get_dataframe_strings_for_column(df, column_name, top_row, bottom_row, NaN='\n'):
    print('refreshing cache', top_row, bottom_row)
    # data_string = df.ix[top_row:bottom_row,[df.columns.get_loc(column_name)]].to_string(index=False, index_names=False, header=False)
    data_string = df.ix[top_row:bottom_row].to_string(index=False, index_names=False, header=False, columns=[column_name])
    strs = data_string.split('\n')
    assert len(strs) == bottom_row - top_row
    while len(strs[0]) < len(strs[1]):
        strs[0] = ' ' + strs[0]
    return strs

class DataframeColumnCache(object):
    MIN_WIDTH = 2
    MAX_WIDTH = 50
    DEFAULT_CACHE_SIZE = 200
    def __init__(self, src_df_func, column_name, std_cache_size=200, min_cache_on_either_side=50):
        self.get_src_df = src_df_func
        self.column_name = column_name
        self.native_width = None
        self.assigned_width = None
        self.top_of_cache = 0
        self.row_strings = list()
        self._min_cache_on_either_side = min_cache_on_either_side
        self._std_cache_size = std_cache_size
    def _update_native_width(self):
        self.native_width = len(self.column_name)
        for s in self.row_strings:
            self.native_width = max(self.native_width, len(s))
    def change_width(self, n):
        if not self.assigned_width:
            self.assigned_width = self.native_width
        self.assigned_width += n
        self.assigned_width = max(MIN_WIDTH, min(MIN_WIDTH, self.assigned_width))
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
            new_cache = get_dataframe_strings_for_column(df, self.column_name, new_top_of_cache, new_bottom_of_cache)
        if new_cache:
            print('new cache from', new_top_of_cache, 'to', new_bottom_of_cache,
                  len(self.row_strings), len(new_cache))
            self.top_of_cache = new_top_of_cache
            self.row_strings = new_cache
            self._update_native_width()
        return self.row_strings[top_row-self.top_of_cache : bottom_row-self.top_of_cache]

class dfcol_defaultdict(defaultdict):
    def __init__(self, get_df):
        self.get_df = get_df
    def __missing__(self, column_name):
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
        pass

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
