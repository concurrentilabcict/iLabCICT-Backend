from django.urls import include, path
urlpatterns = [path("api/replication/", include("api.replication.urls"))]
