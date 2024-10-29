import os
import random
from flask import Flask, render_template, request, redirect, url_for
from waitress import serve
import backend as bE


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
    global p1
    if request.method == 'POST':
        
        formData = request.form.to_dict()
        tracks = bE._getPlaylist(formData['playlist'])
        if tracks == None:
            return redirect(url_for('.home',reason='Invalid Playlist'))
        shuffledTracks= bE._shuffleTracks(tracks,formData['rounds'])
        p1 = bE.playerSession('Player',formData['guessesPer'],shuffledTracks)
        roundInfo = p1.roundInformation()
        return render_template('game.html',roundData = roundInfo,button={'text': 'Guess'})
    else:
        return redirect(url_for('.home',reason=''))


@app.route("/guess", methods=['POST'])
def guess():
    global p1
    formData = request.form.to_dict()
    if formData['button'] == 'Guess':
        p1.guess(formData)
    elif formData['button'] == 'Give Up':
        p1.endRound()
    elif formData['button'] == 'Next Round':
        p1.createRound()
    roundInfo = p1.roundInformation()
    
    return render_template('game.html',roundData = roundInfo,button={'text':f"{'Guess'if p1.roundStatus=='Active'else 'Next Round'}"})





# Start webserver
if __name__ == '__main__': 
    serve(app, host = 'localhost', port=8888)

