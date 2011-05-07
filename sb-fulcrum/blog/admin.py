from django.contrib import admin
from blog.models import Blogpost, Tags
admin.site.register(Blogpost)
admin.site.register(Tags)