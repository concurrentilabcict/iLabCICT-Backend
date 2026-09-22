from django.db.models import Max, IntegerField
from django.db.models.functions import Cast, Substr

def generate_pc_local_code(model, room):

    last_number = (
        model.objects
        .filter(room=room)
        .annotate(
            pc_number=Cast(
                Substr("computer_number", 4),
                IntegerField()
            )
        )
        .aggregate(max_number=Max("pc_number"))
        ["max_number"]
    )

    next_number = (last_number or 0) + 1

    return f"PC-{next_number:02d}"



