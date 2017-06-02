from sdb_utils import *
import dataframe_browser
import smartmerge
import os

class DuboisDomain:
    def __init__(self, name, shortname, suffix, datetime_columns=list()):
        self.name = name
        self.shortname = shortname
        self.datetime_columns = datetime_columns
        self.suffix = suffix
        try:
            self.main_datetime_column = datetime_columns[0]
        except:
            self.main_datetime_column = None

_dubois_domains = [
    DuboisDomain('dubois_coach_identities', 'coaches', '_OF_COACH',
                 []),
    DuboisDomain('dubois_devices', 'devices', '_OF_DEVICE',
                 ['datetime_last_launched', 'datetime_first_install']),
    DuboisDomain('dubois_mathlete_identities', 'mathletes', '_OF_MATHLETE'),

    DuboisDomain('dubois_mathlete_attribute_updates', 'attributes', '_OF_ATTR',
                 ['datetime']),
    DuboisDomain('dubois_fraction_representations', 'representations', '_OF_REPR',
                 []),
    DuboisDomain('dubois_fractions_games_played', 'games', '_OF_GAME',
                 ['start', 'end']),
    DuboisDomain('dubois_fractions_game_answers', 'answers', '_OF_ANSWER',
                 ['datetime']),
    DuboisDomain('dubois_fractions_game_challenges', 'challenges', '_OF_CHALLENGE',
                 ['datetime'] ),
    DuboisDomain('dubois_uncaught_exceptions', 'exceptions', '_OF_EXCEPTION',
                 ['datetime']),
]

_known_merges = [
    ['games', 'mathletes', 'player_id'],
    ['games', 'coaches', 'admin_key'],
    ['games', 'devices', 'device_id'],
    ['attributes', 'mathletes', 'mathlete_id'],
    ['answers', 'challenges', 'challenge_id'],
    ['answers','games', 'game_id'],
    ['exceptions', 'devices', 'device_id'],
    ['challenges', 'games', 'game_id'],
    ['challenges', 'representations', 'repr_id'],
    ]

# connect to US-East region by default
def get_admin_conn():
    conn = boto.sdb.connect_to_region('us-east-1')
    return conn
def get_readonly_conn():
    return None # this should be implemented soon.

def download_recent_domain_data(conn, ddomains=_dubois_domains,
                                date_start=yesterday(), date_end=None, lcl_dir='local_data'):
    df_merger = smartmerge.DataframeSmartMerger()
    #downloaded_resultsets = dict()
    # download the daterange
    for dd in ddomains:
        try:
            domain_name = dd.name
            dt_range_col = dd.main_datetime_column
        except:
            domain_name = dd
            dt_range_col = None
        domain = conn.get_domain(domain_name)
        itemsets = download_dtrange_from_domain(
            domain, datetime_col=dt_range_col, date_start=date_start, date_end=date_end)
        #downloaded_resultsets[domain_name] = itemsets
        DF = make_df_from_sdb(itemsets)
        if lcl_dir:
            if not os.path.exists(lcl_dir):
                os.makedirs(lcl_dir)
            DF.to_csv(lcl_dir + os.sep + domain_name + '.csv')
        df_merger.add(DF, dd.shortname, suffix=dd.suffix)

    # register known smart merges with dataframe browser
    for km in _known_merges:
        df_merger.register_smart_merge(km[0], km[2], km[1])
    return df_merger
