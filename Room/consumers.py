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
            language = f"{data.get('language')}".lower()
            versionIndex = data.get("versionIndex")

            file_obj = await self.get_file(file_id)
            if not file_obj:
                return

            # Save file content and language properly
            file_obj.content = script
            file_obj.extension = f"{language}".lower()  # Correct field name
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
        exec_url = "https://emkc.org/api/v2/piston/execute"
        exec_data = {
            "language":language,
            "version": await self.get_version(language),
            "files":[{"name":"main","content":script}],
            "stdin":"",
        }
        try:
            exec_response = requests.post(exec_url, json=exec_data)

            if exec_response.status_code == 200:
                exec_json = exec_response.json()
                return ({
                    "output": exec_json.get("run", {}).get("stdout", ""),
                    "error": exec_json.get("run", {}).get("stderr", ""),
                    "exit_code": exec_json.get("run", {}).get("code", ""),
                    "cpuTime": exec_json.get("run", {}).get("time", ""),
                    "memory": exec_json.get("run", {}).get("memory", ""),
                    "language": exec_json.get("language", ""),
                    "version": exec_json.get("version", "")
                })
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

    async def user_list_update(self, event):
            await self.send(text_data=json.dumps({"action": "user_list_update", "users": event["users"]}))


    async def get_version(self,lang):
        languages_dict = {
        "matl": {"version": "22.7.4", "aliases": []},
        "bash": {"version": "5.2.0", "aliases": ["sh"]},
        "befunge93": {"version": "0.2.0", "aliases": ["b93"]},
        "bqn": {"version": "1.0.0", "aliases": []},
        "brachylog": {"version": "1.0.0", "aliases": []},
        "brainfuck": {"version": "2.7.3", "aliases": ["bf"]},
        "cjam": {"version": "0.6.5", "aliases": []},
        "clojure": {"version": "1.10.3", "aliases": ["clojure", "clj"]},
        "cobol": {"version": "3.1.2", "aliases": ["cob"]},
        "coffeescript": {"version": "2.5.1", "aliases": ["coffeescript", "coffee"]},
        "cow": {"version": "1.0.0", "aliases": ["cow"]},
        "crystal": {"version": "0.36.1", "aliases": ["crystal", "cr"]},
        "dart": {"version": "2.19.6", "aliases": []},
        "dash": {"version": "0.5.11", "aliases": ["dash"]},
        "typescript": {"version": "1.32.3", "aliases": ["deno", "deno-ts"], "runtime": "deno"},
        "javascript": {"version": "1.32.3", "aliases": ["deno-js"], "runtime": "deno"},
        "basic.net": {
            "version": "5.0.201",
            "aliases": ["basic", "visual-basic", "vb.net", "dotnet-basic"],
            "runtime": "dotnet",
        },
        "fsharp.net": {
            "version": "5.0.201",
            "aliases": ["fsharp", "fs", "f#", "dotnet-fsharp"],
            "runtime": "dotnet",
        },
        "csharp.net": {
            "version": "5.0.201",
            "aliases": ["csharp", "c#", "dotnet-csharp"],
            "runtime": "dotnet",
        },
        "fsi": {
            "version": "5.0.201",
            "aliases": ["fsx", "fsharp-interactive"],
            "runtime": "dotnet",
        },
        "dragon": {"version": "1.9.8", "aliases": []},
        "elixir": {"version": "1.11.3", "aliases": ["elixir", "exs"]},
        "emacs": {"version": "27.1.0", "aliases": ["el", "elisp"]},
        "emojicode": {"version": "1.0.2", "aliases": ["emojic"]},
        "erlang": {"version": "23.0.0", "aliases": ["erl", "escript"]},
        "file": {"version": "0.0.1", "aliases": ["executable", "elf", "binary"]},
        "forth": {"version": "0.7.3", "aliases": ["gforth"]},
        "freebasic": {"version": "1.9.0", "aliases": ["qbasic", "quickbasic"]},
        "awk": {"version": "5.1.0", "aliases": ["gawk"], "runtime": "gawk"},
        "c": {"version": "10.2.0", "aliases": ["gcc"], "runtime": "gcc"},
        "c++": {"version": "10.2.0", "aliases": ["cpp", "g++"], "runtime": "gcc"},
        "d": {"version": "10.2.0", "aliases": ["gdc"], "runtime": "gcc"},
        "go": {"version": "1.16.2", "aliases": ["go", "golang"]},
        "java": {"version": "15.0.2", "aliases": []},
        "julia": {"version": "1.8.5", "aliases": ["jl"]},
        "kotlin": {"version": "1.8.20", "aliases": ["kt"]},
        "lisp": {"version": "2.1.2", "aliases": ["cl", "sbcl", "commonlisp"]},
        "lua": {"version": "5.4.4", "aliases": []},
        "python2": {"version": "2.7.18", "aliases": ["py2"]},
        "python": {"version": "3.10.0", "aliases": ["py", "python3", "python3.10"]},
        "racket": {"version": "8.3.0", "aliases": ["rkt"]},
        "ruby": {"version": "3.0.1", "aliases": ["rb"]},
        "rust": {"version": "1.68.2", "aliases": ["rs"]},
        "scala": {"version": "3.2.2", "aliases": ["sc"]},
        "smalltalk": {"version": "3.2.3", "aliases": ["st"]},
        "sqlite3": {"version": "3.36.0", "aliases": ["sqlite", "sql"]},
        "swift": {"version": "5.3.3", "aliases": ["swift"]},
        "typescript": {"version": "5.0.3", "aliases": ["ts", "node-ts"]},
        "vlang": {"version": "0.3.3", "aliases": ["v"]},
        "zig": {"version": "0.10.1", "aliases": []},
    }
        for key, value in languages_dict.items():
            if lang == key or lang in value.get("aliases", []):
                return value["version"]
        return None
