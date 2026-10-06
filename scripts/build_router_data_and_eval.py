"""[R&D] Xây dựng tập dữ liệu huấn luyện UC022 từ TEMPLATE và khử trùng lặp gần giống.

Việc script này làm — mô tả đúng như code chạy:
1. Sinh câu train bằng TỔ HỢP TEMPLATE (``SLOTS`` + ``random.choice``, seed 42), KHÔNG gọi LLM,
   theo 6 văn phong: polite_full 25% · short_abbrev 25% · no_accent 20% · typo 15% ·
   en_mix 10% · emoji 5%, trên 7 ý định.
2. Để đủ chỉ tiêu 3.000 mẫu thô, script CHỦ ĐỘNG CHÈN bản sao gần giống của câu đã có
   (thêm từ đệm " ạ", " nhé"... hoặc khoảng trắng) — xem ``create_dataset_with_natural_duplicates``.
   Vì vậy tỉ lệ khử trùng lặp ở bước 3 là hệ quả của số bản sao được chèn, KHÔNG phải số đo
   về dữ liệu tự nhiên; không được trình bày như bằng chứng cho cảnh báo "~30% là bản sao".
3. Khử trùng lặp gần giống: Jaccard trên character 3-gram, ngưỡng 0,88, trong từng ý định.
4. Ghi SHA-256 tập sạch vào artifacts/DATA_HASHES.txt và phân bố vào reports/eval/.

Cohen's Kappa KHÔNG còn tính ở đây: phiên bản cũ tự dựng nhãn "Dev A" từ nhãn vàng cộng 13 ca
bất đồng viết cứng — đó là số liệu giả lập. Kappa thật đọc nhãn của hai người từ hai file
riêng: ``scripts/compute_annotation_kappa.py``.
"""

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

INTENTS = [
    "GREETING",
    "KB_SEARCH",
    "PRICING_POLICY",
    "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN",
    "TECH_ERROR",
    "BUYING_INTENT",
]

