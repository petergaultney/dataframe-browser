#!/usr/bin/env python
# this script depends on pandas. 
# pandas is a data-domination library. 
# it is intended to mirror the capabilities of R.
# it takes a little while to get used to, but is extraordinarily powerful and fast.

import sys, os
import re
import pandas as pd
import datetime as dt
import readline
import dubois
from sdb_utils import *
from interactive_utils import *
import datetime_utils

def xstr(s):
    if s is None:
        return ''
    return str(s)

basic_def_cols = [
    'name',
    'start',
    'game_type',
    'level_at_end',
    'value',
    'solution', 'level', 'pool', 'num_errors',
    'time_elapsed', 'solved', 'repr_type', 'repr_level',
    'repr_descrip',
    'correct', 'num_solved', 'answer',
    'score', 'level_integer', 'level_fraction', 'notes',
    ]

def interactive_dataframe_display(df, def_cols=basic_def_cols, prefix=None):
    completer = Completer(list(df) + ['?defaults'])
    readline.set_completer(completer.complete)

    comparison_regex_str = '(\w+)(' + '|'.join(dataframe_utils.comparison_ops_dict.keys()) + ')' + '(.*)'
    comp_re = re.compile(comparison_regex_str)
    print('In DISPLAY mode, the following comparison operators are supported for name-value pairs:')
    print(', '.join(dataframe_utils.comparison_ops_dict.keys()))
    
    print('Columns can be sorted by typing their name and adding a direction specifier, + or -')
    sort_regex_str = '(\w+)(-|\+)'
    sort_re = re.compile(sort_regex_str)
    
    pd.set_option('display.max_rows', 999)
    # pd.set_option('display.expand_frame_repr', False) # this turns off wrapping altogether
    pd.set_option('display.width', None) # this wraps to Terminal width

    if not def_cols:
        def_cols = list(df)
    display_cols = [col for col in def_cols if col in list(df)]

    while True:
        try:
            print(xstr(prefix) + ' DISPLAY > Press Enter for defaults, ' +
                  'TAB to complete column names, or Ctrl-C to exit DISPLAY.')
            new_display_cols = raw_input(xstr(prefix) + ' DISPLAY >>> ')
            if new_display_cols:
                if new_display_cols == '?defaults':
                    print(xstr(prefix) + ' DISPLAY > DEFAULTS: ' + ', '.join(display_cols))
                    continue
                else:
                    new_display_cols = new_display_cols.split(' ')

            query_strs = list()
            display_df = df

            for dc in new_display_cols:
                try:
                    cmpr = comp_re.match(dc)
                    srt = sort_re.match(dc)
                    if cmpr:
                        print('filtering {} by {}'.format(cmpr.group(1), cmpr.group(3)))
                        display_df = dataframe_utils.where(display_df, cmpr.group(1),
                                                           cmpr.group(2), cmpr.group(3))
                        if cmpr.group(1) in display_cols:
                            display_cols.remove(cmpr.group(1))
                        display_cols.insert(0, cmpr.group(1)) # we can put this all the way on the left
                    elif srt:
                        print('sorting by ' + srt.group(1))
                        display_df = display_df.sort(srt.group(1),
                                                     ascending=(srt.group(2)=='+'),
                                                     kind='mergesort')
                        if srt.group(1) not in display_cols:
                            display_cols.append(srt.group(1))
                    elif dc in display_cols:
                        print('removing column ' + dc)
                        display_cols.remove(dc)
                    else:
                        print('adding column ' + dc)
                        display_cols.append(dc)
                except Exception as e:
                    print(e)
                    print('There was an error when parsing your selections.')
                    print('Press Ctrl-D to exit debugging mode.')
                    from IPython import embed
                    embed()
                    pass
                
            # verify sanity of input - don't crash because a column doesn't exist
            display_cols = [col for col in display_cols if col in list(display_df)]
            display_df = display_df[display_cols]
            df_str = display_df.to_string(index=False)
            print(df_str)
            print(df_str.split('\n', 1)[0]) # reprint header row
        except KeyboardInterrupt:
            print('')
            break

# this is just a goofy, experimental interactive interface
def browse_dataframes(df_browser):
    # print instructions
    known_df_names = df_browser.get_known_names()
    print('')
    print('Available dataframes are ' + ', '.join(known_df_names))
    print('Type dataframe names to merge them. Press Ctrl-C to return before the previous merge.')
    print('Press Enter to display current merged dataframe')
    vcmds_completer = Completer(known_df_names)

    ptag = ' >>> '
    df_stack = list()
    current_df = None
    
    while True:
        try:
            readline.set_completer(vcmds_completer.complete)

            if current_df is not None:
                prompt = df_browser.get_known_name(current_df) + ptag
            else:
                prompt = ptag
            
            cmdline = raw_input(prompt).strip()
            tokens = cmdline.split(' ')
            if len(tokens) < 1 or not cmdline:
                if current_df is not None:
                    interactive_dataframe_display(current_df)
                    
            # if we are doing standard merge
            if current_df is None and len(tokens) > 0:
                df_name = tokens.pop()
                try:
                    current_df = df_browser[df_name]
                except:
                    print(df_name + ' isn\'t a known dataframe.')
                    pass
                
            for tok in tokens:
                if tok:
                    df_stack.append(current_df)
                    try:
                        current_name = df_browser.get_known_name(current_df)
                        print('Merging current dataframe ' + current_name + ' with ' + tok)
                        try:
                            current_df = df_browser.smart_merge(current_df, tok)
                        except Exception as e:
                            print(e)
                            print('Could not merge ' + current_name + ' with ' + tok)
                            df_stack.pop()
                    except:
                        print(str(current_df) + ' is not a known dataframe')
            
        except KeyboardInterrupt:
            print('')
            try:
                current_df = df_stack.pop()
            except:
                if current_df is not None:
                    current_df = None
                else:
                    break

def start_interactive_query_loop(conn):
    print('Welcome to the DuBois Project Data Explorer!')
    print('Press TAB twice at any time to view the available commands or options.')
    print('Use Ctrl-C to return to previous level, and Ctrl-D to quit.')
    # start readline
    readline.parse_and_bind('tab: complete')

    while True:
        try:
            # local_data = raw_input('type a dirname to use local data, or press enter to download')
            # if local_data and os.path.exists(local_data):

            print('How far back should I download?')
            start = datetime_utils.ask_for_date()
            df_browser = dubois.download_recent_domain_data(conn, date_start=start)
            browse_dataframes(df_browser)
        except (KeyboardInterrupt, EOFError) as e:
            print('\nLeaving the DuBois Project Data Explorer.')
            break

if __name__ == '__main__':
    conn = dubois.get_admin_conn()
    start_interactive_query_loop(conn)
