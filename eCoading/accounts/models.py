from django.db import models
from django.contrib.auth.models import User


class coder(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="user")
    profile = models.ImageField(upload_to='profile_upload/',null=True,blank=True)

    def __str__(self):
        return self.user.username