# 1. TỪ ĐIỂN TỔ HỢP CÂU VĂN BẢN ĐA DẠNG CHO 7 Ý ĐỊNH
SLOTS = {
    "GREETING": {
        "openings": ["Dạ em chào", "Kính chào", "Xin chào", "Chào bạn", "Chào anh chị", "Em chào", "Chào mừng"],
        "subjects": ["anh chị", "quý khách", "bạn", "quý công ty", "mọi người", "team", "bên mình"],
        "wishes": [
            "chúc một ngày tốt lành và nhiều niềm vui",
            "chúc anh chị ngày làm việc hiệu quả và thành công",
            "rất vui được hỗ trợ anh chị hôm nay",
            "chúc tuần mới nhiều may mắn và suôn sẻ",
            "em có thể hỗ trợ thông tin gì cho mình ạ",
            "chúc công việc kinh doanh luôn phát đạt",
            "rất hân hạnh được đồng hành cùng doanh nghiệp",
            "chúc buổi sáng an lành và ngập tràn năng lượng",
            "hy vọng mang lại giải pháp tối ưu cho công ty",
            "rất vui được đón tiếp quý khách ghé thăm",
        ],
        "short_actions": ["alo", "hi", "helo", "2", "chao", "he nho"],
        "short_targets": ["ad", "shop", "bot", "b", "cskh", "team", "crm"],
        "short_endings": ["nhe", "nha", "oi", "vs", "ne", "a", "di"],
        "en_openings": ["Good morning", "Good afternoon", "Hello", "Hi", "Greetings"],
        "en_targets": ["support team", "chatbot assistant", "CRM consultant", "customer service"],
        "en_closings": ["how can I help you today", "hope you have a productive day", "nice to connect with you", "need some quick assistance"],
    },
    "KB_SEARCH": {
        "actions": [
            "hướng dẫn em cách", "cho em hỏi quy trình", "làm sao để",
            "hệ thống có hỗ trợ", "phiền bạn chỉ giúp cách", "cách cấu hình",
            "tài liệu mô tả tính năng", "có thể thiết lập", "cho mình hỏi về cơ chế",
            "làm cách nào để kích hoạt", "các bước để thực hiện", "giải thích giúp em tính năng"
        ],
        "topics": [
            "đồng bộ dữ liệu tin nhắn từ Zalo Official Account",
            "tích hợp Webhook để nhận thông tin khách hàng từ landing page",
            "phân quyền nhân viên quản trị theo từng phòng ban và chi nhánh",
            "xuất báo cáo danh sách khách hàng ra tệp tin Excel định kỳ",
            "cấu hình kịch bản chatbot tự động trả lời theo từ khóa thông minh",
            "tự động chia lead mới cho nhân viên kinh doanh theo lượt quay vòng",
            "kết nối fanpage Facebook Messenger vào phần mềm chăm sóc tập trung",
            "gán nhãn tag tự động và tính năng Semantic Search tri thức",
            "lập lịch gửi tin nhắn thông báo tự động cho khách hàng",
            "tạo khảo sát đánh giá độ hài lòng CSAT sau khi kết thúc cuộc trò chuyện",
            "đồng bộ danh bạ khách hàng từ Google Contacts vào CRM",
            "theo dõi lịch sử tương tác và ghi âm cuộc gọi của tư vấn viên",
            "bảo mật hai lớp 2FA cho tài khoản nhân viên",
            "lọc danh sách liên hệ theo nguồn chiến dịch quảng cáo",
            "nhúng widget chat vào website bán hàng WordPress hoặc Shopify",
            "cấu hình template tin nhắn mẫu cho nhân viên sale",
            "kết nối tổng đài ảo VoIP để nghe gọi trực tiếp trên trình duyệt"
        ],
        "short_actions": ["cai", "hd", "lam sao", "cach", "check", "xem", "chi"],
        "short_topics": ["zalo oa", "webhook", "tag lead", "xuat excel", "phan quyen", "bot auto", "fb fanpage", "tim kiem kb", "api crm", "loc khach"],
        "short_endings": ["sao ad", "ntn b", "o dau z", "dc k shop", "giup e", "the nao ad", "nhanh vs"],
        "en_openings": ["How to configure", "Guide me to setup", "Does the system support", "Where can I find docs for", "Explain the feature of"],
        "en_topics": ["webhook integration", "Zalo OA message synchronization", "user permission by department", "exporting customer list to Excel", "automated chatbot workflow", "semantic search in knowledge base", "embedding chat widget into landing page"],
    },
    "PRICING_POLICY": {
        "actions": [
            "báo giá chi tiết giúp em", "cho em hỏi chi phí", "xin bảng giá hiện tại của",
            "phiền gửi thông tin bảng giá của", "bên mình có gói cước nào dành cho",
            "tư vấn mức giá và khuyến mãi của", "chi phí duy trì hàng tháng của",
            "bảng so sánh giá và tính năng giữa", "chính sách thanh toán định kỳ cho",
            "mức phí cụ thể khi đăng ký", "cho em xin chi tiết học phí dịch vụ của"
        ],
        "plans": [
            "gói Pro dành cho 5 nhân viên kinh doanh",
            "gói Starter cho doanh nghiệp nhỏ khởi nghiệp",
            "gói Enterprise không giới hạn số lượng tin nhắn",
            "thuê bao 1 năm có được chiết khấu thêm không",
            "mua thêm 10 tài khoản người dùng sử dụng đồng thời",
            "gói cước dùng thử miễn phí 14 ngày có đủ tính năng không",
            "gói dịch vụ mở rộng 50.000 tin nhắn ZNS chăm sóc khách hàng",
            "chính sách hoàn tiền trong vòng 30 ngày nếu không hài lòng",
            "hợp đồng cam kết sử dụng tối thiểu 6 tháng hay 1 năm",
            "chi phí triển khai ban đầu và đào tạo nhân viên sử dụng",
            "chương trình ưu đãi giảm giá 20% khi trả theo năm",
            "gói cước nâng cao tích hợp đa kênh toàn diện",
            "chi phí phát sinh khi vượt hạn mức lưu trữ dữ liệu",
            "bảng giá chi tiết cho từng gói theo quy mô nhân sự"
        ],
        "short_actions": ["gia", "xin gia", "ib gia", "phi", "bang gia", "check gia"],
        "short_plans": ["goi pro", "goi starter", "enterprise", "1 nam", "them user", "dung thu", "combo 5 acc", "gia duy tri"],
        "short_endings": ["bn 1 thang", "bn z ad", "co giam k", "sao shop", "ib e", "bn tien", "the nao ad"],
        "en_openings": ["What is the pricing for", "Send me the quote for", "Are there discounts for", "How much does it cost for", "What is the subscription fee of"],
        "en_plans": ["the Pro plan with 5 users", "the Enterprise tier with unlimited messages", "annual contract payment", "adding 10 more staff accounts", "the Starter growth package", "custom on-premise deployment"],
    },
    "COMPLAINT_SUPPORT": {
        "emotions": [
            "Tôi rất bức xúc vì", "Quá thất vọng về dịch vụ khi", "Tại sao bên bạn lại",
            "Làm ăn quá tắc trách và thiếu chuyên nghiệp vì", "Yêu cầu giải quyết ngay việc",
            "Đã phản ánh nhiều lần nhưng không xử lý vấn đề", "Chất lượng dịch vụ quá kém khi",
            "Tôi không thể chấp nhận được tình trạng", "Quá bực mình khi sử dụng phần mềm vì",
            "Cực kỳ khó chịu với thái độ phục vụ khi"
        ],
        "issues": [
            "gọi điện hotline nhiều lần trong giờ hành chính mà không ai nghe máy",
            "hệ thống tự ý trừ tiền hai lần trong tài khoản thẻ của công ty tôi",
            "dữ liệu danh sách khách hàng tháng trước đột nhiên bị biến mất một phần",
            "nhân viên hỗ trợ kỹ thuật trả lời cộc lốc và thái độ rất thiếu tôn trọng",
            "phần mềm liên tục bị treo làm gián đoạn toàn bộ hoạt động chốt đơn của sale",
            "gửi email khiếu nại đã 3 ngày mà không nhận được bất kỳ lời hồi đáp nào",
            "hệ thống tự động nâng cấp làm lỗi toàn bộ kịch bản bot đã thiết lập",
            "tính năng xuất hóa đơn bị sai số tiền mà không có ai hỗ trợ sửa chữa",
            "tin nhắn khách hàng bị chậm trễ hơn 30 phút mới tới được nhân viên trực",
            "cam kết hoàn tiền 100% nhưng khi yêu cầu thì đùn đẩy trách nhiệm"
        ],
        "short_actions": ["lam an", "support", "thai do", "tru tien", "mat data", "kieu nai", "that vong"],
        "short_issues": ["nhu hach", "cham the", "cui bap", "2 lan la sao", "ai den day", "qua te", "k rep tn", "mat khach r"],
        "short_endings": ["ad oi", "shop oi", "di nha", "that su", "giai quyet di", "luon di", "gap"],
        "en_openings": ["I am extremely frustrated that", "Unacceptable service quality because", "Why has customer support ignored", "We demand immediate compensation for", "The system reliability is terrible since"],
        "en_issues": ["the server went down during peak sales hours", "we were double billed for the monthly subscription", "customer contacts disappeared without backup", "technical staff was completely unresponsive to our tickets"],
    },
    "HANDOFF_HUMAN": {
        "requests": [
            "Vui lòng chuyển máy sang", "Cho tôi gặp trực tiếp", "Kết nối tôi với",
            "Phiền bạn chuyển cuộc trò chuyện này cho", "Tôi cần trao đổi riêng với",
            "Bot ngưng trả lời và nối máy cho", "Làm phiền bạn gọi", "Tôi muốn nói chuyện với",
            "Xin vui lòng kết nối ngay với", "Chuyển tiếp yêu cầu này tới"
        ],
        "roles": [
            "nhân viên tư vấn người thật để trao đổi nghiệp vụ chuyên sâu",
            "chuyên viên hỗ trợ kỹ thuật để hỗ trợ qua Ultraviewer hoặc Teamviewer",
            "quản lý phòng kinh doanh để thương lượng điều khoản hợp đồng lớn",
            "tổng đài viên trực ca này vì chatbot trả lời chưa đúng trọng tâm",
            "nhân viên chăm sóc khách hàng trực tuyến ngay bây giờ",
            "bạn phụ trách dự án doanh nghiệp để ký kết văn bản",
            "bộ phận kế toán để kiểm tra lại thông tin đối soát chuyển khoản",
            "trưởng bộ phận kỹ thuật để hướng dẫn cấu hình máy chủ",
            "nhân viên kinh doanh phụ trách khu vực miền Nam",
            "người có thẩm quyền giải quyết khiếu nại dịch vụ"
        ],
        "short_actions": ["gap", "chuyen may", "goi", "noi chuyen", "call", "connect"],
        "short_roles": ["nguoi that", "tu van vien", "cskh", "nv ky thuat", "quan ly", "tong dai", "nhan vien", "sale"],
        "short_endings": ["di ad", "gap nha", "vs b", "ngay di", "bot oi", "giup e", "plz"],
        "en_openings": ["Please transfer me to", "I need to talk with", "Can I speak directly to", "Connect this chat to", "Requesting a call from"],
        "en_roles": ["a human customer service agent", "a live technical specialist", "the sales manager", "a dedicated account manager"],
    },
    "TECH_ERROR": {
        "errors": [
            "Hệ thống báo lỗi Internal Server Error 500 khi",
            "Tôi không thể đăng nhập vào tài khoản vì",
            "Ứng dụng bị đơ và màn hình trắng xóa khi",
            "Báo lỗi kết nối cơ sở dữ liệu timeout trong lúc",
            "Tin nhắn khách hàng gửi đến không hiển thị trên dashboard vì",
            "Không nhận được mã xác thực OTP gửi về điện thoại khi",
            "Webhook trả về mã lỗi 403 Forbidden và 404 Not Found lúc",
            "Gặp lỗi đồng bộ dữ liệu thất bại và tự động thoát ứng dụng khi",
            "Hệ thống báo lỗi quá tải CPU khi đang",
            "Màn hình liên tục xoay tròn không tải được danh sách hội thoại lúc"
        ],
        "contexts": [
            "nhân viên bấm nút xuất báo cáo doanh số tháng ra tệp Excel",
            "tải lên tệp tài liệu PDF hướng dẫn dung lượng trên 10MB vào kho tri thức",
            "gửi tin nhắn trả lời tự động cho khách hàng trên Zalo OA",
            "thực hiện đồng bộ danh sách 2.000 liên hệ mới nhập vào hệ thống",
            "bấm lưu thông tin sửa đổi trong phần phân quyền người dùng",
            "kết nối webhook gửi sự kiện sang phần mềm quản lý kho KiotViet",
            "mở hộp thư hội thoại nhiều tin nhắn trên trình duyệt di động",
            "cập nhật phiên bản mới của tiện ích chat widget trên trang chủ",
            "thực hiện thao tác gán nhãn hàng loạt cho khách hàng",
            "đăng nhập tài khoản bằng phương thức Google Single Sign-On"
        ],
        "short_actions": ["loi", "k vao dc", "app bi", "mat", "k nhan dc", "sap", "k gui dc"],
        "short_contexts": ["500", "otp", "crash", "trang man hinh", "load cham", "login", "mat mang", "ket noi", "file pdf", "tin nhan"],
        "short_endings": ["ad oi", "roi shop", "sao z", "giup voi", "gap ad", "the nay", "cuu e"],
        "en_openings": ["Getting 500 internal server error when", "Application crashed with unhandled exception during", "Cannot login to dashboard because", "Websocket connection dropped unexpectedly while", "Failed to deliver webhook payload due to"],
        "en_contexts": ["syncing contact database", "exporting analytics report", "triggering automated campaign", "uploading PDF document to vector store"],
    },
    "BUYING_INTENT": {
        "intents": [
            "Công ty tôi muốn ký hợp đồng chính thức triển khai",
            "Bên em quyết định chốt mua ngay hôm nay",
            "Vui lòng gửi số tài khoản ngân hàng để công ty em chuyển khoản thanh toán",
            "Cho em xin thủ tục xuất hóa đơn đỏ VAT cho công ty sau khi mua",
            "Em muốn đăng ký nâng cấp tài khoản từ bản dùng thử lên",
            "Phiền anh chị gửi bản hợp đồng mẫu và phiếu đăng ký mua",
            "Chúng tôi đồng ý với báo giá, hãy gửi hợp đồng để sếp duyệt mua",
            "Tôi muốn đặt cọc trước để giữ chính sách ưu đãi giảm giá cho",
            "Bên mình đã sẵn sàng ký kết văn bản nghiệm thu và thanh toán cho",
            "Cần làm thủ tục gia hạn và nâng cấp gói cước cho"
        ],
        "packages": [
            "gói dịch vụ Enterprise dành cho 30 nhân sự phòng kinh doanh",
            "gói Pro thời hạn 1 năm kèm gói mở rộng 20.000 tin nhắn Zalo",
            "bản quyền phần mềm CRM trọn gói cho toàn bộ chuỗi 5 chi nhánh",
            "thêm 15 tài khoản nhân viên sử dụng bắt đầu từ đầu tháng sau",
            "gói thuê bao trả trước 2 năm để hưởng mức chiết khấu tối đa",
            "dịch vụ triển khai và tích hợp hệ thống theo yêu cầu riêng",
            "gói giải pháp Omnichannel tích hợp Zalo, Facebook và Website",
            "gói bảo trì định kỳ và hỗ trợ kỹ thuật chuyên biệt 24/7"
        ],
        "short_actions": ["chot", "mua", "ck", "ky hd", "lay", "nang cap", "xuat vat"],
        "short_packages": ["goi pro", "enterprise", "1 nam", "stk cty", "hop dong", "5 acc", "chot luon", "don hang"],
        "short_endings": ["nhe ad", "nha shop", "di b", "cho e", "ngay gio", "lien nhe", "gap"],
        "en_openings": ["We decided to purchase", "Please send bank details for wire transfer of", "We want to sign the sales contract for", "Ready to upgrade our subscription to", "Send invoice and payment link for"],
        "en_packages": ["Enterprise 1-year package", "Pro plan with 10 user seats", "annual renewal with VAT invoice", "custom deployment tier"],
    },
}

