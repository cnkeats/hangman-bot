import discord
import os
import time
import sys
import asyncio
from spellchecker import SpellChecker

client = discord.Client()

file = open('channel.txt', 'r')
botChannelId = int(file.read())

file = open('admins.txt', 'r')
adminId = int(file.read())

def matchingAuthor(author):
    def innerCheck(message):
        authorMatches = message.author = author
        singleWord = (' ' in message.content) == False
        private = message.channel.type == discord.ChannelType.private
        validWord = len(SpellChecker().unknown([message.content])) == 0
        return authorMatches and singleWord and (private) and validWord
    return innerCheck

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await readyForNewGame()

@client.event
async def on_message(message):
    # Bot should never reply to itself
    if message.author == client.user:
        return

    elif message.content.startswith('!kill') and message.author == client.get_user(adminId):
        await message.channel.send('Bye! :(')
        os._exit(1)
        return

    elif message.content.startswith('!r') and message.author == client.get_user(adminId):
        await message.channel.send('Restarting!')
        print('Restarting the client!')
        os.execl(sys.executable, sys.executable, *sys.argv)
        os._exit(1)
        return
    
    elif message.content.startswith('!wm') or message.content.startswith('!wordmaster') and message.author == client.get_user(adminId) and message.channel == client.get_channel(botChannelId):
        if hasattr(client, 'wordmaster'):
            await message.channel.send('The current wordmaster is ' + str(client.wordmaster))
        else:
            await message.channel.send('There is currently no wordmaster! (Type !hangman to become the Wordmaster!)')
        await message.delete()
        return
    
    elif message.content.startswith('!c') and message.author == client.get_user(adminId):
        if hasattr(client, 'wordmaster'):
            delattr(client, 'wordmaster')
        return
    
    elif message.content.startswith('!hangman') or message.content.startswith('!h') and not hasattr(client, 'wordmaster') and message.channel == client.get_channel(botChannelId):
        await message.delete()
        await startNewGame(message)

        if (not hasattr(client, 'wordmaster')):
            return
        
        await message.channel.send('Wordmaster {0} has chosen a word! React to vote on a letter to pick!\n(Voting ends after 15 seconds)'.format(str(client.wordmaster.mention)))

        while (client.letterStrikes < client.maxStrikes and not client.solved):
            hangmanText = stage[client.letterStrikes]
            guessedLettersText = '```Guessed letters: '
            for letter in client.guessedLetters:
                guessedLettersText += letter + ' '
            reactMessage0 = await message.channel.send(hangmanText + guessedLettersText + '```')

            wordGuessText = ''
            for i in range(0, len(client.word)):
                if (client.word[i] in client.guessedLetters):
                    wordGuessText += client.word[i] + ' '
                else:
                    wordGuessText += '_ '
            await client.change_presence(activity=discord.Game(name=wordGuessText[:-1]))
            reactMessage1 = await message.channel.send('```{0}```'.format(wordGuessText[:-1]))
            await addLetterReactions(reactMessage0, reactMessage1, client.guessedLetters)
            client.reactMessage0 = reactMessage0
            client.reactMessage1 = reactMessage1

            readyToGuess = False
            maxVotes = 0
            maxVoted = None
            while (not readyToGuess):
                time.sleep(15)
                reactions0 = await message.channel.fetch_message(client.reactMessage0.id)
                reactions1 = await message.channel.fetch_message(client.reactMessage1.id)
                fullReactions = reactions0.reactions + reactions1.reactions

                for reaction in fullReactions:
                    if (reaction.count - 1 > maxVotes):
                        maxVoted = reaction
                        maxVotes = reaction.count - 1
                # Only break the loop if at least one person voted
                if (maxVotes > 0):
                    readyToGuess = True
            
            messageText = '\n{0} was the winning guess with {1} votes!'.format(maxVoted, maxVotes)
            
            if (emojiLetterDict[str(maxVoted)] in client.word):
                messageText += ' The guess was correct!'
            else:
                messageText += ' The guess was incorrect!'
                client.letterStrikes += 1
            #await message.channel.send(messageText)
            
            client.guessedLetters += emojiLetterDict[str(maxVoted)]

            client.solved = True
            for letter in client.word:
                if letter not in client.guessedLetters:
                    client.solved = False
    
        hangmanText = stage[client.letterStrikes]

        guessedLettersText = 'Guessed letters: '
        for letter in client.guessedLetters:
            guessedLettersText += letter + ' '
        
        resultText = ''
        if (client.solved):
            resultText = 'won'
        else:
            resultText = 'lost'

        wordGuessText = ''
        for i in range(0, len(client.word)):
            if (client.word[i] in client.guessedLetters):
                wordGuessText += client.word[i] + ' '
            else:
                wordGuessText += '_ '
        
        await message.channel.send('{0}```{1}``````{2}```You {3}! The word was {4}!'.format(hangmanText, guessedLettersText, wordGuessText, resultText, client.word))
        await readyForNewGame()
        return
    
    # The bot will delete messages by default if posted in #bot-spam by someone other than the wordmaster
    elif message.channel == client.get_channel(botChannelId):
        print('deleted message : ' + message.content)
        await message.delete()

