import json
import requests
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache  # Use Django cache with Redis as the backend
from codeEditor.models import File, CurrentOutput
import os
from dotenv import load_dotenv

load_dotenv() 

ROOM_USERS={}



class CodeEditorRoom(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = {}  # In-memory buffer for code execution results, can be replaced by Redis
        self.JD_CLIENT_ID = os.getenv("JD_CLIENT_ID")
        self.JD_CLIENT_SECRET = os.getenv("JD_CLIENT_SECRET")

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']  # Get the room ID
        self.room_group_name = f"editor_{self.room_id}"
        self.username = self.scope["user"].username

        if self.room_group_name not in ROOM_USERS:
            ROOM_USERS[self.room_group_name] = set()
        ROOM_USERS[self.room_group_name].add(self.username)

        # Add the user to the group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"WebSocket Connected: Room ID {self.room_id}")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_list_update",
                "users": list(ROOM_USERS[self.room_group_name]),
            },
        )

    async def disconnect(self, close_code):
         # Remove user from the room
        if self.room_group_name in ROOM_USERS:
            ROOM_USERS[self.room_group_name].discard(self.username)
            if not ROOM_USERS[self.room_group_name]:  # Clean up empty rooms
                del ROOM_USERS[self.room_group_name]

        if self.channel_layer is not None:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"WebSocket Disconnected: Room ID {self.room_id}")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_list_update",
                "users": list(ROOM_USERS.get(self.room_group_name, [])),
            },
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        username = data.get('username')

        if action == 'message':
            username = data.get('username')
            message = data.get('message')
            await self.send_message_to_group(message, username)
        
        if action == "code_update":
            username = data.get("username")
            code = data.get("code")
            cursor = data.get("cursor_position")
            await self.send_code_update_to_group(code, username, cursor)

        if action == "run_code":
            file_id = data.get('file_id')
            script = data.get('content')
            language = data.get('language')
            versionIndex = data.get("versionIndex")

            file_obj = await self.get_file(file_id)
            if not file_obj:
                return

            # Save file content and language properly
            file_obj.content = script
            file_obj.extension = language  # Correct field name
            await self.save_file(file_obj)  # Ensure file is saved

            # Execute code
            output_data = await self.execute_code(script, language)

            # Send results to all users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'code_execution_result',
                    'file_id': file_id,
                    'output_data': output_data,
                }
            )
    
    async def send_message_to_group(self, message, username):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'username': username,
                'message': message
            }
        )
    async def chat_message(self, event):
        message = event['message']
        username = event['username']

        await self.send(text_data=json.dumps({
            'action': 'message',
            'username': username,
            'message': message
        }))
    
    async def code_execution_result(self, event):
        """Send execution results to WebSocket clients."""
        await self.send(text_data=json.dumps({
            'action': 'execution_result',
            'file_id': event['file_id'],
            'output_data': event['output_data'],
        }))

    async def send_code_update_to_group(self, code, username, cursor):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'editor_update',
                'username': username,
                'code': code,
                'cursor_position':cursor,
            }
        )
    
    async def editor_update(self, event):
        await self.send(text_data=json.dumps({
            "action": "code_update",
            "username": event.get("username", ""),
            "code": event.get("code", None),
            "cursor_position":event.get("cursor_position",None)
        }))

    async def execute_code(self, script, language):
        """Calls external API to execute code."""
        exec_url = "https://api.jdoodle.com/v1/execute"
        version_index = await self.get_version_index(language)
        version_index = await self.get_version_index(language)
        if version_index == "Unknown":
            return {"output": "Error: Unsupported language", "memory": "", "cpuTime": ""}


        exec_data = {
            "script": script,
            "stdin": "",
            "language": language,
            "versionIndex": version_index,
            "clientId": self.JD_CLIENT_ID,
            "clientSecret": self.JD_CLIENT_SECRET
        }

        try:
            exec_response = requests.post(exec_url, json=exec_data)

            if exec_response.status_code == 200:
                exec_json = exec_response.json()
                return {
                    'output': exec_json.get('output', ''),
                    'memory': exec_json.get('memory', ''),
                    'cpuTime': exec_json.get('cpuTime', ''),
                }
            else:
                print(f"Error executing code: {exec_response.status_code}, {exec_response.text}")
                return {"output": "Execution error", "memory": "", "cpuTime": ""}

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return {"output": "Request error", "memory": "", "cpuTime": ""}

    # async def save_output_to_redis(self, file_id, output_data):
    #     """Saves the code output to Redis."""
    #     redis_key = f"file_output_{file_id}"
        
    #     # Store the output data as a JSON string in Redis
    #     cache.set(redis_key, json.dumps(output_data), timeout=3600)  # Set expiration time if necessary

    # async def get_output_from_redis(self, file_id):
    #     """Fetches the code output from Redis."""
    #     redis_key = f"file_output_{file_id}"
    #     output_data = cache.get(redis_key)
    #     if output_data:
    #         return json.loads(output_data)
    #     return None

    @database_sync_to_async
    def get_file(self, file_id):
        """Fetches file object asynchronously."""
        try:
            return File.objects.get(id=file_id)
        except File.DoesNotExist:
            return None
        
    @database_sync_to_async
    def save_file(self, file_obj):
        """Saves the file asynchronously."""
        file_obj.save()  # Use save method instead of asave
    
    @database_sync_to_async
    def save_output(self, file_obj, output_data):
        """Saves execution output to the database."""
        try:
            program_output = CurrentOutput.objects.get(file=file_obj)
        except CurrentOutput.DoesNotExist:
            program_output = CurrentOutput(file=file_obj)

        # Ensure no NULL values
        program_output.output = output_data.get('output', 'No Output')
        program_output.memory = output_data.get('memory', '0KB')
        program_output.cpuTime = output_data.get('cpuTime', '0.00s')
        
        program_output.save()

    async def user_list_update(self, event):
            await self.send(text_data=json.dumps({"action": "user_list_update", "users": event["users"]}))



    async def get_version_index(self,language):
        latest_versions = {
            "c": "5",
            "cpp": "5",
            "java": "5",
            "python3": "4",
            "php": "4",
            "perl": "4",
            "ruby": "4",
            "go": "4",
            "scala": "4",
            "bash": "4",
            "r": "4",
            "swift": "4",
            "objc": "4",
            "mysql": "5",
            "mssql": "4",
            "plsql": "4",
            "html": "4",
            "csharp": "4",
            "vb": "4",
            "fsharp": "4",
            "scheme": "4",
            "nodejs": "4",
            "prolog": "4",
            "assembly": "4",
            "clisp": "4",
            "elixir": "4",
            "erlang": "4",
            "dart": "4",
            "kotlin": "4",
            "javascript": None,
        }
        
        return latest_versions.get(language.lower(), "Unknown")

