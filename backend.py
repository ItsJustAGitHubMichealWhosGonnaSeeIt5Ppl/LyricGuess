from lyricsgenius import Genius
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import random
import sqlite3
import re
import logging
import json
from requests import exceptions as reqExcept
import concurrent.futures # Threading?

#TODO fix multiplayer modes
#TODO add sqlite database to track user highscores
#TODO filter "The" from artist name
#TODO filter (featuring) from title
#TODO Filter out apostrophes
#TODO add logging
#TODO use regex to compare guesses

SPOTIPY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_SECRET = os.getenv('SPOTIFY_SECRET')
GENIUS_TOKEN = os.getenv('GENIUS_TOKEN')

# Authorise spotify and Genius

scope = "user-library-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope,client_id=SPOTIPY_CLIENT_ID,client_secret=SPOTIFY_SECRET,redirect_uri='http://localhost:8080'))
genius = Genius(GENIUS_TOKEN,verbose=False)


# Cache songs

con = sqlite3.connect("cachedLyrics.db")
cursor = con.cursor()
cursor.execute("""CREATE TABLE if NOT EXISTS cached_lyrics(
            songID TEXT PRIMARY KEY,
            lyrics TEXT
        )""")

pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Playlist
def _getPlaylist(playlistID,getLyrics=False):
    """Get playlist info, optionally, get lyrics

    Args:
        playlistID (_type_): Spotify playlist link/ID
        getLyrics (bool, optional): Get lyrics for playlist items, if used, remember not to cache lyrics if you start a game before its done!. Defaults to False.

    Returns:
        list: List of tracks
    """
    global pool
    def getAll(): # Loop through all tracks and add them to cache DB
        for track in tracks: 
            _getLyrics(track)
    # Basic input validation
    if playlistID.startswith('http'): 
        playlistID = playlistID.split('?si=')[0]
    playlistID = playlistID.replace('https://open.spotify.com/playlist/','').replace('spotify:playlist:','')
    try:
        playlist = sp.playlist(playlist_id=playlistID)
    except:
        return None
        
    
    playlist = playlist['tracks']
    tracksList = playlist['items']

    while playlist['next']: # If more than 100 songs are in playlist, continue collecting.
        playlist = sp.next(playlist)
        tracksList.extend(playlist['items'])
    tracks = []

    for track in tracksList:
        track = track['track'] # Ignore unneeded information
        artists = [artist['name'] for artist in track['artists']]
        tracks += [{
            'name': track['name'],
            'artists': artists,
            'album': track['album']['name'],
            'id': track['id']
        }]
    if getLyrics: # Get lyrics for all songs
        pool.submit(getAll)
        #pool.shutdown(wait=False)
    return tracks

def _shuffleTracks(tracks,rounds,cacheLyrics=True):
    database = sqlite3.connect("cachedLyrics.db")
    cursor = database.cursor()
    random.shuffle(tracks)# Shuffle the tracks
    loop = 0
    roundData = []
    for track in tracks:
        if loop < int(rounds):
            lyrics = _getLyrics(track,cacheLyrics)
            if lyrics != None:
                roundData += [{
                'name': track['name'],
                'artist': track['artists'][0], # For now, only use the first artist
                'lyrics': lyrics # Maybe move the song lyric choice to here?
                }]

                loop += 1
            else:
                continue # No matching lyrics

        else:
                break
    return roundData


