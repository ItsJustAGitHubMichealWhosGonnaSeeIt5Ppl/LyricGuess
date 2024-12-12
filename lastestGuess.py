""" IDEA
Based on https://lastguess.net/ game for Last FM except with a playlist.

User is presented with a single line of lyrics from a song, they must guess the title of the song, artist, and next time.

Things I want to be different from LastGuess
Make the lyrics a bit longer
Allow more configuration of score, etc

"""
# TODO Choose user interface (web?)
#TODO if song title is in lyric, don't display
#TODO print debug info of song
#TODO thread lyric loading so game can start quicker

from lyricsgenius import Genius
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import random
from flask import Flask, render_template, request, redirect, url_for
from waitress import serve


SPOTIPY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_SECRET = os.getenv('SPOTIFY_SECRET')
GENIUS_TOKEN = os.getenv('GENIUS_TOKEN')

# User variables (will be added to a setup page)

# Authorise spotify and Genius

scope = "user-library-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope,client_id=SPOTIPY_CLIENT_ID,client_secret=SPOTIFY_SECRET,redirect_uri='http://localhost:8080'))
genius = Genius(GENIUS_TOKEN,verbose=False)


# Playlist
def getPlaylist(playlistID):
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
            'album': track['album']['name']
        }]

    return tracks


    

class game: # Track a game
    def __init__(self,tracks,totalRounds):
        self.tracks = tracks.copy()
        self.shuffledTracks = self._shuffleTracks(tracks,totalRounds)
        self.currentRound = 1
        self.currentScore = 0
        self.totalRounds = totalRounds
        self.guessesPerRound = 3
        self.guessCounts = {
            'name': 0,
            'artist': 0, 
            'nextLine':0
        }
        self.correctGuesses = {}
        self.buttonText = 'Guess'
    
    def _shuffleTracks(self,tracks,rounds):
        random.shuffle(tracks)# Shuffle the tracks
        loop = 0
        roundData = []
        for track in tracks:
            if loop < rounds:
                lyrics = genius.search_song(title=track['name'],artist=track['artists'][0])       
                if lyrics != None: # Skip songs where lyrics can't be found.
                    lyrics = lyrics.lyrics
                    lyrics = lyrics.split('\n')  # Create list of each lyric line
                    lyrics.pop(0) # Remove Contributors line
                    lyrics = [line for line in lyrics if line not in [''] and line.startswith(f'See {track['artists'][0]}') == False and line.startswith('(') == False and line.startswith('[') == False] # Remove blank lyrics and things like [Chorus], [Verse 2]
                    roundData += [{
                        'name': track['name'],
                        'artist': track['artists'][0], # For now, only use the first artist
                        'lyrics': lyrics # Maybe move the song lyric choice to here?
                    }]
                    loop += 1
                else:
                    continue
            else:
                break
        return roundData

    def createRound(self):
        self.guessCounts = {
            'name': 0,
            'artist': 0, 
            'nextLine':0
        }
        self.correctGuesses = {}
        self.correctCount == 0
        
        self.currentRoundTrack = self.shuffledTracks[self.currentRound-1]
        lyrics = self.currentRoundTrack['lyrics']
        totalLyrics = len(lyrics)
        ranNum = random.randint(1,totalLyrics-2)
        self.currentLyric = lyrics[ranNum]
        self.nextLyric = lyrics[ranNum+1]
        return self.currentLyric
    
    def guess(self,guessData):
        for field, guess in guessData.items():
            if field != 'button' and guess != '':
                if field == 'nextLine':
                    if guess.lower() in self.nextLyric.strip(".,`';").lower():
                        self.currentScore += self.guessesPerRound - self.guessCounts[field]
                        self.guessCounts[field] = 'Correct'
                        self.correctGuesses[field] = self.nextLyric
                    else:
                        self.guessCounts[field] +=1
                else:
                    if guess.lower() == self.currentRoundTrack[field].lower():
                            self.currentScore += self.guessesPerRound - self.guessCounts[field]
                            self.guessCounts[field] = 'Correct'
                            self.correctGuesses[field] = self.currentRoundTrack[field]
                            
                    else:
                        self.guessCounts[field] +=1
        if len(self.correctGuesses.keys()) >= 3: # 3 Correct guesses
            self.buttonText = 'Next Round'
        
    
    def giveUp(self): # Add reveal.
        self.currentRound+=1
        self.createRound()
    
    def roundInformation(self): # Package up round info
        roundInfo = {
            'playlist': 'NA',
            'lyric': self.currentLyric,
            'nameAttempt': self.guessCounts['name'],
            'artistAttempt': self.guessCounts['artist'],
            'nextLineAttempt': self.guessCounts['nextLine'],
            'score': self.currentScore,
            'currentRound': self.currentRound,
            'totalRounds': self.totalRounds,
            'allowedGuesses': self.guessesPerRound,
            'button': self.buttonText
            
        }
        return roundInfo, self.correctGuesses


def createPlayer():
    pass
       

app = Flask(__name__)

@app.route("/")
def home():
    try:
        reason = request.args['reason']
    except:
        reason = ''
    return render_template('home.html',message=reason)


@app.route("/setup", methods=['GET', 'POST'])
def setupGame():
    global setupFormData
    if request.method == 'POST':
        setupFormData = request.form.to_dict()
        if len(setupFormData.keys()) < 2:
             return redirect(url_for('.home',reason='please set gamemode and player count'))
        elif setupFormData['gameMode'] in ['vs','coop'] and setupFormData['playerCount'].isnumeric():
            setupFormData['playerCount'] = int(setupFormData['playerCount']) # Convert to int
            return render_template('settings.html',data = setupFormData)
        
        else:
            return redirect(url_for('.home',reason='please set player count'))
        
    else:
        return redirect(url_for('.home'))

@app.route("/start", methods=['GET', 'POST'])

def start():
    global setupFormData
    if request.method == 'POST':
        
        formData = request.form.to_dict()
        
        for player in range(0, setupFormData['playerCount']):
            
        
        playerTracks = getPlaylist(formData['playlistID'])
        if playerTracks == None:
            return redirect(url_for('.home',reason='Invalid Playlist ID'))
        
        
        p1 = game(playerTracks,5)
        p1.createRound()
        roundInfo = p1.roundInformation()
        return render_template('game.html',roundData = roundInfo[0],correctGuesses=roundInfo[1])
    else:
        return redirect(url_for('.home',reason=''))


@app.route("/guess", methods=['POST'])
def guess():
    global p1
    formData = request.form.to_dict()
    if formData['button'] == 'Guess':
        p1.guess(formData)
    elif formData['button'] == 'Next Round':
        p1.giveUp()
    else:
        p1.giveUp()
    roundInfo = p1.roundInformation()
    return render_template('game.html',roundData = roundInfo[0],correctGuesses=roundInfo[1])
    





# Start webserver
if __name__ == '__main__': 
    serve(app, host = 'localhost', port=8888)

