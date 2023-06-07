import requests
import globals
import asyncio
import json
import functools
import base64
from datetime import datetime

class HTTPRequests:

    def get_bot_name(self, token):
        headers = {
            "Authorization": token
        }

        url = "https://discord.com/api/v9/users/@me"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            #print(data)
            globals.user_data = data
            return data
        else:
            return {"error": response.text}
        

    def get_user_relationships(self, token):
        headers = {
            "Authorization": token
        }

        url = "https://discord.com/api/v9/users/@me/relationships"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Reset global variables
            globals.relationship_counts = {
                'friends': 0,
                'blocked': 0,
                'incoming_requests': 0,
                'outgoing_requests': 0
            }

            globals.detailed_relationships = {
                'friends': [],
                'blocked': [],
                'incoming_requests': [],
                'outgoing_requests': []
            }

            for relationship in data:
                user_id = relationship['user']['id']
                username = relationship['user']['username']
                discriminator = relationship['user']['discriminator']
                user_link = f"discord://discord.com/users/{user_id}"
                user_info = {"id": user_id, "username": username, "discriminator": discriminator, "link": user_link}
                
                if relationship['type'] == 1:  # Friend
                    globals.relationship_counts['friends'] += 1
                    globals.detailed_relationships['friends'].append(user_info)
                elif relationship['type'] == 2:  # Blocked
                    globals.relationship_counts['blocked'] += 1
                    globals.detailed_relationships['blocked'].append(user_info)
                elif relationship['type'] == 3:  # Incoming Request
                    globals.relationship_counts['incoming_requests'] += 1
                    globals.detailed_relationships['incoming_requests'].append(user_info)
                elif relationship['type'] == 4:  # Outgoing Request
                    globals.relationship_counts['outgoing_requests'] += 1
                    globals.detailed_relationships['outgoing_requests'].append(user_info)
            return True

        else:
            return False

    
    def delete_relationship(self, token, user_id):
        headers = {
            "Authorization": token
        }

        url = f"https://discord.com/api/v9/users/@me/relationships/{user_id}"
        response = requests.delete(url, headers=headers)

        if response.status_code == 204:
            return True
        else:
            return False

    
    def change_profile_picture(self, image_url):
        token = globals.global_token
        response = requests.get(image_url)
        if response.status_code != 200:
            return None

        image_base64 = base64.b64encode(response.content).decode()

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        payload = {
            "avatar": f"data:image/jpeg;base64,{image_base64}"
        }

        response = requests.patch('https://discord.com/api/v9/users/@me', headers=headers, json=payload)
        if response.status_code == 200:
            return True
        else:
            print('Failed to change profile picture. Response status code: %s. Response body: %s', response.status_code, response.text)
            return False


    async def edit_last_message(self, channel_id, message_id, new_content, **kwargs):
        token = globals.global_token
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        data = {
            "content": new_content,
        }
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, functools.partial(requests.patch, url, headers=headers, data=json.dumps(data)))

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as ex:
            print("Error editing message:", str(ex))



    async def delete_message(self, channel_id, message_id, **kwargs):
        token = globals.global_token
        headers = {
            "Authorization": token
        }
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, functools.partial(requests.delete, url, headers=headers))

            
            if response.status_code == 429: 
                retry_after = response.headers['Retry-After'] 
                await asyncio.sleep(int(retry_after))
                response = await loop.run_in_executor(None, functools.partial(requests.delete, url, headers=headers)) 

            if response.status_code == 204:
                return {"success": True}
            else:
                return {"error": response.text}
        except Exception as ex:
            print("Error deleting message:", str(ex))




    async def send_message(self, channel_id, content, **kwargs):
        token = globals.global_token
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        data = {
            "content": content,
        }
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, functools.partial(requests.post, url, headers=headers, data=json.dumps(data)))

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as ex:
            print("Error sending message:", str(ex))


    async def send_slash_command(self, bot_id, channel_id, guild_id, slash_command, **kwargs):
        token = globals.global_token
        url = "https://discord.com/api/v9/interactions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": token
        }

        data = {
            "type": 2,
            "application_id": bot_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "data": {
                "name": slash_command,
                "type": 1
            }
        }

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, functools.partial(requests.post, url, headers=headers, data=json.dumps(data)))

            if response.status_code == 204:
                print("Slash command executed successfully.")
            else:
                print("Failed to execute slash command. Response:", response.content)
        except Exception as ex:
            print("Error executing slash command:", str(ex))



    async def get_channel_messages(self, channel_id, limit=100, before=None, **kwargs):
        token = globals.global_token
        headers = {
            "Authorization": token
        }
        params = {
            "limit": limit
        }
        if before is not None:
            params['before'] = before

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, functools.partial(requests.get, url, headers=headers, params=params))

            if response.status_code == 429: 
                retry_after = response.headers.get('X-RateLimit-Reset-After')
                if retry_after:
                    await asyncio.sleep(float(retry_after))
                    return await self.get_channel_messages(channel_id, limit=limit, before=before, **kwargs)
                else:
                    print("Received rate limit response but no 'Retry-After' header")
                    return {"error": "Rate limit exceeded"}

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as ex:
            print("Error getting channel messages:", str(ex))



    def get_user_info(self, user_id, **kwargs):
        token = globals.global_token
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }

        url = f"https://discord.com/api/v9/users/{user_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            user_data = response.json()

            discord_epoch = 1420070400000

            creation_timestamp = ((int(user_id) >> 22) + discord_epoch) / 1000
            creation_date = datetime.utcfromtimestamp(creation_timestamp).isoformat()

            user_data['creation_date'] = creation_date

            return user_data
        else:
            return {"error": response.text}


    def send_webhook_message(self, url, content=None, embeds=None, **kwargs):
        headers = {
            "Content-Type": "application/json"
        }

        payload = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds

        response = requests.post(url, headers=headers, json=payload)

        if response.content:
            return response.json()
        

    def make_api_request(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None

