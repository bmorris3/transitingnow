# -*- coding: utf-8 -*-
"""
Run this via crontab every minute. It will open the tweet dictionary and do a 
lookup for the current minute. If there is no key for the current minute, it 
will close. It may seem excessive to run it once a minute, but the dictionary
lookup is really fast, so I don't notice its effects on my computer. 

By Brett Morris (@brettmor) for @transitingnow
Code posted at https://github.com/bmorris3/transitingnow
"""
import tweepy
import cPickle
import datetime
from time import sleep 

### read in the list of tweets, already defined in MOCK_PREP.py
rootdir = './.' # Replace this string with the absolute path to the 
                # transitingnow directory. This should be an absolute path if 
                # you planet to run your Twitterbot via crontab, like I do.

with open(rootdir+'tweet_dict.pkl','rb') as tweet_file:
    tweet_dict = cPickle.load(tweet_file)

with open(rootdir+'lastchecked.txt','w') as lastchecked:
    lastchecked.write('Last checked: %s' % (str(datetime.datetime.utcnow())))

# Post the tweet with Tweepy. You'll need keys from apps.twitter.com
CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_KEY = ''
ACCESS_SECRET = ''

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

# Now = YYYY-MM-DD HH:MM   i.e., the current minute
now = str(datetime.datetime.utcnow())[:-10]

try: 
    transits_happening_now = tweet_dict[now]

    Ntransits = len(transits_happening_now) # Number of transits occuring in the next minute

    if Ntransits > 0:
        for tweet in transits_happening_now:
            api.update_status(tweet)

            # If there is more than one transit in this minute, then post the 
            # first transit immediately, and then send the next tweets on even
            # intervals over the next 50 seconds.
            if Ntransits > 1: 
                sleep(50./Ntransits)

        with open(rootdir+'lastposted.txt','w') as lastposted:
            lastposted.write('Last posted: %s' % (str(datetime.datetime.utcnow())))

except KeyError: 
    pass
