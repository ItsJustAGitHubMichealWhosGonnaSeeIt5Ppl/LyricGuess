import backend as backE
import sys

print('Welcome to the commandline version of Spotify Lyric Guessing Game')

def userInput(text,validInputs,timeout=10,**extras): # Timeout after 10 attampts
    loop = 0
    while loop < timeout:
        userInp = input(text + ': ')
        if userInp != '': 
            if userInp.isnumeric(): # Convert numbers to int
                userInp = int(userInp)
            if validInputs == 'int':
                    return int(userInp)
                    
            elif validInputs == 'any': # Don't check, just get user input
                return userInp
            elif userInp in validInputs:
                return userInp
        else:
            print('Please try again')
    if extras['timeoutMessage'] !=None:
        print(extras['timeoutMessage'])
    sys.exit()
        

def gameWindowCreator(gameDetails):
    pass

text = """What mode would you like to play?
1. Solo
2. Coop (Coming soon)
3. VS (Coming soon)
"""
mode = userInput(text,[1,2,3],timeout=2,timeoutMessage='Goodbye')
if mode in [1,2]:
    print(f'You have chosen {"solo" if mode == 1 else "coop"} mode')
    name = userInput(f'Enter your {'team ' if mode == 2 else ''}name','any')
    rounds = userInput('How many rounds would you like to play?','int')
    guessPerRound = userInput('How many guesses per round would you like','int')
    
    vPlaylist = False
    while vPlaylist == False:
        playlist = backE._getPlaylist(userInput('Enter playlist link/ID','any'))
        if playlist != None:
            vPlaylist = True
            
elif mode == 3: # Doesn't do anything right now
    print('You have chose VS mode')

print('starting game!')

tracks = backE._shuffleTracks(playlist,rounds)

session = backE.playerSession(name,guessPerRound,tracks)
gameRound = 1
toolTip = True
while session.round < session.totalRounds:
    inf = session.roundInformation()
    SongStr = session.correctGuesses['name'] if session.correctGuesses['name'] != None else f'? - {session.guessesPerRound - session.guessCounts['name']} guesses remaining'
    artistStr = session.correctGuesses['artist'] if session.correctGuesses['artist'] != None else f'? - {session.guessesPerRound - session.guessCounts['artist']} guesses remaining'
    nextLineStr = session.correctGuesses['nextLine'] if session.correctGuesses['nextLine'] != None else f'? - {session.guessesPerRound - session.guessCounts['nextLine']} guesses remaining'
    text = f"""
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    Round {session.round} - Score: {session.score}
    Lyric: {inf['trackDetails']['lyric']}
    """
    if session.roundStatus == 'Active':
        text += f"""
        1. Song Title (Name): {SongStr}
        2. Artist: {artistStr}
        3. Next Line: {nextLineStr}
        4. Give Up
        """
        if toolTip == True:
            text += '\nTo guess enter the number, then your guess EG: 1 Stevie Wonder'
        text += '\nYour Guess:'
    elif session.roundStatus == 'Ended':
        text += f"""
        Song Title (Name): {SongStr}
        Artist: {artistStr}
        Next Line: {nextLineStr}
        4. NextRound
        When you're ready: 
        """
    guess = input(text)
    if guess.startswith('1'):
        session.guess({'name':guess.replace('1 ','')})
    elif guess.startswith('2'):
        session.guess({'artist':guess.replace('2 ','')})
    elif guess.startswith('3'):
        session.guess({'nextLine':guess.replace('3 ','')})
    elif guess.startswith('4'):
        if session.roundStatus == 'Ended':
            session.createRound()
        else:
            session.endRound()
    else:
        print('not a valid guess')