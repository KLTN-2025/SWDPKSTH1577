from django.shortcuts import render , redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from .models import *
from .forms import *
from datetime import date, timedelta, datetime
from django.urls import reverse
from django.http import JsonResponse
import requests
import logging
logger = logging.getLogger(__name__)
import time
from decimal import Decimal
import json
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import DangKyNhanTinForm 
from .models import DangKyNhanTin 
import logging
logger = logging.getLogger(__name__)

timeout = settings.SESSION_COOKIE_AGE






def is_admin(user):
    return user.is_superuser or getattr(user, 'loai_tk', None) == 'admin'

def is_staff(user):
    return user.loai_tk == 'nhan_vien'

def is_customer(user):
    return user.loai_tk == 'khach_hang' and hasattr(user, 'khachhang')


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    
    total_rooms = Phong.objects.count()
    total_bookings = DonDatPhong.objects.count()
    total_customers = KhachHang.objects.count()
    total_services = DichVu.objects.count()
    
    
    recent_bookings = DonDatPhong.objects.order_by('-ngay_dat')[:5]
    
    
    pending_requests = YeuCau.objects.filter(tinh_trang='cho_phan_cong')[:5]
    
    
    new_feedbacks = PhanHoi.objects.filter(trang_thai='moi')[:3]
    
    context = {
        'total_rooms': total_rooms,
        'total_bookings': total_bookings,
        'total_customers': total_customers,
        'total_services': total_services,
        'recent_bookings': recent_bookings,
        'pending_requests': pending_requests,
        'new_feedbacks': new_feedbacks,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_room_management(request):
    rooms = Phong.objects.all().order_by('ma_p') 
    
    
    search_query = request.GET.get('search', '')
    room_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    
    if search_query:
        rooms = rooms.filter(Q(ten_p__icontains=search_query) | Q(mo_ta__icontains=search_query))
    
    if room_type:
        rooms = rooms.filter(loai_p=room_type)
    
    if status:
        rooms = rooms.filter(trang_thai=status)
    
    
    paginator = Paginator(rooms, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.method == 'POST':
        form = PhongForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm phòng mới")
            return redirect('admin_room_management')
    else:
        form = PhongForm()
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'search_query': search_query,
        'room_type': room_type,
        'status': status,
    }
    return render(request, 'admin/room_management.html', context)


@login_required
@user_passes_test(is_admin)
def edit_room(request, pk):
    room = get_object_or_404(Phong, pk=pk)
    
    if request.method == 'POST':
        form = PhongForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật thông tin phòng")
            return redirect('admin_room_management')
    else:
        form = PhongForm(instance=room)
    
    context = {
        'form': form,
        'room': room,
    }
    return render(request, 'admin/edit_room.html', context)


@login_required
@user_passes_test(is_admin)
def delete_room(request, pk):
    room = get_object_or_404(Phong, pk=pk)
    
    if request.method == 'POST':
        room.delete()
        messages.success(request, "Đã xóa phòng")
        return redirect('admin_room_management')
    
    context = {
        'room': room,
    }
    return render(request, 'admin/delete_room.html', context)


@login_required
@user_passes_test(is_admin)
def delete_staff(request, pk):
    staff = get_object_or_404(NhanVien, pk=pk)
    
    if request.method == 'POST':
        staff.delete()
        messages.success(request, "Đã xóa nhân viên")
        return redirect('admin_staff_management')
    
    return render(request, 'admin/delete_staff.html', {'staff': staff})


@login_required
def admin_booking_history(request):
    bookings = DonDatPhong.objects.all().order_by('-ngay_dat')
    return render(request, 'admin/booking_history.html', {'bookings': bookings})


@login_required
@user_passes_test(is_admin)
def admin_booking_management(request):
    bookings = DonDatPhong.objects.all().order_by('-ngay_dat')
    
    
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    
    if search_query:
        bookings = bookings.filter(
            Q(khach_hang__ten_kh__icontains=search_query) | 
            Q(phong__ten_p__icontains=search_query) |
            Q(ma_ddp=search_query)
        )
    if status:
        bookings = bookings.filter(trang_thai=status)
    
    
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status': status,
    }
    return render(request, 'admin/booking_management.html', context)



@login_required
@user_passes_test(is_admin)
def process_booking(request, pk):
    booking = get_object_or_404(DonDatPhong, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            booking.trang_thai = 'da_xac_nhan'
            booking.save()
            messages.success(request, "Đã xác nhận đặt phòng")
        elif action == 'checkin':
            booking.trang_thai = 'da_checkin'
            booking.phong.trang_thai = 'dang_su_dung'
            booking.phong.save()
            booking.save()
            messages.success(request, "Đã check-in khách")
        elif action == 'checkout':
            booking.trang_thai = 'da_checkout'
            booking.phong.trang_thai = 'trong'
            booking.phong.save()
            
            
            HoaDon.objects.create(
                don_dat_phong=booking,
                tong_tien=booking.gia_ddp,
                da_thanh_toan=False
            )
            booking.save()
            messages.success(request, "Đã check-out khách")
        elif action == 'cancel':
            booking.trang_thai = 'da_huy'
            booking.save()
            messages.success(request, "Đã hủy đặt phòng")
        
        return redirect('admin_booking_management')
    
    context = {
        'booking': booking,
    }
    return render(request, 'admin/process_booking.html', context)


@login_required
@user_passes_test(is_admin)
def admin_customer_management(request):
    customers = KhachHang.objects.all().order_by('-ma_kh')
    
    
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(ten_kh__icontains=search_query) | 
            Q(sdt__icontains=search_query) |
            Q(email__icontains=search_query))
    
    
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'admin/customer_management.html', context)


