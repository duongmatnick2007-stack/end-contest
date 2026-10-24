"""
========================================================================================
DỰ ÁN MACHINE LEARNING: DỰ ĐOÁN GIÁ CĂN HỘ CHUNG CƯ TẠI HÀ NỘI
MODULE: THU THẬP DỮ LIỆU TỰ ĐỘNG (DATA CRAWLING) TỪ CHỢ TỐT API
========================================================================================
Mục tiêu module:
- Khai thác trực tiếp Gateway API chính thức của Chợ Tốt để lấy dữ liệu dạng JSON.
- Thu thập dữ liệu căn hộ chung cư bán tại Hà Nội với đầy đủ: Giá, diện tích, 
  số phòng ngủ, toilet, toạ độ GPS (lat/long) và địa chỉ hành chính (quận/phường).
- Tổ chức và lưu trữ dữ liệu dạng bảng (Tabular Data) ra file CSV chuẩn UTF-8.
========================================================================================
"""

import os            # Thư viện tương tác với hệ điều hành (quản lý đường dẫn thư mục, file)
import sys           # Thư viện hệ thống (dùng cấu hình hiển thị tiếng Việt trên Terminal)
import time          # Thư viện thời gian (dùng để tạo độ trễ giữa các request tránh spam server)
import requests      # Thư viện chuyên gửi yêu cầu HTTP (GET, POST) tới web server
import pandas as pd  # Thư viện xử lý dữ liệu dạng bảng hàng đầu trong Khoa học Dữ liệu

# Cấu hình encoding chuẩn UTF-8 cho Terminal Windows để in tiếng Việt có dấu không bị lỗi font
sys.stdout.reconfigure(encoding='utf-8')

# ========================================================================================
# 1. CẤU HÌNH ĐƯỜNG DẪN VÀ THAM SỐ TOÀN CỤC (GLOBAL CONFIGURATION)
# ========================================================================================

# Lấy đường dẫn thư mục chứa file code hiện tại (d:\end-contest)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Tạo đường dẫn thư mục con 'data' để chứa dữ liệu
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)  # exist_ok=True: Nếu thư mục đã có rồi thì không báo lỗi

# Đường dẫn file CSV lưu trữ dữ liệu thô ban đầu
OUTPUT_CSV_PATH = os.path.join(DATA_DIR, 'raw_apartments_hanoi.csv')

# Endpoint API nội bộ của Chợ Tốt (trả về dữ liệu dạng JSON sạch sẽ, tốc độ cao)
CHOTOT_API_URL = "https://gateway.chotot.com/v1/public/ad-listing"

# HTTP Headers: Giả lập một trình duyệt Chrome thực thụ gửi yêu cầu.
# Rất nhiều web server sẽ từ chối request (lỗi 403) nếu không có User-Agent hợp lệ.
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',  # Báo cho server biết ta mong muốn nhận dữ liệu JSON
    'Origin': 'https://nha.chotot.com',             # Giả lập nguồn gửi từ trang Nhà Tốt
    'Referer': 'https://nha.chotot.com/',           # Giả lập trang giới thiệu trước đó
}

# ========================================================================================
# 2. HÀM THU THẬP DỮ LIỆU TỪ CHỢ TỐT API
# ========================================================================================

