from datetime import datetime

def is_invalid_date_format(value):
    try:
        datetime.strptime(str(value), '%Y-%m-%d')
        return False
    except ValueError:
        return True