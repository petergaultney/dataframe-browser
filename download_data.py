#!/usr/bin/env python
import sys, re, os
import pandas as pd

if __name__ == '__main__':
    pd.set_option('display.max_rows', 9999)
    pd.set_option('display.width', None)

    import dubois
    conn = dubois.get_admin_conn()

    import datetime_utils
    print('Welcome to the DuBois Project Data Explorer!')
    print('Press TAB twice at any time to view the available commands or options.')
    print('Use Ctrl-C to return to previous level, and Ctrl-D to quit.')
    # start readline
    import readline
    readline.parse_and_bind('tab: complete')

    while True:
        try:
            # local_data = raw_input('type a dirname to use local data, or press enter to download')
            # if local_data and os.path.exists(local_data):

            print('How far back should I download?')
            start = datetime_utils.ask_for_date()
            df_sm = dubois.download_recent_domain_data(conn, date_start=start)
            print('Wrote that data to a CSV file. To exit, use Ctrl-D')
        except (KeyboardInterrupt, EOFError) as e:
            print('\nLeaving the DuBois Project Data Explorer.')
            break