async def readyForNewGame():
    if (hasattr(client, 'wordmaster')):
        delattr(client, 'wordmaster')
    await client.change_presence(activity=discord.Game(name='Hangman! (Waiting for a Wordmaster)'))
    botSpamChannel = client.get_channel(botChannelId)
    await botSpamChannel.send('Lets play Hangman! Type !hangman to become the Wordmaster!')

async def startNewGame(message):
    await message.channel.send('Starting a new Hangman game!')
    client.wordmaster = message.author
    await client.change_presence(activity=discord.Game(name='Hangman (Wordmaster is ' + str(client.wordmaster) + ')'))
    try:
        await message.author.send('Please tell me your secret Hangman word! It must be a single word with no spaces and in my dictionary! (I\'m currently missing some words - sorry!)')
        word = (await client.wait_for('message', timeout=15.0, check=matchingAuthor(message.author))).content.upper()
    except asyncio.TimeoutError:
        await message.author.send('You took too long! :(')
        await message.channel.send(str(client.wordmaster) + ' took too long to give me a word! Type !hangman to become the Wordmaster!') 
        await client.change_presence(activity=discord.Game(name='Hangman! (Waiting for a Wordmaster)'))
        delattr(client, 'wordmaster')
        return
    
    client.guessedLetters = []
    client.letterStrikes = 0
    client.maxStrikes = 6
    client.word = word
    client.partialWord = ''
    client.solved = False

