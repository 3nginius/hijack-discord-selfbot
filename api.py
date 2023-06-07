import asyncio
import threading
import json
from websocket_connection import WebSocketConnection
from http_requests import HTTPRequests
from window_functions import WindowFunctions
import globals

class Api(WebSocketConnection, HTTPRequests, WindowFunctions):
    def __init__(self):
        self.window = None
        WebSocketConnection.__init__(self)
        HTTPRequests.__init__(self)
        WindowFunctions.__init__(self)
        
        self.settings = {
            'prefix': ".",
            'show_server_messages': True,
            'show_dm_messages': True,
            'show_updated_messages': True,
            'show_deleted_messages': True,
            'show_bot_messages': True,
            'token_inf' : ""
        }

        self.webhook_settings = {
            'webhook_url': "NULL",
            'on_connect': False,
            'on_updated_message': False,
            'on_deleted_message': False
        }

        self.load_settings()
        self.load_webhook_settings()


    def set_window(self, window):
        self.window = window
        WindowFunctions.set_window(self, window)


    def updatePrefix(self, prefix):
        self.settings['prefix'] = prefix
        self.save_settings()


    def updateConsoleOption(self, showServerMessages, showDMMessages, showUpdatedMessages, showDeletedMessages, showBotMessages):
        self.settings['show_server_messages'] = showServerMessages
        self.settings['show_dm_messages'] = showDMMessages
        self.settings['show_updated_messages'] = showUpdatedMessages
        self.settings['show_deleted_messages'] = showDeletedMessages
        self.settings['show_bot_messages'] = showBotMessages
        self.save_settings()
        

    def updateTokenInfo(self, tokenInformation):
        self.settings['token_inf'] = tokenInformation
        self.save_settings()


    def updateWebhook(self, webhookURL, onConnect, onUpdate, onDelete):
        self.webhook_settings['webhook_url'] = webhookURL
        self.webhook_settings['on_connect'] = onConnect
        self.webhook_settings['on_updated_message'] = onUpdate
        self.webhook_settings['on_deleted_message'] = onDelete
        
        self.save_webhook_settings()
        

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                data = json.load(f)
                self.settings['prefix'] = data.get('prefix', '.')
                self.settings['show_server_messages'] = data.get('show_server_messages', True)
                self.settings['show_dm_messages'] = data.get('show_dm_messages', True)
                self.settings['show_updated_messages'] = data.get('show_updated_messages', True)
                self.settings['show_deleted_messages'] = data.get('show_deleted_messages', True)
                self.settings['show_bot_messages'] = data.get('show_bot_messages', True)
                self.settings['token_inf'] = data.get('token_inf', '')
        except FileNotFoundError:
            pass


    def load_webhook_settings(self):
        try:
            with open('webhook_settings.json', 'r') as f:
                data = json.load(f)
                self.webhook_settings['webhook_url'] = data.get('webhook_url', 'NULL')
                self.webhook_settings['on_connect'] = data.get('on_connect', False)
                self.webhook_settings['on_updated_message'] = data.get('on_updated_message', False)
                self.webhook_settings['on_deleted_message'] = data.get('on_deleted_message', False)
        except FileNotFoundError:
            pass


    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)


    def save_webhook_settings(self):
        with open('webhook_settings.json', 'w') as f:
            json.dump(self.webhook_settings, f)


    def get_settings(self):
        return self.settings
    

    def get_relationships(self):
        self.get_user_relationships(globals.global_token)
        return {
            "relationship_counts": globals.relationship_counts,
            "detailed_relationships": globals.detailed_relationships
        }
    

    def deleteRelationship(self, user_id):
        self.delete_relationship(globals.global_token, user_id)


    def get_webhook_settings(self):
        return self.webhook_settings


    def startBot(self, token):
        name = self.get_bot_name(token)
        globals.global_token = token
        if name is not None and self.window is not None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            websocket_thread = threading.Thread(target=loop.run_until_complete, args=(self.connect(token, self.window),))
            websocket_thread.start()
            return name
        else:
            return "Error: Invalid token"

