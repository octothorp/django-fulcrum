from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.auth.models import User, Permission, Group
from blog.models import Blogpost
import sandbox
import fulcrum

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^srv/', include(fulcrum.site.urls)),
    url(r'^js$', 'blog.views.test_js'),
)

if sandbox.settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': sandbox.settings.MEDIA_URL}),
    )

auth = fulcrum.authentication.HttpBasicAuthentication(realm="My realm")
fulcrum.site.register(Blogpost, authentication=auth)
fulcrum.site.register(User, authentication=auth)
fulcrum.site.register(Permission, authentication=auth)
fulcrum.site.register(Group, authentication=auth)