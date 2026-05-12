from django.utils import timezone

def generate_entity_code(model, field_name, prefix="", digits=5):
    current_year = timezone.now().year

    last_obj = (
        model.objects
        .filter(**{
            f"{field_name}__startswith": f"{prefix}{current_year}"
        })
        .order_by("-id")
        .first()
    )

    if last_obj:
        last_code = getattr(last_obj, field_name)
        last_number = int(last_code[-digits:])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{current_year}{new_number:0{digits}d}"
