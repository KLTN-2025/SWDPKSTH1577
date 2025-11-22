from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

User = settings.AUTH_USER_MODEL
from django.urls import reverse




class Phong(models.Model):
    LOAI_PHONG_CHOICES = [
        ('standard', 'Phòng Standard'),
        ('deluxe', 'Phòng Deluxe'),
        ('suite', 'Phòng Suite'),
        ('family', 'Phòng Gia đình'),
    ]
    TRANG_THAI_CHOICES = [
        ('trong', 'Trống'),
        ('da_dat', 'Đã đặt'),
        ('dang_su_dung', 'Đang sử dụng'),
        ('bao_tri', 'Bảo trì'),
    ]
    ma_p = models.AutoField(primary_key=True)
    ten_p = models.CharField(max_length=50, unique=True)
    gia = models.FloatField(validators=[MinValueValidator(0)])
    loai_p = models.CharField(max_length=25, choices=LOAI_PHONG_CHOICES)
    chinh_sach_huy_p = models.TextField()
    mo_ta = models.TextField()
    anh_dai_dien = models.ImageField(upload_to='phong/')
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='trong')
    suc_chua = models.PositiveIntegerField(default=2)
    tien_ich = models.TextField(blank=True)

    def __str__(self):
        return f"{self.ten_p} - {self.get_loai_p_display()}"

    def get_absolute_url(self):
        return reverse('room_detail', kwargs={'pk': self.pk})
    
    @property
    def guest_range(self):
        return range(1, self.suc_chua + 1)  

class DichVu(models.Model):
    ma_dv = models.AutoField(primary_key=True)
    ten_dv = models.CharField(max_length=50)
    mo_ta = models.TextField()
    phi_dv = models.FloatField(validators=[MinValueValidator(0)])
    anh_dai_dien = models.ImageField(upload_to='dich_vu/')
    hoat_dong = models.BooleanField(default=True)

    def __str__(self):
        return self.ten_dv

class KhachHang(models.Model):
    ma_kh = models.AutoField(primary_key=True)
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ten_kh = models.CharField(max_length=50)
    sdt = models.CharField(max_length=10)
    email = models.EmailField()
    dia_chi = models.TextField()
    anh_dai_dien = models.ImageField(upload_to='khach_hang/', null=True, blank=True)
    ghi_chu = models.TextField(blank=True)

    def __str__(self):
        return self.ten_kh

class NhanVien(models.Model):
    GIOI_TINH_CHOICES = [
        ('Nam', 'Nam'),
        ('Nu', 'Nữ'),
        ('Khac', 'Khác'),
    ]
    TRANG_THAI_CHOICES = [
        ('dang_lam', 'Đang làm'),
        ('nghi_viec', 'Nghỉ việc'),
        ('nghi_phep', 'Nghỉ phép'),
    ]
    VI_TRI_CHOICES = [
        ('le_tan', 'Lễ tân'),
        ('buong_phong', 'Buồng phòng'),
        ('phuc_vu', 'Phục vụ'),
        ('quan_ly', 'Quản lý'),
        ('ky_thuat', 'Kỹ thuật'),
    ]
    ma_nv = models.AutoField(primary_key=True)
    tai_khoan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    ten_nv = models.CharField(max_length=50)
    gioi_tinh = models.CharField(max_length=10, choices=GIOI_TINH_CHOICES)
    sdt = models.CharField(max_length=10)
    email = models.EmailField()
    dia_chi = models.TextField()
    vi_tri = models.CharField(max_length=30, choices=VI_TRI_CHOICES)
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='dang_lam')
    ngay_vao_lam = models.DateField()
    anh_dai_dien = models.ImageField(upload_to='nhan_vien/', null=True, blank=True)

    def __str__(self):
        return self.ten_nv

class LichLamViec(models.Model):
    CA_LAM_CHOICES = [
        ('sang', 'Ca sáng (6h30-11h)'),
        ('chieu', 'Ca chiều (11h-17h)'),
        ('toi', 'Ca tối (17h-22h)'),
    ]
    ma_lich = models.AutoField(primary_key=True)
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE)
    ngay_lam = models.DateField()
    ca_lam = models.CharField(max_length=20, choices=CA_LAM_CHOICES)
    ghi_chu = models.TextField(blank=True)

    class Meta:
        unique_together = ('nhan_vien', 'ngay_lam', 'ca_lam')

    def __str__(self):
        return f"{self.nhan_vien.ten_nv} - {self.ngay_lam} - {self.get_ca_lam_display()}"


class MaGiamGia(models.Model):
    ma_code = models.CharField(max_length=20, unique=True)
    phan_tram_giam = models.PositiveIntegerField(
        default=0, 
        validators=[MaxValueValidator(100)], 
        help_text="Nhập số % giảm (VD: 10 là 10%)"
    )
    so_tien_giam = models.FloatField(default=0, help_text="Giảm số tiền cố định (VNĐ)")
    ngay_bat_dau = models.DateField()
    ngay_ket_thuc = models.DateField()
    so_luong = models.PositiveIntegerField(default=100)
    trang_thai = models.BooleanField(default=True)

    def __str__(self):
        return self.ma_code

    def is_valid(self):
        from django.utils import timezone
        today = timezone.now().date()
        return (self.trang_thai and 
                self.so_luong > 0 and 
                self.ngay_bat_dau <= today <= self.ngay_ket_thuc)

