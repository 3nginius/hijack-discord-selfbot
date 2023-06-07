import asyncio
from http_requests import HTTPRequests
from helper_classes import BumpManager, SpyManager
import time
import requests
import json
import difflib
import globals
import shlex
import os
import sys
import praw
import random
from datetime import datetime
from functools import wraps


def register_commands(cls):
    cls.commands = {}
    for attr_name, attr_value in cls.__dict__.items():
        if hasattr(attr_value, "_command_info"):
            cmd_name, func, min_args, max_args, category, description, usage = attr_value._command_info
            cls.commands[cmd_name] = (func, min_args, max_args, category, description, usage)
    return cls

class ChatCommands:
    def __init__(self, message_cache):
        self.window = None
        self.http_requests = HTTPRequests()
        self.bump_manager = BumpManager()
        self.spy_manager = SpyManager()
        self.message_cache = message_cache

    @staticmethod
    def bot_command(name, min_args=0, max_args=None, category='Uncategorized', description='', usage=''):
        def decorator(func):
            func._command_info = (name, func, min_args, max_args, category, description, usage)
            return func
        return decorator

    async def execute_command(self, window, command, channel_id, message_id, *args, **kwargs):
        parts = shlex.split(command)
        command_name = parts[0]
        command_args = parts[1:]
        try:
            if command_name in self.commands:
                func, min_args, max_args, category, description, usage = self.commands[command_name]
                if min_args <= len(command_args) and (max_args is None or len(command_args) <= max_args):
                    await func(self, window, channel_id, message_id, *command_args, **kwargs)
                    console_message_n = f'<span class="notifications">[Notification] </span>[{time.strftime("%H:%M:%S")}][Command]: {command_name} executed.'
                    window.evaluate_js('printToConsole(`' + console_message_n.replace('`', '\\`') + '`);')
                else:
                    if max_args == 0 and len(command_args) > 0:
                        await self.send_error_message(channel_id, f"Command '**{command_name}**' doesn't take any arguments.", message_id, **kwargs)
                    else:
                        await self.send_error_message(channel_id, f"Command '**{command_name}**' requires between {min_args} and {max_args} arguments.", message_id, **kwargs)
            else:
                close_matches = difflib.get_close_matches(command_name, self.commands.keys(), n=1, cutoff=0.5)
                if close_matches:
                    await self.send_error_message(channel_id, f"Unknown command '{command_name}'. Did you mean '**{close_matches[0]}**'?", message_id, **kwargs)
                else:
                    await self.send_error_message(channel_id, f"Unknown command '{command_name}'", message_id, **kwargs)
        except Exception as ex:
            print("error while executing: "+str(ex))

    ##############
    ## Commands ##
    ##############

    #Help Command
    @bot_command('help', min_args=0, max_args=1, category='General', description='Shows all commands with their descriptions or shows help for a specific command.', usage='help <command>')
    async def help_command(self, window, channel_id, message_id, *args, **kwargs):
        if len(args) > 0:
            # If an argument was provided, give help for that specific command
            specific_command = args[0]
            if specific_command in self.commands:
                _, _, _, _, description, usage = self.commands[specific_command]
                await self.send_specific_success_message(channel_id, "Commands", f"{specific_command}: {description}\n> Usage: {usage}", message_id, **kwargs)
            else:
                # Find similar command names
                close_matches = difflib.get_close_matches(specific_command, self.commands.keys(), n=1, cutoff=0.6)
                if close_matches:
                    await self.send_error_message(channel_id, f"Unknown command '{specific_command}'. Did you mean '{close_matches[0]}'?", message_id, **kwargs)
                else:
                    await self.send_error_message(channel_id, f"Unknown command '{specific_command}'", message_id, **kwargs)
        else:
            # If no specific command was provided, send all commands
            categories = {}
            for cmd_name, cmd_info in self.commands.items():
                _, _, _, category, description, _ = cmd_info
                if category not in categories:
                    categories[category] = []
                categories[category].append((cmd_name, description))

            message = ''
            for category, cmds in categories.items():
                message += f'> ### {category} ###\n'
                for cmd_name, description in cmds:
                    message += f'> - {cmd_name}: {description}\n'
            await self.send_success_message(channel_id, message, message_id, **kwargs)


    #Edit Command
    @bot_command('edit', min_args=1, max_args=1, category='Fun', description='Edits the last message.', usage='edit <"message">')
    async def edit_message(self, window, channel_id, message_id, args, **kwargs):
        message = ' '.join(args)
        edited_message = "[Edited] " + message
        await self.http_requests.edit_last_message(channel_id, message_id, edited_message, **kwargs)


    #Send slash test
    #@bot_command('sendslash', min_args=4, max_args=4, category='Fun', description='Sends a slash command.', usage='sendslash <bot_id> <channel_id> <guild_id> <slash_command>')
    #async def sendslash(self, window, channel_id, message_id, *args, **kwargs):
        #bot_id = args[0]
        #channel_id = args[1]
        #guild_id = args[2]
        #slash_command = args[3]
        #await self.http_requests.send_slash_command(bot_id, channel_id, guild_id, slash_command, **kwargs)
    

    #User info Command
    @bot_command('info', min_args=1, max_args=1, category='Utility', description='Gets information about a user.', usage='info <user_id>')
    async def user_info(self, window, channel_id, message_id, args, **kwargs):
        user_id = self.handle_user_mention(args)
        user_info = self.http_requests.get_user_info(user_id)
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        
        if 'error' in user_info:
            # Handle the error
            await self.send_error_message(channel_id, f"User '{args}' not found.", message_id, **kwargs)
        else:
            # Format the user info nicely
            header = "> ## User Information ##"
            footer = "```md\n> # Ngin#3612 #```"

            user_info_str = f"{header}\n"
            user_info_str += f"> User ID: {user_info['id']}\n"
            user_info_str += f"> Username: {user_info['username']}#{user_info['discriminator']}\n"
            user_info_str += f"> Account Created: {self.get_creation_date(user_info['id'])}\n"
            user_info_str += f"> Public Flags: {user_info['public_flags']}\n"
            user_info_str += f"> Flags: {user_info['flags']}\n"

            if user_info['avatar']:
                user_info_str += f"> Avatar: {user_info['avatar']}\n"
            if user_info['banner']:
                user_info_str += f"> Banner: {user_info['banner']}\n"
            if user_info['accent_color']:
                user_info_str += f"> Accent Color: {user_info['accent_color']}\n"
            if user_info['global_name']:
                user_info_str += f"> Global Name: {user_info['global_name']}\n"
            if user_info['avatar_decoration']:
                user_info_str += f"> Avatar Decoration: {user_info['avatar_decoration']}\n"
            if user_info['display_name']:
                user_info_str += f"> Display Name: {user_info['display_name']}\n"
            if user_info['banner_color']:
                user_info_str += f"> Banner Color: {user_info['banner_color']}\n"

            user_info_str += footer

            await self.http_requests.send_message(channel_id, user_info_str, **kwargs)

    
    #User Avatar Command
    @bot_command('avatar', min_args=1, max_args=1, category='Utility', description='Returns user\'s avatar, banner decoration.', usage='avatar <user_id>')
    async def user_avatar(self, window, channel_id, message_id, args, **kwargs):
        user_id = self.handle_user_mention(args)
        user_info = self.http_requests.get_user_info(user_id)
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        
        if 'error' in user_info:
            # Handle the error
            await self.send_error_message(channel_id, f"User '{args}' not found.", message_id, **kwargs)
        else:
            # Format the user info nicely
            header = "> ## User Avatar ##"
            footer = "```md\n> # Ngin#3612 #```"

            user_info_str = f"{header}\n"
            user_info_str += f"> User ID: {user_info['id']}\n"

            if user_info['avatar']:
                user_info_str += f"> Avatar: https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}\n"
            if user_info['banner']:
                user_info_str += f"> Banner: https://cdn.discordapp.com/banners/{user_info['id']}/{user_info['banner']}\n"
            if user_info['avatar_decoration']:
                user_info_str += f"> Avatar Decoration: {user_info['avatar_decoration']}\n"
            if user_info['banner_color']:
                user_info_str += f"> Banner Color: {user_info['banner_color']}\n"

            user_info_str += footer

            await self.http_requests.send_message(channel_id, user_info_str, **kwargs)


    #Animate Text Command
    @bot_command('animate', min_args=1, max_args=1, category='Fun', description='Animates a text.', usage='animate <"text">')
    async def animate_text(self, window, channel_id, message_id, args, **kwargs):
        text = ''.join(args)
        animated_text = ""
        styles = ["bold", "italic", "underline", "strikethrough", "code"]

        for style in styles:
            styled_text = self.apply_style(text, style)
            animated_text += styled_text + " \n"  # Add a space at the end

            # Edit the message with the current animated text
            await self.http_requests.edit_last_message(channel_id, message_id, animated_text, **kwargs)

            # Pause for 1 second before applying the next style
            await asyncio.sleep(1)


    # Animate Text v2 Command
    @bot_command('animate-2', min_args=1, max_args=1, category='Fun', description='Animates a text v2.', usage='animate-2 <"text">')
    async def animate_text_2(self, window, channel_id, message_id, *args, **kwargs):
        words = args[0].split()
        for i in range(len(words)):
            # Send the first word as a new message
            if i == 0:
                await self.http_requests.edit_last_message(channel_id, message_id, words[i], **kwargs)
            else:
                # Edit the last message with the next word
                await self.http_requests.edit_last_message(channel_id, message_id, words[i], **kwargs)
            await asyncio.sleep(1)
        for i in range(len(words)):
            # Edit the last message with each word together with all previous words
            message = " ".join(words[:i+1])
            await self.http_requests.edit_last_message(channel_id, message_id, message, **kwargs)
            await asyncio.sleep(1)


    #Virus Upload Command
    @bot_command('virus', min_args=0, max_args=0, category='Fun', description='Uploads a virus (for fun).', usage='virus')
    async def virus_upload(self, window, channel_id, message_id, **kwargs):
        progress_bar_length = 30

        virus_frames = [
            "Uploading virus\n",
            "Uploading virus\n",
            "Virus Unpacking\n",
            "Virus Injection\n",
            "Virus Injected\n"
        ]

        progress_counters = [
            [0, 20],
            [20, 40],
            [40, 60],
            [60, 80], 
            [100, 100]  
        ]

        for i, frame in enumerate(virus_frames):
            start_percentage, end_percentage = progress_counters[i]

            progress_bar = self.generate_progress_bar(frame, progress_bar_length, start_percentage, end_percentage)

            message = f"```python\n{frame}\n{progress_bar}\n```"

            await self.http_requests.edit_last_message(channel_id, message_id, message, **kwargs)
            await asyncio.sleep(1)


    #OpenAI Chat GPT Command
    @bot_command('gpt', min_args=1, max_args=1, category='Requests', description='Asks GPT-3 a question.', usage='gpt <"prompt">')
    async def askgpt(self, window, channel_id, message_id, args, **kwargs):
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)

        api_key = "YOUR-API-KEY"
        if api_key == "YOUR-API-KEY":
            error_message = "Provide an API-Key to use this command, this is done through data/scripts/askgpt.py"
            await self.http_requests.send_message(channel_id, error_message, **kwargs)
            return

        text = ''.join(args)

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful, upbeat and funny assistant."},
                    {"role": "user", "content": text}
                ]
            },
            headers={"authorization": f"Bearer {api_key}"}
        ).json()

        if 'error' in response:
            error_message = response['error']['message']
            await self.http_requests.send_message(channel_id, error_message, **kwargs)
        else:
            response_message = f"```Prompt: {text}\n\nAnswer: {response['choices'][0]['message']['content']}```"
            await self.http_requests.send_message(channel_id, response_message, **kwargs)


    # Purge Messages Command
    @bot_command('purge', min_args=1, max_args=1, category='Utility', description='Purge your own messages.', usage='purge <num_of_messages>')
    async def purge_messages(self, window, channel_id, message_id, args, **kwargs):
        # Convert args from string to integer
        number_of_messages = int(args.replace('"', ''))
        
        # Fetch messages in batches until we've fetched enough
        messages_to_delete = []
        user_id = globals.user_data['id']  # get user id from global user data
        last_message_id = message_id  # start from the message that invoked the command
        while len(messages_to_delete) < number_of_messages:
            # Fetch the messages
            recent_messages = await self.http_requests.get_channel_messages(channel_id, limit=100, before=last_message_id, **kwargs)
            # If there are no more messages, we've reached the end of the channel's history
            if not recent_messages:
                break
            # Filter messages by the user who invoked the command and add them to our list
            user_messages = [msg for msg in recent_messages if msg['author']['id'] == user_id]
            messages_to_delete.extend(user_messages[:number_of_messages - len(messages_to_delete)])
            # Set the id of the last fetched message for the next iteration
            last_message_id = recent_messages[-1]['id']

        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        # Check if we found enough messages to delete
        if len(messages_to_delete) < number_of_messages:
            console_message = f'<span class="notifications">[Notification] </span>[{time.strftime("%H:%M:%S")}]: Could only find {len(messages_to_delete)} of your messages in the channel history.'
            window.evaluate_js('printToConsole(`' + console_message.replace('`', '\\`') + '`);')

        # Delete the messages
        for message in messages_to_delete:
            await self.http_requests.delete_message(channel_id, message['id'], **kwargs)


    #Validate Messages Command
    @bot_command('valid', min_args=0, max_args=0, category='Fun', description='Validates the last message jokingly.', usage='valid')
    async def validate_last_message(self, window, channel_id, message_id, *args, **kwargs):
        await self.send_edited_success_message(channel_id, "This opinion has been validated and confirmed by AI.", message_id, **kwargs)


    #Validate Messages Command
    @bot_command('invalid', min_args=0, max_args=0, category='Fun', description='Invalidates the last message jokingly.', usage='invalid')
    async def invalidate_last_message(self, window, channel_id, message_id, *args, **kwargs):
        await self.send_edited_success_message(channel_id, "This opinion is invalid and not confirmed by AI.", message_id, **kwargs)


    # Gottem Command
    @bot_command('gottem', min_args=0, max_args=0, category='Fun', description='Got\'em LMFAO.', usage='gottem')
    async def gottem_last_message(self, window, channel_id, message_id, *args, **kwargs):
        await self.send_edited_success_message(channel_id, "**Got'em good!** 💥👊😎 LMFAO 🚀🌟💯", message_id, **kwargs)


    # Snipe Edited Command
    @bot_command('esnipe', min_args=0, max_args=0, category='General', description='Snipe last edited message.', usage='esnipe')
    async def snipe_edit_message(self, window, channel_id, message_id, *args, **kwargs):
        last_updated_messages = self.message_cache.get_updates(channel_id)

        if last_updated_messages:
            # Extract the most recent version
            author_info = last_updated_messages[-1].get('author')  # get author info from the most recent version

            if author_info.get('id') == globals.user_data['id']:
                return

            if author_info is not None:
                author_name = author_info.get('username', 'Unknown')
                author_discriminator = author_info.get('discriminator', '0000')
                author = f"{author_name}#{author_discriminator}"
            else:
                author = 'Unknown'

            # Build a string containing all updated versions of the message
            updated_versions = ' -> '.join([f"[Edited] **{author}**: {message.get('content')}" for message in last_updated_messages])

            await self.send_specific_success_message(channel_id, "Sniper", updated_versions, message_id, **kwargs)
            return

        # No updated message found
        await self.send_specific_success_message(channel_id, "Sniper",  "No recent updated message found.", message_id, **kwargs)


    # Snipe Command
    @bot_command('dsnipe', min_args=0, max_args=0, category='General', description='Snipe last deleted message.', usage='dsnipe')
    async def snipe_delete_message(self, window, channel_id, message_id, *args, **kwargs):
        #print(f"Received snipe command for channel {channel_id}")

        last_deleted_message = self.message_cache.get_deleted(channel_id)
        
        if last_deleted_message:
            author_info = last_deleted_message.get('author')
            if author_info is not None:
                author_name = author_info.get('username', 'Unknown')
                author_discriminator = author_info.get('discriminator', '0000')
                author_id = author_info.get('id')

                # Exclude logged-in user's messages
                if author_id != globals.user_data['id']:
                    author = f"{author_name}#{author_discriminator}"
                    message_content = f"[Deleted] **{author}**: {last_deleted_message.get('content')}"
                    await self.send_specific_success_message(channel_id, "Sniper",  message_content, message_id, **kwargs)
                    return

        # No deleted message found
        await self.send_specific_success_message(channel_id, "Sniper",  "No recent deleted message found.", message_id, **kwargs)


    # Restart Self-Bot
    @bot_command('restart', min_args=0, max_args=0, category='General', description='Restarts the bot.', usage='restart')
    async def restart_bot(self, window, channel_id, message_id, *args, **kwargs):
        await self.send_edited_success_message(channel_id, "Restarting...", message_id, **kwargs)
        os.execv(sys.executable, ['python'] + sys.argv)

    
    #Ping/Latency Check
    @bot_command('ping', min_args=0, max_args=0, category='General', description='Checks the bot\'s latency, this calculates the speed of code execution and message edit speed.', usage='ping')
    async def ping(self, window, channel_id, message_id, *args, **kwargs):
        command_received_time = time.perf_counter() * 1000  # Convert time to milliseconds
        command_latency = (time.perf_counter() * 1000) - command_received_time
        total_latency = 0
        lowest_latency = float('inf')
        highest_latency = 0
        
        for _ in range(2):
            initial_time = time.perf_counter()
            await self.send_edited_success_message(channel_id, "🏓 Pong!", message_id, **kwargs)
            final_time = time.perf_counter()
            latency = (final_time - initial_time) * 1000
            total_latency += latency
            lowest_latency = min(lowest_latency, latency)
            highest_latency = max(highest_latency, latency)
        
        average_latency = total_latency / 2

        await self.send_edited_success_message(channel_id, f"🏓 Average Ping: {average_latency:.0f}ms\n"
                                                        f"> 🏆 Lowest Ping: {lowest_latency:.0f}ms\n"
                                                        f"> 🥇 Highest Ping: {highest_latency:.0f}ms\n"
                                                        f"> ⏰ SB Execution: {command_latency}ms",
                                                message_id, **kwargs)  # Add command_received_time in the response



    #Clear Chat
    @bot_command('clear', min_args=0, max_args=0, category='Fun', description='Clears the chat.', usage='clear')
    async def clear_chat(self, window, channel_id, message_id, *args, **kwargs):
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        clear_message = ''
        for _ in range(60):  # Change the range value to control the number of empty characters
            clear_message += '⠀\n'  # Use a special Unicode character for empty space
        
        await self.http_requests.send_message(channel_id, clear_message)

    #Dog Image
    @bot_command('dog', min_args=0, max_args=0, category='Fun', description='Get a random dog picture.', usage='dog')
    async def get_dog_picture(self, window, channel_id, message_id, *args, **kwargs):
        url = "https://dog.ceo/api/breeds/image/random"
        json_response = self.http_requests.make_api_request(url)
        
        if json_response is not None:
            image_url = json_response.get('message', None)
            await self.http_requests.delete_message(channel_id, message_id, **kwargs)
            await self.http_requests.send_message(channel_id, f" {image_url}")
        else:
            await self.send_edited_success_message(channel_id, "Failed to get a dog picture.", message_id, **kwargs)

    
    #Scrape an image from a given subreddit
    @bot_command('rscrape', min_args=1, max_args=1, category='Requests', description='Get a random image post from a specific subreddit.', usage='rscrape <subreddit_name>')
    async def get_reddit_scrape_image(self, window, channel_id, message_id, *args, **kwargs):
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        subreddit_name = args[0]

        reddit = praw.Reddit(
            client_id='your_cliend_id',
            client_secret='your_client_secret',
            user_agent='windows:reddit_scraper_hijack_self_bot:v1.2.3 (by /u/your_name_here)'
        )

        subreddit = reddit.subreddit(subreddit_name)
        posts = subreddit.new(limit=50)

        image_urls = [post.url for post in posts if post.url.endswith(('.jpg', '.png', '.gif'))]

        if image_urls:
            image_url = random.choice(image_urls)
            await self.http_requests.send_message(channel_id, f" {image_url}")
        else:
            await self.send_edited_success_message(channel_id, f"Failed to get an image from the subreddit: {subreddit_name}.", message_id, **kwargs)


    #Bump Message Add
    @bot_command('bump_add', min_args=4, max_args=4, category='Utility', description='Add a new bump message.', usage='bump_add <bump_id> <channel_id> <delay> <"Example Message">')
    async def add_bump(self, window, channel_id, message_id, *args, **kwargs):
        bump_id, target_channel, delay_seconds, *message_parts = args
        message_text = ' '.join(message_parts)

        # Handle the <#channel_id> format
        if target_channel.startswith('<#') and target_channel.endswith('>'):
            target_channel = target_channel[2:-1]

        # Add the bump message
        if self.bump_manager.add_bump_message(bump_id, target_channel, message_text, int(delay_seconds)):
            await self.send_specific_success_message(channel_id, "Bumper",  f"Successfully added bump message with ID: {bump_id}", message_id, **kwargs)
        else:
            await self.send_specific_success_message(channel_id, "Bumper", f"A Bump with ID: {bump_id} already exists.", message_id, **kwargs)


    @bot_command('bump_delete', min_args=1, max_args=1, category='Utility', description='Delete a bump message.', usage='bump_delete <bump_id>')
    async def delete_bump(self, window, channel_id, message_id, args, **kwargs):
        id, = args.split()
        
        if self.bump_manager.delete_bump_message(id):
            # If successfully deleted
            await self.send_specific_success_message(channel_id, "Bumper",  f"Successfully deleted bump message with ID: {id}", message_id, **kwargs)
        else:
            # If bump with the given id does not exist
            await self.send_specific_success_message(channel_id, "Bumper",  f"No bump message found with ID: {id}", message_id, **kwargs)


    #Start Bump
    @bot_command('bump_start', min_args=1, max_args=1, category='Utility', description='Start a bump message.', usage='bump_start <bump_id>')
    async def start_bump(self, window, channel_id, message_id, args, **kwargs):
        id, = args.split()

        # Start the bump message
        if self.bump_manager.start_bump(id):
            await self.send_specific_success_message(channel_id, "Bumper",  f"Bumper started for ID: {id}", message_id, **kwargs)
        else:
            await self.send_specific_success_message(channel_id, "Bumper", f"No Bump found with ID: {id}", message_id, **kwargs)

    
    #Stop Bump
    @bot_command('bump_stop', min_args=1, max_args=1, category='Utility', description='Stop a bump message.', usage='bump_stop <bump_id>')
    async def stop_bump(self, window, channel_id, message_id, args, **kwargs):
        id, = args.split()

        # Stop the bump message
        if self.bump_manager.stop_bump(id):
            await self.send_specific_success_message(channel_id, "Bumper",  f"Bumper stopped for ID: {id}", message_id, **kwargs)
        else:
            await self.send_specific_success_message(channel_id, "Bumper", f"No Bump found with ID: {id}", message_id, **kwargs)


    #Bump List
    @bot_command('bump_list', min_args=0, max_args=0, category='Utility', description='List all bump messages.', usage='bump_list')
    async def bump_list(self, window, channel_id, message_id, **kwargs):
        if self.bump_manager.bump_messages:
            message = "Registered bumps:\n"
            for id, bump in self.bump_manager.bump_messages.items():
                status = 'Active' if bump['active'] else 'Inactive'
                message += f"> Bump ID: {id}, Target Channel: {bump['channel_id']}, Delay: {bump['delay']}, Status: {status}\n"
        else:
            message = "No registered bumps found."

        await self.send_specific_success_message(channel_id, "Bumper", message, message_id, **kwargs)


    #Set Profile Photo
    @bot_command('setpfp', min_args=1, max_args=1, category='Utility', description='Change profile picture.', usage='setpfp <image_url>')
    async def set_pfp(self, window, channel_id, message_id, *args, **kwargs):
        image_url = args[0]
        if self.http_requests.change_profile_picture(image_url):
            await self.send_specific_success_message(channel_id, "Avatar", "Successfully changed profile picture.", message_id, **kwargs)
        else:
            await self.send_specific_success_message(channel_id, "Avatar", "Failed to change profile picture.", message_id, **kwargs)


    #Spy Add
    @bot_command('spy_add', min_args=1, max_args=1, category='Utility', description='Add a new id to spy on.', usage='spy_add <user_id>')
    async def add_spy(self, window, channel_id, message_id, *args, **kwargs):
        user_id = self.handle_user_mention(args[0])
        if user_id is None:
            await self.send_specific_success_message(channel_id, "Spy", "Invalid user ID or mention.", message_id, **kwargs)
        elif user_id == globals.user_data['id']:
            await self.send_specific_success_message(channel_id, "Spy", "You cannot add yourself as a spy.", message_id, **kwargs)
        elif self.spy_manager.add_spy(user_id):
            await self.send_specific_success_message(channel_id, "Spy", f"Successfully added spy with user ID: {user_id}", message_id, **kwargs)
        else:
            await self.send_specific_success_message(channel_id, "Spy", f"A spy with user ID: {user_id} already exists.", message_id, **kwargs)


    #Spy Remove
    @bot_command('spy_remove', min_args=1, max_args=1, category='Utility', description='Remove a spy.', usage='spy_remove <user_id>')
    async def remove_spy(self, window, channel_id, message_id, *args, **kwargs):
        user_id = args[0]
        if self.spy_manager.remove_spy(user_id):
            await self.send_specific_success_message(channel_id, "Spy", f"Successfully removed spy with user ID: {user_id}", message_id, **kwargs)
        else:
            await self.send_specific_success_message(channel_id, "Spy", f"No spy with user ID: {user_id} found.", message_id, **kwargs)


    #Spy List
    @bot_command('spy_list', min_args=0, max_args=0, category='Utility', description='List all spies.', usage='spy_list')
    async def list_spies(self, window, channel_id, message_id, *args, **kwargs):
        spies = self.spy_manager.list_spies()
        await self.send_specific_success_message(channel_id, "Spy", f"Current spied people: {', '.join(spies)}", message_id, **kwargs)


    ###############
    ## Functions ##
    ###############
    async def send_error_message(self, channel_id, error_message, message_id, **kwargs):
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        header = "> ## Invalid Command! ##"
        error_message = f"> {error_message}."
        footer = "```md\n> # Ngin#3612 #```"
        await self.http_requests.send_message(channel_id, f"{header}\n{error_message}{footer}")


    async def send_success_message(self, channel_id, success_message, message_id, **kwargs):
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        header = "> ## Commands ## "
        message = f"{success_message}"
        await self.http_requests.send_message(channel_id, f"{header}\n{message}")


    async def send_specific_success_message(self, channel_id, title, success_message, message_id, **kwargs):
        await self.http_requests.delete_message(channel_id, message_id, **kwargs)
        header = f"> ## {title} ##"
        message = f"> {success_message}"
        footer = "```md\n> # Ngin#3612 #```"
        await self.http_requests.send_message(channel_id, f"{header}\n{message}{footer}")


    async def send_edited_success_message(self, channel_id, success_message, message_id, **kwargs):
        header = "> ## Commands ##"
        message = f"> {success_message}"
        footer = "```md\n> # Ngin#3612 #```"
        await self.http_requests.edit_last_message(channel_id, message_id, f"{header}\n{message}{footer}", **kwargs)


    def handle_user_mention(self, user_mention):
        # If the argument starts with <@ and ends with >, it's a mention
        if user_mention.startswith('<@') and user_mention.endswith('>'):
            # Remove <@ and > to get the user ID
            user_id = user_mention[2:-1]

            # If the ID starts with !, it's a nickname mention and we need to remove the !
            if user_id.startswith('!'):
                user_id = user_id[1:]
        elif user_mention.isdigit():
            # If the argument is a number, it's a user ID
            user_id = user_mention
        else:
            # Invalid argument
            return None

        return user_id


    def get_creation_date(self, user_id):
        discord_epoch = 1420070400000
        creation_time = ((int(user_id) >> 22) + discord_epoch) / 1000.0
        return datetime.utcfromtimestamp(creation_time)

    def generate_progress_bar(self, frame, length, start_percentage, end_percentage):
        filled_length = int(length * (end_percentage / 100))
        empty_length = length - filled_length

        # Generate the progress bar with number counter
        progress_bar = f"[{'▓' * filled_length}{' ' * empty_length}] {end_percentage}%"

        return progress_bar

    def apply_style(self, text, style_option):
        # Apply the specified style option to the text
        if style_option == "bold":
            return f"**{text}**"
        elif style_option == "italic":
            return f"*{text}*"
        elif style_option == "underline":
            return f"__{text}__"
        elif style_option == "strikethrough":
            return f"~~{text}~~"
        elif style_option == "code":
            return f"`{text}`"
        else:
            return text


# Apply the decorator to the class
ChatCommands = register_commands(ChatCommands)


