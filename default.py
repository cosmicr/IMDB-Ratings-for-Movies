import os #for file listing
import time #for timestamp
import sys #for pathing and stuff
import urllib, urllib2 #for opening the website
import simplejson #for json api

import xbmc
import xbmcgui
import xbmcaddon

'''setup some general variables'''
#this is used to easily get settings
Addon = xbmcaddon.Addon(id='script.imdbratings')

#the path to the script
script_path = Addon.getAddonInfo('path')

#the path to the file with the last updated imdb id
lastupdated = os.path.join(script_path, "resources/lastid.dat")

#the path to the imdb icon
logoicon = os.path.join (script_path , "resources/images/logo.png")

#this is used for output to the debug log
def lognotify(message):
    xbmc.log(u'IMDB Rating Script: %s' % message)
def logerror(message):
    xbmc.log(u'IMDB Rating Script ERROR: %s' % message)

'''functions used for output to the user'''
#localised strings, set in strings.xml
STRINGS = {
    'beginning_update': 30010,
    'update_complete': 30011,
    'rating': 30012,
    'imdb_ratings_update': 30013,
    'you_have_more_than_fifty_movies_to_update': 30014,
    'are_you_sure_you_want_to_continue': 30015,
}

#get the correct string for this user's localisation    
def _(string_id):
    if string_id in STRINGS:
        return Addon.getLocalizedString(STRINGS[string_id])
    else:
        logerror('String is missing: %s' % string_id)
        return string_id
    
#notification function
def notify(message):
    xbmc.executebuiltin('xbmc.Notification('+message+',6000,'+logoicon+')') 

    
'''main routine'''
def main():
    #check if we need to do the whole library (ie clean is set in the settings)
    if(Addon.getSetting("clean")=="true"):
        lastid = 0
        Addon.setSetting("clean", "false")
    else:
        try:
            f = open(lastupdated,'r')
            lastid = f.read()
            f.close()
        except IOError:
            lognotify("lastid.dat doesnt exist. This is normal on first run.")
            lastid = 0

    if (lastid==0):
        lognotify("Getting ratings for all movies in library...")
    else:
        lognotify("Getting ratings for new movies in library starting at id " + str(lastid) + "...")

    '''get the movies'''
    command='{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties" : ["rating", "imdbnumber", "votes", "top250", "year"] }, "id": 1}'
    result = xbmc.executeJSONRPC( command )
    result = unicode(result, 'ascii', errors='ignore')
    jsonobject = simplejson.loads(result)
    movies = jsonobject["result"]["movies"]

    #time to update the movies
    numupdated = 0
    lastupdatedid = lastid
    for index, movie in enumerate(movies):
        if int(movie['movieid']) > int(lastid)-1:
            movies = movies[index+1:]
            break
    lognotify("Number of movies to update: " + str(len(movies)))
    if(len(movies)>60):
        dialog = xbmcgui.Dialog()
        if(dialog.yesno(_('imdb_ratings_update'), _('you_have_more_than_fifty_movies_to_update'),_('are_you_sure_you_want_to_continue'))==False):
            return
    pDialog = xbmcgui.DialogProgress()
    pDialog.create(_('imdb_ratings_update'), _('beginning_update'))
    for movie in movies:
        if (pDialog.iscanceled()): break
        lastupdatedid = movie['movieid']
        if movie['imdbnumber'] == "":
            logerror(movie['label'] + " doesn't have an imdb number in the database - using manual search.")
            url = "http://www.omdbapi.com/?t=" + urllib.quote(movie['label']) + "&y=" + str(movie['year'])
            lognotify(url)
        else:
            url = "http://www.omdbapi.com/?i=" + movie['imdbnumber']
        imdbdata = simplejson.load(urllib2.urlopen(url))
        if imdbdata['Response'] == 'False':
            logerror("Oops! That Didn't work! Skipping this movie")
            continue
        movieid = str(movie['movieid'])
        rating = str(imdbdata["imdbRating"])
        votes = str(imdbdata["imdbVotes"])
        command='{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid" : ' + movieid + ', "rating" : '+ rating + ', "votes" : "' + votes + '"}, "id": 2}'
        result = xbmc.executeJSONRPC( command )
        #lognotify the user
        percent = (float(numupdated)/len(movies))*100
        pDialog.update(percent,_('beginning_update'),movie['label'],_('rating')+rating)
        numupdated = numupdated + 1

    #write out the last id updated
    if lastupdatedid == lastid:
        lognotify("Nothing to update.")
    else:
        file( lastupdated , "w" ).write(str(lastupdatedid))
        lognotify("Wrote out lastid as "+str(lastupdatedid) + " (updated " + str(numupdated) + " movies)")

    pDialog.close()
    lognotify("Ratings script complete.")

    notify(_('update_complete'))

if __name__ == '__main__':
    main()

