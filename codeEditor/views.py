from django.shortcuts import render, redirect,get_object_or_404
from .models import  File,CurrentOutput
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests

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

def get_version(lang):
    for key, value in languages_dict.items():
        if lang == key or lang in value.get("aliases", []):
            return value["version"]
    return 
def getLanuages():
    return languages_dict

    

@login_required
def dashboard(request):
    if request.user.is_authenticated:

        context = {}
        try:
            files = File.objects.filter(user=request.user)
            context={
                'files': files
            }
        except:
            context = {
                'files': None
            }
        return render(request,'projects.html',context)
    else:   
        return redirect('/loginpage/')

@login_required
def creating_project(request):
    if request.method == 'POST':
        file_name = request.POST['file_name']
        language = request.POST['language']
        description = request.POST['project_description']
        project_obj = File.objects.create(
            user=request.user, 
            file_name=file_name,
            extension = language,
            description = description
        )
        project_obj.save()
    return redirect('/dashboard/')

@login_required
def project_editor(request,file_id):
    file_output =None
    file = None
    try:
        file = File.objects.get(id=file_id,user=request.user)
        file_output = CurrentOutput.objects.get(file=file)
    except Exception as e:
        context={
            'file_output':e,
            'languages':getLanuages()
        }
    context = {
        'file': file,
        'id': file_id,
        'file_output':file_output,
        'languages':getLanuages()
    }
    return render(request, 'editor.html', context)

@login_required
def save_code(request):
    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        content = request.POST.get('content')
        description = request.POST.get('description')   
        file_obj = File.objects.get(id=file_id)
        file_obj.content = content
        file_obj.extension = file_obj.extension
        file_obj.description = description
        file_obj.save()
    return redirect(f'/projecteditor/{file_id}/')

@login_required
def update_file(request):
    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        file_name = request.POST.get('file_name')
        description = request.POST.get('description')
        extainson = request.POST.get('language')

        file_obj = File.objects.get(id=file_id)
        file_obj.extension = extainson
        file_obj.description = description
        file_obj.file_name = file_name
        file_obj.save()
    return redirect(f'/projecteditor/{file_id}/')

@login_required
def rename_file(request):
    context={}
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            filename = data.get("filename")
            file_id = data.get("file_id")
            file = File.objects.get(id=file_id)
            file.file_name = filename
            context = {
                "status": "success",
                "message": "File successfully renamed"
            }
            return JsonResponse(context)
        except Exception as e:
            context['message']=e
            context['status']="Failed"
            return JsonResponse(context)
    context['message']="Request method should be POST"
    return JsonResponse(context)

@csrf_exempt
def delete_file(request, file_id):
    if request.method == "DELETE":
        try:
            file = File.objects.get(id=file_id)
            file.delete()
            return JsonResponse({"message": "File deleted successfully"}, status=200)
        except File.DoesNotExist:
            return JsonResponse({"error": "File not found"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def execute_code(request):
    if request.method == 'POST':
        try:
            # Parse request body
            print("Reauest Come for run code")
            data = json.loads(request.body)
            file_id = data.get('file_id')
            script = data.get('content')
            language = data.get('language')
            # Fetch file object
            file_obj = get_object_or_404(File, id=file_id)
            file_obj.content = script
            file_obj.extension = language
            file_obj.save()

            exec_url = "https://emkc.org/api/v2/piston/execute"
            # Prepare execution request
            exec_data = {
                "language":language,
                "version":get_version(language),
                "files":[{"name":"main","content":script}],
                "stdin":"",
            }

            # Send execution request
            headers = {"Content-Type": "application/json"}
            exec_response = requests.post(exec_url, json=exec_data, headers=headers)
            
            if exec_response.status_code == 200:
                result = exec_response.json()

                # Save output in CurrentOutput model
                output, created = CurrentOutput.objects.update_or_create(
                    file=file_obj,
                    defaults={
                        "output": result.get("run", {}).get("stdout", ""),
                        "memory": result.get("run", {}).get("memory", ""),
                        "cpuTime": result.get("run", {}).get("time", ""),
                    }
                )

                return JsonResponse({
                    "message": "Program executed successfully",
                    "output": result.get("run", {}).get("stdout", ""),
                    "memory": result.get("run", {}).get("memory", ""),
                    "cpuTime": result.get("run", {}).get("time", ""),
                    "error": result.get("run", {}).get("stderr", ""),
                    "exit_code": result.get("run", {}).get("code", ""),
                }, status=200)
            else:
                return JsonResponse({"error": "Error executing code"}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except File.DoesNotExist:
            return JsonResponse({"error": "File not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
