# -*- coding: utf-8 -*-
'''
This script does most of the hard work! Update the list of transiting events
occuring in the next ~24 hours. Run this script via crontab every night.

By Brett Morris (@brettmor) for @transitingnow
Code posted at https://github.com/bmorris3/transitingnow
'''

import ephem	 ## PyEphem module
import numpy as np
import os
import cPickle
from astropy.time import Time
from glob import glob
from urllib import urlopen
import time
import datetime
from numpy.random import randint

# Set some paths to important directories here
rootdir = './.' # Replace this string with the absolute path to the
                # transitingnow directory. This should be an absolute path if
                # you planet to run your Twitterbot via crontab, like I do.

exodbPath = rootdir+'exodb'  # The absolute path to the exoplanet database files


## ----------------------------------------------------------------------------
## Handle time conversions with astropy

def gd2jd(gdlist):
    '''
    Parameters
    ----------
    gdlist : list
        Gregorian date in list format - [year,month,day,hour,minute,second]
    Returns
    -------
    jd : float
        Julian date
    '''

    # Convert the input list into a string in "ISO" format for astropy
    gdstring = "%i-%i-%i %s:%s:%s" % tuple(gdlist)
    return Time(gdstring, format='iso', scale='utc').jd

def jd2gd(jd):
    '''
    Parameters
    ----------
    jd : float
        Time in julian date
    Returns
    -------
    gdlist : list
        Gregorian date in list format - [year,month,day,hour,minute,second]
    '''
    return Time(jd, format='jd', scale='utc').iso

## ----------------------------------------------------------------------------

def downloadAndPickle():
    '''
    Download the .ZIP archive of the exoplanets.org planet database from their
    website, unpack the archive, and convert the .CSV table into a Python
    dictionary. Save that dictionary with the cPickle module for fast loading.

    If there is already a .PKL or .CSV file in the exoplanet database directory,
    use that one. There is a feature that doesn't work perfectly here that should
    be checking to see if the file is more than a week old, and downloading a
    new one if so.
    '''
    pklDatabaseName = os.path.join(exodbPath,'exoplanetDB.pkl')	 ## Name of exoplanet database C-pickle
    pklDatabasePaths = glob(pklDatabaseName)   ## list of files with the name pklDatabaseName in cwd
    csvDatabaseName = os.path.join(exodbPath,'exoplanets.csv')  ## Path to the text file saved from exoplanets.org
    csvDatabasePaths = glob(csvDatabaseName)

    '''First, check if there is an internet connection.'''

    '''If there's a previously archived database pickle in this current working
        directory then use it, if not, grab the data from exoplanets.org in one big CSV file and make one.
        If the old archive is >14 days old, grab a fresh version of the database from exoplanets.org.
        '''
    if csvDatabasePaths == []:
        print 'No local copy of exoplanets.org database. Downloading one...'
        rawCSV = urlopen('http://www.exoplanets.org/csv-files/exoplanets.csv').read()
        saveCSV = open(csvDatabaseName,'w')
        saveCSV.write(rawCSV)
        saveCSV.close()
    else:
        '''If the local copy of the exoplanets.org database is >7 days old, download a new one'''
        secondsSinceLastModification = time.time() - os.path.getmtime(csvDatabaseName) ## in seconds
        daysSinceLastModification = secondsSinceLastModification/(60*60*24*30)
        if daysSinceLastModification > 7:
            print 'Your local copy of the exoplanets.org database is >14 days old. Downloading a fresh one...'
            rawCSV = urlopen('http://www.exoplanets.org/csv-files/exoplanets.csv').read()
            saveCSV = open(csvDatabaseName,'w')
            saveCSV.write(rawCSV)
            saveCSV.close()
        else: print "Your local copy of the exoplanets.org database is <14 days old. That'll do."

    if len(pklDatabasePaths) == 0:
        print 'Parsing '+os.path.split(csvDatabaseName)[1]+', the CSV database from exoplanets.org...'
        rawTable = open(csvDatabaseName).read().splitlines()
        labels = rawTable[0].split(',')
        #labelUnits = rawTable[1].split(',')
        #rawTableArray = np.zeros([len(rawTable),len(labels)])
        exoplanetDB = {}
        planetNameColumn = np.arange(len(labels))[np.array(labels,dtype=str)=='NAME'][0]
        for row in range(1,len(rawTable)):
            splitRow = rawTable[row].split(',')
            exoplanetDB[splitRow[planetNameColumn]] = {}	## Create dictionary for this row's planet
            for col in range(0,len(splitRow)):
                exoplanetDB[splitRow[planetNameColumn]][labels[col]] = splitRow[col]

        output = open(pklDatabaseName,'wb')
        cPickle.dump(exoplanetDB,output)
        output.close()
    else:
        print 'Using previously parsed database from exoplanets.org...'
        inputFile = open(pklDatabaseName,'rb')
        exoplanetDB = cPickle.load(inputFile)
        inputFile.close()

    return exoplanetDB

