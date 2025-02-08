from django.shortcuts import render, redirect,HttpResponse
from .models import  File,CurrentOutput
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import requests
import aiohttp

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
            'file_output':e
        }
    context = {
        'file': file,
        'id': file_id,
        'file_output':file_output
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
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            filename = data.get("new_filename")
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

@login_required
def execute_code(request):
    if request.method == 'POST':
        context = {}
        file_id = request.POST.get('file_id')
        script = request.POST.get('content')
        language = request.POST.get('language')

        file_obj = File.objects.get(id=file_id)

        file_obj.content=script
        file_obj.extension = language
        print(f'Execute: ',script)
        file_obj.save()

        auth_url = "https://api.jdoodle.com/v1/auth-token"
        exec_url = "https://api.jdoodle.com/v1/execute"
        version_index = "2"
        client_id = "79f69246d6fd2665bb3df2f217e57383"
        client_secret = "a5e6d402d2be3923b35dabb61505b71b06157834cad62c58346cec6510814c55"

        auth_data = {
            "clientId": client_id,
            "clientSecret": client_secret,
        }

        # Fetch auth token
        auth_response = requests.post(auth_url, json=auth_data)
        if auth_response.status_code == 200:
            try:
                auth_token = auth_response.text
                
                exec_data = {
                    "script": script,
                    "stdin": "",
                    "language": language,
                    "versionIndex": version_index,
                    "clientId": client_id,
                    "clientSecret": client_secret,
                    "token": auth_token
                }

                # Execute code
                exec_response = requests.post(exec_url, json=exec_data)
                if exec_response.status_code == 200:
                    result = exec_response.json()
                    context['output'] = f" {result.get('output')} "
                    context['Memory'] = f"Memory: {result.get('memory')}"
                    context['cpuTime'] = f"cpuTime: {result.get('cpuTime')}"
                    # Fetch and save the file object
                    try:
                        program_output = CurrentOutput.objects.get(file=file_obj)
                        program_output.output = context['output']
                        program_output.memory = context['Memory']
                        program_output.cpuTime = context['cpuTime']
                        program_output.save()
                        file_obj.save()
                    except:
                        output = CurrentOutput.objects.create(
                            file = file_obj,
                            output = context['output'],
                            memory = context['Memory'],
                            cpuTime = context['cpuTime']
                        ) 
                        output.save()
                        file_obj.save()
                    return redirect(f'/projecteditor/{file_id}')
                else:
                    context['output'] = "Error executing code"
                    return redirect(f'/projecteditor/{file_id}')

            except ValueError:
                context['output'] = "Error parsing response"
        else:
            context['output'] = "Error fetching auth token"
        return redirect(f'/projecteditor/{file_id}')
    
# @login_required
# def create_room(request):
#     if request.method == "POST":
#         room_id = request.POST.get('room_id')
#         file_id = request.POST.get('file_id')
#         file_obj = File.objects.get(id=file_id)
#         print(f"Creating Room: {file_id} {room_id}")
#         if file_obj is None:
#             return redirect('dashboard')
#         file_output = CurrentOutput.objects.get(file = file_obj)
#         context = {
#             'room_id':room_id,
#             'file':file_obj,
#             'file_output':file_output
#         }
#         print(f"Context: {context}")
#         return render(request,'Room_Editor_Page.html',context)

# @login_required
# def join_room(request):
#     if request.method == "POST":
#         room_id = request.POST.get('room_id') 
#         return render(request,'Room_Editor_Page.html',{'room_id':room_id})