def crawl_chotot_data(max_items=2000, delay_seconds=0.6):
    """
    Hàm thực hiện cào dữ liệu danh sách tin bán căn hộ chung cư tại Hà Nội.
    
    Tham số:
        max_items (int): Số lượng tin tối đa cần thu thập (mặc định 2000 tin).
        delay_seconds (float): Thời gian nghỉ (giây) giữa 2 lần gửi request liên tiếp.
                               Giúp hạn chế rủi ro bị server tạm khoá IP do gửi request quá nhanh.
                               
    Trả về:
        pd.DataFrame: Bảng dữ liệu chứa toàn bộ các tin đã thu thập.
    """
    print("=" * 75)
    print("BẮT ĐẦU QUÁ TRÌNH THU THẬP DỮ LIỆU CĂN HỘ CHUNG CƯ HÀ NỘI TỪ CHỢ TỐT API")
    print("=" * 75)
    
    # Danh sách để gom tất cả các bản ghi (mỗi bản ghi là 1 dictionary)
    collected_records = []
    
    # Chợ Tốt API phân trang dựa trên Offset (o) và Limit (limit):
    # - limit: Số lượng tin tối đa muốn lấy trong 1 lần gọi (tối đa Chợ Tốt cho phép là 50).
    # - offset (o): Vị trí bắt đầu lấy tin (ví dụ: o=0 lấy từ tin 0->49, o=50 lấy từ tin 50->99).
    limit = 50
    offset = 0

    while len(collected_records) < max_items:
        # Bộ tham số gửi kèm trong URL (Query Parameters):
        params = {
            'region_v2': 12000,   # Mã định danh khu vực của Hà Nội trong cơ sở dữ liệu Chợ Tốt
            'cg': 1010,           # Mã phân loại Category Group: 1010 là "Căn hộ / Chung cư"
            'st': 's,k',          # Trạng thái tin: 's,k' = Mua bán (loại bỏ hoàn toàn tin cho thuê)
            'limit': limit,       # Lấy 50 tin mỗi trang
            'o': offset           # Dịch chuyển offset qua từng vòng lặp
        }

        try:
            # Gửi request HTTP GET tới server Chợ Tốt
            response = requests.get(
                CHOTOT_API_URL, 
                headers=REQUEST_HEADERS, 
                params=params, 
                timeout=10  # Nếu sau 10 giây server không phản hồi thì tự ngắt để tránh treo code
            )

            # Kiểm tra mã trạng thái HTTP (200 nghĩa là request thành công)
            if response.status_code != 200:
                print(f"[-] Server trả về mã lỗi HTTP {response.status_code} tại offset {offset}. Dừng cào.")
                break

            # Chuyển đổi dữ liệu thô trả về từ chuỗi JSON sang đối tượng Python (dict)
            json_data = response.json()
            
            # Lấy danh sách các bài đăng trong trường 'ads'
            ads_list = json_data.get('ads', [])
            total_available = json_data.get('total', 0)  # Tổng số tin hiện có trên hệ thống

            # Nếu danh sách trả về rỗng, tức là đã cào hết dữ liệu có sẵn
            if not ads_list:
                print("[*] Đã duyệt đến trang cuối cùng của dữ liệu.")
                break

            # Duyệt qua từng tin đăng trong danh sách 50 tin vừa nhận
            for ad in ads_list:
                # Trích xuất có chọn lọc các trường thông tin cần thiết phục vụ cho bài toán ML:
                record = {
                    'list_id': ad.get('list_id'),                       # ID duy nhất của bài đăng (dùng để lọc trùng)
                    'title': ad.get('subject'),                         # Tiêu đề tin đăng (chứa từ khoá: view hồ, sổ đỏ, full đồ...)
                    'price': ad.get('price'),                           # GIÁ BÁN THỰC TẾ (Đơn vị: VNĐ, kiểu số nguyên)
                    'price_string': ad.get('price_string'),             # Giá hiển thị (ví dụ: '3,5 tỷ', '45 triệu/m²')
                    'area': ad.get('size'),                             # DIỆN TÍCH CĂN HỘ (Đơn vị: m²)
                    'rooms': ad.get('rooms'),                           # SỐ PHÒNG NGỦ
                    'toilets': ad.get('toilets'),                       # SỐ PHÒNG VỆ SINH
                    'district': ad.get('area_name'),                    # TÊN QUẬN / HUYỆN (Cầu Giấy, Nam Từ Liêm, Tây Hồ...)
                    'ward': ad.get('ward_name'),                        # TÊN PHƯỜNG / XÃ (Yên Hoà, Mễ Trì, Phú Thượng...)
                    'street': ad.get('street_name'),                    # TÊN ĐƯỜNG / PHỐ
                    'project_name': ad.get('project_name'),             # TÊN DỰ ÁN (Vinhomes Smart City, Imperia...)
                    'latitude': ad.get('latitude'),                     # VĨ ĐỘ GPS (dùng tính khoảng cách đến trung tâm Hà Nội)
                    'longitude': ad.get('longitude'),                   # KINH ĐỘ GPS (dùng tính khoảng cách đến trung tâm Hà Nội)
                    'furnishing': ad.get('furnishing_sell'),            # TÌNH TRẠNG NỘI THẤT (Đầy đủ, cơ bản, nhà thô)
                    'legal_document': ad.get('property_legal_document'), # PHÁP LÝ (Đã có sổ đỏ, đang chờ sổ, hợp đồng mua bán)
                    'direction': ad.get('direction'),                   # HƯỚNG NHÀ (Đông, Tây, Nam, Bắc...)
                    'post_date': ad.get('date'),                        # THỜI GIAN ĐĂNG TIN
                    'url': f"https://nha.chotot.com/{ad.get('list_id')}.htm"  # Link xem bài đăng gốc trên web
                }
                collected_records.append(record)

            # In tiến trình cào dữ liệu ra màn hình
            print(f"    [+] Offset {offset:4d} | Đã thu thập: {len(collected_records):4d}/{total_available} tin...")

            # Cập nhật offset để trang tiếp theo lấy 50 tin mới
            offset += limit
            if offset >= total_available:
                print("[*] Đã thu thập toàn bộ dữ liệu có sẵn trên hệ thống.")
                break

            # Tạo khoảng nghỉ giữa 2 request (Best Practice khi cào dữ liệu để không gây quá tải cho server)
            time.sleep(delay_seconds)

        except requests.exceptions.RequestException as req_err:
            print(f"[-] Lỗi kết nối mạng tại offset {offset}: {req_err}")
            break
        except Exception as err:
            print(f"[-] Lỗi không xác định tại offset {offset}: {err}")
            break

    print(f"\n[+] Hoàn thành cào dữ liệu. Tổng số tin thu thập được: {len(collected_records)}")
    
    # Chuyển đổi danh sách các dictionary thành một Pandas DataFrame (bảng dữ liệu có dòng và cột)
    return pd.DataFrame(collected_records)

