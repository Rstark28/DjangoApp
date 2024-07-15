from django.core.exceptions import ValidationError
import re

class CustomPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least 1 uppercase letter.")
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least 1 number.")

    def get_help_text(self):
        return "Your password must contain at least 8 characters, 1 uppercase letter, and 1 number."