@login_required
@user_passes_test(is_admin)
def admin_staff_management(request):
    staff = NhanVien.objects.all().order_by('-ma_nv')
    
    
    search_query = request.GET.get('search', '')
    position = request.GET.get('position', '')
    status = request.GET.get('status', '')
    
    if search_query:
        staff = staff.filter(
            Q(ten_nv__icontains=search_query) | 
            Q(sdt__icontains=search_query) |
            Q(email__icontains=search_query))
    
    if position:
        staff = staff.filter(vi_tri=position)
    
    if status:
        staff = staff.filter(trang_thai=status)
    
    
    paginator = Paginator(staff, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.method == 'POST':
        form = NhanVienForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm nhân viên mới")
            return redirect('admin_staff_management')
    else:
        form = NhanVienForm()
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'search_query': search_query,
        'position': position,
        'status': status,
    }
    return render(request, 'admin/staff_management.html', context)

@login_required
@user_passes_test(is_admin)
def edit_staff(request, pk):
    staff = get_object_or_404(NhanVien, pk=pk)
    
    if request.method == 'POST':
        form = EditNhanVienForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            try:
             
                staff = form.save()

            
                new_password = request.POST.get('new_password')
                if new_password:
                    if len(new_password) < 8:
                        messages.error(request, "Mật khẩu phải có ít nhất 8 ký tự")
                    else:
                        staff.tai_khoan.set_password(new_password)
                        staff.tai_khoan.save()
                        messages.success(request, "Đã cập nhật mật khẩu")

                messages.success(request, "Đã cập nhật thông tin nhân viên")
                return redirect('admin_staff_management')
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra: {str(e)}")
        else:
            
            messages.error(request, "Vui lòng kiểm tra lại thông tin")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
    else:
        form = EditNhanVienForm(instance=staff)
    
    context = {
        'form': form,
        'staff': staff,
    }
    return render(request, 'admin/edit_staff.html', context)


from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Q

@login_required
@user_passes_test(is_admin)
def admin_schedule_management(request):
    
    today = timezone.now().date()
    year = request.GET.get('year', today.year)
    month = request.GET.get('month', today.month)
    
    try:
        year = int(year)
        month = int(month)
        current_date = date(year, month, 1)
    except (ValueError, TypeError):
        current_date = today.replace(day=1)
    
    
    prev_month = (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    
   
    first_day = current_date.replace(day=1)
    last_day = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
   
    weeks = []
    week = []
    
    
    start_weekday = first_day.weekday() 
    if start_weekday > 0:  
        week.extend([None] * start_weekday)
    
    day = first_day
    while day <= last_day:
        if len(week) == 7:  
            weeks.append(week)
            week = []
        week.append(day)
        day += timedelta(days=1)
    
    
    if week:
        weeks.append(week + [None] * (7 - len(week)))
    
    
    staff = NhanVien.objects.filter(trang_thai='dang_lam')
    schedules = LichLamViec.objects.filter(
        ngay_lam__range=[first_day, last_day]
    ).select_related('nhan_vien')
    
    if request.method == 'POST':
        form = LichLamViecForm(request.POST)
        if form.is_valid():
            try:
                
                existing = LichLamViec.objects.filter(
                    nhan_vien=form.cleaned_data['nhan_vien'],
                    ngay_lam=form.cleaned_data['ngay_lam'],
                    ca_lam=form.cleaned_data['ca_lam']
                ).exists()
                
                if existing:
                    messages.error(request, "Nhân viên đã có lịch làm việc này")
                else:
                    form.save()
                    messages.success(request, "Đã thêm lịch làm việc")
                    return redirect('admin_schedule_management')
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LichLamViecForm(initial={'ngay_lam': today})
    
    context = {
        'current_date': current_date,
        'prev_month': prev_month,
        'next_month': next_month,
        'weeks': weeks,  
        'staff': staff,
        'schedules': schedules,
        'form': form,
    }
    return render(request, 'admin/schedule_management.html', context)


@login_required
@user_passes_test(is_admin)
def delete_schedule(request, pk):
    schedule = get_object_or_404(LichLamViec, pk=pk)
    
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, "Đã xóa lịch làm việc")
        return redirect('admin_schedule_management')
    
    context = {
        'schedule': schedule,
    }
    return render(request, 'admin/delete_schedule.html', context)



@login_required
@user_passes_test(is_admin)
def admin_request_management(request):
    requests = YeuCau.objects.all().order_by('-ngay_tao')
    
    
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        requests = requests.filter(
            Q(ma_yc__icontains=search_query) |
            Q(khach_hang__ten_kh__icontains=search_query) |
            Q(phong__ten_p__icontains=search_query) |
            Q(noi_dung_yc__icontains=search_query)
        )
    
    if status_filter:
        requests = requests.filter(tinh_trang=status_filter)
    
    
    paginator = Paginator(requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'admin/request_management.html', context)


