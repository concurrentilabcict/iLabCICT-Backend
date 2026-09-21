import cloudinary.uploader

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.printable_template.models import PrintableTemplate
from api.printable_template.serializers import PrintableTemplateSerializer, PrintableTemplateReadSerializer

from api.permissions import IsAdmin, IsStaff

class PrintableTemplateListView(ListAPIView):
    permission_classes = [IsAuthenticated,
            IsAdmin]
    serializer_class = PrintableTemplateReadSerializer
    queryset = PrintableTemplate.objects.all()

class PrintableTemplateDeleteView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def delete(self, request, template_name):
        template = PrintableTemplate.objects.filter(
            name=template_name
        ).first()

        if not template:
            return Response(
                {
                    "detail": "Printable template not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if template.cloudinary_public_id:
            cloudinary.uploader.destroy(
                template.cloudinary_public_id,
                resource_type="image",
            )

        template.delete()

        return Response(
            {
                "detail": "Printable template deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT,
        )

class PrintableTemplateUploadView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def post(self, request):
        serializer = PrintableTemplateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        file = serializer.validated_data["file"]
        name = serializer.validated_data["name"]

        public_id = (
            f"ilabcict/printable-templates/{name}"
        )

        upload_result = cloudinary.uploader.upload(
            file,
            public_id=public_id,
            resource_type="image",
            overwrite=True,
        )

        template, _ = PrintableTemplate.objects.update_or_create(
            name=name,
            defaults={
                "template_url": upload_result["secure_url"],
                "cloudinary_public_id": upload_result["public_id"],
                "is_active": True,
                "updated_by": request.user,
            },
        )

        return Response(
            {
                "id": template.id,
                "name": template.name,
                "template_url": template.template_url,
                "cloudinary_public_id": (
                    template.cloudinary_public_id
                ),
                "is_active": template.is_active,
                "updated_at": template.updated_at,
                "created_at": template.created_at
            },
            status=status.HTTP_200_OK,
        )

class PrintableTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, template_name):
        template = PrintableTemplate.objects.filter(
            name=template_name,
            is_active=True,
        ).first()

        if not template:
            return Response(
                {
                    "detail": "Printable template not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PrintableTemplateReadSerializer(template)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )