from django.db import models
from django.contrib.auth.models import User

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class Tags(models.Model):
    name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.name

class Blogpost(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(User, related_name='author_posts')
    tags = models.ManyToManyField(Tags, related_name='tag_posts')
    created_on = models.DateTimeField(auto_now_add=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    def __unicode__(self):
        return self.title