# ========================================================================================
# 3. HÀM CHÍNH THỰC THI (MAIN PIPELINE)
# ========================================================================================

def main():
    # 1. Gọi hàm cào dữ liệu
    df_raw = crawl_chotot_data(max_items=2000, delay_seconds=0.6)

    # 2. Kiểm tra nếu có dữ liệu thì tiến hành sơ chế và lưu trữ
    if not df_raw.empty:
        total_before = len(df_raw)
        
        # Loại bỏ các bài đăng bị trùng lặp dựa vào 'list_id' (giữ lại dòng đầu tiên xuất hiện)
        df_raw.drop_duplicates(subset=['list_id'], keep='first', inplace=True)
        total_after = len(df_raw)
        duplicates_removed = total_before - total_after
        
        print("\n" + "=" * 75)
        print("BÁO CÁO TỔNG QUAN TẬP DỮ LIỆU:")
        print("=" * 75)
        print(f"[+] Số tin thu thập được: {total_before} dòng")
        print(f"[+] Số tin trùng lặp đã loại bỏ: {duplicates_removed} dòng")
        print(f"[+] Số tin hợp lệ còn lại: {total_after} dòng")
        print(f"[+] Kích thước bảng (Shape): {df_raw.shape[0]} hàng x {df_raw.shape[1]} cột")

        # Lưu DataFrame ra file CSV:
        # - index=False: Không ghi thêm cột số thứ tự mặc định của pandas vào file
        # - encoding='utf-8-sig': Sử dụng UTF-8 with BOM giúp mở file trên Microsoft Excel 
        #   trên Windows không bao giờ bị vỡ font chữ tiếng Việt.
        df_raw.to_csv(OUTPUT_CSV_PATH, index=False, encoding='utf-8-sig')
        print(f"[+] Dữ liệu đã được lưu thành công vào file: {OUTPUT_CSV_PATH}")

        # In mẫu 3 dòng dữ liệu đầu tiên để kiểm tra
        print("\n[+] Mẫu 3 bản ghi đầu tiên:")
        display_cols = ['title', 'price', 'area', 'rooms', 'district', 'ward']
        print(df_raw[display_cols].head(3))

        # Thống kê phân bố số lượng tin theo từng Quận/Huyện
        print("\n[+] Top 5 Quận/Huyện có nhiều tin đăng nhất:")
        print(df_raw['district'].value_counts().head(5))

    else:
        print("[-] Không thu thập được dữ liệu nào. Vui lòng kiểm tra lại kết nối Internet.")

# Điểm khởi chạy của chương trình Python
if __name__ == '__main__':
    main()