ACCENT_MAP = {
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'đ': 'd',
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
}

def remove_accents(text: str) -> str:
    res = []
    for ch in text:
        lower = ch.lower()
        if lower in ACCENT_MAP:
            rep = ACCENT_MAP[lower]
            res.append(rep.upper() if ch.isupper() else rep)
        else:
            res.append(ch)
    return "".join(res)

TYPO_RULES = [
    ("hướng dẫn", "hướng dẩn"), ("giá", "já"), ("báo giá", "báo ja"),
    ("chi phí", "chj phí"), ("phần mềm", "fần mềm"), ("không", "kô"),
    ("đăng ký", "đkí"), ("tài khoản", "tài khoãng"), ("hệ thống", "hệ thốg"),
    ("nhân viên", "nhan vjen"), ("chuyển", "chuyễn"), ("hợp đồng", "hơp đồg"),
    ("hóa đơn", "hoá đơm"), ("bực mình", "bực mìn"), ("lỗi", "lổi"),
    ("kết nối", "kêt nôi"), ("xuất", "xuât"), ("khách hàng", "khack hang"),
    ("quản lý", "quãn lí"), ("thất vọng", "thất vọg")
]

def apply_typos(text: str) -> str:
    res = text
    applied = False
    for orig, typo in TYPO_RULES:
        if orig in res.lower() and random.random() < 0.6:
            idx = res.lower().find(orig)
            res = res[:idx] + typo + res[idx + len(orig):]
            applied = True
    if not applied:
        words = res.split()
        if words:
            w_idx = random.randint(0, len(words) - 1)
            target = words[w_idx]
            if len(target) > 3:
                words[w_idx] = target.replace("c", "k").replace("i", "j").replace("qu", "w")
            res = " ".join(words)
    return res

