import datetime as dt
from interactive_utils import *
import readline

def weeks_ago(n):
    # now = dt.datetime.now()
    # then = now - dt.timedelta(7)
    # return then
    return days_ago(7 * int(n))

def days_ago(n):
   return dt.datetime.combine(dt.date.today() - dt.timedelta(int(n)), dt.time.min) 

def hours_ago(n):
   return dt.datetime.now() - dt.timedelta(0, int(n) * 60 * 60)

def yesterday():
    return days_ago(1)

def today():
    return dt.datetime.combine(dt.date.today(), dt.time.min)

def now():
    return dt.datetime.now()

rangefuncs = {
    'today':today,
    'yesterday':yesterday,
    'weeks_ago':weeks_ago,
    'days_ago':days_ago,
    'hours_ago':hours_ago
}

def ask_for_date():
    while True:
        ranges_completer = Completer(rangefuncs.keys())
        readline.set_completer(ranges_completer.complete)
        rgnf = raw_input('DATE >>> ')
        all_args = rgnf.split(' ')

        func_args = list()
        # try:
        if len(all_args) == 1:
            try:
                func_args = [ int(all_args[0]) ]
                function = 'days_ago' # default to days
            except:
                # first argument wasn't a number
                function = all_args[0]
        elif len(all_args) == 2:
            try:
                func_args = [ int(all_args[0]) ]
                function = all_args[1]
            except:
                function = all_args[0]
                func_args = [ int(all_args[1]) ]

        rangefunc = rangefuncs[function]
        rt = rangefunc(*func_args)
        return rt
        # except Exception as e:
        #     print(e)
        #     print('Sorry, that input is invalid. Try again (TAB to see valid options), or Ctrl-C to quit.')

