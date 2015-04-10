# django imports
from django.conf.urls import patterns, url

urlpatterns = patterns('lfs_io.views',
    url(r'^import$', "import_view", name='import'),
)