EMOJI_LIST = [" 😊", " 🙏", " ✨", " 🚀", " 💼", " 📊", " 🏷️", " 💸", " 😡", " 😭", " 📞", " 🤖", " 🤝", " 💳", " ⏳", " 📌", " 💬"]

def apply_emojis(text: str) -> str:
    e1 = random.choice(EMOJI_LIST)
    e2 = random.choice(EMOJI_LIST) if random.random() < 0.3 else ""
    return f"{text}{e1}{e2}"


STYLE_TARGETS = {
    "polite_full": 750,   # 25%
    "short_abbrev": 750,  # 25%
    "no_accent": 600,     # 20%
    "typo": 450,          # 15%
    "en_mix": 300,        # 10%
    "emoji": 150,         # 5%
}


def build_unique_sample(intent: str, style: str) -> str:
    """Sinh một câu độc nhất bằng cách kết hợp ngẫu nhiên các slot."""
    d = SLOTS[intent]
    
    if style == "short_abbrev":
        act = random.choice(d["short_actions"])
        mid = random.choice(d.get("short_targets", d.get("short_topics", d.get("short_plans", d.get("short_issues", d.get("short_roles", d.get("short_contexts", d.get("short_packages"))))))))
        end = random.choice(d["short_endings"])
        return f"{act} {mid} {end}"
    
    if style == "en_mix":
        op = random.choice(d["en_openings"])
        tgt = random.choice(d.get("en_targets", d.get("en_topics", d.get("en_plans", d.get("en_issues", d.get("en_roles", d.get("en_contexts", d.get("en_packages"))))))))
        if "en_closings" in d:
            cl = random.choice(d["en_closings"])
            return f"{op} {tgt}, {cl}."
        return f"{op} {tgt}?"

    # Các câu tiếng Việt cấu trúc
    if intent == "GREETING":
        base = f"{random.choice(d['openings'])} {random.choice(d['subjects'])}, {random.choice(d['wishes'])}"
    elif intent in ["KB_SEARCH", "PRICING_POLICY"]:
        base = f"{random.choice(d['actions'])} {random.choice(d['topics' if intent == 'KB_SEARCH' else 'plans'])}"
    elif intent == "COMPLAINT_SUPPORT":
        base = f"{random.choice(d['emotions'])} {random.choice(d['issues'])}"
    elif intent == "HANDOFF_HUMAN":
        base = f"{random.choice(d['requests'])} {random.choice(d['roles'])}"
    elif intent == "TECH_ERROR":
        base = f"{random.choice(d['errors'])} {random.choice(d['contexts'])}"
    elif intent == "BUYING_INTENT":
        base = f"{random.choice(d['intents'])} {random.choice(d['packages'])}"
    else:
        base = "Xin chào hỗ trợ"

    if style == "polite_full":
        prefix = "Dạ " if not base.startswith("Dạ") and random.random() < 0.6 else ""
        suffix = " ạ." if not base.endswith(("ạ.", "ạ?", "ạ!")) else ""
        return f"{prefix}{base}{suffix}"
    elif style == "no_accent":
        return remove_accents(base).lower()
    elif style == "typo":
        return apply_typos(base)
    elif style == "emoji":
        return apply_emojis(base)

    return base