@login_required
@user_passes_test(is_admin)
def process_request(request, pk):
    yeu_cau = get_object_or_404(YeuCau, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        staff_id = request.POST.get('staff')
        
        if action == 'assign':
            if staff_id:
                staff = get_object_or_404(NhanVien, pk=staff_id)
                yeu_cau.nhan_vien = staff
                yeu_cau.tinh_trang = 'da_phan_cong'
                yeu_cau.save()
                messages.success(request, f"Đã phân công cho {staff.ten_nv}")
            else:
                messages.error(request, "Vui lòng chọn nhân viên")
        elif action == 'complete':
            yeu_cau.tinh_trang = 'da_xu_ly'
            yeu_cau.thoi_gian_hoan_thanh = timezone.now()
            yeu_cau.save()
            messages.success(request, "Đã đánh dấu hoàn thành")
        elif action == 'cancel':
            yeu_cau.tinh_trang = 'da_huy'
            yeu_cau.save()
            messages.success(request, "Đã hủy yêu cầu")
        
        return redirect('admin_request_management')
    
    available_staff = NhanVien.objects.filter(trang_thai='dang_lam')
    
    context = {
        'yeu_cau': yeu_cau,
        'available_staff': available_staff,
    }
    return render(request, 'admin/process_request.html', context)


@login_required
@user_passes_test(is_admin)
def admin_feedback_management(request):
    feedbacks = PhanHoi.objects.all().order_by('-ngay_tao')
    

    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if search_query:
        feedbacks = feedbacks.filter(
            Q(khach_hang__ten_kh__icontains=search_query) | 
            Q(tieu_de__icontains=search_query) |
            Q(noi_dung__icontains=search_query))
    
    if status:
        feedbacks = feedbacks.filter(trang_thai=status)
    
    
    paginator = Paginator(feedbacks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status': status,
    }
    return render(request, 'admin/feedback_management.html', context)


@login_required
@user_passes_test(is_admin)
def process_feedback(request, pk):
    feedback = get_object_or_404(PhanHoi, pk=pk)
    
    if request.method == 'POST':
        form = PhanHoiXuLyForm(request.POST, instance=feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.nhan_vien_phan_hoi = request.user.nhanvien
            feedback.save()
            messages.success(request, "Đã cập nhật phản hồi")
            return redirect('admin_feedback_management')
    else:
        form = PhanHoiXuLyForm(instance=feedback)
    
    context = {
        'feedback': feedback,
        'form': form,
    }
    return render(request, 'admin/process_feedback.html', context)



@login_required
def admin_support_management(request):
    requests = YeuCau.objects.all().order_by('-ngay_tao')
    return render(request, 'admin/support_management.html', {'requests': requests})


@login_required
@user_passes_test(is_admin)
def admin_service_booking(request):
    service_bookings = DonDatDichVu.objects.all().order_by('-ngay_su_dung')

    
    all_services = DichVu.objects.all()
    
    
    search_query = request.GET.get('search', '')
    service_id = request.GET.get('service', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    if search_query:
        service_bookings = service_bookings.filter(
            Q(don_dat_phong__khach_hang__ten_kh__icontains=search_query) | 
            Q(dich_vu__ten_dv__icontains=search_query) |
            Q(don_dat_phong__phong__ten_p__icontains=search_query))
        
    if service_id:
        service_bookings = service_bookings.filter(dich_vu__ma_dv=service_id)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            service_bookings = service_bookings.filter(ngay_su_dung__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            service_bookings = service_bookings.filter(ngay_su_dung__lte=end_date)
        except ValueError:
            pass
    
    
    paginator = Paginator(service_bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'all_services': all_services,
        'search_query': search_query,
    }
    return render(request, 'admin/service_booking.html', context)

@login_required
@user_passes_test(is_admin)
def admin_service_management(request):
    services = DichVu.objects.all().order_by('-ma_dv')
    
    
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    if search_query:
        services = services.filter(
            Q(ten_dv__icontains=search_query) | 
            Q(mo_ta__icontains=search_query))
        
    if status == 'active':
        services = services.filter(hoat_dong=True)
    elif status == 'inactive':
        services = services.filter(hoat_dong=False)

    if min_price:
        try:
            services = services.filter(phi_dv__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            services = services.filter(phi_dv__lte=float(max_price))
        except ValueError:
            pass
    
    
    paginator = Paginator(services, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.method == 'POST':
        form = DichVuForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm dịch vụ mới")
            return redirect('admin_service_management')
    else:
        form = DichVuForm()
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'search_query': search_query,
    }
    return render(request, 'admin/service_management.html', context)


@login_required
@user_passes_test(is_admin)
def edit_service(request, pk):
    service = get_object_or_404(DichVu, pk=pk)
    
    if request.method == 'POST':
        form = DichVuForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật dịch vụ")
            return redirect('admin_service_management')
    else:
        form = DichVuForm(instance=service)
    
    context = {
        'form': form,
        'service': service,
    }
    return render(request, 'admin/edit_service.html', context)


@login_required
@user_passes_test(is_admin)
def delete_service(request, pk):
    service = get_object_or_404(DichVu, pk=pk)
    
    if request.method == 'POST':
        service.delete()
        messages.success(request, "Đã xóa dịch vụ")
        return redirect('admin_service_management')
    
    context = {
        'service': service,
    }
    return render(request, 'admin/delete_service.html', context)


def home(request):
    featured_rooms = Phong.objects.filter(trang_thai='trong')[:8]
    services = DichVu.objects.filter(hoat_dong=True)[:3]
    
    
    total_customers = KhachHang.objects.count()
    total_bookings = DonDatPhong.objects.count()
    total_rooms = Phong.objects.count()
    
    if request.method == 'POST' and 'search_rooms' in request.POST:
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        guests = request.POST.get('guests', 1)
        room_type = request.POST.get('room_type', '')
        
        
        return redirect('room_search') + f'?check_in={check_in}&check_out={check_out}&guests={guests}&room_type={room_type}'
    
    context = {
        'featured_rooms': featured_rooms,
        'services': services,
        'total_customers': total_customers,
        'total_bookings': total_bookings,
        'total_rooms': total_rooms,
    }
    return render(request, 'core/home.html', context)

def room_search(request):
    room_status = request.GET.get('room_status', 'trong')
    guests = request.GET.get('guests', 1)
    room_type = request.GET.get('room_type', '')

   
    rooms = Phong.objects.all()
    
    if room_status:
        rooms = rooms.filter(trang_thai=room_status)

    if guests:
        rooms = rooms.filter(suc_chua__gte=guests)
    
    if room_type:
        rooms = rooms.filter(loai_p=room_type)
    
    context = {
        'rooms': rooms,
        'room_status': room_status,
        'guests': guests,
        'room_type': room_type,
    }
    return render(request, 'core/room_search.html', context)


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(csrf_exempt, name='dispatch')
class RoomDetailView(View):
    def get(self, request, pk):
        room = get_object_or_404(Phong, pk=pk)
        context = {
            'room': room,
            'booking_success': False,
        }
        return render(request, 'core/room_detail.html', context)
    def post(self, request, pk):
        room = get_object_or_404(Phong, pk=pk)
        step = request.POST.get('step', '1')
        
        
        if not request.session.session_key:
            request.session.create()
            logger.debug(f"Created new session: {request.session.session_key}")
        
        if step == '1':
            try:
                check_in = request.POST.get('check_in')
                check_out = request.POST.get('check_out')
                
                if not check_in or not check_out:
                    return JsonResponse({'status': 'error', 'message': 'Vui lòng nhập đầy đủ ngày'})
                
                date_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                date_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                
                if date_out <= date_in:
                    return JsonResponse({'status': 'error', 'message': 'Ngày trả phòng phải sau ngày nhận phòng'})
                
                
                request.session['booking_data'] = {
                    'check_in': check_in,
                    'check_out': check_out,
                    'guests': request.POST.get('guests', 1),
                    'room_id': pk,
                    'timestamp': str(timezone.now())
                }
                request.session.modified = True
                request.session.save()

                logger.debug(f"Session saved with data: {request.session['booking_data']}")
                
                return JsonResponse({'status': 'success', 'session_key': request.session.session_key})
                
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Ngày không hợp lệ'})
        
        elif step == '2':
            
            if 'booking_data' not in request.session:
                logger.error(f"Session data missing. Existing keys: {list(request.session.keys())}")
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Phiên làm việc hết hạn. Vui lòng bắt đầu lại quá trình đặt phòng.'
                }, status=400)
            
            
            
            try:
                booking_data = request.session['booking_data']
                logger.debug(f"Retrieved booking data: {booking_data}")
                check_in = booking_data['check_in']
                check_out = booking_data['check_out']
                guests = booking_data['guests']
                
                if not request.user.is_authenticated:
                    return JsonResponse({'status': 'error', 'message': 'Vui lòng đăng nhập'}, status=401)
                
                if not hasattr(request.user, 'khachhang'):
                    return JsonResponse({'status': 'error', 'message': 'Không tìm thấy thông tin khách hàng'}, status=400)
                
                date_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                date_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                
                if date_out <= date_in:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Ngày trả phòng phải sau ngày nhận phòng'
                    }, status=400)
                total_vnd = room.gia * (date_out - date_in).days
                coupon_data = request.session.get('coupon_data')
                coupon_obj = None
                final_price = total_vnd

                if coupon_data:
                    try:
                        coupon_obj = MaGiamGia.objects.get(id=coupon_data['coupon_id'])
                        if coupon_obj.is_valid():
                            final_price = final_price - coupon_data['discount_amount']
                            coupon_obj.so_luong -= 1
                            coupon_obj.save()
                    except MaGiamGia.DoesNotExist:
                        pass
                
                
                booking = DonDatPhong.objects.create(
                    phong=room,
                    ngay_nhan=date_in,
                    ngay_tra=date_out,
                    so_luong_nguoi=guests,
                    khach_hang=request.user.khachhang,
                    gia_ddp=total_vnd,
                    tong_tien_thuc_te=final_price,
                    ma_giam_gia=coupon_obj,
                    trang_thai='cho_xac_nhan',
                )
                if 'coupon_data' in request.session:
                    del request.session['coupon_data']
                
            
                del request.session['booking_data']
                
                request.session.modified = True
                request.session.save()
                
                return JsonResponse({
                    'status': 'success',
                    'redirect_url': reverse('booking_detail', args=[booking.ma_ddp])
                })
                
            except Exception as e:
                logger.error(f"Booking error: {str(e)}", exc_info=True)
                return JsonResponse({
                    'status': 'error',
                    'message': f'Lỗi hệ thống: {str(e)}'
                }, status=500)


@login_required
@user_passes_test(is_admin)
def customer_detail(request, pk):
    customer = get_object_or_404(KhachHang, pk=pk)
    bookings = DonDatPhong.objects.filter(khach_hang=customer).order_by('-ngay_dat')
    
    context = {
        'customer': customer,
        'bookings': bookings,
    }
    return render(request, 'admin/customer_detail.html', context)


@login_required
@user_passes_test(is_customer)
def customer_bookings(request):
    if not hasattr(request.user, 'khachhang'):
        messages.error(request, "Tài khoản không có thông tin khách hàng")
        return redirect('home')
    
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-ngay_dat') 
    
    bookings = DonDatPhong.objects.filter(khach_hang=request.user.khachhang)
    
    
    if search_query:
        bookings = bookings.filter(
            Q(ma_ddp__icontains=search_query) |
            Q(phong__ten_p__icontains=search_query) |
            Q(phong__loai_p__icontains=search_query)
        )
    
    
    if sort_by in ['ngay_dat', '-ngay_dat']:
        bookings = bookings.order_by(sort_by)
    
    
    bookings = list(bookings)
    for i, booking in enumerate(bookings[:100], start=1):
        booking.like_rank = f"Top {i}"
    
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'core/customer_bookings.html', context)


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(DonDatPhong, pk=pk)
    
    
    if not (request.user.is_staff or booking.khach_hang.tai_khoan == request.user):
        messages.error(request, "Bạn không có quyền truy cập")
        return redirect('home')
    
    services = DonDatDichVu.objects.filter(don_dat_phong=booking)
    available_services = DichVu.objects.filter(hoat_dong=True)
    
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST.get('action')
            
            if action == 'add_service':
                try:
                   
                    print("POST data:", request.POST)
            
                    service_id = request.POST.get('service_id')
                    service_date = request.POST.get('service_date')
                    service_time = request.POST.get('service_time')
                    quantity = request.POST.get('quantity')
                    note = request.POST.get('note', '')

                   
                    print(f"Service ID: {service_id}, Date: {service_date}, Time: {service_time}, Quantity: {quantity}")
                
                
                    dich_vu = DichVu.objects.get(pk=service_id)
                    don_dat_dich_vu = DonDatDichVu(
                        don_dat_phong=booking,
                        dich_vu=dich_vu,
                        ngay_su_dung=service_date,
                        gio_su_dung=service_time,
                        so_luong=quantity,
                        thanh_tien=dich_vu.phi_dv * int(quantity),
                        ghi_chu=note
                    )
                    don_dat_dich_vu.full_clean()
                    don_dat_dich_vu.save()

                    print("Dịch vụ đã được thêm thành công!")
                    messages.success(request, "Đã thêm dịch vụ thành công")
                    return redirect('booking_detail', pk=pk)
                except DichVu.DoesNotExist:
                    messages.error(request, "Dịch vụ không tồn tại")
                except Exception as e:
                    print("Lỗi khi thêm dịch vụ:", str(e))
                    messages.error(request, f"Có lỗi xảy ra: {str(e)}")
                    
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error adding service: {str(e)}")
            
            elif action == 'cancel' and booking.trang_thai == 'cho_xac_nhan':
                booking.trang_thai = 'da_huy'
                booking.save()
                messages.success(request, "Đã hủy đặt phòng")
                return redirect('booking_detail', pk=pk)
    
    context = {
        'booking': booking,
        'services': services,
        'available_services': available_services,
    }
    return render(request, 'core/booking_detail.html', context)

