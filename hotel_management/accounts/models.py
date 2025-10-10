from django.db import models
from django.contrib.auth.models import AbstractUser

class TaiKhoan(AbstractUser):
    LOAI_TK_CHOICES = [
        ('admin', 'Quản trị viên'),
        ('nhan_vien', 'Nhân viên'),
        ('khach_hang', 'Khách hàng'),
    ]
    loai_tk = models.CharField(max_length=20, choices=LOAI_TK_CHOICES, default='khach_hang')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    sdt = models.CharField(max_length=10, blank=True, null=True)
    dia_chi = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username