def create_dataset_with_natural_duplicates() -> list[dict]:
    """Sinh đúng 3.000 mẫu train thô, đảm bảo tỷ lệ trùng lặp tự nhiên đạt ~28% (khoảng 840 mẫu)."""
    random.seed(RANDOM_SEED)

    # Ta sinh 2.160 mẫu cơ sở độc nhất (72%), và 840 mẫu bản sao biến thể (28%)
    TARGET_UNIQUE = 2160
    TARGET_TOTAL = 3000

    unique_items_by_style = {s: [] for s in STYLE_TARGETS}
    
    # Phân bổ số mẫu độc nhất theo từng style (tương ứng 72% mỗi style)
    for style, total_cnt in STYLE_TARGETS.items():
        uniq_cnt = int(round(total_cnt * (TARGET_UNIQUE / TARGET_TOTAL)))
        base_per_intent = uniq_cnt // len(INTENTS)
        rem = uniq_cnt % len(INTENTS)
        
        seen_texts = set()
        for idx, intent in enumerate(INTENTS):
            n_samples = base_per_intent + (1 if idx < rem else 0)
            attempts = 0
            while n_samples > 0 and attempts < 1000:
                attempts += 1
                text = build_unique_sample(intent, style)
                if text not in seen_texts:
                    seen_texts.add(text)
                    unique_items_by_style[style].append({
                        "text": text,
                        "intent": intent,
                        "style": style,
                    })
                    n_samples -= 1

    # Tạo các bản sao gần giống (Near-duplicates) để lấp đầy số lượng đến đúng 3.000
    all_raw = []
    sample_id = 1

    for style, target_total in STYLE_TARGETS.items():
        pool = unique_items_by_style[style]
        # Thêm toàn bộ mẫu độc nhất
        for item in pool:
            all_raw.append({
                "id": sample_id,
                "text": item["text"],
                "intent": item["intent"],
                "style": item["style"],
            })
            sample_id += 1
            
        # Sinh số lượng bản sao gần giống cần thiết
        needed_dups = target_total - len(pool)
        for _ in range(needed_dups):
            source = random.choice(pool)
            orig = source["text"]
            # Biến thể gần giống (thêm dấu chấm, khoảng trắng, từ đệm nhẹ)
            fillers = [" ạ", " nhé", " với", " ơi", " nha"]
            if random.random() < 0.7:
                dup_text = orig.rstrip(".!? ") + random.choice(fillers) + "."
            else:
                dup_text = orig + "  "
                
            all_raw.append({
                "id": sample_id,
                "text": dup_text,
                "intent": source["intent"],
                "style": style,
            })
            sample_id += 1

    assert len(all_raw) == 3000, f"Tổng số mẫu phải là 3000, nhận {len(all_raw)}"

    # Trộn ngẫu nhiên
    random.shuffle(all_raw)
    for i, s in enumerate(all_raw):
        s["id"] = i + 1

    return all_raw


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    cleaned = "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()
    return {cleaned[i:i + n] for i in range(len(cleaned) - n + 1)} if len(cleaned) >= n else {cleaned}


