from rest_framework import serializers
from api.printable_template.models import PrintableTemplate
class PrintableTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)

    file = serializers.FileField()

    def validate_file(self, value):
        if value.content_type != "application/pdf":
            raise serializers.ValidationError(
                "Only PDF files are allowed."
            )

        max_size = 10 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError(
                "PDF must be 10 MB or smaller."
            )

        return value

class PrintableTemplateReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintableTemplate
        fields = [
            "id",
            "name",
            "template_url",
            "is_active",
            "updated_at",
        ]