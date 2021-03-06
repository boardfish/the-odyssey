#!/usr/bin/env python
import logging
from flask import Flask, request 
from flask_restful import Resource, Api
from flask_ask import Ask, statement, question, session, audio
from sqlalchemy import create_engine
from json import dumps
from flask.ext.jsonpify import jsonify
from random import randint 
import os
#https://stackoverflow.com/questions/3728655/titlecasing-a-string-with-exceptions
import re 
# Title case function to fix kingdom names for queries
def title(s):
    word_list = re.split(' ', s)       # re.split behaves as expected
    final = [word_list[0].capitalize()]
    for word in word_list[1:]:
        final.append(word.capitalize())
    return " ".join(final)

# Connect DB
db_connect = create_engine('sqlite:///moons.db')
# Initialise Flask app
app = Flask(__name__, static_url_path='')
# Initialise Alexa endpoint
ask = Ask(app, "/")
logging.getLogger("flask_ask").setLevel(logging.DEBUG)
# Initialise API stuff
api = Api(app)

# Helper: choose a sound based on the moon_type
def choose_sfx(x):
    return {
            1: "https://young-sierra-60676.herokuapp.com/moonget",
            2: "https://young-sierra-60676.herokuapp.com/bigmoonget",
            3: "https://young-sierra-60676.herokuapp.com/multimoonget",
            4: "https://young-sierra-60676.herokuapp.com/starget",
            5: "https://young-sierra-60676.herokuapp.com/8bitmoonget",
            }.get(x, "https://young-sierra-60676.herokuapp.com/moonget")

# Helper: map kingdom aliases to their kingdoms. Alexa always provides these in
#         lower case
def kingdom_names(query):
    return {
            'culmina crater': 'Darker Side',
            'rabbit ridge': 'Dark Side',
            'honeylune ridge': 'Moon',
            'bowser\'s castle': 'Bowser\'s',
            'volbono': 'Luncheon',
            'tostarena': 'Sand',
            'bonneton': 'Cap',
            'fossil falls': 'Cascade',
            'nimbus arena': 'Cloud',
            'crumbleden': 'Ruined',
            'lake lamode': 'Lake',
            'bubblaine': 'Seaside',
            'shiveria': 'Snow',
            'peach\'s castle': 'Mushroom'
            }[query]

# Search for a random moon in a given kingdom based on the provided statement
def search_moon(query):
    print(query)
    conn = db_connect.connect()
    # count = conn.execute("select Count(*) from moons").fetchone()[0]
    # moon_id = randint(1,count)
    queryex = conn.execute("select * from moons where kingdom=\"%s\" ORDER BY RANDOM() LIMIT 1 "  %title(str(query)))
    result = queryex.fetchone()
    if result is not None:
        return gen_moon(result)
    else:
        return False

# Give a random moon from the entire game
def random_moon():
    conn = db_connect.connect()
    count = conn.execute("select Count(*) from moons").fetchone()[0]
    moon_id = randint(1,count)
    query = conn.execute("select * from moons where id =%d "  %int(moon_id))
    result = query.fetchone()
    return gen_moon(result)

# Parse out moon data and generate text template
def gen_moon(record):
    sfx = choose_sfx(record['moon_type'])
    location = record['kingdom']
    postgame = record['is_postgame'] == "True"
    template = "Let's find a moon! " + record['name'] + ". Try searching for this moon in the " + location + " Kingdom" + (" after you've beaten the game.", ".")[postgame]
    return [template, sfx, location, postgame]

# Get random moon - Alexa says it and plays fanfare. Card also shown.
@ask.launch
def launch_moon():
    moon = random_moon()
    return audio(moon[0]).play(moon[1]).simple_card(title='Let\'s Find A Moon!', content=moon[0]+'\nThis'+('',' post-game ')[moon[3]]+ 'moon can be found in the '+moon[2]+' Kingdom.')

# Same as above - don't know if I can decorate twice.
@ask.intent('MoonIntent')
def intent_moon():
    moon = random_moon()
    return audio(moon[0]).play(moon[1]).simple_card(title='Let\'s Find A Moon!', content=moon[0]+'\nThis moon can be found in the '+moon[2]+' Kingdom.')

@ask.intent('KingdomMoonIntent', mapping={'kingdom': 'Kingdom'}, default={'kingdom':'Cap'})
def intent_search_moon(kingdom):
    moon = search_moon(kingdom)
    if not moon:
        moon = search_moon(kingdom_names(kingdom))
        if not moon:
            return audio("I couldn't find anything. Check your Alexa app to see if I got that right.")
    return audio(moon[0]).play(moon[1]).simple_card(title='Let\'s Find A Moon in the {} Kingdom!'.format(title(moon[2])), content=moon[0])


@ask.intent('AMAZON.PauseIntent')
def pause():
    return audio('Paused the stream.').stop()


@ask.intent('AMAZON.ResumeIntent')
def resume():
    return audio('Resuming.').resume()

@ask.intent('AMAZON.StopIntent')
def stop():
return audio('stopping').clear_queue(stop=True)

class Moons(Resource):
    def get(self):
        conn = db_connect.connect()
        query = conn.execute("select id, name, kingdom from moons;")
        result = {'data': [dict(zip(tuple (query.keys()) ,i)) for i in query.cursor]}
        return jsonify(result)

class RandomMoon(Resource):
    def get(self):
        conn = db_connect.connect()
        count = conn.execute("select Count(*) from moons").fetchone()[0]
        moon_id = randint(1,count)
        query = conn.execute("select * from moons where id =%d "  %int(moon_id))
        result = {'data': [dict(zip(tuple (query.keys()) ,i)) for i in query.cursor]}
        return jsonify(result)
        
@app.route('/moonget')
def moonget():
    return app.send_static_file('moonget.mp3')

@app.route('/bigmoonget')
def bigmoonget():
    return app.send_static_file('bigmoonget.mp3')

@app.route('/multimoonget')
def multimoonget():
    return app.send_static_file('multimoonget.mp3')

@app.route('/starget')
def starget():
    return app.send_static_file('starget.mp3')

@app.route('/8bitmoonget')
def ebitmoonget():
    return app.send_static_file('8bitmoonget.mp3')

@app.route('/map')
def map():
    return app.send_static_file('map.jpg')

@app.route('/')
def render_static():
    return app.send_static_file('index.html')


api.add_resource(Moons, '/all') # Route_1
api.add_resource(RandomMoon, '/random') # Route_2

# Init Flask etc.
if __name__ == '__main__':
    app.run(port=os.getenv('PORT', '5000'), host='0.0.0.0')
    # Init Discord bot
