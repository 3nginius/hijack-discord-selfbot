import json
import asyncio
import websockets
import time
from datetime import datetime
import os
import logging
import globals
from message_cache import MessageCache, ReactionCache
from http_requests import HTTPRequests
from chat_commands import ChatCommands
from helper_classes import SpyManager

class WebSocketConnection:

    def __init__(self):
        self.ws = None
        self.message_cache = MessageCache()
        self.reaction_cache = ReactionCache()
        self.http_requests = HTTPRequests()
        self.spy_manager = SpyManager()
        self.chat_commands = ChatCommands(self.message_cache)
        self.webhook_settings = {}
        self.load_webhook_settings()


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


    def send_deleted_message_webhook(self, author, content):
        if self.webhook_settings['on_deleted_message']:
            embed = {
                "title": "Deleted Message",
                "description": f"[{author}]: {content}",
                "color": 65280,
                "footer": {
                    "text": "Delete detected at",
                    "icon_url": "https://i.imgur.com/AfFp7pu.png"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            self.http_requests.send_webhook_message(self.webhook_settings['webhook_url'], embeds=[embed])


    def send_updated_message_webhook(self, author, old_content, new_content):
        if self.webhook_settings['on_updated_message']:
            embed = {
                "title": "Updated Message",
                "description": f"[{author}]: {old_content} -> {new_content}",
                "color": 65280,
                "footer": {
                    "text": "Update detected at",
                    "icon_url": "https://i.imgur.com/AfFp7pu.png"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            self.http_requests.send_webhook_message(self.webhook_settings['webhook_url'], embeds=[embed])


    def check_token_validity(self, token):
        response = self.http_requests.get_bot_name(token)
        if 'error' in response:
            print(f"Token validation failed: {response['error']}")
            return False
        else:
            print(f"Token validated for user {response['username']}")
            if self.webhook_settings['on_connect'] and self.webhook_settings['webhook_url'] != "NULL":
                embed = {
                    "title": "Connection Notification",
                    "description": "Hijack Self-Bot has connected.",
                    "color": 65280,
                    "footer": {
                        "text": "Connection established at",
                        "icon_url": "https://i.imgur.com/AfFp7pu.png"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.http_requests.send_webhook_message(self.webhook_settings['webhook_url'], embeds=[embed])
            return True
    

    def make_console_message(self, window, message_type, timestamp, message_link, user, content, url_string, spy=False):
        message = f'<span class="{message_type}">[{message_type.upper()}] </span>[{timestamp}] '

        user_span = ""
        if user:
            if message_link:
                user_span = f'<a href="{message_link}" target="_blank"><span class="spy">[SPY] [{user}]</span></a>' if spy else f'<a href="{message_link}" target="_blank">[{user}]</a>'
            else:
                user_span = f'<span class="spy">[SPY] [{user}]</span>' if spy else f'[{user}]'

            message += f'{user_span}: '

        message += f'{content} {url_string}'

        console_message = message.replace('`', '\\`')
        window.evaluate_js(f'printToConsole(`{console_message}`);')
        logging.info('<div class="message">' + console_message + '</div>' + "<br>")






    async def connect(self, token, window):

        if not self.check_token_validity(globals.global_token):
            console_message_e = f'<span class="error">[E] </span>[{time.strftime("%H:%M:%S")}][Websocket]: Invalid token, stopping connection attempts....'
            window.evaluate_js('printToConsole(`' + console_message_e.replace('`', '\\`') + '`);')
            return
        
        if not os.path.exists('console'):
            os.makedirs('console')

        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')

        logging.basicConfig(filename=f'console/session_{timestamp}.html', level=logging.INFO, format='%(message)s')

        logging.info("""
        <html>
        <head>
        <style>
            body {
                background-color: #1F1F1F;
                color: #c5c8c6;
                font-family: 'Source Code Pro', monospace;
            }

            .message {
                border-bottom: 1px solid #c5c8c6;
                padding: 10px;
            }

            .success {
                color: #b5bd68;
            }

            .error {
                color: #cc6666;
            }

            .notifications {
                color: #81a2be;
            }

            .server {
                color: #b294bb;
            }

            .dm {
                color: #8abeb7;
            }

            .updated {
                color: #de935f;
            }

            .deleted {
                color: #a3685a;
            }

            a {
                text-decoration: none; /* Removes underline */
                color: rgb(231, 200, 200); /* Sets text color */
            }

            a:hover, a:visited, a:active {
                color: rgb(255, 255, 255); /* Keeps text color the same on hover, after being clicked, and after being visited */
            }
        </style>
        </head>
        <body>
        """)

        auth = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "Windows 11",
                    "$browser": "Google Chrome",
                    "$device": "Windows"
                }
            },
            "s": None,
            "t": None,
        }

        url = "wss://gateway.discord.gg/?v=9&encoding=json"
        
        MAX_RECONNECT_TIME = 60
        base_delay = 2
        retry_delay = base_delay

        while True:
            try:
                async with websockets.connect(url, max_size=10**7) as ws:
                    self.ws = ws
                    await ws.send(json.dumps(auth))

                    hello_message = json.loads(await ws.recv())
                    heartbeat_interval = hello_message['d']['heartbeat_interval'] / 1000.0

                    heartbeat_task = asyncio.create_task(self.send_heartbeat(ws, heartbeat_interval))

                    console_message_n = 'Starting to process messages...'
                    self.make_console_message(window, "notifications", time.strftime("%H:%M:%S"), "Websocket", "", console_message_n, "")
                    await self.process_messages(ws, window)
                    retry_delay = base_delay

                    console_message_e = 'Connection closing, cancelling heartbeat task...'
                    self.make_console_message(window, "error", time.strftime("%H:%M:%S"), "Websocket", "", console_message_e, "")
                    heartbeat_task.cancel()

            except Exception as e:
                console_message_e = f'Exception: {e}...'
                self.make_console_message(window, "error", time.strftime("%H:%M:%S"), "Exception", "", console_message_e, "")
            
            console_message_n = f"Connection failed. Retrying in {retry_delay} seconds..."
            self.make_console_message(window, "notifications", time.strftime("%H:%M:%S"), "Websocket", "", console_message_n, "")
            
            await asyncio.sleep(retry_delay)

            retry_delay *= 2
            retry_delay = min(retry_delay, MAX_RECONNECT_TIME)


    async def send_heartbeat(self, ws, interval):
        while True:
            await ws.send('{"op": 1, "d": null}')
            await asyncio.sleep(interval)


    def get_author_info(self, data):
        author_info = data.get('author')
        if author_info is not None:
            return f"{author_info.get('username', 'Unknown')}#{author_info.get('discriminator', '0000')}"
        else:
            return 'Unknown'
        

    async def process_messages(self, ws, window):
        console_message_n = 'Listening Messages...'
        self.make_console_message(window, "success", time.strftime("%H:%M:%S"), "Websocket", "", console_message_n, "")

        handlers = {
            'MESSAGE_CREATE': self.handle_message_create,
            'MESSAGE_UPDATE': self.handle_message_update,
            'MESSAGE_DELETE': self.handle_message_delete,
            'RELATIONSHIP_ADD': self.handle_relationship_add,
            'RELATIONSHIP_REMOVE': self.handle_relationship_remove,
            'VOICE_STATE_UPDATE': self.handle_voice_state_update,
            'MESSAGE_REACTION_ADD': self.handle_message_reaction_add,
            'MESSAGE_REACTION_REMOVE': self.handle_message_reaction_remove,
            'TYPING_START': self.handle_typing_start
        }
    
        try:
            async for message in ws:
                timestamp_value = time.strftime("%H:%M:%S")
                data = json.loads(message)
                #print(data)
                handler = handlers.get(data['t'])

                if handler:
                    handler(window, timestamp_value, data)

                else:
                    pass
                    
        except Exception as e:
            console_message_n = f'Exception: {e}.'
            self.make_console_message(window, "error", time.strftime("%H:%M:%S"), "Exception", "", console_message_n, "")


    def handle_message_create(self, window, timestamp_value, data):
        if data['d'] is not None and 'author' in data['d'] and data['d']['author'] is not None:
            bot_check = data['d']['author']
            if 'bot' in bot_check and bot_check['bot'] and self.settings['show_bot_messages'] is False:
                return

        content = data['d']['content']
        message_id = data['d']['id']
        channel_id = data['d']['channel_id']
        guild_id = data['d'].get('guild_id', '@me') 
        message_link = f'discord://discord.com/channels/{guild_id}/{channel_id}/{message_id}'
        url_string = ''

        show_server_messages = self.settings['show_server_messages']
        show_dm_messages = self.settings['show_dm_messages']
        user_prefix = self.settings['prefix']

        if 'attachments' in data['d']:
            for attachment in data['d']['attachments']:
                url_string += '\n' + attachment['url']

        user_id = data['d']['author']['id']
        is_spy = user_id in self.spy_manager.list_spies() if user_id else False

        if 'id' in globals.user_data and user_id == globals.user_data['id'] and data['d']['content'].startswith(user_prefix):
            command = content[len(user_prefix):].strip()
            asyncio.create_task(self.chat_commands.execute_command(window, command, channel_id, message_id))

            console_message_n = f'<span class="notifications">[Notification] </span>[{timestamp_value}]<a href="{message_link}" target="_blank">[Command]:</a> {content} {url_string}'
            window.evaluate_js('printToConsole(`' + console_message_n.replace('`', '\\`') + '`);')
            logging.info('<div class="message">' + console_message_n + '</div>' + "<br>")

        else:
            if 'guild_id' in data['d'] and show_server_messages:
                user = self.get_author_info(data['d'])
                self.make_console_message(window, "server", timestamp_value, message_link, user, content, url_string, spy=is_spy)

            if 'guild_id' not in data['d'] and show_dm_messages:
                user = self.get_author_info(data['d'])
                self.make_console_message(window, "dm", timestamp_value, message_link, user, content, url_string, spy=is_spy)

        self.message_cache.add(data['d'])



    def handle_message_update(self, window, timestamp_value, data):
        new_message = data['d']

        if new_message.get('embeds', []):
            return

        old_message = self.message_cache.get(data['d']['id'])

        show_bot_messages = self.settings['show_bot_messages']
        if new_message.get('author', {}).get('bot', False) and not show_bot_messages:
            return

        self.message_cache.update(new_message)

        message_id = data['d']['id']
        channel_id = data['d']['channel_id']
        guild_id = data['d'].get('guild_id', '@me') 
        message_link = f'discord://discord.com/channels/{guild_id}/{channel_id}/{message_id}'

        author_info = new_message.get('author')

        user_id = author_info.get('id') if author_info else None
        is_spy = user_id in self.spy_manager.list_spies() if user_id else False

        if author_info is not None:
            author = self.get_author_info(new_message)
        else:
            author = 'Unknown'

        old_content = old_message.get('content', 'Old message content not available') if old_message is not None else 'Old message content not available'
        new_content = new_message.get('content', 'New message content not available')

        console_message = f'"{old_content}" ---> "{new_content}"'

        if self.webhook_settings['on_updated_message']:
            self.send_updated_message_webhook(author, old_content, new_content)

        self.make_console_message(window, "updated", timestamp_value, message_link, author, console_message, "", is_spy)
        self.message_cache.update(new_message)



    def handle_message_delete(self, window, timestamp_value, data):
        message_id = data['d']['id']

        # Get the deleted message from the cache
        deleted_message = self.message_cache.get(message_id)

        # If deleted message exists in cache, remove it
        if deleted_message is not None:

            # Try to get author info
            author_info = deleted_message.get('author')

            # If author info is None, return and do nothing
            if author_info is None:
                return

            # Exclude bot messages
            show_bot_messages = self.settings['show_bot_messages']
            if deleted_message.get('author', {}).get('bot', False) and not show_bot_messages:
                return

            # Remove the message from the cache and add it to the deleted messages cache
            self.message_cache.delete(message_id)

            show_deleted_messages = self.settings['show_deleted_messages']
            if show_deleted_messages:

                # If author info exists, get username and discriminator
                author = self.get_author_info(deleted_message)

                # Check if user is a spy
                user_id = author_info.get('id')
                is_spy = user_id in self.spy_manager.list_spies() if user_id else False

                # Get the content of the deleted message
                content = deleted_message.get('content', 'Message content not available')

                # Initialize url_string to an empty string
                url_string = ''

                # Find all image attachments and add them to the url_string
                if 'attachments' in deleted_message:
                    for attachment in deleted_message['attachments']:
                        url_string += '\n' + attachment['url']

                # Print the content of the deleted message and any deleted attachments to the console
                console_message = f'"{content}{url_string}" was deleted.'
                self.make_console_message(window, "deleted", timestamp_value, "", author, console_message, "", is_spy)
                self.send_deleted_message_webhook(author, content + url_string)



    def handle_relationship_add(self, window, timestamp_value, data):
        user_id = data['d']['id']
        type = data['d']['type']

        relationship_type_messages = {
            1: 'Added a new friend',
            2: 'Blocked a user',
            3: 'Received a friend request',
            4: 'Sent a friend request',
            5: 'Friend request pending',
        }

        message = relationship_type_messages.get(type, 'Changed relationship status')
        console_message_n = f'{message} with user ID: {user_id}.'
        self.make_console_message(window, "relationship", timestamp_value, "", "", console_message_n, "")


    def handle_relationship_remove(self, window, timestamp_value, data):
        user_id = data['d']['id']
        type = data['d']['type']

        relationship_type_messages = {
            1: 'Removed a friend',
            2: 'Unblocked a user',
            3: 'Rejected a friend request',
            4: 'Canceled a friend request',
            5: 'Friend request no longer pending',
        }

        message = relationship_type_messages.get(type, 'Changed relationship status')
        console_message_n = f'{message} with user ID: {user_id}.'
        self.make_console_message(window, "relationship", timestamp_value, "", "", console_message_n, "")


    def handle_voice_state_update(self, window, timestamp_value, data):
        user_id = data['d']['user_id']

        # Check if user is a spy
        if user_id not in self.spy_manager.list_spies():
            return

        user_info = self.http_requests.get_user_info(user_id)
        if 'error' not in user_info:
            username = user_info['username']
            discriminator = user_info['discriminator']
            user = f"{username}#{discriminator}"
            console_message_n = f'updated their voice state.'
            self.make_console_message(window, "voice", timestamp_value, "", user, console_message_n, "", spy=True)


    def handle_message_reaction_add(self, window, timestamp_value, data):
        user_id = data['d']['user_id']

        # Check if user is a spy
        if user_id not in self.spy_manager.list_spies():
            return

        user_info = self.http_requests.get_user_info(user_id)
        if 'error' not in user_info:
            username = user_info['username']
            discriminator = user_info['discriminator']
            user = f"{username}#{discriminator}"
            emoji = data['d']['emoji']['name']  # Extract name from emoji dict
            channel_id = data['d']['channel_id']
            message_id = data['d']['message_id']
            guild_id = data['d'].get('guild_id', '@me')  # Use @me for DMs
            message_link = f'discord://discord.com/channels/{guild_id}/{channel_id}/{message_id}'
            console_message_n = f'added a reaction: {emoji}.'
            self.make_console_message(window, "reaction", timestamp_value, message_link, user, console_message_n, "", spy=True)


    def handle_message_reaction_remove(self, window, timestamp_value, data):
        user_id = data['d']['user_id']

        # Check if user is a spy
        if user_id not in self.spy_manager.list_spies():
            return

        user_info = self.http_requests.get_user_info(user_id)
        if 'error' not in user_info:
            username = user_info['username']
            discriminator = user_info['discriminator']
            user = f"{username}#{discriminator}"
            emoji = data['d']['emoji']['name']  # Extract name from emoji dict
            channel_id = data['d']['channel_id']
            message_id = data['d']['message_id']
            guild_id = data['d'].get('guild_id', '@me')  # Use @me for DMs
            message_link = f'discord://discord.com/channels/{guild_id}/{channel_id}/{message_id}'
            console_message_n = f'removed a reaction: {emoji}.'
            self.make_console_message(window, "reaction", timestamp_value, message_link, user, console_message_n, "", spy=True)


    def handle_typing_start(self, window, timestamp_value, data):
        user_id = data['d']['user_id']

        if user_id not in self.spy_manager.list_spies():
            return

        user_info = self.http_requests.get_user_info(user_id)
        if 'error' not in user_info:
            username = user_info['username']
            discriminator = user_info['discriminator']
            user = f"{username}#{discriminator}"
            console_message_n = f'is typing.'
            self.make_console_message(window, "typing", timestamp_value, "", user, console_message_n, "", spy=True)



    def update_status(self, status, game=None, afk=False, since=0):
        def run_coroutine_and_return_result():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._update_status(status, game, afk, since))
            loop.close()
            return result

        return run_coroutine_and_return_result()


    async def _update_status(self, status, game=None, afk=False, since=0):
        try:
            game_object = None
            if game:
                game_object = {
                    "name": game['name'],
                    "type": game['type'], 
                }
            status_update = {
                "op": 3,
                "d": {
                    "since": since,
                    "status": status,
                    "afk": afk,
                    "game": game_object
                }
            }
            await self.ws.send(json.dumps(status_update))
        except Exception as e:
            console_message_n = f'<span class="error">[E] </span>[{time.strftime("%H:%M:%S")}][Exception]: {e}.'
            logging.info('<div class="message">' + console_message_n + '</div>' + "<br>")

