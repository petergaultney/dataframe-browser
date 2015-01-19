#!/usr/bin/env python

import sys
import re

def match_string(string, regex):
    if isinstance(regex, basestring):
        return re.search(regex, string)
    else:
        # assume it's a compiled regex
        return regex.match(string)
    
def rsearch_obj_regex(obj, regex, name, flatlist=list()):
    if isinstance(obj, basestring):
        flatlist.append((name, match_string(obj, regex), obj))
    else: # either an object/dict or a number or a sequence
        try:
            for i, item in enumerate(iter(obj)):
                try: # dict?
                    rsearch_obj_regex(obj[item], regex, name + '[' + str(item) + ']', flatlist)
                except (KeyError, IndexError) as e:
                    # might have been a list or set, not a dict
                    rsearch_obj_regex(item, regex, name + '[' + str(i) + ']', flatlist)
        except TypeError: # not iterable, maybe an object?
            try:
                names = [nname for nname in dir(obj)]
                names = [nname for nname in names if not nname.startswith('__')]
                names = [nname for nname in names if not callable(getattr(obj,nname))]

                results = list()
                for rname in names:
                    rsearch_obj_regex(obj[rname], regex, name + '.' + str(rname), flatlist)
            except:
                # convert to string and try again?
                print('failed with ' + str(obj))
                flatlist.append((name, None, None))
        except:
            # convert to string and try again?
            print('failed with ' + str(obj))
            flatlist.append((name, None, None))
    return flatlist

            

            
        
    