def midTransit(Tc, P, start, end):
    '''
    Calculate mid-transits between Julian Dates `start` and `end`, using a 2500
    orbital phase kernel since T_c (for 2 day period, 2500 phases is 14 years)

    Parameters
    ----------
    Tc : float
        Mid-transit epoch
    P : float
        Orbital period
    start : float
        Julian date on which to start searching for transits
    end : float
        Julian date on which to end searching for transits

    Returns
    -------
        transitTimesInSem : list-like
            All transit times between `start` and `end`
    '''
    Nepochs = np.arange(0,2500,dtype=np.float64)
    transitTimes = Tc + P*Nepochs
    transitTimesInSem = transitTimes[(transitTimes < end)*(transitTimes > start)]
    return transitTimesInSem


# Get exoplanet database
exoplanetDB = downloadAndPickle()

# Identify planets that (1) are transiting, (2) have a mid-trans time listed
allplanets = [planet for planet in exoplanetDB.keys() if \
              exoplanetDB[planet]['TRANSIT'] == '1' and \
              exoplanetDB[planet]['TT'] != '']

# Update the tweet list from right now through `buildDBforNdays` days from now
buildDBforNdays = 1.2
start_date = Time(str(datetime.datetime.utcnow()), format='iso', scale='utc').jd
end_date = Time(str(datetime.datetime.utcnow() + \
                datetime.timedelta(days=buildDBforNdays)), format='iso', \
                scale='utc').jd

# Make a text file with all upcoming tweets for easy reading/debugging
eventfile = open(os.path.join(os.path.dirname(__file__),'eventList.txt'),'w')

## Some constants needed for comparisons and conversions
R_earth = 6378100.0 # meters
R_jupiter = 69911000.0 # meters
lyperpc = 3.262 # light years per parsec
Teffsol = 5780.0 # K
a_mercury = 0.387 # AU
a_earth = 1.0 # AU