def _jaccard_similarity(s1: set[str], s2: set[str]) -> float:
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def deduplicate(samples: list[dict], threshold: float = 0.88) -> tuple[list[dict], list[dict], dict]:
    cleaned = []
    removed = []
    seen_by_intent = {i: [] for i in INTENTS}

    for item in samples:
        text = item["text"]
        intent = item["intent"]
        ngram_set = _char_ngrams(text, n=3)

        is_dup = False
        for existing_ngram, existing_item in seen_by_intent[intent]:
            sim = _jaccard_similarity(ngram_set, existing_ngram)
            if sim >= threshold:
                is_dup = True
                removed.append({
                    "removed_id": item["id"],
                    "removed_text": text,
                    "intent": intent,
                    "matched_with_id": existing_item["id"],
                    "matched_text": existing_item["text"],
                    "similarity": round(sim, 4),
                })
                break

        if not is_dup:
            seen_by_intent[intent].append((ngram_set, item))
            cleaned.append(item)

    for i, item in enumerate(cleaned):
        item["id"] = i + 1

    stats = {
        "raw_count": len(samples),
        "dedup_count": len(cleaned),
        "removed_count": len(removed),
        "dedup_rate_percent": round((len(removed) / len(samples)) * 100, 2),
    }

    return cleaned, removed, stats


