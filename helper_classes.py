import asyncio
import json
import os
from http_requests import HTTPRequests

class BumpManager:
    def __init__(self):
        self.bump_messages = {}
        self.http_requests = HTTPRequests()
        self.load_bumps()

    def load_bumps(self):
        if os.path.exists('bumps.json'):
            with open('bumps.json', 'r') as f:
                self.bump_messages = json.load(f)

    def save_bumps(self):
        with open('bumps.json', 'w') as f:
            json.dump(self.bump_messages, f)

    def add_bump_message(self, id, channel_id, message, delay):
        if id in self.bump_messages:
            return False
        self.bump_messages[id] = {
            'channel_id': channel_id,
            'message': message,
            'delay': delay,
            'active': False,
            'task': None,
        }
        self.save_bumps()
        return True
    
    def delete_bump_message(self, id):
        if id not in self.bump_messages:
            return False
        else:
            if self.bump_messages[id]['active']:
                self.stop_bump(id)

            del self.bump_messages[id]

            self.save_bumps()

            return True

    def start_bump(self, id):
        bump_message = self.bump_messages.get(id)
        if bump_message:
            if not bump_message['active']:
                bump_message['active'] = True
                bump_message['task'] = asyncio.create_task(self.bump_message(bump_message))
            return True
        return False

    def stop_bump(self, id):
        bump_message = self.bump_messages.get(id)
        if bump_message:
            if bump_message['active']:
                bump_message['task'].cancel()
                bump_message['active'] = False
            return True
        return False

    async def bump_message(self, bump_message):
        while bump_message['active']:
            await self.http_requests.send_message(bump_message['channel_id'], bump_message['message'])
            await asyncio.sleep(bump_message['delay'])



class SpyManager:
    def __init__(self):
        self.load_spies()

    def load_spies(self):
        try:
            with open('spy.json', 'r') as f:
                self.spies = json.load(f)
        except FileNotFoundError:
            self.spies = {}

    def save_spies(self):
        with open('spy.json', 'w') as f:
            json.dump(self.spies, f)

    def add_spy(self, user_id):
        if user_id not in self.spies:
            self.spies[user_id] = True
            self.save_spies()
            return True
        else:
            return False

    def remove_spy(self, user_id):
        if user_id in self.spies:
            del self.spies[user_id]
            self.save_spies()
            return True
        else:
            return False

    def list_spies(self):
        return self.spies.keys()