class DonDatPhong(models.Model):
    TRANG_THAI_CHOICES = [
        ('cho_xac_nhan', 'Chờ xác nhận'),
        ('da_xac_nhan', 'Đã xác nhận'),
        ('da_checkin', 'Đã check-in'),
        ('da_checkout', 'Đã check-out'),
        ('da_huy', 'Đã hủy'),
    ]
    ma_ddp = models.AutoField(primary_key=True)
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.CASCADE)
    phong = models.ForeignKey(Phong, on_delete=models.CASCADE)
    ngay_dat = models.DateTimeField(auto_now_add=True)
    ngay_nhan = models.DateField()
    ngay_tra = models.DateField()
    so_luong_nguoi = models.PositiveIntegerField(default=1)
    gia_ddp = models.FloatField(validators=[MinValueValidator(0)])
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='cho_xac_nhan')
    ghi_chu = models.TextField(blank=True)
    da_thanh_toan = models.BooleanField(default=False)
    paypal_order_id = models.CharField(max_length=255, blank=True, null=True)
    ma_giam_gia = models.ForeignKey(MaGiamGia, on_delete=models.SET_NULL, null=True, blank=True)
    tong_tien_thuc_te = models.FloatField(default=0, help_text="Số tiền sau khi giảm giá")

    def save(self, *args, **kwargs):
        # Logic tính lại tiền nếu chưa có tong_tien_thuc_te
        if not self.tong_tien_thuc_te:
            self.tong_tien_thuc_te = self.gia_ddp
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Đặt phòng #{self.ma_ddp} - {self.khach_hang.ten_kh}"

class DonDatDichVu(models.Model):
    ma_ddv = models.AutoField(primary_key=True)
    don_dat_phong = models.ForeignKey(DonDatPhong, on_delete=models.CASCADE)
    dich_vu = models.ForeignKey(DichVu, on_delete=models.CASCADE)
    ngay_su_dung = models.DateField()
    gio_su_dung = models.TimeField()
    so_luong = models.PositiveIntegerField(default=1)
    thanh_tien = models.FloatField(validators=[MinValueValidator(0)])
    ghi_chu = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.thanh_tien = self.dich_vu.phi_dv * self.so_luong
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.don_dat_phong} - {self.dich_vu.ten_dv}"

class YeuCau(models.Model):
    LOAI_YC_CHOICES = [
        ('buong_phong', 'Buồng phòng'),
        ('ky_thuat', 'Kỹ thuật'),
        ('phuc_vu', 'Phục vụ'),
        ('le_tan', 'Lễ tân'),
        ('khac', 'Khác'),
    ]
    TINH_TRANG_CHOICES = [
        ('cho_phan_cong', 'Chưa phân công'),
        ('da_phan_cong', 'Đã phân công'),
        ('dang_xu_ly', 'Đang xử lý'),
        ('da_xu_ly', 'Đã xử lý'),
        ('da_huy', 'Đã hủy'),
    ]
    ma_yc = models.AutoField(primary_key=True)
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True)
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.CASCADE)
    phong = models.ForeignKey(Phong, on_delete=models.CASCADE)
    loai_yc = models.CharField(max_length=20, choices=LOAI_YC_CHOICES)
    noi_dung_yc = models.TextField()
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
    tinh_trang = models.CharField(max_length=30, choices=TINH_TRANG_CHOICES, default='cho_phan_cong')
    thoi_gian_hoan_thanh = models.DateTimeField(null=True, blank=True)
    ghi_chu = models.TextField(blank=True)

    def __str__(self):
        return f"YC {self.ma_yc} - {self.get_loai_yc_display()}"

class PhanHoi(models.Model):
    TRANG_THAI_CHOICES = [
        ('moi', 'Mới'),
        ('dang_xu_ly', 'Đang xử lý'),
        ('da_xu_ly', 'Đã xử lý'),
    ]
    ma_ph = models.AutoField(primary_key=True)
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.CASCADE)
    tieu_de = models.CharField(max_length=100)
    noi_dung = models.TextField()
    ngay_tao = models.DateTimeField(auto_now_add=True)
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='moi')
    phan_hoi = models.TextField(blank=True)
    nhan_vien_phan_hoi = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Phản hồi {self.ma_ph} - {self.tieu_de}"

class HoaDon(models.Model):
    ma_hd = models.AutoField(primary_key=True)
    don_dat_phong = models.OneToOneField(DonDatPhong, on_delete=models.CASCADE)
    ngay_tao = models.DateTimeField(auto_now_add=True)
    tong_tien = models.FloatField(validators=[MinValueValidator(0)])
    da_thanh_toan = models.BooleanField(default=False)
    phuong_thuc_tt = models.CharField(max_length=50, blank=True)
    ghi_chu = models.TextField(blank=True)

    def __str__(self):
        return f"Hóa đơn #{self.ma_hd} - {self.don_dat_phong}"

class DangKyNhanTin(models.Model):
    email = models.EmailField(unique=True, verbose_name="Địa chỉ email")
    ngay_dang_ky = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đăng ký")

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Đăng ký nhận tin"
        verbose_name_plural = "Danh sách đăng ký nhận tin"
        