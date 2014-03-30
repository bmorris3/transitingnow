# -*- coding: utf-8 -*-
"""
Run this via the command line to check what tranit events are going to be
posted about soon. 

Example: 
$ python shownextevents.py        ## Returns events in the next 15 min (default)
$ python shownextevents.py 60     ## Returns events i the next 60 min
"""
import datetime
import cPickle
import sys

### read in the list of tweets, already defined in MOCK_PREP.py
rootdir = './.' # Replace this string with the absolute path to the 
                # transitingnow directory. This should be an absolute path if 
                # you planet to run your Twitterbot via crontab, like I do.
tweet_file = open(rootdir+'tweet_dict.pkl','rb')
tweet_dict = cPickle.load(tweet_file)
tweet_file.close()

## Accept arguments to the Python command to search on longer timescales
if len(sys.argv) > 1:
    Nminutes = int(sys.argv[1])
else:
    Nminutes = 15

now = str(datetime.datetime.utcnow())

# Now = YYYY-MM-DD HH:MM
now = str(datetime.datetime.utcnow())[:-10]
#now_plus_min = str(datetime.datetime.utcnow() + datetime.timedelta(minutes=Nminutes))[:-10]
each_minute = []
for minute_increment in range(Nminutes):
    each_minute.append(str(datetime.datetime.utcnow() + \
                       + datetime.timedelta(minutes=minute_increment))[:-10])

upcoming_transits = []
for minute in each_minute:
    try: 
        transits_happening_now = tweet_dict[minute]

        Ntransits = len(transits_happening_now) # Number of transits occuring in the next minute

        if Ntransits > 0:
            for tweet in transits_happening_now:
                upcoming_transits.append([minute, tweet])
    except KeyError: 
        pass

print "\nUpcoming transits in the next %i minutes:\n" % Nminutes
for time, transit in upcoming_transits:
    print "At "+time+" -\n"+transit