tweetlist = []
tweetdict = {}
for planet in allplanets:
    # Calculate upcoming transits for all planets
    transit_epoch = float(exoplanetDB[planet]['TT'])
    period = float(exoplanetDB[planet]['PER'])
    upcoming_transits = midTransit(transit_epoch,period,start_date,end_date)

    # If there is one or more transit occurring within `buildDBforNdays` days,
    if len(upcoming_transits) > 0:
        # For each of those transits, assemble the tweet data!
        for transit in upcoming_transits:
            # Identify constellation containing transiting planet with PyEphem
            star = ephem.FixedBody()
            star._ra = ephem.hours(exoplanetDB[planet]['RA_STRING'])
            star._dec = ephem.degrees(exoplanetDB[planet]['DEC_STRING'])
            star.compute()
            const = ephem.constellation(star)[1] # This is the full cnstellation name

            # Fetch the radius of the planet
            radius = float(exoplanetDB[planet]['R'])
            transittime = transit

            # Identify the minute during which the mid-transit time occurs.
            # This is the basis for how the transt tweet will be stored, since
            # tweets will be updated once per minute via crontab
            transitminute = jd2gd(transit)[:-7]

            # Start building the tweet! The first part will say which planet
            # is transiting
            planetline = "%s is transiting now" % planet

            # If there is a measurd distance to this planet and the tweet is
            # short enough, add in distance.
            distanceline = ""
            if exoplanetDB[planet]['DIST'] != '':
                distance = float(exoplanetDB[planet]['DIST'])*lyperpc
                distanceline = "%i ly away" % distance

            # If there is an effective temperature and tweet is short enough,
            # add it in!
            Teffline = ""
            if exoplanetDB[planet]['TEFF'] != '':
                Teff = float(exoplanetDB[planet]['TEFF'])
                if Teff < Teffsol:
                    Teffline = "star is %i degrees C cooler than the Sun" % (Teffsol-Teff)
                if Teff > Teffsol:
                    Teffline = "star is %i degrees C hotter than the Sun" % (Teff-Teffsol)

            # Name the constellation
            constellationline = "in %s" % const

            # The `radius` parameter is in units of Jupiter radii. Build a
            # sentence comparing the radius to either Jupiter's or Earth's,
            # depending on which is appropriate.
            if radius > 1:
                sizeline = "%.1fx larger than Jupiter" % (radius)
            elif radius <= 1 and radius > R_earth/R_jupiter:
                sizeline = "%.1fx larger than Earth" % (radius*R_jupiter/R_earth)
            elif radius <= R_earth/R_jupiter:
                sizeline = "%.1fx the size of Earth" % (radius*R_jupiter/R_earth)

            # State the orbital period
            periodline = "transits again in %.1f days" % period

            # Build a sentence for the semimajor axis, comparing it to Earth's
            # or Mercury's. Units: AU
            axisline = ''
            if exoplanetDB[planet]['A'] != '':
                a_planet = float(exoplanetDB[planet]['A'])
                if a_planet < a_mercury:
                    axisline = "orbits its star %.1fx closer than Mercury orbits the Sun" % (a_mercury/a_planet)
                elif a_planet > a_mercury and a_planet < a_earth:
                    axisline = "orbits its star %.1fx closer than Earth orbits the Sun" % (a_earth/a_planet)

            # Build a few sentences, hopefully one is <140 characters
            option1 = "%s %s %s. It's %s and %s.\n" % \
                      (planetline, distanceline, constellationline, sizeline, periodline)
            option2 = "%s %s. It's %s and %s.\n" % \
                      (planetline, constellationline, sizeline, periodline)
            option3 = "%s %s %s. It's %s and its %s.\n" % \
                      (planetline, distanceline, constellationline, sizeline, Teffline)
            option4 = "%s %s %s. It's %s and %s.\n" % \
                      (planetline, distanceline, constellationline, sizeline, axisline)
            option5 = "%s %s. It's %s and %s.\n" % \
                      (planetline, constellationline, sizeline, axisline)

            # If the long options are acceptable, choose one randomly
            if len(option1) <= 140 and distanceline != '' and \
               len(option4) <= 140 and axisline != '' and \
               len(option3) <= 140 and Teffline != '':
                tweetline = [option1,option3,option4][randint(3)]

            # If the semimajor axis sentence isn't available, pick between these
            elif len(option1) <= 140 and distanceline != '' and \
                 len(option3) <= 140 and Teffline != '':
                tweetline = [option1,option2,option3][randint(3)]

            # Perferentially include the distance measurement if it's available
            elif len(option1) <= 140 and distanceline != '':
                tweetline = option1

            # If the semimajor axis is available, use that or not, randomly
            elif len(option5) <= 140 and axisline != '':
                tweetline = [option2,option5][randint(2)]

            # Even if none of the extras are available, option2 should always work
            else:
                tweetline = option2

            # If the tweet built is indeed <=140 characters, add it to the
            # dictionary of tweets to post
            if len(tweetline) <= 140:
                eventfile.write(tweetline+'\n')     # tweet text file

                # If the key is already in the dict, make a list of the
                # tweets for that minute
                if transitminute in tweetdict:
                    tweetdict[transitminute].append(tweetline)
                else:
                    tweetdict[transitminute] = [tweetline]

eventfile.close()

# Save tweets to pickle
with open(rootdir+'tweet_dict.pkl','wb') as output:
    cPickle.dump(tweetdict,output)

# Log updates
with open(rootdir+'lastupdatedevents.txt','w') as updatelog:
    updatelog.write('Last updated event list: %s' % (str(datetime.datetime.utcnow())))
