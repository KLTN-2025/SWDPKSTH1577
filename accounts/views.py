from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, TaiKhoanCreationForm, UserProfileForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from core.models import KhachHang
from django.contrib.auth.models import User
from .models import TaiKhoan
from django.contrib.auth import get_user_model
from django.urls import reverse


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.is_superuser or user.loai_tk == 'admin':
                    return redirect('admin_dashboard')
                elif user.loai_tk == 'nhan_vien':
                    return redirect('nhan_vien_dashboard')
                else:
                    return redirect('home')
            else:
                form.add_error(None, 'Tên đăng nhập hoặc mật khẩu không đúng')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

def register_view(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        username = request.POST.get('username')
        password = request.POST.get('password')

        
        if not all([fullname, email, phone, address, username, password]):
            messages.error(request, 'Vui lòng điền đầy đủ thông tin')
            return redirect('register')
        if len(password) < 8:
            messages.error(request, 'Mật khẩu phải có ít nhất 8 ký tự')
            return redirect('register')
        
        if not (phone.isdigit() and len(phone) == 10):
            messages.error(request, 'Số điện thoại phải có đúng 10 chữ số')
            return redirect('register')
        
       
        User = get_user_model()

        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã tồn tại')
            return redirect('register')
        
        

       
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được đăng ký')
            return redirect('register')
        
        try:
           
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                loai_tk='khach_hang',  
                sdt=phone,
                dia_chi=address
            )

            

          
            KhachHang.objects.create(
                tai_khoan=user,
                ten_kh=fullname,
                sdt=phone,
                email=email,
                dia_chi=address
            )

            messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra: {str(e)}')
            return redirect('register')
    
    return render(request, 'accounts/register.html')

@login_required
def profile_view(request):
    if request.method == 'POST':
        
        pass
    return render(request, 'accounts/profile.html')

@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thông tin đã được cập nhật thành công!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})

def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  
            messages.success(request, 'Mật khẩu đã được thay đổi thành công!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})