def _getLyrics(track,cache=True):
    """Get lyrics from internal DB or genius

    Args:
        track (dict): Custom track object
        cache (bool, optional): Cache lyrics into the database.  IF YOU HAVE STARTED A FULL CACHE OF A PLAYLIST, MAKE SURE THIS IS FALSE!!!!!!!!

    Returns:
        list: Lyrics in list form
    """
    lyrics = None
    database = sqlite3.connect("cachedLyrics.db")
    cursor = database.cursor()
    cursor.execute(""" SELECT * FROM cached_lyrics WHERE songID=?""",(track['id'],))
    lyricsFromDB = cursor.fetchone()
    
    if lyricsFromDB != None:
        lyrics = json.loads(lyricsFromDB[1])

    else:
        fails = 0

        while fails < 10: # Allow 10 failures
            try:
                artist = genius.search_artist(track['artists'][0],max_songs=0)
                lyrics = artist.song(track['name'])
                break
            except reqExcept.ReadTimeout:
                fails +=1
                continue
            except AttributeError:
                fails +=1
                continue
                
        if lyrics != None and lyrics.lyrics_state == 'complete': # Skip songs where lyrics can't be found.
            lyrics = lyrics.lyrics
            lyrics = lyrics.split('\n')  # Create list of each lyric line
            lyrics = [line.replace('\\','') for line in lyrics if line not in [''] and line.startswith(f'See {track['artists'][0]}') == False and line.startswith('(') == False and line.startswith('[') == False] # Remove blank lyrics and things like [Chorus], [Verse 2]
            if cache: # Hopefully avoids issues of the same track being added twice
                cursor.execute("INSERT OR IGNORE INTO cached_lyrics VALUES(:songID, :lyrics)",(track['id'], json.dumps(lyrics)))
                database.commit()
        else:
            return None
    
    return lyrics

class playerSession: # Track a game
    def __init__(self,name,guessesPer,tracks,debug=False):
        #logger
        if debug:
            logging.basicConfig(level='DEBUG')
        # Game info
        self.playerName = name
        self.totalRounds = len(tracks)
        self.guessesPerRound = int(guessesPer)
        self.tracks = tracks
        self.round = 1
        self.score = 0
        self.roundStatus = 'Active'
        self.createRound() # Start the first round
        

    # round info (resets each time)
    def resetRoundInfo(self):
        self.guessCounts = {
            'name': 0,
            'artist': 0, 
            'nextLine':0
        }
        self.correctGuesses = {
            'name': None,
            'artist': None, 
            'nextLine': None,
        }
        self.correctCount = 0
        self.currentTrack = None
        self.roundStatus = 'Active'

    def createRound(self): # Create a new game round
        # Reset round info
        self.resetRoundInfo()
        nextTrack = self.tracks[self.round-1]
        
        lyrics = nextTrack['lyrics']
        totalLyrics = len(lyrics)
        ranLoop = True
        while ranLoop == True: # Avoid short annoying lyrics
            ranNum = random.randint(1,totalLyrics-2)
            if len(lyrics[ranNum].replace('-',' ').split(' ')) > 5:
                ranLoop = False
                
        self.currentTrack = {
            'name': nextTrack['name'],
            'artist': nextTrack['artist'],
            'lyric': lyrics[ranNum],
            'nextLine': lyrics[ranNum+1],
            }
        logging.debug(f'Current Song: {self.currentTrack['name']}, next line: {self.currentTrack['nextLine']}')
        
    
    def guess(self,guessData):
        for field, guess in guessData.items():
            logging.debug(f'COMPARING: Guess: {guess.strip(".,`';-! " if field == 'song'else ".,`';- ").lower()}, Correct Answer: {self.currentTrack[field].strip(".,`';-! " if field == 'song'else ".,`';- ").lower()}. Field: {field}')
            correct = False
            if field == 'button':
                continue
            if guess != '':
                if guess.strip(".,`';- ").lower() in self.currentTrack[field].strip(".,`';- ").lower():
                    correct = True
                elif field == 'song' and guess.strip(".,`';-! ").lower() in self.currentTrack[field].split('(')[0].strip(".,`';-! ").lower():
                    correct = True
                if correct == True:
                    logging.info('CORRECT GUESS')
                    self.score += self.guessesPerRound - self.guessCounts[field]
                    self.correctGuesses[field] = self.currentTrack[field]
                    self.guessCounts[field] =3 # Prevent further guesses
                else:
                    self.guessCounts[field] +=1
                    logging.info('INCORRECT GUESS')
    
    def endRound(self):
        self.correctGuesses = {
            'name': self.currentTrack['name'],
            'artist': self.currentTrack['artist'],
            'nextLine': self.currentTrack['nextLine'],
        }
        self.round+=1
        self.roundStatus = 'Ended'
        
    
    def roundInformation(self): # Package up round info
        info = {
            'trackDetails': self.currentTrack,
            'score': self.score,
            'round': self.round,
            'totalGuesses': self.guessesPerRound,
            'remainingGuesses': self.guessCounts,
            'correctGuesses':self.correctGuesses,
            'totalRounds':self.totalRounds,
            
        }
        return info
    
    



