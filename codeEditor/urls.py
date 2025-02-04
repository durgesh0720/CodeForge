from django.urls import path    
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('creating_project/',views.creating_project, name='creating_project'),
    path('projecteditor/<int:file_id>/',views.project_editor, name='project_editor'),
    path('save-code/', views.save_code, name='saveCode'),
    path('update-file/', views.update_file,name='updateFile'),
    path('execute-code/',views.execute_code, name='executeCode'),
    # path('createing-Room/',views.create_room,name='create_room'),
    # path('joining-room/',views.join_room,name='join_room')
]
