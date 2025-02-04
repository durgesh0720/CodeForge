from django.db import models
from django.contrib.auth.models import User

class File(models.Model): 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=100)
    content = models.TextField(null=True, blank=True)
    extension = models.CharField(max_length=10, default='txt')  # Fix Typo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(default="", null=True, blank=True)

    def __str__(self):
        return self.file_name

class CurrentOutput(models.Model):
    file = models.OneToOneField(File,on_delete=models.CASCADE,related_name='currentoutput')
    output = models.TextField(blank=True)
    memory = models.CharField(max_length=50, blank=True)
    cpuTime = models.CharField(max_length=50, blank=True)

    
