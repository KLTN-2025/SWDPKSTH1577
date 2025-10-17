import threading
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse

logger = logging.getLogger(__name__)

from .models import Phong, DangKyNhanTin

def send_bulk_email_in_thread(subject, html_message, recipient_list):
    try:
        logger.info(f"Bắt đầu gửi email hàng loạt đến {len(recipient_list)} người dùng...")
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Gửi email hàng loạt THÀNH CÔNG.")
    except Exception as e:
        logger.error(f"Gửi email hàng loạt THẤT BẠI. Lỗi: {e}")

import threading
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from .models import Phong, DangKyNhanTin

logger = logging.getLogger(__name__)

def send_bulk_email_in_thread(subject, html_message, recipient_list):
    """Gửi email hàng loạt trong luồng riêng để không làm chậm response."""
    try:
        logger.info(f"Bắt đầu gửi email hàng loạt đến {len(recipient_list)} người dùng...")
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Gửi email hàng loạt THÀNH CÔNG.")
    except Exception as e:
        logger.error(f"Gửi email hàng loạt THẤT BẠI. Lỗi: {e}")


@receiver(post_save, sender=Phong)
def send_email_on_new_room(sender, instance, created, **kwargs):
    """Tự động gửi email cho tất cả người đăng ký khi có phòng mới được tạo."""
    if not created:
        return

    logger.info(f"Phát hiện phòng mới: {instance.ten_p}. Kích hoạt gửi email hàng loạt.")

    subscribers = DangKyNhanTin.objects.values_list('email', flat=True)
    if not subscribers:
        logger.info("Không có người dùng nào đăng ký nhận tin.")
        return

    domain = getattr(settings, "SITE_DOMAIN", "http://127.0.0.1:8000")


    image_url = (
        f"{domain}{instance.anh_dai_dien.url}"
        if instance.anh_dai_dien
        else f"{domain}/static/default-room.jpg"
    )

    
    room_detail_url = f"{domain}{reverse('room_detail', args=[instance.pk])}"

   
    tieu_de_chinh = "🔥 Phòng Mới Siêu Hot Vừa Ra Mắt! 🔥"
    noi_dung_chinh = (
        f"Một lựa chọn tuyệt vời mới, phòng '{instance.ten_p}', đã có mặt tại khách sạn của chúng tôi. "
        f"Hãy là một trong những người đầu tiên trải nghiệm!"
    )

    context = {
        'tieu_de': tieu_de_chinh,
        'tieu_de_chinh': tieu_de_chinh,
        'noi_dung_chinh': noi_dung_chinh,
        'phong': instance,
        'image_url': image_url,
        'link_chi_tiet': room_detail_url,
    }

    subject = f"Phòng mới tại Khách sạn Crowne Plaza: {instance.ten_p}"
    html_message = render_to_string('emails/phong_notification.html', context)

    
    email_thread = threading.Thread(
        target=send_bulk_email_in_thread,
        args=(subject, html_message, list(subscribers))
    )
    email_thread.start()
