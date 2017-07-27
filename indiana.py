import calendar
from datetime import datetime as dt
from datetime import timedelta
import logging
import time
from time import sleep
import sys

import numpy as np
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
LOG = logging.getLogger("main")


def utcnow():
    return calendar.timegm(time.gmtime())

DEBUG = False                    # if True and "where" sent to the bot, replies with the real location
PARAMS = {'tolerance': 100.,     # Distance from the final goal 
          'attempts': 10.,       # How many guesses
          'distance_error': 25., # Reported distance is within this much of the real one
          }

def get_updates(token, offset=None):
    result = requests.get('https://api.telegram.org/bot%s/getUpdates' % token, json=({'offset': offset} if offset else {}))
    result.raise_for_status()
    return result.json()

def send_message(message, token, chat):
    result = requests.post('https://api.telegram.org/bot%s/sendMessage' % token, json={'chat_id': chat,
                                                                                       'text': message})
    return result


def send_location(location, token, chat):
    result = requests.post('https://api.telegram.org/bot%s/sendLocation' % token, json={'chat_id': chat,
                                                                                       'latitude': location[0],
                                                                                        'longitude': location[1]})
    return result


def convert_dms(d, m, s, negate=False):
    # Convert degree-minute-second coordinates into decimal
    return (-1 if negate else 1) * (d + m/60. + s/3600.)


def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    return 6367000. * c


class State(object):
    def __init__(self, token, chat):
        self.entry_time = utcnow()
        self.token = token
        self.chat = chat
        
    def process_message(self, message):
        pass
    
    def enter(self):
        pass
    
    def process_time(self):
        pass
    
    def send_message(self, message):
        send_message(message, self.token, self.chat)
        
    def send_location(self, location):
        send_location(location, self.token, self.chat)
    

class TreasureHunt(State):
    def __init__(self, token, chat, location, return_to):
        State.__init__(self, token, chat)
        self.location = location
        self.return_to = return_to
        self.attempts = PARAMS['attempts']
    
    def process_message(self, message):
        if 'text' in message and 'where' in message['text'] and DEBUG:
            self.send_message('here')
            self.send_location(self.location)
            return
            
        if 'location' in message:
            location = (message['location']['latitude'], message['location']['longitude'])
            distance = get_distance(location[0], location[1],
                                    self.location[0], self.location[1])
            
            if distance < PARAMS['tolerance']:
                self.send_message("Congratulations!")
                self.send_location(self.location)
                self.send_message("The actual treasure was here, but close enough.")
                return self.return_to
            else:
                reported_distance = np.random.uniform(low=distance - PARAMS['distance_error'],
                                                      high=distance + PARAMS['distance_error'])
                self.send_message("You are %.0f metres away." % reported_distance)
                self.attempts -= 1
                if self.attempts > 0:
                    self.send_message("You have %d attempt%s remaining." % (self.attempts, ('' if self.attempts == 1 else 's')))
                else:
                    self.send_message("You've lost!")
                    self.send_location(self.location)
                    self.send_message("The treasure was here the whole time!")
                    
    def enter(self):
        self.send_message("The treasure is buried somewhere around...")
        self.send_message("Send me your location and I'll tell you how far you are.")
        self.send_message("You have %d tries." % self.attempts)
        if PARAMS['distance_error'] > 0.:
            self.send_message("Also, the distance I give you will be within %d metres of the real distance." % PARAMS['distance_error'])
    
    def __repr__(self):
        return "<TreasureHunt(location=%r, attempts=%r)>" % (self.location, self.attempts)


class TreasureHuntIntro(State):

    def _get_random_coords(self):
        return (np.random.uniform(self.bounds[0], self.bounds[1]),
                np.random.uniform(self.bounds[2], self.bounds[3]))
    
    def _in_bounds(self, coords):
        return coords[0] >= self.bounds[0] and coords [0] <= self.bounds[1]\
               and coords[1] >= self.bounds[2] and coords[1] <= self.bounds[3]
    
    def _get_random_near_player(self, coords, sigma):
        while True:
            result = (coords[0] + np.random.randn() * sigma,
                      coords[1] + np.random.randn() * sigma)
            if self._in_bounds(result):
                return result
         
    def __init__(self, token, chat, bounds):
        State.__init__(self, token, chat)
        self.bounds = bounds
    
    def enter(self):
        self.send_message("Welcome to the treasure hunt!")
        self.send_message("Type 'hunt' to begin.")
        
    def process_message(self, message):
        if "text" in message and "hunt" in message['text']:
            self.send_message("OK")
            location = self._get_random_coords()
            return TreasureHunt(token, chat, location, self)
    
    def __repr__(self):
        return "<TreasureHuntIntro(bounds=%r)>" % (self.bounds,)


# Rough coordinates of the corners of Hyde Park (west edge bumped to avoid Kensington Palace)
PARK_RECTANGLE = convert_dms(51, 30, 11), convert_dms(51, 30, 35),\
                convert_dms(0, 11, 0, True), convert_dms(0, 9, 33, True)


if __name__ == '__main__':
    print sys.argv
    if len(sys.argv) != 3:
        LOG.error("Usage: indiana.py <bot token> <chat ID>")
        sys.exit(1)

    token, chat = sys.argv[1], sys.argv[2]
    
    start_state = TreasureHuntIntro(token, chat, PARK_RECTANGLE)
    start_time = utcnow()
    
    last_update_id = 0
    start_state.enter()
    current_state = start_state
    
    while True:
        sleep(5)
        updates = get_updates(token, offset=last_update_id)
        for update in updates['result']:
            if update['update_id'] <= last_update_id:
                continue
            
            last_update_id = update['update_id'] 
            if update['message']['date'] <= start_time:
                continue
            LOG.info("Received update %r" % update)
            new_state = current_state.process_message(update['message'])
            
            if new_state and new_state != current_state:
                LOG.info("New state %r" % new_state)
                current_state = new_state
                new_state.enter()
                
        new_state = current_state.process_time()
        if new_state and new_state != current_state:
            LOG.info("New state %r" % new_state)
            current_state = new_state
            new_state.enter()
