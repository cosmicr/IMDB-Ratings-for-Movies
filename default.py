import os #for file listing
import time #for timestamp
import sys #for pathing and stuff
import urllib, urllib2 #for opening the website
import re #regular expressions
import shutil #for copying the database
try:
    import sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

import xbmc
import xbmcgui
import xbmcaddon

'''setup some general variables'''
#this is used for output to the debug log
d_error = "IMDB Rating Script ERROR: "
d_notify = "IMDB Rating Script: "

#this is used to easily get settings
Addon = xbmcaddon.Addon(id='script.imdbratings')

#the path to the script
script_path = Addon.getAddonInfo('path')

#the path to the file with the last updated imdb id
lastupdated = os.path.join(script_path, "resources/lastid.dat")

#the path to the imdb icon
logoicon = os.path.join (script_path , "resources/images/logo.png")

#the path to the database
database_path = os.path.join(script_path, "../../userdata/Database")

# The url in which to find the imdb data
Base_URL = "http://www.imdb.com/title/"

#for spoofing imdb
headers = { 'User-Agent' : 'Mozilla/5.0' }

#notify the user
xbmc.executebuiltin('xbmc.Notification(IMDB Ratings Beginning Update,This may take some time...,10000,'+logoicon+')') 

#what database type are we working with?
MySQL = int(Addon.getSetting("database"))
print d_notify + "Database type is set to " + ("MySQL" if MySQL else "SQLite")
if MySQL:
  MySQL_Address = Addon.getSetting("dbloc")
  if MySQL_Address.startswith("0."):
    print d_error + "MySQL Server Addres not set correctly"
    sys.exit()
  else:
    print d_notify + "MySQL Server Address is " + MySQL_Address
  dialog = xbmcgui.Dialog()
  if not dialog.yesno('Warning', 'Please ensure you have a backup of your database','as MySQL functionality is experimental.','Do you want to continue?'):
    sys.exit()

#for MySQL
sys.path.append( os.path.join(script_path, "resources/lib") ) 
import MySQLdb as mdb

#find the database name
databases = [] #an empty array
if not MySQL:
  try: 
    filelist = os.listdir(database_path) #get a directory listing
  except Exception, inst:
    print d_error + "Unable to find database file in " + database_path
    sys.exit()
  for f in filelist:
    if f.startswith('MyVideo') and f.endswith('.db'): #check for valid database names
	  databases.append(f) #add it to the array
  databases.sort() #sort the list of database file(s)
  filename = databases.pop() #get the last one since it should be the latest
  database = os.path.join(script_path, database_path, filename) #put the paths all together
else: #find mysql db name
  try:
    conn = mdb.connect(MySQL_Address, 'xbmc', 'xbmc')
  except:
    print d_error + "Couldn't connect to database. Check the ip address is correct."
    xbmc.executebuiltin("xbmc.Notification(IMDB Ratings,Couldn't connect to database,5000,"+logoicon+")") 
    sys.exit()
  c = conn.cursor()
  c.execute("show databases")
  dblist = []
  for f in c.fetchall():
    dblist.extend(list(f))
  for f in dblist:
    if f.startswith('MyVideo'):
      databases.append(f)
  databases.sort()
  database = databases.pop()
  print d_notify + "db name is " + database
  q = "USE " + database
  c.execute(q)


'''backup the database'''
if not MySQL:
  databasebackup = database + ".bak." + time.strftime("%Y%m%d-%H%M",time.localtime())
  try:
    shutil.copy(database, databasebackup)
  #if it doesnt work we want to stop the script
  except IOError as (errno, strerror):
    print d_error + "Error backing up database: I/O error({0}): {1}".format(errno, strerror)
    print d_error + "I was trying to save it to " + databasebackup
    sys.exit()
	
#so far so good!
  print d_notify + "Database backed up to " + databasebackup
print d_notify + "So far so good!"

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
		print d_notify + "lastid.dat doesnt exist. This is normal on first run."
		lastid = 0

if (lastid==0):
	print d_notify + "Getting ratings for all movies in library..."
else:
	print d_notify + "Getting ratings for new movies in library starting at id " + str(lastid) + "..."

'''get the movies'''
if not MySQL:
  try: 
    conn = sqlite3.connect(database)
  except:
    print d_error + "Couldn't connect to database!"
    sys.exit()
  c = conn.cursor()

#get all the imdb id's from each movie
q = 'SELECT c09, c00, idMovie FROM movie WHERE idMovie > ' + str(lastid)
c.execute(q) #c09 = imdb id, c00 = the title, idMovie = the internal id
num_movies = 0 # number of movies, duh
#empty arrays for the movie metadata
imdbid = []
title = []
lid = []
for row in c:
	if (row[0]==''):
		print d_notify + row[1] + " doesnt seem have an IMDB id!!!"
	else:
		imdbid.append(row[0])
		title.append(row[1])
		lid.append(row[2])
		num_movies = num_movies + 1
	lastid = row[2]

#okay, lets update the movies
j = 0 #an index for the movies in the database
if (num_movies):
	print d_notify + str(num_movies) + " Movies to update"
	for num in imdbid:
		if (num):		
			print d_notify + "Opening " + Base_URL + num
			try:
				req = urllib2.Request(Base_URL+num, None, headers) #merge the header with the url
				WebSock = urllib2.urlopen(req) #open the url to the movie
			except:
				print d_error + "Couldn't open url (probably timed out)."
				xbmc.executebuiltin('xbmc.Notification(IMDB Ratings,COULDNT OPEN URL)') 
				break;
			WebHTML = WebSock.read() #get the data from the webpage
			WebSock.close() #close the connection
			rating = re.compile('([0-9]\.[0-9])\/10').findall(WebHTML) #regular expression to find the rating
			votes = re.compile('([0-9]{1,3}[,]*[0-9]{1,3}) votes').findall(WebHTML) #regular expression to find the number of votes
			top250 = re.compile('Top 250 #([0-9]{1,3})').findall(WebHTML) #regular expression to find the top250 (if it's there)
			string =  d_notify + title[j] + "(" + str(lid[j]) + ")" + " rating: " + str(rating[0]) + "/10"
			print string.encode("ascii", "ignore") #update the log
			xbmc.executebuiltin('xbmc.Notification(IMDB Ratings,'+title[j].encode("ascii", "ignore")+',1000,'+logoicon+')') #tell the user which movie
			if(rating):
				q = 'UPDATE movie SET c05 = ' + str(rating[0]) + ' WHERE idMovie = ' + str(lid[j])
				c.execute(q)
				if(votes):
					q = 'UPDATE movie SET c04 = "' + str(votes[0]) + '" WHERE idMovie = ' + str(lid[j])
					c.execute(q)
				if(top250):
					print d_notify + "Top #250: " + str(top250[0])
					q = 'UPDATE movie SET c13 = "' + str(top250[0])  + '" WHERE idMovie =  ' + str(lid[j])
					c.execute(q)
			j = j + 1

	#commit the updates to the database
	conn.commit()
	c.close()     
	#write out the last id updated
	file( lastupdated , "w" ).write(str(lid[j-1]))
	print d_notify + "Wrote out lastid as "+str(lid[j-1]) + " (updated " + str(j) + " movies)"
else:
	print d_notify + "Nothing to update"

print d_notify + "Ratings script complete."

xbmc.executebuiltin('xbmc.Notification(IMDB Ratings,Update Complete,5000,'+logoicon+')') 


