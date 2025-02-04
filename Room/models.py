from django.db import models
from codeEditor.models import File

class Room(models.Model):
    file = models.OneToOneField(File,on_delete=models.CASCADE,related_name='room')
    room_id = models.CharField(max_length=20,blank=True)

    def generateRoom(self, username, id, filename):
        room_id = f'{username}{id}{filename}'[:20]  # Truncate before assignment
        self.room_id = room_id
        self.save()
        return self.room_id