def main():
    print("=" * 70)
    print("1. SINH TẬP HUẤN LUYỆN 3.000 MẪU (THEO 6 VĂN PHONG)")
    print("=" * 70)
    raw_samples = create_dataset_with_natural_duplicates()
    print(f"Tổng số mẫu raw: {len(raw_samples)}")
    
    style_dist = Counter(s["style"] for s in raw_samples)
    print("Phân bố văn phong thô (Target):")
    for style, count in style_dist.items():
        pct = (count / len(raw_samples)) * 100
        print(f"  - {style:<15}: {count:4d} mẫu ({pct:.1f}%)")

    raw_path = Path("data/intent_train_raw.jsonl")
    with open(raw_path, "w", encoding="utf-8") as f:
        for s in raw_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"-> Đã ghi file: {raw_path}")

    print("\n" + "=" * 70)
    print("2. KHỬ TRÙNG LẶP GẦN GIỐNG (NEAR-DUPLICATE DEDUPLICATION)")
    print("=" * 70)
    clean_samples, removed, dedup_stats = deduplicate(raw_samples, threshold=0.88)
    print(f"Số mẫu trước khử trùng lặp : {dedup_stats['raw_count']}")
    print(f"Số mẫu trùng lặp bị loại bỏ: {dedup_stats['removed_count']}")
    print(f"Số mẫu sạch sau khử trùng lặp: {dedup_stats['dedup_count']}")
    print(f"Tỉ lệ loại bỏ (Deduplication Rate): {dedup_stats['dedup_rate_percent']}%")

    clean_path = Path("data/intent_train_dedup.jsonl")
    with open(clean_path, "w", encoding="utf-8") as f:
        for s in clean_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"-> Đã ghi file: {clean_path}")

    eval_dir = Path("reports/eval")
    eval_dir.mkdir(parents=True, exist_ok=True)
    # Cohen's Kappa: xem scripts/compute_annotation_kappa.py (đọc nhãn thật của hai người)

    dist_file = eval_dir / "intent_data_distribution.json"
    clean_style_dist = Counter(s["style"] for s in clean_samples)
    clean_intent_dist = Counter(s["intent"] for s in clean_samples)
    dist_report = {
        "raw_samples_count": len(raw_samples),
        "clean_samples_count": len(clean_samples),
        "duplicates_removed_count": len(removed),
        "deduplication_rate_percent": dedup_stats["dedup_rate_percent"],
        "target_style_distribution_raw": {s: round(c / len(raw_samples) * 100, 2) for s, c in style_dist.items()},
        "clean_style_distribution": {s: {"count": c, "pct": round(c / len(clean_samples) * 100, 2)} for s, c in clean_style_dist.items()},
        "clean_intent_distribution": {i: {"count": c, "pct": round(c / len(clean_samples) * 100, 2)} for i, c in clean_intent_dist.items()},
    }
    with open(dist_file, "w", encoding="utf-8") as f:
        json.dump(dist_report, f, ensure_ascii=False, indent=2)
    print(f"-> Đã xuất báo cáo phân bố: {dist_file}")

    print("\n" + "=" * 70)
    print("3. ĐÓNG BĂNG MÃ HASH SHA-256")
    print("=" * 70)
    clean_hash = hashlib.sha256(clean_path.read_bytes()).hexdigest()
    hashes_file = Path("artifacts/DATA_HASHES.txt")
    lines = hashes_file.read_text(encoding="utf-8").splitlines() if hashes_file.exists() else []
    
    new_lines = [l for l in lines if not l.startswith("data/intent_train_dedup.jsonl:")]
    new_lines.append(f"data/intent_train_dedup.jsonl:{clean_hash}")
    hashes_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"-> Đã đóng băng SHA-256 vào {hashes_file}:")
    print(f"   data/intent_train_dedup.jsonl:{clean_hash}")


if __name__ == "__main__":
    main()
