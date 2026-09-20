from django.urls import path
from api.printable_template.views import PrintableTemplateUploadView, PrintableTemplateView

urlpatterns=[
    path(
    "upload/",
    PrintableTemplateUploadView.as_view(),
    ),
    path(
        "<str:template_name>/",
        PrintableTemplateView.as_view(),
    ),
]