@login_required
def booking_history(request):
    if not hasattr(request.user, 'khachhang'):
        return redirect('home')
    
    bookings = DonDatPhong.objects.filter(khach_hang=request.user.khachhang).order_by('-ngay_dat')
    return render(request, 'core/booking_history.html', {'bookings': bookings})


def service_list(request):
    search_query = request.GET.get('search', '')
    
    services = DichVu.objects.filter(hoat_dong=True)
    
    if search_query:
        services = services.filter(
            Q(ten_dv__icontains=search_query) | 
            Q(mo_ta__icontains=search_query) |
            Q(ma_dv__icontains=search_query)
        )
    
    paginator = Paginator(services, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'core/service_list.html', context)

def service_detail(request, pk):
    service = get_object_or_404(DichVu, pk=pk)
    context = {
        'service': service,
    }
    return render(request, 'core/service_detail.html', context)

@login_required
def send_feedback(request):
    if request.method == 'POST':
        form = PhanHoiForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.khach_hang = request.user.khachhang
            feedback.save()
            messages.success(request, "Cảm ơn phản hồi của bạn!")
            return redirect('home')
    else:
        form = PhanHoiForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/send_feedback.html', context)


@login_required
def create_request(request, booking_pk):
    booking = get_object_or_404(DonDatPhong, pk=booking_pk)
    
    if booking.khach_hang.tai_khoan != request.user:
        messages.error(request, "Bạn không có quyền truy cập")
        return redirect('home')
    
    if request.method == 'POST':
        form = YeuCauForm(request.POST)
        if form.is_valid():
            yeu_cau = form.save(commit=False)
            yeu_cau.khach_hang = request.user.khachhang
            yeu_cau.phong = booking.phong
            yeu_cau.save()
            messages.success(request, "Đã gửi yêu cầu hỗ trợ")
            return redirect('booking_detail', pk=booking_pk)
    else:
        form = YeuCauForm(initial={'phong': booking.phong})
    
    context = {
        'form': form,
        'booking': booking,
    }
    return render(request, 'core/create_request.html', context)

