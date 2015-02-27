# a module for interacting with Amazon SimpleDB using Python pandas (and boto of course)
import pandas as pd
import boto.sdb
import datetime as dt
import dataframe_utils
from datetime_utils import *

class Creds:
    def __init__(self, ID, secret):
        self.ID = ID
        self.secret = secret

# a domain is equivalent to a resultset from a select query.
def make_records_from_resultsets(resultsets):
    records = list()
    for itemlist in resultsets:
        records += [dict(list(item.items()) + [('itemName', item.name)]) for item in itemlist]
    return records

def df_force_numerics(df):
    for col in df.columns:
        try:
            df[col] = df[col].astype(int)
        except:
            try:
                df[col] = df[col].astype(float)
            except:
                try:
                    df[col] = pd.to_datetime(df[col])
                except:
                    pass

# this turns a SDB domain into a dataframe, and converts columns to be datetime objects
def make_dataframe_from_records_with_dates(records, force_numerics=True):
    if len(records) == 0:
        return pd.DataFrame() # empty dataframe
    df = pd.DataFrame.from_records(records, index='itemName') # SDB always indexes by itemName
    if force_numerics:
        df_force_numerics(df)
    return df

# this is a convenience function
# rename to read_sdb
def make_df_from_sdb(resultsets):
    return make_dataframe_from_records_with_dates(
        make_records_from_resultsets(resultsets))

def build_sdb_datarange_query(domain_name, datetime_col=None,
                              date_start=yesterday(), date_end=None,
                              select_columns=None):
    query = 'select '
    if select_columns:
        query += '`' + '`,`'.join(select_columns) + '` '
    else:
        query += '* '
    query += 'from `' + domain_name + '` '
    if (date_start or date_end) and datetime_col:
        query += 'where '
        if date_start:
            query += '`' + datetime_col + '` > "' + date_start.isoformat() + '" '
            if date_end:
                query += 'AND '
        if date_end:
            query += '`' + datetime_col + '` < "' + date_end.isoformat() + '" '
    return query

def download_dtrange_from_domain(domain, datetime_col=None,
                                 date_start=yesterday(), date_end=None,
                                 select_columns=None):
    query = build_sdb_datarange_query(domain.name, datetime_col=datetime_col,
                                      date_start=date_start, date_end=None,
                                      select_columns=None)
    return from_sdb_query(domain, query)

def from_sdb_query(domain, query):
    rsets = list()
    print('Performing SDB query: ' + query)
    resultset = domain.connection.select(domain, query=query)
    while resultset.next_token:
        rsets.append(resultset)
        resultset = domain.connection.select(domain, query=query, next_token=resultset.next_token)
    rsets.append(resultset)
    return rsets
    
