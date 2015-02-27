import pandas as pd

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


