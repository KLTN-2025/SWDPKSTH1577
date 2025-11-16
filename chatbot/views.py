# chatbot/views.py

from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
import json
import logging
import google.generativeai as genai
import re
import random 


from core.models import Phong, DichVu

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Bạn là một nhân viên tư vấn khách sạn chuyên nghiệp của khách sạn 5 sao Crowne Plaza.
Nhiệm vụ của bạn là hỗ trợ khách hàng đặt phòng, tư vấn dịch vụ, giải đáp thắc mắc về khách sạn và đưa ra gợi ý phù hợp với nhu cầu khách hàng.

YÊU CẦU:
- Luôn giao tiếp lịch sự, thân thiện, xưng hô "quý khách".
- Trả lời ngắn gọn, rõ ràng, nhưng đầy đủ thông tin cần thiết.
- Nếu khách hỏi về dịch vụ hoặc giá mà bạn không có dữ liệu, hãy nói: "Dạ để hỗ trợ tốt nhất, quý khách vui lòng để lại thông tin, nhân viên của chúng tôi sẽ liên hệ lại ngay ạ."
- Giữ phong cách chuyên nghiệp, sang trọng, giống như đang đại diện cho một khách sạn 5 sao.
- Khi tư vấn, hãy đề xuất thêm dịch vụ phù hợp (ví dụ: spa, phòng view biển, nhà hàng cao cấp trong khách sạn).
- Nếu khách hàng yêu cầu hoặc câu hỏi không liên quan đến khách sạn, lịch sự trả lời: "Dạ xin lỗi, tôi chỉ có thể hỗ trợ các thông tin liên quan đến khách sạn Crowne Plaza. Quý khách cần hỗ trợ thêm về dịch vụ của chúng tôi không ạ?"

THÔNG TIN VỀ KHÁCH SẠN:
- Tên khách sạn: Crowne Plaza Hotel
- Địa chỉ: 8 Võ Nguyên Giáp, Street, Ward, Thành phố Đà Nẵng
- Số điện thoại: 0702 664 640
- Email: info@crowneplaza.com
- Dịch vụ nổi bật: Hồ bơi vô cực, Spa cao cấp, Nhà hàng Á - Âu, Đưa đón sân bay miễn phí, Tour du lịch thành phố.
- Ảnh đại diện khách sạn: https://cf.bstatic.com/xdata/images/hotel/max1024x768/570617431.jpg?k=35a212392f47501ead2ce6d8c4e1d63ece6bd5178abe1156e90cac12cff200e9&o=&hp=1

