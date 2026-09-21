from django.urls import path
from api.printable_template.views import PrintableTemplateUploadView, PrintableTemplateView, PrintableTemplateDeleteView, PrintableTemplateListView

urlpatterns=[
    path(
    "upload/",
    PrintableTemplateUploadView.as_view(),
    ),
    path(
        "<str:template_name>/",
        PrintableTemplateView.as_view(),
    ),

    path(
        "<str:template_name>/delete/",
        PrintableTemplateDeleteView.as_view(),
        name="printable-template-delete",
    ),

    path("",PrintableTemplateListView.as_view())
]