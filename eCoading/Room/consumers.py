import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eCoading.settings")
django.setup()  # ✅ Initialize Django before importing models

import json
import requests
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from codeEditor.models import File, CurrentOutput

class CodeEditorRoom(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = {}  # Initialize buffer

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']  # Get the room ID
        self.room_group_name = f"editor_{self.room_id}"

        # Add the user to the group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"WebSocket Connected: Room ID {self.room_id}")

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"WebSocket Disconnected: Room ID {self.room_id}")

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

            file_obj = await self.get_file(file_id)
            if not file_obj:
                return

            # Save file content and language properly
            file_obj.content = script
            file_obj.extension = language  # Correct field name
            await self.save_file(file_obj)  # Ensure file is saved

            # Execute code
            output_data = await self.execute_code(script, language)

            # Store in buffer and save to DB
            self.buffer[file_id] = output_data
            await self.save_output(file_obj, output_data)

            # Send results to all users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'code_execution_result',
                    'file_id': file_id,
                    'output_data': output_data,
                }
            )

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

    async def code_execution_result(self, event):
        """Send execution results to WebSocket clients."""
        await self.send(text_data=json.dumps({
            'action': 'execution_result',
            'file_id': event['file_id'],
            'output_data': event['output_data'],
        }))

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
    

    async def execute_code(self, script, language):
        """Calls external API to execute code."""
        exec_url = "https://api.jdoodle.com/v1/execute"
        version_index = "2"

        client_id = "75ffd2d60cf63f433bceb887182c5d5a"
        client_secret = "dcb1d3e63c7486f34c325bcb516b45a6aa9e1c68fdbc4cf52b2f542e5bb614dd"

        exec_data = {
            "script": script,
            "stdin": "",
            "language": language,
            "versionIndex": version_index,
            "clientId": client_id,
            "clientSecret": client_secret
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

    
