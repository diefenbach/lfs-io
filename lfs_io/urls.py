from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^import$', views.import_view, name='import'),
]
