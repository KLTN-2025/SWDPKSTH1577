from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import TaiKhoan

class TaiKhoanCreationForm(UserCreationForm):
    class Meta:
        model = TaiKhoan
        fields = ('username', 'email', 'loai_tk')

class TaiKhoanChangeForm(UserChangeForm):
    class Meta:
        model = TaiKhoan
        fields = ('username', 'email', 'loai_tk')

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = TaiKhoan
        fields = ['first_name', 'last_name', 'email', 'sdt', 'dia_chi', 'avatar']