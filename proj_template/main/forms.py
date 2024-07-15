from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .validators import CustomPasswordValidator
from django.contrib.auth.forms import PasswordResetForm

class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        
        # Apply custom password validation
        validator = CustomPasswordValidator()
        validator.validate(password1)
        
        return password2

class CustomPasswordResetForm(PasswordResetForm):
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        CustomPasswordValidator(password1)
        return password1