async def addLetterReactions(message0, message1, guessedLetters):
    alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        
    filteredAlphabet = [letter for letter in alphabet if letter not in guessedLetters]

    for letter in filteredAlphabet[:len(filteredAlphabet)//2]:
        await message0.add_reaction(letterEmojiDict[letter])
    for letter in filteredAlphabet[len(filteredAlphabet)//2:]:
        await message1.add_reaction(letterEmojiDict[letter])
    return

stage = { 
    0 :
    '```\n  +------+\n  |      |\n  |\n  |\n  |\n  |\n============```',
    1 :
    '```\n  +------+\n  |      |\n  |      O\n  |\n  |\n  |\n============```',
    2 :
    '```\n  +------+\n  |      |\n  |      O\n  |      |\n  |\n  |\n============```',
    3 :
    '```\n  +------+\n  |      |\n  |      O\n  |     /|\n  |\n  |\n============```',
    4 :
    '```\n  +------+\n  |      |\n  |      O\n  |     /|\\\n  |\n  |\n============```',
    5 :
    '```\n  +------+\n  |      |\n  |      O\n  |     /|\\\n  |     /\n  |\n============```',
    6 :
    '```\n  +------+\n  |      |\n  |      O\n  |     /|\\\n  |     / \\\n  |\n============```',
}

letterEmojiDict = {
    'A' : '\N{REGIONAL INDICATOR SYMBOL LETTER A}',
    'B' : '\N{REGIONAL INDICATOR SYMBOL LETTER B}',
    'C' : '\N{REGIONAL INDICATOR SYMBOL LETTER C}',
    'D' : '\N{REGIONAL INDICATOR SYMBOL LETTER D}',
    'E' : '\N{REGIONAL INDICATOR SYMBOL LETTER E}',
    'F' : '\N{REGIONAL INDICATOR SYMBOL LETTER F}',
    'G' : '\N{REGIONAL INDICATOR SYMBOL LETTER G}',
    'H' : '\N{REGIONAL INDICATOR SYMBOL LETTER H}',
    'I' : '\N{REGIONAL INDICATOR SYMBOL LETTER I}',
    'J' : '\N{REGIONAL INDICATOR SYMBOL LETTER J}',
    'K' : '\N{REGIONAL INDICATOR SYMBOL LETTER K}',
    'L' : '\N{REGIONAL INDICATOR SYMBOL LETTER L}',
    'M' : '\N{REGIONAL INDICATOR SYMBOL LETTER M}',
    'N' : '\N{REGIONAL INDICATOR SYMBOL LETTER N}',
    'O' : '\N{REGIONAL INDICATOR SYMBOL LETTER O}',
    'P' : '\N{REGIONAL INDICATOR SYMBOL LETTER P}',
    'Q' : '\N{REGIONAL INDICATOR SYMBOL LETTER Q}',
    'R' : '\N{REGIONAL INDICATOR SYMBOL LETTER R}',
    'S' : '\N{REGIONAL INDICATOR SYMBOL LETTER S}',
    'T' : '\N{REGIONAL INDICATOR SYMBOL LETTER T}',
    'U' : '\N{REGIONAL INDICATOR SYMBOL LETTER U}',
    'V' : '\N{REGIONAL INDICATOR SYMBOL LETTER V}',
    'W' : '\N{REGIONAL INDICATOR SYMBOL LETTER W}',
    'X' : '\N{REGIONAL INDICATOR SYMBOL LETTER X}',
    'Y' : '\N{REGIONAL INDICATOR SYMBOL LETTER Y}',
    'Z' : '\N{REGIONAL INDICATOR SYMBOL LETTER Z}',
}

emojiLetterDict = {
    '\N{REGIONAL INDICATOR SYMBOL LETTER A}' : 'A',
    '\N{REGIONAL INDICATOR SYMBOL LETTER B}' : 'B',
    '\N{REGIONAL INDICATOR SYMBOL LETTER C}' : 'C',
    '\N{REGIONAL INDICATOR SYMBOL LETTER D}' : 'D',
    '\N{REGIONAL INDICATOR SYMBOL LETTER E}' : 'E',
    '\N{REGIONAL INDICATOR SYMBOL LETTER F}' : 'F',
    '\N{REGIONAL INDICATOR SYMBOL LETTER G}' : 'G',
    '\N{REGIONAL INDICATOR SYMBOL LETTER H}' : 'H',
    '\N{REGIONAL INDICATOR SYMBOL LETTER I}' : 'I',
    '\N{REGIONAL INDICATOR SYMBOL LETTER J}' : 'J',
    '\N{REGIONAL INDICATOR SYMBOL LETTER K}' : 'K',
    '\N{REGIONAL INDICATOR SYMBOL LETTER L}' : 'L',
    '\N{REGIONAL INDICATOR SYMBOL LETTER M}' : 'M',
    '\N{REGIONAL INDICATOR SYMBOL LETTER N}' : 'N',
    '\N{REGIONAL INDICATOR SYMBOL LETTER O}' : 'O',
    '\N{REGIONAL INDICATOR SYMBOL LETTER P}' : 'P',
    '\N{REGIONAL INDICATOR SYMBOL LETTER Q}' : 'Q',
    '\N{REGIONAL INDICATOR SYMBOL LETTER R}' : 'R',
    '\N{REGIONAL INDICATOR SYMBOL LETTER S}' : 'S',
    '\N{REGIONAL INDICATOR SYMBOL LETTER T}' : 'T',
    '\N{REGIONAL INDICATOR SYMBOL LETTER U}' : 'U',
    '\N{REGIONAL INDICATOR SYMBOL LETTER V}' : 'V',
    '\N{REGIONAL INDICATOR SYMBOL LETTER W}' : 'W',
    '\N{REGIONAL INDICATOR SYMBOL LETTER X}' : 'X',
    '\N{REGIONAL INDICATOR SYMBOL LETTER Y}' : 'Y',
    '\N{REGIONAL INDICATOR SYMBOL LETTER Z}' : 'Z'
}

file = open('auth.txt', 'r')
token = file.read()

client.run(token, bot=True)