QUY TẮC ĐẶC BIỆT:
- Khi khách hàng hỏi địa chỉ, vị trí hoặc hỏi khách sạn ở đâu, hãy trả lời bằng địa chỉ trong phần THÔNG TIN VỀ KHÁCH SẠN và BẮT BUỘC kèm theo ảnh của khách sạn bằng mã HTML sau: <img src="https://cf.bstatic.com/xdata/images/hotel/max1024x768/570617431.jpg?k=35a212392f47501ead2ce6d8c4e1d63ece6bd5178abe1156e90cac12cff200e9&o=&hp=1" alt="Ảnh khách sạn Crowne Plaza" style="max-width:100%; border-radius:10px; margin-top:10px;">
"""

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except AttributeError:
    logger.error("GEMINI_API_KEY not found in settings.py.")
    pass

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = None
try:
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash',
        safety_settings=safety_settings,
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)


# === BỘ NÃO GỢI Ý ===
SUGGESTIONS = {
    "after_room_list": [
        {'display': 'Phòng 2 người', 'value': 'Tìm phòng cho 2 người'},
        {'display': 'Xem phòng Deluxe', 'value': 'Phòng Deluxe giá bao nhiêu?'},
        {'display': 'Xem dịch vụ', 'value': 'Xem các dịch vụ của khách sạn'},
    ],
    "after_service_list": [
        {'display': 'Dịch vụ Spa', 'value': 'Giá dịch vụ Spa?'},
        {'display': 'Nhà hàng', 'value': 'Đặt bàn tại nhà hàng'},
        {'display': 'Xem lại phòng', 'value': 'Tôi muốn xem lại các phòng'},
    ],
    "default": [
        {'display': 'Các loại phòng', 'value': 'Xem các loại phòng'},
        {'display': 'Dịch vụ', 'value': 'Khách sạn có dịch vụ gì?'},
        {'display': 'Địa chỉ', 'value': 'Địa chỉ khách sạn ở đâu?'},
        {'display': 'Tư vấn', 'value': 'Tôi cần tư vấn đặt phòng'},
    ]
}

def get_random_suggestions(context_key, num=3):
   
    default_suggestions = SUGGESTIONS['default']
    context_suggestions = SUGGESTIONS.get(context_key, [])
    all_possible_suggestions = list({s['value']: s for s in context_suggestions + default_suggestions}.values())
    random.shuffle(all_possible_suggestions)
    return all_possible_suggestions[:num]

# --- CÁC HÀM HỖ TRỢ TRUY VẤN DATABASE---

def format_room_as_html(phong):
    """Định dạng thông tin một phòng thành chuỗi HTML."""
    image_url = phong.anh_dai_dien.url if phong.anh_dai_dien else '#'
    detail_url = reverse('room_detail', args=[phong.pk])
    html = f"""
    <div class='bot-card'>
        <img src='{image_url}' alt='{phong.ten_p}'/>
        <div class='bot-card-body'>
            <div class='bot-card-title'>{phong.ten_p} ({phong.get_loai_p_display()})</div>
            <div class='bot-card-price'>{phong.gia:,.0f} VNĐ/đêm</div>
            <div class='bot-card-text'>Sức chứa: {phong.suc_chua} người</div>
            <a href='{detail_url}' target='_blank' class='bot-card-button'>Xem chi tiết</a>
        </div>
    </div>
    """
    return html

# === HÀM ĐỊNH DẠNG CHO DỊCH VỤ ===
def format_service_as_html(service):
    """Định dạng thông tin một dịch vụ thành chuỗi HTML."""
    image_url = service.anh_dai_dien.url if service.anh_dai_dien else '#'
    
    detail_url = reverse('service_detail', args=[service.pk])
    html = f"""
    <div class='bot-card'>
        <img src='{image_url}' alt='{service.ten_dv}'/>
        <div class='bot-card-body'>
            <div class='bot-card-title'>{service.ten_dv}</div>
            <div class='bot-card-price'>Chỉ từ {service.phi_dv:,.0f} VNĐ</div>
            <p class='bot-card-text-truncate'>{service.mo_ta}</p>
            <a href='{detail_url}' target='_blank' class='bot-card-button'>Xem chi tiết</a>
        </div>
    </div>
    """
    return html

# --- CÁC HÀM LOGIC ---

def extract_booking_params(message):
    params = {}
    # 1. Tìm số người
    match_nguoi = re.search(r'(\d+)\s*(người|khách|ng)', message, re.IGNORECASE)
    if match_nguoi:
        params['suc_chua'] = int(match_nguoi.group(1))

    # 2. Tìm loại phòng
    room_types = ['standard', 'deluxe', 'suite', 'family', 'đơn', 'đôi', 'gia đình']
    for room_type in room_types:
        if room_type in message:
            params['loai_p'] = room_type
            break 
            
    return params

def tim_phong_trong_db(params):
    try:
        queryset = Phong.objects.filter(trang_thai='trong')
        
        loai_phong = params.get('loai_p', '')
        if loai_phong:
            if any(k in loai_phong.lower() for k in ['standard', 'thường']):
                queryset = queryset.filter(loai_p='standard')
            elif any(k in loai_phong.lower() for k in ['deluxe', 'cao cấp']):
                queryset = queryset.filter(loai_p='deluxe')
            elif 'suite' in loai_phong.lower():
                queryset = queryset.filter(loai_p='suite')
            elif any(k in loai_phong.lower() for k in ['family', 'gia đình']):
                queryset = queryset.filter(loai_p='family')
        suc_chua = params.get('suc_chua')
        if suc_chua:
            queryset = queryset.filter(suc_chua__gte=suc_chua)
        
        phong_tim_thay = list(queryset[:3])
        
        if not phong_tim_thay:
            reply = "Dạ thưa quý khách, hiện tại khách sạn đã hết loại phòng phù hợp với yêu cầu. Quý khách có muốn tham khảo các lựa chọn khác không ạ?"
        else:
            reply = "Dạ, Crowne Plaza đã tìm thấy một số phòng phù hợp với yêu cầu của quý khách:<br>"
            for phong in phong_tim_thay:
                reply += format_room_as_html(phong)
            if len(phong_tim_thay) < queryset.count():
                reply += "<br>Và còn nhiều lựa chọn khác ạ. Quý khách có thể cho tôi biết thêm yêu cầu chi tiết hơn không?"

        return {
            'reply': reply,
            'suggestions': get_random_suggestions('after_room_list')
        }
    except Exception as e:
        logger.error(f"Lỗi khi tìm phòng trong DB: {e}")
        return {
            'reply': "Dạ, đã có lỗi xảy ra trong quá trình tìm kiếm.",
            'suggestions': get_random_suggestions('default')
        }

def goi_y_phong_noi_bat():
    try:
        
        loai_phong_uu_tien = ['deluxe', 'suite', 'family']
        phongs_da_chon = {}
        phong_goi_y = Phong.objects.filter(trang_thai='trong', loai_p__in=loai_phong_uu_tien).order_by('loai_p')
        for phong in phong_goi_y:
            if phong.loai_p not in phongs_da_chon:
                phongs_da_chon[phong.loai_p] = phong
        phongs = list(phongs_da_chon.values())
        if not phongs:
            phongs = list(Phong.objects.filter(trang_thai='trong')[:3])

        if not phongs:
            reply = "Dạ hiện tại khách sạn đang cập nhật thông tin phòng ạ."
        else:
            reply = "Dạ đây là một vài gợi ý phòng nổi bật tại Crowne Plaza ạ:<br>"
            for phong in phongs:
                reply += format_room_as_html(phong)
        
        return {
            'reply': reply,
            'suggestions': get_random_suggestions('after_room_list')
        }
    except Exception as e:
        logger.error(f"Lỗi khi gợi ý phòng: {e}")
        return {
            'reply': "Dạ, tôi chưa thể tải được danh sách phòng lúc này, quý khách vui lòng thử lại sau ạ.",
            'suggestions': get_random_suggestions('default')
        }

# === HÀM DỊCH VỤ TRẢ VỀ CARD VÀ GỢI Ý ===
def tim_dich_vu_trong_db():
    try:
        services = DichVu.objects.filter(hoat_dong=True)[:3] # Lấy 3 dịch vụ nổi bật
        if not services:
            reply = "Dạ hiện tại khách sạn đang cập nhật thông tin dịch vụ ạ."
        else:
            reply = "Dạ, Crowne Plaza hân hạnh phục vụ quý khách các dịch vụ cao cấp sau:<br>"
            for dv in services:
                reply += format_service_as_html(dv)
        
        return {
            'reply': reply,
            'suggestions': get_random_suggestions('after_service_list')
        }
    except Exception as e:
        logger.error(f"Lỗi khi tìm dịch vụ: {e}")
        return {
            'reply': "Dạ, tôi chưa thể tải được danh sách dịch vụ lúc này, quý khách vui lòng thử lại sau ạ.",
            'suggestions': get_random_suggestions('default')
        }


# --- VIEW API CHÍNH ---
def chat_api(request):
    if not model:
        return JsonResponse({'error': 'Gemini model is not initialized.'}, status=503)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').lower()

            if not user_message:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)

            bot_response = {}

            # --- MỞ RỘNG KEYWORDS ---
            keywords_xem_phong = [
                'xem phòng', 'danh sách phòng', 'các loại phòng', 'gợi ý phòng', 
                'có phòng nào', 'check phòng', 'book phòng'
            ]
            keywords_dich_vu = [
                'dịch vụ', 'spa', 'nhà hàng', 'hồ bơi', 'gym', 'tiện ích', 
                'ăn uống', 'thư giãn'
            ]
            # --- LOẠI KEYWORD MỚI ---
            keywords_thong_tin_chung = [
                'địa chỉ', 'ở đâu', 'vị trí', 'liên hệ', 'số điện thoại', 'sdt',
                'email', 'chính sách', 'quy định', 'hủy phòng', 'check-in', 'check-out'
            ]
            
            # === BƯỚC 1: Ưu tiên rút trích thông tin đặt phòng cụ thể ===
            booking_params = extract_booking_params(user_message)
            
            if booking_params: # Nếu tìm thấy "2 người", "phòng deluxe"... -> Chắc chắn là muốn tìm phòng
                bot_response = tim_phong_trong_db(booking_params)
                return JsonResponse(bot_response)

            # === BƯỚC 2: Xét các từ khóa chung cho từng loại ý định ===
            if any(keyword in user_message for keyword in keywords_xem_phong):
                bot_response = goi_y_phong_noi_bat()
            
            elif any(keyword in user_message for keyword in keywords_dich_vu):
                bot_response = tim_dich_vu_trong_db()

            # === BƯỚC 3: Nếu là câu hỏi thông tin chung hoặc không khớp, dùng AI tổng quát ===
            # Quy tắc trong SYSTEM_PROMPT sẽ xử lý việc chèn ảnh khi hỏi địa chỉ
            else:
                response = model.generate_content(user_message)
                # Dùng gợi ý mặc định cho các câu trả lời chung
                suggestions_context = 'default'
                # Nếu câu trả lời có nhắc đến phòng/dịch vụ, ta có thể đổi ngữ cảnh gợi ý
                if any(kw in response.text.lower() for kw in ['phòng', 'suite', 'deluxe']):
                    suggestions_context = 'after_room_list'
                elif any(kw in response.text.lower() for kw in ['dịch vụ', 'spa', 'nhà hàng']):
                    suggestions_context = 'after_service_list'
                
                bot_response = {
                    'reply': response.text,
                    'suggestions': get_random_suggestions(suggestions_context)
                }

            return JsonResponse(bot_response)

        except Exception as e:
            logger.error(f"An unexpected error occurred in chat_api: {e}", exc_info=True)
            return JsonResponse({'error': 'An internal server error occurred.'}, status=500)

    return JsonResponse({'error': 'Only POST method is allowed'}, status=405)