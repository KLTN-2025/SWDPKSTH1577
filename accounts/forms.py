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
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'sdt': forms.TextInput(attrs={'class': 'form-control'}),
            'dia_chi': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'avatar': forms.FileInput(attrs={'id': 'id_avatar'}),
        }