@login_required
@user_passes_test(is_admin)
def add_room(request):
    if request.method == 'POST':
        form = PhongForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm phòng mới")
            return redirect('admin_room_management')
    else:
        form = PhongForm()
    
    return render(request, 'admin/add_room.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def add_service(request):
    if request.method == 'POST':
        form = DichVuForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm dịch vụ mới")
            return redirect('admin_service_management')
    else:
        form = DichVuForm()
    
    return render(request, 'admin/add_service.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def add_staff(request):
    if request.method == 'POST':
        print("POST data:", request.POST)  
        print("FILES data:", request.FILES)  
        form = AddNhanVienForm(request.POST, request.FILES)
        print("Form is valid:", form.is_valid())  
        print("Form errors:", form.errors)  
        if form.is_valid():
            try:
                
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']

                user = TaiKhoan.objects.create_user(
                    username=username,
                    password=password,
                    loai_tk='nhan_vien',
                    email=form.cleaned_data['email']
                )

                
                
                print("Dữ liệu form:", form.cleaned_data)
                
                staff = form.save(commit=False)
                staff.tai_khoan = user
                print("Staff object before save:", staff.__dict__)
                staff.save() 
                print("Staff ID after save:", staff.ma_nv)
                messages.success(request, "Đã thêm nhân viên mới thành công")
                return redirect('admin_staff_management')  
            except Exception as e:
                messages.error(request, f"Lỗi khi thêm nhân viên: {str(e)}")
               
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error adding staff: {str(e)}")
        else:
           
            messages.error(request, "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AddNhanVienForm()
    
    
    return render(request, 'admin/add_staff.html',{'form': form})



@login_required
def customer_requests(request):
    if not hasattr(request.user, 'khachhang'):
        messages.error(request, "Bạn không có quyền truy cập")
        return redirect('home')
    
    
    confirmed_bookings = DonDatPhong.objects.filter(
        khach_hang=request.user.khachhang,
        trang_thai__in=['da_xac_nhan', 'da_checkin', 'da_checkout']
    ).order_by('-ngay_dat')
    
    context = {
        'bookings': confirmed_bookings
    }
    return render(request, 'core/customer_requests.html', context)


@login_required
def request_detail(request, booking_pk):
    booking = get_object_or_404(DonDatPhong, pk=booking_pk)
    
    
    if booking.khach_hang.tai_khoan != request.user:
        messages.error(request, "Bạn không có quyền truy cập")
        return redirect('home')
    
   
    requests = YeuCau.objects.filter(phong=booking.phong).order_by('-ngay_tao')
    print("Method:", request.method)
    if request.method == 'POST':
        print("POST data:", request.POST)
        form = YeuCauForm(request.POST)
        print("Form valid:", form.is_valid())  
        print("Form errors:", form.errors)  
        if form.is_valid():
            yeu_cau = form.save(commit=False)
            yeu_cau.khach_hang = request.user.khachhang
            yeu_cau.phong = booking.phong
            yeu_cau.save()
            messages.success(request, "Đã gửi yêu cầu thành công")
            return redirect('request_detail', booking_pk=booking_pk)
        else:
           
            messages.error(request, "Vui lòng kiểm tra lại thông tin")
    else:
        form = YeuCauForm()
    
    context = {
        'booking': booking,
        'requests': requests,
        'form': form
    }
    return render(request, 'core/request_detail.html', context)


@login_required
@user_passes_test(is_admin)
def edit_request(request, pk):
    yeu_cau = get_object_or_404(YeuCau, pk=pk)
    
    if request.method == 'POST':
        form = YeuCauForm(request.POST, instance=yeu_cau)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật yêu cầu thành công")
            return redirect('process_request', pk=pk)
    else:
        form = YeuCauForm(instance=yeu_cau)
    
    context = {'yeu_cau': yeu_cau, 'form': form}
    return render(request, 'admin/edit_request.html', context)

@login_required
@user_passes_test(is_admin)
def delete_request(request, pk):
    yeu_cau = get_object_or_404(YeuCau, pk=pk)
    
    if request.method == 'POST':
        yeu_cau.delete()
        messages.success(request, "Đã xóa yêu cầu thành công")
        return redirect('admin_request_management')
    
    return redirect('process_request', pk=pk)


@login_required
@user_passes_test(is_admin)
def edit_customer(request, pk):
    customer = get_object_or_404(KhachHang, pk=pk)
    
    if request.method == 'POST':
        form = KhachHangForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            customer = form.save()
            is_active = request.POST.get('is_active') == 'on'
            customer.tai_khoan.is_active = is_active
            new_password = request.POST.get('new_password')
            if new_password:
                if len(new_password) < 8:
                    messages.error(request, "Mật khẩu phải có ít nhất 8 ký tự")
                else:
                    customer.tai_khoan.set_password(new_password)
                    messages.success(request, "Đã cập nhật mật khẩu")
            customer.tai_khoan.save()
            messages.success(request, "Đã cập nhật thông tin khách hàng")
            return redirect('customer_detail', pk=pk)
    else:
        form = KhachHangForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
    }
    return render(request, 'admin/edit_customer.html', context)

@login_required
@user_passes_test(is_admin)
def delete_customer(request, pk):
    customer = get_object_or_404(KhachHang, pk=pk)
    
    if request.method == 'POST':
       
        user = customer.tai_khoan
        customer.delete()
        user.delete()
        messages.success(request, "Đã xóa khách hàng thành công")
        return redirect('admin_customer_management')
    
    return redirect('customer_detail', pk=pk)


def get_hot_rooms(request):
    try:
       
        hot_rooms = Phong.objects.filter(trang_thai='trong').order_by('?')
        
      
        room_data = []
        for room in hot_rooms:
            room_data.append({
                'name': room.ten_p,
                'room_type': room.get_loai_p_display(), 
                'image_url': room.anh_dai_dien.url if room.anh_dai_dien else '',
                'price': f"{room.gia:,.0f} VNĐ/đêm",
                'details_url': reverse('room_detail', args=[room.ma_p]),
            })
        
        return JsonResponse({'status': 'success', 'rooms': room_data})
    except Exception as e:
       
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


PAYPAL_CLIENT_ID = 'AUbh_JXsTbSU-qKuw2cR5TMVzTdMcFwFkEg9dTHEApigqGwaBFz1K19mmAMr9GWo-XA7P3sbfphMZZDo'
PAYPAL_SECRET = 'ENnasq6RpplLZhlodxG2Sea-YThmQxlgLJ7GDylhpJLDBMoO34RGzd28ClBGmuoEUjbkcWlu85LtM2mm'
PAYPAL_BASE_URL = 'https://api-m.sandbox.paypal.com' 

def get_paypal_access_token():
    """Lấy Access Token từ PayPal."""
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'en_US',
    }
    data = {'grant_type': 'client_credentials'}
    response = requests.post(
        f'{PAYPAL_BASE_URL}/v1/oauth2/token',
        headers=headers,
        data=data,
        auth=auth
    )
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        logger.error(f"Failed to get PayPal access token: {response.text}")
        return None


@login_required
def create_paypal_order(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ.'}, status=405)

    try:
       
        data = json.loads(request.body)
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        room_id = data.get('room_id')
        guests = data.get('guests', 1)

        if not check_in or not check_out or not room_id:
            return JsonResponse({'status': 'error', 'message': 'Thiếu dữ liệu đặt phòng.'}, status=400)

        
        room = get_object_or_404(Phong, pk=room_id)

        # Tính số đêm
        date_in = datetime.strptime(check_in, '%Y-%m-%d').date()
        date_out = datetime.strptime(check_out, '%Y-%m-%d').date()
        nights = (date_out - date_in).days

        if nights <= 0:
            return JsonResponse({'status': 'error', 'message': 'Ngày trả phòng phải sau ngày nhận phòng.'}, status=400)

        # Tính tổng tiền VND
        total_vnd = room.gia * nights
        if total_vnd <= 0:
            return JsonResponse({'status': 'error', 'message': 'Tổng tiền phải lớn hơn 0.'}, status=400)

        # Đổi sang USD
        exchange_rate = 26000 
        total_usd = Decimal(total_vnd) / Decimal(exchange_rate)

        if total_usd < Decimal("0.01"):
            total_usd = Decimal("0.01")

        total_usd_formatted = f"{total_usd:.2f}"

        logger.debug(f"Booking: room={room.ten_p}, nights={nights}, total_vnd={total_vnd}, total_usd={total_usd_formatted}")

       
        access_token = get_paypal_access_token()
        if not access_token:
            return JsonResponse({'status': 'error', 'message': 'Không thể kết nối tới PayPal.'}, status=500)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': 'USD',
                    'value': total_usd_formatted,
                }
            }]
        }

       
        response = requests.post(
            f'{PAYPAL_BASE_URL}/v2/checkout/orders',
            headers=headers,
            data=json.dumps(payload)
        )

        if response.status_code == 201:
            order_id = response.json().get('id')

           
            request.session['booking_data'] = {
                'check_in': check_in,
                'check_out': check_out,
                'guests': guests,
                'room_id': room_id,
                'total_vnd': total_vnd
            }
            request.session.modified = True

            return JsonResponse({'orderID': order_id})
        else:
            logger.error(f"PayPal create order failed: {response.text}")
            return JsonResponse({'status': 'error', 'message': 'Không thể tạo đơn hàng PayPal.'}, status=500)

    except Exception as e:
        logger.error(f"Lỗi trong create_paypal_order: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)




@login_required
def capture_paypal_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('orderID')
            
            if not order_id:
                return JsonResponse({'status': 'error', 'message': 'Không tìm thấy Order ID.'}, status=400)
            
            access_token = get_paypal_access_token()
            if not access_token:
                return JsonResponse({'status': 'error', 'message': 'Không thể kết nối đến PayPal.'}, status=500)
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
            }
            
            response = requests.post(
                f'{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture',
                headers=headers
            )
            
            if response.status_code == 201:
                paypal_response = response.json()
                if paypal_response['status'] == 'COMPLETED':
                   
                    booking_data = request.session.get('booking_data')
                    if not booking_data:
                        return JsonResponse({'status': 'error', 'message': 'Phiên đặt phòng đã hết hạn.'}, status=400)

                 
                    room = get_object_or_404(Phong, pk=booking_data['room_id'])
                    date_in = datetime.strptime(booking_data['check_in'], '%Y-%m-%d').date()
                    date_out = datetime.strptime(booking_data['check_out'], '%Y-%m-%d').date()

                    total_vnd = room.gia * (date_out - date_in).days
                    final_price = total_vnd
                    
                    coupon_data = request.session.get('coupon_data')
                    coupon_obj = None

                    if coupon_data:
                        try:
                            coupon_obj = MaGiamGia.objects.get(id=coupon_data['coupon_id'])
                            if coupon_obj.is_valid():
                                final_price = final_price - coupon_data['discount_amount']
                              
                                coupon_obj.so_luong -= 1
                                coupon_obj.save()
                        except MaGiamGia.DoesNotExist:
                            pass

                    booking = DonDatPhong.objects.create(
                        phong=room,
                        ngay_nhan=date_in,
                        ngay_tra=date_out,
                        so_luong_nguoi=booking_data['guests'],
                        khach_hang=request.user.khachhang,
                        gia_ddp=total_vnd,              # Giá gốc
                        tong_tien_thuc_te=final_price,  # Giá sau giảm
                        ma_giam_gia=coupon_obj,         # Mã coupon
                        trang_thai='da_xac_nhan', 
                        da_thanh_toan=True,
                        paypal_order_id=order_id
                    )
                    
                    if 'coupon_data' in request.session:
                        del request.session['coupon_data']
                    del request.session['booking_data']

                    return JsonResponse({
                        'status': 'success',
                        'message': 'Thanh toán thành công!',
                        'redirect_url': reverse('booking_detail', args=[booking.ma_ddp])
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': 'Giao dịch chưa hoàn tất.'}, status=400)
            else:
                logger.error(f"Failed to capture PayPal order: {response.text}")
                return JsonResponse({'status': 'error', 'message': 'Lỗi khi xác thực giao dịch.'}, status=500)
                
        except Exception as e:
            logger.error(f"Error in capture_paypal_order: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Lỗi hệ thống.'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ.'}, status=405)


@login_required
def nhan_vien_schedule_management(request):
    """
    Hiển thị lịch làm việc của nhân viên đang đăng nhập.
    """
    try:
        # Lấy thông tin nhân viên từ tài khoản user đang đăng nhập
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
        # Lọc lịch làm việc của nhân viên đó
        schedules = LichLamViec.objects.filter(nhan_vien=nhan_vien).order_by('-ngay_lam')
    except NhanVien.DoesNotExist:
        schedules = []

    context = {
        'schedules': schedules
    }
    return render(request, 'nhan_vien/schedule_management.html', context)

@login_required
def nhan_vien_request_management(request):
    """
    Hiển thị các yêu cầu được gán cho nhân viên đang đăng nhập.
    """
    try:
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
        # Lọc các yêu cầu được gán cho nhân viên đó
        requests = YeuCau.objects.filter(nhan_vien=nhan_vien).order_by('-ngay_tao')
    except NhanVien.DoesNotExist:
        requests = []

    context = {
        'requests': requests
    }
    return render(request, 'nhan_vien/request_management.html', context)


@login_required
def nhan_vien_dashboard(request):
    """
    View hiển thị trang dashboard cho nhân viên với các thông tin tổng quan.
    """
    context = {
        'schedules_today': [],
        'pending_requests_count': 0,
        'recent_requests': [],
        'nhan_vien_profile': None,
    }

    try:
      
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
        context['nhan_vien_profile'] = nhan_vien

        # 1. Lấy lịch làm việc hôm nay
        today = timezone.now().date()
        schedules_today = LichLamViec.objects.filter(nhan_vien=nhan_vien, ngay_lam=today)
        context['schedules_today'] = schedules_today

        # 2. Đếm số lượng yêu cầu đang chờ ("đã phân công") hoặc đang xử lý
        pending_statuses = ['da_phan_cong', 'dang_xu_ly']
        pending_requests_count = YeuCau.objects.filter(
            nhan_vien=nhan_vien,
            tinh_trang__in=pending_statuses
        ).count()
        context['pending_requests_count'] = pending_requests_count

        # 3. Lấy 5 yêu cầu gần nhất được giao
        recent_requests = YeuCau.objects.filter(nhan_vien=nhan_vien).order_by('-ngay_tao')[:5]
        context['recent_requests'] = recent_requests

    except NhanVien.DoesNotExist:
       
        pass

    return render(request, 'nhan_vien/dashboard.html', context)

def subscribe_newsletter(request):
    if request.method == 'POST':
        form = DangKyNhanTinForm(request.POST)
        if form.is_valid():
            form.save()
            email_address = form.cleaned_data.get('email')
            
            try:
                subject = 'Cảm ơn bạn đã đăng ký nhận tin từ Khách sạn Crowne Plaza!'
                context = {'email': email_address}
                html_message = render_to_string('emails/promotion_email.html', context)
                
                # --- LOGGING ---
                logger.info(f"Đang chuẩn bị gửi email chào mừng đến {email_address}...")
                
                send_mail(
                    subject, 
                    '', 
                    settings.DEFAULT_FROM_EMAIL, 
                    [email_address], 
                    html_message=html_message
                )

                # --- LOGGING ---
                logger.info(f"Gửi email chào mừng đến {email_address} THÀNH CÔNG.")
                messages.success(request, 'Đăng ký thành công! Vui lòng kiểm tra email của bạn.')
            
            except Exception as e:
                # --- LOGGING ---
                logger.error(f"Gửi email chào mừng đến {email_address} THẤT BẠI. Lỗi: {e}")
                messages.warning(request, 'Đăng ký thành công, nhưng chúng tôi gặp sự cố khi gửi email cho bạn.')

        else:
            error_msg = form.errors.get('email')[0] if form.errors.get('email') else "Dữ liệu không hợp lệ."
            messages.error(request, error_msg)
            
    return redirect(request.META.get('HTTP_REFERER', 'home'))



def check_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code')
        total_amount = float(request.POST.get('total_amount', 0))
        
        try:
            coupon = MaGiamGia.objects.get(ma_code=code)
            if coupon.is_valid():
                discount_amount = 0
                if coupon.phan_tram_giam > 0:
                    discount_amount = total_amount * (coupon.phan_tram_giam / 100)
                elif coupon.so_tien_giam > 0:
                    discount_amount = coupon.so_tien_giam
                
                
                discount_amount = min(discount_amount, total_amount)
                final_total = total_amount - discount_amount

               
                request.session['coupon_data'] = {
                    'code': code,
                    'discount_amount': discount_amount,
                    'coupon_id': coupon.id
                }
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Đã áp dụng mã giảm {discount_amount:,.0f} VNĐ',
                    'new_total': final_total,
                    'discount_amount': discount_amount
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Mã giảm giá đã hết hạn hoặc hết lượt dùng'})
        except MaGiamGia.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Mã giảm giá không tồn tại'})
            
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ'})



@login_required
@user_passes_test(is_admin)
def admin_coupon_management(request):
    coupons = MaGiamGia.objects.all().order_by('-id')
    
   
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if search_query:
        coupons = coupons.filter(ma_code__icontains=search_query)
    
    if status == 'active':
        coupons = coupons.filter(trang_thai=True)
    elif status == 'inactive':
        coupons = coupons.filter(trang_thai=False)

   
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    if request.method == 'POST':
        form = MaGiamGiaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã tạo mã giảm giá mới")
            return redirect('admin_coupon_management')
        else:
            messages.error(request, "Lỗi khi tạo mã. Vui lòng kiểm tra lại.")
    else:
        form = MaGiamGiaForm()

    context = {
        'page_obj': page_obj,
        'form': form,
        'search_query': search_query,
        'status': status
    }
    return render(request, 'admin/coupon_management.html', context)

@login_required
@user_passes_test(is_admin)
def edit_coupon(request, pk):
    coupon = get_object_or_404(MaGiamGia, pk=pk)
    if request.method == 'POST':
        form = MaGiamGiaForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật mã giảm giá")
            return redirect('admin_coupon_management')
    else:
        form = MaGiamGiaForm(instance=coupon)
    
    return render(request, 'admin/edit_coupon.html', {'form': form, 'coupon': coupon})

@login_required
@user_passes_test(is_admin)
def delete_coupon(request, pk):
    coupon = get_object_or_404(MaGiamGia, pk=pk)
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, "Đã xóa mã giảm giá")
        return redirect('admin_coupon_management')
    return render(request, 'admin/delete_coupon.html', {'coupon': coupon})
