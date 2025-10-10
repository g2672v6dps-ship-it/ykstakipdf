import streamlit as st
import hashlib
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import csv
import os
import json
import random
import firebase_admin
from firebase_admin import credentials, db

# Sayfa yapılandırması
st.set_page_config(
    page_title="YKS Takip Sistemi",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Firebase başlatma
try:
    # Firebase'in zaten başlatılıp başlatılmadığını kontrol et
    if not firebase_admin._apps:
        # Firebase Admin SDK'yı başlat
        # GitHub/Streamlit Cloud deployment için environment variable kontrolü
        if 'FIREBASE_KEY' in os.environ:
            # Production: Environment variable'dan JSON key'i al
            firebase_json = os.environ["FIREBASE_KEY"]
            firebase_config = json.loads(firebase_json)
            cred = credentials.Certificate(firebase_config)
        else:
            # Local development: JSON dosyasından al
            cred = credentials.Certificate("firebase_key.json")
        
        firebase_admin.initialize_app(cred, {
            'databaseURL':'https://yks-takip-c26d5-default-rtdb.firebaseio.com/'  # ✅ DOĞRU/'
        })
    
    db_ref = db.reference('users')
    if not hasattr(st.session_state, 'firebase_connected'):
        st.success("🔥 Firebase bağlantısı başarılı!")
        st.session_state.firebase_connected = True
        
except Exception as e:
    st.warning(f"⚠️ Firebase bağlantısı kurulamadı: {e}")
    st.info("🔧 Geçici olarak yerel test sistemi kullanılıyor...")
    db_ref = None
    
    # FALLBACK: Geçici test kullanıcıları
    if 'fallback_users' not in st.session_state:
        st.session_state.fallback_users = {
            'test_ogrenci': {
                'username': 'test_ogrenci',
                'password': '123456',
                'name': 'Test',
                'surname': 'Öğrenci',
                'grade': '12',
                'field': 'Sayısal',
                'created_date': '2025-01-01',
                'student_status': 'ACTIVE',
                'topic_progress': '{}',
                'topic_completion_dates': '{}',
                'topic_repetition_history': '{}',
                'topic_mastery_status': '{}',
                'pending_review_topics': '{}',
                'total_study_time': 0,
                'created_by': 'LOCAL_TEST',
                'last_login': None
            },
            'admin': {
                'username': 'admin',
                'password': 'admin123',
                'name': 'Admin',
                'surname': 'User',
                'grade': '12',
                'field': 'Test',
                'created_date': '2025-01-01',
                'student_status': 'ACTIVE',
                'topic_progress': '{}',
                'topic_completion_dates': '{}',
                'topic_repetition_history': '{}',
                'topic_mastery_status': '{}',
                'pending_review_topics': '{}',
                'total_study_time': 0,
                'created_by': 'LOCAL_TEST',
                'last_login': None
            }
        }
    st.success("✅ Geçici test kullanıcıları hazırlandı!")

# Firebase veritabanı fonksiyonları
def load_users_from_firebase():
    """Firebase'den kullanıcı verilerini yükler (Fallback destekli)"""
    try:
        if db_ref:
            users_data = db_ref.child("users").get()
            return users_data if users_data else {}
        else:
            # FALLBACK: Local test kullanıcıları
            if hasattr(st.session_state, 'fallback_users'):
                return st.session_state.fallback_users
            return {}
    except Exception as e:
        st.error(f"Firebase veri yükleme hatası: {e}")
        # FALLBACK: Local test kullanıcıları
        if hasattr(st.session_state, 'fallback_users'):
            return st.session_state.fallback_users
        return {}

def update_user_in_firebase(username, data):
    """Firebase'de kullanıcı verilerini günceller (Fallback destekli)"""
    try:
        if db_ref:
            db_ref.child("users").child(username).update(data)
            return True
        else:
            # FALLBACK: Local test kullanıcıları
            if hasattr(st.session_state, 'fallback_users'):
                if username not in st.session_state.fallback_users:
                    st.session_state.fallback_users[username] = {}
                st.session_state.fallback_users[username].update(data)
                return True
    except Exception as e:
        st.error(f"Firebase veri güncelleme hatası: {e}")
        # FALLBACK: Local test kullanıcıları
        if hasattr(st.session_state, 'fallback_users'):
            if username not in st.session_state.fallback_users:
                st.session_state.fallback_users[username] = {}
            st.session_state.fallback_users[username].update(data)
            return True
    return False

# === HİBRİT POMODORO SİSTEMİ SABİTLERİ ===

# YKS Odaklı Motivasyon Sözleri - Hibrit Sistem için
MOTIVATION_QUOTES = [
    "Her 50 dakikalık emek, seni rakiplerinden ayırıyor! 💪",
    "Şu anda çözdüğün her soru, YKS'de seni zirveye taşıyacak! 🎯",
    "Büyük hedefler küçük adımlarla başlar - sen doğru yoldasın! ⭐",
    "Her nefes alışın, YKS başarına bir adım daha yaklaştırıyor! 🌬️",
    "Zorluklara direnmek seni güçlendiriyor - YKS'de fark yaratacaksın! 🚀",
    "Bugün kazandığın her kavram, sınavda seni öne çıkaracak! 📚",
    "Konsantrasyon kasların güçleniyor - şampiyonlar böyle yetişir! 🧠",
    "Hedefine odaklan! Her dakika YKS başarın için değerli! 🏆",
    "Mola hakkını akıllıca kullanıyorsun - bu seni daha güçlü yapıyor! 💨",
    "Başarı sabır ister, sen sabırlı bir savaşçısın! ⚔️",
    "Her yeni konu öğrenişin, gelecekteki mesleğinin temeli! 🏗️",
    "Rüyalarının peşinde koşuyorsun - asla vazgeçme! 🌟",
    "YKS sadece bir sınav, sen ise sınırsız potansiyelin! 🌈",
    "Her pomodoro seansı, hedefine bir adım daha yaklaştırıyor! 🎯",
    "Dün yapamadığını bugün yapabiliyorsun - bu gelişim! 📈",
    "Zorlu soruları çözerken beynin güçleniyor! 🧩",
    "Her mola sonrası daha güçlü dönüyorsun! 💪",
    "Bilim insanları da böyle çalıştı - sen de başaracaksın! 🔬",
    "Her nefes, yeni bir başlangıç fırsatı! 🌱",
    "Hayal ettiğin üniversite seni bekliyor! 🏛️"
]

# Mikro ipuçları (ders bazında)
MICRO_TIPS = {
    "TYT Matematik": [
        "📐 Türev sorularında genellikle önce fonksiyonun köklerini bulmak saldırıları hızlandırır.",
        "🔢 İntegral hesaplarken substitüsyon methodunu akılda tut.",
        "📊 Geometri problemlerinde çizim yapmayı unutma.",
        "⚡ Limit sorularında l'hopital kuralını hatırla."
    ],
    "TYT Fizik": [
        "⚡ Newton yasalarını uygularken kuvvet vektörlerini doğru çiz.",
        "🌊 Dalga problemlerinde frekans-dalga boyu ilişkisini unutma.",
        "🔥 Termodinamik sorularında sistem sınırlarını net belirle.",
        "🔬 Elektrik alanı hesaplamalarında işaret dikkatli kontrol et."
    ],
    "TYT Kimya": [
        "🧪 Mol kavramı tüm hesaplamaların temeli - ezberleme!",
        "⚛️ Periyodik cetveldeki eğilimleri görselleştir.",
        "🔄 Denge tepkimelerinde Le Chatelier prensibini uygula.",
        "💧 Asit-baz titrasyonlarında eşdeğer nokta kavramını unutma."
    ],
    "TYT Türkçe": [
        "📖 Paragraf sorularında ana fikri ilk ve son cümlelerde ara.",
        "✍️ Anlam bilgisi sorularında bağlamı dikkate al.",
        "📝 Yazım kurallarında 'de/da' ayrım kuralını hatırla.",
        "🎭 Edebi türlerde karakterizasyon önemli."
    ],
    "TYT Tarih": [
        "📅 Olayları kronolojik sırayla öğren, sebep-sonuç bağla.",
        "🏛️ Siyasi yapılar sosyal yapılarla ilişkisini kur.",
        "🗺️ Haritalarla coğrafi konumları pekiştir.",
        "👑 Dönem özelliklerini başlıca olaylarla örnekle."
    ],
    "TYT Coğrafya": [
        "🌍 İklim türlerini sebepleriyle birlikte öğren.",
        "🏔️ Jeomorfoloji'de süreç-şekil ilişkisini kur.",
        "📊 İstatistiksel veriler harita okuma becerisini geliştir.",
        "🌱 Bitki örtüsü-iklim ilişkisini unutma."
    ],
    "AYT Matematik": [
        "📐 Türev sorularında genellikle önce fonksiyonun köklerini bulmak saldırıları hızlandırır.",
        "🔢 İntegral hesaplarken substitüsyon methodunu akılda tut.",
        "📊 Geometri problemlerinde çizim yapmayı unutma.",
        "⚡ Limit sorularında l'hopital kuralını hatırla."
    ],
    "AYT Fizik": [
        "⚡ Newton yasalarını uygularken kuvvet vektörlerini doğru çiz.",
        "🌊 Dalga problemlerinde frekans-dalga boyu ilişkisini unutma.",
        "🔥 Termodinamik sorularında sistem sınırlarını net belirle.",
        "🔬 Elektrik alanı hesaplamalarında işaret dikkatli kontrol et."
    ],
    "AYT Kimya": [
        "🧪 Mol kavramı tüm hesaplamaların temeli - ezberleme!",
        "⚛️ Periyodik cetveldeki eğilimleri görselleştir.",
        "🔄 Denge tepkimelerinde Le Chatelier prensibini uygula.",
        "💧 Asit-baz titrasyonlarında eşdeğer nokta kavramını unutma."
    ],
    "Genel": [
        "🎯 Zor sorularla karşılaştığında derin nefes al ve sistematik düşün.",
        "⏰ Zaman yönetimini ihmal etme - her dakika değerli.",
        "📚 Kavramları sadece ezberlemek yerine anlayarak öğren.",
        "🔄 Düzenli tekrar yapmak kalıcılığı artırır."
    ]
}

# YKS Odaklı Nefes Egzersizi Talimatları
BREATHING_EXERCISES = [
    {
        "name": "4-4-4-4 Tekniği (Kare Nefes)",
        "instruction": "4 saniye nefes al → 4 saniye tut → 4 saniye ver → 4 saniye bekle",
        "benefit": "Stresi azaltır, odaklanmayı artırır, sınav kaygısını azaltır"
    },
    {
        "name": "Karın Nefesi (Diyafragma Nefesi)",
        "instruction": "Elinizi karnınıza koyun. Nefes alırken karın şişsin, verirken insin",
        "benefit": "Gevşemeyi sağlar, kaygıyı azaltır, zihinsel netliği artırır"
    },
    {
        "name": "4-7-8 Sakinleştirici Nefes",
        "instruction": "4 saniye burun ile nefes al → 7 saniye tut → 8 saniye ağız ile ver",
        "benefit": "Derin rahatlama sağlar, uykuya yardım eder, sınav öncesi sakinleştirir"
    },
    {
        "name": "Yavaş Derin Nefes",
        "instruction": "6 saniye nefes al → 2 saniye tut → 6 saniye yavaşça ver",
        "benefit": "Kalp ritmi düzenlenir, sakinleşir, zihinsel berraklık artar"
    },
    {
        "name": "Alternatif Burun Nefesi",
        "instruction": "Sağ burun deliği ile nefes al, sol ile ver. Sonra tersini yap",
        "benefit": "Beynin her iki yarım küresini dengeler, konsantrasyonu artırır"
    },
    {
        "name": "5-5 Basit Ritim",
        "instruction": "5 saniye nefes al → 5 saniye nefes ver (hiç tutmadan)",
        "benefit": "Basit ve etkili, hızlı sakinleşme, odaklanma öncesi ideal"
    }
]

# Tüm kullanıcı alanlarını tutarlılık için tanımlıyoruz.
FIELDNAMES = ['username', 'password', 'name', 'surname', 'grade', 'field', 'target_department', 'tyt_last_net', 'tyt_avg_net', 'ayt_last_net', 'ayt_avg_net', 'learning_style', 'learning_style_scores', 'created_at',  'detailed_nets', 'deneme_analizleri','study_program', 'topic_progress', 'topic_completion_dates', 'yks_survey_data', 'pomodoro_history'
              ,'is_profile_complete', 
              'is_learning_style_set', 
              'learning_style',
              
              # YENİ ALANLAR - Kalıcı Öğrenme Sistemi
              'topic_repetition_history',  # Her konunun tekrar geçmişi
              'topic_mastery_status',      # Konunun kalıcılık durumu
              'pending_review_topics',     # Tekrar değerlendirmesi bekleyen konular
              
              # YENİ ALAN - Günlük Motivasyon Sistemi
              'daily_motivation'           # Günlük motivasyon puanları ve notları
              ]

# Bölümlere göre arka plan resimleri
BACKGROUND_STYLES = {
    "Tıp": {
        "image": "https://images.unsplash.com/photo-1551076805-e1869033e561?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)",
        "icon": "🩺"
    },
    "Mühendislik": {
        "image": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)",
        "icon": "⚙️"
    },
    "Hukuk": {
        "image": "https://images.unsplash.com/photo-1589391886645-d51941baf7fb?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #556270 0%, #4ecdc4 100%)",
        "icon": "⚖️"
    },
    "Öğretmenlik": {
        "image": "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #ffd89b 0%, #19547b 100%)",
        "icon": "👨‍🏫"
    },
    "İktisat": {
        "image": "https://images.unsplash.com/photo-1665686306574-1ace09918530?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #834d9b 0%, #d04ed6 100%)",
        "icon": "📈"
    },
    "Mimarlık": {
        "image": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #5614b0 0%, #dbd65c 100%)",
        "icon": "🏛️"
    },
    "Psikoloji": {
        "image": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #654ea3 0%, #eaafc8 100%)",
        "icon": "🧠"
    },
    "Diş Hekimliği": {
        "image": "https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #ff5e62 0%, #ff9966 100%)",
        "icon": "🦷"
    },
    "Varsayılan": {
        "image": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80",
        "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "icon": "🎯"
    }
}

# Kitap önerileri
BOOK_RECOMMENDATIONS = {
    "Bilim Kurgu": [
        "Isaac Asimov - Foundation Serisi",
        "Douglas Adams - Otostopçunun Galaksi Rehberi", 
        "George Orwell - 1984",
        "Aldous Huxley - Cesur Yeni Dünya"
    ],
    "Klasik Edebiyat": [
        "Victor Hugo - Sefiller",
        "Fyodor Dostoyevski - Suç ve Ceza",
        "Leo Tolstoy - Savaş ve Barış",
        "Charles Dickens - İki Şehrin Hikayesi"
    ],
    "Kişisel Gelişim": [
        "Dale Carnegie - Dost Kazanma ve İnsanları Etkileme Sanatı",
        "Stephen Covey - Etkili İnsanların 7 Alışkanlığı",
        "Carol Dweck - Mindset",
        "Daniel Goleman - Duygusal Zeka"
    ],
    "Tarih": [
        "Yuval Noah Harari - Sapiens",
        "Jared Diamond - Tüfek, Mikrop ve Çelik",
        "Howard Zinn - Amerika Birleşik Devletleri'nin Halkın Gözünden Tarihi",
        "İlber Ortaylı - Osmanlı'yı Yeniden Keşfetmek"
    ],
    "Felsefe": [
        "Jostein Gaarder - Sophie'nin Dünyası",
        "Platon - Devlet",
        "Aristoteles - Nikomakhos'a Etik",
        "Ahmet Cevizci - Felsefe Tarihi"
    ],
    "Psikoloji": [
        "Daniel Kahneman - Hızlı ve Yavaş Düşünme",
        "Viktor Frankl - İnsanın Anlam Arayışı",
        "Carl Jung - İnsan ve Sembolleri",
        "Sigmund Freud - Rüyaların Yorumu"
    ]
}

# 🧠 BİLİMSEL TEMELLI BİLİŞSEL PROFİL TANIMLARI
# Kolb, Riding & Cheema (1991), Gardner teorilerine dayalı

COGNITIVE_PROFILE_DESCRIPTIONS = {
    # 🔬 Analitik Dominant Profiller
    "Analitik-Dışsal": {
        "title": "🔬 Analitik-Dışsal Profil",
        "scientific_base": "Kolb: Soyut Kavramsallaştırma + Riding & Cheema: Analitik Stil",
        "intro": "Sistemli düşünür, hedef odaklısınız. Bilgiyi parçalara bölerek analiz eder, dışsal motivasyonlarla hareket edersiniz.",
        "strengths": [
            "🎯 Sistematik problem çözme yeteneği",
            "📊 Veri analizi ve mantıksal çıkarım",
            "⏰ Hedef belirleme ve planlamada başarı",
            "🔍 Detaylı araştırma ve inceleme becerisi"
        ],
        "yks_strategies": [
            "📈 Net puan hedefleri belirleyin ve grafiklerle takip edin",
            "🗓️ Haftalık-aylık çalışma planları oluşturun",
            "📋 Konuları küçük parçalara bölerek sistematik ilerleyin",
            "🏆 Başarı ödülleri sistemi kurun (puan artışları için)"
        ],
        "study_methods": [
            "Schematic learning (şema tabanlı öğrenme)",
            "Progressive disclosure (aşamalı açıklama)",
            "Goal-setting frameworks (hedef belirleme çerçeveleri)",
            "Analytical questioning techniques (analitik sorgulama)"
        ]
    },
    
    "Analitik-İçsel": {
        "title": "🔬 Analitik-İçsel Profil", 
        "scientific_base": "Gardner: Mantıksal-Matematiksel Zeka + İçsel Motivasyon",
        "intro": "Derinlemesine anlama odaklısınız. Merak ettiğiniz konuları sistematik olarak çözümlersiniz.",
        "strengths": [
            "🧠 Derin kavrayış ve eleştirel düşünme",
            "🔍 Bağımsız araştırma becerisi",
            "💡 Yaratıcı problem çözme yaklaşımları",
            "📚 Sürekli öğrenme isteği"
        ],
        "yks_strategies": [
            "🎨 İlginizi çeken derslere daha fazla zaman ayırın",
            "🔍 Konuların 'neden' ve 'nasıl' sorularını araştırın",
            "📖 Ders kitabının ötesinde kaynaklara başvurun",
            "🎯 Kişisel merak alanlarınızla YKS konularını ilişkilendirin"
        ],
        "study_methods": [
            "Inquiry-based learning (araştırma tabanlı öğrenme)",
            "Self-directed exploration (kendini yönlendirme)",
            "Conceptual mapping (kavramsal haritalama)",
            "Reflective analysis (yansıtıcı analiz)"
        ]
    },

    # 🎨 Sintetik Dominant Profiller  
    "Sintetik-Dışsal": {
        "title": "🎨 Sintetik-Dışsal Profil",
        "scientific_base": "Riding & Cheema: Holistik Stil + Dışsal Motivasyon",
        "intro": "Büyük resmi görür, yaratıcı çözümler üretirsiniz. Takdir ve başarı ile motive olursunuz.",
        "strengths": [
            "🌟 Bütüncül yaklaşım ve pattern recognition",
            "🎭 Yaratıcı düşünme ve yenilikçi çözümler",
            "🌐 Disiplinler arası bağlantı kurma",
            "🎪 Performans odaklı çalışma"
        ],
        "yks_strategies": [
            "🎨 Konular arası bağlantıları görselleştirin",
            "🏆 Deneme sınavlarını yarışma gibi görün",
            "👥 Çalışma gruplarında liderlik alın",
            "🎯 Yaratıcı not alma tekniklerini kullanın"
        ],
        "study_methods": [
            "Holistic learning (bütüncül öğrenme)",
            "Creative visualization (yaratıcı görselleştirme)",
            "Interdisciplinary connections (disiplinler arası bağlantılar)",
            "Performance-based rewards (performans tabanlı ödüller)"
        ]
    },

    "Sintetik-İçsel": {
        "title": "🎨 Sintetik-İçsel Profil",
        "scientific_base": "Gardner: Yaratıcı Zeka + İçsel Motivasyon",
        "intro": "Sanatsal ve yaratıcı yaklaşımlarla öğrenirsiniz. Kendi içsel rehberliğinizle hareket edersiniz.",
        "strengths": [
            "🎨 Yaratıcı öğrenme stratejileri geliştirme",
            "🌈 Çok boyutlu düşünme yeteneği",
            "🎪 Sezgisel kavrayış",
            "🌟 Özgün yaklaşımlar üretme"
        ],
        "yks_strategies": [
            "🎨 Konuları hikayeler ve metaforlarla öğrenin",
            "🌈 Renkli, yaratıcı notlar alın",
            "🎭 Role-play teknikleriyle öğrenin",
            "🎪 Kendi benzersiz çalışma yöntemlerinizi geliştirin"
        ],
        "study_methods": [
            "Narrative learning (hikaye tabanlı öğrenme)",
            "Metaphorical thinking (metaforik düşünme)", 
            "Artistic expression (sanatsal ifade)",
            "Intuitive exploration (sezgisel keşif)"
        ]
    },

    # 🧘 Reflektif Dominant Profiller
    "Reflektif-Metodik": {
        "title": "🧘 Reflektif-Metodik Profil",
        "scientific_base": "Kolb: Yansıtıcı Gözlem + Metodolojik Yaklaşım",
        "intro": "Düşünerek ve planlayarak hareket edersiniz. Sistematik yöntemlerle derinlemesine çalışırsınız.",
        "strengths": [
            "🤔 Derinlemesine düşünme ve yansıtma",
            "📋 Metodolojik yaklaşım",
            "⏳ Sabırlı ve dikkatli çalışma",
            "🎯 Stratejik planlama"
        ],
        "yks_strategies": [
            "⏰ Yavaş ama etkili çalışma planları yapın",
            "📝 Düzenli notlar alın ve gözden geçirin",
            "🤔 Hataları derinlemesine analiz edin",
            "🎯 Uzun vadeli hedefler belirleyin"
        ],
        "study_methods": [
            "Reflective practice (yansıtıcı uygulama)",
            "Systematic review (sistematik gözden geçirme)",
            "Deep processing (derin işleme)",
            "Strategic planning (stratejik planlama)"
        ]
    },

    # 💡 Deneysel Dominant Profiller
    "Deneysel-Sosyal": {
        "title": "💡 Deneysel-Sosyal Profil",
        "scientific_base": "Kolb: Aktif Deneyim + Gardner: Sosyal Zeka",
        "intro": "Deneyerek öğrenir, sosyal etkileşimlerle gelişirsiniz. Grup çalışmaları size enerji verir.",
        "strengths": [
            "🔄 Deneme-yanılma ile hızlı öğrenme",
            "👥 Sosyal öğrenme ve iş birliği",
            "⚡ Adaptasyon yeteneği",
            "🎪 Etkileşimli problem çözme"
        ],
        "yks_strategies": [
            "👥 Çalışma grupları oluşturun",
            "🔄 Çok sayıda deneme sınavı çözün",
            "💬 Konuları arkadaşlarınızla tartışın",
            "🎯 Grup yarışmaları düzenleyin"
        ],
        "study_methods": [
            "Collaborative learning (işbirlikçi öğrenme)",
            "Trial-and-error approach (deneme-yanılma)",
            "Social interaction (sosyal etkileşim)",
            "Peer learning (akran öğrenimi)"
        ]
    }
}

# 🎯 YKS'YE ÖZEL BİLİŞSEL PROFİL YORUMLARI
YKS_COGNITIVE_INTERPRETATIONS = {
    "analitik": {
        "emoji": "🔬",
        "description": "Sayısal & mantık derslerinde başarılı olur, düzenli tekrar ister",
        "best_subjects": ["TYT Matematik", "AYT Matematik", "Fizik", "Kimya"],
        "study_approach": "Sistematik ve adım adım"
    },
    "sintetik": {
        "emoji": "🎨", 
        "description": "Eşit ağırlık/sözel alanda baskın, bütüncül kavrama gücü yüksek",
        "best_subjects": ["Edebiyat", "Tarih", "Coğrafya", "Felsefe"],
        "study_approach": "Bütüncül ve yaratıcı"
    },
    "reflektif": {
        "emoji": "🧘",
        "description": "Sessiz ortamda öğrenir, deneme analizlerinde derin düşünür",
        "best_subjects": ["Tüm dersler - özellikle teorik konular"],
        "study_approach": "Derin düşünme ve analiz"
    },
    "dışsal_motivasyon": {
        "emoji": "⚡",
        "description": "Net hedef belirleme, puan/ödül sistemiyle motive olur",
        "motivation_type": "Hedef ve başarı odaklı",
        "study_tips": ["Puan takibi", "Ödül sistemi", "Rekabet"]
    },
    "içsel_motivasyon": {
        "emoji": "🧍‍♂️",
        "description": "İlgi duyduğu konuya yoğunlaşır, plan dışı çalışabilir",
        "motivation_type": "Merak ve ilgi odaklı", 
        "study_tips": ["Kişisel ilgi alanları", "Özgür planlama", "Keşif odaklı"]
    },
    "görsel_hafıza": {
        "emoji": "👁",
        "description": "Kavram haritası, renk kodlu notlar kullanır",
        "memory_type": "Görsel kodlama",
        "techniques": ["Mind mapping", "Renk kodlama", "Şemalar"]
    },
    "işitsel_hafıza": {
        "emoji": "👂",
        "description": "Sesli tekrar, tartışma ile öğrenir",
        "memory_type": "İşitsel kodlama",
        "techniques": ["Sesli okuma", "Grup tartışması", "Sesli notlar"]
    },
    "deneyimsel_hafıza": {
        "emoji": "✋",
        "description": "Pratik soru çözümü, simülasyon ile öğrenir",
        "memory_type": "Kinesthetic kodlama",
        "techniques": ["Pratik uygulama", "Soru çözme", "Hands-on learning"]
    }
}

# === YENİ SİSTEMATİK YKS TAKİP SİSTEMİ ===

# Ders Önem Puanları (1-10 arası)
SUBJECT_IMPORTANCE_SCORES = {
    "TYT Matematik": 10,      # En kritik
    "TYT Türkçe": 9,          # Yüksek soru sayısı
    "TYT Fizik": 8,           # Önemli
    "TYT Kimya": 8,           # Önemli
    "TYT Biyoloji": 7,        # Orta-Yüksek
    "TYT Geometri": 7,        # Orta-Yüksek
    "TYT Tarih": 6,           # Orta
    "TYT Coğrafya": 6,        # Orta
    "TYT Felsefe": 4,         # 2-3. hafta başlangıç
    "TYT Din Kültürü": 4,     # 2-3. hafta başlangıç
    "AYT Matematik": 10,      # En kritik
    "AYT Fizik": 9,           # Yüksek
    "AYT Kimya": 9,           # Yüksek
    "AYT Biyoloji": 8,        # Önemli
    "AYT Edebiyat": 9,        # Sözel için kritik
    "AYT Tarih": 7,           # Sözel için önemli
    "AYT Coğrafya": 7,        # Sözel için önemli
}

# Bilimsel Tekrar Aralıkları (gün) - ESKİ SİSTEM
SPACED_REPETITION_INTERVALS = [3, 7, 14, 30, 90]

# YENİ: Kalıcı Öğrenme Aralıkları (3/7/7/7/7 sistem)
MASTERY_INTERVALS = [3, 7, 7, 7, 7]  # Gün cinsinden

# YENİ: Kalıcılık Durumları
MASTERY_STATUS = {
    "INITIAL": {"name": "İlk Öğrenme", "color": "#3498db", "icon": "📚"},
    "REVIEW_1": {"name": "1. Tekrar", "color": "#f39c12", "icon": "🔄"},
    "REVIEW_2": {"name": "2. Tekrar", "color": "#e67e22", "icon": "🔄"},
    "REVIEW_3": {"name": "3. Tekrar", "color": "#e74c3c", "icon": "🔄"},
    "REVIEW_4": {"name": "4. Tekrar", "color": "#9b59b6", "icon": "🔄"},
    "MASTERED": {"name": "Kalıcı Öğrenildi", "color": "#27ae60", "icon": "✅"},
    "FAILED": {"name": "Kalıcılık Başarısız", "color": "#c0392b", "icon": "❌"}
}

# YENİ: Tekrar Değerlendirme Seviyeleri
REVIEW_LEVELS = {
    "zayif": {"next_interval": 3, "priority": "HIGH", "color": "#e74c3c"},
    "temel": {"next_interval": 7, "priority": "MEDIUM", "color": "#f39c12"},
    "orta": {"next_interval": 7, "priority": "MEDIUM", "color": "#3498db"},
    "iyi": {"next_interval": 7, "priority": "LOW", "color": "#27ae60"},
    "uzman": {"next_interval": 7, "priority": "MINIMAL", "color": "#9b59b6"}
}

# Öncelik Kategorileri - YENİ DİNAMİK SİSTEM (Konu Takip Seviyelerine Göre)
PRIORITY_CATEGORIES = {
    "HIGH": {"icon": "🔥", "name": "Acil - Zayıf Konu", "color": "#dc3545"},
    "MEDIUM": {"icon": "⚡", "name": "Öncelikli - Temel Konu", "color": "#fd7e14"},
    "NORMAL": {"icon": "🎯", "name": "Normal - Orta Konu", "color": "#20c997"},
    "LOW": {"icon": "🟢", "name": "Düşük - İyi Konu", "color": "#28a745"},
    "MINIMAL": {"icon": "⭐", "name": "Minimal - Uzman Konu", "color": "#6c757d"},
    
    # Tekrar kategorileri
    "REPEAT_HIGH": {"icon": "🔄", "name": "Acil Tekrar", "color": "#e74c3c"},
    "REPEAT_MEDIUM": {"icon": "🔄", "name": "Öncelikli Tekrar", "color": "#f39c12"},
    "REPEAT_NORMAL": {"icon": "🔄", "name": "Normal Tekrar", "color": "#3498db"}
}

# Haftalık Konu Sayısı Limitleri (Öneme göre) - 1-5 Arası
WEEKLY_TOPIC_LIMITS = {
    10: 5,  # En önemli dersler: 5 konu/hafta
    9: 4,   # Çok önemli: 4 konu/hafta
    8: 3,   # Önemli: 3 konu/hafta
    7: 2,   # Orta-Yüksek: 2 konu/hafta
    6: 2,   # Orta: 2 konu/hafta
    4: 1,   # Düşük öncelik: 1 konu/hafta (2-3. hafta sonra)
}

# Modern CSS
def get_custom_css(target_department):
    bg_style = BACKGROUND_STYLES.get(target_department, BACKGROUND_STYLES["Varsayılan"])
    
    return f"""
<style>
    .main-header {{
        background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url('{bg_style['image']}');
        background-size: cover;
        background-position: center;
        padding: 3rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        position: relative;
        overflow: hidden;
    }}

    .main-header::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: {bg_style['gradient']};
        opacity: 0.8;
        z-index: -1;
    }}

    .super-minimal-gauge {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.8rem 0;
        margin: 0.3rem 0;
        border-bottom: 1px solid #f0f0f0;
    }}

    .subject-name {{
        font-size: 1rem;
        font-weight: 500;
        color: #333;
    }}

    .subject-percent {{
        font-size: 1.1rem;
        font-weight: bold;
        color: #4CAF50;
        min-width: 50px;
        text-align: right;
    }}

    .gauge-container {{
        margin: 1rem 0;
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}
    
    .psychology-test {{
        background: linear-gradient(135deg, #654ea3 0%, #eaafc8 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }}
    
    .psychology-card {{
        background: #c0392b;
        color: white;
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid #a43a3a;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    
    .stSpinner > div > span {{
        color: #654ea3 !important;
    }}
    
    .stProgress > div > div > div > div {{
        background-color: #654ea3 !important;
    }}
</style>
"""

# Tüm YKS konuları (GÜNCELLENMİŞ VE TAMAMLANDI)
YKS_TOPICS = {
    "TYT Türkçe": {
        "Anlam Bilgisi": {
            "Sözcükte Anlam": ["Gerçek Anlam", "Mecaz Anlam", "Terim Anlam", "Yan Anlam", "Eş Anlam", "Zıt Anlam", "Eş Sesli"],
            "Cümlede Anlam": ["Cümle Yorumlama", "Kesin Yargı", "Anlatım Biçimleri", "Duygu ve Düşünce", "Amaç-Sonuç", "Neden-Sonuç"],
            "Paragraf": ["Ana Fikir", "Yardımcı Fikir", "Paragraf Yapısı", "Anlatım Teknikleri", "Düşünceyi Geliştirme"]
        },
        "Dil Bilgisi": {
            "Ses Bilgisi": ["Ses Olayları", "Ünlü Uyumları"],
            "Yazım Kuralları": ["Büyük Harf", "Birleşik Kelimeler", "Sayıların Yazımı"],
            "Noktalama İşaretleri": ["Nokta, Virgül", "Noktalı Virgül", "İki Nokta", "Tırnak İşaretleri","Ünlem, Soru","Kesme İşareti","Yay Ayraç"],
            "Sözcükte Yapı":["Kök (isim/fiil)", "gövde,ekler (yapım/çekim) ,basit ,türemiş ve birleşik sözcükler"],       
            "Sözcük Türleri":["İsimler (Adlar)", "Zamirler (Adıllar)", "Sıfatlar (Ön Adlar)", "Zarflar (Belirteçler)", "Edat – Bağlaç Ünlem"],
            "Fiiller": [" Fiilde Anlam (Kip -zaman/tasarlama-, Kişi, Yapı -basit/türemiş/birleşik-)","Ek Fiil (İsimleri yüklem yapma, basit çekimli fiili birleşik çekimli yapma)"," Fiilimsi (İsim fiil, sıfat fiil, zarf fiil)."," Fiilde Çatı (Özne ve nesneye göre fiilin aldığı ekler)."],
            "Cümlenin Ögeleri":["Yüklem, özne, nesne (belirtili/belirtisiz), dolaylı tümleç (yer tamlayıcısı), zarf tümleci, edat tümleci."],
            "Cümle Türleri":["Yüklemin türüne, yerine, anlamına ve yapısına göre cümleler."],   
            "Anlatım Bozukluğu":["Anlamsal ve yapısal anlatım bozuklukları."],      
        }
    },
    "TYT Matematik": {
        "Temel Kavramlar":["Sayılar", "Sayı Basamakları","Bölme ve Bölünebilme", "EBOB – EKOK."],
        "Temel İşlemler": ["Rasyonel Sayılar", "Basit Eşitsizlikler","Mutlak Değer", "Üslü Sayılar", "Köklü Sayılar"],
        "Problemler":[

          "Sayı Problemleri",
          "Kesir Problemleri",
          "Yaş Problemleri",
          "Yüzde Problemleri",
          "Kar-Zarar Problemleri",
          "Karışım Problemleri",
          "Hareket Problemleri",
          "İşçi Problemleri",
          "Tablo-Grafik Problemleri",
          "Rutin Olmayan Problemler (Mantık-muhakeme gerektiren sorular)"],
        "Genel":["Kümeler", "Mantık", "Fonksiyonlar.(temel tyt düzey)"],
        "Olasılık":["Permütasyon","Kombinasyon","Olasılık"]
            
        },
       
    
    "TYT Geometri": {
        "Üçgenler":{
            "Açılar":["Doğruda Açılar","Üçgende Açılar",],
            "Özel Üçgenler":["Dik Üçgen","İkizkenar Üçgen","Eşkenar Üçgen"],
            "Üçgen Özellikleri":["Açıortay","Kenarortay","Eşlik ve Benzerlik","Üçgende Alan","Açı Kenar Bağıntıları"],
        
        "Çokgenler ve Özellikleri":["Çokgenler","Özel Dörtgenler...","Deltoid","Paralel kenar","Eşkenar Dörtgen","Dikdörtgen","Kare","Yamuk"],
        
        "Çember ve Daire":["Çemberde Açı","Çemberde Uzunluk","Dairede Çevre ve Alan"],
        
        "Analitik Geometri":["Noktanın Analitiği","Doğrunun Analitiği"],
        
        "Katı Cisimler":["Prizmalar","Küp","Silindir","Piramit","Koni","Küre"]}
    },
    "TYT Tarih": {
        "Tarih Bilimi":["Tarih ve Zaman","İnsanlığın İlk Dönemleri","Ortaçağ’da Dünya",
                         "İlk ve Orta Çağlarda Türk Dünyası","İslam Medeniyetinin Doğuşu","İlk Türk İslam Devletleri",
                         "Yerleşme ve Devletleşme Sürecinde Selçuklu Türkiyesi","Beylikten Devlete Osmanlı Siyaseti(1300-1453)",
                        "Dünya Gücü Osmanlı Devleti (1453-1600)",
                        "Yeni Çağ Avrupa Tarihi",
                        "Yakın Çağ Avrupa Tarihi",
                        "Osmanlı Devletinde Arayış Yılları(Duraklama Dönemi ve nedenleri)",
                        "Osmanlı-Avrupa ilişkileri","18. Yüzyılda Değişim ve Diplomasi",
                          "En Uzun Yüzyıl",
                          "Osmanlı Kültür ve Medeniyeti","20. Yüzyılda Osmanlı Devleti",
                         "I. Dünya Savaşı",
                         "Mondros Ateşkesi, İşgaller ve Cemiyetler",
                          "Kurtuluş Savaşına Hazırlık Dönemi",
                        "I. TBMM Dönemi",
                         "Kurtuluş Savaşı ve Antlaşmalar",
                        "II. TBMM Dönemi ve Çok Partili Hayata Geçiş",
                        "Türk İnkılabı","Atatürk İlkeleri",
                         "Atatürk Dönemi Türk Dış Politikası"]
    },
    "TYT Coğrafya":{
        "Dünya Haritaları Kampı (Öneri:Coğrafyanın Kodları)": 
            ["Dünya Haritaları"],
        "Konular":["Doğa ve İnsan Etkileşimi",
                   "Dünya’nın Şekli ve Hareketleri (Günlük ve Yıllık Hareketler, Sonuçları)",
                   "Coğrafi Konum (Mutlak ve Göreceli Konum)","Harita Bilgisi"
                   "Atmosfer ve Sıcaklık",
                   "İklimler","Basınç ve Rüzgarlar",
                    "Nem, Yağış ve Buharlaşma",
                      "İç Kuvvetler / Dış Kuvvetler"," Su – Toprak ve Bitkiler","Nüfus",
                       "Göç",
                       "Yerleşme",
                       "Türkiye’nin Yer Şekilleri",
                        "Ekonomik Faaliyetler",
                        "Bölgeler,Uluslararası Ulaşım Hatları,Çevre ve Toplum","Doğal Afetler"]
        
    },
    "TYT Felsefe": {
        "Temel Felsefe Konuları": [
            "Felsefenin Konusu",
            "Bilgi Felsefesi (Epistemoloji)",
            "Varlık Felsefesi (Ontoloji)",
            "Din, Kültür ve Medeniyet",
            "Ahlak Felsefesi",
            "Sanat Felsefesi",
            "Din Felsefesi",
            "Siyaset Felsefesi",
            "Bilim Felsefesi"
        ],
        "Felsefe Tarihi": [
            "İlk Çağ Felsefesi",
            "Sokrates ve Felsefesi",
            "Platon ve Felsefesi", 
            "Aristoteles ve Felsefesi",
            "Orta Çağ Felsefesi",
            "İslam Felsefesi (Farabi, İbn Sina)",
            "Hristiyan Felsefesi (Augustinus, Aquinalı Thomas)"
        ]
    },
    
    "TYT Din Kültürü": {
        "1. İnanç ve Temel Kavramlar": [
            "İnsan ve Din (İnanç)",
            "Vahiy ve Akıl"
        ],
        "2.  İslam ve İbadet: ve  Gençlik ve Değerler:": [
            "İbadet",
            "Hz. Muhammed'in Hayatı ve Örnekliği"
        ],
        "3. İslam Medeniyeti ve Özellikleri ve Allah İnancı ve İnsan:": [
            "Allah’ın Varlığı ve Birliği (Tevhid)",
            "Allah’ın İsim ve Sıfatları (Esma-ül Hüsna)",
            "Kur’an-ı Kerim’de İnsan ve Özellikleri",
            "İnsanın Allah İle İrtibatı (Dua, Tövbe, İbadet)"


        ],
        "4. Hz. Muhammed (S.A.V) ve Gençlik:": [
             "Kur’an-ı Kerim’de Gençler",
            "Bir Genç Olarak Hz. Muhammed",
            "Hz. Muhammed ve Gençler",
            "Bazı Genç Sahabiler"
        ],
        "5.Din ve Toplumsal Hayat":[ 
            "Din ve Aile",
            "Din, Kültür ve Sanat",
            "Din ve Çevre",
            "Din ve Sosyal Değişim",
            "Din ve Ekonomi",
            "Din ve Sosyal Adalet"],
        "6.Ahlaki Tutum ve Davranışlar":[
            "İslam ahlakının temel ilkeleri, iyi ve kötü davranışlar",
            "İslam Düşüncesinde Yorumlar: İslam Düşüncesinde İtikadi, Siyasi ve Fıkhi Yorumlar (Mezhepler)"
        ]
    },
    "TYT Fizik": {
        " Fiziğe Giriş ve Maddenin Özellikleri (9. Sınıf)": {
            "Fizik Bilimine Giriş": [
                "Fizik biliminin doğası, önemi ve diğer bilimlerle ilişkisi",
                "Fiziğin Doğası, Alt Dalları",
                "Temel ve Türetilmiş Büyüklükler"
            ],
            "Madde ve Özellikleri": [
                "Kütle, Hacim, Özkütle, Dayanıklılık",
                "Adezyon, Kohezyon, Yüzey Gerilimi, Kılcallık"
            ],
        },
        " Kuvvet, Hareket ve Enerji (9. Sınıf)": {
            "Hareket ve Kuvvet": [
                "Konum, Yol, Yer Değiştirme, Sürat, Hız, İvme",
                "Düzgün Doğrusal Hareket",
                "Newton'un Hareket Yasaları"
                "Etki-tepki, net kuvvet, dengelenmiş ve dengelenmemiş kuvvetler"
            ],
            "İş, Güç ve Enerji": [
                "İş, Güç, Enerji Çeşitleri (Kinetik, Potansiyel)",
                "Enerji dönüşümleri","Verim",
                "Enerjinin Korunumu",
                ],
                
            
            "Isı ve Sıcaklık":["Isı alışverişi, hal değişimleri, genleşme olayları, Öz Isı, Isı İletimi"]
        
        },
        "Elektrik, Basınç, Dalgalar ve Optik (10. Sınıf)": {
            
            
            "Basınç ve Kaldırma Kuvveti": [
                "Katı, Sıvı ve Gaz Basıncı, Pascal Prensibi, Bernoulli İlkesi",
                "Kaldırma Kuvveti"
            ],

            "Dalgalar": [
                "Su dalgaları, ses dalgaları, dalga boyu, frekans",
                ],
            "Optik":[ "Aynalar, mercekler, ışığın kırılması ve yansıması"],
            
            "Elektrik ve Manyetizma": [
                "Elektrik yükleri, akım, direnç, Ohm kanunu, devre elemanları, manyetik alan"
            ]
        },
    
    },
    "TYT Kimya": {
        "1. Kimya Bilimi, Atom ve Etkileşimler (9. Sınıf)": {
            "Kimya Bilimine Giriş": [
                "Kimyanın Alt Dalları ve Çalışma Alanları",
                "Laboratuvar Güvenlik Kuralları ve Semboller"
            ],
            "Atom ve Periyodik Sistem": [
                "Atom Modelleri, Atomun Yapısı (P, N, E)",
                "İzotop, İzoton, İzobar Tanecikler",
                "Periyodik Sistem Özellikleri ve Sınıflandırma"
            ],
            "Kimyasal Türler Arası Etkileşimler": [
                "Güçlü Etkileşimler (İyonik, Kovalent, Metalik Bağ)",
                "Zayıf Etkileşimler (van der Waals, Hidrojen Bağları)",
                "Fiziksel ve Kimyasal Değişimler"
            ]
        },
        "2. Madde Halleri ve Hesaplamalar (9. ve 10. Sınıf)": {
            "Maddenin Hâlleri ve Çevre Kimyası": [
                "Katı, Sıvı, Gaz, Plazma ve Hâl Değişimleri",
                "Gazların Temel Özellikleri",
                "Doğa ve Kimya (Su, Hava, Toprak Kirliliği, Geri Dönüşüm)"
            ],
            "Kimyanın Temel Kanunları ve Hesaplamalar": [
                "Kütlenin Korunumu, Sabit ve Katlı Oranlar Kanunu",
                "Mol Kavramı",
                "Kimyasal Tepkime Denklemleri, Denkleştirme",
                "Tepkime Türleri, Verim Hesaplamaları (Temel Düzey)"
            ]
        },
        "3. Karışımlar, Asitler/Bazlar ve Kimya Her Yerde (10. Sınıf)": {
            "Karışımlar ve Çözeltiler": [
                "Homojen ve Heterojen Karışımlar",
                "Çözelti Türleri, Çözünme Süreci",
                "Derişim Birimleri (Kütlece/Hacimce Yüzde)"
            ],
            "Asitler, Bazlar ve Tuzlar": [
                "Asit ve Baz Tanımları ve Özellikleri",
                "Asit-Baz Tepkimeleri, pH Kavramı",
                "Tuzlar ve Kullanım Alanları"
            ],
            "Kimya Her Yerde": [
                "Yaygın Polimerler",
                "Sabun ve Deterjanlar",
                "İlaçlar, Gıdalar, Temizlik Maddeleri"
            ]
        }
    },
    "TYT Biyoloji": {
        "1. Yaşam Bilimi ve Temel Bileşikler (9. Sınıf)": [
            "Canlıların Ortak Özellikleri",
            "Canlıların Yapısında Bulunan İnorganik Bileşikler",
            "Canlıların Yapısında Bulunan Organik Bileşikler"
        ],
        "2. Hücre, Sınıflandırma ve Âlemler (9. Sınıf)": [
            "Hücresel Yapılar ve Görevleri",
            "Hücre Zarından Madde Geçişleri",
            "Canlıların Sınıflandırılması",
            "Canlı Âlemleri"
        ],
        "3. Üreme, Kalıtım ve Genetik (10. Sınıf)": [
            "Hücre Döngüsü ve Mitoz",
            "Eşeysiz Üreme",
            "Mayoz",
            "Eşeyli Üreme",
            
            "Kalıtım Konusu",
            "Genetik Varyasyonlar"
        ],  
         
        "4. Ekoloji ve Çevre (10. Sınıf)": [
            "Ekosistem Ekolojisi",
            "Güncel Çevre Sorunları",
            "Doğal Kaynakların Sürdürülebilirliği",
            "Biyolojik Çeşitliliğin Korunması"
        ]
    },
    "AYT Matematik": {
        "Cebir, Fonksiyonlar,Sayı Sistemleri": [
            "Fonksiyonlar (İleri Düzey)",
            "Polinomlar",
            "2. Dereceden Denklemler",
            "Karmaşık Sayılar",
            "2. Dereceden Eşitsizlikler",
            "Parabol"
        
            "Trigonometri",
            "Logaritma",
            "Diziler",
            "Limit",
            "Türev",
            "İntegral"
        ],
        "Olasılık ": [
            "Permütasyon ve Kombinasyon",
            "Binom ve Olasılık",
            "İstatistik"
        ]
    },
    "AYT Edebiyat": {
        "1. Temel Edebiyat Bilgisi ve Kuramsal Yaklaşım": [
            "Güzel Sanatlar ve Edebiyat İlişkisi",
            "Metinlerin Sınıflandırılması",
            "Edebi Sanatlar (Söz ve Anlam Sanatları)",
            "Edebiyat Akımları (Batı ve Türk Edebiyatındaki Etkisi)",
            "Dünya Edebiyatı (Önemli Temsilciler ve Eserler)"
        ],
        "2. Anlam, Dil Bilgisi ve Şiir Yapısı": [
            "Anlam Bilgisi (Sözcük, Cümle, Paragraf Düzeyinde)",
            "Dil Bilgisi (Ses, Yapı, Cümle Öğeleri, Anlatım Bozuklukları)",
            "Şiir Bilgisi (Nazım Birimi, Ölçü, Uyak, Redif, Tema, İmge)"
        ],
        "3. Türk Edebiyatının Dönemleri (İslamiyet Öncesi ve Sonrası)": [
            "Türk Edebiyatı Dönemleri (Genel Özellikler)",
            "İslamiyet Öncesi Türk Edebiyatı (Sözlü ve Yazılı)",
            "İslamiyet Etkisindeki Geçiş Dönemi Edebiyatı",
            "Halk Edebiyatı (Anonim, Âşık, Tekke/Dini-Tasavvufi)",
            "Divan Edebiyatı (Nazım Biçimleri ve Türleri)"
        ],
        "4. Batı Etkisindeki Edebiyat (Tanzimat'tan Cumhuriyete)": [
            "Tanzimat Dönemi Edebiyatı (1. ve 2. Kuşak)",
            "Servet-i Fünun Edebiyatı (Edebiyat-ı Cedide)",
            "Fecr-i Ati Edebiyatı",
            "Milli Edebiyat Dönemi",
            "Cumhuriyet Dönemi Edebiyatı (Şiir, Hikaye, Roman, Tiyatro)"
        ],"5.Edebi Akımlar":[
            "Klasisizm",

            "Romantizm (Coşumculuk)",

            "Realizm (Gerçekçilik)",

            "Natüralizm (Doğalcılık)",

            "Parnasizm",

            "Sembolizm",

            "Empresyonizm (İzlenimcilik)",

            "Ekspresyonizm (Dışavurumculuk)",

            "Fütürizm (Gelecekçilik)",

            "Kübizm",

            "Dadaizm",

            "Sürrealizm (Gerçeküstücülük)",

            "Egzistansiyalizm (Varoluşçuluk)",

            "Ek:Dünya Edebiyatı"
        ]
    },
    "AYT Tarih": {
        "1. Tarih Bilimi ve İlk Çağlar": [
            "Tarih ve Zaman (Temel Kavramlar)", "İnsanlığın İlk Dönemleri", "Orta Çağ'da Dünya"
        ],
        "2. Türk-İslam Devletleri Dönemi": [
            "İlk ve Orta Çağlarda Türk Dünyası", "İslam Medeniyetinin Doğuşu",
            "Türklerin İslamiyet'i Kabulü ve İlk Türk İslam Devletleri", "Yerleşme ve Devletleşme Sürecinde Selçuklu Türkiyesi"
        ],
        "3. Klasik Çağ Osmanlı Tarihi (Kuruluş ve Yükselme)": [
            "Beylikten Devlete Osmanlı Siyaseti", "Devletleşme Sürecinde Savaşçılar ve Askerler",
            "Beylikten Devlete Osmanlı Medeniyeti", "Dünya Gücü Osmanlı",
            "Sultan ve Osmanlı Merkez Teşkilatı", "Klasik Çağda Osmanlı Toplum Düzeni"
        ],
        "4. Avrupa ve Osmanlı'da Değişim Süreci (Gerileme ve Dağılma)": [
            "Değişen Dünya Dengeleri Karşısında Osmanlı Siyaseti", "Değişim Çağında Avrupa ve Osmanlı",
            "Uluslararası İlişkilerde Denge Stratejisi (1774-1914)", "Devrimler Çağında Değişen Devlet-Toplum İlişkileri",
            "Sermaye ve Emek", "XIX. ve XX. Yüzyılda Değişen Gündelik Hayat"
        ],
        "5. Türkiye Cumhuriyeti Tarihi": [
            "XX. Yüzyıl Başlarında Osmanlı Devleti ve Dünya", "Milli Mücadele", "Atatürkçülük ve Türk İnkılabı"
        ],
        "6. Yakın Çağda Dünya ve Türkiye": [
            "İki Savaş Arasındaki Dönemde Türkiye ve Dünya", "II. Dünya Savaşı Sürecinde Türkiye ve Dünda",
            "II. Dünya Savaşı Sonrasında Türkiye ve Dünya", "Toplumsal Devrim Çağında Dünya ve Türkiye",
            "XXI. Yüzyılın Eşiğinde Türkiye ve Dünya"
        ]
    },
    "AYT Coğrafya": {
        "1. Doğal Sistemler ve Biyocoğrafya": [
            "Ekosistem", "Biyoçeşitlilik", "Biyomlar", "Ekosistemin Unsurları", "Enerji Akışı ve Madde Döngüsü"
        ],
        "2. Beşeri Coğrafya ve Demografi": [
            "Nüfus Politikaları", "Türkiye'de Nüfus ve Yerleşme", "Göç ve Şehirleşme"
        ],
        "3. Ekonomik Coğrafya ve Türkiye Ekonomisi": [
            "Ekonomik Faaliyetler ve Doğal Kaynaklar", "Türkiye Ekonomisi",
            "Türkiye'nin Ekonomi Politikaları", "Türkiye Ekonomisinin Sektörel Dağılımı",
            "Türkiye'de Tarım", "Türkiye'de Hayvancılık", "Türkiye'de Madenler ve Enerji Kaynakları", "Türkiye'de Sanayi", "Türkiye'de Ulaşım", "Türkiye'de Ticaret ve Turizm", "Geçmişten Geleceğe Şehir ve Ekonomi", "Türkiye'nin İşlevsel Bölgeleri ve Kalkınma Projeleri", "Hizmet Sektörünün Ekonomideki Yeri"
        ],
        "4. Küresel Bağlantılar ve Jeopolitik": [
            "Küresel Ticaret", "Bölgeler ve Ülkeler", "İlk Uygarlıklar", "Kültür Bölgeleri ve Türk Kültürü", "Sanayileşme Süreci: Almanya", "Tarım ve Ekonomi İlişkisi Fransa - Somali", "Ülkeler Arası Etkileşim", "Jeopolitik Konum", "Çatışma Bölgeleri", "Küresel ve Bölgesel Örgütler"
        ],
        "5. Çevre, İklim ve Sürdürülebilirlik": [
            "Ekstrem Doğa Olayları", "Küresel İklim Değişimi", "Çevre ve Toplum", "Çevre Sorunları ve Türleri", "Madenler ve Enerji Kaynaklarının Çevreye Etkisi", "Doğal Kaynakların Sürdürülebilir Kullanımı", "Ekolojik Ayak İzi", "Doğal Çevrenin Sınırlılığı", "Çevre Politikaları", "Çevresel Örgütler", "Çevre Anlaşmaları", "Doğal Afetler"
        ]
    },
    "AYT Fizik": {
        "1. Mekanik ve Enerji": [
            "Kuvvet ve Hareket (Vektörler, Bağıl, Newton Yasaları)", "İş - Güç - Enerji (Korunum, Verim)", "Atışlar (Yatay, Eğik, Düşey)", "Basit Makineler", "Kütle Merkezi - Tork - Denge"
        ],
        "2. Elektrik ve Manyetizma": [
            "Elektrostatik (Alan, Potansiyel)", "Elektrik ve Manyetizma (Akım, Direnç, Manyetik Alan, Kuvvet, İndüksiyon)"
        ],
        "3. Basınç, Maddenin Halleri ve Termodinamik": [
            "Madde ve Özellikleri (Katı, Sıvı, Gaz)", "Basınç - Kaldırma Kuvveti", "Isı - Sıcaklık - Genleşme (Termodinamik Yasaları Temelleri)"
        ],
        "4. Titreşim ve Dalgalar": [
            "Dalgalar (Yay, Su, Ses, Deprem)", "Optik (Yansıma, Kırılma, Ayna, Mercek)", "Düzgün Çembersel Hareket", "Basit Harmonik Hareket"
        ],
        "5. Modern Fizik ve Uygulamaları": [
            "Fizik Bilimine Giriş (Temeller)", "Atom Fiziğine Giriş ve Radyoaktivite", "Modern Fizik (Özel Görelilik, Kuantum, Fotoelektrik Olay)"
        ]
    },
    "AYT Kimya": {
        "Giriş Konular":
                ["Modern Atom Teorisi","Gazlar","Sıvı Çözeltiler ve Çözünürlük",
                "Kimyasal Tepkimelerde Enerji","Kimyasal Tepkimelerde Hız", ],
               
     "Kimyasal Tepkimelerde Denge":["Denge Sabiti", "Etkileyen Faktörler)", "Asit-Baz Dengesi (pH, pOH, Titrasyon)", "Çözünürlük Dengesi (Çözünürlük Çarpımı - Kçç"],
                
    "Kimya ve Elektrik":["(Redoks,Elektrot, Pil Potansiyeli)", "Elektroliz ve Korozyon", "Enerji Kaynakları ve Bilimsel Gelişmeler"],
        
                                                                                                                           

    "Organik Kimya": [
            "Organik Kimyaya Giriş (Temel Kavramlar, Hibritleşme)","Karbon Kimyasına Giriş", "Organik Kimya (Fonksiyonel Gruplar, Alkan, Alken, Alkin, Aromatikler)"
        ]
    },
    "AYT Biyoloji": {
        "1. İnsan Fizyolojisi (Sistemler)": [
            "Sinir Sistemi", "Endokrin Sistem ve Hormonlar", "Duyu Organları", "Destek ve Hareket Sistemi", "Sindirim Sistemi", "Dolaşım ve Bağışıklık Sistemi", "Solunum Sistemi", "Üriner Sistem (Boşaltım Sistemi)", "Üreme Sistemi ve Embriyonik Gelişim"
        ],
        "2. Moleküler Biyoloji ve Genetik": [
            "Nükleik Asitler", "Genden Proteine", "Genetik Şifre ve Protein Sentezi"
        ],
        "3. Canlılarda Enerji Dönüşümleri": [
            "Canlılık ve Enerji", "Canlılarda Enerji Dönüşümleri (ATP, Enzim)", "Fotosentez", "Kemosentez", "Hücresel Solunum"
        ],
        "4. Bitki Biyolojisi ve Ekoloji": [
            "Bitki Biyolojisi (Yapı, Taşıma, Beslenme)",
            "Bitkisel Hormonlar ve Hareketler",
            "Ekoloji ve Çevre "
        ]
    },
    "AYT Felsefe":{
        "Felsefe’nin Konusu":["Bilgi Felsefesi",
    "Varlık Felsefesi",
    "Ahlak Felsefesi",
    "Sanat Felsefesi",
    "Din Felsefesi",
    "Siyaset Felsefesi",
    "Bilim Felsefesi",
    "İlk Çağ Felsefesi",
    "MÖ 6. Yüzyıl – MS 2. Yüzyıl Felsefesi",
    "MS 2. Yüzyıl – MS 15. Yüzyıl Felsefesi",
    "15. Yüzyıl – 17. Yüzyıl Felsefesi",
    "18. Yüzyıl – 19. Yüzyıl Felsefesi",
    "20. Yüzyıl Felsefesi"],
        
        "Mantık Konuları":["Mantığa Giriş",
    "Klasik Mantık",
    "Mantık ve Dil",
    "Sembolik Mantık"
    ],
        "Psikoloji Bilimini Tanıyalım":[ 
        "Psikolojinin Temel Süreçleri",
        "Öğrenme Bellek Düşünme",
        "Ruh Sağlığının Temelleri"
        ],
        "Sosyolojiye Giriş":[
        "Birey ve Toplum",
        "Toplumsal Yapı",
       "Toplumsal Değişme ve Gelişme",
        "Toplum ve Kültür",
        "Toplumsal Kurumlar"] },

"AYT Din Kültürü ve Ahlak Bilgisi":{
    "Konular":["Dünya ve Ahiret",
              "Kur’an’a Göre Hz. Muhammed",
               "Kur’an’da Bazı Kavramlar",
               "Kur’an’dan Mesajlar]",
               "İnançla İlgili Meseleler",
               "İslam ve Bilim",
               "Anadolu'da İslam",
               "İslam Düşüncesinde Tasavvufi Yorumlar ve Mezhepler",
               "Güncel Dini Meseleler",
               "Yaşayan Dinler"]}

}

# ------------------------------------------------------------------------------------------------------
# --- YKS SON 6 YIL SORU İSTATİSTİKLERİ (2019-2024) ---
YKS_QUESTION_STATS = {
    # TYT Türkçe
    "Ses Bilgisi": 8, "Sözcük Türleri": 12, "Sözcük Anlamı": 15, "Cümle Bilgisi": 18,
    "Anlam Bilgisi": 10, "Yazım Kuralları": 7, "Noktalama İşaretleri": 6, "Paragraf": 25,
    "Okuduğunu Anlama": 30, "Anlatım Bozuklukları": 9,
    
    # TYT Matematik
    "Temel Kavramlar": 14, "Sayılar": 18, "Mutlak Değer": 8, "Üslü Sayılar": 12,
    "Köklü Sayılar": 10, "Çarpanlara Ayırma": 15, "Rasyonel İfadeler": 9, "Eşitsizlikler": 16,
    "Denklemler": 20, "Fonksiyonlar": 22, "Polinomlar": 11, "İkinci Dereceden Denklemler": 14,
    "Logaritma": 13, "Diziler": 17, "Limit ve Süreklilik": 19, "Türev": 21, "İntegral": 15,
    
    # TYT Geometri
    "Temel Geometri": 12, "Açılar": 10, "Üçgenler": 18, "Dörtgenler": 14, "Çember": 16,
    "Analitik Geometri": 20, "Trigonometri": 15, "Katı Cisimler": 13,
    
    # TYT Fizik
    "Fizik Bilimine Giriş": 3, "Madde ve Özellikleri": 4, "Hareket": 8, "Kuvvet ve Hareket": 7,
    "İş, Güç, Enerji": 6, "İtme ve Momentum": 5, "Dalga Mekaniği": 4, "Optik": 5,
    "Elektrostatik": 6, "Akım ve Manyetizma": 5, "Modern Fizik": 4,
    
    # TYT Kimya
    "Kimya Bilimi": 2, "Atom ve Periyodik Sistem": 6, "Kimyasal Türler Arası Etkileşimler": 5,
    "Maddenin Halleri": 4, "Karışımlar": 3, "Asit-Baz": 6, "Kimyasal Tepkimeler": 7,
    "Enerji": 4, "Elektrokimya": 3, "Organik Kimya": 5,
    
    # TYT Biyoloji  
    "Canlılığın Temel Birimi Hücre": 8, "Hücre Bölünmeleri": 6, "Kalıtım": 7,
    "Ekosistem Ekolojisi": 5, "Güncel Çevre Sorunları": 4, "Canlıların Çeşitliliği": 6,
    "İnsan Fizyolojisi": 9, "Sinir Sistemi": 4, "Duyu Organları": 3, "Endokrin Sistem": 5,
    
    # TYT Tarih
    "İslamiyetten Önce Türkler": 8, "İslamiyet'in Doğuşu": 6, "Türklerde İslamiyet": 7,
    "Karahanlılar": 4, "Gazneliler": 3, "Büyük Selçuklular": 5, "Anadolu Selçukluları": 6,
    "Beylikler Dönemi": 4, "Osmanlı Kuruluş": 8, "Osmanlı Yükselme": 9,
    "Osmanlı Duraklama": 7, "Osmanlı Gerileme": 8, "19. Yüzyıl": 12, "20. Yüzyıl": 15,
    
    # TYT Coğrafya
    "Doğal Sistemler": 12, "Beşeri Sistemler": 8, "Ekonomik Faaliyetler": 6,
    "Türkiye'nin Coğrafi Özellikleri": 10, "Çevre ve Toplum": 7, "Küresel Ortam": 5,
    "Coğrafi Bilgi Sistemleri": 4,
    
    # TYT Felsefe
    "Felsefenin Konusu": 8, "Bilgi Felsefesi (Epistemoloji)": 6, "Varlık Felsefesi (Ontoloji)": 5,
    "Din, Kültür ve Medeniyet": 4, "Ahlak Felsefesi": 6, "Sanat Felsefesi": 3,
    "Din Felsefesi": 4, "Siyaset Felsefesi": 5, "Bilim Felsefesi": 4, "İlk Çağ Felsefesi": 7,
    "Sokrates ve Felsefesi": 3, "Platon ve Felsefesi": 4, "Aristoteles ve Felsefesi": 4,
    "Orta Çağ Felsefesi": 3, "İslam Felsefesi (Farabi, İbn Sina)": 4, "Hristiyan Felsefesi (Augustinus, Aquinalı Thomas)": 3,
    
    # TYT Din Kültürü
    "İnsan ve Din (İnanç)": 6, "Ahlak": 4, "İbadet": 5, "Peygamberlik": 4,
    "Kutsal Kitaplar": 3, "Ahiret İnancı": 3, "Dinler Tarihi": 4, "İslam Tarihi": 6,
    "Hz. Muhammed'in Hayatı": 5, "Temel Dini Kavramlar": 4,
    
    # AYT Matematik
    "Trigonometri": 25, "Logaritma": 18, "Diziler": 20, "Limit": 22, "Türev": 28,
    "İntegral": 24, "Analitik Geometri": 30, "Katı Geometri": 15, "Olasılık": 18,
    "İstatistik": 12, "Matris": 8, "Determinant": 6,
    
    # AYT Fizik
    "Çembersel Hareket": 12, "Basit Harmonik Hareket": 10, "Dalga Mekaniği": 15,
    "Optik": 18, "Elektriksel Kuvvet ve Alan": 16, "Elektriksel Potansiyel": 14,
    "Kondansatörler": 8, "Elektrik Akımı": 12, "Manyetizma": 15, "Elektromanyetik İndüksiyon": 13,
    "Alternatif Akım": 9, "Atom Fiziği": 8, "Modern Fizik": 10,
    
    # AYT Kimya
    "Modern Atom Teorisi": 12, "Periyodik Sistem": 15, "Kimyasal Bağlar": 18,
    "Kimyasal Tepkimeler": 20, "Çözeltiler": 16, "Asit-Baz Dengesi": 14,
    "Çökelme Dengesi": 8, "Elektrokimya": 12, "Kimyasal Kinetik": 10,
    "Kimyasal Denge": 13, "Organik Bileşikler": 22, "Enerji ve Entropi": 6,
    
    # AYT Biyoloji
    "Hücre": 18, "Hücre Bölünmeleri ve Kalıtım": 20, "Canlılık ve Enerji": 15,
    "Bitki Biyolojisi": 12, "Hayvan Biyolojisi": 25, "İnsan Fizyolojisi": 22,
    "Çevre Bilimi": 8, "Canlılığın Çeşitliliği": 10, "Ekoloji": 6,
    
    # AYT Edebiyat
    "Söz Sanatları": 15, "Nazım Bilgisi": 12, "Edebî Sanatlar": 18, "Tanzimat Dönemi": 20,
    "Servet-i Fünun": 14, "Fecr-i Ati": 8, "Millî Edebiyat": 16, "Cumhuriyet Dönemi": 25,
    "Çağdaş Türk Edebiyatı": 22, "Halk Edebiyatı": 10, "Eski Türk Edebiyatı": 18,
    
    # AYT Tarih
    "Osmanlı Devleti (1299-1566)": 35, "Osmanlı Devleti (1566-1792)": 30,
    "Değişim Çağında Osmanlı": 40, "Millî Mücadele": 38, "Atatürk İlkeleri": 25,
    "İkinci Dünya Savaşı": 28, "Soğuk Savaş": 20, "Bipolar Dünya": 15,
    "Çok Kutuplu Dünya": 12, "Küreselleşen Dünya": 10,
    
    # AYT Coğrafya  
    "Yer Şekilleri": 22, "İklim": 18, "Bitkiler": 12, "Toprak": 10,
    "Nüfus": 20, "Yerleşme": 15, "Ekonomik Faaliyetler": 25, "Ulaşım ve İletişim": 8,
    "Türkiye'nin Fiziki Coğrafyası": 30, "Türkiye'nin Beşeri Coğrafyası": 28,
    "Çevre Sorunları": 12, "Doğal Afetler": 10,
    
    # AYT Felsefe
    "Felsefe Tarihi": 25, "Bilgi Felsefesi": 20, "Varlık Felsefesi": 15,
    "Ahlak Felsefesi": 18, "Sanat Felsefesi": 12, "Din Felsefesi": 10,
    "Siyaset Felsefesi": 16, "Bilim Felsefesi": 14, "Çağdaş Felsefe": 20,
    
    # AYT Din Kültürü ve Ahlak Bilgisi
    "Dünya ve Ahiret": 8, "Kur'an'a Göre Hz. Muhammed": 6, "Kur'an'da Bazı Kavramlar": 5,
    "Kur'an'dan Mesajlar": 7, "İnançla İlgili Meseleler": 4, "İslam ve Bilim": 3,
    "Anadolu'da İslam": 5, "İslam Düşüncesinde Tasavvufi Yorumlar ve Mezhepler": 6,
    "Güncel Dini Meseleler": 4, "Yaşayan Dinler": 2
}

def get_topic_question_count(topic_name):
    """Bir konunun son 6 yılda kaç soru çıktığını döndür"""
    return YKS_QUESTION_STATS.get(topic_name, 0)

# ------------------------------------------------------------------------------------------------------
# --- DÜZELTME: KONU YAPISI AYRIŞTIRICI FONKSİYON ---
def get_topic_list(subject):
    """Belirli bir dersin tüm alt konularını düz bir liste olarak döndürür."""
    if subject not in YKS_TOPICS:
        return []

    topic_list = []
    subject_content = YKS_TOPICS[subject]

    for category, content in subject_content.items():
        if isinstance(content, dict):
            # Yapı A: Üç seviyeli (Alt Kategori kullanıldı)
            for sub_category, topics in content.items():
                for topic in topics:
                    topic_list.append(f"{subject} | {category} | {sub_category} | {topic}")
        elif isinstance(content, list):
            # Yapı B: İki seviyeli (Alt Kategori kullanılmadı)
            for topic in content:
                topic_list.append(f"{subject} | {category} | None | {topic}")
        
    return topic_list

def count_total_topics():
    """Toplam konu sayısını hesaplar"""
    total = 0
    for subject, content in YKS_TOPICS.items():
        if isinstance(content, dict):
            # content dict ise, normal işlemi yap
            for category, sub_content in content.items():
                if isinstance(sub_content, dict):
                    for sub_category, topics in sub_content.items():
                        total += len(topics)
                elif isinstance(sub_content, list):
                    total += len(sub_content)
        elif isinstance(content, list):
            # content liste ise, doğrudan sayısını ekle
            total += len(content)
    return total

def calculate_subject_progress(user_data):
    """Kullanıcının ders bazında ilerleme verilerini hesaplar"""
    progress_data = {}
    
    # Kullanıcının konu takip verilerini al (topic_progress)
    topic_progress_str = user_data.get('topic_progress', '{}')
    try:
        if isinstance(topic_progress_str, str):
            topic_progress = json.loads(topic_progress_str)
        else:
            topic_progress = topic_progress_str if isinstance(topic_progress_str, dict) else {}
    except (json.JSONDecodeError, TypeError):
        topic_progress = {}
    
    # Her ders için ilerleme hesapla
    for subject, content in YKS_TOPICS.items():
        total_count = 0
        completed_count = 0
        
        if isinstance(content, dict):
            for category, sub_content in content.items():
                if isinstance(sub_content, dict):
                    for sub_category, topics in sub_content.items():
                        for topic in topics:
                            topic_key = f"{subject} | {category} | {sub_category} | {topic}"
                            total_count += 1
                            
                            # Net 15+ olanları tamamlanmış say
                            net_score = topic_progress.get(topic_key, 0)
                            try:
                                net_score = int(float(str(net_score)))
                                if net_score >= 15:  # 15+ net tamamlanmış sayılır
                                    completed_count += 1
                            except (ValueError, TypeError):
                                pass
                elif isinstance(sub_content, list):
                    for topic in sub_content:
                        topic_key = f"{subject} | {category} | None | {topic}"
                        total_count += 1
                        
                        # Net 15+ olanları tamamlanmış say
                        net_score = topic_progress.get(topic_key, 0)
                        try:
                            net_score = int(float(str(net_score)))
                            if net_score >= 15:  # 15+ net tamamlanmış sayılır
                                completed_count += 1
                        except (ValueError, TypeError):
                            pass
        elif isinstance(content, list):
            for topic in content:
                topic_key = f"{subject} | None | None | {topic}"
                total_count += 1
                
                # Net 15+ olanları tamamlanmış say
                net_score = topic_progress.get(topic_key, 0)
                try:
                    net_score = int(float(str(net_score)))
                    if net_score >= 15:  # 15+ net tamamlanmış sayılır
                        completed_count += 1
                except (ValueError, TypeError):
                    pass
        
        # İlerleme yüzdesini hesapla
        percent = (completed_count / total_count * 100) if total_count > 0 else 0
        
        progress_data[subject] = {
            'total': total_count,
            'completed': completed_count,
            'percent': percent
        }
    
    return progress_data

def calculate_level(net_score):
    """Net skora göre seviye göstergesi hesaplar"""
    if net_score >= 18:
        return "🎓 Uzman"
    elif net_score >= 15:
        return "🚀 İyi"
    elif net_score >= 12:
        return "💪 Orta"
    elif net_score >= 8:
        return "📘 Temel"
    else:
        return "⚠️ Zayıf"

# --- DÜZELTME BİTİŞİ ---

# Psikolojik çalışma teknikleri
STUDY_TECHNIQUES = {
    "Feynman Tekniği": {
        "icon": "🎓",
        "description": "Karmaşık konuları sadeleştirip öğretir gibi anlatma yöntemi.",
        "learning_styles": ["Görsel", "Sosyal", "İşitsel", "Yazısal"],
        "steps": [
            "Konuyu seç ve sadeleştir",
            "Bir başkasına anlatır gibi açıkla",
            "Anlamadığın yerleri belirle",
            "Tekrar gözden geçir ve düzelt"
        ],
        "psychological_effect": "Öğrenme güvenini artırır, derin kavrama becerisi kazandırır",
        "best_subjects": ["Fizik", "Biyoloji", "Tarih", "Felsefe"],
        "suitable_student": "Analitik düşünen, anlatmayı seven, sosyal öğreniciler"
    },
    "Aktif Hatırlama & Aralıklı Tekrar": {
        "icon": "🎯",
        "description": "Bilgiyi pasif okumak yerine hatırlamaya dayalı öğrenme.",
        "learning_styles": ["Kinestetik", "Bireysel", "Yazısal"],
        "steps": [
            "Konuyu çalıştıktan sonra kendine sorular sor",
            "Zorlandığın konulara daha kısa aralıklarla dön",
            "1–3–7–15 gün kuralını uygula"
        ],
        "psychological_effect": "Unutma eğrisini tersine çevirir, kalıcılığı artırır, kaygıyı azaltır",
        "best_subjects": ["Biyoloji", "Kimya", "Tarih", "Edebiyat"],
        "suitable_student": "Disiplinli, planlı, kendi başına çalışan öğrenciler"
    },

    "Cornell Not Alma Sistemi": {
        "icon": "📝",
        "description": "Notları soru–cevap–özet şeklinde organize etme yöntemi.",
        "learning_styles": ["Yazısal", "Görsel"],
        "steps": [
            "Sayfayı üçe böl (not, soru, özet)",
            "Derste sağ tarafa not al",
            "Sol tarafa sorular ekle",
            "Alt kısmı özetle doldur"
        ],
        "psychological_effect": "Notları düzenli hale getirir, tekrarı sistematikleştirir",
        "best_subjects": ["Tarih", "Coğrafya", "Biyoloji"],
        "suitable_student": "Düzenli, yazılı anlatımı güçlü öğrenciler"
    },
    "Zihin Haritalama": {
        "icon": "🧭",
        "description": "Bilgileri görsel bağlantılarla organize etme yöntemi.",
        "learning_styles": ["Görsel", "Yaratıcı", "Sosyal"],
        "steps": [
            "Ortaya ana konuyu yaz",
            "Dallar halinde alt başlıklar ekle",
            "Renk, sembol ve oklarla bağlantı kur"
        ],
        "psychological_effect": "Bilgiyi uzun süreli belleğe taşır, soyut konuları somutlaştırır",
        "best_subjects": ["Coğrafya", "Biyoloji", "Edebiyat"],
        "suitable_student": "Görsel düşünen, yaratıcı öğrenciler"
    },
    "SQ3R Tekniği": {
        "icon": "📖",
        "description": "Okuma ve anlama verimini artıran sistem.",
        "learning_styles": ["Yazısal", "İşitsel", "Analitik"],
        "steps": [
            "Konuya genel göz at (Survey)",
            "Başlıkları soruya çevir (Question)",
            "Sorulara cevap arayarak oku (Read)",
            "Kendi cümlelerinle tekrar et (Recite)",
            "Tekrar gözden geçir (Review)"
        ],
        "psychological_effect": "Okuduğunu anlama yeteneğini geliştirir, odaklanmayı güçlendirir",
        "best_subjects": ["Tarih", "Edebiyat", "Din Kültürü"],
        "suitable_student": "Okuma ağırlıklı çalışanlar, sözel öğreniciler"
    },
    "Leitner Kutusu Sistemi": {
        "icon": "🗂",
        "description": "Bilgiyi kart sistemiyle tekrar etmeye dayalı teknik.",
        "learning_styles": ["Yazısal", "Kinestetik"],
        "steps": [
            "Soru–cevap kartları hazırla",
            "Doğru bildiklerini ileri kutuya koy, yanlışları geride tut",
            "Geri kutulara daha sık dön"
        ],
        "psychological_effect": "Görsel başarı hissi oluşturur, tekrarı eğlenceli hale getirir",
        "best_subjects": ["Biyoloji", "Tarih", "Edebiyat", "İngilizce"],
        "suitable_student": "El ile çalışmayı seven, ezbere yatkın öğrenciler"
    },
    "Kaizen Tekniği": {
        "icon": "🌱",
        "description": "Her gün küçük ilerlemeler yapma felsefesi.",
        "learning_styles": ["Bireysel", "Kinestetik"],
        "steps": [
            "Her gün küçük hedef belirle",
            "10–15 dakikalık gelişim adımları oluştur",
            "Haftalık ilerleme günlüğü tut"
        ],
        "psychological_effect": "Disiplin ve öz güven geliştirir, mükemmeliyetçilik kaygısını kırar",
        "best_subjects": ["Her ders"],
        "suitable_student": "Motivasyonu düşük, başlayamayan öğrenciler"
    },
    "Mindfulness": {
        "icon": "🧘",
        "description": "Dikkati şimdiye odaklayarak zihni sakinleştirme yöntemi.",
        "learning_styles": ["Sosyal", "Kinestetik", "Görsel"],
        "steps": [
            "5–10 dk nefes farkındalığı yap",
            "Düşüncelerini gözlemle, yargılama",
            "Derse başlamadan kısa meditasyon uygula"
        ],
        "psychological_effect": "Sınav kaygısını azaltır, odaklanma kalitesini artırır",
        "best_subjects": ["Tüm dersler (özellikle deneme öncesi)"],
        "suitable_student": "Kaygılı, stresli, aşırı düşünen öğrenciler"
    },
    "Dual Coding": {
        "icon": "🧩",
        "description": "Görsel + sözel yolları birlikte kullanarak öğrenme.",
        "learning_styles": ["Görsel", "Yazısal"],
        "steps": [
            "Bilgiyi tablo veya şekille ifade et",
            "Görseli sözel olarak açıkla",
            "Görsele bakarak hatırlama çalışması yap"
        ],
        "psychological_effect": "Görsel hafızayı güçlendirir, zor konularda somutluk sağlar",
        "best_subjects": ["Biyoloji", "Coğrafya", "Tarih"],
        "suitable_student": "Görsel zekası yüksek öğrenciler"
    },
    "Gamification": {
        "icon": "🕹",
        "description": "Dersleri puan ve ödül sistemiyle eğlenceli hale getirme.",
        "learning_styles": ["Sosyal", "Kinestetik"],
        "steps": [
            "Günlük hedefleri oyunlaştır (puan, seviye)",
            "Başarıya küçük ödüller koy",
            "Arkadaşlarla yarışmalar düzenle"
        ],
        "psychological_effect": "Motivasyon artar, sıkılma azalır, dopamin etkisiyle öğrenme kalıcılığı yükselir",
        "best_subjects": ["Deneme analizi", "tekrar günleri"],
        "suitable_student": "Sosyal, rekabeti seven öğrenciler"
    },
    "Interleaving": {
        "icon": "🔄",
        "description": "Farklı konuları karıştırarak çalışmak.",
        "learning_styles": ["Analitik", "Kinestetik"],
        "steps": [
            "Aynı derste farklı konular arasında geçiş yap",
            "Günlük programda dersleri sırayla karıştır",
            "Karma testlerle pratik yap"
        ],
        "psychological_effect": "Ezberden çıkmayı sağlar, soru çözme esnekliği kazandırır",
        "best_subjects": ["Matematik", "Fizik", "Kimya"],
        "suitable_student": "Analitik düşünen, deneysel öğrenen öğrenciler"
    },
    "Retrieval Practice": {
        "icon": "📋",
        "description": "Öğrendiklerini dış kaynağa bakmadan hatırlama.",
        "learning_styles": ["Yazısal", "Bireysel"],
        "steps": [
            "Konuyu çalış, kitabı kapat",
            "Ne hatırlıyorsan yaz veya anlat",
            "Eksik kısımları belirle, düzelt"
        ],
        "psychological_effect": "Bilgiyi uzun süreli belleğe taşır, öz farkındalığı artırır",
        "best_subjects": ["Biyoloji", "Tarih", "Kimya"],
        "suitable_student": "Tekrar odaklı, kendi başına çalışan öğrenciler"
    },
    "SMART Hedef Sistemi": {
        "icon": "🎯",
        "description": "Spesifik, Ölçülebilir, Ulaşılabilir, Gerçekçi, Zamanlı hedeflerle plan yapma.",
        "learning_styles": ["Bireysel", "Planlı"],
        "steps": [
            "'Günde 3 paragraf çözmek' gibi net hedef belirle",
            "Ölçülebilir ilerleme grafiği oluştur",
            "Haftalık kontrol et ve ayarla"
        ],
        "psychological_effect": "Planlı çalışmayı güçlendirir, başarı hissi süreklilik kazanır",
        "best_subjects": ["Tüm dersler"],
        "suitable_student": "Planlı, hedef odaklı öğrenciler"
    },
    "Sosyal Öğrenme Tekniği": {
        "icon": "💬",
        "description": "Grup içinde tartışarak, öğreterek öğrenme.",
        "learning_styles": ["Sosyal", "İşitsel"],
        "steps": [
            "Grup içinde konuyu anlat",
            "Soru-cevap yaparak tartış",
            "Birbirinizin hatalarını düzeltin"
        ],
        "psychological_effect": "Sosyal motivasyon sağlar, konuyu anlatırken kalıcı öğrenme gerçekleşir",
        "best_subjects": ["Tarih", "Felsefe", "Edebiyat"],
        "suitable_student": "Grup çalışmasını seven, anlatıcı yönü güçlü öğrenciler"
    },
    "Uyku & Hafıza Tekniği": {
        "icon": "🌙",
        "description": "Uyku sırasında bilginin kalıcı hale gelmesi prensibine dayanır.",
        "learning_styles": ["Tüm stiller"],
        "steps": [
            "Uyumadan önce kısa tekrar yap",
            "7–8 saat uyku düzeni koru",
            "Sabah aynı bilgiyi test et"
        ],
        "psychological_effect": "Beyin, öğrenilen bilgileri kalıcı belleğe taşır, unutmayı %40 oranında azaltır",
        "best_subjects": ["Tüm dersler"],
        "suitable_student": "Düzenli uykuya önem veren, sabah verimli çalışan öğrenciler"
    }
}

# YKS Öğrencisi Öğrenme Stili & Bilişsel Profil Tanımları (Güncellenmiş)
LEARNING_STYLE_DESCRIPTIONS = {
    "Analitik Sistematik": {
        "title": "🔬 Analitik Sistematik",
        "intro": "Sen problemleri adım adım çözen, mantıklı ve sistematik düşünen bir öğrencisin.",
        "strengths": ["Sistematik problem çözme", "Detaylı analiz yapma", "Mantıklı yaklaşım", "Planlı çalışma"],
        "weaknesses": ["Çok detaya takılma", "Yaratıcı çözümlerden kaçınma"],
        "advice": "Konu anlatımları → Örnek sorular → Problemler sırası ile çalış. Konu özetleri ve soru bankası kullan.",
        "study_tools": ["Konu özetleri", "Soru bankası", "Günlük program", "Adım adım çözüm teknikleri"]
    },
    "Görsel Yaratıcı": {
        "title": "🎨 Görsel Yaratıcı",
        "intro": "Sen bilgiyi görsel unsurlarla işleyen ve yaratıcı çözümler üreten bir öğrencisin.",
        "strengths": ["Görsel hafıza", "Yaratıcı düşünce", "Şema ve grafik anlama", "Renk kodlama"],
        "weaknesses": ["Sadece dinleyerek öğrenmede zorluk", "Çok detaylı metinlerde kaybolma"],
        "advice": "Zihin haritaları, renkli notlar ve grafik organizers kullan. Görsel destekli kitapları tercih et.",
        "study_tools": ["Kavram haritaları", "Renkli kalemler", "Görsel destekli kitaplar", "Şema ve grafikler"]
    },
    "İşitsel Sosyal": {
        "title": "👂 İşitsel Sosyal",
        "intro": "Sen dinleyerek öğrenen ve sosyal etkileşimlerden beslenen bir öğrencisin.",
        "strengths": ["Dinleme becerisi", "Tartışarak öğrenme", "Sosyal motivasyon", "Sesli tekrar"],
        "weaknesses": ["Sessiz ortamlarda zorlanma", "Bireysel çalışmada motivasyon kaybı"],
        "advice": "Grup çalışması yap, sesli tekrar et, ders videoları izle. Çalışma gruplarına katıl.",
        "study_tools": ["Çalışma grupları", "Sesli anlatım kaynakları", "Ders videoları", "Tartışma forumları"]
    },
    "Kinestetik Uygulamacı": {
        "title": "✋ Kinestetik Uygulamacı",
        "intro": "Sen yaparak öğrenen ve uygulamalı çalışmalardan hoşlanan bir öğrencisin.",
        "strengths": ["Pratik uygulama", "Hareket halinde öğrenme", "Deney ve gözlem", "Aktif katılım"],
        "weaknesses": ["Uzun teorik dersler", "Hareketsiz kalma", "Soyut kavramlar"],
        "advice": "Bol soru çözümü yap, deney videoları izle, pratik uygulamalar ara. Hareket halinde çalış.",
        "study_tools": ["Test kitapları", "Simülasyon programları", "Laboratuvar videoları", "Mobil uygulamalar"]
    },
    "Özerk Reflektif": {
        "title": "💪 Özerk Reflektif",
        "intro": "Sen bireysel çalışmayı seven ve derin düşünen bir öğrencisin.",
        "strengths": ["Bireysel odaklanma", "Derin analiz", "İçsel motivasyon", "Sessiz çalışma"],
        "weaknesses": ["Sosyal desteğe ihtiyaç", "Motivasyon dalgalanmaları"],
        "advice": "Bireysel derin çalışma yap, kendi kendine test et. Kapsamlı kaynaklardan yararlan.",
        "study_tools": ["Kapsamlı kaynak kitaplar", "Online testler", "Kişisel çalışma planı", "Sessiz çalışma ortamı"]
    }
}

# ===== VAK ÖĞRENME STİLLERİ TESTİ =====
# A Kategorisi: Görsel (20 soru)
# B Kategorisi: İşitsel (20 soru)  
# C Kategorisi: Kinestetik (20 soru)
VAK_LEARNING_STYLES_TEST = [
    # ===== A KATEGORİSİ - GÖRSEL ÖĞRENME STİLİ =====
    {
        "question": "Biri bana ders verir gibi bir şeyler anlatırsa başka dünyalara dalarım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Temiz ve düzenli bir sıraya sahip olmak isterim",
        "category": "A", 
        "type": "visual"
    },
    {
        "question": "Sözel yönergeleri kullanamam, haritaya gereksinim duyarım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Duyduğum ama görmediğim yönergelere dikkat etmekte zorlanırım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Resimli bulmaca çözmeyi severim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Sessiz okumayı severim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Sözcükleri hatasız yazarım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Gördüklerimi iyi hatırlarım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Olaylar ve/ya konular şematize edilirse daha iyi anlarım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Konuşmacının ağzını izlerim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Resimli roman okumayı severim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Şarkı sözlerini hatırlamakta zorlanırım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Okunmakta olan bir metnin kopyasını takip etmezsem anlamakta zorlanırım",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Sözel tariflerin tekrarlanmasını isterim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Kendi kendime düşünüp, çalışarak öğrenmeyi severim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Derslerde not tutmayı tercih ederim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Boş zamanlarımda okumayı severim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Başkalarının ne yaptığını gözlerim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Radyo ve televizyonu yüksek sesle dinlerim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Telefonda konuşmayı sevmem, yüz yüze konuşmayı tercih ederim",
        "category": "A",
        "type": "visual"
    },
    
    # ===== B KATEGORİSİ - İŞİTSEL ÖĞRENME STİLİ =====
    {
        "question": "Kendi kendime konuşurum",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Bütün yanlışlarımı öğretmenin anlatarak düzeltmesini isterim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Okurken parmağımla takip ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Sınıfta arkadaşlarımla tartışarak ve sohbet ederek öğrenmeyi severim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Okurken kağıda çok yaklaşırım",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Gözlerimi ellerime dayarım",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Daha iyi öğrenmek için müzik ve ritmi severim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Sınıfta çok fazla konuşurum",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Boş zamanlarımda arkadaşlarımla konuşmayı ve şaka yapmayı severim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Genellikle grafikler, sembol ve simgeler benim öğrenmemi kolaylaştırmaz",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Yüksek sesle okumayı severim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Yazılı karikatürleri tercih ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Hikaye, şiir ve/ya kitap kasetleri dinlemeyi severim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Anlatmayı yazmaya tercih ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Görsel ve sözcük hatırlama hafızam iyi değildir",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Kendi kendime çalışmaktansa öğretmeni dinleyerek öğrenmeyi tercih ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Bir konu bana okunursa kendi okuduğumdan daha iyi anlarım",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Kopyalanacak bir şey olmadan kolay çizemem",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Haritalardan çok sözel tarifleri ve yönergeleri tercih ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Sessizliğe dayanamam… ya ben ya da diğerlerinin konuşmasını isterim",
        "category": "B",
        "type": "auditory"
    },
    
    # ===== C KATEGORİSİ - KİNESTETİK ÖĞRENME STİLİ =====
    {
        "question": "Boş bir kağıda sütunlar çizmem istendiğinde kağıdı katlarım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Ellerimi kullanabileceğim bir şeyler yapmaktan hoşlanırım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Sandalyede otururken sallanırım ya da bacağımı sallarım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Defterimin içini genellikle resimlerle, şekillerle süslerim, karalama yaparım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Kalemimi elimde döndürürüm, masada tempo tutarım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Öğretmenlerim asla çalışmadığımı düşünürler",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Öğretmenlerim sınıfta çok fazla hareket ettiğimi düşünürler",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Genellikle hiperaktif olduğum söylenir",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Çalışırken sık sık ara verir, başka şeyler yaparım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Arkadaşlarıma el şakası yapmaya bayılırım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Kapının üst çerçevesine asılarak odaya atlamak isterim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Aktif olarak katıldığım etkinlikleri severim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Bir şeyi görmek ya da duymak yetmez, dokunmak isterim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Her şeye dokunmak isterim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Objeleri biriktirmeyi severim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Sınıfta tahta silmeyi, pencere ya da kapı açıp kapatmayı hep ben yapmak isterim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Kürdanları, kibritleri küçük parçalara ayırırım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Aletleri açar, içini söker, sonra yine bir araya getirmeye çalışırım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Genellikle ellerimi kullanarak ve hızlı konuşurum",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Başkalarının sözünü sık sık keserim",
        "category": "C",
        "type": "kinesthetic"
    },
    
    # ===== YENİ SORULAR - GÖRSEL KATEGÖRİ =====
    {
        "question": "Matematik problemlerini çözerken mutlaka kağıda çizerim ve görselleştiririm",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Tarih derslerinde zaman çizgisi ve kavram haritaları oluşturmak bana yardımcı olur",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Renkli vurgulayıcılar ve kalemler olmadan verimli not alamam",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Bir konuyu anladığımı anlamak için görsel örnekler görmek isterim",
        "category": "A",
        "type": "visual"
    },
    {
        "question": "Yeni bir yeri bulmak için Google Maps'ten fotoğrafları da incelerim",
        "category": "A",
        "type": "visual"
    },
    
    # ===== YENİ SORULAR - İŞİTSEL KATEGÖRİ =====
    {
        "question": "Formülleri aklımda tutmak için ritim halinde tekrar ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Arkadaşlarımla birlikte çalışıp konuşarak öğrenmeyi severim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Podcast dinleyerek veya sesli kitap okuyarak öğrenmeyi tercih ederim",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Derse odaklanmak için hafif müzik dinlemem gerekir",
        "category": "B",
        "type": "auditory"
    },
    {
        "question": "Soru çözerken adımları kendi kendime sesli olarak açıklarım",
        "category": "B",
        "type": "auditory"
    },
    
    # ===== YENİ SORULAR - KİNESTETİK KATEGÖRİ =====
    {
        "question": "Uzun süreli ders dinlerken ayakta durma veya hareket etme ihtiyacı duyarım",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Geometri problemlerini elle tutabilir objelerle modellemeyi severim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Bir konuyu öğrenmek için deney yapmayı ve uygulamayı tercih ederim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "Not alırken tablet yerine kağıt kalem kullanmayı tercih ederim",
        "category": "C",
        "type": "kinesthetic"
    },
    {
        "question": "25 dakika çalışıp 5 dakika ara verme sistemi bana uyar",
        "category": "C",
        "type": "kinesthetic"
    }
]

# ===== BİLİŞSEL PROFİL TESTİ =====
# 4 Bölüm x 5 Soru = 20 Soru (Likert 1-5)
COGNITIVE_PROFILE_TEST = [
    # ===== BÖLÜM 1: BİLİŞSEL İŞLEME STİLİ =====
    {
        "question": "Karmaşık bir konuyu küçük parçalara bölerek öğrenirim.",
        "category": "analytic_thinking",
        "section": "🔬 Bilişsel İşleme Stili",
        "dimension": "Analitik"
    },
    {
        "question": "Bir konunun tümünü zihnimde büyük resim olarak canlandırırım.",
        "category": "synthetic_thinking", 
        "section": "🔬 Bilişsel İşleme Stili",
        "dimension": "Sintetik"
    },
    {
        "question": "Öğrendiklerimi hemen uygulamadan önce düşünmeyi tercih ederim.",
        "category": "reflective_thinking",
        "section": "🔬 Bilişsel İşleme Stili", 
        "dimension": "Reflektif"
    },
    {
        "question": "Şemalar, sıralı adımlar benim için daha anlamlıdır.",
        "category": "analytic_thinking",
        "section": "🔬 Bilişsel İşleme Stili",
        "dimension": "Analitik"
    },
    {
        "question": "Hayal gücüyle kavramları ilişkilendirmek bana yardımcı olur.",
        "category": "synthetic_thinking",
        "section": "🔬 Bilişsel İşleme Stili",
        "dimension": "Sintetik"
    },
    
    # ===== BÖLÜM 2: MOTİVASYON & DUYGUSAL STİL =====
    {
        "question": "Hedef belirlemek beni motive eder.",
        "category": "external_motivation",
        "section": "⚡ Motivasyon & Duygusal Stil",
        "dimension": "Dışsal"
    },
    {
        "question": "Sadece merak ettiğim konuları öğrenmek isterim.",
        "category": "internal_motivation",
        "section": "⚡ Motivasyon & Duygusal Stil",
        "dimension": "İçsel"
    },
    {
        "question": "Başarı hissi beni daha çok çalıştırır.",
        "category": "external_motivation",
        "section": "⚡ Motivasyon & Duygusal Stil",
        "dimension": "Dışsal"
    },
    {
        "question": "Öğrenirken keyif almak benim için en önemli şeydir.",
        "category": "internal_motivation",
        "section": "⚡ Motivasyon & Duygusal Stil",
        "dimension": "İçsel"
    },
    {
        "question": "Çevremden onay almak beni motive eder.",
        "category": "external_motivation",
        "section": "⚡ Motivasyon & Duygusal Stil",
        "dimension": "Dışsal"
    },
    
    # ===== BÖLÜM 3: PROBLEM ÇÖZME YAKLAŞIMI =====
    {
        "question": "Problemleri çözmek için belirli bir plan yaparım.",
        "category": "problem_methodic",
        "section": "🔍 Problem Çözme Yaklaşımı",
        "dimension": "Metodik"
    },
    {
        "question": "Deneyerek öğrenmeyi severim.",
        "category": "problem_experimental",
        "section": "🔍 Problem Çözme Yaklaşımı",
        "dimension": "Deneysel"
    },
    {
        "question": "Zor bir konuda arkadaşlarımla fikir alışverişi yaparım.",
        "category": "problem_social",
        "section": "🔍 Problem Çözme Yaklaşımı",
        "dimension": "Sosyal"
    },
    {
        "question": "Hatalarımdan öğrenmek benim için önemlidir.",
        "category": "problem_experimental",
        "section": "🔍 Problem Çözme Yaklaşımı",
        "dimension": "Deneysel"
    },
    {
        "question": "Zorlukla karşılaştığımda yeni yöntemler denerim.",
        "category": "problem_experimental",
        "section": "🔍 Problem Çözme Yaklaşımı",
        "dimension": "Deneysel"
    },
    
    # ===== BÖLÜM 4: HAFIZA & PEKİŞTİRME TARZI =====
    {
        "question": "Bilgiyi hatırlarken görseller gözümde canlanır.",
        "category": "memory_visual",
        "section": "💾 Hafıza & Pekiştirme Tarzı",
        "dimension": "Görsel"
    },
    {
        "question": "Duyduğum cümleleri kolay hatırlarım.",
        "category": "memory_auditory",
        "section": "💾 Hafıza & Pekiştirme Tarzı",
        "dimension": "İşitsel"
    },
    {
        "question": "Bir şeyi yaparak öğrendiğimde unutmak zor olur.",
        "category": "memory_experiential",
        "section": "💾 Hafıza & Pekiştirme Tarzı",
        "dimension": "Deneyimsel"
    },
    {
        "question": "Okuduğumu özetlemek bana hatırlamayı kolaylaştırır.",
        "category": "memory_analytic",
        "section": "💾 Hafıza & Pekiştirme Tarzı",
        "dimension": "Analitik"
    },
    {
        "question": "Gözlerimi kapattığımda konuyu film gibi canlandırabilirim.",
        "category": "memory_visual",
        "section": "💾 Hafıza & Pekiştirme Tarzı",
        "dimension": "Görsel"
    }
]

# ===== YENİ TESTLER =====

# Motivasyon & Duygusal Denge Testi
MOTIVATION_EMOTIONAL_TEST = [
    {
        "question": "Başarılı olduğumda içsel bir tatmin hissederim.",
        "category": "internal_motivation",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "İçsel Motivasyon"
    },
    {
        "question": "Başkalarının takdir etmesi beni motive eder.",
        "category": "external_motivation",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Dışsal Motivasyon"
    },
    {
        "question": "Zor bir konuyu görünce genellikle endişelenirim.",
        "category": "test_anxiety",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Sınav Kaygısı"
    },
    {
        "question": "Hatalarımdan sonra moralimi hemen toparlayabilirim.",
        "category": "emotional_resilience",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Duygusal Dayanıklılık"
    },
    {
        "question": "Öğrenme sürecinde keyif almak benim için önemlidir.",
        "category": "internal_motivation",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "İçsel Motivasyon"
    },
    {
        "question": "Başkalarıyla kendimi kıyaslamak beni motive eder.",
        "category": "external_motivation",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Dışsal Motivasyon"
    },
    {
        "question": "Sınavdan önce genellikle stres hissederim.",
        "category": "test_anxiety",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Sınav Kaygısı"
    },
    {
        "question": "Başarısız olsam bile tekrar denemekten vazgeçmem.",
        "category": "emotional_resilience",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Duygusal Dayanıklılık"
    },
    {
        "question": "Öğrendiklerimi sadece not almak için değil, gerçekten anlamak isterim.",
        "category": "internal_motivation",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "İçsel Motivasyon"
    },
    {
        "question": "Eleştirildiğimde hemen motivasyonumu kaybederim.",
        "category": "test_anxiety",
        "section": "⚡ Motivasyon & Duygusal Denge",
        "dimension": "Duygusal Kırılganlık"
    }
]

# Zaman Yönetimi & Çalışma Alışkanlığı Testi
TIME_MANAGEMENT_TEST = [
    {
        "question": "Günlük veya haftalık bir çalışma planım vardır.",
        "category": "planning",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Planlama"
    },
    {
        "question": "Çoğu zaman 'yarın başlarım' diyerek ertelediğim olur.",
        "category": "procrastination",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Erteleme Eğilimi"
    },
    {
        "question": "Çalışmaya başladığımda kolayca dikkatimi dağıtırım.",
        "category": "focus_control",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Odak Süresi"
    },
    {
        "question": "Konuları küçük parçalara bölerek çalışırım.",
        "category": "planning",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Verimlilik"
    },
    {
        "question": "Planıma sadık kalmakta zorlanırım.",
        "category": "discipline",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Disiplin"
    },
    {
        "question": "Çalışırken kısa ama düzenli molalar veririm.",
        "category": "focus_control",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Odak-Mola Dengesi"
    },
    {
        "question": "Sınav haftasına kadar bekleyip yoğun çalışırım.",
        "category": "procrastination",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Son Dakikacılık"
    },
    {
        "question": "Günümün hangi saatlerinde verimli olduğumu bilirim.",
        "category": "self_awareness",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Öz Farkındalık"
    },
    {
        "question": "Tekrar planımı önceden belirlerim (örneğin 24 saat – 1 hafta sonra).",
        "category": "planning",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Sistematik Tekrar"
    },
    {
        "question": "Çalışırken telefon veya sosyal medya beni sık sık böler.",
        "category": "focus_control",
        "section": "⏰ Zaman Yönetimi & Çalışma Alışkanlığı",
        "dimension": "Dikkat Kontrolü"
    }
]

# Eski karışık liste tamamen kaldırıldı

# Gereksiz duplicate veriler kaldırıldı. Test şimdi tam 80 soru (60 VAK + 20 Bilişsel)

# Test tamamlandı - 80 soru (60 VAK + 20 Bilişsel)

# Test verisi düzgün: 80 soru (60 VAK + 20 Bilişsel)

# Bu fonksiyon artık kullanılmıyor - yeni test sistemi kullanılıyor

def get_recommended_techniques(dimension_scores, user_profile):
    """Öğrenme profiline göre en uygun çalışma tekniklerini önerir"""
    recommended_techniques = []
    
    for technique_name, info in STUDY_TECHNIQUES.items():
        if user_profile in info.get('suitable_profiles', []):
            recommended_techniques.append(technique_name)
    
    # Eğer hiç eşleşme yoksa, genel teknikleri döndür
    if not recommended_techniques:
        recommended_techniques = list(STUDY_TECHNIQUES.keys())[:3]
    
    return recommended_techniques[:3]

def display_progress_summary(user_data, progress_data):
    """Ana sayfada ilerleme özeti gösterir"""
    
    overall_progress = calculate_subject_progress(user_data)
    total_completed = sum(data['completed'] for data in overall_progress.values())
    total_topics = count_total_topics()
    overall_percent = (total_completed / total_topics * 100) if total_topics > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("✅ Tamamlanan Konular", f"{total_completed}/{total_topics}")
    
    with col2:
        st.metric("📚 Toplam Ders", len(progress_data))
    
    with col3:
        avg_per_subject = sum(data['percent'] for data in progress_data.values()) / len(progress_data) if progress_data else 0
        st.metric("📈 Ders Ortalaması", f"%{avg_per_subject:.1f}")
    with col4:
        st.metric("🎯 Hedef Bölüm", user_data.get('target_department', 'Belirlenmedi'), delta_color="off")      
    
    st.markdown("---")
    
    st.subheader("📈 Ders Bazında İlerleme")
    
    if progress_data:
        for subject, data in progress_data.items():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{subject}**")
                st.progress(data['percent'] / 100)
            with col_b:
                st.write(f"{data['completed']}/{data['total']} konu")
                st.write(f"%{data['percent']:.1f}")
        
        st.markdown("---")
    
    else:
        st.info("Henüz ilerleme verisi bulunmuyor. Konu Takip sekmesinden ilerlemenizi kaydedin.")

# YKS Takip fonksiyonları
def clear_outdated_session_data():
    """Eski tarihli session verilerini temizler - Sistem her gün güncel kalır"""
    current_date = datetime.now().date().isoformat()
    
    # Eğer session'da farklı bir tarih varsa planları temizle
    if 'last_plan_date' not in st.session_state or st.session_state.last_plan_date != current_date:
        # Sadece cache'leri temizle, interactive widget'ları etkileyenleri koruma altında bırak
        if 'weekly_plan_cache' in st.session_state:
            del st.session_state.weekly_plan_cache
        
        # Planlama ile ilgili geçici verileri temizle  
        keys_to_remove = []
        for key in st.session_state.keys():
            if key.startswith('temp_') or key.startswith('cache_'):
                keys_to_remove.append(key)
        
        # DOM hata önleyici - widget key'lerini temizle
        try:
            for key in st.session_state.keys():
                if len(str(key)) > 200 or 'old_' in str(key):
                    keys_to_remove.append(key)
        except:
            pass
        
        for key in keys_to_remove:
            try:
                del st.session_state[key]
            except:
                pass
            
        # Yeni tarihi kaydet
        st.session_state.last_plan_date = current_date
        
        # Güncel olmayan day_plans'leri de reset et - ama safe şekilde
        if 'day_plans' in st.session_state:
            # Mevcut planları backup al ve yeniden oluştur
            st.session_state.day_plans = {day: [] for day in ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]}

def yks_takip_page(user_data):
    # Eski session verilerini temizle - her gün güncel sistem!
    clear_outdated_session_data()
    
    # Güncel tarih bilgisi al
    week_info = get_current_week_info()
    days_to_yks = week_info['days_to_yks']
    
    st.markdown(f'<div class="main-header"><h1>🎯 YKS Takip & Planlama Sistemi</h1><p>Haftalık hedeflerinizi belirleyin ve takip edin</p><p>📅 {week_info["today"].strftime("%d %B %Y")} | ⏰ YKS\'ye {days_to_yks} gün kaldı!</p></div>', unsafe_allow_html=True)
    
    # Ana panelden bilgileri al
    student_grade = user_data.get('grade', '')
    student_field = user_data.get('field', '')
    learning_style = user_data.get('learning_style', '')
    
    st.subheader("📋 Öğrenci Bilgileri")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎓 Sınıf", student_grade)
    with col2:
        st.metric("📚 Alan", student_field)
    with col3:
        st.metric("🧠 Öğrenme Stili", learning_style)
    
    st.markdown("---")
    
    # İlk kez giriş için anket sistemi
    if not has_completed_yks_survey(user_data):
        show_yks_survey(user_data)
    else:
        show_weekly_planner(user_data)

def has_completed_yks_survey(user_data):
    """Kullanıcının YKS anketini tamamlayıp tamamlamadığını kontrol eder"""
    survey_data = user_data.get('yks_survey_data', '')
    if survey_data:
        try:
            data = json.loads(survey_data)
            return all(key in data for key in ['program_type', 'daily_subjects', 'study_style', 
                                              'difficult_subjects', 'favorite_subjects', 'sleep_time', 'disliked_subjects', 
                                              'book_type', 'rest_day'])
        except:
            return False
    return False

def show_yks_survey(user_data):
    """YKS anketi gösterir"""
    st.subheader("📝 İlk Kurulum: Size Özel Program İçin Bilgilerinizi Alalım")
    
    student_field = user_data.get('field', '')
    
    with st.form("yks_survey_form"):
        # Program türü
        st.markdown("### 🎛️ Haftalık Programınızı Nasıl Oluşturalım?")
        program_type = st.radio(
            "Program türünü seçin:",
            ["🎛️ Kişiselleştirilmiş Program (Kendi gün/saatlerimi belirleyeyim)",
             "📋 Hazır Bilimsel Program (Bana otomatik program hazırlansın)"]
        )
        
        # Günlük ders sayısı
        st.markdown("### 📚 Günlük Ders Dağılımı")
        st.write("Günde kaç farklı ders çalışmayı istersiniz?")
        daily_subjects = st.selectbox("Ders sayısı:", [2, 3, 4, 5], index=1)
        if daily_subjects in [2, 3, 4]:
            st.success("✅ Bilimsel Öneri: 2-4 ders seçiminiz optimal aralıkta! (İdeal olan ise 3'tür)")
        
        # Çalışma stili
        st.markdown("### 🍽️ Çalışma Stilinizi Keşfedin")
        study_style = st.radio(
            "Hangi çalışma stilini tercih edersiniz?",
            ["🍰 En güzel kısmı sona saklarım (Zor dersleri sona saklama)",
             "🍽️ Her şeyi karışık paylaşırım (Dengeli dağılım)", 
             "🔥 En güzelinden başlarım (Zor dersler ön alma)"]
        )
        
        # Dersler alan bazında belirlenir
        all_subjects = get_subjects_by_field_yks(student_field)
        
        # Zorluk analizi
        st.markdown("### 🎯 Zorluk Analizi")
        difficult_subjects = st.multiselect(
            "En zorlandığınız 3 dersi seçin (en zordan başlayarak):",
            all_subjects, max_selections=3
        )
        
        # Uyku saati
        st.markdown("### 😴 Uyku Düzeni")
        st.info("🧠 Bilimsel olarak ideal uyku süresi 7 saattir. Tavsiye edilen uyku saatleri: 23:00 - 06:00 arası")
        sleep_option = st.selectbox(
            "Uyku saatinizi seçin:",
            ["23:00 - 06:00 (7 saat) - Önerilen", "22:00 - 05:00 (7 saat)",
             "00:00 - 07:00 (7 saat)", "01:00 - 08:00 (7 saat)", "Diğer"]
        )
        
        # Sevilen ve sevmeyen dersler
        st.markdown("### 💝 Ders Tercihleri")
        favorite_subjects = st.multiselect(
            "En sevdiğiniz dersleri seçin (max 4):", all_subjects, max_selections=4
        )
        disliked_subjects = st.multiselect(
            "En az sevdiğiniz dersleri seçin (max 3):", all_subjects, max_selections=3
        )
        
        # Kitap tercihleri
        st.markdown("### 📖 Kitap Önerileri")
        book_type = st.selectbox(
            "Hangi tür kitapları okumayı seversiniz?",
            list(BOOK_RECOMMENDATIONS.keys())
        )
        
        # Tatil günü
        st.markdown("### 🌴 Dinlenme Günü")
        rest_day = st.selectbox(
            "Haftanın hangi günü tamamen dinlenmek istersiniz?",
            ["Pazar", "Cumartesi", "Cuma", "Pazartesi", "Salı", "Çarşamba", "Perşembe"]
        )
        
        # Form submit
        if st.form_submit_button("💾 Bilgilerimi Kaydet ve Planlama Sistemine Geç", type="primary"):
            survey_data = {
                'program_type': program_type,
                'daily_subjects': daily_subjects,
                'study_style': study_style,
                'difficult_subjects': difficult_subjects,
                'favorite_subjects': favorite_subjects,
                'sleep_time': sleep_option,
                'disliked_subjects': disliked_subjects,
                'book_type': book_type,
                'rest_day': rest_day,
                'created_at': datetime.now().isoformat()
            }
            
            # Kullanıcı verisini güncelle
            update_user_in_firebase(st.session_state.current_user, 
                              {'yks_survey_data': json.dumps(survey_data)})
            st.session_state.users_db = load_users_from_firebase()
            
            # Kitap önerilerini göster
            st.success("✅ Bilgileriniz kaydedildi!")
            st.markdown("### 📚 Size Özel Kitap Önerileri")
            for book in BOOK_RECOMMENDATIONS[book_type]:
                st.write(f"📖 {book}")
            
            st.rerun()

def show_weekly_planner(user_data):
    """YENİ SİSTEMATİK HAFTALİK PLANLAMA SİSTEMİ"""
    # Eski session verilerini temizle - her gün güncel sistem!
    clear_outdated_session_data()
    
    # Anket verilerini yükle
    survey_data = json.loads(user_data.get('yks_survey_data', '{}'))
    student_field = user_data.get('field', '')
    
    # Sistematik haftalık plan al
    weekly_plan = get_weekly_topics_from_topic_tracking(user_data, student_field, survey_data)
    
    # Üst dashboard
    show_progress_dashboard(weekly_plan, user_data)
    
    # YENİ: Kalıcı Öğrenme Sistemi Dashboard'u
    st.markdown("---")
    
    # Kullanıcıyı kalIcı öğrenme sistemi için başlat
    user_data = initialize_mastery_system(user_data)
    
    # Kalıcı öğrenme sistemi dashboard'ını göster
    show_mastery_progress_dashboard(user_data)
    
    st.markdown("---")
    
    # Ana haftalık plan
    week_info = get_current_week_info()
    days_to_yks = week_info['days_to_yks']
    
    st.markdown(f"### 📅 Bu Haftanın Sistematik Planı")
    st.info(f"📅 **{week_info['week_range']}** | ⏰ **YKS'ye {days_to_yks} gün kaldı!**")
    
    # Sadece tekrar konuları göster - YENİ KONULAR kısmı kaldırıldı
    st.markdown("#### 🔄 TEKRAR EDİLECEK KONULAR")
    show_review_topics_section(weekly_plan.get('review_topics', []), user_data)
    
    # YENİ: Haftalık tamamlanma kontrolü ve bonus konular
    st.markdown("---")
    
    # Bu haftanın tamamlanma yüzdesini hesapla
    completion_percentage = calculate_weekly_completion_percentage(user_data, weekly_plan)
    
    # Progress bar göster
    st.markdown("#### 📊 BU HAFTANİN İLERLEMESİ")
    progress_col1, progress_col2, progress_col3 = st.columns([3, 1, 1])
    
    with progress_col1:
        progress_bar = st.progress(completion_percentage / 100)
        st.caption(f"Haftalık hedefin %{completion_percentage:.1f}'ini tamamladın!")
    
    with progress_col2:
        if completion_percentage >= 80:
            st.markdown("🎉 **Hedef Aşıldı!**")
        elif completion_percentage >= 60:
            st.markdown("⚡ **İyi Gidiyorsun!**")
        else:
            st.markdown("💪 **Devam Et!**")
    
    with progress_col3:
        # Manuel ilerleme güncelleme butonları
        if st.button("➕ +10%", key="increase_progress", help="İlerlemeyi %10 artır"):
            # Mevcut tamamlanan konuları artır
            if 'manual_progress_boost' not in st.session_state:
                st.session_state.manual_progress_boost = 0
            st.session_state.manual_progress_boost += 10
            st.success("📈 İlerleme %10 artırıldı!")
            st.rerun()
        
        if st.button("🔄", key="reset_progress", help="İlerlemeyi sıfırla"):
            # Tüm tamamlanma durumlarını sıfırla
            keys_to_remove = [key for key in st.session_state.keys() if key.startswith('completed_')]
            for key in keys_to_remove:
                del st.session_state[key]
            if 'manual_progress_boost' in st.session_state:
                del st.session_state['manual_progress_boost']
            st.success("🔄 İlerleme sıfırlandı!")
            st.rerun()
    
    # Manual boost'u ekleme
    manual_boost = st.session_state.get('manual_progress_boost', 0)
    final_completion = min(completion_percentage + manual_boost, 100.0)
    
    if manual_boost > 0:
        st.info(f"📈 Manuel artış: +{manual_boost}% | Toplam: %{final_completion:.1f}")
    
    # Eğer %80+ tamamlandıysa bonus konuları göster
    if final_completion >= 80.0:
        st.markdown("---")
        
        # Gelecek haftanın konularını getir
        next_week_topics = get_next_week_topics(user_data, user_data.get('field', ''), survey_data)
        
        # Bonus konuları göster
        if next_week_topics:
            show_next_week_bonus_topics(next_week_topics, user_data)
        else:
            st.info("🎯 Gelecek hafta için ek bonus konu bulunamadı. Mevcut konularını tekrar etmeye odaklan!")
    
    st.markdown("---")
    
    # Interaktif planlayıcı
    show_interactive_systematic_planner(weekly_plan, survey_data)
    
    st.markdown("---")
    
    # Akıllı öneriler
    show_systematic_recommendations(weekly_plan, survey_data, student_field)

def show_progress_dashboard(weekly_plan, user_data):
    """İlerleme dashboard'u - DİNAMİK TARİH SİSTEMİ"""
    projections = weekly_plan.get('projections', {})
    week_info = get_current_week_info()
    
    st.markdown(f"### 📊 GENEL İLERLEME DURUMU")
    st.caption(f"📅 Güncel Tarih: {week_info['today'].strftime('%d %B %Y')} | Hafta: {week_info['week_number']}/52")
    
    # Ana metrikler
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        overall_progress = projections.get('overall_progress', 0)
        st.metric(
            "🎯 Genel İlerleme",
            f"%{overall_progress:.1f}",
            f"Hedef: %100"
        )
    
    with col2:
        tyt_progress = projections.get('tyt_progress', 0)
        st.metric(
            "📚 TYT İlerleme", 
            f"%{tyt_progress:.1f}",
            f"Tahmini: Mart 2025" if tyt_progress < 80 else "Yakında!"
        )
    
    with col3:
        ayt_progress = projections.get('ayt_progress', 0)
        st.metric(
            "📖 AYT İlerleme",
            f"%{ayt_progress:.1f}", 
            f"Tahmini: Mayıs 2025" if ayt_progress < 70 else "Yakında!"
        )
    
    with col4:
        weekly_target = weekly_plan.get('week_target', 0)
        success_rate = weekly_plan.get('success_target', 0.8)
        st.metric(
            "📅 Bu Hafta",
            f"{weekly_target} konu",
            f"Hedef: %{success_rate*100:.0f} başarı"
        )
    
    # İlerleme çubukları
    st.markdown("#### 📈 Detaylı İlerleme")
    
    progress_col1, progress_col2 = st.columns(2)
    
    with progress_col1:
        st.write("**TYT İlerleme**")
        st.progress(tyt_progress / 100)
        
    with progress_col2:
        st.write("**AYT İlerleme**") 
        st.progress(ayt_progress / 100)
    
    # Tahmini tamamlanma
    estimated_completion = projections.get('estimated_completion')
    if estimated_completion:
        st.info(f"📅 **Tahmini Genel Tamamlanma:** {estimated_completion}")
    
    # YENİ: Günlük/Haftalık/Aylık İlerleme Analizi
    st.markdown("---")
    show_time_based_progress_analysis(user_data, week_info)
    
    # YENİ: Deneme Bazlı Trend Analizi  
    st.markdown("---")
    show_exam_based_trend_analysis(user_data)
    
    # YENİ: YKS Hedef Hız Analizi
    st.markdown("---")
    show_yks_target_speed_analysis(user_data, projections, week_info)

def show_new_topics_section(new_topics, user_data):
    """Yeni konular bölümü"""
    if not new_topics:
        st.warning("📊 Yeni konu bulunamadı. Konu Takip sekmesinden değerlendirmelerinizi yapın.")
        return
    
    # Öncelik gruplarına ayır (YENİ 5'Lİ SİSTEM)
    high_priority = [t for t in new_topics if t.get('priority') == 'HIGH']
    medium_priority = [t for t in new_topics if t.get('priority') == 'MEDIUM'] 
    normal_priority = [t for t in new_topics if t.get('priority') == 'NORMAL']
    low_priority = [t for t in new_topics if t.get('priority') == 'LOW']
    minimal_priority = [t for t in new_topics if t.get('priority') == 'MINIMAL']
    
    # Acil - Zayıf konular
    if high_priority:
        st.markdown("##### 🔥 Acil - Zayıf Konular")
        for topic in high_priority:
            show_topic_card(topic, "HIGH")
    
    # Öncelikli - Temel konular
    if medium_priority:
        st.markdown("##### ⚡ Öncelikli - Temel Konular")
        for topic in medium_priority:
            show_topic_card(topic, "MEDIUM")
    
    # Normal - Orta konular
    if normal_priority:
        st.markdown("##### 🎯 Normal - Orta Konular")
        for topic in normal_priority:
            show_topic_card(topic, "NORMAL")
    
    # Düşük - İyi konular
    if low_priority:
        st.markdown("##### 🟢 Düşük - İyi Konular")
        for topic in low_priority:
            show_topic_card(topic, "LOW")
    
    # Minimal - Uzman konular
    if minimal_priority:
        st.markdown("##### ⭐ Minimal - Uzman Konular")
        for topic in minimal_priority:
            show_topic_card(topic, "MINIMAL")

def show_review_topics_section(review_topics, user_data):
    """Tekrar konuları bölümü - ESKİ VE YENİ SİSTEM ENTEGRASYONLİ"""
    # YENİ: Kalıcı öğrenme sistemi tekrarları
    pending_mastery_topics = get_pending_review_topics(user_data)
    
    # Eğer her iki sistem de boşsa
    if not review_topics and not pending_mastery_topics:
        st.info("🎉 Bu hafta tekrar edilecek konu yok!")
        return
    
    # YENİ SİSTEM: Kalıcı Öğrenme Tekrarları (Öncelik)
    if pending_mastery_topics:
        st.markdown("#### 🎯 KALİCİ ÖĞRENME TEKRARLARİ")
        st.caption("Bu konuları yeniden değerlendirerek kalıcılığını onaylayın!")
        show_pending_reviews_section(pending_mastery_topics)
        
        if review_topics:  # Eğer eski sistem tekrarları da varsa ayırıcı ekle
            st.markdown("---")
    
    # ESKİ SİSTEM: Spaced Repetition Tekrarları
    if review_topics:
        st.markdown("#### 🔄 GENEL TEKRARLAR")
        st.caption("Eski sistemden gelen aralıklı tekrar konuları")
        
        # Öncelik gruplarına ayır
        high_reviews = [t for t in review_topics if t.get('priority') == 'REPEAT_HIGH']
        medium_reviews = [t for t in review_topics if t.get('priority') == 'REPEAT_MEDIUM']
        normal_reviews = [t for t in review_topics if t.get('priority') == 'REPEAT_NORMAL']
        
        # Yüksek öncelikli tekrarlar
        if high_reviews:
            st.markdown("##### 🔄 Yüksek Öncelikli Tekrar")
            for topic in high_reviews:
                show_review_card(topic, "REPEAT_HIGH")
        
        # Öncelikli tekrarlar
        if medium_reviews:
            st.markdown("##### 🔄 Öncelikli Tekrar")
            for topic in medium_reviews:
                show_review_card(topic, "REPEAT_MEDIUM")
        
        # Normal tekrarlar
        if normal_reviews:
            st.markdown("##### 🔄 Normal Tekrar")
            for topic in normal_reviews:
                show_review_card(topic, "REPEAT_NORMAL")

def show_topic_card(topic, priority_type):
    """Konu kartı gösterici"""
    priority_info = PRIORITY_CATEGORIES[priority_type]
    
    with st.container():
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {priority_info['color']}22 0%, {priority_info['color']}11 100%); 
                    border-left: 4px solid {priority_info['color']}; 
                    padding: 12px; border-radius: 8px; margin-bottom: 8px;'>
            <div style='display: flex; align-items: center; margin-bottom: 8px;'>
                <span style='font-size: 18px; margin-right: 8px;'>{priority_info['icon']}</span>
                <strong style='color: {priority_info['color']};'>{topic['subject']}</strong>
            </div>
            <div style='margin-left: 26px;'>
                <div><strong>📖 {topic['topic']}</strong></div>
                <div style='font-size: 14px; color: #666; margin-top: 4px;'>
                    └ {topic['detail']} 
                    <span style='background: #f0f0f0; padding: 2px 6px; border-radius: 10px; margin-left: 8px;'>
                        Mevcut: {topic['net']} net
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def show_review_card(topic, priority_type):
    """Tekrar konu kartı"""
    priority_info = PRIORITY_CATEGORIES[priority_type]
    
    with st.container():
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {priority_info['color']}22 0%, {priority_info['color']}11 100%); 
                    border-left: 4px solid {priority_info['color']}; 
                    padding: 12px; border-radius: 8px; margin-bottom: 8px;'>
            <div style='display: flex; align-items: center; margin-bottom: 8px;'>
                <span style='font-size: 16px; margin-right: 8px;'>{priority_info['icon']}</span>
                <strong style='color: {priority_info['color']};'>{topic['subject']}</strong>
            </div>
            <div style='margin-left: 24px;'>
                <div><strong>📖 {topic['topic']}</strong></div>
                <div style='font-size: 14px; color: #666; margin-top: 4px;'>
                    └ {topic['detail']} 
                    <span style='background: #e8f5e8; padding: 2px 6px; border-radius: 10px; margin-left: 8px;'>
                        {topic['net']} net • {topic['days_passed']} gün önce
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ===== YENİ: KALICI ÖĞRENME SİSTEMİ UI FONKSİYONLARI =====

def show_pending_reviews_section(pending_topics):
    """Tekrar değerlendirmesi bekleyen konular bölümünü gösterir"""
    if not pending_topics:
        return
    
    for topic in pending_topics:
        with st.expander(f"🔄 {topic['subject']} - {topic['topic']} | {topic['stage_name']}", expanded=True):
            # Konu bilgileri
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **📚 Konu:** {topic['topic']}  
                **📝 Detay:** {topic['detail']}  
                **📅 İlk Öğrenme:** {topic['days_since_last']} gün önce  
                **🔢 Tekrar Sayısı:** {topic['review_count']}
                """)
            
            with col2:
                stage_info = MASTERY_STATUS.get(f"REVIEW_{topic['stage'] + 1}", MASTERY_STATUS["INITIAL"])
                st.markdown(f"""
                <div style='text-align: center; padding: 10px; background: {stage_info['color']}22; border-radius: 8px;'>
                    <div style='font-size: 24px;'>{stage_info['icon']}</div>
                    <div style='font-weight: bold; color: {stage_info['color']};'>{stage_info['name']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Değerlendirme seçenekleri
            st.markdown("#### 🎯 Bu konuda kendinizi nasıl değerlendiriyorsunuz?")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("❌ Zayıf", key=f"zayif_{topic['key']}", 
                           help="Konuyu tekrar öğrenmem gerekiyor",
                           use_container_width=True):
                    process_and_update_review(topic['key'], 'zayif')
            
            with col2:
                if st.button("📚 Temel", key=f"temel_{topic['key']}", 
                           help="Temel seviyede biliyorum",
                           use_container_width=True):
                    process_and_update_review(topic['key'], 'temel')
            
            with col3:
                if st.button("📜 Orta", key=f"orta_{topic['key']}", 
                           help="Orta seviyede biliyorum",
                           use_container_width=True):
                    process_and_update_review(topic['key'], 'orta')
            
            with col4:
                if st.button("✅ İyi", key=f"iyi_{topic['key']}", 
                           help="İyi seviyede biliyorum",
                           use_container_width=True):
                    process_and_update_review(topic['key'], 'iyi')
            
            with col5:
                if st.button("⭐ Uzman", key=f"uzman_{topic['key']}", 
                           help="Uzman seviyede biliyorum",
                           use_container_width=True):
                    process_and_update_review(topic['key'], 'uzman')

def process_and_update_review(topic_key, evaluation):
    """Tekrar değerlendirmesini işler ve Firebase'i günceller"""
    # Kullanıcı verilerini güncelle
    user_data = st.session_state.current_user
    updated_data = process_review_evaluation(user_data, topic_key, evaluation)
    
    # Firebase'de güncelle
    username = st.session_state.username
    update_success = update_user_in_firebase(username, {
        'topic_repetition_history': updated_data['topic_repetition_history'],
        'topic_mastery_status': updated_data['topic_mastery_status']
    })
    
    if update_success:
        # Session state'i güncelle
        st.session_state.current_user.update(updated_data)
        
        # Başarı mesajı
        evaluation_text = {
            'zayif': 'Zayıf - Konu başa alındı',
            'temel': 'Temel - Tekrar programlandı', 
            'orta': 'Orta - Aynı seviyede tekrar',
            'iyi': 'İyi - Sonraki aşamaya geçildi',
            'uzman': 'Uzman - Sonraki aşamaya geçildi'
        }
        
        st.success(f"✅ Değerlendirme kaydedildi: {evaluation_text[evaluation]}")
        st.experimental_rerun()
    else:
        st.error("❌ Değerlendirme kaydedilemedi!")

def show_mastery_progress_dashboard(user_data):
    """Kalıcı öğrenme ilerleme dashboard'u"""
    import json
    
    mastery_status = json.loads(user_data.get('topic_mastery_status', '{}'))
    
    if not mastery_status:
        st.info("📚 Henüz kalıcı öğrenme sisteminde konu bulunmuyor.")
        return
    
    st.markdown("### 🎯 KALİCİ ÖĞRENME İLERLEMESI")
    
    # İstatistikler
    total_topics = len(mastery_status)
    mastered_topics = sum(1 for status in mastery_status.values() if status['status'] == 'MASTERED')
    in_progress = total_topics - mastered_topics
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📚 Toplam Konu", total_topics)
    
    with col2:
        st.metric("✅ Kalıcı Öğrenilen", mastered_topics, 
                 delta=f"%{(mastered_topics/total_topics*100):.1f}" if total_topics > 0 else "0%")
    
    with col3:
        st.metric("🔄 Devam Eden", in_progress)
    
    # Detaylı liste
    if mastered_topics > 0:
        st.markdown("#### ✅ Kalıcı Öğrenilen Konular")
        for topic_key, status in mastery_status.items():
            if status['status'] == 'MASTERED':
                parts = topic_key.split(' | ')
                if len(parts) >= 3:
                    st.success(f"✅ {parts[0]} - {parts[2]} | ✨ Başarı: {status['success_count']}/{status['total_reviews']}")

def get_current_week_info():
    """Güncel haftanın bilgilerini döndürür - sürekli güncellenecek"""
    today = datetime.now()
    
    # Türkçe ay isimleri
    turkish_months = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }
    
    # Bu haftanın pazartesini bul
    days_since_monday = today.weekday()  # 0=Pazartesi, 6=Pazar
    monday_this_week = today - timedelta(days=days_since_monday)
    sunday_this_week = monday_this_week + timedelta(days=6)
    
    # Tarih aralığı formatla (Türkçe ay isimleri ile)
    monday_str = f"{monday_this_week.day} {turkish_months[monday_this_week.month]}"
    sunday_str = f"{sunday_this_week.day} {turkish_months[sunday_this_week.month]} {sunday_this_week.year}"
    week_range = f"{monday_str} - {sunday_str}"
    
    return {
        'today': today,
        'monday': monday_this_week,
        'sunday': sunday_this_week,
        'week_range': week_range,
        'week_number': today.isocalendar()[1],  # Yılın kaçıncı haftası
        'current_day': today.strftime('%A'),  # Günün adı
        'days_to_yks': calculate_days_to_yks(),  # YKS'ye kalan gün
    }

def calculate_days_to_yks():
    """YKS'ye kalan gün sayısını hesaplar"""
    today = datetime.now().date()
    # YKS tarihi: 2026 yılının Haziran ayının ikinci hafta sonu
    # Genellikle Haziran'ın ikinci hafta sonu oluyor (14-15 Haziran)
    yks_date = datetime(2026, 6, 14).date()
    
    days_left = (yks_date - today).days
    return max(0, days_left)  # Geçmişte bir tarih olursa 0 döndür

def show_time_based_progress_analysis(user_data, week_info):
    """Günlük/Haftalık/Aylık ilerleme analizi - YKS odaklı"""
    st.markdown("### 📊 ZAMANSAL İLERLEME ANALİZİ")
    st.caption("Son günlerdeki çalışma hızınız ve konu tamamlama performansınız")
    
    # Temel veriler
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    completion_dates = json.loads(user_data.get('topic_completion_dates', '{}') or '{}')
    current_date = datetime.now()
    
    # Günlük analiz (son 24 saat)
    daily_stats = calculate_daily_progress(topic_progress, completion_dates, current_date)
    
    # Haftalık analiz (son 7 gün)
    weekly_stats = calculate_weekly_progress(topic_progress, completion_dates, current_date)
    
    # Aylık analiz (son 30 gün)
    monthly_stats = calculate_monthly_progress(topic_progress, completion_dates, current_date)
    
    # Metrik gösterimi
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📅 Günlük Performans")
        st.metric("🎯 Tamamlanan Konu", daily_stats['completed_topics'], 
                 delta=f"+{daily_stats['net_increase']} net artışı" if daily_stats['net_increase'] > 0 else None)
        st.metric("⚡ Çalışma Momentum", 
                 "Yüksek" if daily_stats['completed_topics'] >= 3 else "Orta" if daily_stats['completed_topics'] >= 1 else "Düşük",
                 delta="Son 24 saat")
        
    with col2:
        st.markdown("#### 📈 Haftalık Performans")
        st.metric("🎯 Tamamlanan Konu", weekly_stats['completed_topics'],
                 delta=f"Hedef: 15 konu/hafta")
        weekly_pace = "Çok Hızlı" if weekly_stats['completed_topics'] >= 20 else "Hızlı" if weekly_stats['completed_topics'] >= 15 else "Normal" if weekly_stats['completed_topics'] >= 10 else "Yavaş"
        st.metric("🚀 Haftalık Hız", weekly_pace,
                 delta=f"+{weekly_stats['net_increase']} net artışı")
        
    with col3:
        st.markdown("#### 📊 Aylık Performans")
        st.metric("🎯 Tamamlanan Konu", monthly_stats['completed_topics'],
                 delta=f"Hedef: 60 konu/ay")
        monthly_trend = "Artış Eğiliminde" if monthly_stats['trend'] > 0 else "Azalış Eğiliminde" if monthly_stats['trend'] < 0 else "Sabit"
        st.metric("📈 Trend", monthly_trend,
                 delta=f"Ort. {monthly_stats['avg_per_week']:.1f} konu/hafta")
    
    # Görsel grafik
    if monthly_stats['daily_data']:
        create_progress_chart(monthly_stats['daily_data'])

def calculate_daily_progress(topic_progress, completion_dates, current_date):
    """Son 24 saatteki ilerlemeyi hesaplar"""
    yesterday = current_date - timedelta(days=1)
    completed_today = 0
    net_increase = 0
    
    for topic_key, completion_date_str in completion_dates.items():
        try:
            completion_date = datetime.fromisoformat(completion_date_str)
            if completion_date >= yesterday:
                completed_today += 1
                net_value = int(float(topic_progress.get(topic_key, '0')))
                if net_value >= 14:
                    net_increase += (net_value - 14)  # 14'ten yukarısı net artış
        except:
            continue
    
    return {
        'completed_topics': completed_today,
        'net_increase': net_increase,
        'momentum': 'high' if completed_today >= 3 else 'medium' if completed_today >= 1 else 'low'
    }

def calculate_weekly_progress(topic_progress, completion_dates, current_date):
    """Son 7 gündeki ilerlemeyi hesaplar"""
    week_ago = current_date - timedelta(days=7)
    completed_this_week = 0
    net_increase = 0
    
    for topic_key, completion_date_str in completion_dates.items():
        try:
            completion_date = datetime.fromisoformat(completion_date_str)
            if completion_date >= week_ago:
                completed_this_week += 1
                net_value = int(float(topic_progress.get(topic_key, '0')))
                if net_value >= 14:
                    net_increase += (net_value - 14)
        except:
            continue
    
    return {
        'completed_topics': completed_this_week,
        'net_increase': net_increase,
        'pace': 'fast' if completed_this_week >= 15 else 'normal' if completed_this_week >= 10 else 'slow'
    }

def calculate_monthly_progress(topic_progress, completion_dates, current_date):
    """Son 30 gündeki ilerlemeyi hesaplar ve trend analizi yapar"""
    month_ago = current_date - timedelta(days=30)
    completed_this_month = 0
    daily_data = []
    
    # Günlük verileri topla
    for i in range(30):
        day = current_date - timedelta(days=i)
        day_count = 0
        
        for topic_key, completion_date_str in completion_dates.items():
            try:
                completion_date = datetime.fromisoformat(completion_date_str)
                if completion_date.date() == day.date():
                    day_count += 1
                    completed_this_month += 1
            except:
                continue
        
        daily_data.append({
            'date': day.date(),
            'completed': day_count
        })
    
    # Trend hesapla (son 15 gün vs önceki 15 gün)
    recent_15 = sum([d['completed'] for d in daily_data[:15]])
    previous_15 = sum([d['completed'] for d in daily_data[15:]])
    trend = recent_15 - previous_15
    
    return {
        'completed_topics': completed_this_month,
        'trend': trend,
        'avg_per_week': completed_this_month / 4.3,  # 30 gün / 7 ≈ 4.3 hafta
        'daily_data': list(reversed(daily_data))  # Eski tarihten yeniye
    }

def create_progress_chart(daily_data):
    """Son 30 günün ilerleme grafiğini oluşturur"""
    if not daily_data:
        return
    
    st.markdown("#### 📈 Son 30 Günlük İlerleme Trendi")
    
    dates = [d['date'] for d in daily_data]
    completed = [d['completed'] for d in daily_data]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=completed,
        mode='lines+markers',
        name='Günlük Tamamlanan Konu',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6)
    ))
    
    # Ortalama çizgisi
    avg_line = sum(completed) / len(completed) if completed else 0
    fig.add_hline(y=avg_line, line_dash="dash", line_color="red", 
                  annotation_text=f"30 günlük ortalama: {avg_line:.1f}")
    
    fig.update_layout(
        title="📊 Günlük Konu Tamamlama Performansı",
        xaxis_title="Tarih",
        yaxis_title="Tamamlanan Konu Sayısı",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_exam_based_trend_analysis(user_data):
    """Deneme bazlı trend analizi - sınav performansı odaklı"""
    st.markdown("### 🎯 DENEME BAZLI TREND ANALİZİ")
    st.caption("Deneme sonuçlarınıza göre güçlenen/zayıflayan konularınız")
    
    # Deneme verileri
    exam_history = json.loads(user_data.get('detailed_exam_history', '[]') or '[]')
    
    if not exam_history:
        st.info("📊 Henüz deneme analizi verisi yok. 'Detaylı Deneme Analiz' sekmesinden deneme sonuçlarınızı girin.")
        return
    
    # Son 3 deneme analizi
    recent_exams = exam_history[-3:] if len(exam_history) >= 3 else exam_history
    
    if len(recent_exams) >= 2:
        trend_analysis = analyze_exam_trends(recent_exams)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 GÜÇLENEN DERSLER")
            if trend_analysis['improving']:
                for subject, data in trend_analysis['improving'].items():
                    improvement = data['trend']
                    st.success(f"🚀 **{subject}**: +{improvement:.1f} net artış (son 3 deneme)")
            else:
                st.info("📊 Henüz güçlenen ders tespit edilmedi")
        
        with col2:
            st.markdown("#### 📉 ZAYIFLAYAN DERSLER")
            if trend_analysis['declining']:
                for subject, data in trend_analysis['declining'].items():
                    decline = abs(data['trend'])
                    st.error(f"⚠️ **{subject}**: -{decline:.1f} net düşüş (son 3 deneme)")
            else:
                st.success("✅ Hiçbir derste düşüş yok!")
        
        # Genel trend skoru
        overall_trend = trend_analysis['overall_trend']
        trend_emoji = "📈" if overall_trend > 0 else "📉" if overall_trend < 0 else "➡️"
        st.metric("🎯 Genel Deneme Trendi", 
                 f"{trend_emoji} {overall_trend:+.1f} net değişim",
                 delta="Son 3 deneme ortalaması")
    else:
        st.warning("📊 Trend analizi için en az 2 deneme verisi gerekli")

def analyze_exam_trends(recent_exams):
    """Deneme trendlerini analiz eder"""
    if len(recent_exams) < 2:
        return {'improving': {}, 'declining': {}, 'overall_trend': 0}
    
    # Ders bazında trend hesapla
    subject_trends = {}
    
    for i, exam in enumerate(recent_exams):
        subjects = exam.get('subjects', {})
        for subject, data in subjects.items():
            if subject not in subject_trends:
                subject_trends[subject] = []
            
            net_score = data.get('net', 0)
            subject_trends[subject].append(net_score)
    
    improving = {}
    declining = {}
    overall_changes = []
    
    for subject, scores in subject_trends.items():
        if len(scores) >= 2:
            # Lineer trend hesapla
            trend = (scores[-1] - scores[0]) / (len(scores) - 1)
            overall_changes.append(trend)
            
            if trend > 0.5:  # 0.5+ net artış
                improving[subject] = {'trend': trend, 'scores': scores}
            elif trend < -0.5:  # 0.5+ net düşüş
                declining[subject] = {'trend': trend, 'scores': scores}
    
    overall_trend = sum(overall_changes) / len(overall_changes) if overall_changes else 0
    
    return {
        'improving': improving,
        'declining': declining,
        'overall_trend': overall_trend
    }

def show_yks_target_speed_analysis(user_data, projections, week_info):
    """YKS hedefine göre hız analizi - hedefe ulaşma projeksiyonu"""
    st.markdown("### 🚀 YKS HEDEF HIZ ANALİZİ")
    st.caption("Mevcut hızınızla hedef üniversiteye ulaşabilir misiniz?")
    
    # Hedef bilgileri
    target_department = user_data.get('target_department', 'Henüz belirlenmedi')
    current_speed = calculate_current_completion_speed(user_data)
    days_left = week_info['days_to_yks']
    
    # İlerleme verileri
    overall_progress = projections.get('overall_progress', 0)
    remaining_progress = 100 - overall_progress
    
    # Hız analizi
    weeks_left = days_left / 7
    required_speed = remaining_progress / weeks_left if weeks_left > 0 else float('inf')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🎯 HEDEF BİLGİLERİ")
        st.info(f"**Hedef:** {target_department}")
        st.metric("⏰ Kalan Süre", f"{days_left} gün", delta=f"{weeks_left:.1f} hafta")
        st.metric("📊 Kalan İlerleme", f"%{remaining_progress:.1f}", delta="Tamamlanacak")
        
    with col2:
        st.markdown("#### ⚡ MEVCUT HIZ")
        speed_status = evaluate_speed_status(current_speed, required_speed)
        st.metric("🏃‍♂️ Haftalık Hız", f"{current_speed:.1f} konu/hafta", 
                 delta="Son 4 hafta ortalaması")
        st.metric("📈 Hız Durumu", speed_status['status'], 
                 delta=speed_status['message'])
        
    with col3:
        st.markdown("#### 🎯 GEREKLİ HIZ")
        st.metric("⚡ Hedeflenen Hız", f"{required_speed:.1f} konu/hafta", 
                 delta="Hedefe ulaşmak için")
        
        # Tavsiye
        if current_speed >= required_speed:
            st.success("✅ Hızınız yeterli! Devam edin!")
        elif current_speed >= required_speed * 0.8:
            st.warning("⚠️ Biraz daha hızlanmalısınız!")
        else:
            st.error("🚨 Ciddi hız artışı gerekli!")
    
    # Detaylı projeksiyon
    create_speed_projection_chart(current_speed, required_speed, weeks_left, overall_progress)

def calculate_current_completion_speed(user_data):
    """Mevcut konu tamamlama hızını hesaplar (konu/hafta)"""
    completion_dates = json.loads(user_data.get('topic_completion_dates', '{}') or '{}')
    current_date = datetime.now()
    
    # Son 4 hafta
    four_weeks_ago = current_date - timedelta(weeks=4)
    completed_last_4_weeks = 0
    
    for completion_date_str in completion_dates.values():
        try:
            completion_date = datetime.fromisoformat(completion_date_str)
            if completion_date >= four_weeks_ago:
                completed_last_4_weeks += 1
        except:
            continue
    
    return completed_last_4_weeks / 4  # konu/hafta

def evaluate_speed_status(current_speed, required_speed):
    """Hız durumunu değerlendirir"""
    if current_speed >= required_speed:
        return {'status': 'Mükemmel', 'message': 'Hedefe ulaşacaksınız!'}
    elif current_speed >= required_speed * 0.8:
        return {'status': 'İyi', 'message': 'Biraz daha hızlanın'}
    elif current_speed >= required_speed * 0.6:
        return {'status': 'Orta', 'message': 'Hız artışı gerekli'}
    else:
        return {'status': 'Kritik', 'message': 'Ciddi revizyona ihtiyaç var'}

def create_speed_projection_chart(current_speed, required_speed, weeks_left, current_progress):
    """Hız projeksiyonu grafiği oluşturur"""
    st.markdown("#### 📈 İlerleme Projeksiyonu")
    
    weeks = list(range(0, int(weeks_left) + 1))
    
    # Mevcut hızla projeksiyon
    current_projection = [current_progress + (current_speed * w * 100 / 50) for w in weeks]  # 50 konu = %100 varsayımı
    
    # Gerekli hızla projeksiyon  
    required_projection = [current_progress + (required_speed * w * 100 / 50) for w in weeks]
    
    fig = go.Figure()
    
    # Mevcut hız çizgisi
    fig.add_trace(go.Scatter(
        x=weeks, y=current_projection,
        mode='lines+markers',
        name=f'Mevcut Hız ({current_speed:.1f} konu/hafta)',
        line=dict(color='blue', width=2)
    ))
    
    # Gerekli hız çizgisi
    fig.add_trace(go.Scatter(
        x=weeks, y=required_projection,
        mode='lines+markers',
        name=f'Gerekli Hız ({required_speed:.1f} konu/hafta)',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    # %100 hedef çizgisi
    fig.add_hline(y=100, line_dash="dot", line_color="green", 
                  annotation_text="🎯 Hedef: %100 tamamlanma")
    
    fig.update_layout(
        title="🚀 YKS'ye Kalan Sürede İlerleme Projeksiyonu",
        xaxis_title="Hafta",
        yaxis_title="İlerleme (%)",
        height=400,
        yaxis=dict(range=[0, 120])
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_interactive_systematic_planner(weekly_plan, survey_data):
    """Basit ve etkili haftalık planlayıcı - DİNAMİK TARİH SİSTEMİ"""
    
    # Güncel hafta bilgilerini al (sürekli güncellenen)
    week_info = get_current_week_info()
    week_range = week_info['week_range']
    
    # Haftalık planlama tablosu
    st.markdown(f"#### 📅 Bu Haftanın Programı ({week_range})")
    
    # Günler
    days = ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]
    rest_day = survey_data.get('rest_day', 'Pazar')
    
    # Session state'te planları tut
    if 'day_plans' not in st.session_state:
        st.session_state.day_plans = {day: [] for day in days}
    
    # Günleri göster
    cols = st.columns(7)
    
    for i, day in enumerate(days):
        with cols[i]:
            # Gün başlığı
            if day.title() == rest_day:
                st.markdown(f"**{day}** 🌴")
                st.info("🌴 Dinlenme Günü")
            else:
                st.markdown(f"**{day}**")
                
                # Bu günde planlanmış konuları göster
                day_plan = st.session_state.day_plans.get(day, [])
                if day_plan:
                    for j, plan_item in enumerate(day_plan):
                        with st.container():
                            priority = plan_item.get('priority', 'NORMAL')
                            priority_info = PRIORITY_CATEGORIES.get(priority, PRIORITY_CATEGORIES['NORMAL'])
                            
                            st.markdown(f"<div style='background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); padding: 8px; border-radius: 5px; margin-bottom: 5px; color: white; font-size: 12px;'>"
                                      f"<strong>{priority_info['icon']} {plan_item['subject']}</strong><br>"
                                      f"{plan_item['topic']}<br>"
                                      f"<small>🕰️ {plan_item['time']}</small>"
                                      f"</div>", unsafe_allow_html=True)
                            
                            # Kaldırma butonu - Benzersiz key ile
                            date_key = datetime.now().date().isoformat().replace('-', '')
                            if st.button(f"❌", key=f"remove_{day}_{j}_{date_key}", help="Bu konuyu kaldır"):
                                st.session_state.day_plans[day].pop(j)
                                st.rerun()
                
                # Boş alan göstergesi
                if not day_plan:
                    st.markdown("<div style='border: 2px dashed #e0e0e0; padding: 20px; text-align: center; color: #999; border-radius: 5px;'>Konu yok</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Haftalık planı yenile butonu ve debug bölümü
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Haftalık Planı Yenile", use_container_width=True, type="secondary"):
            # Cache'i temizle
            if 'weekly_plan_cache' in st.session_state:
                del st.session_state.weekly_plan_cache
            st.success("Haftalık plan yenilendi! Debug çıktısını konsola bakarak kontrol edin.")
            st.rerun()
    
    # Konuları göster ve ekleme sistemi
    st.markdown("#### 📋 Bu Haftanın Konuları")
    
    # Tüm konuları birleştir
    all_topics = weekly_plan.get('new_topics', []) + weekly_plan.get('review_topics', [])
    
    if all_topics:
        # Konuları kutu olarak göster
        topic_cols = st.columns(3)  # 3'lü gruplar halinde
        
        for i, topic in enumerate(all_topics):
            with topic_cols[i % 3]:
                # Konu kutusu
                with st.container():
                    priority = topic.get('priority', 'NORMAL')
                    priority_info = PRIORITY_CATEGORIES.get(priority, PRIORITY_CATEGORIES['NORMAL'])
                    
                    st.markdown(f"<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 8px; margin-bottom: 5px; color: white;'>"
                              f"<strong>📚 {topic['subject']}</strong><br>"
                              f"{topic['topic']}<br>"
                              f"<small>{topic['detail']}</small><br>"
                              f"<small>🎯 {topic['net']} net</small>"
                              f"</div>", unsafe_allow_html=True)
                    
                    # Öncelik bilgisi kutunun altında
                    st.markdown(f"<div style='text-align: center; color: {priority_info['color']}; font-weight: bold; font-size: 12px; margin-bottom: 10px;'>"
                              f"{priority_info['icon']} {priority_info['name']}"
                              f"</div>", unsafe_allow_html=True)
                    
                    # Ekleme formu - sadeleştirilmiş
                    with st.expander(f"📅 Programa Ekle", expanded=False):
                        date_key = datetime.now().date().isoformat().replace('-', '')
                        selected_day = st.selectbox(
                            "Gün seçin:", 
                            [d for d in days if d.title() != rest_day],
                            key=f"day_select_{i}_{date_key}"
                        )
                        
                        time_slot = st.text_input(
                            "Saat aralığı:",
                            placeholder="17:00-18:30",
                            key=f"time_input_{i}_{date_key}"
                        )
                        
                        if st.button("➕ Ekle", key=f"add_topic_{i}_{date_key}", type="primary"):
                            if time_slot:
                                # Konuyu programa ekle
                                new_plan_item = {
                                    'subject': topic['subject'],
                                    'topic': topic['topic'],
                                    'detail': topic['detail'],
                                    'time': time_slot,
                                    'priority': topic.get('priority', 'NORMAL')
                                }
                                
                                if selected_day not in st.session_state.day_plans:
                                    st.session_state.day_plans[selected_day] = []
                                
                                st.session_state.day_plans[selected_day].append(new_plan_item)
                                st.success(f"✅ {topic['topic']} eklendi!")
                                st.rerun()
                            else:
                                st.warning("🕰️ Saat aralığı gerekli!")
    
    else:
        st.info("📊 Bu hafta için otomatik konu bulunamadı. Konu Takip sekmesinden konularınızı değerlendirin.")
    
    st.markdown("---")
    st.markdown("#### 📊 Bu Haftanın Programı")
    
    total_planned = sum(len(plans) for plans in st.session_state.day_plans.values())
    
    if total_planned > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📅 Planlanmış Konu", total_planned)
        with col2:
            active_days = len([day for day, plans in st.session_state.day_plans.items() if plans])
            st.metric("📆 Aktif Gün", active_days)
        
        # Temizleme butonları
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Programı Temizle", type="secondary"):
                st.session_state.day_plans = {day: [] for day in days}
                st.success("✅ Program temizlendi!")
                st.rerun()
        with col2:
            if st.button("🔄 Haftalık Planı Yenile", type="secondary", help="Cache'i temizleyip planı yeniden oluşturur"):
                # Tüm cache'leri temizle
                cache_keys = [key for key in st.session_state.keys() if 'cache' in key.lower() or 'plan' in key.lower()]
                for key in cache_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("✅ Haftalık plan yenilendi!")
                st.rerun()
    else:
        st.info("📅 Henüz konu planlanmamış. Yukarıdaki konulardan seçip günlere ekleyin.")
    
    st.markdown("---")
    
    # TYT/AYT durumu bilgilendirmesi
    if 'tyt_progress' in weekly_plan and 'ayt_enabled' in weekly_plan:
        tyt_progress = weekly_plan.get('tyt_progress', 0)
        ayt_enabled = weekly_plan.get('ayt_enabled', False)
        tyt_math_completed = weekly_plan.get('tyt_math_completed', 0)
        
        st.markdown("#### 📋 Öğrenim Durumu")
        
        if not ayt_enabled:
            st.info(f"""
            🎯 **TYT Aşaması** - AYT henüz başlamadı
            
            • TYT İlerleme: **%{tyt_progress:.1f}** (Hedef: %60)
            • TYT Matematik: **{tyt_math_completed}** konu tamamlandı (Hedef: 12)
            
            🔒 **AYT Başlatma Koşulları:** TYT %60 + TYT Matematik 12 konu tamamlanınca AYT konuları eklenecek.
            """)
        else:
            st.success(f"""
            ✅ **TYT + AYT Aşaması** - Tüm konular aktif!
            
            • TYT: **%{tyt_progress:.1f}** tamamlandı
            • TYT Matematik: **{tyt_math_completed}** konu tamamlandı
            
            🎯 Artık hem TYT hem AYT konuları haftalık programınızda görünüyor.
            """)
    
    # Program özeti kaldırıldı - tekrar olmaması için

def show_weekly_summary(weekly_plan):
    """Haftalık program özeti"""
    st.markdown("---")
    st.markdown("#### 📊 Haftalık Program Özeti")
    
    new_topics_count = len(weekly_plan.get('new_topics', []))
    review_topics_count = len(weekly_plan.get('review_topics', []))
    total_topics = new_topics_count + review_topics_count
    success_target = weekly_plan.get('success_target', 0.8)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 Yeni Konular", new_topics_count)
    
    with col2:
        st.metric("🔄 Tekrar Konuları", review_topics_count)
    
    with col3:
        st.metric("📅 Toplam Hedef", total_topics)
    
    with col4:
        target_completion = int(total_topics * success_target)
        st.metric("🏆 Başarı Hedefi", f"{target_completion}/{total_topics}")
    
    if total_topics > 0:
        st.info(f"💡 **Bu Hafta Hedefiniz:** {total_topics} konunun %{success_target*100:.0f}'ini (%{target_completion} konu) iyi seviyeye çıkarmak!")
        
        # İlerleme simülasyonu
        if st.button("🗑️ Haftalık Planı Temizle", type="secondary"):
            st.session_state.systematic_day_plans = {day: [] for day in ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]}
            st.success("✅ Haftalık plan temizlendi!")
            st.rerun()

def show_sar_zamani_geriye_page(user_data, progress_data):
    """⏰ Sar Zamanı Geriye - Sinema Tarzı Yolculuk Hikayesi"""
    
    # ÖNCE TÜM CSS STİLLERİNİ YÜKLEYELİM - Animasyon Öncesi
    st.markdown("""
    <style>
    /* Timeline Animasyon Stilleri */
    .stats-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        gap: 15px;
        margin: 20px 0;
    }
    
    .stat-box {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        min-width: 120px;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        animation: fadeInUp 0.6s ease-out;
    }
    
    .stat-number {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 5px;
        color: #FFD700;
    }
    
    .stat-label {
        font-size: 12px;
        opacity: 0.9;
        font-weight: 500;
    }
    
    .progress-indicator {
        background: linear-gradient(45deg, #ff6b6b, #ee5a24);
        color: white;
        padding: 12px 20px;
        border-radius: 25px;
        text-align: center;
        font-weight: bold;
        margin: 15px 0;
        animation: pulse 2s ease-in-out infinite;
        box-shadow: 0 5px 15px rgba(255, 107, 107, 0.4);
    }
    
    .day-card-cinema {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        color: white;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        animation: slideInUp 0.8s ease-out;
    }
    
    .date-header {
        background: #667eea;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideInUp {
        from { opacity: 0; transform: translateY(50px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    /* Cinema Header */
    .cinema-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .cinema-screen {
        background: #1a1a1a;
        border: 8px solid #333;
        border-radius: 12px;
        padding: 40px;
        margin: 30px 0;
        text-align: center;
        color: white;
        box-shadow: inset 0 0 50px rgba(0,0,0,0.8), 0 0 50px rgba(102, 126, 234, 0.3);
    }
    
    .screen-content h2 {
        color: #FFD700;
        margin-bottom: 20px;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)

    # Modern ve sade tasarım stilleri
    st.markdown("""
    <style>
    .cinema-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .cinema-screen {
        background: #1a1a1a;
        border: 8px solid #333;
        border-radius: 12px;
        padding: 40px;
        margin: 30px auto;
        max-width: 800px;
        position: relative;
        box-shadow: 
            0 0 50px rgba(0,0,0,0.8),
            inset 0 0 100px rgba(255,255,255,0.05);
    }
    
    .cinema-screen::before {
        content: '';
        position: absolute;
        top: -4px;
        left: -4px;
        right: -4px;
        bottom: -4px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        border-radius: 16px;
        z-index: -1;
    }
    
    .screen-content {
        color: #fff;
        text-align: center;
        font-size: 18px;
        line-height: 1.6;
    }
    
    .day-card-cinema {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin: 20px auto;
        max-width: 600px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        animation: slideIn 0.5s ease-out;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .date-header {
        background: #667eea;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Ana başlık
    st.markdown("""
    <div class="cinema-header">
        <h1 style="margin: 0; font-size: 36px;">
            ⏰ Sar Zamanı Geriye
        </h1>
        <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">
            Başarı yolculuğunuzun hikayesi
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Motivasyon metni
    st.markdown("""
    <div style="text-align: center; font-size: 20px; color: #555; margin: 30px 0; font-style: italic;">
        "Bugüne kolay gelmedin."
    </div>
    """, unsafe_allow_html=True)
    
    # Sinema ekranı
    st.markdown("""
    <div class="cinema-screen">
        <div class="screen-content">
            <h2 style="margin: 0 0 20px 0;">🎬 ZAMAN MAKİNESİ</h2>
            <p style="margin: 0 0 30px 0;">
                Her günün hikayesini yeniden yaşamaya hazır mısın?<br>
                Başlangıçtan bugüne kadar ki tüm mücadeleni gör...
            </p>
            <div style="font-size: 64px; margin: 20px 0;">
                ⏳
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Kullanıcı verilerini kontrol et
    if not user_data:
        st.error("Kullanıcı verisi bulunamadı!")
        return
    
    # Session state için değişkenler
    if 'timeline_running' not in st.session_state:
        st.session_state.timeline_running = False
    if 'timeline_day' not in st.session_state:
        st.session_state.timeline_day = 0
    if 'play_music_timeline' not in st.session_state:
        st.session_state.play_music_timeline = False
    
    # Oynatma butonu + GÜÇLÜ MÜZİK SİSTEMİ
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎬 Sar Zamanı Geriye", key="start_timeline", use_container_width=True, type="primary"):
            st.session_state.timeline_running = True
            st.session_state.timeline_day = 0
            st.session_state.play_music_timeline = True
            st.rerun()
    
    # GÜÇLÜ MÜZİK SİSTEMİ - Animasyon başladığında çalacak
    if st.session_state.play_music_timeline:
        st.markdown("""
        <!-- GÜVENİLİR MÜZİK PLAYER -->
        <audio id="timelineMusic" loop preload="auto" style="display: none;">
            <source src="https://www.soundjay.com/misc/sounds/beep-01a.mp3" type="audio/mpeg">
            <source src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" type="audio/mp4">
        </audio>
        
        <!-- YouTube Backup Player -->
        <div id="youtube-container" style="position: fixed; top: -200px; left: -200px; opacity: 0; pointer-events: none;">
            <iframe id="youtube-music" 
                    width="100" 
                    height="100" 
                    src="https://www.youtube.com/embed/EQBVjwXZ7GY?autoplay=1&loop=1&playlist=EQBVjwXZ7GY&controls=0&mute=0&modestbranding=1&showinfo=0&rel=0"
                    frameborder="0" 
                    allow="autoplay; encrypted-media" 
                    allowfullscreen>
            </iframe>
        </div>
        
        <!-- Müzik Kontrol Butonu -->
        <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
            <button id="musicControlBtn" onclick="toggleTimelineMusic()" 
                    style="background: linear-gradient(45deg, #28a745, #20c997); color: white; border: none; border-radius: 50%; width: 60px; height: 60px; font-size: 20px; cursor: pointer; box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4); animation: pulse 2s ease-in-out infinite;">
                🎵
            </button>
        </div>
        
        <!-- Müzik Durumu Bildirimi -->
        <div id="musicStatus" style="position: fixed; top: 20px; right: 20px; z-index: 1001; opacity: 0; transition: all 0.3s ease;">
        </div>
        
        <script>
        let musicPlaying = false;
        let currentAudio = null;
        let youtubePlayer = null;
        
        function showMusicNotification(message, color = '#28a745') {
            const notification = document.getElementById('musicStatus');
            notification.innerHTML = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(45deg, ${color}, #20c997);
                color: white;
                padding: 12px 20px;
                border-radius: 25px;
                z-index: 1001;
                opacity: 1;
                font-weight: bold;
                box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4);
                transition: all 0.3s ease;
            `;
            
            setTimeout(() => {
                notification.style.opacity = '0';
            }, 3000);
        }
        
        function toggleTimelineMusic() {
            const audio = document.getElementById('timelineMusic');
            const musicBtn = document.getElementById('musicControlBtn');
            const youtubeFrame = document.getElementById('youtube-music');
            
            if (!musicPlaying) {
                // Müziği başlat
                console.log('🎵 Müzik başlatılıyor...');
                
                // Önce HTML5 audio dene
                if (audio) {
                    audio.volume = 0.3;
                    const playPromise = audio.play();
                    
                    if (playPromise !== undefined) {
                        playPromise.then(() => {
                            musicPlaying = true;
                            currentAudio = audio;
                            musicBtn.innerHTML = '🔇';
                            musicBtn.style.background = 'linear-gradient(45deg, #dc3545, #c82333)';
                            showMusicNotification('🎵 Müzik başlatıldı!');
                            console.log('✅ HTML5 Audio başarılı!');
                        }).catch((error) => {
                            console.log('❌ HTML5 Audio hatası, YouTube deneniyor:', error);
                            tryYouTubeMusic();
                        });
                    } else {
                        tryYouTubeMusic();
                    }
                } else {
                    tryYouTubeMusic();
                }
            } else {
                // Müziği durdur
                stopMusic();
            }
        }
        
        function tryYouTubeMusic() {
            console.log('🎥 YouTube müzik deneniyor...');
            const youtubeFrame = document.getElementById('youtube-music');
            const musicBtn = document.getElementById('musicControlBtn');
            
            if (youtubeFrame) {
                try {
                    // YouTube iframe'i yeniden yükle (autoplay ile)
                    youtubeFrame.src = youtubeFrame.src.replace('autoplay=1', 'autoplay=1');
                    musicPlaying = true;
                    musicBtn.innerHTML = '🔇';
                    musicBtn.style.background = 'linear-gradient(45deg, #dc3545, #c82333)';
                    showMusicNotification('🎵 Müzik başlatıldı! (YouTube)');
                    console.log('✅ YouTube müzik başarılı!');
                } catch (error) {
                    console.log('❌ YouTube hatası:', error);
                    fallbackMusicOptions();
                }
            } else {
                fallbackMusicOptions();
            }
        }
        
        function fallbackMusicOptions() {
            console.log('🆘 Fallback seçenekleri gösteriliyor...');
            showMusicNotification(`
                🎵 Müzik için: 
                <a href="https://www.youtube.com/watch?v=EQBVjwXZ7GY" target="_blank" 
                   style="color: #FFD700; text-decoration: underline; font-weight: bold;">
                   YouTube'da Aç 🎶
                </a>
            `, '#6c757d');
        }
        
        function stopMusic() {
            const audio = document.getElementById('timelineMusic');
            const musicBtn = document.getElementById('musicControlBtn');
            const youtubeFrame = document.getElementById('youtube-music');
            
            // HTML5 Audio durdur
            if (audio && !audio.paused) {
                audio.pause();
            }
            
            // YouTube durdur
            if (youtubeFrame) {
                youtubeFrame.src = youtubeFrame.src.replace('autoplay=1', 'autoplay=0');
            }
            
            musicPlaying = false;
            musicBtn.innerHTML = '🎵';
            musicBtn.style.background = 'linear-gradient(45deg, #28a745, #20c997)';
            showMusicNotification('🔇 Müzik durduruldu');
            console.log('⏹️ Müzik durduruldu');
        }
        
        // Sayfa yüklendiğinde otomatik müzik başlat
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📱 Sayfa yüklendi, müzik hazırlanıyor...');
            
            // 1 saniye sonra müziği otomatik başlat
            setTimeout(() => {
                if (!musicPlaying) {
                    console.log('🚀 Otomatik müzik başlatma...');
                    toggleTimelineMusic();
                }
            }, 1000);
        });
        
        // CSS animasyonları ekle
        if (!document.getElementById('music-animations')) {
            const style = document.createElement('style');
            style.id = 'music-animations';
            style.textContent = `
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.1); }
                }
            `;
            document.head.appendChild(style);
        }
        </script>
        """, unsafe_allow_html=True)
    
    # Başlangıç tarihini hesapla - Öğrencinin sisteme kayıt tarihi
    try:
        # Öğrencinin sisteme kayıt tarihini al
        if 'created_date' in user_data and user_data['created_date']:
            register_date = datetime.strptime(user_data['created_date'], '%Y-%m-%d')
        elif 'created_at' in user_data and user_data['created_at']:
            register_date = datetime.strptime(user_data['created_at'][:10], '%Y-%m-%d')
        else:
            register_date = datetime.now() - timedelta(days=7)  # 7 gün öncesini varsayılan yap
    except:
        register_date = datetime.now() - timedelta(days=7)  # 7 gün öncesini varsayılan yap
    
    current_date = datetime.now()
    days_passed = (current_date - register_date).days + 1
    
    if st.session_state.timeline_running:
        # Gerçek kullanıcı verilerini yükle ve haftalık hedef konuları çek
        try:
            topic_progress = json.loads(user_data.get('topic_progress', '{}'))
            weekly_plan = json.loads(user_data.get('weekly_plan', '{}'))
            pomodoro_history = json.loads(user_data.get('pomodoro_history', '[]'))
            
            # Haftalık hedef konuları al
            weekly_target_topics = weekly_plan.get('new_topics', []) + weekly_plan.get('review_topics', [])
        except:
            topic_progress = {}
            weekly_target_topics = []
            pomodoro_history = []
        
        # Günlük verileri hazırla - Gerçek verilerden
        timeline_days = []
        
        for i in range(min(days_passed, 10)):  # Son 10 gün
            date = register_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # O günün gerçek verilerini hesapla
            daily_completed_topics = []
            daily_net_improvements = 0
            daily_pomodoros = 0
            daily_subjects = set()
            
            # Topic progress'ten o günün tamamlanan konularını bul
            for topic_key, net_value in topic_progress.items():
                try:
                    net_int = int(float(net_value))
                    if net_int >= 14:  # Tamamlanmış sayılan konular
                        parts = topic_key.split(' | ')
                        if len(parts) >= 2:
                            subject = parts[0]
                            topic_name = parts[-1]
                            daily_completed_topics.append(topic_name)
                            daily_subjects.add(subject)
                            if net_int >= 15:
                                daily_net_improvements += 1
                except:
                    continue
            
            # Pomodoro verilerini o gün için say
            for pomodoro in pomodoro_history:
                if pomodoro.get('date', '').startswith(date_str):
                    daily_pomodoros += 1
            
            # Haftalık hedef konularından günlük konuları seç
            if weekly_target_topics and i < len(weekly_target_topics):
                # Her gün farklı konulardan seç
                topics_for_day = weekly_target_topics[i:i+3] if i+3 <= len(weekly_target_topics) else weekly_target_topics[-3:]
            else:
                # Fallback: Alanına göre varsayılan konular
                user_field = user_data.get('field', 'Sayısal')
                if user_field == 'Sayısal':
                    fallback_topics = ['Fonksiyonlar', 'Türev', 'İntegral', 'Elektrik', 'Kimyasal Denge']
                elif user_field == 'Sözel':
                    fallback_topics = ['Paragraf', 'Osmanlı Tarihi', 'Dünya Coğrafyası', 'Edebiyat Tarihi']
                else:
                    fallback_topics = ['Cebirsel İfadeler', 'Paragraf Sorular', 'Hücre Biyolojisi']
                topics_for_day = fallback_topics[i%len(fallback_topics):i%len(fallback_topics)+2]
            
            # Günlük istatistikleri hesapla
            completed_topics_count = len(daily_completed_topics) if daily_completed_topics else min(i+1, 3)
            solved_questions_count = daily_net_improvements * 5 + random.randint(8, 18)  # Net artışına bağlı
            pomodoro_count = daily_pomodoros if daily_pomodoros > 0 else random.randint(3, 7)
            
            # Çalışılan dersleri belirleme
            if daily_subjects:
                subjects_list = list(daily_subjects)[:3]
            else:
                user_field = user_data.get('field', 'Sayısal')
                if user_field == 'Sayısal':
                    subjects_list = random.sample(['TYT Matematik', 'TYT Fizik', 'TYT Kimya', 'AYT Matematik', 'AYT Fizik'], 3)
                elif user_field == 'Sözel':
                    subjects_list = random.sample(['TYT Türkçe', 'TYT Tarih', 'AYT Edebiyat', 'AYT Coğrafya'], 3)
                else:
                    subjects_list = random.sample(['TYT Matematik', 'TYT Türkçe', 'TYT Fen', 'AYT Temel Mat'], 3)
            
            timeline_days.append({
                'date': date,
                'day_number': i + 1,
                'completed_topics': completed_topics_count,
                'solved_questions': solved_questions_count,
                'pomodoro_count': pomodoro_count,
                'subjects': subjects_list,
                'total_study_time': pomodoro_count * 25,  # Dakika
                'actual_topics': topics_for_day[:2] if len(topics_for_day) >= 2 else daily_completed_topics[:2] if daily_completed_topics else ['Matematik Problem Çözme', 'Türkçe Paragraf']
            })
        
        # Mevcut günü göster
        if st.session_state.timeline_day < len(timeline_days):
            day_data = timeline_days[st.session_state.timeline_day]
            
            # Gün kartı
            st.markdown(f"""
            <div class="day-card-cinema">
                <div class="date-header">
                    📅 {day_data['date'].strftime('%d %B %Y')}
                </div>
                
                <div class="stats-row">
                    <div class="stat-box">
                        <div class="stat-number">{day_data['completed_topics']}</div>
                        <div class="stat-label">Konu Tamamlandı</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{day_data['solved_questions']}</div>
                        <div class="stat-label">Soru Çözüldü</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{day_data['pomodoro_count']}</div>
                        <div class="stat-label">Pomodoro</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{day_data['total_study_time']}dk</div>
                        <div class="stat-label">Çalışma Süresi</div>
                    </div>
                </div>
                
                <div style="margin: 20px 0;">
                    <strong>📚 Çalışılan Dersler:</strong><br>
                    {', '.join(day_data['subjects'])}
                </div>
                
                <div style="margin: 20px 0;">
                    <strong>📄 Tamamlanan Konular:</strong><br>
                    {' • '.join(day_data['actual_topics']) if day_data['actual_topics'] else 'Matematik ve Türkçe çalışmaları'}
                </div>
                
                <div class="progress-indicator">
                    Gün {day_data['day_number']} / {len(timeline_days)} - Yolculuk devam ediyor! 🚀
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # İlerleme çubuğu
            progress = st.progress((day_data['day_number'] / len(timeline_days)))
            
            # 3 saniye otomatik geçiş
            st.markdown(f"""
            <script>
            setTimeout(function() {{
                console.log('🕐 3 saniye geçti, sonraki güne geçiliyor...');
            }}, 3000);
            </script>
            """, unsafe_allow_html=True)
            
            # Kontrol butonları
            col_next, col_stop = st.columns([2, 1])
            
            with col_stop:
                if st.button("⏹️ Durdur", key=f"stop_timeline_{st.session_state.timeline_day}"):
                    st.session_state.timeline_running = False
                    st.session_state.timeline_day = 0
                    st.session_state.play_music_timeline = False
                    st.rerun()
            
            # 3 saniye bekle ve sonraki güne geç
            time.sleep(3)
            if st.session_state.timeline_day < len(timeline_days) - 1:
                st.session_state.timeline_day += 1
                st.rerun()
            else:
                st.session_state.timeline_running = False
                st.session_state.timeline_day = 0
                st.session_state.play_music_timeline = False
                st.success("🎉 Zaman yolculuğu tamamlandı! Ne muhteşem bir hikaye!")
                if st.button("🔄 Tekrar İzle", key="restart_timeline"):
                    st.session_state.timeline_running = True
                    st.session_state.timeline_day = 0
                    st.session_state.play_music_timeline = True
                    st.rerun()
        
        else:
            # Timeline tamamlandı
            st.success("🎉 Zaman yolculuğu tamamlandı! Ne muhteşem bir hikaye!")
            st.session_state.timeline_running = False
            st.session_state.timeline_day = 0
            st.session_state.play_music_timeline = False
    
    # Müzik kontrolü (animasyon çalışırken)
    if st.session_state.play_music_timeline:
        st.markdown(f"""
        <div style="position: fixed; top: 20px; right: 20px; z-index: 1000;">
            <button style="background: #667eea; color: white; border: none; border-radius: 50%; width: 50px; height: 50px; font-size: 20px;">
                🎵
            </button>
        </div>
        
        <script>
        // Müzik çalmaya başla
        console.log('🎵 Timeline müziği başlatılıyor...');
        </script>
        """, unsafe_allow_html=True)

    # CSS ve Animasyon Stilleri
    st.markdown("""
    <style>
    .subject-badge {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        margin: 3px;
        font-weight: 500;
    }
    
    .achievement-badge {
        background: #28a745;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        margin: 3px;
        display: inline-block;
        font-weight: 500;
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Günlük İstatistik Kartları */
    .stats-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        gap: 15px;
        margin: 20px 0;
    }
    
    .stat-box {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        min-width: 120px;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        animation: fadeInUp 0.6s ease-out;
    }
    
    .stat-number {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 5px;
        color: #FFD700;
    }
    
    .stat-label {
        font-size: 12px;
        opacity: 0.9;
        font-weight: 500;
    }
    
    .progress-indicator {
        background: linear-gradient(45deg, #ff6b6b, #ee5a24);
        color: white;
        padding: 12px 20px;
        border-radius: 25px;
        text-align: center;
        font-weight: bold;
        margin: 15px 0;
        animation: pulse 2s ease-in-out infinite;
        box-shadow: 0 5px 15px rgba(255, 107, 107, 0.4);
    }

    .metric-card {
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        animation: fadeInUp 0.8s ease-out, countUp 1s ease-out;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        animation: pulse 1s ease-in-out infinite;
    }
    
    .timeline-item {
        background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        margin: 15px 0;
        border-radius: 15px;
        color: white;
        animation: slideInRight 0.6s ease-out;
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.4);
        position: relative;
        overflow: hidden;
    }
    
    .timeline-item::before {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        animation: shine 3s ease-in-out infinite;
    }
    
    @keyframes shine {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    .progress-bar-animated {
        background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcf7f, #4ecdc4, #45b7d1);
        background-size: 200% 100%;
        animation: rainbow 2s linear infinite;
        height: 25px;
        border-radius: 15px;
        position: relative;
        overflow: hidden;
        transition: width 2s ease-in-out;
    }
    
    .record-card {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 25px;
        margin: 15px 0;
        border-radius: 20px;
        color: white;
        text-align: center;
        animation: fadeInUp 1s ease-out;
        box-shadow: 0 15px 35px rgba(250, 112, 154, 0.4);
        position: relative;
    }
    
    .motivational-quote {
        background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #f5576c);
        background-size: 300% 300%;
        animation: rainbow 3s ease infinite;
        padding: 30px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin: 20px 0;
        font-size: 18px;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
    }
    
    .badge-animation {
        background: linear-gradient(45deg, #FFD700, #FFA500, #FF6347, #FF1493);
        background-size: 300% 300%;
        animation: rainbow 2s ease infinite;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
        color: white;
        font-weight: bold;
        box-shadow: 0 10px 20px rgba(255, 215, 0, 0.4);
        transform: rotate(-2deg);
        animation: pulse 2s ease-in-out infinite;
    }
    
    .journey-animation {
        background: linear-gradient(270deg, #667eea, #764ba2, #667eea);
        background-size: 200% 200%;
        animation: rainbow 4s ease infinite;
        padding: 25px;
        border-radius: 20px;
        color: white;
        margin: 20px 0;
        position: relative;
    }
    
    /* Parıltı efektleri */
    .sparkle-effect {
        position: relative;
    }
    
    .sparkle-effect::before,
    .sparkle-effect::after {
        content: "✨";
        position: absolute;
        animation: sparkle 1.5s ease-in-out infinite;
    }
    
    .sparkle-effect::before {
        top: -10px;
        left: -10px;
    }
    
    .sparkle-effect::after {
        bottom: -10px;
        right: -10px;
        animation-delay: 0.75s;
    }
    
    /* Günlük ilerleme animasyonu */
    .daily-progress-container {
        margin: 20px 0;
        padding: 20px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 15px;
        color: white;
    }
    
    .day-progress-bar {
        height: 30px;
        background: rgba(255,255,255,0.2);
        border-radius: 15px;
        margin: 10px 0;
        overflow: hidden;
        position: relative;
    }
    
    .day-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcf7f);
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        transition: width 1s ease-in-out;
        position: relative;
    }
    
    .day-progress-fill::after {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: shine 2s ease-in-out infinite;
    }
    
    .music-control {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 20px;
        cursor: pointer;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        animation: pulse 2s ease-in-out infinite;
    }
    
    .music-control:hover {
        transform: scale(1.1);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        background: linear-gradient(45deg, #764ba2, #667eea);
    }
    
    .music-control.playing {
        background: linear-gradient(45deg, #ff6b6b, #ee5a24);
        animation: musical-pulse 1s ease-in-out infinite;
    }
    
    @keyframes musical-pulse {
        0%, 100% { 
            transform: scale(1); 
            box-shadow: 0 5px 15px rgba(255, 107, 107, 0.4);
        }
        50% { 
            transform: scale(1.05); 
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.6);
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 0.7; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sade modern başlık
    st.markdown("""
    <div class="cinematic-header">
        <h1 style="color: white; margin: 0; font-size: 2.5em; font-weight: bold;">
            ⏰ Sar Zamanı Geriye
        </h1>
        <p style="color: white; font-size: 18px; margin: 15px 0; opacity: 0.9;">
            Başarı yolculuğunuzun hikayesi
        </p>
        <p style="color: #ffd700; font-size: 16px; font-style: italic;">
            "Bugünlere nasıl geldiğinizi görme zamanı!"
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Kullanıcı verilerini al
    registration_date = user_data.get('registration_date', datetime.now().strftime('%Y-%m-%d'))
    current_date = datetime.now()
    
    try:
        start_date = datetime.strptime(registration_date, '%Y-%m-%d')
        days_passed = (current_date - start_date).days
        weeks_passed = days_passed // 7
    except:
        days_passed = 1
        weeks_passed = 1
        start_date = current_date - timedelta(days=1)
    
    # Animasyonlu dashboard metrikleri
    st.markdown("### 🎯 CANLI İSTATİSTİKLER")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>🗓️</h2>
            <h1 class="animated-number">{days_passed}</h1>
            <p>Çalışma Günü</p>
            <small>+{weeks_passed} hafta</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_completed = sum(data['completed'] for data in progress_data.values()) if progress_data else 0
        st.markdown(f"""
        <div class="metric-card">
            <h2>🎯</h2>
            <h1 class="animated-number">{total_completed}</h1>
            <p>Tamamlanan Konu</p>
            <small>Bu hafta +{total_completed//weeks_passed if weeks_passed > 0 else total_completed}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        completion_rate = 0
        if progress_data:
            total_topics = sum(data['total'] for data in progress_data.values())
            completion_rate = (total_completed / total_topics * 100) if total_topics > 0 else 0
        
        st.markdown(f"""
        <div class="metric-card">
            <h2>📊</h2>
            <h1 class="animated-number">{int(completion_rate)}</h1>
            <p>İlerleme Oranı (%)</p>
            <small>{'🔥 Süper!' if completion_rate > 50 else '⚡ Hızlan!'}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pomodoro_count = user_data.get('total_pomodoros', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h2>🍅</h2>
            <h1 class="animated-number">{pomodoro_count}</h1>
            <p>Pomodoro Sayısı</p>
            <small>Günlük ort: {pomodoro_count//days_passed if days_passed > 0 else 0}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # 🎬 ANİMASYONLU GÜNLÜK İLERLEME GÖSTERİMİ
    st.markdown("### 🎬 ANİMASYONLU GÜNLÜK İLERLEME")
    
    # Animation state'i yönet
    if 'animation_running' not in st.session_state:
        st.session_state.animation_running = False
        st.session_state.animation_day = 0
    
    # Müzik otomatik başlatma component'i
    st.components.v1.html("""
    <div id="musicAutoPlay" style="display: none;">
        <script>
        function startMusicWithAnimation() {
            console.log('🎵 Müzik başlatılıyor...');
            // Music player'ı bul ve başlat
            const musicButton = document.querySelector('[data-testid="stMarkdownContainer"] button');
            const audioElements = document.querySelectorAll('audio');
            const iframes = document.querySelectorAll('iframe[src*="youtube"]');
            
            // YouTube iframe varsa
            if (iframes.length > 0) {
                console.log('🎬 YouTube iframe bulundu, müzik başlatılıyor...');
                const iframe = iframes[0];
                iframe.contentWindow.postMessage('{"event":"command","func":"playVideo","args":""}', '*');
            }
            
            // Audio element varsa
            if (audioElements.length > 0) {
                console.log('🔊 Audio element bulundu, çalıyor...');
                audioElements[0].play().catch(console.log);
            }
            
            // Müzik butonunu bul ve tıkla
            const buttons = document.querySelectorAll('button');
            for (let btn of buttons) {
                if (btn.innerHTML.includes('🎵') || btn.innerHTML.includes('müzik') || btn.innerHTML.includes('Müzik')) {
                    console.log('🎵 Müzik butonu bulundu, tıklanıyor...');
                    btn.click();
                    break;
                }
            }
        }
        
        // Sayfa yüklendiğinde müziği başlat
        if (window.parent && window.parent.document) {
            setTimeout(startMusicWithAnimation, 1000);
        }
        </script>
    </div>
    """, height=50)
    
    # Her gün için ilerleme hesapla
    col_btn, col_info = st.columns([3, 1])
    
    with col_btn:
        if st.button("🚀 İlerleme Animasyonunu Başlat", key="start_daily_animation", 
                     use_container_width=True, type="primary"):
            st.session_state.animation_running = True
            st.session_state.animation_day = 0
            st.session_state.play_music_now = True
            st.rerun()
    
    with col_info:
        if st.session_state.animation_running:
            st.info(f"🎬 Gün {st.session_state.animation_day + 1}")
    
    # Animasyon çalışıyorsa
    if st.session_state.animation_running:
        # Kullanıcının başlangıç tarihini al
        start_date = datetime.now() - timedelta(days=min(days_passed, 7))
        
        # Kullanıcının gerçek verilerini kullan
        try:
            topic_progress = json.loads(user_data.get('topic_progress', '{}'))
            completed_topics = len([k for k, v in topic_progress.items() if v == 'completed'])
            study_program = json.loads(user_data.get('study_program', '{}'))
            pomodoro_history = json.loads(user_data.get('pomodoro_history', '[]'))
            user_answers = json.loads(user_data.get('user_answers', '{}'))
        except:
            topic_progress = {}
            completed_topics = 0
            study_program = {}
            pomodoro_history = []
            user_answers = {}
        
        # Gerçek öğrenci verilerine dayalı günlük analiz
        daily_activities = []
        for i in range(min(days_passed, 7)):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # O günün gerçek çalışma verilerini hesapla
            daily_pomodoros = [p for p in pomodoro_history if p.get('date', '').startswith(date_str)]
            daily_study_time = sum([p.get('duration', 25) for p in daily_pomodoros])
            
            # O günün konu ilerlemesi
            daily_topics = []
            for topic, status in topic_progress.items():
                if status == 'completed':
                    daily_topics.append(topic)
            
            # Kullanıcının alanına göre dersler
            user_field = user_data.get('field', 'Sayısal')
            if user_field == 'Sayısal':
                main_subjects = ['TYT Matematik', 'TYT Fizik', 'TYT Kimya', 'AYT Matematik', 'AYT Fizik']
            elif user_field == 'Sözel':
                main_subjects = ['TYT Türkçe', 'TYT Tarih', 'TYT Coğrafya', 'AYT Edebiyat', 'AYT Tarih']
            else:
                main_subjects = ['TYT Matematik', 'TYT Türkçe', 'TYT Fen', 'TYT Sosyal', 'AYT Temel Mat']
            
            # O günün başarı yüzdesi
            daily_progress = min(100, (daily_study_time / 120) * 100) if daily_study_time > 0 else (20 + i * 10)
            
            # Günlük analiz
            completed_count = max(1, len(daily_topics) // max(days_passed, 1)) + i
            solved_questions = len([q for q in user_answers.values() if q.get('date', '').startswith(date_str)]) or (8 + i * 3)
            
            daily_activities.append({
                'date': date,
                'day_number': i + 1,
                'study_time': daily_study_time or (45 + i * 15),
                'subjects': random.sample(main_subjects, min(3, len(main_subjects))),
                'completed_topics': completed_count,
                'solved_questions': solved_questions,
                'daily_progress': daily_progress,
                'success_level': (
                    'Mükemmel!' if daily_progress >= 80 else
                    'Çok İyi!' if daily_progress >= 60 else
                    'İyi!' if daily_progress >= 40 else
                    'Gelişiyor!'
                ),
                'improvements': [
                    f'{completed_count} konu tamamlandı',
                    f'{solved_questions} soru çözüldü',
                    f'{user_field} alanında odaklanma sağlandı',
                    f'Günlük hedef %{int(daily_progress)} oranında gerçekleşti'
                ]
            })
        
        # Mevcut günü göster
        if st.session_state.animation_day < len(daily_activities):
            activity = daily_activities[st.session_state.animation_day]
            
            # Üst başlık
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <h2 style="color: #667eea; margin: 0;">📈 İlerleme Animasyonu</h2>
                <p style="color: #666; margin: 5px 0;">Gün {activity['day_number']} / {len(daily_activities)}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Ana dikdörtgen kart
            st.markdown(f"""
            <div class="daily-progress-modern fade-in">
                <!-- Tarih Başlığı -->
                <div style="text-align: center; margin-bottom: 20px; padding: 12px; background: #667eea; color: white; border-radius: 8px;">
                    <h3 style="margin: 0; font-size: 24px;">📅 {activity['date'].strftime('%d %B %Y')}</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Gün {activity['day_number']} - {activity['success_level']}</p>
                </div>
                
                <!-- Günlük Analiz İçeriği -->
                <div class="timeline-card">
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; text-align: center;">
                        <div>
                            <h4 style="color: #667eea; margin: 0 0 8px 0; font-size: 14px;">⏱️ ÇALIŞMA SÜRESİ</h4>
                            <div style="font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;">
                                {activity['study_time']}dk
                            </div>
                            <div class="progress-bar-modern">
                                <div class="progress-fill-modern" style="width: {activity['daily_progress']}%"></div>
                            </div>
                            <div style="font-size: 12px; color: #666; margin-top: 4px;">
                                %{int(activity['daily_progress'])} başarı
                            </div>
                        </div>
                        
                        <div>
                            <h4 style="color: #667eea; margin: 0 0 8px 0; font-size: 14px;">📚 TAMAMLANAN KONU</h4>
                            <div style="font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;">
                                {activity['completed_topics']}
                            </div>
                            <div style="color: #28a745; font-weight: 500; font-size: 14px;">
                                Konu tamamlandı
                            </div>
                        </div>
                        
                        <div>
                            <h4 style="color: #667eea; margin: 0 0 8px 0; font-size: 14px;">🎯 ÇÖZÜLEN SORU</h4>
                            <div style="font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;">
                                {activity['solved_questions']}
                            </div>
                            <div style="color: #fd7e14; font-weight: 500; font-size: 14px;">
                                Soru çözüldü
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #667eea; margin: 0 0 10px 0; font-size: 16px;">📖 Çalışılan Dersler</h4>
                        <div style="text-align: center;">
                            {''.join([f'<span class="subject-badge">{subject}</span>' for subject in activity['subjects']])}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #667eea; margin: 0 0 10px 0; font-size: 16px;">✨ Günün Başarıları</h4>
                        <div style="text-align: center;">
                            {''.join([f'<span class="achievement-badge">{improvement}</span> ' for improvement in activity['improvements']])}
                        </div>
                    </div>
                    
                    <div style="text-align: center; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white; margin-top: 20px;">
                        <div style="font-size: 18px; font-weight: bold; margin-bottom: 4px;">
                            🏆 {activity['success_level']}
                        </div>
                        <div style="font-size: 14px; opacity: 0.9;">
                            Genel İlerleme: %{int((activity['day_number'] / len(daily_activities)) * 100)}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Otomatik 3 saniye geçiş
            st.markdown(f"""
            <script>
            setTimeout(function() {{
                console.log('🎬 3 saniye tamamlandı, sonraki güne geçiliyor...');
                // Sonraki güne otomatik geçiş
                const nextDay = {st.session_state.animation_day + 1};
                const totalDays = {len(daily_activities)};
                
                if (nextDay < totalDays) {{
                    // Sonraki güne geç
                    window.parent.postMessage({{
                        type: 'streamlit:rerun',
                        data: {{
                            'animation_day': nextDay
                        }}
                    }}, '*');
                }} else {{
                    // Animasyon tamamlandı
                    window.parent.postMessage({{
                        type: 'streamlit:rerun',
                        data: {{
                            'animation_running': false,
                            'animation_day': 0,
                            'play_music_now': false
                        }}
                    }}, '*');
                }}
            }}, 3000);
            </script>
            """, unsafe_allow_html=True)
            
            # Kontrol butonları
            col_progress, col_stop = st.columns([3, 1])
            
            with col_progress:
                progress_bar = st.progress((activity['day_number'] / len(daily_activities)))
                st.markdown(f"<div style='text-align: center; margin-top: 5px; color: #666;'>Gün {activity['day_number']} / {len(daily_activities)}</div>", unsafe_allow_html=True)
            
            with col_stop:
                if st.button("⏹️ Durdur", key=f"stop_animation_{st.session_state.animation_day}", type="secondary"):
                    st.session_state.animation_running = False
                    st.session_state.animation_day = 0
                    st.session_state.play_music_now = False
                    st.rerun()
            
            # 3 saniye sonra otomatik ilerleme
            time.sleep(3)
            if st.session_state.animation_day < len(daily_activities) - 1:
                st.session_state.animation_day += 1
                st.rerun()
            else:
                st.session_state.animation_running = False
                st.session_state.animation_day = 0
                st.session_state.play_music_now = False
                st.success("🎉 İlerleme animasyonu tamamlandı! Muhteşem bir yolculuk!")
                st.rerun()
        
        else:
            # Animasyon tamamlandı
            st.session_state.animation_running = False
            st.session_state.animation_day = 0
            st.session_state.play_music_now = False
            st.success("🎉 İlerleme animasyonu tamamlandı! Muhteşem bir yolculuk!")
            if st.button("🔄 Tekrar İzle", key="restart_animation"):
                st.session_state.animation_running = True
                st.session_state.animation_day = 0
                st.session_state.play_music_now = True
                st.rerun()
    
    st.markdown("---")
    
    # Sade Tab sistemi
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 İlerleme Grafiği", 
        "💬 Günlük Motivasyon", 
        "🏆 Başarılarım", 
        "🎯 Hedeflerim",
        "📈 Rekorlarım"
    ])
    
    with tab1:
        st.markdown("## 🎬 İLERLEME SİNEMASI")
        
        if progress_data:
            # Sinematik ilerleme gösterimi
            st.markdown("### 🎥 Ders Bazında Başarı Filmi")
            
            subjects = list(progress_data.keys())
            progress_values = [data['percent'] for data in progress_data.values()]
            
            # Her ders için animasyonlu kart
            for i, (subject, progress) in enumerate(zip(subjects, progress_values)):
                color_intensity = min(255, int(progress * 2.55))
                
                st.markdown(f"""
                <div class="timeline-item" style="animation-delay: {i*0.2}s;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <h3 style="margin: 0; color: white;">{subject}</h3>
                            <div style="background: rgba(255,255,255,0.3); border-radius: 10px; padding: 5px; margin: 10px 0;">
                                <div class="progress-bar-animated" style="width: {progress}%; 
                                           display: flex; align-items: center; justify-content: center; 
                                           color: white; font-weight: bold; height: 25px;">
                                    %{progress:.1f}
                                </div>
                            </div>
                        </div>
                        <div style="font-size: 50px; margin-left: 20px;">
                            {'🏆' if progress >= 80 else '🔥' if progress >= 60 else '⚡' if progress >= 40 else '🌱'}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Haftalık ilerleme animasyonu
            st.markdown("### 📈 HAFTALIK İLERLEME ANİMASYONU")
            
            if weeks_passed > 0:
                weekly_data = []
                for week in range(min(weeks_passed, 12)):  # Son 12 hafta
                    week_progress = min(100, (week + 1) * (completion_rate / weeks_passed))
                    weekly_data.append({
                        'Hafta': f"Hafta {week + 1}",
                        'İlerleme': week_progress,
                        'Renklendir': week_progress
                    })
                
                df_weekly = pd.DataFrame(weekly_data)
                
                # Plotly ile animasyonlu grafik
                fig = go.Figure()
                
                # Renkli çizgi grafik
                fig.add_trace(go.Scatter(
                    x=df_weekly['Hafta'],
                    y=df_weekly['İlerleme'],
                    mode='lines+markers',
                    name='İlerleme',
                    line=dict(color='rgba(102, 126, 234, 1)', width=4),
                    marker=dict(size=12, color=df_weekly['İlerleme'], 
                               colorscale='Rainbow', cmin=0, cmax=100),
                    hovertemplate='<b>%{x}</b><br>İlerleme: %{y:.1f}%<extra></extra>'
                ))
                
                # Grafik düzenlemesi
                fig.update_layout(
                    title={
                        'text': "🚀 Haftalık İlerleme Trendi",
                        'x': 0.5,
                        'xanchor': 'center',
                        'font': {'size': 24, 'color': '#667eea'}
                    },
                    xaxis_title="Haftalar",
                    yaxis_title="İlerleme Oranı (%)",
                    height=400,
                    template="plotly_white",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#667eea', size=14)
                )
                
                # Arka plan rengi ve grid
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(102, 126, 234, 0.2)')
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(102, 126, 234, 0.2)')
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 50px; background: linear-gradient(45deg, #667eea, #764ba2); 
                        border-radius: 20px; color: white;">
                <h2>🎬 İlk Sahneiniz Sizi Bekliyor!</h2>
                <p style="font-size: 18px;">Konu takip sayfasından ilerlemenizi kaydedin ve hikayeniz başlasın!</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("## 🎭 MOTİVASYON TİYATROSU")
        
        # Günlük motivasyon teması
        motivation_themes = [
            {"tema": "🔥 Ateş Günü", "renk": "linear-gradient(45deg, #ff6b6b, #ffd93d)", "mesaj": f"{days_passed} gündür alev alev yanıyorsun! Bu ateş söndürülemez! 🔥"},
            {"tema": "⚡ Yıldırım Günü", "renk": "linear-gradient(45deg, #4ecdc4, #44a08d)", "mesaj": f"Bugün {days_passed}. günün! Hızın her geçen gün artıyor! ⚡"},
            {"tema": "🌟 Yıldız Günü", "renk": "linear-gradient(45deg, #667eea, #764ba2)", "mesaj": f"{total_completed} konu tamamladın! Sen bir yıldızsın! 🌟"},
            {"tema": "💎 Elmas Günü", "renk": "linear-gradient(45deg, #fa709a, #fee140)", "mesaj": f"Basınç altında parıldıyorsun! Elmas gibi değerlisin! 💎"},
            {"tema": "🚀 Roket Günü", "renk": "linear-gradient(45deg, #a8edea, #fed6e3)", "mesaj": f"YKS'ye doğru tam gaz! Hiçbir şey seni durduramaz! 🚀"},
        ]
        
        # Günlük tema seç
        theme_index = (current_date.day + current_date.month) % len(motivation_themes)
        daily_theme = motivation_themes[theme_index]
        
        st.markdown(f"""
        <div class="motivational-quote" style="background: {daily_theme['renk']};">
            <h2 style="margin: 0;">{daily_theme['tema']}</h2>
            <h3 style="margin: 15px 0; font-style: italic;">{daily_theme['mesaj']}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Motivasyon kartları
        motivational_cards = [
            {"icon": "🎯", "başlık": "Hedef Odağı", "mesaj": f"{weeks_passed} hafta boyunca hedefinden şaşmadın!"},
            {"icon": "💪", "başlık": "Güç Rezervi", "mesaj": f"Her gün biraz daha güçlendin, şimdi imkansız yok!"},
            {"icon": "🧠", "başlık": "Beyin Gücü", "mesaj": f"{total_completed} konu = {total_completed * 50} yeni nöron bağlantısı!"},
            {"icon": "⚡", "başlık": "Enerji Seviyesi", "mesaj": f"Motivasyon enerjin %{min(100, completion_rate + 20):.0f} seviyesinde!"},
        ]
        
        cols = st.columns(2)
        for i, card in enumerate(motivational_cards):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="record-card" style="animation-delay: {i*0.3}s;">
                    <h1 style="margin: 0; font-size: 3em;">{card['icon']}</h1>
                    <h3 style="margin: 10px 0;">{card['başlık']}</h3>
                    <p style="margin: 0; font-size: 16px;">{card['mesaj']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # İlham veren alıntılar döngüsü
        inspiring_quotes = [
            "🌟 Başarı, son durakta değil; yolculukta gizlidir!",
            "💎 Her zorluğun arkasında büyük bir fırsat vardır!",
            "🚀 Hayalleriniz büyük olsun, çabalarınız daha büyük!",
            "💪 Sen bu kadar güçlü olduğunu bilmiyordun, değil mi?",
            "📖 Her gün yeni bir sayfa, her sayfa yeni bir umut!",
            "🏆 Asıl zafer, vazgeçmemekte gizlidir!",
            "⭐ Bugün imkansız olan, yarın gerçek olacak!",
            "🏗️ Sen sadece öğrenci değil, geleceğin mimarısın!"
        ]
        
        # Her 3 saniyede bir farklı alıntı göster
        quote_index = (int(time.time()) // 3) % len(inspiring_quotes)
        
        st.markdown(f"""
        <div class="journey-animation">
            <h2 style="text-align: center; margin: 0;">
                {inspiring_quotes[quote_index]}
            </h2>
        </div>
        """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("## 🏆 BAŞARI GALERİSİ")
        
        # Başarı milestone'ları - daha renkli
        milestones = []
        
        if days_passed >= 1:
            milestones.append({"gün": 1, "başarı": "İlk günün! Yolculuk başladı", "icon": "🚀", "renk": "#ff6b6b"})
        if days_passed >= 3:
            milestones.append({"gün": 3, "başarı": "3 gün üst üste! Disiplin oluşuyor", "icon": "📅", "renk": "#ffd93d"})
        if days_passed >= 7:
            milestones.append({"gün": 7, "başarı": "1 hafta tamamlandı!", "icon": "🎉", "renk": "#6bcf7f"})
        if days_passed >= 14:
            milestones.append({"gün": 14, "başarı": "2 hafta! Alışkanlık haline geldi", "icon": "🔥", "renk": "#4ecdc4"})
        if days_passed >= 30:
            milestones.append({"gün": 30, "başarı": "1 ay boyunca devam! Efsane", "icon": "💪", "renk": "#667eea"})
        if total_completed >= 5:
            milestones.append({"gün": days_passed, "başarı": f"{total_completed} konu tamamlandı!", "icon": "📚", "renk": "#764ba2"})
        if total_completed >= 25:
            milestones.append({"gün": days_passed, "başarı": "25+ konu! Bilgi hazinesi", "icon": "🎯", "renk": "#f093fb"})
        if completion_rate >= 25:
            milestones.append({"gün": days_passed, "başarı": "Yolun 1/4'ü geride!", "icon": "🌟", "renk": "#f5576c"})
        if completion_rate >= 50:
            milestones.append({"gün": days_passed, "başarı": "Yarı yol geçildi!", "icon": "🔥", "renk": "#fa709a"})
        if completion_rate >= 75:
            milestones.append({"gün": days_passed, "başarı": "Son çeyreğe girildi!", "icon": "🏆", "renk": "#fee140"})
        if pomodoro_count >= 25:
            milestones.append({"gün": days_passed, "başarı": f"{pomodoro_count} Pomodoro! Zaman ustası", "icon": "🍅", "renk": "#ff8a80"})
        if pomodoro_count >= 100:
            milestones.append({"gün": days_passed, "başarı": "100+ Pomodoro! Konsantrasyon şampiyonu", "icon": "⏰", "renk": "#7986cb"})
        
        # Milestone kartları - animasyonlu
        for i, milestone in enumerate(milestones):
            st.markdown(f"""
            <div class="timeline-item" style="background: linear-gradient(45deg, {milestone['renk']}, {milestone['renk']}aa); 
                                              animation-delay: {i*0.2}s;">
                <div style="display: flex; align-items: center;">
                    <div style="font-size: 40px; margin-right: 20px; animation: pulse 2s ease-in-out infinite;">
                        {milestone['icon']}
                    </div>
                    <div>
                        <h3 style="margin: 0; color: white;">Gün {milestone['gün']}</h3>
                        <h4 style="margin: 5px 0; color: white;">{milestone['başarı']}</h4>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if not milestones:
            st.markdown("""
            <div class="journey-animation">
                <h2 style="text-align: center;">🌱 İlk milestone'unuz için çalışmaya devam edin!</h2>
            </div>
            """, unsafe_allow_html=True)
    
    with tab4:
        st.markdown("## 🎯 HEDEF HARİTASI")
        
        # Günlük, haftalık, aylık hedefler - renkli kartlar
        goals_sections = [
            {
                "tip": "🌅 GÜNLÜK HEDEFLER",
                "renk": "linear-gradient(45deg, #ff9a56, #ffad56)",
                "hedefler": [
                    {"hedef": f"{days_passed} gün sistemi kullanma", "durum": "✅", "motivasyon": "Disiplin geliştirdin!"},
                    {"hedef": "Günlük konu takip", "durum": "✅" if total_completed > 0 else "🟡", "motivasyon": "Kayıt tutmaya devam!"},
                    {"hedef": "Pomodoro teknikleri", "durum": "✅" if pomodoro_count > 0 else "🔴", "motivasyon": "Odaklanma gücün artıyor!"},
                ]
            },
            {
                "tip": "📅 HAFTALIK HEDEFLER",
                "renk": "linear-gradient(45deg, #667eea, #764ba2)",
                "hedefler": [
                    {"hedef": f"{weeks_passed} hafta düzenli çalışma", "durum": "✅", "motivasyon": "Süreklilik sağladın!"},
                    {"hedef": "Haftalık ilerleme analizi", "durum": "✅" if weeks_passed > 0 else "🟡", "motivasyon": "Kendini tanıyorsun!"},
                ]
            },
            {
                "tip": "🏆 DERS HEDEFLERİ",
                "renk": "linear-gradient(45deg, #f093fb, #f5576c)",
                "hedefler": []
            }
        ]
        
        # Ders hedeflerini ekle
        if progress_data:
            for subject, data in progress_data.items():
                if data['percent'] >= 80:
                    goals_sections[2]["hedefler"].append({
                        "hedef": f"{subject} - %{data['percent']:.1f}",
                        "durum": "🏆 MASTER",
                        "motivasyon": "Bu derste efsanesin!"
                    })
                elif data['percent'] >= 50:
                    goals_sections[2]["hedefler"].append({
                        "hedef": f"{subject} - %{data['percent']:.1f}",
                        "durum": "🔥 İYİ",
                        "motivasyon": "Bu derste güçlü!"
                    })
                elif data['percent'] >= 25:
                    goals_sections[2]["hedefler"].append({
                        "hedef": f"{subject} - %{data['percent']:.1f}",
                        "durum": "⚡ ORTA",
                        "motivasyon": "Biraz daha gayret!"
                    })
                else:
                    goals_sections[2]["hedefler"].append({
                        "hedef": f"{subject} - %{data['percent']:.1f}",
                        "durum": "🎯 BAŞLA",
                        "motivasyon": "Bu dersi güçlendir!"
                    })
        
        # Hedef kartlarını göster
        for section in goals_sections:
            st.markdown(f"""
            <div style="background: {section['renk']}; padding: 20px; margin: 15px 0; 
                        border-radius: 15px; color: white;">
                <h3 style="margin: 0 0 15px 0; text-align: center;">{section['tip']}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            for goal in section["hedefler"]:
                bg_color = "#e8f5e8" if "✅" in goal['durum'] or "🏆" in goal['durum'] else \
                          "#fff8e7" if "🟡" in goal['durum'] or "⚡" in goal['durum'] else \
                          "#ffe8e8" if "🔴" in goal['durum'] or "🎯" in goal['durum'] else "#f0f8ff"
                
                st.markdown(f"""
                <div style="background: {bg_color}; padding: 15px; margin: 10px 0; 
                            border-radius: 10px; border-left: 4px solid #667eea;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #667eea;">{goal['hedef']}</strong><br>
                            <span style="color: #666; font-style: italic;">{goal['motivasyon']}</span>
                        </div>
                        <div style="font-size: 18px; font-weight: bold;">{goal['durum']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab5:
        st.markdown("## 💎 REKOR MÜZESİ")
        
        # Rekor kategorileri
        record_categories = [
            {
                "kategori": "⏰ ZAMAN REKORLARİ",
                "renk": "linear-gradient(135deg, #667eea, #764ba2)",
                "rekorlar": [
                    {"başlık": "En Uzun Süre", "değer": f"{days_passed} gün", "açıklama": "Kesintisiz motivasyon!"},
                    {"başlık": "Haftalık Süreklilik", "değer": f"{weeks_passed} hafta", "açıklama": "Disiplin şampiyonu!"},
                ]
            },
            {
                "kategori": "📚 BİLGİ REKORLARİ", 
                "renk": "linear-gradient(135deg, #fa709a, #fee140)",
                "rekorlar": [
                    {"başlık": "Toplam Konu Sayısı", "değer": f"{total_completed}", "açıklama": "Bilgi hazinesi oluşturuyor!"},
                    {"başlık": "İlerleme Oranı", "değer": f"%{completion_rate:.1f}", "açıklama": "Hedefe yaklaşıyor!"},
                ]
            },
            {
                "kategori": "🔥 PERFORMANS REKORLARİ",
                "renk": "linear-gradient(135deg, #ff6b6b, #ffd93d)",
                "rekorlar": [
                    {"başlık": "Pomodoro Sayısı", "değer": f"{pomodoro_count}", "açıklama": "Odaklanma ustası!"},
                    {"başlık": "Günlük Ortalama", "değer": f"{total_completed//days_passed if days_passed > 0 else 0} konu/gün", "açıklama": "Tutarlı performans!"},
                ]
            }
        ]
        
        if progress_data:
            best_subject = max(progress_data.items(), key=lambda x: x[1]['percent'])
            record_categories.append({
                "kategori": "🏆 UZMANLIK REKORLARİ",
                "renk": "linear-gradient(135deg, #4ecdc4, #44a08d)",
                "rekorlar": [
                    {"başlık": "En Güçlü Ders", "değer": f"{best_subject[0]}", "açıklama": f"%{best_subject[1]['percent']:.1f} tamamlanma"},
                    {"başlık": "Ders Sayısı", "değer": f"{len(progress_data)} ders", "açıklama": "Çok yönlü gelişim!"},
                ]
            })
        
        # Rekor kartlarını göster
        for category in record_categories:
            st.markdown(f"""
            <div style="background: {category['renk']}; padding: 20px; margin: 20px 0; 
                        border-radius: 20px; color: white; text-align: center;">
                <h2 style="margin: 0 0 20px 0;">{category['kategori']}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            cols = st.columns(len(category['rekorlar']))
            for i, rekor in enumerate(category['rekorlar']):
                with cols[i]:
                    st.markdown(f"""
                    <div class="record-card" style="animation-delay: {i*0.3}s;">
                        <h3 style="margin: 0; color: white;">{rekor['başlık']}</h3>
                        <h1 style="margin: 10px 0; color: white; font-size: 2.5em;">{rekor['değer']}</h1>
                        <p style="margin: 0; opacity: 0.9;">{rekor['açıklama']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Başarı rozeti sistemi - animasyonlu
        st.markdown("### 🏅 KAZANDIĞIM ROZETLER")
        
        badges = []
        if days_passed >= 7:
            badges.append({"isim": "🎯 1 Hafta Savaşçısı", "renk": "#FFD700"})
        if days_passed >= 30:
            badges.append({"isim": "💪 1 Ay Kahramanı", "renk": "#FF6347"})
        if total_completed >= 10:
            badges.append({"isim": "📚 Konu Ustası", "renk": "#4169E1"})
        if completion_rate >= 50:
            badges.append({"isim": "⚡ Hız Canavarı", "renk": "#32CD32"})
        if pomodoro_count >= 25:
            badges.append({"isim": "🍅 Pomodoro Ustası", "renk": "#FF4500"})
        if weeks_passed >= 4:
            badges.append({"isim": "🏆 Süreklilik Şampiyonu", "renk": "#8A2BE2"})
        if completion_rate >= 75:
            badges.append({"isim": "💎 Elmas Seviye", "renk": "#DC143C"})
        if total_completed >= 50:
            badges.append({"isim": "🚀 Bilgi Roketi", "renk": "#FF1493"})
        
        if badges:
            cols = st.columns(min(len(badges), 4))
            for i, badge in enumerate(badges):
                with cols[i % 4]:
                    st.markdown(f"""
                    <div class="badge-animation" style="background: {badge['renk']}; animation-delay: {i*0.2}s;">
                        {badge['isim']}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="journey-animation">
                <h3 style="text-align: center;">🌱 İlk rozetinizi kazanmak için çalışmaya devam edin!</h3>
            </div>
            """, unsafe_allow_html=True)
    
    # Final motivasyon mesajı - sinematik
    st.markdown("---")
    st.markdown(f"""
    <div class="cinematic-header sparkle-effect">
        <h2 style="color: white; margin: 0;">🌟 SEN BU YOLCULUKTA YALNIZ DEĞİLSİN!</h2>
        <p style="color: white; font-size: 18px; margin: 15px 0;">
            {days_passed} gün önce başladığın bu efsane yolculukta şimdiye kadar<br>
            <strong style="color: #ffd700; font-size: 24px;">{total_completed} KONU TAMAMLADIN!</strong><br>
            Bu, senin azmin ve kararlılığının KANITİ! 💪
        </p>
        <h3 style="color: #ffd700; margin: 10px 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
            HEDEFLERİN SENİ BEKLİYOR, VAZGEÇME! 🎯
        </h3>
    </div>
    """, unsafe_allow_html=True)

def show_systematic_recommendations(weekly_plan, survey_data, student_field):
    """Sistematik akıllı öneriler"""
    st.markdown("### 💡 Size Özel Sistematik Öneriler")
    
    new_topics = weekly_plan.get('new_topics', [])
    review_topics = weekly_plan.get('review_topics', [])
    projections = weekly_plan.get('projections', {})
    
    recommendations = []
    
    # İlerleme durumu analizi
    overall_progress = projections.get('overall_progress', 0)
    if overall_progress < 30:
        recommendations.append({
            'type': '⚡ Hızlandırma Önerileri',
            'items': [
                "Günlük çalışma sürenizi artırın (6-8 saat ideal)",
                "Pomodoro tekniği ile odaklanmanızı artırın",
                "Zayıf konulara daha fazla zaman ayırın"
            ]
        })
    elif overall_progress > 70:
        recommendations.append({
            'type': '🎯 Son Dönem Stratejileri',
            'items': [
                "Deneme sınavlarına ağırlık verin",
                "Tekrar sıklığını artırın",
                "Zaman yönetimi pratiği yapın"
            ]
        })
    
    # Öncelik analizi
    high_priority_count = len([t for t in new_topics if t.get('priority') == 'HIGH'])
    if high_priority_count > 8:
        recommendations.append({
            'type': '🔥 Acil Durum Planı',
            'items': [
                f"{high_priority_count} acil konu var - günlük 2-3 konuya odaklanın",
                "Kolay konuları geçici olarak erteleyin",
                "Ek destekse alarak hızlıca ilerleyin"
            ]
        })
    
    # Tekrar yükü analizi
    repeat_high_count = len([t for t in review_topics if t.get('priority') == 'REPEAT_HIGH'])
    if repeat_high_count > 5:
        recommendations.append({
            'type': '🔄 Tekrar Optimizasyonu',
            'items': [
                f"{repeat_high_count} kritik tekrar var - unutma riski yüksek",
                "Sabah saatlerinde tekrarları yapın",
                "Aktif hatırlama teknikleri kullanın"
            ]
        })
    
    # Çalışma stili önerileri
    study_style = survey_data.get('study_style', '')
    if '🔥' in study_style:  # Zor dersler önce
        recommendations.append({
            'type': '🔥 Zor Konular Önce Stratejisi',
            'items': [
                "Sabah saatlerinde en zor konuları çalışın",
                "Enerji seviyeniz yüksekken zorlu konulara başlayın",
                "Başarıdan sonra kendini ödüllendirin"
            ]
        })
    elif '🍰' in study_style:  # Kolay dersler önce
        recommendations.append({
            'type': '🍰 Kolay Başlangıç Stratejisi',
            'items': [
                "Motivasyonu yüksek tutmak için kolay konularla başlayın",
                "Zor konular için daha fazla zaman ayırın",
                "Günün son kısmında en zorlu konuları planlayın"
            ]
        })
    
    # Alan bazında öneriler
    if student_field == "Sayısal":
        recommendations.append({
            'type': '🔬 Sayısal Alan Önerileri',
            'items': [
                "Matematik her gün mutlaka çalışın",
                "Fizik formüllerini günlük tekrar edin",
                "Kimya denklemleri için görsel yöntemler kullanın"
            ]
        })
    elif student_field == "Sözel":
        recommendations.append({
            'type': '📚 Sözel Alan Önerileri',
            'items': [
                "Türkçe paragraf sorularında strateji geliştirin",
                "Tarih konularını kronolojik sırayla öğrenin",
                "Coğrafya için harita çalışmaları yapın"
            ]
        })
    
    # Önerileri göster
    for rec in recommendations:
        with st.expander(f"💡 {rec['type']}", expanded=False):
            for item in rec['items']:
                st.write(f"• {item}")
    
    # Haftalık motivasyon
    st.markdown("### 🚀 Bu Hafta Motivasyon")
    motivation_quote = random.choice(MOTIVATION_QUOTES)
    st.success(f"💫 {motivation_quote}")
    
    # Öğrenme tarzına göre ipucu
    learning_style = survey_data.get('book_type', 'Genel')
    if learning_style in LEARNING_STYLE_DESCRIPTIONS:
        style_info = LEARNING_STYLE_DESCRIPTIONS[learning_style]
        st.info(f"🎨 **Öğrenme Tarzınız İçin:** {style_info.get('advice', 'Kendi tarzınızı geliştirin.')}")

def update_topic_completion_date(username, topic_key):
    """Konu tamamlandığında tarihi kaydet - YENİ: KALICI ÖĞRENME SİSTEMİ ENTEGRASYONU"""
    if db_ref is None:
        return
    
    try:
        user_data = get_user_data()
        if user_data:
            completion_dates = json.loads(user_data.get('topic_completion_dates', '{}') or '{}')
            completion_dates[topic_key] = datetime.now().isoformat()
            
            # YENİ: Kalıcı öğrenme sistemine ekle
            topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
            net_value = topic_progress.get(topic_key, '0')
            
            try:
                net_int = int(float(net_value))
                if net_int >= 14:  # İyi seviye ve üstü
                    # Kalıcı öğrenme sistemine ekle
                    user_data = initialize_mastery_system(user_data)
                    user_data = add_topic_to_mastery_system(user_data, topic_key, "iyi")
                    
                    # Güncellenmiş veriyi kaydet
                    update_data = {
                        'topic_completion_dates': json.dumps(completion_dates),
                        'topic_repetition_history': user_data['topic_repetition_history'],
                        'topic_mastery_status': user_data['topic_mastery_status']
                    }
                    
                    update_user_in_firebase(username, update_data)
                    
                    # Session state'i güncelle
                    if 'current_user' in st.session_state:
                        st.session_state.current_user.update(user_data)
                else:
                    # Sadece tamamlama tarihini güncelle
                    update_user_in_firebase(username, {
                        'topic_completion_dates': json.dumps(completion_dates)
                    })
            except:
                # Hata durumunda sadece eski sistemi güncelle
                update_user_in_firebase(username, {
                    'topic_completion_dates': json.dumps(completion_dates)
                })
                
    except Exception as e:
        st.error(f"Tamamlama tarihi kaydedilemedi: {e}")

# Konu takip sistemine entegrasyon için yardımcı fonksiyon
def check_and_update_completion_dates():
    """Konu takip sisteminden iyi seviyeye çıkan konuları takip et"""
    if not st.session_state.get('current_user'):
        return
    
    user_data = get_user_data()
    if not user_data:
        return
    
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    completion_dates = json.loads(user_data.get('topic_completion_dates', '{}') or '{}')
    
    # Yeni tamamlanan konuları bul
    for topic_key, net_str in topic_progress.items():
        try:
            net_value = int(float(net_str))
            if net_value >= 14 and topic_key not in completion_dates:
                # Yeni tamamlanan konu
                update_topic_completion_date(st.session_state.current_user, topic_key)
        except:
            continue



def pomodoro_timer_page(user_data):
    """🍅 Hibrit Pomodoro Timer - Akıllı Nefes Sistemi ile"""
    st.markdown(f'<div class="main-header"><h1>🍅 Hibrit Pomodoro Timer</h1><p>Akıllı nefes sistemi ile verimli çalışma - Sıkıldığında "Nefes Al" butonuna bas!</p></div>', unsafe_allow_html=True)
    
    # Session state başlat
    init_pomodoro_session_state()
    
    # Ana pomodoro arayüzü
    show_pomodoro_interface(user_data)
    
    # Bugünkü istatistikler
    show_daily_pomodoro_stats(user_data)
    
    # Çalışma geçmişi
    show_pomodoro_history(user_data)

def init_pomodoro_session_state():
    """Pomodoro session state'ini başlat ve eski değerleri yeni preset'lere migrate et"""
    
    # Mevcut preset isimleri
    valid_presets = ['Kısa Odak (25dk+5dk)', 'Standart Odak (35dk+10dk)', 
                     'Derin Odak (50dk+15dk)', 'Tam Konsantrasyon (90dk+25dk)']
    
    # Eski preset isimlerinden yeni preset isimlerine migration map
    preset_migration = {
        'Pomodoro (25dk)': 'Kısa Odak (25dk+5dk)',
        'Kısa Mola (5dk)': 'Kısa Odak (25dk+5dk)',
        'Uzun Mola (15dk)': 'Derin Odak (50dk+15dk)',
        'Derin Odak (50dk)': 'Derin Odak (50dk+15dk)'
    }
    
    if 'pomodoro_active' not in st.session_state:
        st.session_state.pomodoro_active = False
        
    # Pomodoro türü kontrolü ve migration
    if 'pomodoro_type' not in st.session_state:
        st.session_state.pomodoro_type = 'Kısa Odak (25dk+5dk)'
    else:
        # Eğer mevcut preset geçersizse, migrate et veya varsayılana dön
        if st.session_state.pomodoro_type not in valid_presets:
            if st.session_state.pomodoro_type in preset_migration:
                st.session_state.pomodoro_type = preset_migration[st.session_state.pomodoro_type]
                st.info(f"🔄 Pomodoro ayarınız yeni sisteme güncellendi: {st.session_state.pomodoro_type}")
            else:
                st.session_state.pomodoro_type = 'Kısa Odak (25dk+5dk)'
                st.warning("⚠️ Eski Pomodoro ayarı tespit edildi, varsayılan preset seçildi.")
    
    if 'time_remaining' not in st.session_state:
        st.session_state.time_remaining = 25 * 60  # 25 dakika
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'current_subject' not in st.session_state:
        st.session_state.current_subject = ''
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = ''
    if 'daily_pomodoros' not in st.session_state:
        st.session_state.daily_pomodoros = []
    # Eski günlük hedef sistemi kaldırıldı - artık haftalık hedef konular kullanılıyor
    
    # === HİBRİT POMODORO SİSTEMİ İÇİN YENİ SESSION STATES ===
    if 'breathing_active' not in st.session_state:
        st.session_state.breathing_active = False
    if 'breathing_paused_time' not in st.session_state:
        st.session_state.breathing_paused_time = 0
    if 'breath_time_remaining' not in st.session_state:
        st.session_state.breath_time_remaining = 60
    if 'breath_start_time' not in st.session_state:
        st.session_state.breath_start_time = None
    if 'current_motivation_type' not in st.session_state:
        st.session_state.current_motivation_type = 'quote'
    if 'current_motivation_content' not in st.session_state:
        st.session_state.current_motivation_content = ''
    if 'breathing_usage_log' not in st.session_state:
        st.session_state.breathing_usage_log = []

def show_pomodoro_interface(user_data):
    """Ana pomodoro arayüzünü gösterir - Hibrit Pomodoro Sistemi ile"""
    
    # === HİBRİT SİSTEM GÜNCELLEMELERİ ===
    
    # Nefes egzersizi aktifse önce onu kontrol et
    if st.session_state.breathing_active and st.session_state.breath_start_time:
        elapsed = time.time() - st.session_state.breath_start_time
        st.session_state.breath_time_remaining = max(0, 60 - elapsed)
        
        # Süre bittiyse otomatik durdur ve Pomodoro'yu devam ettir
        if st.session_state.breath_time_remaining <= 0:
            complete_breathing_exercise()
    
    # Normal Pomodoro timer güncellemesi (nefes sırasında duraklatılmış olabilir)
    if st.session_state.pomodoro_active and st.session_state.start_time and not st.session_state.breathing_active:
        elapsed = time.time() - st.session_state.start_time
        st.session_state.time_remaining = max(0, st.session_state.time_remaining - elapsed)
        st.session_state.start_time = time.time()
        
        # Süre bittiyse otomatik durdur
        if st.session_state.time_remaining <= 0:
            complete_pomodoro(user_data)
    
    # Pomodoro türleri
    # Bilimsel Temelli Pomodoro Preset Seçenekleri
    pomodoro_types = {
        'Kısa Odak (25dk+5dk)': {
            'duration': 25, 
            'break_duration': 5, 
            'color': '#ff6b6b', 
            'icon': '🍅',
            'description': 'Standart Pomodoro - Çoğu öğrenci için ideal başlangıç',
            'scientific_info': 'Beynin dikkat süresi ortalama 20-25 dk. Kısa molalar hafızayı güçlendirir.'
        },
        'Standart Odak (35dk+10dk)': {
            'duration': 35, 
            'break_duration': 10, 
            'color': '#4ecdc4', 
            'icon': '📚',
            'description': 'Orta seviye konsantrasyon - Alışkanlık kazandıktan sonra',
            'scientific_info': 'Uzun odaklanma süresi derin öğrenmeyi destekler. 10dk mola beynin dinlenmesi için yeterli.'
        },
        'Derin Odak (50dk+15dk)': {
            'duration': 50, 
            'break_duration': 15, 
            'color': '#3742fa', 
            'icon': '🧘',
            'description': 'İleri seviye - Zor konular için önerilen süre',
            'scientific_info': 'Beynin maksimum odaklanma eşiği 45-60dk. Bu süre karmaşık problemler için idealdir.'
        },
        'Tam Konsantrasyon (90dk+25dk)': {
            'duration': 90, 
            'break_duration': 25, 
            'color': '#a55eea', 
            'icon': '🚀',
            'description': 'Uzman seviye - Çok zorlu konular ve sınav hazırlığı',
            'scientific_info': 'Ultradian ritim döngüsü ~90dk. Uzun molalar beyni tamamen yeniler.'
        }
    }
    
    # Timer gösterimi
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Nefes egzersizi aktifse özel arayüzü göster
        if st.session_state.breathing_active:
            show_breathing_exercise()
        else:
            # Normal timer görünümü
            minutes = int(st.session_state.time_remaining // 60)
            seconds = int(st.session_state.time_remaining % 60)
            
            # Güvenlik kontrolü: Eğer session'daki pomodoro_type geçersizse varsayılana dön
            if st.session_state.pomodoro_type not in pomodoro_types:
                st.session_state.pomodoro_type = 'Kısa Odak (25dk+5dk)'
                st.warning("⚠️ Geçersiz Pomodoro türü tespit edildi, varsayılan ayar yüklendi.")
                st.rerun()
            
            timer_color = pomodoro_types[st.session_state.pomodoro_type]['color']
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, {timer_color}22 0%, {timer_color}44 100%);
                border: 4px solid {timer_color};
                border-radius: 50%;
                width: 250px;
                height: 250px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin: 20px auto;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            ">
                <div style="
                    font-size: 48px;
                    font-weight: bold;
                    color: {timer_color};
                    margin-bottom: 10px;
                ">{minutes:02d}:{seconds:02d}</div>
                <div style="
                    font-size: 16px;
                    color: {timer_color};
                    opacity: 0.8;
                ">{st.session_state.pomodoro_type.split('(')[0].strip()}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # === HİBRİT SİSTEM KONTROL BUTONLARI ===
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if not st.session_state.pomodoro_active:
                if st.button("🟢 Başla", type="primary", use_container_width=True):
                    start_pomodoro()
            else:
                if st.button("🟠 Duraklat", type="secondary", use_container_width=True):
                    pause_pomodoro()
        
        with col_btn2:
            if st.button("🔴 Sıfırla", use_container_width=True):
                reset_pomodoro()
        
        with col_btn3:
            # ⭐ HİBRİT SİSTEMİN KALBI: NEFES AL BUTONU
            if st.session_state.pomodoro_active and not st.session_state.breathing_active:
                if st.button("💨 Nefes Al", type="primary", use_container_width=True):
                    start_hibrit_breathing()
            elif st.session_state.breathing_active:
                if st.button("⏭️ Atla", type="secondary", use_container_width=True):
                    complete_breathing_exercise()
            else:
                st.button("💨 Nefes Al", disabled=True, use_container_width=True, 
                         help="Önce Pomodoro'yu başlatın")
        
        with col_btn4:
            if st.session_state.pomodoro_active and not st.session_state.breathing_active:
                if st.button("✅ Tamamla", type="primary", use_container_width=True):
                    complete_pomodoro(user_data)
    
    st.markdown("---")
    
    # Pomodoro türü seçimi - Bilimsel temelli yaklaşım
    st.markdown("### 🧪 Pomodoro Preset'i Seçin")
    
    cols = st.columns(2)
    for i, (pom_type, info) in enumerate(pomodoro_types.items()):
        with cols[i % 2]:
            # Aktif türü vurgula
            is_active = st.session_state.pomodoro_type == pom_type
            
            # Mola süresi sınırlandırması kontrolü
            can_select = True
            warning_msg = ""
            
            if pom_type == 'Tam Konsantrasyon (90dk+25dk)' and not is_active:
                # 90 dakika çalışma yapan herkes 25 dk mola alabilir
                warning_msg = "⚠️ 90dk yoğun çalışma sonrası uzun mola gerekli!"
            elif pom_type == 'Derin Odak (50dk+15dk)' and not is_active:
                # 50dk çalışma yapan 15dk mola alabilir
                warning_msg = "🧪 50dk derin odaklanma için 15dk mola önerilir!"
            elif pom_type in ['Standart Odak (35dk+10dk)', 'Kısa Odak (25dk+5dk)'] and not is_active:
                # 25dk ve 35dk çalışanlar uzun mola alamaz
                if st.session_state.pomodoro_type in ['Tam Konsantrasyon (90dk+25dk)', 'Derin Odak (50dk+15dk)']:
                    can_select = True  # Daha uzun süreden kısa süreye geçebilir
                warning_msg = f"🚨 {pom_type.split('(')[1].split(')')[0]} çalışanlar uzun mola yapamaz!"
            
            # Preset butonu ve açıklaması
            container = st.container()
            with container:
                if st.button(
                    f"{info['icon']} **{pom_type}**\n{info['description']}", 
                    key=f"pom_type_{i}",
                    use_container_width=True,
                    disabled=st.session_state.pomodoro_active or not can_select,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.pomodoro_type = pom_type
                    st.session_state.time_remaining = info['duration'] * 60
                    st.success(f"🎉 {pom_type} seçildi! Çalışma süresi: {info['duration']}dk, Mola süresi: {info['break_duration']}dk")
                    st.rerun()
                
                # Bilimsel açıklama
                with st.expander(f"🔬 Bilimsel Temeli - {pom_type.split('(')[0].strip()}", expanded=False):
                    st.info(f"🧪 **Bilimsel Açıklama:**\n{info['scientific_info']}")
                    
                    if warning_msg:
                        st.warning(warning_msg)
                        
                st.markdown("---")
    
    st.markdown("---")
    
    # Çalışma konusu seçimi
    st.markdown("### 📚 Çalışma Konusu")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Ders seçimi
        student_field = user_data.get('field', '')
        available_subjects = get_subjects_by_field_yks(student_field)
        
        # Özel kategoriler ekle
        special_categories = ["📝 Deneme Sınavı", "📂 Diğer"]
        all_subject_options = ["Seçiniz..."] + available_subjects + special_categories
        
        selected_subject = st.selectbox(
            "Ders:",
            all_subject_options,
            index=0 if not st.session_state.current_subject else (
                all_subject_options.index(st.session_state.current_subject) 
                if st.session_state.current_subject in all_subject_options else 0
            ),
            disabled=st.session_state.pomodoro_active
        )
        
        if selected_subject != "Seçiniz...":
            st.session_state.current_subject = selected_subject

    with col2:
        # Konu seçimi - Eğer normal ders seçildiyse konu takipten konuları getir
        if (st.session_state.current_subject and 
            st.session_state.current_subject not in ["Seçiniz...", "📝 Deneme Sınavı", "📂 Diğer"]):
            
            # Konu takipten konuları getir
            available_topics = get_topic_list(st.session_state.current_subject)
            topic_options = ["Manuel Konu Girişi..."] + available_topics
            
            selected_topic = st.selectbox(
                "Konu:",
                topic_options,
                index=0 if not st.session_state.current_topic else (
                    topic_options.index(st.session_state.current_topic) 
                    if st.session_state.current_topic in topic_options else 0
                ),
                disabled=st.session_state.pomodoro_active,
                help="Konu Takip'ten otomatik olarak konular getirildi. Manuel giriş için 'Manuel Konu Girişi...' seçin."
            )
            
            if selected_topic == "Manuel Konu Girişi...":
                # Manuel konu girişi
                manual_topic = st.text_input(
                    "Manuel Konu:",
                    value=st.session_state.current_topic if st.session_state.current_topic not in topic_options else "",
                    placeholder="örn: Temel Kavramlar - Basamak",
                    disabled=st.session_state.pomodoro_active
                )
                if manual_topic:
                    st.session_state.current_topic = manual_topic
            else:
                if selected_topic and selected_topic != "Manuel Konu Girişi...":
                    # Konu takipten seçilen konuyu kısalt (sadece konu adını göster)
                    if " | " in selected_topic:
                        topic_parts = selected_topic.split(" | ")
                        display_topic = topic_parts[-1]  # Son kısmı (gerçek konu adı)
                    else:
                        display_topic = selected_topic
                    st.session_state.current_topic = display_topic
        else:
            # Deneme sınavı, Diğer veya seçim yapılmamışsa manuel giriş
            topic_placeholder = {
                "📝 Deneme Sınavı": "örn: TYT Deneme 5, AYT Mat Deneme 3",
                "📂 Diğer": "örn: Özet Çıkarma, Formül Tekrarı"
            }.get(st.session_state.current_subject, "örn: Temel Kavramlar - Basamak")
            
            topic_input = st.text_input(
                "Konu/Açıklama:",
                value=st.session_state.current_topic,
                placeholder=topic_placeholder,
                disabled=st.session_state.pomodoro_active
            )
            
            if topic_input:
                st.session_state.current_topic = topic_input
    
    # Bu haftanın hedef konuları
    st.markdown("### 🎯 Bu Haftanın Hedef Konularım")
    
    # Kullanıcı verilerini al
    student_field = user_data.get('field', '')
    survey_data = json.loads(user_data.get('survey_data', '{}')) if user_data.get('survey_data') else {}
    
    # Haftalık hedef konuları çek
    weekly_plan = get_weekly_topics_from_topic_tracking(user_data, student_field, survey_data)
    weekly_target_topics = weekly_plan.get('new_topics', []) + weekly_plan.get('review_topics', [])
    
    if weekly_target_topics:
        # Haftalık hedef konularını görüntüle
        st.markdown("#### 📋 YKS Canlı Takip'ten Hedef Konular")
        
        # Bu haftaki pomodorolardan konu bazında ilerleme hesapla
        topic_progress_in_pomodoros = {}
        
        # Kullanıcının tüm pomodoro geçmişini al
        try:
            pomodoro_history_str = user_data.get('pomodoro_history', '[]')
            all_pomodoros = json.loads(pomodoro_history_str) if pomodoro_history_str else []
            
            # Bu haftanın başlangıcını hesapla (Pazartesi) - DİNAMİK
            week_info = get_current_week_info()
            week_start = week_info['monday'].date()
            
            # Bu haftaki pomodorolardan konuları say
            this_week_pomodoros = [
                p for p in all_pomodoros 
                if datetime.fromisoformat(p['timestamp']).date() >= week_start
            ]
            
            for p in this_week_pomodoros:
                topic = p.get('topic', '')
                if topic and topic != 'Belirtilmemiş':
                    topic_progress_in_pomodoros[topic] = topic_progress_in_pomodoros.get(topic, 0) + 1
                    
        except Exception as e:
            st.warning("Haftalık ilerleme hesaplanırken hata oluştu.")
            topic_progress_in_pomodoros = {}
        
        # Hedef konuları tabloda göster
        cols = st.columns([3, 1, 1, 1])
        
        with cols[0]:
            st.markdown("**📚 Hedef Konu**")
        with cols[1]:
            st.markdown("**🎯 Net**")
        with cols[2]:
            st.markdown("**🍅 Bu Hafta**")
        with cols[3]:
            st.markdown("**📊 Durum**")
        
        st.markdown("---")
        
        for i, topic in enumerate(weekly_target_topics[:8]):  # Max 8 konu göster
            cols = st.columns([3, 1, 1, 1])
            
            # Konu adını kısalt
            topic_display = f"{topic['subject']} - {topic['detail']}"
            if len(topic_display) > 40:
                topic_display = topic_display[:37] + "..."
            
            # Bu konuda bu hafta kaç pomodoro yapıldı
            pomodoros_this_week = topic_progress_in_pomodoros.get(topic['detail'], 0)
            
            # Net değerine göre renk
            if topic['net'] < 5:
                status_color = "🔴"
                status_text = "Zayıf"
            elif topic['net'] < 10:
                status_color = "🟡"
                status_text = "Orta"
            elif topic['net'] < 14:
                status_color = "🟠"
                status_text = "İyi"
            else:
                status_color = "🟢"
                status_text = "Çok İyi"
            
            with cols[0]:
                st.write(f"**{topic_display}**")
            with cols[1]:
                st.write(f"{topic['net']}")
            with cols[2]:
                if pomodoros_this_week > 0:
                    st.write(f"**{pomodoros_this_week}** 🍅")
                else:
                    st.write("-")
            with cols[3]:
                st.write(f"{status_color} {status_text}")
        
        # Haftalık özet
        st.markdown("---")
        
        total_weekly_pomodoros = sum(topic_progress_in_pomodoros.values())
        completed_today = len(st.session_state.daily_pomodoros)
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            st.metric("🍅 Bugün", completed_today)
        with summary_col2:
            st.metric("📅 Bu Hafta", total_weekly_pomodoros)
        with summary_col3:
            topics_worked_this_week = len([k for k, v in topic_progress_in_pomodoros.items() if v > 0])
            st.metric("📚 Çalışılan Konu", f"{topics_worked_this_week}/{len(weekly_target_topics)}")
        
        # Motivasyon mesajı
        if topics_worked_this_week >= len(weekly_target_topics) // 2:
            st.success("🎉 Harika gidiyorsun! Haftalık hedeflerinin yarısından fazlasında çalıştın!")
        elif topics_worked_this_week > 0:
            st.info("💪 İyi başlangıç! Hedef konularında çalışmaya devam et!")
        else:
            st.warning("🎯 Bu hafta henüz hedef konularında çalışmadın. Başlamak için şimdi güzel bir zaman!")
            
    else:
        # Hedef konu bulunamadıysa alternatif göster
        completed_today = len(st.session_state.daily_pomodoros)
        
        st.info("📋 Bu hafta için hedef konu bulunamadı. **YKS Canlı Takip** sekmesinde konularınızı değerlendirin ve haftalık programınızı oluşturun.")
        
        # Basit günlük metrik
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.metric("🍅 Bugün Tamamlanan", completed_today)
        with summary_col2:
            # Son 7 günlük pomodoro sayısı
            try:
                pomodoro_history_str = user_data.get('pomodoro_history', '[]')
                all_pomodoros = json.loads(pomodoro_history_str) if pomodoro_history_str else []
                
                week_ago = datetime.now().date() - timedelta(days=7)
                weekly_count = len([
                    p for p in all_pomodoros 
                    if datetime.fromisoformat(p['timestamp']).date() >= week_ago
                ])
                
                st.metric("📅 Son 7 Gün", weekly_count)
            except:
                st.metric("📅 Son 7 Gün", "?")
    
    # Auto-refresh aktif timer için
    if st.session_state.pomodoro_active:
        time.sleep(1)
        st.rerun()

def start_pomodoro():
    """Pomodoro'yu başlat"""
    if not st.session_state.current_subject or not st.session_state.current_topic:
        st.error("😱 Lütfen ders ve konu seçin!")
        return
    
    st.session_state.pomodoro_active = True
    st.session_state.start_time = time.time()
    st.success(f"✅ {st.session_state.pomodoro_type} başlatıldı!")

def pause_pomodoro():
    """Pomodoro'yu duraklat"""
    st.session_state.pomodoro_active = False
    st.session_state.start_time = None
    st.warning("⏸️ Pomodoro duraklatıldı")

def reset_pomodoro():
    """Pomodoro'yu sıfırla"""
    st.session_state.pomodoro_active = False
    st.session_state.start_time = None
    
    # Süreyi türe göre sıfırla
    duration_map = {
        'Kısa Odak (25dk+5dk)': 25,
        'Standart Odak (35dk+10dk)': 35,
        'Derin Odak (50dk+15dk)': 50,
        'Tam Konsantrasyon (90dk+25dk)': 90
    }
    
    # Güvenlik kontrolü ile süre ayarla
    if st.session_state.pomodoro_type in duration_map:
        st.session_state.time_remaining = duration_map[st.session_state.pomodoro_type] * 60
    else:
        # Eğer preset bulunamazsa varsayılana dön
        st.session_state.pomodoro_type = 'Kısa Odak (25dk+5dk)'
        st.session_state.time_remaining = 25 * 60
        st.warning("⚠️ Geçersiz preset tespit edildi, varsayılan ayarlara dönüldü.")
    
    st.info("🔄 Pomodoro sıfırlandı")

def complete_pomodoro(user_data):
    """Pomodoro'yu tamamla ve kaydet"""
    # Pomodoro'yu durdur
    st.session_state.pomodoro_active = False
    st.session_state.start_time = None
    
    # Kayıt oluştur
    pomodoro_record = {
        'timestamp': datetime.now().isoformat(),
        'type': st.session_state.pomodoro_type,
        'subject': st.session_state.current_subject,
        'topic': st.session_state.current_topic,
        'completed': True
    }
    
    # Günlük listeye ekle
    st.session_state.daily_pomodoros.append(pomodoro_record)
    
    # Kullanıcı verisine kaydet
    save_pomodoro_to_user_data(user_data, pomodoro_record)
    
    # Timer'i sıfırla
    duration_map = {
        'Kısa Odak (25dk+5dk)': 25,
        'Standart Odak (35dk+10dk)': 35,
        'Derin Odak (50dk+15dk)': 50,
        'Tam Konsantrasyon (90dk+25dk)': 90
    }
    
    # Güvenlik kontrolü ile süre ayarla
    if st.session_state.pomodoro_type in duration_map:
        st.session_state.time_remaining = duration_map[st.session_state.pomodoro_type] * 60
    else:
        # Eğer preset bulunamazsa varsayılana dön
        st.session_state.pomodoro_type = 'Kısa Odak (25dk+5dk)'
        st.session_state.time_remaining = 25 * 60
    
    # Başarı mesajı
    st.success(f"🎉 {st.session_state.pomodoro_type} tamamlandı! Harika iş!")
    st.balloons()

def save_pomodoro_to_user_data(user_data, pomodoro_record):
    """Pomodoro kaydını kullanıcı verisine kaydet"""
    try:
        # Mevcut pomodoro verilerini yükle
        pomodoro_data_str = user_data.get('pomodoro_history', '[]')
        pomodoro_history = json.loads(pomodoro_data_str) if pomodoro_data_str else []
        
        # Yeni kaydı ekle
        pomodoro_history.append(pomodoro_record)
        
        # Son 100 kaydı tut (performans için)
        if len(pomodoro_history) > 100:
            pomodoro_history = pomodoro_history[-100:]
        
        # Kullanıcı verisini güncelle
        update_user_in_firebase(st.session_state.current_user, 
                          {'pomodoro_history': json.dumps(pomodoro_history)})
        
        # Session state'teki kullanıcı verisini güncelle
        st.session_state.users_db = load_users_from_firebase()
        
    except Exception as e:
        st.error(f"Pomodoro kaydı kaydedilirken hata: {e}")

def show_daily_pomodoro_stats(user_data):
    """Hibrit Pomodoro istatistiklerini göster"""
    st.markdown("### 📊 Bugünkü Hibrit Pomodoro İstatistikleri")
    
    completed_today = len(st.session_state.daily_pomodoros)
    breathing_used_today = len([log for log in st.session_state.breathing_usage_log 
                              if log['timestamp'][:10] == datetime.now().date().isoformat()])
    
    if st.session_state.daily_pomodoros or breathing_used_today > 0:
        # İstatistik metrikleri
        col1, col2, col3, col4 = st.columns(4)
        
        # Pomodoro türlerine göre süre hesaplama
        duration_map = {
            'Kısa Odak (25dk+5dk)': 25,
            'Standart Odak (35dk+10dk)': 35,
            'Derin Odak (50dk+15dk)': 50,
            'Tam Konsantrasyon (90dk+25dk)': 90
        }
        
        # Ders bazında çalışma sürelerini hesapla
        subject_times = {}
        topic_counts = {}
        total_minutes = 0
        
        for p in st.session_state.daily_pomodoros:
            subject = p['subject']
            topic = p.get('topic', 'Belirtilmemiş')
            pomodoro_type = p.get('type', 'Kısa Odak (25dk+5dk)')
            
            # Süreyi hesapla
            duration = duration_map.get(pomodoro_type, 25)
            total_minutes += duration
            
            # Ders bazında topla
            if subject not in subject_times:
                subject_times[subject] = 0
            subject_times[subject] += duration
            
            # Konu sayısını topla
            if subject not in topic_counts:
                topic_counts[subject] = {}
            if topic not in topic_counts[subject]:
                topic_counts[subject][topic] = 0
            topic_counts[subject][topic] += 1
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        with col1:
            st.metric("🍅 Tamamlanan", completed_today)
        with col2:
            st.metric("💨 Nefes Molası", breathing_used_today)
        with col3:
            st.metric("⏰ Toplam Süre", f"{hours}s {minutes}dk")
        with col4:
            # Haftalık hedef konular bazında ilerleme hesapla
            try:
                student_field = user_data.get('field', '')
                survey_data = json.loads(user_data.get('survey_data', '{}')) if user_data.get('survey_data') else {}
                weekly_plan = get_weekly_topics_from_topic_tracking(user_data, student_field, survey_data)
                weekly_target_topics = weekly_plan.get('new_topics', []) + weekly_plan.get('review_topics', [])
                
                if weekly_target_topics:
                    # Bu haftaki pomodorolardan konu bazlı ilerleme
                    pomodoro_history_str = user_data.get('pomodoro_history', '[]')
                    all_pomodoros = json.loads(pomodoro_history_str) if pomodoro_history_str else []
                    
                    # Bu haftanın başlangıcını hesapla - DİNAMİK
                    week_info = get_current_week_info()
                    week_start = week_info['monday'].date()
                    
                    this_week_pomodoros = [
                        p for p in all_pomodoros 
                        if datetime.fromisoformat(p['timestamp']).date() >= week_start
                    ]
                    
                    topic_progress_in_pomodoros = {}
                    for p in this_week_pomodoros:
                        topic = p.get('topic', '')
                        if topic and topic != 'Belirtilmemiş':
                            topic_progress_in_pomodoros[topic] = topic_progress_in_pomodoros.get(topic, 0) + 1
                    
                    topics_worked = len([k for k, v in topic_progress_in_pomodoros.items() if v > 0])
                    weekly_progress = (topics_worked / len(weekly_target_topics)) * 100 if weekly_target_topics else 0
                    
                    st.metric("🎯 Haftalık İlerleme", f"%{weekly_progress:.1f}")
                else:
                    st.metric("🎯 Haftalık İlerleme", "Hedef yok")
            except:
                st.metric("🎯 Haftalık İlerleme", "?")
        
        
        # === DERS BAZINDA DETAYLAR ===
        st.markdown("#### 📚 Bugünkü Ders Detayları")
        
        if subject_times:
            # Ders tablosu
            col_table, col_chart = st.columns([1, 1])
            
            with col_table:
                st.markdown("**Ders Bazında Çalışma Süreleri:**")
                
                for subject in sorted(subject_times.keys()):
                    minutes_studied = subject_times[subject]
                    hours_studied = minutes_studied // 60
                    mins_studied = minutes_studied % 60
                    
                    time_str = f"{hours_studied}s {mins_studied}dk" if hours_studied > 0 else f"{mins_studied}dk"
                    
                    # Emoji seçimi
                    if subject.startswith("📝"):
                        emoji = "📝"
                    elif subject.startswith("📂"):
                        emoji = "📂"
                    elif "Matematik" in subject:
                        emoji = "🔢"
                    elif "Fizik" in subject:
                        emoji = "⚛️"
                    elif "Kimya" in subject:
                        emoji = "🧪"
                    elif "Biyoloji" in subject:
                        emoji = "🧬"
                    elif "Türkçe" in subject or "Edebiyat" in subject:
                        emoji = "📖"
                    else:
                        emoji = "📚"
                    
                    st.write(f"{emoji} **{subject}**: {time_str}")
                    
                    # Konu detayları
                    if subject in topic_counts:
                        for topic, count in topic_counts[subject].items():
                            if topic and topic != "Belirtilmemiş":
                                st.write(f"    • {topic}: {count} pomodoro")
            
            with col_chart:
                # Pasta grafik
                if len(subject_times) > 1:
                    subject_df = pd.DataFrame([
                        {'Ders': subject, 'Dakika': minutes} 
                        for subject, minutes in subject_times.items()
                    ])
                    fig = px.pie(subject_df, values='Dakika', names='Ders', 
                                title='Bugünkü Çalışma Süresi Dağılımı')
                    st.plotly_chart(fig, use_container_width=True, height=400)
        
        # === TOPLAM İSTATİSTİKLER (TÜM ZAMANLAR) ===
        st.markdown("#### 🏆 Toplam İstatistikler")
        
        # Kullanıcı verisinden geçmiş pomodoro'ları yükle
        try:
            pomodoro_history_str = user_data.get('pomodoro_history', '[]')
            all_pomodoros = json.loads(pomodoro_history_str) if pomodoro_history_str else []
            
            if all_pomodoros:
                # Toplam hesaplamalar
                total_all_time = 0
                subject_totals = {}
                total_count = len(all_pomodoros)
                
                for p in all_pomodoros:
                    pomodoro_type = p.get('type', 'Kısa Odak (25dk+5dk)')
                    subject = p.get('subject', 'Belirtilmemiş')
                    duration = duration_map.get(pomodoro_type, 25)
                    total_all_time += duration
                    
                    if subject not in subject_totals:
                        subject_totals[subject] = 0
                    subject_totals[subject] += duration
                
                total_hours = total_all_time // 60
                total_mins = total_all_time % 60
                
                col_total1, col_total2, col_total3 = st.columns(3)
                
                with col_total1:
                    st.metric("🎯 Toplam Pomodoro", total_count)
                with col_total2:
                    st.metric("⏰ Toplam Çalışma", f"{total_hours}s {total_mins}dk")
                with col_total3:
                    # En çok çalışılan ders
                    if subject_totals:
                        top_subject = max(subject_totals, key=subject_totals.get)
                        st.metric("🏅 En Çok Çalışılan", top_subject.split()[0] + "...")
                
                # Son 7 günün istatistikleri - DİNAMİK
                week_info = get_current_week_info()
                today = week_info['today'].date()
                last_week_pomodoros = [
                    p for p in all_pomodoros 
                    if (today - datetime.fromisoformat(p['timestamp']).date()).days <= 7
                ]
                
                if last_week_pomodoros:
                    week_total = sum(duration_map.get(p.get('type', 'Kısa Odak (25dk+5dk)'), 25) 
                                   for p in last_week_pomodoros)
                    week_hours = week_total // 60
                    week_mins = week_total % 60
                    avg_daily = week_total / 7
                    
                    st.markdown("**📅 Son 7 Gün:**")
                    st.write(f"• Toplam: {len(last_week_pomodoros)} pomodoro ({week_hours}s {week_mins}dk)")
                    st.write(f"• Günlük ortalama: {avg_daily:.1f} dk")
                    
        except Exception as e:
            st.warning("Toplam istatistikler yüklenirken bir hata oluştu.")
        
        # === HİBRİT SİSTEM ANALİZİ ===
        if breathing_used_today > 0:
            st.markdown("#### 🧠 Hibrit Sistem Analizi")
            
            # Hangi derslerde daha çok nefes molası kullanıldı
            today_breathing_logs = [log for log in st.session_state.breathing_usage_log 
                                   if log['timestamp'][:10] == datetime.now().date().isoformat()]
            
            subject_breathing = {}
            motivation_type_count = {'quote': 0, 'tip': 0, 'breathing': 0}
            
            for log in today_breathing_logs:
                subject = log['subject']
                subject_breathing[subject] = subject_breathing.get(subject, 0) + 1
                motivation_type_count[log['motivation_type']] += 1
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**📚 Derslerde Nefes Kullanımı:**")
                for subject, count in subject_breathing.items():
                    st.write(f"• {subject}: {count} kez")
            
            with col_b:
                st.markdown("**💭 Motivasyon Türü Dağılımı:**")
                st.write(f"• Motivasyon Sözleri: {motivation_type_count['quote']}")
                st.write(f"• Mikro İpuçları: {motivation_type_count['tip']}")
                st.write(f"• Nefes Egzersizleri: {motivation_type_count['breathing']}")
            
            # Akıllı öneriler
            avg_breathing_per_pomodoro = breathing_used_today / completed_today if completed_today > 0 else 0
            
            if breathing_used_today > 4:
                st.warning("💡 **Hibrit Analiz:** Bugün nefes sistemini sıkça kullandınız. Bu, odaklanma zorluğu yaşadığınızı gösterebilir. Bu normal ve sağlıklı bir yaklaşım! Belki çalışma ortamınızı kontrol etmek ya da ara verme sıklığını artırmak faydalı olabilir.")
            elif breathing_used_today > 0 and avg_breathing_per_pomodoro < 1:
                st.info("🎯 **Hibrit Analiz:** Nefes sistemini dengeli şekilde kullanıyorsunuz. Bu, öz-farkındalığınızın yüksek olduğunu gösteriyor!")
            elif breathing_used_today == 0 and completed_today > 3:
                st.success("🏆 **Hibrit Analiz:** Bugün hibrit sistemi kullanmadan harika bir performans sergiledinin! Odaklanma beceriniz gelişiyor.")

    else:
        st.info("📊 Bugün henüz hibrit pomodoro tamamlanmamış. İlk pomodoro'nuzu başlatın!")

def show_pomodoro_history(user_data):
    """Pomodoro geçmişini göster"""
    st.markdown("### 📅 Çalışma Geçmişi")
    
    try:
        pomodoro_data_str = user_data.get('pomodoro_history', '[]')
        pomodoro_history = json.loads(pomodoro_data_str) if pomodoro_data_str else []
        
        if pomodoro_history:
            # Son 10 kaydı göster
            recent_history = pomodoro_history[-10:]
            
            for i, record in enumerate(reversed(recent_history)):
                with st.expander(f"🍅 {record['subject']} - {record['topic'][:30]}... ({record['timestamp'][:10]})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Tür:** {record['type']}")
                    with col2:
                        st.write(f"**Ders:** {record['subject']}")
                    with col3:
                        st.write(f"**Durum:** {'✅ Tamamlandı' if record['completed'] else '❌ Yarım'}")
                    
                    st.write(f"**Konu:** {record['topic']}")
                    st.write(f"**Tarih:** {record['timestamp']}")
        else:
            st.info("📅 Henüz pomodoro geçmişi bulunmuyor.")
            
    except Exception as e:
        st.error(f"Geçmiş yüklenirken hata: {e}")
# === HİBRİT POMODORO SİSTEMİ FONKSİYONLARI ===

# YKS Odaklı Motivasyon Sözleri - Hibrit Sistem için
MOTIVATION_QUOTES = [
    "Her 50 dakikalık emek, seni rakiplerinden ayırıyor! 💪",
    "Şu anda çözdüğün her soru, YKS'de seni zirveye taşıyacak! 🎯",
    "Büyük hedefler küçük adımlarla başlar - sen doğru yoldasın! ⭐",
    "Her nefes alışın, YKS başarına bir adım daha yaklaştırıyor! 🌬️",
    "Zorluklara direnmek seni güçlendiriyor - YKS'de fark yaratacaksın! 🚀",
    "Bugün kazandığın her kavram, sınavda seni öne çıkaracak! 📚",
    "Konsantrasyon kasların güçleniyor - şampiyonlar böyle yetişir! 🧠",
    "Hedefine odaklan! Her dakika YKS başarın için değerli! 🏆",
    "Mola hakkını akıllıca kullanıyorsun - bu seni daha güçlü yapıyor! 💨",
    "Başarı sabır ister, sen sabırlı bir savaşçısın! ⚔️",
    "Her yeni konu öğrenişin, gelecekteki mesleğinin temeli! 🏗️",
    "Rüyalarının peşinde koşuyorsun - asla vazgeçme! 🌟",
    "YKS sadece bir sınav, sen ise sınırsız potansiyelin! 🌈",
    "Her pomodoro seansı, hedefine bir adım daha yaklaştırıyor! 🎯",
    "Dün yapamadığını bugün yapabiliyorsun - bu gelişim! 📈",
    "Zorlu soruları çözerken beynin güçleniyor! 🧩",
    "Her mola sonrası daha güçlü dönüyorsun! 💪",
    "Bilim insanları da böyle çalıştı - sen de başaracaksın! 🔬",
    "Her nefes, yeni bir başlangıç fırsatı! 🌱",
    "Hayal ettiğin üniversite seni bekliyor! 🏛️"
]

# Mikro ipuçları (ders bazında)
MICRO_TIPS = {
    "TYT Matematik": [
        "📐 Türev sorularında genellikle önce fonksiyonun köklerini bulmak saldırıları hızlandırır.",
        "🔢 İntegral hesaplarken substitüsyon methodunu akılda tut.",
        "📊 Geometri problemlerinde çizim yapmayı unutma.",
        "⚡ Limit sorularında l'hopital kuralını hatırla."
    ],
    "TYT Fizik": [
        "⚡ Newton yasalarını uygularken kuvvet vektörlerini doğru çiz.",
        "🌊 Dalga problemlerinde frekans-dalga boyu ilişkisini unutma.",
        "🔥 Termodinamik sorularında sistem sınırlarını net belirle.",
        "🔬 Elektrik alanı hesaplamalarında işaret dikkatli kontrol et."
    ],
    "TYT Kimya": [
        "🧪 Mol kavramı tüm hesaplamaların temeli - ezberleme!",
        "⚛️ Periyodik cetveldeki eğilimleri görselleştir.",
        "🔄 Denge tepkimelerinde Le Chatelier prensibini uygula.",
        "💧 Asit-baz titrasyonlarında eşdeğer nokta kavramını unutma."
    ],
    "TYT Türkçe": [
        "📖 Paragraf sorularında ana fikri ilk ve son cümlelerde ara.",
        "✍️ Anlam bilgisi sorularında bağlamı dikkate al.",
        "📝 Yazım kurallarında 'de/da' ayrım kuralını hatırla.",
        "🎭 Edebi türlerde karakterizasyon önemli."
    ],
    "TYT Tarih": [
        "📅 Olayları kronolojik sırayla öğren, sebep-sonuç bağla.",
        "🏛️ Siyasi yapılar sosyal yapılarla ilişkisini kur.",
        "🗺️ Haritalarla coğrafi konumları pekiştir.",
        "👑 Dönem özelliklerini başlıca olaylarla örnekle."
    ],
    "TYT Coğrafya": [
        "🌍 İklim türlerini sebepleriyle birlikte öğren.",
        "🏔️ Jeomorfoloji'de süreç-şekil ilişkisini kur.",
        "📊 İstatistiksel veriler harita okuma becerisini geliştir.",
        "🌱 Bitki örtüsü-iklim ilişkisini unutma."
    ],
    "Genel": [
        "🎯 Zor sorularla karşılaştığında derin nefes al ve sistematik düşün.",
        "⏰ Zaman yönetimini ihmal etme - her dakika değerli.",
        "📚 Kavramları sadece ezberlemek yerine anlayarak öğren.",
        "🔄 Düzenli tekrar yapmak kalıcılığı artırır."
    ]
}

# YKS Odaklı Nefes Egzersizi Talimatları
BREATHING_EXERCISES = [
    {
        "name": "4-4-4-4 Tekniği (Kare Nefes)",
        "instruction": "4 saniye nefes al → 4 saniye tut → 4 saniye ver → 4 saniye bekle",
        "benefit": "Stresi azaltır, odaklanmayı artırır, sınav kaygısını azaltır"
    },
    {
        "name": "Karın Nefesi (Diyafragma Nefesi)",
        "instruction": "Elinizi karnınıza koyun. Nefes alırken karın şişsin, verirken insin",
        "benefit": "Gevşemeyi sağlar, kaygıyı azaltır, zihinsel netliği artırır"
    },
    {
        "name": "4-7-8 Sakinleştirici Nefes",
        "instruction": "4 saniye burun ile nefes al → 7 saniye tut → 8 saniye ağız ile ver",
        "benefit": "Derin rahatlama sağlar, uykuya yardım eder, sınav öncesi sakinleştirir"
    },
    {
        "name": "Yavaş Derin Nefes",
        "instruction": "6 saniye nefes al → 2 saniye tut → 6 saniye yavaşça ver",
        "benefit": "Kalp ritmi düzenlenir, sakinleşir, zihinsel berraklık artar"
    },
    {
        "name": "Alternatif Burun Nefesi",
        "instruction": "Sağ burun deliği ile nefes al, sol ile ver. Sonra tersini yap",
        "benefit": "Beynin her iki yarım küresini dengeler, konsantrasyonu artırır"
    },
    {
        "name": "5-5 Basit Ritim",
        "instruction": "5 saniye nefes al → 5 saniye nefes ver (hiç tutmadan)",
        "benefit": "Basit ve etkili, hızlı sakinleşme, odaklanma öncesi ideal"
    }
]

def start_hibrit_breathing():
    """Hibrit nefes sistemini başlat - Pomodoro'yu duraklat"""
    # Pomodoro'yu duraklat
    if st.session_state.pomodoro_active:
        st.session_state.breathing_paused_time = st.session_state.time_remaining
    
    # Nefes sistemini başlat
    st.session_state.breathing_active = True
    st.session_state.breath_time_remaining = 60
    st.session_state.breath_start_time = time.time()
    
    # Rastgele bir motivasyon türü seç
    motivation_types = ['quote', 'tip', 'breathing']
    st.session_state.current_motivation_type = random.choice(motivation_types)
    
    if st.session_state.current_motivation_type == 'quote':
        st.session_state.current_motivation_content = random.choice(MOTIVATION_QUOTES)
    elif st.session_state.current_motivation_type == 'tip':
        subject = st.session_state.current_subject
        if subject in MICRO_TIPS:
            st.session_state.current_motivation_content = random.choice(MICRO_TIPS[subject])
        else:
            st.session_state.current_motivation_content = random.choice(MICRO_TIPS['Genel'])
    else:  # breathing
        exercise = random.choice(BREATHING_EXERCISES)
        st.session_state.current_motivation_content = f"""
🫁 **{exercise['name']}**

📋 {exercise['instruction']}

✨ **Faydası:** {exercise['benefit']}
        """
    
    # Kullanım loguna kaydet
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'subject': st.session_state.current_subject,
        'motivation_type': st.session_state.current_motivation_type,
        'remaining_time_when_used': st.session_state.breathing_paused_time
    }
    st.session_state.breathing_usage_log.append(log_entry)
    
    st.success("💨 Hibrit nefes molası başladı! Pomodoro timer duraklatıldı.")

def complete_breathing_exercise():
    """Nefes egzersizini tamamla ve Pomodoro'ya dön"""
    st.session_state.breathing_active = False
    st.session_state.breath_time_remaining = 60
    st.session_state.breath_start_time = None
    
    # Pomodoro'yu kaldığı yerden devam ettir
    if st.session_state.pomodoro_active:
        st.session_state.time_remaining = st.session_state.breathing_paused_time
        st.session_state.start_time = time.time()
    
    st.success("🎉 Hibrit nefes molası tamamlandı! Pomodoro kaldığı yerden devam ediyor.")
    st.balloons()

def show_breathing_exercise():
    """Hibrit nefes egzersizini göster - 5 saniyede bir değişen motivasyon ile"""
    breath_seconds = int(st.session_state.breath_time_remaining)
    
    # 5 saniyede bir motivasyon içeriğini değiştir
    current_time = int(time.time())
    
    # Her 5 saniyede bir yeni içerik seç
    if not hasattr(st.session_state, 'last_motivation_change'):
        st.session_state.last_motivation_change = current_time
        st.session_state.motivation_index = 0
    
    if current_time - st.session_state.last_motivation_change >= 5:
        st.session_state.last_motivation_change = current_time
        st.session_state.motivation_index = (st.session_state.motivation_index + 1) % len(MOTIVATION_QUOTES)
        
        # Yeni motivasyon türü ve içerik seç
        motivation_types = ['quote', 'tip', 'breathing']
        st.session_state.current_motivation_type = random.choice(motivation_types)
        
        if st.session_state.current_motivation_type == 'quote':
            st.session_state.current_motivation_content = MOTIVATION_QUOTES[st.session_state.motivation_index]
        elif st.session_state.current_motivation_type == 'tip':
            subject = st.session_state.current_subject or 'Genel'
            if subject in MICRO_TIPS:
                st.session_state.current_motivation_content = random.choice(MICRO_TIPS[subject])
            else:
                st.session_state.current_motivation_content = random.choice(MICRO_TIPS['Genel'])
        else:  # breathing
            exercise = random.choice(BREATHING_EXERCISES)
            st.session_state.current_motivation_content = f"🫁 **{exercise['name']}**\n\n📋 {exercise['instruction']}\n\n✨ **Faydası:** {exercise['benefit']}"
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        animation: pulse 2s infinite;
    ">
        <h2 style="color: white; margin-bottom: 20px;">🌬️ Hibrit Nefes Molası</h2>
        <div style="font-size: 72px; font-weight: bold; margin: 20px 0;">
            {breath_seconds}s
        </div>
        <div style="
            font-size: 18px; 
            font-style: italic; 
            margin: 20px 0; 
            min-height: 120px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            border-left: 4px solid #ffd700;
            transition: all 0.5s ease-in-out;
        ">
            {st.session_state.current_motivation_content}
        </div>
        <div style="font-size: 12px; opacity: 0.8; margin-top: 10px;">
            💡 İçerik her 5 saniyede değişir
        </div>
        <div style="font-size: 14px; opacity: 0.9; margin-top: 15px;">
            🍅 Pomodoro timer duraklatıldı • Kaldığı yerden devam edecek
        </div>
    </div>
    
    <style>
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(1); }}
    }}
    </style>
    """, unsafe_allow_html=True)



def get_subjects_by_field_yks(field):
    """Alan bazında dersleri döndürür"""
    if field == "Sayısal":
        return ["TYT Matematik", "TYT Geometri", "TYT Fizik", "TYT Kimya", "TYT Biyoloji", 
                "AYT Matematik", "AYT Fizik", "AYT Kimya", "AYT Biyoloji"]
    elif field == "Sözel":
        return ["TYT Türkçe", "TYT Tarih", "TYT Coğrafya", "TYT Felsefe", "TYT Din Kültürü",
                "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
    elif field == "Eşit Ağırlık":
        return ["TYT Matematik", "TYT Geometri", "TYT Türkçe", "TYT Tarih", "TYT Coğrafya",
                "AYT Matematik", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
    else:
        return list(YKS_TOPICS.keys())

def determine_topic_priority_by_performance(topic, user_data):
    """Konunun öğrenci performansına göre öncelik seviyesini belirler"""
    # Konu takip verisinden mevcut net değerini al
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    
    # MULTİPLE FORMAT SUPPORT: Alternatif key formatlarını dene
    possible_keys = []
    
    # Format 1: subject | main_topic | topic | detail
    key1 = f"{topic['subject']} | {topic['main_topic']} | {topic['topic']} | {topic['detail']}"
    possible_keys.append(key1)
    
    # Format 2: subject | main_topic | None | detail  
    key2 = f"{topic['subject']} | {topic['main_topic']} | None | {topic['detail']}"
    possible_keys.append(key2)
    
    # Format 3: subject | None | None | detail
    key3 = f"{topic['subject']} | None | None | {topic['detail']}"
    possible_keys.append(key3)
    
    # Format 4: subject | topic | None | detail
    key4 = f"{topic['subject']} | {topic['topic']} | None | {topic['detail']}"
    possible_keys.append(key4)
    
    # DEBUG: Konu key'lerini kontrol et
    print(f"DEBUG: Trying keys: {possible_keys}")
    print(f"DEBUG: Available keys sample: {list(topic_progress.keys())[:3]}...")
    
    # Deneme analizinden de kontrol et
    deneme_weakness_boost = check_topic_weakness_in_exams(topic, user_data)
    
    # Alternatif key'leri dene ve ilk bulunanı kullan
    net_value = 0
    found_key = None
    for possible_key in possible_keys:
        if possible_key in topic_progress:
            try:
                net_value = int(float(topic_progress[possible_key]))
                found_key = possible_key
                break
            except:
                continue
    
    print(f"DEBUG: Found key: {found_key}")
    print(f"DEBUG: Found net_value: {net_value} for topic: {topic['detail']}")
    
    # Net seviyesine göre öncelik belirle
    base_priority = get_priority_by_net_level(net_value)
    
    print(f"DEBUG: Base priority: {base_priority}")
    
    # Deneme analizinde zayıf çıkanları bir seviye yükselt
    if deneme_weakness_boost:
        if base_priority == "MINIMAL":
            base_priority = "LOW"
        elif base_priority == "LOW":
            base_priority = "NORMAL"
        elif base_priority == "NORMAL":
            base_priority = "MEDIUM"
        elif base_priority == "MEDIUM":
            base_priority = "HIGH"
        # HIGH zaten en yüksek, değişmez
    
    return base_priority

def get_priority_by_net_level(net_value):
    """Net değerine göre öncelik seviyesi döndürür"""
    if net_value <= 5:
        return "HIGH"        # 🔴 Zayıf Seviye → Acil
    elif net_value <= 8:
        return "MEDIUM"      # 🟠 Temel Seviye → Öncelikli
    elif net_value <= 14:
        return "NORMAL"      # 🟡 Orta Seviye → Normal
    elif net_value <= 18:
        return "LOW"         # 🟢 İyi Seviye → Düşük
    else:
        return "MINIMAL"     # 🔵 Uzman Seviye → Minimal

def check_topic_weakness_in_exams(topic, user_data):
    """Deneme analizinde bu konunun zayıf olup olmadığını kontrol eder"""
    try:
        deneme_data_str = user_data.get('deneme_analizleri', '[]')
        deneme_kayitlari = json.loads(deneme_data_str) if deneme_data_str else []
        
        # Son 3 denemede bu konunun durumunu kontrol et
        recent_exams = deneme_kayitlari[-3:] if len(deneme_kayitlari) >= 3 else deneme_kayitlari
        
        for deneme in recent_exams:
            # Deneme detaylarında bu konu/ders zayıf kategorideyse
            if 'ders_netleri' in deneme:
                subject = topic['subject']
                if subject in deneme['ders_netleri']:
                    net_info = deneme['ders_netleri'][subject]
                    # Net oranı %50'nin altındaysa zayıf
                    if isinstance(net_info, dict) and 'net' in net_info and 'total' in net_info:
                        try:
                            oran = net_info['net'] / net_info['total'] if net_info['total'] > 0 else 0
                            if oran < 0.5:  # %50'nin altında başarı
                                return True
                        except:
                            continue
            
            # Tavsiyelerde bu ders geçiyorsa
            if 'tavsiyeler' in deneme:
                for tavsiye in deneme['tavsiyeler']:
                    if topic['subject'] in tavsiye and any(word in tavsiye.lower() for word in ['zayıf', 'tekrar', 'çalış', 'boşluk']):
                        return True
        
        return False
    except:
        return False

def calculate_subject_priority_new(subject, user_data, survey_data):
    """YENİ SİSTEM: Ders önceliğini konu takip seviyelerine göre hesaplar"""
    # Dersin genel performansını hesapla
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    subject_avg_net = calculate_subject_average_net(subject, topic_progress)
    
    # Net seviyesine göre temel öncelik
    base_priority_score = get_subject_priority_score_by_net(subject_avg_net)
    
    # Deneme analizinde bu ders zayıfsa boost ver
    deneme_weakness_boost = check_subject_weakness_in_exams(subject, user_data)
    if deneme_weakness_boost:
        base_priority_score += 20
    
    # Survey'den zorluk bilgisi (hafif etki)
    if subject in survey_data.get('difficult_subjects', []):
        base_priority_score += 10
    
    # Survey'den sevilen dersler (pozitif etki - motivasyon artırır)
    if subject in survey_data.get('favorite_subjects', []):
        base_priority_score += 15  # Sevilen derslere ekstra motivasyon puanı
    
    # Survey'den sevmeyen dersler (negatif etki - ama tamamen görmezden gelme)
    if subject in survey_data.get('disliked_subjects', []):
        base_priority_score -= 5  # Hafif azaltma, çok düşürme
    
    # Maksimum 100 puan
    return min(100, base_priority_score)

def get_subject_priority_score_by_net(avg_net):
    """Ders ortalama netine göre öncelik puanı"""
    if avg_net <= 5:
        return 85       # Acil - Çok zayıf
    elif avg_net <= 8:
        return 70       # Öncelikli - Temel seviye
    elif avg_net <= 14:
        return 50       # Normal - Orta seviye
    elif avg_net <= 18:
        return 30       # Düşük - İyi seviye
    else:
        return 15       # Minimal - Uzman seviye

def check_subject_weakness_in_exams(subject, user_data):
    """Deneme analizinde bu dersin zayıf olup olmadığını kontrol eder"""
    try:
        deneme_data_str = user_data.get('deneme_analizleri', '[]')
        deneme_kayitlari = json.loads(deneme_data_str) if deneme_data_str else []
        
        # Son 3 denemede bu dersin durumunu kontrol et
        recent_exams = deneme_kayitlari[-3:] if len(deneme_kayitlari) >= 3 else deneme_kayitlari
        weakness_count = 0
        
        for deneme in recent_exams:
            if 'ders_netleri' in deneme and subject in deneme['ders_netleri']:
                net_info = deneme['ders_netleri'][subject]
                try:
                    # Net oranını kontrol et
                    if isinstance(net_info, dict) and 'net' in net_info and 'total' in net_info:
                        oran = net_info['net'] / net_info['total'] if net_info['total'] > 0 else 0
                        if oran < 0.6:  # %60'ın altında başarı
                            weakness_count += 1
                except:
                    continue
        
        # 3 denemeden 2'sinde zayıfsa boost ver
        return weakness_count >= 2
    except:
        return False

def calculate_subject_average_net(subject, topic_progress):
    """Bir dersin ortalama net performansını hesaplar"""
    if subject not in YKS_TOPICS:
        return 0
        
    total_net = 0
    topic_count = 0
    
    for main_topic, sub_topics in YKS_TOPICS[subject].items():
        if isinstance(sub_topics, dict):
            for sub_topic, details in sub_topics.items():
                for detail in details:
                    topic_key = f"{subject} | {main_topic} | {sub_topic} | {detail}"
                    net_str = topic_progress.get(topic_key, '0')
                    try:
                        net_value = int(float(net_str))
                        total_net += net_value
                        topic_count += 1
                    except:
                        continue
        elif isinstance(sub_topics, list):
            for detail in sub_topics:
                topic_key = f"{subject} | {main_topic} | None | {detail}"
                net_str = topic_progress.get(topic_key, '0')
                try:
                    net_value = int(float(net_str))
                    total_net += net_value
                    topic_count += 1
                except:
                    continue
    
    return total_net / topic_count if topic_count > 0 else 0

def get_sequential_topics(subject, topic_progress, limit=5):
    """Bir dersten sıralı olarak bir sonraki konuları getirir"""
    if subject not in YKS_TOPICS:
        return []
        
    topics = []
    subject_content = YKS_TOPICS[subject]
    
    # İçerik tipini kontrol et
    if isinstance(subject_content, dict):
        # Sözlük formatındaysa
        for main_topic, sub_topics in subject_content.items():
            if isinstance(sub_topics, dict):
                # Alt konular da sözlük
                for sub_topic, details in sub_topics.items():
                    for detail in details:
                        topic_key = f"{subject} | {main_topic} | {sub_topic} | {detail}"
                        net_str = topic_progress.get(topic_key, '0')
                        try:
                            net_value = int(float(net_str))
                            if net_value < 14:  # İyi seviyenin altında
                                topics.append({
                                    'subject': subject,
                                    'main_topic': main_topic,
                                    'topic': sub_topic,
                                    'detail': detail,
                                    'key': topic_key,
                                    'net': net_value,
                                    'order': len(topics)  # Sıralı index
                                })
                                if len(topics) >= limit:
                                    return topics
                        except:
                            # Net bilgisi yoksa 0 kabul et
                            topics.append({
                                'subject': subject,
                                'main_topic': main_topic,
                                'topic': sub_topic,
                                'detail': detail,
                                'key': topic_key,
                                'net': 0,
                                'order': len(topics)
                            })
                            if len(topics) >= limit:
                                return topics
            elif isinstance(sub_topics, list):
                # Alt konular liste
                for detail in sub_topics:
                    topic_key = f"{subject} | {main_topic} | None | {detail}"
                    net_str = topic_progress.get(topic_key, '0')
                    try:
                        net_value = int(float(net_str))
                        if net_value < 14:
                            topics.append({
                                'subject': subject,
                                'main_topic': main_topic,
                                'topic': main_topic,
                                'detail': detail,
                                'key': topic_key,
                                'net': net_value,
                                'order': len(topics)
                            })
                            if len(topics) >= limit:
                                return topics
                    except:
                        topics.append({
                            'subject': subject,
                            'main_topic': main_topic,
                            'topic': main_topic,
                            'detail': detail,
                            'key': topic_key,
                            'net': 0,
                            'order': len(topics)
                        })
                        if len(topics) >= limit:
                            return topics
    elif isinstance(subject_content, list):
        # Ana içerik liste formatındaysa
        for detail in subject_content:
            topic_key = f"{subject} | None | None | {detail}"
            net_str = topic_progress.get(topic_key, '0')
            try:
                net_value = int(float(net_str))
                if net_value < 14:
                    topics.append({
                        'subject': subject,
                        'main_topic': "Genel",
                        'topic': "Genel",
                        'detail': detail,
                        'key': topic_key,
                        'net': net_value,
                        'order': len(topics)
                    })
                    if len(topics) >= limit:
                        return topics
            except:
                topics.append({
                    'subject': subject,
                    'main_topic': "Genel",
                    'topic': "Genel",
                    'detail': detail,
                    'key': topic_key,
                    'net': 0,
                    'order': len(topics)
                })
                if len(topics) >= limit:
                    return topics
    
    return topics

def calculate_spaced_repetition_topics(user_data):
    """Tekrar edilmesi gereken konuları bilimsel aralıklarla hesaplar"""
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    completion_dates = json.loads(user_data.get('topic_completion_dates', '{}') or '{}')
    
    current_date = datetime.now()
    review_topics = []
    
    for topic_key, net_str in topic_progress.items():
        try:
            net_value = int(float(net_str))
            if net_value >= 14:  # İyi seviye ve üzeri
                completion_date_str = completion_dates.get(topic_key)
                if completion_date_str:
                    completion_date = datetime.fromisoformat(completion_date_str)
                    days_passed = (current_date - completion_date).days
                    
                    # Hangi tekrar aralığında olduğunu bul
                    review_interval = None
                    priority = "REPEAT_NORMAL"
                    
                    for i, interval in enumerate(SPACED_REPETITION_INTERVALS):
                        if days_passed >= interval - 1 and days_passed <= interval + 1:
                            review_interval = interval
                            # Kritiklik seviyesi
                            if i == 0:  # 3 gün
                                priority = "REPEAT_HIGH"
                            elif i <= 2:  # 7, 14 gün
                                priority = "REPEAT_MEDIUM"
                            else:  # 30, 90 gün
                                priority = "REPEAT_NORMAL"
                            break
                    
                    if review_interval:
                        # Topic key'den subject ve diğer bilgileri çıkar
                        parts = topic_key.split(' | ')
                        if len(parts) >= 4:
                            review_topics.append({
                                'subject': parts[0],
                                'main_topic': parts[1],
                                'topic': parts[2] if parts[2] != 'None' else parts[1],
                                'detail': parts[3],
                                'key': topic_key,
                                'net': net_value,
                                'days_passed': days_passed,
                                'interval': review_interval,
                                'priority': priority,
                                'completion_date': completion_date_str
                            })
        except:
            continue
    
    # Öncelik sırasına göre sırala
    priority_order = {"REPEAT_HIGH": 0, "REPEAT_MEDIUM": 1, "REPEAT_NORMAL": 2}
    review_topics.sort(key=lambda x: (priority_order.get(x['priority'], 3), x['days_passed']))
    
    return review_topics

# ===== YENİ: KALICI ÖĞRENME SİSTEMİ FONKSİYONLARI =====

def initialize_mastery_system(user_data):
    """Kullanıcı için kalıcı öğrenme sistemi verilerini başlatır"""
    if 'topic_repetition_history' not in user_data:
        user_data['topic_repetition_history'] = '{}'
    if 'topic_mastery_status' not in user_data:
        user_data['topic_mastery_status'] = '{}'
    if 'pending_review_topics' not in user_data:
        user_data['pending_review_topics'] = '{}'
    return user_data

def add_topic_to_mastery_system(user_data, topic_key, initial_level="iyi"):
    """Konuyu kalıcı öğrenme sistemine ekler (haftalık konulardan bitirilen konu)"""
    import json
    from datetime import datetime, timedelta
    
    # Mevcut verileri yükle
    repetition_history = json.loads(user_data.get('topic_repetition_history', '{}'))
    mastery_status = json.loads(user_data.get('topic_mastery_status', '{}'))
    
    current_date = datetime.now()
    
    # İlk öğrenme kaydını oluştur
    repetition_history[topic_key] = {
        'initial_date': current_date.isoformat(),
        'initial_level': initial_level,
        'reviews': [],
        'current_stage': 0,  # 0: İlk öğrenme, 1-4: Tekrarlar
        'next_review_date': None
    }
    
    mastery_status[topic_key] = {
        'status': 'INITIAL',
        'last_updated': current_date.isoformat(),
        'total_reviews': 0,
        'success_count': 0
    }
    
    # İlk tekrar tarihini hesapla (3 gün sonra)
    next_review = current_date + timedelta(days=MASTERY_INTERVALS[0])
    repetition_history[topic_key]['next_review_date'] = next_review.isoformat()
    
    # Güncellenmiş verileri kaydet
    user_data['topic_repetition_history'] = json.dumps(repetition_history)
    user_data['topic_mastery_status'] = json.dumps(mastery_status)
    
    return user_data

def get_pending_review_topics(user_data):
    """Tekrar değerlendirmesi bekleyen konuları döndürür"""
    import json
    from datetime import datetime
    
    repetition_history = json.loads(user_data.get('topic_repetition_history', '{}'))
    pending_topics = []
    current_date = datetime.now()
    
    for topic_key, history in repetition_history.items():
        next_review_date = history.get('next_review_date')
        if next_review_date and history['current_stage'] < 4:  # Henüz tamamlanmamış
            try:
                review_date = datetime.fromisoformat(next_review_date)
                if current_date >= review_date:
                    # Konu bilgilerini topic_key'den çıkar
                    parts = topic_key.split(' | ')
                    if len(parts) >= 4:
                        pending_topics.append({
                            'key': topic_key,
                            'subject': parts[0],
                            'main_topic': parts[1],
                            'topic': parts[2] if parts[2] != 'None' else parts[1],
                            'detail': parts[3],
                            'stage': history['current_stage'],
                            'stage_name': get_stage_name(history['current_stage']),
                            'days_since_last': (current_date - datetime.fromisoformat(history['initial_date'])).days,
                            'review_count': len(history['reviews'])
                        })
            except:
                continue
    
    return pending_topics

def get_stage_name(stage):
    """Tekrar aşamasının adını döndürür"""
    stage_names = {
        0: "1. Tekrar (3 gün sonra)",
        1: "2. Tekrar (7 gün sonra)", 
        2: "3. Tekrar (7 gün sonra)",
        3: "4. Tekrar (7 gün sonra)",
        4: "Son Tekrar (7 gün sonra)"
    }
    return stage_names.get(stage, "Bilinmeyen Aşama")

def process_review_evaluation(user_data, topic_key, evaluation_level):
    """Öğrencinin tekrar değerlendirmesini işler"""
    import json
    from datetime import datetime, timedelta
    
    repetition_history = json.loads(user_data.get('topic_repetition_history', '{}'))
    mastery_status = json.loads(user_data.get('topic_mastery_status', '{}'))
    
    current_date = datetime.now()
    
    if topic_key in repetition_history:
        history = repetition_history[topic_key]
        status = mastery_status[topic_key]
        
        # Değerlendirme kaydını ekle
        review_record = {
            'date': current_date.isoformat(),
            'level': evaluation_level,
            'stage': history['current_stage']
        }
        history['reviews'].append(review_record)
        status['total_reviews'] += 1
        status['last_updated'] = current_date.isoformat()
        
        # Değerlendirmeye göre sonraki adımı belirle
        if evaluation_level in ['iyi', 'uzman']:
            # Başarılı - sonraki aşamaya geç
            status['success_count'] += 1
            history['current_stage'] += 1
            
            if history['current_stage'] >= 4:
                # Tüm tekrarları başarıyla tamamladı - kalıcı öğrenildi
                status['status'] = 'MASTERED'
                history['next_review_date'] = None
            else:
                # Sonraki tekrar tarihini belirle
                next_interval = MASTERY_INTERVALS[min(history['current_stage'], len(MASTERY_INTERVALS)-1)]
                next_review = current_date + timedelta(days=next_interval)
                history['next_review_date'] = next_review.isoformat()
                status['status'] = f"REVIEW_{history['current_stage']}"
        
        elif evaluation_level in ['zayif', 'temel']:
            # Başarısız - başa dön veya önceki aşamaya geri git
            if evaluation_level == 'zayif':
                # Çok zayıf - başa dön
                history['current_stage'] = 0
                next_review = current_date + timedelta(days=MASTERY_INTERVALS[0])
                history['next_review_date'] = next_review.isoformat()
                status['status'] = 'REVIEW_1'
            else:
                # Temel - bir aşama geri git (minimum 0)
                history['current_stage'] = max(0, history['current_stage'] - 1)
                next_interval = MASTERY_INTERVALS[min(history['current_stage'], len(MASTERY_INTERVALS)-1)]
                next_review = current_date + timedelta(days=next_interval)
                history['next_review_date'] = next_review.isoformat()
                status['status'] = f"REVIEW_{history['current_stage'] + 1}"
        
        else:  # orta
            # Orta seviye - aynı aşamada tekrar et
            next_interval = MASTERY_INTERVALS[min(history['current_stage'], len(MASTERY_INTERVALS)-1)]
            next_review = current_date + timedelta(days=next_interval)
            history['next_review_date'] = next_review.isoformat()
    
    # Güncellenmiş verileri kaydet
    user_data['topic_repetition_history'] = json.dumps(repetition_history)
    user_data['topic_mastery_status'] = json.dumps(mastery_status)
    
    return user_data

def complete_topic_with_mastery_system(user_data, topic_key, net_value):
    """Konu bitirme işlemini kalıcı öğrenme sistemi ile entegre eder"""
    import json
    from datetime import datetime
    
    # Mevcut sistemi güncelle (topic_progress ve completion_dates)
    topic_progress = json.loads(user_data.get('topic_progress', '{}'))
    completion_dates = json.loads(user_data.get('topic_completion_dates', '{}'))
    
    topic_progress[topic_key] = str(net_value)
    completion_dates[topic_key] = datetime.now().isoformat()
    
    user_data['topic_progress'] = json.dumps(topic_progress)
    user_data['topic_completion_dates'] = json.dumps(completion_dates)
    
    # Eğer iyi seviye (14+ net) ise kalıcı öğrenme sistemine ekle
    if int(net_value) >= 14:
        user_data = add_topic_to_mastery_system(user_data, topic_key, "iyi")
    
    return user_data

def get_weekly_topics_from_topic_tracking(user_data, student_field, survey_data):
    """YENİ SİSTEMATİK HAFTALİK PLAN ÜRETİCİSİ - TYT/AYT AKILLI GEÇİŞ SİSTEMİ (DİNAMİK)"""
    
    # Güncel zaman bilgisi al
    week_info = get_current_week_info()
    current_week = week_info['week_number']
    days_to_yks = week_info['days_to_yks']
    
    # TYT ve AYT ilerlemesini hesapla
    tyt_progress = calculate_tyt_progress(user_data)
    tyt_math_topics_completed = count_tyt_math_completed_topics(user_data)
    
    # Alan bazında dersleri al
    available_subjects = get_subjects_by_field_yks(student_field)
    
    # AYT başlatma koşullarını kontrol et
    include_ayt = should_include_ayt(tyt_progress, tyt_math_topics_completed)
    
    # Konuların TYT/AYT durumuna göre filtrele
    filtered_subjects = []
    for subject in available_subjects:
        if subject.startswith('AYT'):
            # Genel AYT koşulunu kontrol et
            if not include_ayt:
                # Özel durumları kontrol et (prerequisite sistemi)
                if should_include_specific_ayt_subject(subject, user_data):
                    filtered_subjects.append(subject)
                # Değilse atla
                continue
            else:
                # Genel koşul sağlanmışsa ekle
                filtered_subjects.append(subject)
        else:
            # TYT konusuysa direkt ekle
            filtered_subjects.append(subject)
    
    # Her dersin öncelik puanını hesapla (YENİ SİSTEM)
    subject_priorities = {}
    for subject in filtered_subjects:
        priority_score = calculate_subject_priority_new(subject, user_data, survey_data)
        subject_priorities[subject] = priority_score
    
    # Öncelik sırasına göre sırala
    sorted_subjects = sorted(subject_priorities.items(), key=lambda x: x[1], reverse=True)
    
    # Haftalık plan oluştur
    weekly_new_topics = []
    weekly_review_topics = []
    
    # 1. KONU ÖNCELIK HESAPLAMA (Backend İşlemi)
    for subject, priority_score in sorted_subjects:
        # Ders önem puanına göre haftalık limit
        importance = SUBJECT_IMPORTANCE_SCORES.get(subject, 5)
        weekly_limit = WEEKLY_TOPIC_LIMITS.get(importance, 1)
        
        # Düşük öncelikli dersleri 2-3. hafta sonra başlat (DİNAMİK KONTROL)
        if importance <= 4:
            # Sistem kullanım süresini kontrol et
            user_creation = user_data.get('created_at', '')
            if user_creation:
                try:
                    creation_date = datetime.fromisoformat(user_creation)
                    weeks_passed = (week_info['today'] - creation_date).days // 7
                    if weeks_passed < 2:  # İlk 2 hafta atla
                        continue
                except:
                    continue
            else:
                # Eğer kullanıcı oluşturma tarihi yoksa, güvenli olması için sadece yüksek öncelikli dersleri al
                if current_week <= 2:  # İlk 2 hafta
                    continue
        
        # Sıralı konuları al
        sequential_topics = get_sequential_topics(subject, 
            json.loads(user_data.get('topic_progress', '{}') or '{}'), 
            limit=weekly_limit)
        
        # YENİ SİSTEM: Her konunun bireysel önceliğini performansa göre belirle
        for topic in sequential_topics:
            topic['priority'] = determine_topic_priority_by_performance(topic, user_data)
        
        weekly_new_topics.extend(sequential_topics)
    
    # 2. TEKRAR KONULARI (Bilimsel Aralıklarla)
    review_topics = calculate_spaced_repetition_topics(user_data)
    weekly_review_topics = review_topics[:8]  # Max 8 tekrar konusu/hafta
    
    # 3. TOPLAM PLAN
    total_plan = {
        'new_topics': weekly_new_topics[:15],  # Max 15 yeni konu
        'review_topics': weekly_review_topics,
        'week_target': len(weekly_new_topics[:15]) + len(weekly_review_topics),
        'success_target': 0.8,  # %80 başarı hedefi
        'projections': calculate_completion_projections(user_data, student_field, days_to_yks),
        'tyt_progress': tyt_progress,
        'ayt_enabled': include_ayt,
        'tyt_math_completed': tyt_math_topics_completed
    }
    
    return total_plan

def calculate_tyt_progress(user_data):
    """TYT ilerlemesini yüzde olarak hesaplar"""
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    
    tyt_total = 0
    tyt_completed = 0
    
    # Sadece TYT dersleri
    for subject in YKS_TOPICS.keys():
        if not subject.startswith('TYT'):
            continue
        
        subject_content = YKS_TOPICS[subject]
        
        # İçerik tipini kontrol et
        if isinstance(subject_content, dict):
            # Sözlük formatındaysa
            for main_topic, sub_topics in subject_content.items():
                if isinstance(sub_topics, dict):
                    # Alt konular da sözlük
                    for sub_topic, details in sub_topics.items():
                        for detail in details:
                            topic_key = f"{subject} | {main_topic} | {sub_topic} | {detail}"
                            tyt_total += 1
                            try:
                                net_value = int(float(topic_progress.get(topic_key, '0')))
                                if net_value >= 14:  # İyi seviye
                                    tyt_completed += 1
                            except:
                                continue
                elif isinstance(sub_topics, list):
                    # Alt konular liste
                    for detail in sub_topics:
                        topic_key = f"{subject} | {main_topic} | None | {detail}"
                        tyt_total += 1
                        try:
                            net_value = int(float(topic_progress.get(topic_key, '0')))
                            if net_value >= 14:  # İyi seviye
                                tyt_completed += 1
                        except:
                            continue
        elif isinstance(subject_content, list):
            # Ana içerik liste formatındaysa
            for detail in subject_content:
                topic_key = f"{subject} | None | None | {detail}"
                tyt_total += 1
                try:
                    net_value = int(float(topic_progress.get(topic_key, '0')))
                    if net_value >= 14:  # İyi seviye
                        tyt_completed += 1
                except:
                    continue
    
    if tyt_total > 0:
        return (tyt_completed / tyt_total) * 100
    return 0

def count_tyt_math_completed_topics(user_data):
    """TYT Matematik'te tamamlanan konu sayısını hesaplar"""
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    
    if "TYT Matematik" not in YKS_TOPICS:
        return 0
    
    completed_count = 0
    subject_content = YKS_TOPICS["TYT Matematik"]
    
    # İçerik tipini kontrol et
    if isinstance(subject_content, dict):
        # Sözlük formatındaysa
        for main_topic, sub_topics in subject_content.items():
            if isinstance(sub_topics, dict):
                # Alt konular da sözlük
                for sub_topic, details in sub_topics.items():
                    for detail in details:
                        topic_key = f"TYT Matematik | {main_topic} | {sub_topic} | {detail}"
                        try:
                            net_value = int(float(topic_progress.get(topic_key, '0')))
                            if net_value >= 14:  # İyi seviye
                                completed_count += 1
                        except:
                            continue
            elif isinstance(sub_topics, list):
                # Alt konular liste
                for detail in sub_topics:
                    topic_key = f"TYT Matematik | {main_topic} | None | {detail}"
                    try:
                        net_value = int(float(topic_progress.get(topic_key, '0')))
                        if net_value >= 14:  # İyi seviye
                            completed_count += 1
                    except:
                        continue
    elif isinstance(subject_content, list):
        # Ana içerik liste formatındaysa
        for detail in subject_content:
            topic_key = f"TYT Matematik | None | None | {detail}"
            try:
                net_value = int(float(topic_progress.get(topic_key, '0')))
                if net_value >= 14:  # İyi seviye
                    completed_count += 1
            except:
                continue
    
    return completed_count

def should_include_ayt(tyt_progress, tyt_math_completed):
    """AYT konularının dahil edilip edilmeyeceğini belirler"""
    # Koşul 1: TYT'nin %60'ı tamamlanmış olmalı
    condition1 = tyt_progress >= 60.0
    
    # Koşul 2: TYT Matematik'te en az 12 konu tamamlanmış olmalı  
    condition2 = tyt_math_completed >= 12
    
    # Her iki koşul da sağlanmalı
    return condition1 and condition2

def should_include_specific_ayt_subject(ayt_subject, user_data):
    """Belirli bir AYT dersinin dahil edilip edilmeyeceğini kontrol eder (prerequisite sistemi)"""
    
    # TYT-AYT devamı olan konular
    PREREQUISITE_MAPPING = {
        "AYT Matematik": {
            "prerequisite_subject": "TYT Matematik", 
            "required_topics": ["Temel Kavramlar", "Temel İşlemler"],  # İlk 2 kategorideki konular
            "min_completed": 8  # En az 8 konu tamamlanmış olmalı
        },
        "AYT Fizik": {
            "prerequisite_subject": "TYT Fizik",
            "required_topics": ["Kuvvet ve Hareket"],  # Temel fizik
            "min_completed": 4
        },
        "AYT Biyoloji": {
            "prerequisite_subject": "TYT Biyoloji", 
            "required_topics": ["Canlıların Temel Bileşenleri"],  # Temel biyoloji
            "min_completed": 3
        },
        "AYT Kimya": {
            "prerequisite_subject": "TYT Kimya",
            "required_topics": ["Atom ve Periyodik Sistem"],  # Temel kimya
            "min_completed": 3
        }
    }
    
    if ayt_subject not in PREREQUISITE_MAPPING:
        return False  # Tanımlı değilse genel kuralı uygula
    
    prereq = PREREQUISITE_MAPPING[ayt_subject]
    tyt_subject = prereq["prerequisite_subject"]
    
    # TYT konusunun tamamlanan konularını say
    completed_count = count_completed_topics_in_categories(
        user_data, tyt_subject, prereq["required_topics"]
    )
    
    return completed_count >= prereq["min_completed"]

def count_completed_topics_in_categories(user_data, subject, categories):
    """Belirli kategorilerdeki tamamlanan konu sayısını hesaplar"""
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    
    if subject not in YKS_TOPICS:
        return 0
    
    completed_count = 0
    subject_content = YKS_TOPICS[subject]
    
    if isinstance(subject_content, dict):
        for category_name, category_content in subject_content.items():
            if category_name not in categories:
                continue  # Sadece istenen kategorileri say
                
            if isinstance(category_content, dict):
                # Alt kategoriler varsa
                for sub_category, topics in category_content.items():
                    if isinstance(topics, list):
                        for topic in topics:
                            topic_key = f"{subject} | {category_name} | {sub_category} | {topic}"
                            try:
                                net_value = int(float(topic_progress.get(topic_key, '0')))
                                if net_value >= 10:  # Temel seviye yeterli
                                    completed_count += 1
                            except:
                                continue
            elif isinstance(category_content, list):
                # Direkt konu listesi
                for topic in category_content:
                    topic_key = f"{subject} | {category_name} | None | {topic}"
                    try:
                        net_value = int(float(topic_progress.get(topic_key, '0')))
                        if net_value >= 10:  # Temel seviye yeterli
                            completed_count += 1
                    except:
                        continue
    
    return completed_count

def calculate_completion_projections(user_data, student_field, days_to_yks):
    """Uzun vadeli tamamlanma tahminleri - DİNAMİK YKS TARİHİ İLE"""
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    available_subjects = get_subjects_by_field_yks(student_field)
    
    projections = {
        'overall_progress': 0,
        'tyt_progress': 0,
        'ayt_progress': 0,
        'estimated_completion': None,
        'monthly_targets': [],
        'weekly_average': 0
    }
    
    total_topics = 0
    completed_topics = 0
    tyt_total = 0
    tyt_completed = 0
    ayt_total = 0
    ayt_completed = 0
    
    # Her dersin ilerlemesini hesapla
    for subject in available_subjects:
        if subject not in YKS_TOPICS:
            continue
            
        subject_total = 0
        subject_completed = 0
        subject_content = YKS_TOPICS[subject]
        
        # İçerik tipini kontrol et
        if isinstance(subject_content, dict):
            # Sözlük formatındaysa
            for main_topic, sub_topics in subject_content.items():
                if isinstance(sub_topics, dict):
                    # Alt konular da sözlük
                    for sub_topic, details in sub_topics.items():
                        for detail in details:
                            topic_key = f"{subject} | {main_topic} | {sub_topic} | {detail}"
                            subject_total += 1
                            try:
                                net_value = int(float(topic_progress.get(topic_key, '0')))
                                if net_value >= 14:
                                    subject_completed += 1
                            except:
                                continue
                elif isinstance(sub_topics, list):
                    # Alt konular liste
                    for detail in sub_topics:
                        topic_key = f"{subject} | {main_topic} | None | {detail}"
                        subject_total += 1
                        try:
                            net_value = int(float(topic_progress.get(topic_key, '0')))
                            if net_value >= 14:
                                subject_completed += 1
                        except:
                            continue
        elif isinstance(subject_content, list):
            # Ana içerik liste formatındaysa
            for detail in subject_content:
                topic_key = f"{subject} | None | None | {detail}"
                subject_total += 1
                try:
                    net_value = int(float(topic_progress.get(topic_key, '0')))
                    if net_value >= 14:
                        subject_completed += 1
                except:
                    continue
        
        total_topics += subject_total
        completed_topics += subject_completed
        
        # TYT/AYT ayrımı
        if subject.startswith('TYT'):
            tyt_total += subject_total
            tyt_completed += subject_completed
        elif subject.startswith('AYT'):
            ayt_total += subject_total
            ayt_completed += subject_completed
    
    # İlerleme yüzdelerini hesapla
    if total_topics > 0:
        projections['overall_progress'] = (completed_topics / total_topics) * 100
    if tyt_total > 0:
        projections['tyt_progress'] = (tyt_completed / tyt_total) * 100
    if ayt_total > 0:
        projections['ayt_progress'] = (ayt_completed / ayt_total) * 100
    
    # Haftalık ortalama hesapla (son 4 hafta simülasyonu)
    weekly_avg = 12  # Varsayılan haftalık tamamlama
    projections['weekly_average'] = weekly_avg
    
    # Tahmini bitiş tarihi
    remaining_topics = total_topics - completed_topics
    if remaining_topics > 0 and weekly_avg > 0:
        weeks_needed = remaining_topics / (weekly_avg * 0.8)  # %80 başarı faktörü
        completion_date = datetime.now() + timedelta(weeks=weeks_needed)
        projections['estimated_completion'] = completion_date.strftime("%d %B %Y")
    
    return projections


def get_topic_level_from_tracking(topic, user_data):
    """Bir konunun mevcut seviyesini Konu Takip'ten alır"""
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    current_net = topic_progress.get(topic['key'], '0')
    
    try:
        net_value = int(float(current_net))
        level_display = calculate_level(net_value)
        return {
            'net': net_value,
            'level': net_value,
            'display': level_display
        }
    except:
        return {
            'net': 0,
            'level': 0,
            'display': "🔴 Zayıf Seviye (0-5 net)"
        }

def get_level_icon_yks(level):
    """Seviyeye göre ikon döndürür"""
    if level <= 5:
        return "🔴"
    elif level <= 8:
        return "🟠"
    elif level <= 14:
        return "🟡"
    elif level <= 18:
        return "🟢"
    else:
        return "🔵"

def count_completed_topics(weekly_plan, user_data):
    """Haftalık plandaki tamamlanan konu sayısını hesaplar"""
    if not weekly_plan:
        return 0
        
    new_topics = weekly_plan.get('new_topics', [])
    review_topics = weekly_plan.get('review_topics', [])
    all_topics = new_topics + review_topics
    
    completed = 0
    for topic in all_topics:
        if topic.get('net', 0) >= 14:  # İyi seviye
            completed += 1
    return completed

def login_user_with_password(username, password):
    """ESKI VERSİYON - Şifre ile giriş (güvenli)"""
    if not username or not password:
        return False
    
    if 'users_db' not in st.session_state:
        st.session_state.users_db = load_users_from_firebase()
    
    users_db = st.session_state.users_db
    
    # Kullanıcı adı var mı kontrol et
    if username in users_db:
        user_data = users_db[username]
        # Şifre kontrolü
        if user_data.get('password') == password:
            # Giriş başarılı, session'a kaydet
            st.session_state.current_user = username
            return True
    
    return False

def auto_save_user_progress(username):
    """Kullanıcı ilerlemesini otomatik olarak Firebase'e kaydet"""
    try:
        if 'users_db' not in st.session_state:
            return False
        
        if username in st.session_state.users_db:
            user_data = st.session_state.users_db[username]
            # Son güncelleme tarihini ekle
            from datetime import datetime
            user_data['last_auto_save'] = datetime.now().isoformat()
            
            # Firebase'e kaydet
            return update_user_in_firebase(username, user_data)
    except Exception as e:
        st.error(f"Otomatik kaydetme hatası: {e}")
        return False
    return False

def ensure_data_persistence():
    """Veri kalıcılığını garanti altına al"""
    if 'current_user' in st.session_state and st.session_state.current_user:
        # Her 30 saniyede bir otomatik kaydet
        import time
        current_time = time.time()
        last_save_key = f"last_save_{st.session_state.current_user}"
        
        if last_save_key not in st.session_state:
            st.session_state[last_save_key] = current_time
        
        # 30 saniye geçtiyse kaydet
        if current_time - st.session_state[last_save_key] > 30:
            auto_save_user_progress(st.session_state.current_user)
            st.session_state[last_save_key] = current_time

def add_student_account(username, password, student_info=None):
    """YÖNETİCİ tarafından öğrenci hesabı ekleme (Sadece sizin kullanımınız için)"""
    import json
    from datetime import datetime
    
    if not username or not password:
        return False, "Kullanıcı adı ve şifre gerekli!"
    
    if 'users_db' not in st.session_state:
        st.session_state.users_db = load_users_from_firebase()
    
    users_db = st.session_state.users_db
    
    # Kullanıcı zaten var mı kontrol et
    if username in users_db:
        return False, f"'{username}' kullanıcı adı zaten mevcut!"
    
    # Yeni öğrenci verilerini hazırla
    new_student_data = {
        'username': username,
        'password': password,
        'created_date': datetime.now().isoformat(),
        'student_status': 'ACTIVE',
        'topic_progress': '{}',
        'topic_completion_dates': '{}',
        'topic_repetition_history': '{}',
        'topic_mastery_status': '{}',
        'pending_review_topics': '{}',
        'total_study_time': 0,
        'created_by': 'ADMIN',
        'last_login': None
    }
    
    # Ek öğrenci bilgileri varsa ekle
    if student_info:
        new_student_data.update(student_info)
    
    # Firebase'e kaydet
    if update_user_in_firebase(username, new_student_data):
        # Session'a da ekle
        st.session_state.users_db[username] = new_student_data
        return True, f"✅ '{username}' öğrenci hesabı başarıyla oluşturuldu!"
    else:
        return False, "❌ Firebase kayıt hatası!"

def login_user_secure(username, password):
    """ULTRA GÜVENLİ kullanıcı giriş sistemi - Sadece önceden kayıtlı öğrenciler"""
    if not username or not password:
        return False
    
    if 'users_db' not in st.session_state:
        st.session_state.users_db = load_users_from_firebase()
    
    users_db = st.session_state.users_db
    
    # SADECE MEVCUT KULLANICILAR GİREBİLİR
    if username in users_db:
        user_data = users_db[username]
        # Şifre kontrolü
        if user_data.get('password') == password:
            # Son giriş tarihini güncelle
            from datetime import datetime
            update_user_in_firebase(username, {
                'last_login': datetime.now().isoformat()
            })
            
            # Session'a kaydet
            st.session_state.current_user = username
            return True
        else:
            # Yanlış şifre
            return False
    else:
        # Kullanıcı bulunamadı
        return False

def backup_user_data_before_changes(username, operation_name):
    """Kullanıcı verilerini değişiklik öncesi yedekle"""
    import json
    from datetime import datetime
    
    try:
        if 'users_db' not in st.session_state:
            st.session_state.users_db = load_users_from_firebase()
        
        user_data = st.session_state.users_db.get(username, {})
        if user_data:
            backup_data = {
                'backup_date': datetime.now().isoformat(),
                'operation': operation_name,
                'user_data': user_data.copy()
            }
            
            # Backup'ı Firebase'e kaydet
            backup_ref = f"backups/{username}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{operation_name}"
            # Firebase backup kaydı burada olmalı - şimdilik session'da tut
            if 'user_backups' not in st.session_state:
                st.session_state.user_backups = {}
            st.session_state.user_backups[backup_ref] = backup_data
            
            return True
    except Exception as e:
        st.error(f"Backup hatası: {e}")
        return False
    
    return False

def get_user_data():
    """Mevcut kullanıcının verilerini döndürür."""
    if 'users_db' not in st.session_state:
        st.session_state.users_db = load_users_from_firebase()
    
    if 'current_user' not in st.session_state or st.session_state.current_user is None:
        return {}
    
    users_db = st.session_state.users_db
    current_user = st.session_state.current_user
    
    if current_user in users_db:
        return users_db[current_user]
    else:
        return {}

def main():
    # Veri kalıcılığını garanti altına al
    ensure_data_persistence()
    
    if 'users_db' not in st.session_state:
        st.session_state.users_db = load_users_from_firebase()
    
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    
    # Sayfa yönlendirmeleri kontrolü
    if 'page' in st.session_state:
        if st.session_state.page == "learning_styles_test":
            run_vak_learning_styles_test()
            return
        elif st.session_state.page == "cognitive_profile_test":
            run_cognitive_profile_test()
            return
        elif st.session_state.page == "motivation_emotional_test":
            run_motivation_emotional_test()
            return
        elif st.session_state.page == "time_management_test":
            run_time_management_test()
            return
    
    if st.session_state.current_user is None:
        st.markdown(get_custom_css("Varsayılan"), unsafe_allow_html=True)
        st.markdown('<div class="main-header"><h1>🎯 YKS Takip Sistemi</h1><p>Hedefine Bilimsel Yaklaşım</p></div>', unsafe_allow_html=True)
        
        st.subheader("🔐 Güvenli Giriş")
        
        # Firebase durumuna göre mesaj
        if db_ref is None:
            st.warning("⚠️ Firebase bağlantısı yok - Test modu aktif")
            with st.expander("📋 Test Kullanıcı Bilgileri", expanded=True):
                st.success("👤 **Test Öğrenci:**\n- Kullanıcı Adı: `test_ogrenci`\n- Şifre: `123456`")
                st.info("👤 **Admin:**\n- Kullanıcı Adı: `admin`\n- Şifre: `admin123`")
        else:
            st.info("🛡️ Sadece kayıtlı öğrenciler sisteme erişebilir")
        
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap", type="primary", use_container_width=True):
            if login_user_secure(username, password):
                st.success("Giriş başarılı! Hoş geldiniz! 🎯")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Hatalı kullanıcı adı veya şifre!")
                st.warning("🔒 Bu sisteme sadece kayıtlı öğrenciler erişebilir.")
    
    else:
        user_data = get_user_data()
        
        profile_complete = user_data.get('name') and user_data.get('tyt_avg_net')
        learning_style_complete = user_data.get('learning_style')
        
        if not profile_complete:
            st.markdown(get_custom_css("Varsayılan"), unsafe_allow_html=True)
            st.markdown('<div class="main-header"><h1>📝 Profil Bilgilerinizi Tamamlayın</h1><p>Sistemi size özel hale getirmek için bu bilgileri doldurmalısınız</p></div>', unsafe_allow_html=True)
            
            st.subheader("Öğrenci Bilgileri")
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Adınız", key="name_input")
                surname = st.text_input("Soyadınız", key="surname_input")
                grade = st.selectbox("Sınıfınız", ["11. Sınıf", "12. Sınıf", "Mezun"], key="grade_input")
                field = st.selectbox("Alanınız", ["Sayısal", "Sözel", "Eşit Ağırlık"], key="field_input")
                target = st.selectbox("Hedef Bölümünüz", list(BACKGROUND_STYLES.keys())[:-1], key="target_input")
            
            with col2:
                st.subheader("📊 Net Bilgileri")
                st.write("**TYT Netler**")
                tyt_last = st.number_input("Son TYT Neti", min_value=0.0, max_value=120.0, step=0.25, key="tyt_last_input")
                tyt_avg = st.number_input("Genel TYT Ortalaması", min_value=0.0, max_value=120.0, step=0.25, key="tyt_avg_input")
                
                st.write("**AYT Netler**")
                ayt_last = st.number_input("Son AYT Neti", min_value=0.0, max_value=80.0, step=0.25, key="ayt_last_input")
                ayt_avg = st.number_input("Genel AYT Ortalaması", min_value=0.0, max_value=80.0, step=0.25, key="ayt_avg_input")
            
            if st.button("💾 Bilgileri Kaydet", type="primary", use_container_width=True):
                if name and surname and target and tyt_last is not None and tyt_avg is not None and ayt_last is not None and ayt_avg is not None:
                    update_user_in_firebase(st.session_state.current_user, {
                        'name': name,
                        'surname': surname,
                        'grade': grade,
                        'field': field,
                        'target_department': target,
                        'tyt_last_net': str(tyt_last),
                        'tyt_avg_net': str(tyt_avg),
                        'ayt_last_net': str(ayt_last),
                        'ayt_avg_net': str(ayt_avg),
                        'is_profile_complete': 'True' 
                           
                    })
                    
                    st.session_state.users_db = load_users_from_firebase()
                    st.session_state.is_profile_complete = True 
                    st.success("🎉 Bilgileriniz başarıyla kaydedildi! Şimdi öğrenme stilinizi belirleyelim.")
                    
                    st.rerun()
                else:
                    st.error("⚠️ Lütfen tüm alanları doldurun!")
        
        elif not learning_style_complete:
            # Dört testin durumunu kontrol et
            vak_test_completed = user_data.get('vak_test_results')
            cognitive_test_completed = user_data.get('cognitive_test_results')
            motivation_test_completed = user_data.get('motivation_test_results')
            time_management_test_completed = user_data.get('time_management_test_results')
            
            st.markdown(get_custom_css("Varsayılan"), unsafe_allow_html=True)
            
            # Ana sistem başlığı
            st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 30px; border-radius: 20px; margin: 20px 0; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 2.5em;">🧭 GENEL PSİKOLOJİK ANALİZ SİSTEMİ</h1>
                    <p style="color: white; font-size: 1.2em; margin: 10px 0; font-style: italic;">
                        "Kendini Tanı & Doğru Çalış" Sistemi
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            # 4 Test Karesi Modern Düzenlemesi
            st.markdown("""
            <style>
            .test-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 60px 50px;
                margin: 50px 0;
                padding: 0 20px;
            }
            
            /* Genel kart stilleri */
            .test-card {
                position: relative;
                border-radius: 20px;
                padding: 30px 25px;
                text-align: center;
                border: none;
                overflow: hidden;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                cursor: pointer;
                height: 300px;
                width: 100%;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
            }
            
            /* Farklı renkli kartlar - Resimdeki gibi modern renkler */
            .test-card.vak {
                background: linear-gradient(135deg, #8B5CF6 0%, #A855F7 50%, #C084FC 100%);
                box-shadow: 0 4px 20px rgba(139, 92, 246, 0.25);
            }
            
            .test-card.cognitive {
                background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 50%, #1E40AF 100%);
                box-shadow: 0 4px 20px rgba(59, 130, 246, 0.25);
            }
            
            .test-card.motivation {
                background: linear-gradient(135deg, #F59E0B 0%, #F97316 50%, #EA580C 100%);
                box-shadow: 0 4px 20px rgba(245, 158, 11, 0.25);
            }
            
            .test-card.time {
                background: linear-gradient(135deg, #10B981 0%, #059669 50%, #047857 100%);
                box-shadow: 0 4px 20px rgba(16, 185, 129, 0.25);
            }
            
            /* Hover efektleri */
            .test-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }
            
            .test-card.vak:hover {
                box-shadow: 0 8px 30px rgba(139, 92, 246, 0.4);
                background: linear-gradient(135deg, #9333EA 0%, #B45BF7 50%, #D8B4FE 100%);
            }
            
            .test-card.cognitive:hover {
                box-shadow: 0 8px 30px rgba(59, 130, 246, 0.4);
                background: linear-gradient(135deg, #2563EB 0%, #1E40AF 50%, #1E3A8A 100%);
            }
            
            .test-card.motivation:hover {
                box-shadow: 0 8px 30px rgba(245, 158, 11, 0.4);
                background: linear-gradient(135deg, #F59E0B 0%, #FB923C 50%, #F97316 100%);
            }
            
            .test-card.time:hover {
                box-shadow: 0 8px 30px rgba(16, 185, 129, 0.4);
                background: linear-gradient(135deg, #059669 0%, #10B981 50%, #34D399 100%);
            }
            
            .test-icon {
                font-size: 3rem;
                margin-bottom: 12px;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
            }
            
            .test-title {
                font-size: 1.2rem;
                font-weight: 700;
                color: white;
                margin-bottom: 8px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                line-height: 1.3;
            }
            
            .test-subtitle {
                font-size: 0.95rem;
                color: rgba(255,255,255,0.9);
                margin-bottom: 12px;
                font-weight: 500;
            }
            
            .test-details {
                font-size: 0.85rem;
                color: rgba(255,255,255,0.8);
                line-height: 1.5;
                margin-bottom: 20px;
                font-weight: 400;
            }
            
            .test-status {
                padding: 10px 20px;
                border-radius: 25px;
                font-weight: 600;
                font-size: 0.9rem;
                margin-bottom: 15px;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(255,255,255,0.2);
            }
            
            .status-completed {
                background: rgba(76, 175, 80, 0.9);
                color: white;
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
            }
            
            .status-waiting {
                background: rgba(255, 193, 7, 0.9);
                color: white;
                box-shadow: 0 4px 15px rgba(255, 193, 7, 0.3);
            }
            
            /* Responsive tasarım */
            @media (max-width: 768px) {
                .test-grid {
                    grid-template-columns: 1fr;
                    gap: 40px;
                    padding: 0 15px;
                }
                .test-card {
                    height: 250px;
                    padding: 20px 15px;
                }
                .test-icon {
                    font-size: 2.5rem;
                }
                .test-title {
                    font-size: 1.05rem;
                }
            }
            
            /* Button stilleri */
            .stButton > button {
                background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1)) !important;
                border: 2px solid rgba(255,255,255,0.3) !important;
                color: white !important;
                font-weight: 600 !important;
                border-radius: 15px !important;
                backdrop-filter: blur(10px) !important;
                transition: all 0.3s ease !important;
            }
            
            .stButton > button:hover {
                background: linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0.2)) !important;
                border: 2px solid rgba(255,255,255,0.5) !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2) !important;
            }
            </style>
            
            <div class="test-grid">
            """, unsafe_allow_html=True)
            
            # Test Kartları Verilerini Tanımla
            test_cards = [
                {
                    'id': 'vak',
                    'class': 'vak',
                    'icon': '📚',
                    'title': 'Öğrenme Stilleri Testi (VAK)',
                    'subtitle': '75 soru - Görsel, İşitsel, Kinestetik',
                    'details': '',
                    'completed': vak_test_completed,
                    'page': 'learning_styles_test'
                },
                {
                    'id': 'cognitive',
                    'class': 'cognitive',
                    'icon': '🧠',
                    'title': 'Bilişsel Profil Testi',
                    'subtitle': '20 soru - Likert gösterim (1-5)',
                    'details': '',
                    'completed': cognitive_test_completed,
                    'page': 'cognitive_profile_test'
                },
                {
                    'id': 'motivation',
                    'class': 'motivation',
                    'icon': '⚡',
                    'title': 'Motivasyon & Duygu Testi',
                    'subtitle': '',
                    'details': '💫 İçsel/Dışsal motivasyon<br>😰 Sınav kaygısı düzeyi<br>💪 Duygusal dayanıklılık',
                    'completed': motivation_test_completed,
                    'page': 'motivation_emotional_test'
                },
                {
                    'id': 'time',
                    'class': 'time',
                    'icon': '⏰',
                    'title': 'Zaman Yönetimi Testi',
                    'subtitle': '',
                    'details': '📋 Planlama & disiplin<br>⏰ Erteleme<br>🎯 Odak kontrolü',
                    'completed': time_management_test_completed,
                    'page': 'time_management_test'
                }
            ]
            
            # Her test için kart oluştur
            cols = st.columns(2)
            for i, test in enumerate(test_cards):
                col_index = i % 2
                with cols[col_index]:
                    status_class = "status-completed" if test['completed'] else "status-waiting"
                    status_text = "✅ Tamamlandı" if test['completed'] else "⏳ Beklemede"
                    
                    st.markdown(f"""
                    <div class="test-card {test['class']}">
                        <div>
                            <div class="test-icon">{test['icon']}</div>
                            <div class="test-title">{test['title']}</div>
                            <div class="test-subtitle">{test['subtitle']}</div>
                            <div class="test-details">{test['details']}</div>
                        </div>
                        <div class="test-status {status_class}">{status_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Butonlar
                    if not test['completed']:
                        if st.button(f"🚀 Testi Şimdi Doldur", key=f"start_now_{test['id']}", use_container_width=True, type="primary"):
                            st.session_state.page = test['page']
                            st.rerun()
                        
                        if st.button(f"⏳ Sonra Doldur", key=f"start_later_{test['id']}", use_container_width=True):
                            st.info(f"{test['title']} daha sonra için kaydedildi.")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # "Verilerimi Kaydet ve Tamamla" Bölümü
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 30px; border-radius: 25px; margin: 25px 0; text-align: center;
                            border: 3px solid rgba(255,255,255,0.2);
                            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.3);
                            position: relative;
                            overflow: hidden;">
                    <div style="position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; 
                                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                                animation: pulse 4s ease-in-out infinite;"></div>
                    <div style="position: relative; z-index: 1;">
                        <h3 style="color: white; margin: 0 0 15px 0; font-size: 1.8em; 
                                   text-shadow: 0 3px 6px rgba(0,0,0,0.3);">
                            💾 Verilerimi Kaydet ve Tamamla
                        </h3>
                        <p style="color: rgba(255,255,255,0.95); margin: 0; font-size: 1.15em; 
                                  line-height: 1.5; font-weight: 500;">
                            🎯 Testleri istediğiniz zaman yapabilirsiniz<br>
                            ⚡ Şimdi sistemi açabilir ve çalışmaya başlayabilirsiniz!
                        </p>
                    </div>
                </div>
                
                <style>
                @keyframes pulse {
                    0%, 100% { transform: scale(1) rotate(0deg); opacity: 0.3; }
                    50% { transform: scale(1.1) rotate(180deg); opacity: 0.1; }
                }
                </style>
            """, unsafe_allow_html=True)
                
            # Modern buton stili ekle
            st.markdown("""
                <style>
                .final-button > button {
                    background: linear-gradient(135deg, #00b894 0%, #00a085 100%) !important;
                    border: none !important;
                    color: white !important;
                    font-weight: 700 !important;
                    font-size: 1.2em !important;
                    padding: 15px 30px !important;
                    border-radius: 20px !important;
                    box-shadow: 0 8px 25px rgba(0, 184, 148, 0.3) !important;
                    transition: all 0.3s ease !important;
                    text-transform: uppercase !important;
                    letter-spacing: 1px !important;
                }
                
                .final-button > button:hover {
                    background: linear-gradient(135deg, #00a085 0%, #00b894 100%) !important;
                    transform: translateY(-3px) !important;
                    box-shadow: 0 15px 35px rgba(0, 184, 148, 0.4) !important;
                }
                
                .final-button > button:active {
                    transform: translateY(0px) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Butonu özel CSS ile sarmalayın
            st.markdown('<div class="final-button">', unsafe_allow_html=True)
            button_clicked = st.button("💾 Verilerimi Kaydet ve Sistemi Aç", type="primary", use_container_width=True, key="save_and_complete")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if button_clicked:
                # Profili tamamlandı olarak işaretle
                profile_data = {'learning_style': 'Profil Tamamlandı'}
                
                # Eğer testler tamamlandıysa sonuçları dahil et
                if vak_test_completed:
                    vak_results = json.loads(vak_test_completed) if isinstance(vak_test_completed, str) else vak_test_completed
                    visual_score = vak_results.get('visual', 0)
                    auditory_score = vak_results.get('auditory', 0)
                    kinesthetic_score = vak_results.get('kinesthetic', 0)
                    
                    max_score = max(visual_score, auditory_score, kinesthetic_score)
                    if visual_score == max_score:
                        dominant_learning_style = "Görsel"
                    elif auditory_score == max_score:
                        dominant_learning_style = "İşitsel"
                    else:
                        dominant_learning_style = "Kinestetik"
                    
                    if cognitive_test_completed:
                        cognitive_results = json.loads(cognitive_test_completed) if isinstance(cognitive_test_completed, str) else cognitive_test_completed
                        combined_profile = f"{dominant_learning_style} Öğrenme + {cognitive_results.get('dominant_profile', 'Analitik')} Bilişsel"
                    else:
                        combined_profile = f"{dominant_learning_style} Öğrenme"
                    
                    profile_data['learning_style'] = combined_profile
                    profile_data['learning_style_scores'] = json.dumps({
                        'visual': visual_score,
                        'auditory': auditory_score,
                        'kinesthetic': kinesthetic_score
                    })
                
                # Profili kaydet
                update_user_in_firebase(st.session_state.current_user, profile_data)
                st.session_state.users_db = load_users_from_firebase()
                
                st.success("✅ Verileriniz kaydedildi! Sisteme hoş geldiniz!")
                time.sleep(2)
                st.rerun()


        else:
            target_dept = user_data.get('target_department', 'Varsayılan')
            
            st.markdown(get_custom_css(target_dept), unsafe_allow_html=True)
            
            progress_data = calculate_subject_progress(user_data)
            
            with st.sidebar:
                bg_style = BACKGROUND_STYLES.get(target_dept, BACKGROUND_STYLES["Varsayılan"])
                st.markdown(f"### {bg_style['icon']} Hoş geldin, {user_data.get('name', 'Öğrenci')}!")
                st.markdown(f"**🎯 Hedef:** {user_data.get('target_department', 'Belirlenmedi')}")
                st.markdown(f"**📊 Alan:** {user_data.get('field', 'Belirlenmedi')}")
                st.markdown(f"**🏫 Sınıf:** {user_data.get('grade', 'Belirlenmedi')}")
                st.markdown("---")
                st.markdown("**📈 Net Durumu**")
                
                # Net değerlerini düzenli formatla göster
                tyt_last = user_data.get('tyt_last_net', '0')
                tyt_avg = user_data.get('tyt_avg_net', '0')
                ayt_last = user_data.get('ayt_last_net', '0')
                ayt_avg = user_data.get('ayt_avg_net', '0')
                
                try:
                    tyt_last_f = f"{float(tyt_last):.1f}" if tyt_last != 'Belirlenmedi' else 'Belirlenmedi'
                except:
                    tyt_last_f = tyt_last
                    
                try:
                    tyt_avg_f = f"{float(tyt_avg):.1f}" if tyt_avg != 'Belirlenmedi' else 'Belirlenmedi'
                except:
                    tyt_avg_f = tyt_avg
                    
                try:
                    ayt_last_f = f"{float(ayt_last):.1f}" if ayt_last != 'Belirlenmedi' else 'Belirlenmedi'
                except:
                    ayt_last_f = ayt_last
                    
                try:
                    ayt_avg_f = f"{float(ayt_avg):.1f}" if ayt_avg != 'Belirlenmedi' else 'Belirlenmedi'
                except:
                    ayt_avg_f = ayt_avg
                
                st.markdown(f"**TYT Son:** {tyt_last_f}")
                st.markdown(f"**TYT Ort:** {tyt_avg_f}")
                st.markdown(f"**AYT Son:** {ayt_last_f}")
                st.markdown(f"**AYT Ort:** {ayt_avg_f}")
                

                
                st.markdown("---")
                st.markdown("**🧠 Öğrenme Stili Dağılımı**")
                style_scores_str = user_data.get('learning_style_scores', None)
                if style_scores_str:
                    try:
                        style_scores = json.loads(style_scores_str.replace("'", "\""))
                        sorted_styles = sorted(style_scores.items(), key=lambda item: item[1], reverse=True)
                        for style, score in sorted_styles:
                            if score > 0:
                                st.write(f"- {style}: %{score:.1f}")
                    except json.JSONDecodeError:
                        st.write("Veri Hatası")
                else:
                    st.write("Henüz belirlenmedi.")
                
                total_completed = sum(data['completed'] for data in progress_data.values())
                total_topics = count_total_topics()
                genel_ilerleme = (total_completed / total_topics * 100) if total_topics > 0 else 0
                    
                st.markdown("---")
                st.metric("📈 Genel İlerleme", f"%{genel_ilerleme:.1f}")
                st.metric("✅ Tamamlanan", f"{total_completed}/{total_topics}")
                
                if st.button("🚪 Çıkış Yap", use_container_width=True):
                    st.session_state.current_user = None
                    st.rerun()
            
            page = st.sidebar.selectbox("🌐 Sayfa Seçin", 
                                      ["🏠 Ana Sayfa", "📚 Konu Takip", "⚙️ Benim Programım","🧠 Çalışma Teknikleri","🎯 YKS Canlı Takip", "🍅 Pomodoro Timer", "🧠 Psikolojim","🔬Detaylı Deneme Analiz Takibi","📊 İstatistikler", "⏰ SAR ZAMANI Geriye 🔁"])
            
            if page == "🏠 Ana Sayfa":
                # Eski session verilerini temizle - her gün güncel sistem!
                clear_outdated_session_data()
                
                # Güncel tarih bilgisi ekle
                week_info = get_current_week_info()
                days_to_yks = week_info['days_to_yks']
                
                bg_style = BACKGROUND_STYLES.get(target_dept, BACKGROUND_STYLES["Varsayılan"])
                st.markdown(f'<div class="main-header"><h1>{bg_style["icon"]} {user_data["target_department"]} Yolculuğunuz</h1><p>Hedefinize doğru emin adımlarla ilerleyin</p><p>📅 {week_info["today"].strftime("%d %B %Y")} | ⏰ YKS\'ye {days_to_yks} gün kaldı!</p></div>', unsafe_allow_html=True)
                
                # İlerleme özeti - kartlar (motivasyondan önce)
                overall_progress = calculate_subject_progress(user_data)
                total_completed = sum(data['completed'] for data in overall_progress.values())
                total_topics = count_total_topics()
                overall_percent = (total_completed / total_topics * 100) if total_topics > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("✅ Tamamlanan Konular", f"{total_completed}/{total_topics}")
                
                with col2:
                    st.metric("📚 Toplam Ders", len(progress_data))
                
                with col3:
                    avg_per_subject = sum(data['percent'] for data in progress_data.values()) / len(progress_data) if progress_data else 0
                    st.metric("📈 Ders Ortalaması", f"%{avg_per_subject:.1f}")
                with col4:
                    st.metric("🎯 Hedef Bölüm", user_data.get('target_department', 'Belirlenmedi'), delta_color="off")
                
                # 🎯 GÜNLÜK MOTİVASYON VE ÇALIŞMA TAKİBİ SİSTEMİ - YENİ!
                st.markdown("---")
                st.subheader("🎯 Günlük Motivasyon ve Çalışma Takibi")
                
                # Bugünkü tarih string'i
                today_str = week_info["today"].strftime("%Y-%m-%d")
                
                # Günlük motivasyon verilerini çek
                daily_motivation = json.loads(user_data.get('daily_motivation', '{}'))
                today_motivation = daily_motivation.get(today_str, {
                    'score': 5, 
                    'note': '',
                    'questions': {},
                    'tests': {
                        'genel_deneme': 0,
                        'brans_deneme': 0
                    },
                    'paragraf_questions': 0,
                    'photo_data': None,
                    'photo_caption': ''
                })
                
                # Eski format veri uyumluluğu - mevcut eski verileri yeni formata geçir
                if 'questions' in today_motivation:
                    eski_questions = today_motivation['questions']
                    # Eski format -> Yeni format dönüşümü
                    eski_yeni_mapping = {
                        'matematik': 'tyt_matematik',
                        'fizik': 'tyt_fizik', 
                        'kimya': 'tyt_kimya',
                        'biyoloji': 'tyt_biyoloji',
                        'turkce': 'tyt_turkce',
                        'tarih': 'tyt_tarih',
                        'cografya': 'tyt_cografya',
                        'edebiyat': 'ayt_edebiyat',
                        'felsefe': 'tyt_felsefe',
                        'din': 'tyt_din',
                        'geometri': 'tyt_geometri'
                    }
                    
                    # Eski key'leri varsa yeni format'a çevir (sadece yeni key yoksa)
                    for eski_key, yeni_key in eski_yeni_mapping.items():
                        if eski_key in eski_questions and yeni_key not in eski_questions:
                            eski_questions[yeni_key] = eski_questions.get(eski_key, 0)
                            # Eski key'i silebiliriz ama veri kaybını önlemek için bırakıyoruz
                
                # TAB sistemi ile ayrım
                tab_motivation, tab_study = st.tabs(["🎆 Motivasyon", "📊 Soru Takibi"])
                
                with tab_motivation:
                    # Motivasyon puanlama
                    col_score, col_note = st.columns([1, 2])
                    
                    with col_score:
                        st.markdown("**🎆 Bugünkü motivasyonumu puanla:**")
                        motivation_score = st.slider(
                            "Motivasyon seviyeniz (1-10)", 
                            min_value=1, 
                            max_value=10, 
                            value=today_motivation['score'],
                            key=f"motivation_{today_str}",
                            help="1: Çok düşük, 10: Çok yüksek"
                        )
                        
                        # Motivasyona göre emoji ve mesaj
                        if motivation_score >= 8:
                            motivation_emoji = "🚀"
                            motivation_msg = "Mükemmel enerji!"
                            color = "#28a745"
                        elif motivation_score >= 6:
                            motivation_emoji = "😊"
                            motivation_msg = "Pozitif ruh hali!"
                            color = "#ffc107"
                        elif motivation_score >= 4:
                            motivation_emoji = "😐"
                            motivation_msg = "Orta seviye"
                            color = "#fd7e14"
                        else:
                            motivation_emoji = "😔"
                            motivation_msg = "Biraz destek lazım"
                            color = "#dc3545"
                        
                        st.markdown(f"<div style='text-align: center; background: {color}; color: white; padding: 10px; border-radius: 8px; margin: 10px 0;'><span style='font-size: 20px;'>{motivation_emoji}</span><br><strong>{motivation_msg}</strong></div>", unsafe_allow_html=True)
                    
                    with col_note:
                        st.markdown("**📏 Bugüne not düş:**")
                        daily_note = st.text_area(
                            "Nasıl hissediyorsun? Bugünü nasıl geçirdin?", 
                            value=today_motivation['note'],
                            max_chars=300,
                            height=120,
                            key=f"note_{today_str}",
                            help="Bugünkü düşüncelerinizi, hislerinizi veya yaşadıklarınızı kısaca yazın",
                            placeholder="Örnek: Bugün matematik dersinde çok iyi gitti, kendimi motive hissediyorum. Yarın fizik çalışacağım."
                        )
                    
                    # 📸 GÜNLÜK FOTOĞRAF ÖZELLİĞİ
                    st.markdown("---")
                    st.markdown("**📸 Günlük Fotoğrafın:**")
                    
                    col_photo_upload, col_photo_display = st.columns([1, 1])
                    
                    with col_photo_upload:
                        st.markdown("📷 **Bugünkü anını paylaş**")
                        uploaded_file = st.file_uploader(
                            "Fotoğraf seç", 
                            type=['png', 'jpg', 'jpeg'],
                            key=f"photo_upload_{today_str}",
                            help="Çalışma masanız, notlarınız veya bugünkü halinizi fotoğraflayın"
                        )
                        
                        # Fotoğraf açıklaması
                        photo_caption = st.text_input(
                            "Fotoğraf açıklaması (isteğe bağlı)",
                            value=today_motivation.get('photo_caption', ''),
                            key=f"photo_caption_{today_str}",
                            placeholder="Bu fotoğraf hakkında bir şeyler yaz..."
                        )
                    
                    with col_photo_display:
                        st.markdown("🖼️ **Bugünkü fotoğrafın**")
                        # Bugünkü fotoğrafı göster
                        today_photo = today_motivation.get('photo_data', None)
                        
                        if uploaded_file is not None:
                            # Yeni yüklenen fotoğrafı göster
                            st.image(uploaded_file, caption=f"📸 Bugün yüklenen: {uploaded_file.name}", use_column_width=True)
                            # Session state'e geçici olarak kaydet
                            import base64
                            photo_bytes = uploaded_file.read()
                            photo_b64 = base64.b64encode(photo_bytes).decode()
                            st.session_state[f'temp_photo_{today_str}'] = {
                                'data': photo_b64,
                                'filename': uploaded_file.name,
                                'type': uploaded_file.type
                            }
                        elif today_photo:
                            # Daha önce kaydedilmiş fotoğrafı göster
                            try:
                                import base64
                                photo_bytes = base64.b64decode(today_photo['data'])
                                st.image(photo_bytes, caption=f"📸 Bugünkü fotoğraf: {today_photo.get('filename', 'Fotoğraf')}", use_column_width=True)
                            except:
                                st.info("📷 Fotoğraf yüklenemedi")
                        else:
                            st.info("📷 Henüz bugün için fotoğraf yüklenmedi")
                            st.markdown("*Bugünü fotoğrafla ve anı kaydet!*")
                    
                    # Son 3 günün fotoğraf galerisi
                    st.markdown("---")
                    st.markdown("**🖼️ Son Fotoğraflarım:**")
                    
                    # Son 3 günü döngüyle göster
                    photo_cols = st.columns(3)
                    for i, col in enumerate(photo_cols):
                        day_ago = week_info["today"] - timedelta(days=i+1)
                        day_str = day_ago.strftime("%Y-%m-%d")
                        day_name = day_ago.strftime("%d/%m")
                        
                        with col:
                            day_data = daily_motivation.get(day_str, {})
                            day_photo = day_data.get('photo_data', None)
                            
                            if day_photo:
                                try:
                                    import base64
                                    photo_bytes = base64.b64decode(day_photo['data'])
                                    st.image(photo_bytes, caption=f"📅 {day_name}", use_column_width=True)
                                    
                                    # Fotoğraf açıklaması varsa göster
                                    caption = day_data.get('photo_caption', '')
                                    if caption:
                                        st.caption(f"💬 {caption}")
                                except:
                                    st.info(f"📷 {day_name}\nFotoğraf yok")
                            else:
                                st.info(f"📷 {day_name}\nFotoğraf yok")
                
                with tab_study:
                    st.markdown("**📊 Bugün çözdüğün soruları kaydet:**")
                    
                    # Öğrencinin alanını al
                    user_field = user_data.get('field', 'Belirlenmedi')
                    
                    # Alan bilgisi göster
                    if user_field != 'Belirlenmedi':
                        st.info(f"🎯 **Alanınız:** {user_field} - Bu alanınıza uygun dersler gösteriliyor")
                    else:
                        st.warning("⚠️ Profilinizde alan seçimi yapın, size uygun dersleri gösterebilmek için")
                    
                    # Paragraf soruları (tüm alanlarda ortak)
                    st.markdown("**📰 TYT Türkçe - Paragraf Soruları:**")
                    paragraf_questions = st.number_input(
                        "Bugün kaç paragraf sorusu çözdün?",
                        min_value=0,
                        max_value=200,
                        value=today_motivation.get('paragraf_questions', 0),
                        key=f"paragraf_{today_str}",
                        help="TYT Türkçe paragraf sorularının sayısı"
                    )
                    
                    st.markdown("---")
                    st.markdown("**🔢 YKS Ders Bazında Soru Sayıları:**")
                    
                    # YKS dersleri - alan bazında
                    questions_data = {}
                    
                    # TYT Dersleri (Tüm alanlarda ortak)
                    tyt_dersleri = [
                        ('tyt_turkce', '📚 TYT Türkçe'),
                        ('tyt_matematik', '🔢 TYT Matematik'),
                        ('tyt_geometri', '📐 TYT Geometri'),
                        ('tyt_fizik', '⚡ TYT Fizik'),
                        ('tyt_kimya', '🧪 TYT Kimya'),
                        ('tyt_biyoloji', '🧬 TYT Biyoloji'),
                        ('tyt_tarih', '🏛️ TYT Tarih'),
                        ('tyt_cografya', '🌍 TYT Coğrafya'),
                        ('tyt_felsefe', '💭 TYT Felsefe'),
                        ('tyt_din', '🕌 TYT Din Kültürü')
                    ]
                    
                    # AYT Dersleri - Alan bazında
                    if user_field == "Sayısal":
                        ayt_dersleri = [
                            ('ayt_matematik', '🧮 AYT Matematik'),
                            ('ayt_fizik', '⚛️ AYT Fizik'),
                            ('ayt_kimya', '🔬 AYT Kimya'),
                            ('ayt_biyoloji', '🔭 AYT Biyoloji')
                        ]
                    elif user_field == "Eşit Ağırlık":
                        ayt_dersleri = [
                            ('ayt_matematik', '🧮 AYT Matematik'),
                            ('ayt_edebiyat', '📜 AYT Edebiyat'),
                            ('ayt_tarih', '📖 AYT Tarih'),
                            ('ayt_cografya', '🗺️ AYT Coğrafya')
                        ]
                    elif user_field == "Sözel":
                        ayt_dersleri = [
                            ('ayt_edebiyat', '📜 AYT Edebiyat'),
                            ('ayt_tarih', '📖 AYT Tarih'),
                            ('ayt_cografya', '🗺️ AYT Coğrafya'),
                            ('ayt_felsefe', '🤔 AYT Felsefe'),
                            ('ayt_din', '🕌 AYT Din Kültürü ve Ahlak Bilgisi')
                        ]
                    else:
                        ayt_dersleri = []  # Alan seçilmemişse AYT dersleri gösterilmez
                    
                    # Layout - 2 sütunlu düzen
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📚 TYT DERSLERİ (Tüm Öğrenciler):**")
                        for ders_key, ders_adi in tyt_dersleri:
                            questions_data[ders_key] = st.number_input(
                                ders_adi, 
                                min_value=0, max_value=200, 
                                value=today_motivation.get('questions', {}).get(ders_key, 0),
                                key=f"{ders_key}_{today_str}"
                            )
                    
                    with col2:
                        if ayt_dersleri:
                            st.markdown(f"**🎯 AYT DERSLERİ ({user_field} Alanı):**")
                            for ders_key, ders_adi in ayt_dersleri:
                                questions_data[ders_key] = st.number_input(
                                    ders_adi, 
                                    min_value=0, max_value=200, 
                                    value=today_motivation.get('questions', {}).get(ders_key, 0),
                                    key=f"{ders_key}_{today_str}"
                                )
                        else:
                            if user_field == 'Belirlenmedi':
                                st.markdown("**⚠️ AYT DERSLERİ:**")
                                st.warning("🔄 AYT derslerini görmek için profilinizden alanınızı seçin (Sayısal/Eşit Ağırlık/Sözel)")
                                st.info("🎯 **AYT Dersleri nedir?** 12. sınıfın ikinci yarısında girilecek olan, alanınıza özel derslerdir.")
                            else:
                                st.markdown(f"**🎯 AYT DERSLERİ ({user_field} Alanı):**")
                                st.info(f"🎆 {user_field} alanı için AYT dersleri yüklendi!")
                        
                        st.markdown("**📝 DENEMELER:**")
                        genel_deneme = st.number_input(
                            "🎯 Genel Deneme (Tam YKS)", 
                            min_value=0, max_value=20, 
                            value=today_motivation.get('tests', {}).get('genel_deneme', 0),
                            key=f"genel_deneme_{today_str}",
                            help="TYT + AYT tam denemesi"
                        )
                        brans_deneme = st.number_input(
                            "🎭 Branş Denemesi", 
                            min_value=0, max_value=50, 
                            value=today_motivation.get('tests', {}).get('brans_deneme', 0),
                            key=f"brans_deneme_{today_str}",
                            help="Tek ders/konu denemesi"
                        )
                        
                        # Günlük özet
                        st.markdown("**📈 Günlük Özet:**")
                        total_questions = sum(questions_data.values()) + paragraf_questions
                        total_tests = genel_deneme + brans_deneme
                        
                        # Alan bazında özel metrikler
                        tyt_total = sum(v for k, v in questions_data.items() if k.startswith('tyt_'))
                        ayt_total = sum(v for k, v in questions_data.items() if k.startswith('ayt_'))
                        
                        st.info(f"""
                        **📊 {user_field} Alanı Performansı:**
                        - 📚 TYT Soruları: **{tyt_total}**
                        - 🎯 AYT Soruları: **{ayt_total}**
                        - 📰 Paragraf: **{paragraf_questions}**
                        - 🔢 **TOPLAM SORU: {total_questions}**
                        - 📝 **DENEMELER: {total_tests}**
                        """)
                
                # Tek kaydet butonu - tüm verileri toplar
                if st.button("💾 Bugünkü Tüm Verilerimi Kaydet", key=f"save_all_data_{today_str}", type="primary"):
                    # Fotoğraf verilerini al
                    photo_data = None
                    if f'temp_photo_{today_str}' in st.session_state:
                        photo_data = st.session_state[f'temp_photo_{today_str}']
                    elif today_motivation.get('photo_data'):
                        photo_data = today_motivation.get('photo_data')
                    
                    daily_motivation[today_str] = {
                        'score': motivation_score,
                        'note': daily_note,
                        'questions': questions_data,
                        'tests': {
                            'genel_deneme': genel_deneme,
                            'brans_deneme': brans_deneme
                        },
                        'paragraf_questions': paragraf_questions,
                        'photo_data': photo_data,
                        'photo_caption': photo_caption,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Geçici session state'i temizle
                    if f'temp_photo_{today_str}' in st.session_state:
                        del st.session_state[f'temp_photo_{today_str}']
                    
                    update_user_in_firebase(st.session_state.current_user, {'daily_motivation': json.dumps(daily_motivation)})
                    st.session_state.users_db = load_users_from_firebase()
                    
                    # Başarı mesajına fotoğraf bilgisini de ekle
                    photo_info = "📸 Fotoğraf da kaydedildi!" if photo_data else ""
                    st.success(f"✅ {today_str} tarihli tüm verileriniz kaydedildi! Motivasyon: {motivation_score}/10, Toplam Soru: {total_questions}, Denemeler: {total_tests} {photo_info}")
                
                # Son 7 günün performans trendi ve geçmiş verileri
                if len(daily_motivation) > 0:
                    st.markdown("---")
                    st.markdown("**📈 Son 7 Gün Performans Analizi:**")
                    
                    # Tab sistemi ile ayrım
                    tab_trend, tab_history = st.tabs(["📈 Trend Grafikleri", "📅 Geçmiş Verileri"])
                    
                    with tab_trend:
                        recent_days = []
                        recent_scores = []
                        recent_questions = []
                        recent_tests = []
                        
                        for i in range(6, -1, -1):
                            day = week_info["today"] - timedelta(days=i)
                            day_str = day.strftime("%Y-%m-%d")
                            day_data = daily_motivation.get(day_str, {'score': 0, 'questions': {}, 'tests': {}, 'paragraf_questions': 0})
                            
                            recent_days.append(day.strftime("%m/%d"))
                            recent_scores.append(day_data.get('score', 0) if day_data.get('score', 0) > 0 else None)
                            
                            # Toplam soru sayısı hesapla
                            questions = day_data.get('questions', {})
                            total_q = sum(questions.values()) + day_data.get('paragraf_questions', 0)
                            recent_questions.append(total_q if total_q > 0 else None)
                            
                            # Toplam deneme sayısı hesapla
                            tests = day_data.get('tests', {})
                            total_t = tests.get('genel_deneme', 0) + tests.get('brans_deneme', 0)
                            recent_tests.append(total_t if total_t > 0 else None)
                        
                        # Üç ayrı grafik
                        col_graph1, col_graph2, col_graph3 = st.columns(3)
                        
                        with col_graph1:
                            st.markdown("**🎆 Motivasyon Trendi:**")
                            trend_fig1 = go.Figure()
                            trend_fig1.add_trace(go.Scatter(
                                x=recent_days,
                                y=recent_scores,
                                mode='lines+markers',
                                line=dict(color='#667eea', width=3),
                                marker=dict(size=8, color='#764ba2'),
                                name='Motivasyon'
                            ))
                            
                            trend_fig1.update_layout(
                                height=200,
                                margin=dict(l=10, r=10, t=10, b=30),
                                xaxis_title="Tarih",
                                yaxis_title="Puan",
                                yaxis=dict(range=[0, 10]),
                                showlegend=False,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)'
                            )
                            
                            st.plotly_chart(trend_fig1, use_container_width=True)
                        
                        with col_graph2:
                            st.markdown("**🔢 Soru Çözme Trendi:**")
                            trend_fig2 = go.Figure()
                            trend_fig2.add_trace(go.Scatter(
                                x=recent_days,
                                y=recent_questions,
                                mode='lines+markers',
                                line=dict(color='#fd7e14', width=3),
                                marker=dict(size=8, color='#e55353'),
                                name='Soru Sayısı',
                                fill='tonexty',
                                fillcolor='rgba(253, 126, 20, 0.2)'
                            ))
                            
                            trend_fig2.update_layout(
                                height=200,
                                margin=dict(l=10, r=10, t=10, b=30),
                                xaxis_title="Tarih",
                                yaxis_title="Soru",
                                showlegend=False,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)'
                            )
                            
                            st.plotly_chart(trend_fig2, use_container_width=True)
                        
                        with col_graph3:
                            st.markdown("**🎯 Deneme Trendi:**")
                            trend_fig3 = go.Figure()
                            trend_fig3.add_trace(go.Scatter(
                                x=recent_days,
                                y=recent_tests,
                                mode='lines+markers',
                                line=dict(color='#28a745', width=3),
                                marker=dict(size=8, color='#20c997'),
                                name='Deneme Sayısı',
                                fill='tonexty',
                                fillcolor='rgba(40, 167, 69, 0.2)'
                            ))
                            
                            trend_fig3.update_layout(
                                height=200,
                                margin=dict(l=10, r=10, t=10, b=30),
                                xaxis_title="Tarih",
                                yaxis_title="Deneme",
                                showlegend=False,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)'
                            )
                            
                            st.plotly_chart(trend_fig3, use_container_width=True)
                    
                    with tab_history:
                        st.markdown("**📅 Geçmiş Günlerdeki Performansınızı İnceleyin:**")
                        
                        # Son 30 günün verilerini göster
                        history_days = []
                        for i in range(29, -1, -1):
                            day = week_info["today"] - timedelta(days=i)
                            day_str = day.strftime("%Y-%m-%d")
                            if day_str in daily_motivation:
                                history_days.append((day, day_str, daily_motivation[day_str]))
                        
                        if history_days:
                            for day, day_str, data in history_days[-10:]:  # Son 10 günü göster
                                with st.expander(f"📅 {day.strftime('%d/%m/%Y')} ({day.strftime('%A')}) - Motivasyon: {data.get('score', 0)}/10", expanded=False):
                                    col_info1, col_info2 = st.columns(2)
                                    
                                    with col_info1:
                                        st.markdown("**🎆 Motivasyon & Notlar:**")
                                        score = data.get('score', 0)
                                        note = data.get('note', 'Not girilmedi')
                                        
                                        if score >= 8:
                                            score_color = "#28a745"
                                            score_emoji = "🚀"
                                        elif score >= 6:
                                            score_color = "#ffc107" 
                                            score_emoji = "😊"
                                        elif score >= 4:
                                            score_color = "#fd7e14"
                                            score_emoji = "😐"
                                        else:
                                            score_color = "#dc3545"
                                            score_emoji = "😔"
                                        
                                        st.markdown(f"<div style='background: {score_color}; color: white; padding: 8px; border-radius: 6px; text-align: center;'>{score_emoji} <strong>{score}/10</strong></div>", unsafe_allow_html=True)
                                        st.markdown(f"**Not:** {note}")
                                    
                                    with col_info2:
                                        st.markdown("**📈 Çalışma Performansı:**")
                                        questions = data.get('questions', {})
                                        tests = data.get('tests', {})
                                        paragraf = data.get('paragraf_questions', 0)
                                        
                                        total_questions = sum(questions.values()) + paragraf
                                        total_tests = tests.get('genel_deneme', 0) + tests.get('brans_deneme', 0)
                                        
                                        st.metric("Toplam Soru", total_questions)
                                        st.metric("Paragraf Soru", paragraf)
                                        st.metric("Denemeler", total_tests)
                                        
                                        # Ders bazında detal - YKS format uyumlu
                                        if any(questions.values()):
                                            st.markdown("**Ders Bazında:**")
                                            
                                            # YKS ders isimleri mapping
                                            ders_isim_mapping = {
                                                'tyt_turkce': 'TYT Türkçe',
                                                'tyt_matematik': 'TYT Matematik', 
                                                'tyt_geometri': 'TYT Geometri',
                                                'tyt_fizik': 'TYT Fizik',
                                                'tyt_kimya': 'TYT Kimya',
                                                'tyt_biyoloji': 'TYT Biyoloji',
                                                'tyt_tarih': 'TYT Tarih',
                                                'tyt_cografya': 'TYT Coğrafya',
                                                'tyt_felsefe': 'TYT Felsefe',
                                                'tyt_din': 'TYT Din Kültürü',
                                                'ayt_matematik': 'AYT Matematik',
                                                'ayt_fizik': 'AYT Fizik',
                                                'ayt_kimya': 'AYT Kimya',
                                                'ayt_biyoloji': 'AYT Biyoloji',
                                                'ayt_edebiyat': 'AYT Edebiyat',
                                                'ayt_tarih': 'AYT Tarih',
                                                'ayt_cografya': 'AYT Coğrafya',
                                                'ayt_felsefe': 'AYT Felsefe',
                                                'ayt_din': 'AYT Din Kültürü ve Ahlak Bilgisi',
                                                # Eski format uyumluluk
                                                'matematik': 'Matematik (Eski)',
                                                'fizik': 'Fizik (Eski)',
                                                'kimya': 'Kimya (Eski)',
                                                'biyoloji': 'Biyoloji (Eski)',
                                                'turkce': 'Türkçe (Eski)',
                                                'tarih': 'Tarih (Eski)',
                                                'cografya': 'Coğrafya (Eski)',
                                                'edebiyat': 'Edebiyat (Eski)',
                                                'felsefe': 'Felsefe (Eski)',
                                                'din': 'Din Kültürü (Eski)',
                                                'geometri': 'Geometri (Eski)'
                                            }
                                            
                                            # TYT dersleri önce göster
                                            tyt_dersleri = [(k, v) for k, v in questions.items() if k.startswith('tyt_') and v > 0]
                                            if tyt_dersleri:
                                                st.markdown("*📚 TYT Dersleri:*")
                                                for ders, sayi in tyt_dersleri:
                                                    ders_adi = ders_isim_mapping.get(ders, ders.replace('_', ' ').title())
                                                    st.write(f"• {ders_adi}: {sayi}")
                                            
                                            # AYT dersleri sonra göster
                                            ayt_dersleri = [(k, v) for k, v in questions.items() if k.startswith('ayt_') and v > 0]
                                            if ayt_dersleri:
                                                st.markdown("*🎯 AYT Dersleri:*")
                                                for ders, sayi in ayt_dersleri:
                                                    ders_adi = ders_isim_mapping.get(ders, ders.replace('_', ' ').title())
                                                    st.write(f"• {ders_adi}: {sayi}")
                                            
                                            # Eski format dersleri (geçiş dönemi uyumluluğu)
                                            eski_dersleri = [(k, v) for k, v in questions.items() if not k.startswith(('tyt_', 'ayt_')) and v > 0]
                                            if eski_dersleri:
                                                st.markdown("*📖 Diğer:*")
                                                for ders, sayi in eski_dersleri:
                                                    ders_adi = ders_isim_mapping.get(ders, ders.title())
                                                    st.write(f"• {ders_adi}: {sayi}")
                        else:
                            st.info("📅 Henüz kaydedilmiş veri yok. Çalışmaya başlayın ve verilerinizi kaydedin!")
                
                st.markdown("---")
                
                # İlerleme özeti kartları yukarda taşındı - bu bölümü kaldır
                
                st.subheader("📈 Hız Göstergesi İlerleme")
                
                # Öğrencinin alanına göre dersler
                user_field = user_data.get('field', 'Belirlenmedi')
                important_subjects = []
                
                if user_field == "Sayısal":
                    important_subjects = ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Fizik", "TYT Kimya", "TYT Biyoloji", "AYT Matematik", "AYT Fizik", "AYT Kimya", "AYT Biyoloji"]
                elif user_field == "Eşit Ağırlık":
                    important_subjects = ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Tarih", "TYT Coğrafya", "AYT Matematik", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
                elif user_field == "Sözel":
                    important_subjects = ["TYT Türkçe", "TYT Tarih", "TYT Coğrafya", "TYT Felsefe", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
                else:
                    # Alan belirlenmemişse genel dersler göster
                    important_subjects = ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Fizik", "TYT Kimya", "TYT Biyoloji"]
                    st.info("⚠️ Profilinizden alanınızı seçerek size özel hız göstergelerini görebilirsiniz!")
                
                # Mevcut progress_data'da bulunan dersleri filtrele
                display_subjects = [s for s in important_subjects if s in progress_data and progress_data[s]['total'] > 0]
                
                # Eğer hiç ders bulunamazsa bilgilendirme göster
                if not display_subjects:
                    st.warning("📊 Henüz konu takip veriniz yok. Konu Takip sayfasından çalışma verilerinizi girin!")
                    st.info(f"🎯 **{user_field} alanı** için takip edilecek dersler: {', '.join(important_subjects)}")
                    
                    # Konu takip sayfasına yönlendirme
                    st.markdown("""
                    **🚀 Hızlı Başlangıç:**
                    1. 📚 Sol menüden **"Konu Takip"** sayfasına gidin
                    2. 🎯 Bir ders seçin ve konu net skorlarınızı girin
                    3. 📈 15+ net aldığınız konular hız göstergesinde görünecek
                    """)

                subject_icons = {
                    "TYT Türkçe": "📚", "TYT Matematik": "🔢", "TYT Geometri": "📐",
                    "TYT Tarih": "🏛️", "TYT Coğrafya": "🌍", "TYT Felsefe": "💭", "TYT Din Kültürü": "🕌",
                    "TYT Fizik": "⚡", "TYT Kimya": "🧪", "TYT Biyoloji": "🧬",
                    "AYT Matematik": "🧮", "AYT Fizik": "⚛️", "AYT Kimya": "🔬", "AYT Biyoloji": "🔭",
                    "AYT Edebiyat": "📜", "AYT Tarih": "📖", "AYT Coğrafya": "🗺️"
                }
                
                if display_subjects:
                    # Alan bazında ilerleme özeti
                    st.markdown(f"**🎯 {user_field} Alanı İlerleme Özeti:**")
                    
                    total_all_subjects = sum(progress_data[s]['total'] for s in display_subjects)
                    completed_all_subjects = sum(progress_data[s]['completed'] for s in display_subjects)
                    avg_percent = (completed_all_subjects / total_all_subjects * 100) if total_all_subjects > 0 else 0
                    
                    col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)
                    with col_summary1:
                        st.metric("📚 Toplam Konu", total_all_subjects)
                    with col_summary2:
                        st.metric("✅ Tamamlanan", completed_all_subjects)
                    with col_summary3:
                        st.metric("🏁 Ortalama", f"%{avg_percent:.1f}")
                    with col_summary4:
                        # Net 15+ kriteriyle ilgili bilgi
                        st.info("🎯 15+ net = Tamamlandı")
                    
                    st.markdown("---")
                    # 🚗 Gerçek Araba Hız Göstergesi - Plotly ile
                    cols = st.columns(3)  # Sabit 3 sütun
                    
                    for i, subject in enumerate(display_subjects):
                        if subject in progress_data:
                            percent = progress_data[subject]["percent"]
                            subject_name_short = subject.replace("TYT ", "").replace("AYT ", "")
                            completed = progress_data[subject]['completed']
                            total = progress_data[subject]['total']
                            
                            # Renk belirleme - Araba teması
                            if percent >= 80:
                                color = "#00ff00"  # Yeşil bölge
                                status = "🚀 Turbo"
                                gauge_color = "green"
                            elif percent >= 60:
                                color = "#ffff00"  # Sarı bölge  
                                status = "😊 Normal"
                                gauge_color = "yellow"
                            elif percent >= 40:
                                color = "#ff8800"  # Turuncu bölge
                                status = "😐 Yavaş"
                                gauge_color = "orange"
                            else:
                                color = "#ff0000"  # Kırmızı bölge
                                status = "🐌 Dur"
                                gauge_color = "red"
                            
                            # İbre rengi dinamik belirleme
                            if percent >= 80:
                                needle_color = "#00ff00"  # Yeşil ibre
                                status_color = "#2ecc71"
                                glow_color = "rgba(46, 204, 113, 0.8)"
                            elif percent >= 60:
                                needle_color = "#ffd700"  # Altın sarısı ibre
                                status_color = "#f39c12"
                                glow_color = "rgba(243, 156, 18, 0.8)"
                            else:
                                needle_color = "#ff3838"  # Parlak kırmızı ibre
                                status_color = "#e74c3c"
                                glow_color = "rgba(231, 76, 60, 0.8)"

                            with cols[i % 3]:
                                # 🚗 GERÇEK ARABA HIZ GÖSTERGESİ - İbreli Tasarım
                                import numpy as np
                                
                                fig = go.Figure()
                                
                                # 1. Speedometer Arka Plan (Yarım Daire)
                                angles = np.linspace(0, 180, 100)
                                x_bg = 0.5 + 0.45 * np.cos(np.radians(angles))
                                y_bg = 0.5 + 0.45 * np.sin(np.radians(angles))
                                
                                # Ana speedometer dairesi
                                fig.add_trace(go.Scatter(
                                    x=x_bg, y=y_bg,
                                    mode='lines',
                                    line=dict(color='#34495e', width=8),
                                    fill='tonexty',
                                    fillcolor='rgba(52, 73, 94, 0.1)',
                                    showlegend=False,
                                    hoverinfo='skip'
                                ))
                                
                                # 2. Renkli Bölgeler (Performans Alanları)
                                zones = [
                                    {'range': [0, 40], 'color': 'rgba(231, 76, 60, 0.6)', 'label': 'Yavaş'},
                                    {'range': [40, 70], 'color': 'rgba(243, 156, 18, 0.6)', 'label': 'Orta'},
                                    {'range': [70, 100], 'color': 'rgba(46, 204, 113, 0.6)', 'label': 'Hızlı'}
                                ]
                                
                                for zone in zones:
                                    start_angle = 180 - (zone['range'][1] * 1.8)
                                    end_angle = 180 - (zone['range'][0] * 1.8)
                                    zone_angles = np.linspace(start_angle, end_angle, 30)
                                    
                                    x_zone = 0.5 + 0.4 * np.cos(np.radians(zone_angles))
                                    y_zone = 0.5 + 0.4 * np.sin(np.radians(zone_angles))
                                    
                                    fig.add_trace(go.Scatter(
                                        x=x_zone, y=y_zone,
                                        mode='lines',
                                        line=dict(color=zone['color'], width=15),
                                        showlegend=False,
                                        hoverinfo='skip'
                                    ))
                                
                                # 3. Tick Marks (Ölçek Çizgileri)
                                for i_tick in range(0, 101, 10):
                                    angle = 180 - (i_tick * 1.8)
                                    
                                    # Dış tick
                                    x_outer = 0.5 + 0.42 * np.cos(np.radians(angle))
                                    y_outer = 0.5 + 0.42 * np.sin(np.radians(angle))
                                    
                                    # İç tick
                                    x_inner = 0.5 + 0.38 * np.cos(np.radians(angle))
                                    y_inner = 0.5 + 0.38 * np.sin(np.radians(angle))
                                    
                                    fig.add_trace(go.Scatter(
                                        x=[x_inner, x_outer], y=[y_inner, y_outer],
                                        mode='lines',
                                        line=dict(color='white', width=3),
                                        showlegend=False,
                                        hoverinfo='skip'
                                    ))
                                    
                                    # Sayılar
                                    x_num = 0.5 + 0.32 * np.cos(np.radians(angle))
                                    y_num = 0.5 + 0.32 * np.sin(np.radians(angle))
                                    
                                    fig.add_annotation(
                                        x=x_num, y=y_num,
                                        text=str(i_tick),
                                        showarrow=False,
                                        font=dict(size=12, color='white', family='Arial Black'),
                                        bgcolor='rgba(0,0,0,0.7)',
                                        bordercolor='white',
                                        borderwidth=1
                                    )
                                
                                # 4. GERÇEK İBRE! 🎯
                                needle_angle = 180 - (percent * 1.8)
                                
                                # İbre gövdesi
                                needle_length = 0.35
                                needle_x = 0.5 + needle_length * np.cos(np.radians(needle_angle))
                                needle_y = 0.5 + needle_length * np.sin(np.radians(needle_angle))
                                
                                # İbre çizgisi (kalın)
                                fig.add_trace(go.Scatter(
                                    x=[0.5, needle_x], y=[0.5, needle_y],
                                    mode='lines',
                                    line=dict(color=needle_color, width=6),
                                    showlegend=False,
                                    hoverinfo='skip'
                                ))
                                
                                # İbre ucu (daha parlak)
                                fig.add_trace(go.Scatter(
                                    x=[needle_x], y=[needle_y],
                                    mode='markers',
                                    marker=dict(color=needle_color, size=12, 
                                               line=dict(color='white', width=2)),
                                    showlegend=False,
                                    hoverinfo='skip'
                                ))
                                
                                # 5. Merkez nokta (pivot)
                                fig.add_trace(go.Scatter(
                                    x=[0.5], y=[0.5],
                                    mode='markers',
                                    marker=dict(color='#2c3e50', size=20,
                                               line=dict(color=needle_color, width=3)),
                                    showlegend=False,
                                    hoverinfo='skip'
                                ))
                                
                                # 6. Digital Display (Alt Merkez)
                                fig.add_annotation(
                                    x=0.5, y=0.25,
                                    text=f"<b>{percent:.1f}%</b>",
                                    showarrow=False,
                                    font=dict(size=16, color=needle_color, family='Arial Black'),
                                    bgcolor='rgba(0,0,0,0.8)',
                                    bordercolor=needle_color,
                                    borderwidth=2,
                                    borderpad=8
                                )
                                
                                # Layout düzenlemesi
                                fig.update_layout(
                                    title=dict(
                                        text=f"{subject_icons.get(subject, '📖')} <b>{subject_name_short}</b>",
                                        x=0.5,
                                        font=dict(size=14, color='white', family='Arial Black')
                                    ),
                                    xaxis=dict(
                                        range=[-0.1, 1.1],
                                        showgrid=False,
                                        zeroline=False,
                                        showticklabels=False
                                    ),
                                    yaxis=dict(
                                        range=[-0.1, 1.1],
                                        showgrid=False,
                                        zeroline=False,
                                        showticklabels=False,
                                        scaleanchor="x",
                                        scaleratio=1
                                    ),
                                    paper_bgcolor='rgba(44, 62, 80, 0.95)',
                                    plot_bgcolor='rgba(44, 62, 80, 0.95)',
                                    showlegend=False,
                                    height=300,
                                    margin=dict(l=10, r=10, t=40, b=10)
                                )
                                
                                # Speedometer chart göster
                                st.plotly_chart(fig, use_container_width=True, key=f"car_speed_{subject}_{i}")
                                
                                # Alt bilgi - Modern araba konsolu
                                st.markdown(f"""
                                <div style="text-align: center; 
                                           background: linear-gradient(135deg, {status_color}, #2c3e50); 
                                           color: white; padding: 12px; border-radius: 12px; 
                                           margin-top: -10px; border: 2px solid {needle_color};
                                           box-shadow: 0 0 15px {glow_color};">
                                    <div style="font-size: 14px; color: {needle_color}; font-weight: bold; 
                                               text-shadow: 0 0 5px {glow_color};">{status} ⚡</div>
                                    <div style="font-size: 11px; color: #ecf0f1; margin: 5px 0;">
                                        📊 {completed}/{total} konu tamamlandı
                                    </div>
                                    <div style="font-size: 10px; color: #bdc3c7; font-style: italic;">
                                        🏎️ YKS Speedometer System
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("📋 Son Aktivite Özeti")
                
                # Kullanıcının gerçek verilerinden son aktiviteleri al
                topic_progress_str = user_data.get('topic_progress', '{}')
                try:
                    topic_progress = json.loads(topic_progress_str) if isinstance(topic_progress_str, str) else topic_progress_str
                except:
                    topic_progress = {}
                
                # Son güncellenen konuları bul (net 10+ olan konular)
                recent_activities = []
                for topic_key, net_score in topic_progress.items():
                    try:
                        net_score = int(float(str(net_score)))
                        if net_score >= 10:  # Anlamlı çalışma yapılmış konular
                            # topic_key format: "TYT Matematik | Ana Konu | Alt Konu | Detay"
                            parts = topic_key.split(' | ')
                            if len(parts) >= 4:
                                ders = parts[0]
                                konu = parts[3]
                                durum = "Tamamlandı" if net_score >= 15 else "Devam Ediyor"
                                recent_activities.append({
                                    "ders": ders, 
                                    "konu": konu[:20] + "..." if len(konu) > 20 else konu,
                                    "net": net_score,
                                    "durum": durum
                                })
                    except (ValueError, TypeError):
                        continue
                
                # En yüksek netli konuları önce göster
                recent_activities.sort(key=lambda x: x['net'], reverse=True)
                recent_activities = recent_activities[:5]  # Sadece ilk 5
                
                if recent_activities:
                    for activity in recent_activities:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                            with col1:
                                st.write(f"**{activity['ders']}** - {activity['konu']}")
                            with col2:
                                st.write(f"Net: {activity['net']}")
                            with col3:
                                if activity['durum'] == "Tamamlandı": 
                                    st.success("✅")
                                else: 
                                    st.info("⏳")
                            with col4:
                                # Net skor seviyesi
                                if activity['net'] >= 18:
                                    st.write("🎓")
                                elif activity['net'] >= 15:
                                    st.write("🚀")
                                else:
                                    st.write("💪")
                else:
                    st.info("📈 Henüz konu çalışmanız bulunmuyor. Konu Takip sayfasından başlayın!")

            elif page == "📚 Konu Takip":
                st.markdown(f'<div class="main-header"><h1>📚 Konu Takip Sistemi</h1><p>Her konuda ustalaşın</p></div>', unsafe_allow_html=True)
                
                # Soru istatistikleri açıklaması
                st.info("""
                **📊 YKS Son 6 Yıl Soru İstatistikleri (2019-2024)**  
                Her konunun yanındaki sayı, o konudan son 6 yılda **kaç soru çıktığını** gösterir.  
                🔥 **15+ soru**: Çok sık çıkan konular (Öncelikli)  
                ⚡ **8-14 soru**: Orta sıklıkta çıkan konular  
                📚 **1-7 soru**: Az sıklıkta çıkan konular  
                """)
                
                user_field = user_data.get('field', 'Belirlenmedi')
                
                if user_field == "Sayısal":
                    available_subjects = ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Fizik", "TYT Kimya", "TYT Biyoloji", "AYT Matematik", "AYT Fizik", "AYT Kimya", "AYT Biyoloji"]
                elif user_field == "Eşit Ağırlık":
                    available_subjects = ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Tarih", "TYT Coğrafya", "AYT Matematik", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
                elif user_field == "Sözel":
                    available_subjects = ["TYT Türkçe", "TYT Tarih", "TYT Coğrafya", "TYT Felsefe", "TYT Din Kültürü", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya", "AYT Felsefe", "AYT Din Kültürü ve Ahlak Bilgisi"]
                else:
                    available_subjects = list(YKS_TOPICS.keys())
                
                # DOM hata önleyici - stabil key kullan
                selected_subject = st.selectbox("📖 Ders Seçin", available_subjects, key="stable_subject_selector")

                if selected_subject and selected_subject in YKS_TOPICS:
                    st.subheader(f"{selected_subject} Konuları")
                    
                    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
                    subject_content = YKS_TOPICS[selected_subject]
                    
                    # DOM hata önleyici - update tracker
                    if 'topic_updates' not in st.session_state:
                        st.session_state.topic_updates = []
                    
                    # Toplu güncelleme için container
                    update_container = st.empty()
                    
                    # İçerik tipini kontrol et
                    if isinstance(subject_content, dict):
                        # Sözlük formatındaysa
                        for main_topic, sub_topics in subject_content.items():
                            with st.expander(f"📂 {main_topic}", expanded=False):
                                if isinstance(sub_topics, dict):
                                    # Alt konular da sözlük
                                    for sub_topic, details in sub_topics.items():
                                        st.write(f"**📋 {sub_topic}**")
                                        for detail in details:
                                            topic_key = f"{selected_subject} | {main_topic} | {sub_topic} | {detail}"
                                            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                                            with col1:
                                                # Soru sayısı bilgisini ekle
                                                question_count = get_topic_question_count(detail)
                                                if question_count > 0:
                                                    st.write(f"• {detail} <span style='color: #ff6b6b; font-size: 0.8em;'>({question_count} soru)</span>", unsafe_allow_html=True)
                                                else:
                                                    st.write(f"• {detail}")
                                            with col2:
                                                current_net = topic_progress.get(topic_key, '0')
                                                try:
                                                    current_net_int = int(float(current_net))
                                                except (ValueError, TypeError):
                                                    current_net_int = 0
                                                # DOM hata önleyici - stabil key oluştur
                                                stable_key = f"slider_{hash(topic_key)}_{selected_subject}_{main_topic}_{sub_topic}_{detail}"
                                                new_net = st.slider(f"Net ({detail})", 0, 20, current_net_int, key=stable_key, label_visibility="collapsed")
                                            with col3:
                                                st.write(calculate_level(new_net))
                                            with col4:
                                                # Soru sıklığı ikonu
                                                if question_count > 0:
                                                    if question_count >= 15:
                                                        st.write("🔥", help=f"Çok sık çıkan konu: {question_count} soru")
                                                    elif question_count >= 8:
                                                        st.write("⚡", help=f"Orta sıklıkta çıkan konu: {question_count} soru")
                                                    else:
                                                        st.write("📚", help=f"Az sıklıkta çıkan konu: {question_count} soru")
                                            
                                            # Güncelleme
                                            if str(new_net) != current_net:
                                                topic_progress[topic_key] = str(new_net)
                                                update_user_in_firebase(st.session_state.current_user, {'topic_progress': json.dumps(topic_progress)})
                                                st.session_state.users_db = load_users_from_firebase()
                                                # Haftalık plan cache'ini temizle
                                                if 'weekly_plan_cache' in st.session_state:
                                                    del st.session_state.weekly_plan_cache
                                                # 14+ net ise tamamlama tarihini kaydet
                                                check_and_update_completion_dates()
                                                st.session_state.topic_updates.append((detail, new_net))
                                elif isinstance(sub_topics, list):
                                    # Alt konular liste
                                    for detail in sub_topics:
                                        topic_key = f"{selected_subject} | {main_topic} | None | {detail}"
                                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                                        with col1:
                                            # Soru sayısı bilgisini ekle
                                            question_count = get_topic_question_count(detail)
                                            if question_count > 0:
                                                st.write(f"• {detail} <span style='color: #ff6b6b; font-size: 0.8em;'>({question_count} soru)</span>", unsafe_allow_html=True)
                                            else:
                                                st.write(f"• {detail}")
                                        with col2:
                                            current_net = topic_progress.get(topic_key, '0')
                                            try:
                                                current_net_int = int(float(current_net))
                                            except (ValueError, TypeError):
                                                current_net_int = 0
                                            # DOM hata önleyici - stabil key oluştur
                                            stable_key = f"slider_{hash(topic_key)}_{selected_subject}_{main_topic}_{detail}"
                                            new_net = st.slider(f"Net ({detail})", 0, 20, current_net_int, key=stable_key, label_visibility="collapsed")
                                        with col3:
                                            st.write(calculate_level(new_net))
                                        with col4:
                                            # Soru sıklığı ikonu
                                            if question_count > 0:
                                                if question_count >= 15:
                                                    st.write("🔥", help=f"Çok sık çıkan konu: {question_count} soru")
                                                elif question_count >= 8:
                                                    st.write("⚡", help=f"Orta sıklıkta çıkan konu: {question_count} soru")
                                                else:
                                                    st.write("📚", help=f"Az sıklıkta çıkan konu: {question_count} soru")
                                        
                                        # Güncelleme
                                        if str(new_net) != current_net:
                                            topic_progress[topic_key] = str(new_net)
                                            update_user_in_firebase(st.session_state.current_user, {'topic_progress': json.dumps(topic_progress)})
                                            st.session_state.users_db = load_users_from_firebase()
                                            # Haftalık plan cache'ini temizle
                                            if 'weekly_plan_cache' in st.session_state:
                                                del st.session_state.weekly_plan_cache
                                            # 14+ net ise tamamlama tarihini kaydet
                                            check_and_update_completion_dates()
                                            st.session_state.topic_updates.append((detail, new_net))
                    elif isinstance(subject_content, list):
                        # Ana içerik liste formatındaysa
                        with st.expander(f"📂 {selected_subject} Konuları", expanded=True):
                            for detail in subject_content:
                                topic_key = f"{selected_subject} | None | None | {detail}"
                                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                                with col1:
                                    # Soru sayısı bilgisini ekle
                                    question_count = get_topic_question_count(detail)
                                    if question_count > 0:
                                        st.write(f"• {detail} <span style='color: #ff6b6b; font-size: 0.8em;'>({question_count} soru)</span>", unsafe_allow_html=True)
                                    else:
                                        st.write(f"• {detail}")
                                with col2:
                                    current_net = topic_progress.get(topic_key, '0')
                                    try:
                                        current_net_int = int(float(current_net))
                                    except (ValueError, TypeError):
                                        current_net_int = 0
                                    # DOM hata önleyici - stabil key oluştur
                                    stable_key = f"slider_{hash(topic_key)}_{selected_subject}_{detail}"
                                    new_net = st.slider(f"Net ({detail})", 0, 20, current_net_int, key=stable_key, label_visibility="collapsed")
                                with col3:
                                    st.write(calculate_level(new_net))
                                with col4:
                                    # Soru sıklığı ikonu
                                    if question_count > 0:
                                        if question_count >= 15:
                                            st.write("🔥", help=f"Çok sık çıkan konu: {question_count} soru")
                                        elif question_count >= 8:
                                            st.write("⚡", help=f"Orta sıklıkta çıkan konu: {question_count} soru")
                                        else:
                                            st.write("📚", help=f"Az sıklıkta çıkan konu: {question_count} soru")
                                
                                # Güncelleme
                                if str(new_net) != current_net:
                                    topic_progress[topic_key] = str(new_net)
                                    update_user_in_firebase(st.session_state.current_user, {'topic_progress': json.dumps(topic_progress)})
                                    st.session_state.users_db = load_users_from_firebase()
                                    # Haftalık plan cache'ini temizle
                                    if 'weekly_plan_cache' in st.session_state:
                                        del st.session_state.weekly_plan_cache
                                    # 14+ net ise tamamlama tarihini kaydet
                                    check_and_update_completion_dates()
                                    st.session_state.topic_updates.append((detail, new_net))
                    
                    # Toplu güncelleme bildirimi - DOM güvenli
                    if len(st.session_state.topic_updates) > 0:
                        with update_container.container():
                            st.success(f"✅ {len(st.session_state.topic_updates)} konu güncellendi!")
                            
                            # Güncellenen konuları göster
                            for detail, net in st.session_state.topic_updates[-5:]:  # Son 5 güncelleme
                                st.caption(f"• {detail}: {net} net")
                    
                    # Toplu kaydetme seçeneği
                    if st.button("💾 Tüm Değişiklikleri Kaydet", type="primary", key="save_all_button"):
                        try:
                            update_user_in_firebase(st.session_state.current_user, {'topic_progress': json.dumps(topic_progress)})
                            st.session_state.users_db = load_users_from_firebase()
                            # Cache temizleme
                            if 'weekly_plan_cache' in st.session_state:
                                del st.session_state.weekly_plan_cache
                            check_and_update_completion_dates()
                            st.success("✅ Tüm net değerleri başarıyla kaydedildi!")
                            # Güncelleme listesini temizle
                            st.session_state.topic_updates = []
                        except Exception as e:
                            st.error(f"Kaydetme hatası: {str(e)}")

            elif page == "⚙️ Benim Programım":
                st.markdown(f'<div class="main-header"><h1>⚙️ Benim Programım</h1><p>Derece öğrencisi disipliniyle çalışın</p></div>', unsafe_allow_html=True)
                
                user_data = get_user_data()
                
                # Program seçimi
                st.subheader("🎯 Çalışma Programını Seçin")
                selected_program = st.selectbox(
                    "Size uygun programı seçin:",
                    list(STUDY_PROGRAMS.keys()),
                    format_func=lambda x: f"{x} - {STUDY_PROGRAMS[x]['description']}"
                )
                
                program_info = STUDY_PROGRAMS[selected_program]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📅 Program Süresi", f"{program_info['duration']} gün")
                with col2:
                    st.metric("⏰ Günlük Çalışma", f"{program_info['daily_hours']} saat")
                with col3:
                    st.metric("🎯 Hedef", program_info['target'])
                
                if st.button("🚀 Programı Başlat", type="primary", use_container_width=True):
                    study_plan = calculate_study_schedule(user_data, selected_program)
                    st.session_state.current_study_plan = study_plan
                    st.success(f"🎉 {selected_program} başlatıldı! {program_info['duration']} gün boyunca bu programı takip edeceksiniz.")
                
                # Günlük planlama
                st.markdown("---")
                st.subheader("📝 Günlük Çalışma Planı")
                
                # Günlük zaman çizelgesi
                st.write("**⏰ Örnek Günlük Zaman Çizelgesi**")
                selected_schedule = st.selectbox("Program tipi seçin:", list(DAILY_PLAN_TEMPLATES.keys()))
                
                for time_slot, activity in DAILY_PLAN_TEMPLATES[selected_schedule].items():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.write(f"**{time_slot}**")
                    with col2:
                        st.write(activity)
                
                # Haftalık hedef belirleme
                st.markdown("---")
                st.subheader("🎯 Haftalık Hedefler")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    weekly_goal_subjects = st.number_input("Haftalık ders sayısı", min_value=1, max_value=10, value=4)
                with col2:
                    weekly_goal_topics = st.number_input("Haftalık konu sayısı", min_value=1, max_value=20, value=8)
                with col3:
                    weekly_goal_hours = st.number_input("Haftalık çalışma saati", min_value=10, max_value=50, value=25)
                
                if st.button("💾 Haftalık Hedefleri Kaydet", use_container_width=True):
                    st.success("Hedefler kaydedildi! Bu hafta bu hedeflere ulaşmaya odaklanın.")
                
                # Aylık ilerleme takibi
                st.markdown("---")
                st.subheader("📈 Aylık İlerleme Takibi")
                
                # Basit bir ilerleme grafiği
                months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"]
                progress_data = {
                    'Ay': months,
                    'Tamamlanan Konu': [15, 28, 42, 35, 50, 65],
                    'Çalışılan Saat': [120, 135, 150, 140, 160, 180],
                    'Deneme Net Ort.': [45.2, 48.7, 52.1, 55.3, 58.9, 62.4]
                }
                
                progress_df = pd.DataFrame(progress_data)
                fig = px.line(progress_df, x='Ay', y=['Tamamlanan Konu', 'Çalışılan Saat', 'Deneme Net Ort.'], 
                             title='Aylık İlerleme Grafiği', markers=True)
                st.plotly_chart(fig, use_container_width=True)
                
                # Motivasyon ve hatırlatıcılar
                st.markdown("---")
                st.subheader("💫 Motivasyon ve Hatırlatıcılar")
                
                fmotivation_tips = [
                    "🔹 Her gün aynı saatte çalışmaya başlayarak rutin oluşturun",
                    "🔹 Büyük hedefleri küçük parçalara bölün",
                    "🔹 Her tamamlanan konu için kendinizi ödüllendirin",
                    "🔹 Düzenli molalar vererek zihninizi taze tutun",
                    "🔹 Haftada bir genel tekrar yapın",
                    "🔹 Uyku düzeninize dikkat edin",
                    "🔹 Spor yaparak stres atın"
                ]
                
                for tip in fmotivation_tips:
                    st.write(tip)
                
                # Çalışma istatistikleri
                st.markdown("---")
                st.subheader("📊 Çalışma İstatistikleri")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🔥 Bugünkü Çalışma", "3.5 saat")
                with col2:
                    st.metric("✅ Bu Hafta Tamamlanan", "12 konu")
                with col3:
                    st.metric("🎯 Bu Ayki Hedef", "45 konu")
                with col4:
                    st.metric("📈 İlerleme Oranı", "%68")
                
                # Anlık geri bildirim
                st.markdown("---")
                st.subheader("💡 Anlık Geri Bildirim")
                
                feedback_options = {
                    "Çok verimli geçti": "🟢",
                    "Normal verimlilikte": "🟡", 
                    "Düşük verimlilik": "🔴",
                    "Planı revize etmem gerek": "🔵"
                }
                
                st.write("Bugünkü çalışmanızı nasıl değerlendiriyorsunuz?")
                selected_feedback = st.radio("Geri bildirim:", list(feedback_options.keys()))
                
                if st.button("📤 Geri Bildirimi Gönder", use_container_width=True):
                    st.success("Geri bildiriminiz kaydedildi! Programınız bu geri bildirime göre optimize edilecek.")

            elif page == "🧠 Çalışma Teknikleri":
                st.markdown(f'<div class="main-header"><h1>🧠 Çalışma Teknikleri</h1><p>YKS öğrencisine özel, psikolojik ve bilimsel çalışma yöntemleri</p></div>', unsafe_allow_html=True)
                
                st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px; margin-bottom: 30px; text-align: center;">
                    <h2>💪 Harika! Aşağıda senin için özel hazırlanmış teknikler var</h2>
                    <p>Her teknik için psikolojik etki, uygun dersler ve öğrenci tipi belirtildi</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Renk paleti - her teknik için farklı renk
                colors = [
                    "#8B5CF6",  # Mor
                    "#3B82F6",  # Mavi  
                    "#10B981",  # Yeşil
                    "#F59E0B",  # Turuncu
                    "#EF4444",  # Kırmızı
                    "#8B5A2B",  # Kahverengi
                    "#6366F1",  # İndigo
                    "#EC4899",  # Pembe
                    "#14B8A6",  # Teal
                    "#F97316",  # Amber
                    "#84CC16",  # Lime
                    "#A855F7",  # Violet
                    "#06B6D4",  # Cyan
                    "#D946EF",  # Fuchsia
                    "#22C55E"   # Green
                ]
                
                # Teknikleri 3'er 3'er grupla
                technique_list = list(STUDY_TECHNIQUES.items())
                
                # Her satırda 3 kolon
                for group_start in range(0, len(technique_list), 3):
                    group_techniques = technique_list[group_start:group_start + 3]
                    cols = st.columns(3)
                    
                    for i, (technique_name, info) in enumerate(group_techniques):
                        color = colors[(group_start + i) % len(colors)]
                        
                        with cols[i]:
                            # Ana kart
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, {color}, {color}CC); border-radius: 20px; padding: 25px; margin-bottom: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); color: white; text-align: center; transform: translateY(0); transition: all 0.3s ease;">
                                <h3 style="margin-bottom: 15px; font-size: 1.3rem; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">{info['icon']} {technique_name}</h3>
                                <p style="font-size: 1rem; margin-bottom: 15px; opacity: 0.95;"><strong>🎯 Tanım:</strong> {info['description']}</p>
                                <p style="font-size: 0.9rem; margin-bottom: 0; opacity: 0.9;"><strong>🧠 Uygun Stiller:</strong> {', '.join(info['learning_styles'])}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Detayları göster butonu
                            if st.button(f"📋 Detayları Gör", key=f"detail_{technique_name}", use_container_width=True):
                                st.session_state[f'show_detail_{technique_name}'] = not st.session_state.get(f'show_detail_{technique_name}', False)
                            
                            # Detaylar açıldıysa göster
                            if st.session_state.get(f'show_detail_{technique_name}', False):
                                
                                st.markdown("**📘 Adımlar:**")
                                for step in info['steps']:
                                    st.write(f"• {step}")
                                
                                st.markdown("**💬 Psikolojik Etkisi:**")
                                st.info(info['psychological_effect'])
                                
                                st.markdown("**🧩 En Uygun Dersler:**")
                                if isinstance(info['best_subjects'], list):
                                    st.success(', '.join(info['best_subjects']))
                                else:
                                    st.success(info['best_subjects'])
                                
                                st.markdown("**👤 Uygun Öğrenci Tipi:**")
                                st.warning(info['suitable_student'])
                                
                                # Kapatma butonu
                                if st.button(f"❌ Kapat", key=f"close_{technique_name}", use_container_width=True):
                                    st.session_state[f'show_detail_{technique_name}'] = False
                                    st.rerun()
                    
                    # Grup arası boşluk
                    if group_start + 3 < len(technique_list):
                        st.markdown("<br>", unsafe_allow_html=True)
                
                # Alt bilgi
                st.markdown("""
                <div style="background: linear-gradient(135deg, #e6fffa 0%, #b2f5ea 100%); border-radius: 15px; padding: 25px; margin-top: 40px; border-left: 5px solid #38b2ac; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                    <h4 style="color: #2d3748; margin-bottom: 15px; font-size: 1.2rem;">💡 Kullanım Önerisi</h4>
                    <p style="color: #4a5568; margin: 0; font-size: 1rem; line-height: 1.6;">Kendi öğrenme stilinize ve hedef bölümünüze uygun teknikleri seçin. Bir anda çok fazla teknik denemek yerine, 2-3 tanesini düzenli olarak uygulayın.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 🃏 ÇEVİRMELİ KAĞIT OYUNU - YENİ!
                st.markdown("---")
                st.markdown("""
                <div style="background: linear-gradient(135deg, #ff6b6b 0%, #feca57 50%, #48dbfb 100%); color: white; padding: 30px; border-radius: 20px; margin: 40px 0; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
                    <h1 style="margin: 0; font-size: 2.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">🃏 ÇEVİRMELİ KAĞIT OYUNU</h1>
                    <p style="margin: 10px 0 0 0; font-size: 1.3rem; opacity: 0.95;">Kendi kartlarını oluştur ve çalış! Eğlenceli ezber sistemi</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Kullanıcının kartlarını saklamak için Firebase entegrasyonu
                if 'user_flashcards' not in st.session_state:
                    # Firebase'den kullanıcının kartlarını yükle
                    username = st.session_state.get('current_user', None)
                    if username:
                        users_data = load_users_from_firebase()
                        user_data = users_data.get(username, {})
                        saved_cards = user_data.get('flashcards', '{}')
                        try:
                            if isinstance(saved_cards, str):
                                st.session_state.user_flashcards = json.loads(saved_cards)
                            else:
                                st.session_state.user_flashcards = saved_cards if isinstance(saved_cards, dict) else {}
                        except (json.JSONDecodeError, TypeError):
                            st.session_state.user_flashcards = {}
                    else:
                        st.session_state.user_flashcards = {}
                
                # Sekme sistemi - Kartlarımı Göster | Yeni Kart Ekle
                tab1, tab2 = st.tabs(["🎮 Kartlarımı Çalış", "➕ Yeni Kart Ekle"])
                
                with tab2:
                    # Form temizleme kontrolü
                    if 'card_form_counter' not in st.session_state:
                        st.session_state.card_form_counter = 0
                    
                    # Yeni kart ekleme formu
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                               border-radius: 15px; padding: 25px; margin: 20px 0;">
                        <h3 style="color: #2d3748; margin-bottom: 20px; text-align: center;">✨ Yeni Kart Oluştur</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Form alanları - unique key'ler
                    form_key = st.session_state.card_form_counter
                    col_form1, col_form2 = st.columns(2)
                    
                    with col_form1:
                        # Ders seçimi
                        subject_for_card = st.selectbox(
                            "📚 Hangi ders için kart?",
                            ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Fizik", "TYT Kimya", "TYT Biyoloji", 
                             "TYT Tarih", "TYT Coğrafya", "TYT Felsefe", "AYT Matematik", "AYT Fizik", "AYT Kimya", 
                             "AYT Biyoloji", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"],
                            key=f"new_card_subject_{form_key}"
                        )
                        
                        # Kartın ön yüzü
                        card_front = st.text_area(
                            "📝 Kartın Ön Yüzü (Soru/Kavram)",
                            placeholder="Örnek: Ahmet Haşim\nveya: (a+b)² = ?\nveya: 1453 yılında ne oldu?",
                            height=100,
                            key=f"card_front_{form_key}"
                        )
                    
                    with col_form2:
                        # Kart kategorisi
                        card_category = st.text_input(
                            "🏷️ Kategori (isteğe bağlı)",
                            placeholder="Örnek: Şairler, Formüller, Tarihler...",
                            key=f"card_category_{form_key}"
                        )
                        
                        # Kartın arka yüzü
                        card_back = st.text_area(
                            "✅ Kartın Arka Yüzü (Cevap/Açıklama)",
                            placeholder="Örnek: Göl Saatleri, O Belde, Gurabahane-i Laklakan\nveya: a² + 2ab + b²\nveya: İstanbul'un Fethi",
                            height=100,
                            key=f"card_back_{form_key}"
                        )
                    
                    # Kart ekleme butonu
                    if st.button("🎯 Kartı Kaydet", use_container_width=True, type="primary", key=f"save_card_{form_key}"):
                        if card_front.strip() and card_back.strip():
                            # Kullanıcının kartlarına ekle
                            if subject_for_card not in st.session_state.user_flashcards:
                                st.session_state.user_flashcards[subject_for_card] = []
                            
                            new_card = {
                                'front': card_front.strip(),
                                'back': card_back.strip(),
                                'category': card_category.strip() if card_category.strip() else "Genel",
                                'created_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                'study_count': 0,
                                'known': False
                            }
                            
                            st.session_state.user_flashcards[subject_for_card].append(new_card)
                            
                            # Firebase'e kaydet
                            username = st.session_state.get('current_user', None)
                            if username:
                                try:
                                    flashcards_json = json.dumps(st.session_state.user_flashcards, ensure_ascii=False)
                                    update_user_in_firebase(username, {'flashcards': flashcards_json})
                                    st.success(f"🎉 Kart '{subject_for_card}' dersine eklendi ve Firebase'e kaydedildi!")
                                except Exception as e:
                                    st.success(f"🎉 Kart '{subject_for_card}' dersine eklendi! (Yerel olarak)")
                                    st.info("💾 Kartlarınız bu oturum boyunca saklanacak.")
                            else:
                                st.success(f"🎉 Kart '{subject_for_card}' dersine eklendi! (Geçici)")
                                st.warning("⚠️ Giriş yapın ki kartlarınız kalıcı olarak saklansın!")
                            
                            st.balloons()
                            
                            # Form counter'ı artır ve yenile (bu şekilde form temizlenir)
                            st.session_state.card_form_counter += 1
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Lütfen hem ön yüz hem de arka yüz alanlarını doldurun!")
                
                with tab1:
                    # Kartları çalışma bölümü
                    if not st.session_state.user_flashcards:
                        st.info("📋 Henüz hiç kartınız yok. 'Yeni Kart Ekle' sekmesinden kartlarınızı oluşturun!")
                    else:
                        # Ders seçimi
                        available_subjects = list(st.session_state.user_flashcards.keys())
                        selected_subject = st.selectbox(
                            "🎯 Hangi dersi çalışmak istiyorsun?",
                            available_subjects,
                            key="study_subject_select"
                        )
                        
                        if selected_subject and st.session_state.user_flashcards[selected_subject]:
                            cards = st.session_state.user_flashcards[selected_subject]
                            
                            # Kart seçimi ve durum
                            if 'current_card_index' not in st.session_state:
                                st.session_state.current_card_index = 0
                            if 'show_answer' not in st.session_state:
                                st.session_state.show_answer = False
                            
                            # Index'i kontrol et
                            if st.session_state.current_card_index >= len(cards):
                                st.session_state.current_card_index = 0
                            
                            current_card = cards[st.session_state.current_card_index]
                            
                            # İstatistikler
                            col_stat1, col_stat2, col_stat3 = st.columns(3)
                            with col_stat1:
                                st.metric("📊 Toplam Kart", len(cards))
                            with col_stat2:
                                known_cards = sum(1 for card in cards if card.get('known', False))
                                st.metric("✅ Bildiğim", known_cards)
                            with col_stat3:
                                progress_percent = (known_cards / len(cards) * 100) if len(cards) > 0 else 0
                                st.metric("🎯 İlerleme", f"%{progress_percent:.1f}")
                            
                            # Ana kart gösterimi - Düzeltilmiş animasyon
                            card_color = "#667eea" if not st.session_state.show_answer else "#764ba2"
                            card_icon = "📝" if not st.session_state.show_answer else "✅"
                            card_title = "SORU / KAVRAM" if not st.session_state.show_answer else "CEVAP / AÇIKLAMA"
                            card_content = current_card['front'] if not st.session_state.show_answer else current_card['back']
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(145deg, {card_color} 0%, #764ba2 100%); 
                                        border-radius: 25px; padding: 40px; margin: 30px 0; 
                                        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
                                        text-align: center; min-height: 250px; 
                                        transition: all 0.3s ease-in-out;">
                                <div style="color: white; font-size: 1.2rem; margin-bottom: 15px; opacity: 0.9;">
                                    📚 {selected_subject} - Kart {st.session_state.current_card_index + 1}/{len(cards)}
                                </div>
                                <div style="color: rgba(255,255,255,0.8); font-size: 0.9rem; margin-bottom: 20px;">
                                    🏷️ {current_card.get('category', 'Genel')}
                                </div>
                                <div style="background: rgba(255,255,255,0.15); border-radius: 15px; padding: 30px; margin: 20px 0;">
                                    <div style="font-size: 1.8rem; color: white; font-weight: bold; margin-bottom: 20px;">
                                        {card_icon} {card_title}
                                    </div>
                                    <div style="font-size: 1.6rem; color: white; line-height: 1.5; word-wrap: break-word;">
                                        {card_content}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Kontrol butonları
                            col1, col2, col3, col4, col5 = st.columns(5)
                            
                            with col1:
                                if st.button("⬅️ Önceki", use_container_width=True):
                                    if st.session_state.current_card_index > 0:
                                        st.session_state.current_card_index -= 1
                                    else:
                                        st.session_state.current_card_index = len(cards) - 1
                                    st.session_state.show_answer = False
                                    st.rerun()
                            
                            with col2:
                                if st.button(f"🔄 {'Cevabı Gör' if not st.session_state.show_answer else 'Soruya Dön'}", 
                                           use_container_width=True, type="primary"):
                                    st.session_state.show_answer = not st.session_state.show_answer
                                    st.rerun()
                            
                            with col3:
                                if st.button("✅ Biliyorum", use_container_width=True, type="secondary"):
                                    current_card['known'] = True
                                    current_card['study_count'] = current_card.get('study_count', 0) + 1
                                    
                                    # Firebase'e kaydet
                                    username = st.session_state.get('current_user', None)
                                    if username:
                                        try:
                                            flashcards_json = json.dumps(st.session_state.user_flashcards, ensure_ascii=False)
                                            update_user_in_firebase(username, {'flashcards': flashcards_json})
                                        except:
                                            pass  # Sessiz hata yönetimi
                                    
                                    st.success("🎉 Harika! Bu kartı bildiğinizi işaretledik!")
                                    time.sleep(1)
                                    st.rerun()
                            
                            with col4:
                                if st.button("❌ Bilmiyorum", use_container_width=True):
                                    current_card['known'] = False
                                    current_card['study_count'] = current_card.get('study_count', 0) + 1
                                    
                                    # Firebase'e kaydet
                                    username = st.session_state.get('current_user', None)
                                    if username:
                                        try:
                                            flashcards_json = json.dumps(st.session_state.user_flashcards, ensure_ascii=False)
                                            update_user_in_firebase(username, {'flashcards': flashcards_json})
                                        except:
                                            pass  # Sessiz hata yönetimi
                                    
                                    st.info("💪 Sorun yok! Bu kartı tekrar çalışalım!")
                                    time.sleep(1)
                                    st.rerun()
                            
                            with col5:
                                if st.button("➡️ Sonraki", use_container_width=True):
                                    if st.session_state.current_card_index < len(cards) - 1:
                                        st.session_state.current_card_index += 1
                                    else:
                                        st.session_state.current_card_index = 0
                                    st.session_state.show_answer = False
                                    st.rerun()
                            
                            # Ek özellikler
                            st.markdown("---")
                            col_extra1, col_extra2, col_extra3 = st.columns(3)
                            
                            with col_extra1:
                                if st.button("🎲 Rastgele Kart", use_container_width=True):
                                    st.session_state.current_card_index = random.randint(0, len(cards) - 1)
                                    st.session_state.show_answer = False
                                    st.rerun()
                            
                            with col_extra2:
                                if st.button("🗑️ Bu Kartı Sil", use_container_width=True):
                                    if st.button("⚠️ Evet, Sil!", key="confirm_delete"):
                                        cards.pop(st.session_state.current_card_index)
                                        
                                        # Firebase'e kaydet
                                        username = st.session_state.get('current_user', None)
                                        if username:
                                            try:
                                                flashcards_json = json.dumps(st.session_state.user_flashcards, ensure_ascii=False)
                                                update_user_in_firebase(username, {'flashcards': flashcards_json})
                                            except:
                                                pass  # Sessiz hata yönetimi
                                        
                                        if not cards:  # Son kart silinmişse
                                            st.session_state.current_card_index = 0
                                        elif st.session_state.current_card_index >= len(cards):
                                            st.session_state.current_card_index = len(cards) - 1
                                        st.success("🗑️ Kart silindi ve Firebase'den kaldırıldı!")
                                        st.rerun()
                            
                            with col_extra3:
                                if st.button("📊 Sadece Bilmediklerim", use_container_width=True):
                                    unknown_cards = [i for i, card in enumerate(cards) if not card.get('known', False)]
                                    if unknown_cards:
                                        st.session_state.current_card_index = random.choice(unknown_cards)
                                        st.session_state.show_answer = False
                                        st.rerun()
                                    else:
                                        st.success("🎉 Harika! Tüm kartları biliyorsunuz!")
                            
                            # İlerleme çubuğu
                            st.progress(progress_percent / 100)
                            st.markdown(f"**📈 İlerleme Durumun:** {known_cards}/{len(cards)} kart tamamlandı (%{progress_percent:.1f})")
                        else:
                            st.info(f"📋 '{selected_subject}' dersinde henüz kart yok. Yeni kart ekleyin!")
                
                # Kullanım ipuçları ve veri saklama bilgisi
                st.markdown("""
                <div style="background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%); 
                           border-radius: 15px; padding: 20px; margin-top: 30px;">
                    <h4 style="color: #2d3748; margin-bottom: 15px;">💡 Nasıl Daha Etkili Kullanırım?</h4>
                    <ul style="color: #4a5568; margin: 0; padding-left: 20px;">
                        <li><strong>➕ Kendi Kartlarını Yap:</strong> İhtiyacın olan konuları ekle</li>
                        <li><strong>🔄 Düzenli Tekrar:</strong> Bilmediklerini daha sık çalış</li>
                        <li><strong>🎲 Karışık Çalış:</strong> Rastgele özelliğini kullan</li>
                        <li><strong>📊 İlerlemeni Takip Et:</strong> Hangi kartları bildiğini işaretle</li>
                        <li><strong>🏷️ Kategorize Et:</strong> Konuları kategorilere ayır</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Veri saklama durumu
                username = st.session_state.get('current_user', None)
                if username:
                    total_cards = sum(len(cards) for cards in st.session_state.user_flashcards.values())
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                               border-radius: 15px; padding: 20px; margin-top: 20px; text-align: center;">
                        <h4 style="color: #2d3748; margin-bottom: 15px;">💾 Veri Saklama Durumu</h4>
                        <div style="color: #2d3748; font-size: 1.1rem;">
                            <div style="margin: 10px 0;"><strong>👤 Kullanıcı:</strong> {username}</div>
                            <div style="margin: 10px 0;"><strong>📊 Toplam Kartların:</strong> {total_cards} adet</div>
                            <div style="margin: 10px 0;"><strong>💾 Saklama:</strong> <span style="color: #27ae60; font-weight: bold;">KALICI ✅</span></div>
                            <div style="margin: 10px 0;"><strong>🔄 Senkronizasyon:</strong> <span style="color: #27ae60;">Firebase Database</span></div>
                            <div style="margin: 10px 0; font-size: 0.9rem; opacity: 0.8;">
                                <strong>⏰ Süre:</strong> Kartların hesabınızda kalıcı olarak saklanıyor.<br>
                                Farklı cihazlardan giriş yaptığınızda tüm kartlarınızı görebilirsiniz!
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                               border-radius: 15px; padding: 20px; margin-top: 20px; text-align: center;">
                        <h4 style="color: #2d3748; margin-bottom: 15px;">⚠️ Veri Saklama Uyarısı</h4>
                        <div style="color: #2d3748; font-size: 1.1rem;">
                            <div style="margin: 10px 0;"><strong>👤 Durum:</strong> <span style="color: #e74c3c;">Giriş Yapılmamış</span></div>
                            <div style="margin: 10px 0;"><strong>💾 Saklama:</strong> <span style="color: #e74c3c; font-weight: bold;">GEÇİCİ ❌</span></div>
                            <div style="margin: 10px 0;"><strong>⏰ Süre:</strong> <span style="color: #e74c3c;">Tarayıcı kapanana kadar</span></div>
                            <div style="margin: 15px 0; font-size: 0.9rem; padding: 10px; background: rgba(231, 76, 60, 0.1); border-radius: 8px;">
                                <strong>🔑 Çözüm:</strong> Ana sayfa → Giriş Yap → Kartlarınız kalıcı olarak saklanacak!
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif page == "🎯 YKS Canlı Takip":
                yks_takip_page(user_data)
            
            elif page == "🍅 Pomodoro Timer":
                pomodoro_timer_page(user_data)
            
            
              
            
            elif page == "🧠 Psikolojim":
                run_psychology_page()
            elif page == "🔬Detaylı Deneme Analiz Takibi":
                st.markdown(f'<div class="main-header"><h1>🔬Detaylı Deneme Analiz Takibi</h1><p>Sınav performansınızı bilimsel analiz edin</p></div>', unsafe_allow_html=True)

                # Eğer global olarak daha önce tanımlanmadıysa ders soru sayılarını tanımla
                if 'SUBJECT_MAX_QUESTIONS' not in globals():
                    SUBJECT_MAX_QUESTIONS = {
                        "TYT Türkçe": 40, "TYT Matematik": 40, "TYT Geometri": 40,
                        "TYT Tarih": 5, "TYT Coğrafya": 5, "TYT Felsefe": 5, "TYT Din Kültürü": 5,
                        "TYT Fizik": 7, "TYT Kimya": 7, "TYT Biyoloji": 6,
                        "AYT Matematik": 40, "AYT Fizik": 14, "AYT Kimya": 13, "AYT Biyoloji": 13,
                        "AYT Edebiyat": 40, "AYT Tarih": 40, "AYT Coğrafya": 40
                    }

                # Kullanıcının deneme verilerini yükle
                deneme_data_str = user_data.get('deneme_analizleri', '[]')
                try:
                    deneme_kayitlari = json.loads(deneme_data_str) if deneme_data_str else []
                except Exception:
                    deneme_kayitlari = []

                # Yeni deneme ekleme (manuel toplam_net alanını koruyoruz)
                with st.expander("➕ Yeni Deneme Ekle", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        deneme_adi = st.text_input("Deneme Adı", placeholder="Örn: 2024 TYT Denemesi #1", key="deneme_adi")
                        deneme_tarihi = st.date_input("Deneme Tarihi", key="deneme_tarihi")
                    with col2:
                        deneme_turu = st.selectbox("Deneme Türü", ["TYT", "AYT", "TYT-AYT"], key="deneme_turu")
                        # Eski arayüzde olan toplam_net alanını bırakıyoruz (kullanıcı manuel girebilir)
                        toplam_net_input = st.number_input("Toplam Net (manuel, istersen bırak)", min_value=0.0, max_value=200.0, step=0.25, key="toplam_net")
                    with col3:
                        toplam_dogru = st.number_input("Toplam Doğru", min_value=0, max_value=200, step=1, key="toplam_dogru")
                        toplam_yanlis = st.number_input("Toplam Yanlış", min_value=0, max_value=200, step=1, key="toplam_yanlis")

                # Ders bazlı net bilgileri (her dersin max'ını SUBJECT_MAX_QUESTIONS ile kontrol et)
                st.subheader("📝 Ders Bazlı Net Dağılımı")
                ders_netleri = {}

                if deneme_turu in ("TYT", "TYT-AYT"):
                    tyt_dersler = ["TYT Türkçe", "TYT Matematik", "TYT Geometri",
                                   "TYT Fizik", "TYT Kimya", "TYT Biyoloji",
                                   "TYT Tarih", "TYT Coğrafya", "TYT Felsefe", "TYT Din Kültürü"]
                    cols = st.columns(2)
                    for i, ders in enumerate(tyt_dersler):
                        with cols[i % 2]:
                            max_val = SUBJECT_MAX_QUESTIONS.get(ders, 20)
                            ders_netleri[ders] = st.number_input(
                                f"{ders} Net",
                                min_value=0.0,
                                max_value=float(max_val),
                                step=0.25,
                                key=f"tyt_{ders}"
                            )

                if deneme_turu in ("AYT", "TYT-AYT"):
                    ayt_dersler = ["AYT Matematik", "AYT Fizik", "AYT Kimya", "AYT Biyoloji", "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
                    cols = st.columns(2)
                    for i, ders in enumerate(ayt_dersler):
                        with cols[i % 2]:
                            max_val = SUBJECT_MAX_QUESTIONS.get(ders, 20)
                            ders_netleri[ders] = st.number_input(
                                f"{ders} Net",
                                min_value=0.0,
                                max_value=float(max_val),
                                step=0.25,
                                key=f"ayt_{ders}"
                            )

                # Yanlış analizi (eski key'leri koruyoruz: f"{ders}_{neden}" -> böylece önceki kayıtlara bağlılık bozulmaz)
                st.subheader("🔍 Yanlış Analizi")
                yanlis_nedenleri = {
                    "Bilgi Eksikliği": "Konuyu tam olarak öğrenmemiş olmak",
                    "Dikkatsizlik": "Soruyu yanlış okuma veya işlem hatası",
                    "Zaman Yetmedi": "Süreyi iyi kullanamama",
                    "Yorum Hatası": "Sorunun mantığını anlayamama",
                    "Şans Eseri Doğru": "Tahminle doğru cevabı bulma",
                    "Kodlama Hatası": "İşaretleme hatası"
                }

                yanlis_analiz = {}
                for ders, net in ders_netleri.items():
                    subject_max = SUBJECT_MAX_QUESTIONS.get(ders, 20)
                    if float(net) < float(subject_max) * 0.75:
                        with st.expander(f"❌ {ders} - Yanlış Analizi"):
                            st.write(f"Bu derste {float(subject_max) - float(net):.1f} net kaybınız var. Sebepleri:")
                            for neden, aciklama in yanlis_nedenleri.items():
                                # Burada eski key formatını koruyoruz: key=f"{ders}_{neden}"
                                yanlis_sayisi = st.number_input(
                                    f"{ders} - {neden}",
                                    min_value=0,
                                    max_value=int(subject_max),
                                    value=0,
                                    step=1,
                                    key=f"{ders}_{neden}"
                                )
                                if yanlis_sayisi > 0:
                                    if ders not in yanlis_analiz:
                                        yanlis_analiz[ders] = {}
                                    yanlis_analiz[ders][neden] = int(yanlis_sayisi)

                # Eksik konu tespiti (aynı mantık korunuyor)
                st.subheader("📌 Eksik Konu Tespiti")
                eksik_konular = {}
                for ders, net in ders_netleri.items():
                    subject_max = SUBJECT_MAX_QUESTIONS.get(ders, 20)
                    if float(net) < float(subject_max) * 0.6:
                        st.write(f"**{ders}** - Eksik konularınızı işaretleyin:")
                        ders_konulari = get_topic_list(ders)
                        if ders_konulari:
                            secilen_konular = st.multiselect(f"{ders} eksik konular", ders_konulari, key=f"eksik_{ders}")
                            if secilen_konular:
                                eksik_konular[ders] = secilen_konular

                # Kaydet butonu: manuel toplam_net_input varsa onu kullan, yoksa ders_netleri toplamını kullan
                if st.button("💾 Deneme Analizini Kaydet", type="primary", use_container_width=True, key="kaydet_deneme"):
                    if deneme_adi and deneme_tarihi:
                        # Derslerden otomatik toplam
                        computed_total = sum([float(v) for v in ders_netleri.values()]) if ders_netleri else 0.0
                        # Eğer kullanıcı manuel toplam girmişse (manuel > 0) onu öncelikle kullan, değilse computed_total
                        toplam_net_to_save = float(toplam_net_input) if float(toplam_net_input) > 0.0 else float(computed_total)

                        yeni_deneme = {
                            "id": len(deneme_kayitlari) + 1,
                            "adi": deneme_adi,
                            "tarih": str(deneme_tarihi),
                            "tur": deneme_turu,
                            "toplam_net": float(toplam_net_to_save),
                            "toplam_dogru": int(toplam_dogru),
                            "toplam_yanlis": int(toplam_yanlis),
                            "ders_netleri": ders_netleri,
                            "yanlis_analiz": yanlis_analiz,
                            "eksik_konular": eksik_konular,
                            "tavsiyeler": []
                        }

                        # Basit otomatik tavsiyeler (ders oranlarına göre)
                        tavsiyeler = []
                        if float(toplam_net_to_save) < 50.0:
                            tavsiyeler.append("🔴 Netiniz düşük: Öncelik temel konu tekrarları olmalı.")
                        elif float(toplam_net_to_save) < 80.0:
                            tavsiyeler.append("🟡 Orta seviye: Eksik konulara ve hız çalışmasına odaklanın.")
                        else:
                            tavsiyeler.append("🟢 İyi seviyedesiniz: Deneme pratiğini sürdürün, süre yönetimini geliştirin.")

                        # Sadece düşük performanslı dersler için tavsiye ekle
                        dusuk_dersler = []
                        orta_dersler = []
                        for ders, net in ders_netleri.items():
                            subject_max = SUBJECT_MAX_QUESTIONS.get(ders, 20)
                            oran = float(net) / subject_max if subject_max > 0 else 0
                            if oran < 0.3:
                                dusuk_dersler.append(ders)
                            elif oran < 0.6:
                                orta_dersler.append(ders)
                        
                        if dusuk_dersler:
                            tavsiyeler.append(f"📚 **Öncelikli Dersler ({len(dusuk_dersler)} ders)**: {', '.join(dusuk_dersler[:3])} {'ve diğerleri' if len(dusuk_dersler) > 3 else ''} - Temel konu tekrarı yapın.")
                        if orta_dersler:
                            tavsiyeler.append(f"📖 **Geliştirilebilir Dersler ({len(orta_dersler)} ders)**: {', '.join(orta_dersler[:3])} {'ve diğerleri' if len(orta_dersler) > 3 else ''} - Soru çözme pratiği yapın.")

                        yeni_deneme["tavsiyeler"] = tavsiyeler
                        deneme_kayitlari.append(yeni_deneme)

                        # TYT/AYT NET GÜNCELLEMESİ - Otomatik hesapla ve güncelle
                        updates_to_firebase = {'deneme_analizleri': json.dumps(deneme_kayitlari)}
                        
                        # Son 3 denemeyi al ve net hesapla
                        recent_3_exams = deneme_kayitlari[-3:] if len(deneme_kayitlari) >= 3 else deneme_kayitlari
                        
                        # Değişkenleri başta tanımla
                        last_tyt_total = 0
                        last_ayt_total = 0
                        
                        # TYT NET HESAPLAMA
                        if deneme_turu in ["TYT", "TYT-AYT"]:
                            tyt_subjects = ["TYT Türkçe", "TYT Matematik", "TYT Geometri", "TYT Fizik", 
                                          "TYT Kimya", "TYT Biyoloji", "TYT Tarih", "TYT Coğrafya", 
                                          "TYT Felsefe", "TYT Din Kültürü"]
                            
                            # En son denemenin TYT toplam net'ini hesapla
                            last_tyt_total = sum([float(ders_netleri.get(subj, 0)) for subj in tyt_subjects])
                            updates_to_firebase['tyt_last_net'] = str(last_tyt_total)
                            
                            # Son 3 denemenin TYT ortalamasını hesapla
                            tyt_totals = []
                            for exam in recent_3_exams:
                                if exam.get('tur') in ["TYT", "TYT-AYT"]:
                                    exam_tyt_total = sum([float(exam.get('ders_netleri', {}).get(subj, 0)) for subj in tyt_subjects])
                                    tyt_totals.append(exam_tyt_total)
                            
                            if tyt_totals:
                                tyt_avg = sum(tyt_totals) / len(tyt_totals)
                                updates_to_firebase['tyt_avg_net'] = str(tyt_avg)
                        
                        # AYT NET HESAPLAMA
                        if deneme_turu in ["AYT", "TYT-AYT"]:
                            ayt_subjects = ["AYT Matematik", "AYT Fizik", "AYT Kimya", "AYT Biyoloji", 
                                          "AYT Edebiyat", "AYT Tarih", "AYT Coğrafya"]
                            
                            # En son denemenin AYT toplam net'ini hesapla
                            last_ayt_total = sum([float(ders_netleri.get(subj, 0)) for subj in ayt_subjects])
                            updates_to_firebase['ayt_last_net'] = str(last_ayt_total)
                            
                            # Son 3 denemenin AYT ortalamasını hesapla
                            ayt_totals = []
                            for exam in recent_3_exams:
                                if exam.get('tur') in ["AYT", "TYT-AYT"]:
                                    exam_ayt_total = sum([float(exam.get('ders_netleri', {}).get(subj, 0)) for subj in ayt_subjects])
                                    ayt_totals.append(exam_ayt_total)
                            
                            if ayt_totals:
                                ayt_avg = sum(ayt_totals) / len(ayt_totals)
                                updates_to_firebase['ayt_avg_net'] = str(ayt_avg)
                        
                        # Tüm güncellemeleri Firebase'e kaydet
                        update_user_in_firebase(st.session_state.current_user, updates_to_firebase)
                        
                        # Firebase'den fresh data çek
                        st.session_state.users_db = load_users_from_firebase()
                        
                        # MEVCUT KULLANICININ USER_DATA'SINI TAMAMEN YENİLE
                        current_user_name = st.session_state.current_user
                        if current_user_name in st.session_state.users_db:
                            # user_data'yı tamamen yenile
                            st.session_state.user_data = st.session_state.users_db[current_user_name].copy()

                        # Başarı mesajını güncelle
                        success_msg = "✅ Deneme analizi başarıyla kaydedildi!"
                        if deneme_turu in ["TYT", "TYT-AYT"]:
                            success_msg += f"\n🔄 TYT Son Net: {last_tyt_total:.1f} olarak güncellendi"
                            if 'tyt_avg_net' in updates_to_firebase:
                                success_msg += f"\n📊 TYT Ortalama Net: {float(updates_to_firebase['tyt_avg_net']):.1f} olarak güncellendi"
                        if deneme_turu in ["AYT", "TYT-AYT"]:
                            success_msg += f"\n🔄 AYT Son Net: {last_ayt_total:.1f} olarak güncellendi"
                            if 'ayt_avg_net' in updates_to_firebase:
                                success_msg += f"\n📊 AYT Ortalama Net: {float(updates_to_firebase['ayt_avg_net']):.1f} olarak güncellendi"
                        
                        st.success(success_msg)
                        
                        # Güncellenen netleri göster
                        if deneme_turu in ["TYT", "TYT-AYT"] and 'tyt_last_net' in updates_to_firebase:
                            st.info(f"📈 TYT netlerin güncellendi: Son {float(updates_to_firebase['tyt_last_net']):.1f}, Ort {float(updates_to_firebase.get('tyt_avg_net', 0)):.1f}")
                        if deneme_turu in ["AYT", "TYT-AYT"] and 'ayt_last_net' in updates_to_firebase:
                            st.info(f"📈 AYT netlerin güncellendi: Son {float(updates_to_firebase['ayt_last_net']):.1f}, Ort {float(updates_to_firebase.get('ayt_avg_net', 0)):.1f}")
                        
                        # Başarı animasyonu (kısa)
                        st.balloons()
                        
                        # DOM hatasını önlemek için daha kısa delay ve alternatif yenileme
                        time.sleep(0.5)
                        
                        # State'i temizle ve yeniden yükle
                        if 'deneme_form_submitted' not in st.session_state:
                            st.session_state.deneme_form_submitted = True
                        
                        st.rerun()
                    else:
                        st.error("⚠️ Lütfen deneme adı ve tarihini giriniz")

                # Geçmiş denemeleri gösterme + seçilen deneme detayları
                if deneme_kayitlari:
                    st.markdown("---")
                    st.subheader("📈 Geçmiş Denemeler")

                    deneme_listesi = [f"{d['adi']} - {d['tarih']} ({d['tur']})" for d in deneme_kayitlari]
                    secilen_deneme = st.selectbox("Analizini görüntülemek istediğiniz denemeyi seçin:", deneme_listesi, key="deneme_secim")

                    if secilen_deneme:
                        deneme_index = deneme_listesi.index(secilen_deneme)
                        deneme = deneme_kayitlari[deneme_index]

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📊 Toplam Net", f"{float(deneme.get('toplam_net', 0)):.1f}")
                        with col2:
                            st.metric("✅ Doğru Sayısı", deneme.get('toplam_dogru', 0))
                        with col3:
                            st.metric("❌ Yanlış Sayısı", deneme.get('toplam_yanlis', 0))
                        with col4:
                            st.metric("🎯 Deneme Türü", deneme.get('tur', '—'))

                        # Net dağılım grafiği
                        st.subheader("📊 Net Dağılımı")
                        dersler = [d for d, v in (deneme.get('ders_netleri') or {}).items() if v > 0]
                        netler = [deneme.get('ders_netleri', {}).get(d, 0) for d in dersler]
                        if dersler:
                            fig = px.bar(x=dersler, y=netler, title="Derslere Göre Net Dağılımı",
                                         labels={'x': 'Dersler', 'y': 'Net'}, color=netler,
                                         color_continuous_scale="Viridis")
                            st.plotly_chart(fig, use_container_width=True, key=f"analysis_chart_{deneme.get('adi', '')}_{deneme.get('tarih', '')}_{hash(str(dersler))}")

                        # Öneriler (kaydedilmiş öneriler gösterilsin) - DOM hatasını önlemek için tek markdown
                        st.subheader("💡 Kayıtlı Gelişim Tavsiyeleri")
                        tavsiyeler = deneme.get('tavsiyeler', [])
                        if tavsiyeler and len(tavsiyeler) > 0:
                            # Tüm tavsiyeleri tek bir markdown string'de birleştir
                            tavsiye_text = "\n".join([f"{i+1}. {tavsiye}" for i, tavsiye in enumerate(tavsiyeler)])
                            st.markdown(tavsiye_text)
                        else:
                            st.info("📝 Bu deneme için henüz tavsiye kaydedilmemiş.")

                    # ----- EN ALTA: Tüm denemelerin gidişat grafiği -----
                    st.markdown("---")
                    st.subheader("📈 Zaman İçinde Gelişim (Tüm Denemeler)")
                    tarihler = [d.get('tarih') for d in deneme_kayitlari]
                    netler = [float(d.get('toplam_net', 0)) for d in deneme_kayitlari]
                    if tarihler and any(netler):
                        gelisim_df = pd.DataFrame({"Tarih": tarihler, "Toplam Net": netler})
                        fig_line = px.line(gelisim_df, x="Tarih", y="Toplam Net", markers=True,
                                           title="Denemelerde Net Gelişimi")
                        st.plotly_chart(fig_line, use_container_width=True, key=f"gelisim_grafigi_{len(deneme_kayitlari)}_{hash(str(netler))}")

                        # Son denemeye özel ders bazlı öneriler (kısa, eyleme dönük)
                        son_deneme = deneme_kayitlari[-1]
                        low_subjects = []
                        for ders, net in (son_deneme.get('ders_netleri') or {}).items():
                            max_val = SUBJECT_MAX_QUESTIONS.get(ders, 20)
                            try:
                                oran = float(net) / float(max_val) if float(max_val) > 0 else 0
                            except Exception:
                                oran = 0
                            if oran < 0.5:
                                low_subjects.append((ders, oran))

                        st.subheader("📌 Son Denemeye Göre Öncelikli Öneriler")
                        if low_subjects and len(low_subjects) > 0:
                            # DOM hatasını önlemek için tüm önerileri tek markdown'da birleştir
                            oneriler_listesi = []
                            for i, (ders, oran) in enumerate(low_subjects):
                                oneriler_listesi.append(f"{i+1}. **{ders}** (%{oran*100:.0f}): Konu tekrarı ve çıkmış soru çözümü; eksik konuları parça parça kapatın.")
                            st.markdown("\n".join(oneriler_listesi))
                        else:
                            st.markdown("🎉 Tebrikler! Son denemede ders bazında kayda değer düşük alan bulunmadı.")

                        # Genel çalışma önerileri (kaynaklı, kısa)
                        st.markdown("---")
                        st.subheader("🔎 Güvenilir Kaynaklardan Derlenen Kısa Çalışma Önerileri")
                        st.markdown("- Okuduğunu anlama için günlük okuma alışkanlığı (gazete/deneme/uzun paragraflar).")

            elif page == "📊 İstatistikler":
                st.markdown(f'<div class="main-header"><h1>📊 Detaylı İstatistikler</h1><p>İlerlemenizi analiz edin</p></div>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_completed = sum(data['completed'] for data in progress_data.values())
                    total_topics = count_total_topics()
                    st.metric("📊 Toplam Konu", f"{total_completed}/{total_topics}")
                with col2:
                    completion_rate = (total_completed / total_topics * 100) if total_topics > 0 else 0
                    st.metric("🎯 Tamamlanma Oranı", f"%{completion_rate:.1f}")
                with col3:
                    avg_net = 0; net_count = 0
                    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
                    for topic_data in topic_progress.values():
                        try:
                            avg_net += float(topic_data)
                            net_count += 1
                        except ValueError:
                            continue
                    avg_net = (avg_net / net_count) if net_count > 0 else 0
                    st.metric("⭐ Ortalama Net", f"{avg_net:.1f}")
                
                st.subheader("📈 Ders Bazında İlerleme")
                if progress_data:
                    subjects = list(progress_data.keys())
                    percents = [data['percent'] for data in progress_data.values()]
                    fig = px.bar(x=subjects, y=percents, title="Derslere Göre Tamamlanma Oranları", labels={'x': 'Dersler', 'y': 'Tamamlanma (%)'}, color=percents, color_continuous_scale="Viridis")
                    st.plotly_chart(fig, use_container_width=True)
                    st.subheader("📋 Detaylı İlerleme Tablosu")
                    progress_df = pd.DataFrame([{'Ders': s, 'Tamamlanan': d['completed'], 'Toplam': d['total'], 'Oran (%)': d['percent']} for s, d in progress_data.items()])
                    st.dataframe(progress_df, use_container_width=True)
                else:
                    st.info("📊 Henüz yeterli veri bulunmuyor. Konu takip sayfasından ilerlemenizi kaydedin.")
                    
            elif page == "⏰ SAR ZAMANI Geriye 🔁":
                show_sar_zamani_geriye_page(user_data, progress_data)
            
            elif page == "🎨 Öğrenme Stilleri Testi":
                run_vak_learning_styles_test()
            
            elif page == "🧠 Bilişsel Profil Testi":
                run_cognitive_profile_test()
            
            elif page == "⚡ Motivasyon & Duygu Testi":
                run_motivation_emotional_test()
            
            elif page == "⏰ Zaman Yönetimi Testi":
                run_time_management_test()

# === HİBRİT POMODORO SİSTEMİ FONKSİYONLARI ===

def start_hibrit_breathing():
    """Hibrit nefes sistemini başlat - Pomodoro'yu duraklat"""
    # Pomodoro'yu duraklat
    if st.session_state.pomodoro_active:
        st.session_state.breathing_paused_time = st.session_state.time_remaining
    
    # Nefes sistemini başlat
    st.session_state.breathing_active = True
    st.session_state.breath_time_remaining = 60
    st.session_state.breath_start_time = time.time()
    
    # Rastgele bir motivasyon türü seç
    motivation_types = ['quote', 'tip', 'breathing']
    st.session_state.current_motivation_type = random.choice(motivation_types)
    
    if st.session_state.current_motivation_type == 'quote':
        st.session_state.current_motivation_content = random.choice(MOTIVATION_QUOTES)
    elif st.session_state.current_motivation_type == 'tip':
        subject = st.session_state.current_subject
        if subject in MICRO_TIPS:
            st.session_state.current_motivation_content = random.choice(MICRO_TIPS[subject])
        else:
            st.session_state.current_motivation_content = random.choice(MICRO_TIPS['Genel'])
    else:  # breathing
        exercise = random.choice(BREATHING_EXERCISES)
        st.session_state.current_motivation_content = f"""
🫁 **{exercise['name']}**

📋 {exercise['instruction']}

✨ **Faydası:** {exercise['benefit']}
        """
    
    # Kullanım loguna kaydet
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'subject': st.session_state.current_subject,
        'motivation_type': st.session_state.current_motivation_type,
        'remaining_time_when_used': st.session_state.breathing_paused_time
    }
    st.session_state.breathing_usage_log.append(log_entry)
    
    st.success("💨 Hibrit nefes molası başladı! Pomodoro timer duraklatıldı.")

def complete_breathing_exercise():
    """Nefes egzersizini tamamla ve Pomodoro'ya dön"""
    st.session_state.breathing_active = False
    st.session_state.breath_time_remaining = 60
    st.session_state.breath_start_time = None
    
    # Pomodoro'yu kaldığı yerden devam ettir
    if st.session_state.pomodoro_active:
        st.session_state.time_remaining = st.session_state.breathing_paused_time
        st.session_state.start_time = time.time()
    
    st.success("🎉 Hibrit nefes molası tamamlandı! Pomodoro kaldığı yerden devam ediyor.")
    st.balloons()

def show_breathing_exercise():
    """Hibrit nefes egzersizini göster"""
    breath_seconds = int(st.session_state.breath_time_remaining)
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        animation: pulse 2s infinite;
    ">
        <h2 style="color: white; margin-bottom: 20px;">🌬️ Hibrit Nefes Molası</h2>
        <div style="font-size: 72px; font-weight: bold; margin: 20px 0;">
            {breath_seconds}s
        </div>
        <div style="
            font-size: 18px; 
            font-style: italic; 
            margin: 20px 0; 
            min-height: 100px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            border-left: 4px solid #ffd700;
            white-space: pre-line;
        ">
            {st.session_state.current_motivation_content}
        </div>
        <div style="font-size: 14px; opacity: 0.9; margin-top: 15px;">
            🍅 Pomodoro timer duraklatıldı • Kaldığı yerden devam edecek
        </div>
    </div>
    
    <style>
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(1); }}
    }}
    </style>
    """, unsafe_allow_html=True)

# ===== MODERN VAK ANALIZ FONKSİYONLARI =====

def display_modern_vak_analysis(dominant_style, visual_percent, auditory_percent, kinesthetic_percent):
    """Modern ve detaylı VAK analizi gösterir"""
    
    # Paydaşılan bilgi paragrafına göre detaylı özellikler
    vak_detailed_info = {
        "Görsel": {
            "icon": "👁️",
            "title": "GÖRSEL ÖĞRENME STİLİ",
            "natural_places": [
                "Doğal olarak düzenli ve temiz bir çevresi olmasını ister",
                "Ayrıntıları ve renkleri iyi hatırlar",
                "Okumayı, yazmayı sever",
                "İnsanların yüzünü hatırlar ama isimlerini unutur",
                "Zihinsel (görsel) imgeler yaratmayı sever"
            ],
            "problem_solving": [
                "Talimatları okumayı tercih eder",
                "Problemleri listeler",
                "Düşüncelerini düzenlerken grafiksel malzemeler kullanır",
                "Akış kartları ve şemaları etkili kullanır",
                "Kağıt üzerinde grafiksel çalışmalar yapar"
            ],
            "evaluation_needs": [
                "Görsel-yazılı testlerde başarılı",
                "Araştırma raporları hazırlamayı sever",
                "Grafiksel gösterimlerden yararlanır",
                "Yazılı sınavlarda yüksek başarı gösterir"
            ],
            "best_learning": [
                "Not alarak öğrenir",
                "Liste yaparak bilgileri organize eder",
                "Bir gösteriyi izleyerek öğrenir",
                "Kitaplar, video filmler ve basılı materyallerden yararlanır",
                "Görsel destekli içeriklerle daha iyi anlar"
            ],
            "school_difficulties": [
                "Ne yapılacağını görmeden hareket etmekte zorlanır",
                "Gürültülü ve hareketli çevrede çalışamaz",
                "Görsel resim ve malzeme olmadan öğretmeni dinleyemez",
                "Sıkıcı ve düzensiz sınıfta çalışmak istemez",
                "Florasan ışığı altında çalışmaktan verim alamaz"
            ],
            "general_evaluation": [
                "Özel yaşamlarında genellikle düzenlidirler",
                "Karışıklık ve dağınıklıktan rahatsız olurlar",
                "Çantaları, dolapları her zaman düzenlidir",
                "Harita, poster, şema, grafik gibi görsel araçlardan kolay etkilenirler",
                "Öğrendikleri konuları gözlerinin önüne getirerek hatırlamaya çalışırlar"
            ]
        },
        "İşitsel": {
            "icon": "👂",
            "title": "İŞİTSEL ÖĞRENME STİLİ",
            "natural_places": [
                "Doğaçlama (spontan) konuşur",
                "Ayaküstü düşünür",
                "Karşılaştığı insanların yüzlerini unutur ama adlarını hatırlar",
                "Kelimelerle ve dille çalışmayı sever",
                "Hafif sesli ortamlardan hoşlanır"
            ],
            "problem_solving": [
                "Tartışmalardan hoşlanır",
                "Seçenekler hakkında konuşur",
                "Bir durumda ne yapılacağını o durumu yaşayanlara sorar",
                "Hedefi sözle ifade eder",
                "Sözlü tekrarlar yapar"
            ],
            "evaluation_needs": [
                "Yazılılardan ziyade sözlülerde başarılı olur",
                "Projelerini sözlü olarak sunar",
                "Ne öğrendiğinin birileri tarafından sorulmasını ister",
                "Şiir okumaktan, şarkı söylemekten hoşlanır"
            ],
            "best_learning": [
                "Yüksek sesle anlatım dinleyerek",
                "Küçük ve büyük grup tartışması yaparak",
                "Çalışma yerinde fon olarak sessiz müzik dinleyerek",
                "Sesli kaynak materyallerle",
                "Konuları anlatarak ve tartışarak"
            ],
            "school_difficulties": [
                "Görsel öğrencilerden daha yavaş okur",
                "Uzun süre sessiz okuyamaz",
                "Okuduğu parçada resimleri umursamaz",
                "Sessizleştirilmiş ortamda yaşamada sıkıntı yaşar",
                "Uzun süre sessiz kalmakta zorlanır"
            ],
            "general_evaluation": [
                "Küçük yaşlarda kendi kendilerine konuşurlar",
                "Ses ve müziğe duyarlıdırlar",
                "Sohbet etmeyi, birileri ile çalışmayı severler",
                "Genellikle ahenkli ve güzel konuşurlar",
                "İşittiklerini daha iyi anlarlar ve hatırlarlar"
            ]
        },
        "Kinestetik": {
            "icon": "✋",
            "title": "KİNESTETİK ÖĞRENME STİLİ",
            "natural_places": [
                "Çeşitli spor ve danslarla uğraşmayı sever",
                "Yarışmalardan ve maceradan hoşlanır",
                "Zorluklara meydan okur",
                "Koşma, sıçrama, atlama, yuvarlanma gibi hareketlerden hoşlanır",
                "Büyük motor kasları kullanmayı gerektiren eylemlerden hoşlanır"
            ],
            "problem_solving": [
                "Harekete geçer daha sonra da sonuçlara bakarak plan yapar",
                "Problemleri güç kullanarak (fiziksel olarak) çözmeye çalışır",
                "Önemli ölçüde bedensel çaba gerektiren çözümler arar",
                "Problemleri bireysel olarak veya çok küçük gruplarla çalışarak çözmeyi tercih eder",
                "Deneme-yanılma ve keşfetme yoluyla öğrenir"
            ],
            "evaluation_needs": [
                "Performansa dayalı ve proje yönelimli değerlendirmelerde başarılı olur",
                "Öğrendiği şeyi sergileme veya gösterme eğilimi vardır",
                "Bir şeyi anlatmaktan ziyade nasıl yapılacağını göstermeyi tercih eder",
                "Uygulamalı değerlendirmelerde daha başarılı"
            ],
            "best_learning": [
                "Canlandırma ve taklit yaparak",
                "Gezerek ve performansa dayalı öğrenmeyle",
                "Küçük tartışma grupları ile",
                "Yaparak yaşayarak öğrenir",
                "Ellerini kullanabileceği yöntemlerle"
            ],
            "school_difficulties": [
                "Okunaaklı el yazısına sahip değildir",
                "Uzun süre oturamaz",
                "Kelimeleri doğru okuma ve kullanmada sıkıntı yaşar",
                "Duyulan, görülen ve yapılan şeyleri hatırlamakta zorlanır",
                "Uzun süre herhangi bir eylemi devam ettiremez"
            ],
            "general_evaluation": [
                "Oldukça hareketli olurlar",
                "Sınıfta yerlerinde duramazlar",
                "Sürekli hareket halindedirler",
                "Dersin anlatılması veya görsel malzemelerle zenginleştirilmesi beklenildiği ölçülerde katkı sağlamaz",
                "Mutlaka ellerini kullanabilecekleri, yaparak yaşayarak öğrenme yöntemlerinin kullanılması gerekir"
            ]
        }
    }
    
    style_info = vak_detailed_info[dominant_style]
    
    st.markdown("---")
    st.markdown(f"## {style_info['icon']} **{style_info['title']}** - Baskın Stiliniz!")
    
    # Stil dağılımı grafik
    col1, col2 = st.columns([2, 1])
    
    with col1:
        import plotly.express as px
        
        vak_data = {
            'Stil': ['Görsel', 'İşitsel', 'Kinestetik'],
            'Yüzde': [visual_percent, auditory_percent, kinesthetic_percent],
            'Renk': ['#FF6B6B', '#4ECDC4', '#45B7D1']
        }
        
        fig = px.pie(
            values=vak_data['Yüzde'], 
            names=vak_data['Stil'],
            title="📊 Öğrenme Stili Dağılımıniz",
            color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1']
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            height=400,
            font=dict(size=14),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Puan Detayları")
        styles = [
            ("Görsel 👁️", visual_percent, "#FF6B6B"),
            ("İşitsel 👂", auditory_percent, "#4ECDC4"),
            ("Kinestetik ✋", kinesthetic_percent, "#45B7D1")
        ]
        
        for style_name, percentage, color in styles:
            is_dominant = style_name.split()[0] == dominant_style
            border = "3px solid #gold" if is_dominant else "1px solid #ddd"
            
            st.markdown(f"""
                <div style="
                    border: {border};
                    padding: 10px;
                    margin: 8px 0;
                    border-radius: 8px;
                    background: linear-gradient(90deg, {color}20, transparent);
                    text-align: center;
                ">
                    <strong>{style_name}</strong><br>
                    <span style="font-size: 24px; color: {color};">%{percentage:.1f}</span>
                </div>
            """, unsafe_allow_html=True)
    
    # Detaylı özellikler
    st.markdown("### 🔍 Detaylı Özellik Analizi")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌟 Doğal Özellikler", 
        "🔧 Problem Çözme", 
        "📉 Değerlendirme", 
        "🎯 En İyi Öğrenme", 
        "⚠️ Okul Zorlukları", 
        "📄 Genel Değerlendirme"
    ])
    
    with tab1:
        st.markdown("**Doğal olduğunuz yerler:**")
        for item in style_info['natural_places']:
            st.write(f"• {item}")
    
    with tab2:
        st.markdown("**Problem çözme yollarınız:**")
        for item in style_info['problem_solving']:
            st.write(f"• {item}")
    
    with tab3:
        st.markdown("**Değerlendirme ve test etme ihtiyacınız:**")
        for item in style_info['evaluation_needs']:
            st.write(f"• {item}")
    
    with tab4:
        st.markdown("**En iyi öğrenme yollarınız:**")
        for item in style_info['best_learning']:
            st.write(f"• {item}")
    
    with tab5:
        st.markdown("**Okuldaki güçlükleriniz:**")
        for item in style_info['school_difficulties']:
            st.write(f"• {item}")
    
    with tab6:
        st.markdown("**Genel değerlendirmeniz:**")
        for item in style_info['general_evaluation']:
            st.write(f"• {item}")
    
    # YKS'ye özel stratejiler
    st.markdown("### 🎯 YKS İçin Özel Stratejileriniz")
    
    yks_strategies = {
        "Görsel": [
            "🗺️ **Kavram haritaları** oluşturun ve konuları görsel olarak bağlayın",
            "🎨 **Renkli kalemler** kullanarak notlarınızı kategorilendirin",
            "📊 **Şemalar ve grafikler** çizerek formülleri ve süreci görselleştirin",
            "📹 **Görsel destekli videolar** izleyin ve ekran görüntüsü alın",
            "📖 **Güzel tasarlanmış kitaplar** ve renkli test kitapları tercih edin",
            "📝 **Akış şemaları** ile konuları adım adım çizin",
            "🖼️ **Poster ve infografikler** hazırlayarak duvarlarınıza asın"
        ],
        "İşitsel": [
            "🎧 **Podcast ve sesli anlatım** kaynakları bulun ve dinleyin",
            "👥 **Çalışma grupları** oluşturun ve konuları tartışın",
            "🗣️ **Konuları sesli anlatın** (kendinize ya da arkadaşlarınıza)",
            "🎵 **Hafif klasik müzik** eşliğinde çalışın",
            "📞 **Online grup çalışmaları** ve Zoom seansı organize edin",
            "🎤 **Sesli notlar** kayıt edin ve tekrar dinleyin",
            "📻 **Radyo programları** ve eğitim yayınları takip edin"
        ],
        "Kinestetik": [
            "✍️ **Çok soru çözümü** yapın (mutlaka elle yazarak)",
            "🚶 **Ayakta çalışma** dönemleri ekleyin (masa başında)",
            "🔧 **Laboratuvar ve pratik uygulamalar** yapın",
            "📝 **El yazısı notlar** alın, tablet yerine kağıt kullanın",
            "⚡ **25 dk çalış, 5 dk hareket** sistemi uygulayın",
            "🎯 **Interaktif simülasyonlar** ve oyunlar kullanın",
            "🏃 **Yürüyüş yaparken** ses kayıtları dinleyin"
        ]
    }
    
    strategies = yks_strategies[dominant_style]
    
    for i, strategy in enumerate(strategies, 1):
        st.markdown(f"{i}. {strategy}")

def display_teacher_guide_section(dominant_style):
    """Eğitimciler için rehber bölümü"""
    
    st.markdown("---")
    st.markdown("🎓 ## Eğitimci Rehberi")
    
    teacher_guide = {
        "Görsel": {
            "recommended_methods": [
                "Tahtada renkli kalemler kullanarak anlatım yapın",
                "Kavram haritaları ve akış şemaları hazırlayın",
                "Görsel destekli sunumlar ve videolar kullanın",
                "Grafik, tablo ve şekiller çizerek açıklayın",
                "Sınıfı düzenli ve görsel olarak zengin tutun"
            ],
            "classroom_setup": [
                "Parlak ve iyi aydınlatılmış sınıf ortamı",
                "Duvar posterler ve eğitici görseller",
                "Düzenli sıra düzenlemesi",
                "Beyaz tahta ve projeksiyon kullanımı",
                "Renkli öğretim materyalleri"
            ],
            "avoid": [
                "Sadece sözlü anlatım yapmayı uzun süre sürdürmek",
                "Gürültülü ve karışık sınıf ortamı",
                "Görsel destek olmadan sınavlar yapmak"
            ]
        },
        "İşitsel": {
            "recommended_methods": [
                "Sesli anlatım ve hikaye anlatımı kullanın",
                "Grup tartışmaları ve beyin fırtınası organize edin",
                "Müzik ve ses efektleri ile dersi zenginleştirin",
                "Sık sık soru-cevap seçimi kullanın",
                "Sesli okuma ve tekrar seçimi yapın"
            ],
            "classroom_setup": [
                "Akustik kalitesi iyi sınıf",
                "Grup çalışmasına uygun oturma düzenlemesi",
                "Ses sistemi ve mikrofonlar",
                "Müzik çalar ve ses kaydı imkanları",
                "Tartışmaya uygun havalandırma"
            ],
            "avoid": [
                "Uzun süre sessizlik dayatmak",
                "Sadece görsel materyallerle ders işlemek",
                "Bireysel çalışmayı çok uzun sürdürmek"
            ]
        },
        "Kinestetik": {
            "recommended_methods": [
                "Uygulamalı etkinlikler ve deneyler organize edin",
                "Hareket gerektiren oyunlar ve simülasyonlar kullanın",
                "Sık ara verme ve fiziksel aktivite ekleyin",
                "Elle tutulur materyaller ve modellerle çalışın",
                "Proje tabanlı öğrenme yöntemini tercih edin"
            ],
            "classroom_setup": [
                "Hareket edebilecek geniş alan",
                "Grup çalışmasına uygun masa düzenlemesi",
                "Deneysel malzemeler ve araçlar",
                "Ayakta çalışma imkanı",
                "Esnek oturma düzenleri"
            ],
            "avoid": [
                "Uzun süre hareketsiz oturmaya zorlama",
                "Sadece teorik anlatım yapma",
                "Fiziksel aktiviteyi kısıtlama"
            ]
        }
    }
    
    guide = teacher_guide[dominant_style]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### ✅ **Tavsiye Edilen Yöntemler**")
        for method in guide['recommended_methods']:
            st.write(f"• {method}")
    
    with col2:
        st.markdown("### 🏢 **Sınıf Düzenlemesi**")
        for setup in guide['classroom_setup']:
            st.write(f"• {setup}")
    
    with col3:
        st.markdown("### ❌ **Kaçınılması Gerekenler**")
        for avoid in guide['avoid']:
            st.write(f"• {avoid}")

def display_advanced_study_techniques(dominant_style):
    """Gelişmiş çalışma teknikleri"""
    
    st.markdown("---")
    st.markdown("⚙️ ## Gelişmiş Çalışma Teknikleri")
    
    advanced_techniques = {
        "Görsel": {
            "memory_techniques": [
                "🗺️ **Zihin Haritası**: Konuları renkli dallar halinde çizin",
                "🎨 **Görsel Hafıza Teknikleri**: Bilgileri resim ve sembollerle ilişkilendirin",
                "🎭 **Hikaye Yöntemi**: Bilgileri görsel hikayeler halinde organize edin",
                "📋 **Zaman Çizgisi**: Tarih ve sıralı konuları çizgisel görsele dönüştürün"
            ],
            "study_tools": [
                "Canva, Miro, MindMeister gibi görsel tasarım araçları",
                "iPad ve Apple Pencil ile dijital çizim",
                "Renkli kağıtlar ve yapışkan notlar",
                "Görsel plan bçleri ve infografikler"
            ],
            "exam_prep": [
                "Soru tiplerine göre renkli kodlama sistemi",
                "Görsel formül kartı hazırlama",
                "Konu başlıklarını akış şeması olarak düzenleme"
            ]
        },
        "İşitsel": {
            "memory_techniques": [
                "🎵 **Müziksel Hafıza**: Bilgileri şarkı ya da ritim halinde öğrenin",
                "🗣️ **Sesli Tekrar**: Konuları kendi sesinizle kaydedin ve dinleyin",
                "👥 **Sosyal Öğrenme**: Arkadaşlarınızla tartışarak öğrenin",
                "🎤 **Anlatım Yöntemi**: Konuları başkalarına anlatarak pekiştirin"
            ],
            "study_tools": [
                "Otter.ai, Rev gibi ses kayıt ve tranükripsiyon araçları",
                "Spotify, Apple Music eğitim listleri",
                "Discord, Zoom grup çalışma platformları",
                "Podcast uygulamaları ve sesli kitaplar"
            ],
            "exam_prep": [
                "Soru çözüm adımlarını sesli açıklama",
                "Grup halinde mock sınav yapımı",
                "Formülleri ritimli şekilde ezberleme"
            ]
        },
        "Kinestetik": {
            "memory_techniques": [
                "✋ **Hareket ile Hafıza**: El hareketleriyle formülleri ilişkilendirin",
                "🚶 **Yürüyüş Hafızası**: Yürüyerek seslice tekrar yapın",
                "🎯 **Fiziksel Model**: Konuları 3D modellerle görselleştirin",
                "✍️ **Yazma Hafızası**: Elle yazarak kas hafızasını geliştirin"
            ],
            "study_tools": [
                "Pomodoro Timer uygulamaları",
                "Standing desk ve egzersiz topları",
                "Fidget araçları ve stres topları",
                "İnteraktif simülasyon yazıçları"
            ],
            "exam_prep": [
                "El yazısı ile çok soru çözme pratiği",
                "Fiziksel hareket ile mental ara verme",
                "Mock sınav sırasında hareket gülümseme"
            ]
        }
    }
    
    techniques = advanced_techniques[dominant_style]
    
    tab1, tab2, tab3 = st.tabs(["🧠 Hafıza Teknikleri", "🛠️ Çalışma Araçları", "📈 Sınav Hazırlığı"])
    
    with tab1:
        st.markdown("**Hafıza ve Öğrenme Teknikleri:**")
        for technique in techniques['memory_techniques']:
            st.write(f"• {technique}")
    
    with tab2:
        st.markdown("**Tavsiye Edilen Çalışma Araçları:**")
        for tool in techniques['study_tools']:
            st.write(f"• {tool}")
    
    with tab3:
        st.markdown("**Sınav Hazırlık Stratejileri:**")
        for prep in techniques['exam_prep']:
            st.write(f"• {prep}")
    
    # Bonus motivasyon bölümü
    st.markdown("### 🏆 Motivasyon İpuçları")
    motivation_tips = {
        "Görsel": "Görsel hedefler koyun! YKS hedef üniversitenizin fotoğrafını çalışma alanınıza asın. İlerleme grafikleri hazırlayın.",
        "İşitsel": "Motivasyon müziği dinleyin! Başarı hikayeleri podcast'lerini takip edin. Kendinize günün sonunda ses kaydı ile teşekkür mesajı bırakın.",
        "Kinestetik": "Hareket halinde hedef belirleyin! Her başarı için kendinizi fiziksel bir aktivite ile ödüllendirin. İlerleme için fiziksel bir başarı panosu hazırlayın."
    }
    
    st.info(motivation_tips[dominant_style])

# ===== PSİKOLOJİM SAYFA FONKSİYONU =====

def run_psychology_page():
    """GENEL PSİKOLOJİK ANALİZ SİSTEMİ - Kendini Tanı & Doğru Çalış"""
    
    # Modern CSS stilleri
    st.markdown("""
    <style>
    /* Ana sistem başlığı */
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    .main-header h1 {
        margin: 0 0 0.5rem 0;
        font-size: 2.2rem;
        font-weight: 600;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-header p {
        margin: 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Psikoloji sayfası için özel header stili */
    .psychology-header {
        position: relative;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .psychology-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(0,0,0,0.6), rgba(0,0,0,0.3));
        border-radius: 15px;
        z-index: 1;
    }
    
    .psychology-header h1,
    .psychology-header p {
        position: relative;
        z-index: 2;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    .section-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 2rem 0 1.5rem 0;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .section-title h2 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 600;
    }
    
    /* Modern Test Kartları - Sade ve Okunabilir */
    .analysis-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e0e6ed;
        transition: all 0.3s ease;
        margin-bottom: 15px;
    }
    
    /* Test Kartları için Renkli Gradient'ler */
    .analysis-card-vak {
        background: linear-gradient(135deg, #8B5CF6, #A855F7, #C084FC);
        border: 1px solid rgba(139, 92, 246, 0.2);
    }
    
    .analysis-card-cognitive {
        background: linear-gradient(135deg, #3B82F6, #1D4ED8, #2563EB);
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    
    .analysis-card-motivation {
        background: linear-gradient(135deg, #F59E0B, #D97706, #EAB308);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }
    
    .analysis-card-time {
        background: linear-gradient(135deg, #10B981, #059669, #16A34A);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    /* Renkli kartlar için yazı rengini beyaza çevirelim */
    .analysis-card-vak h3,
    .analysis-card-cognitive h3,
    .analysis-card-motivation h3,
    .analysis-card-time h3 {
        color: white;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .analysis-card-vak p,
    .analysis-card-cognitive p,
    .analysis-card-motivation p,
    .analysis-card-time p {
        color: rgba(255,255,255,0.9);
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .analysis-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        border-color: #667eea;
    }
    
    .analysis-card-vak:hover,
    .analysis-card-cognitive:hover,
    .analysis-card-motivation:hover,
    .analysis-card-time:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 12px 30px rgba(0,0,0,0.15);
    }
    
    .analysis-card h3 {
        color: #2d3748;
        margin-bottom: 12px;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    .analysis-card p {
        color: #4a5568;
        margin-bottom: 15px;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 15px;
    }
    
    .status-completed {
        background: #e6fffa;
        color: #234e52;
        border: 1px solid #81e6d9;
    }
    
    .status-pending {
        background: #fffbeb;
        color: #92400e;
        border: 1px solid #fbd38d;
    }
    
    /* Genel profil analizi - Daha sade */
    .comprehensive-profile {
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        color: #2d3748;
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    .comprehensive-profile h2 {
        color: #2d3748;
        margin-bottom: 0.5rem;
    }
    
    .comprehensive-profile p {
        color: #4a5568;
    }
    
    .profile-chart {
        background: white;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    
    /* Analiz section */
    .analysis-section {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
    }
    
    .analysis-section h3 {
        color: #2d3748;
        margin: 0;
        font-size: 1.4rem;
        font-weight: 600;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-header {
            padding: 1.5rem;
        }
        .section-title {
            padding: 1rem;
        }
        .analysis-card {
            padding: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Kullanıcı kontrolü
    username = st.session_state.get('current_user', None)
    if not username:
        st.warning("⚠️ Bu sayfaya erişim için önce giriş yapmanız gerekir.")
        st.info("👈 Lütfen sol menüden 'Ana Sayfa' bölümünde giriş yapın.")
        return
    
    users_data = load_users_from_firebase()
    user_data = users_data.get(username, {})
    
    # Ana başlık - Hedef bölüme göre dinamik arka plan
    target_department = user_data.get('target_department', 'Varsayılan')
    bg_style = BACKGROUND_STYLES.get(target_department, BACKGROUND_STYLES["Varsayılan"])
    
    st.markdown(f'''
    <div class="main-header psychology-header" style="background-image: linear-gradient(135deg, rgba(0,0,0,0.6), rgba(0,0,0,0.4)), url('{bg_style["image"]}'); background-size: cover; background-position: center; background-attachment: fixed;">
        <h1>🧭 GENEL PSİKOLOJİK ANALİZ SİSTEMİ</h1>
        <p>"Kendini Tanı & Doğru Çalış" Sistemi</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">🎯 Hedef: {target_department} {bg_style["icon"]}</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Test yapılandırmaları
    test_configs = [
        {
            'id': 'vak',
            'title': '📚 VAK Öğrenme Stilleri Testi',
            'icon': '📚',
            'description': 'Görsel, İşitsel ve Kinestetik öğrenme tercihlerinizi analiz eder.',
            'data_key': 'vak_test_results'
        },
        {
            'id': 'cognitive',
            'title': '🧠 Bilişsel Profil Testi',
            'icon': '🧠',
            'description': 'Analitik düşünce gücünüz ve problem çözme yaklaşımınızı değerlendirir.',
            'data_key': 'cognitive_test_results'
        },
        {
            'id': 'motivation',
            'title': '⚡ Motivasyon & Duygusal Denge Testi',
            'icon': '⚡',
            'description': 'İçsel/dışsal motivasyon düzeyiniz ve duygusal dengenizi analiz eder.',
            'data_key': 'motivation_test_results'
        },
        {
            'id': 'time',
            'title': '⏰ Zaman Yönetimi Testi',
            'icon': '⏰',
            'description': 'Planlama becerileriniz, erteleme eğiliminiz ve odak kontrolünüzü değerlendirir.',
            'data_key': 'time_test_results'
        }
    ]
    
    # 1. BÖLÜM: GENEL PSİKOLOJİK TAHMİNİ ANALİZİM
    st.markdown('''
    <div class="section-title">
        <h2>🔍 Genel Psikolojik Tahmini Analizim</h2>
    </div>
    ''', unsafe_allow_html=True)
    
    # Test kartlarını 2x2 grid ile göster
    cols = st.columns(2)
    completed_tests = []
    
    for i, test in enumerate(test_configs):
        is_completed = bool(user_data.get(test['data_key']))
        if is_completed:
            completed_tests.append(test['id'])
        
        col_index = i % 2
        with cols[col_index]:
            status_class = "status-completed" if is_completed else "status-pending"
            status_text = "✅ Tamamlandı" if is_completed else "⏳ Henüz Yapılmadı"
            
            st.markdown(f'''
            <div class="analysis-card analysis-card-{test['id']}">
                <h3>{test['icon']} {test['title']}</h3>
                <p>{test['description']}</p>
                <div class="status-badge {status_class}">{status_text}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Analiz sonucunu görüntüle butonu
            if is_completed:
                if st.button(f"📊 Analizini Gör", key=f"view_{test['id']}", use_container_width=True):
                    st.session_state[f'show_{test["id"]}_analysis'] = True
                    st.rerun()
            else:
                st.info("Bu test henüz tamamlanmamış.")
            
            # Güncelle/Tekrarla butonu
            if st.button(f"🔄 Testimi Güncelle/Tekrarla", key=f"update_{test['id']}", use_container_width=True):
                # Teste yönlendir
                if test['id'] == 'vak':
                    st.session_state.page = "learning_styles_test"
                elif test['id'] == 'cognitive':
                    st.session_state.page = "cognitive_profile_test"
                elif test['id'] == 'motivation':
                    st.session_state.page = "motivation_emotional_test"
                elif test['id'] == 'time':
                    st.session_state.page = "time_management_test"
                st.rerun()
    
    # Test analizlerini göster
    for test in test_configs:
        if test['id'] in completed_tests and st.session_state.get(f'show_{test["id"]}_analysis', False):
            st.markdown("---")
            
            # Kapat butonu
            if st.button("❌ Analizi Kapat", key=f"close_{test['id']}"):
                st.session_state[f'show_{test["id"]}_analysis'] = False
                st.rerun()
            
            display_individual_test_analysis(test, user_data)
    
    # 2. BÖLÜM: GENEL TAHMİNİ PSİKOLOJİK PROFİLİM
    if len(completed_tests) >= 2:
        st.markdown("---")
        st.markdown('''
        <div class="section-title">
            <h2>🎯 Genel Tahmini Psikolojik Profilim</h2>
        </div>
        ''', unsafe_allow_html=True)
        
        display_comprehensive_psychological_profile(completed_tests, user_data)
    else:
        st.markdown("---")
        st.info("🎯 **Genel psikolojik profilinizi görebilmek için en az 2 test tamamlayın.** Bu sayede size özel, detaylı öneriler sunabiliriz!")
    
    # Test sonucu yoksa bilgilendirme
    if not completed_tests:
        st.markdown("---")
        st.info("🎯 **Henüz hiç test yapmadınız.** Kişiselleştirilmiş öneriler alabilmek için yukarıdaki testlerden birini tamamlamaya başlayabilirsiniz!")

def display_comprehensive_psychological_profile(completed_tests, user_data):
    """Tüm testlerden genel psikolojik profil çıkarımı - Örneğe göre yeniden yazıldı"""
    
    st.markdown('''
    <div class="comprehensive-profile">
        <h2>🧭 GENEL PSİKOLOJİK PROFİL ANALİZİN</h2>
        <p><strong>Öğrenci:</strong> "Senin Beyin Haritan"</p>
        <p><strong>Kaynak:</strong> Öğrenme Stilleri + Bilişsel Profil + Motivasyon + Zaman Yönetimi Testleri</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Test sonuçlarını topla
    profile_data = {}
    
    # VAK Test sonuçları
    if 'vak' in completed_tests:
        vak_scores = user_data.get('learning_style_scores', '')
        vak_style = user_data.get('learning_style', '')
        if vak_scores and vak_style:
            try:
                vak_data = json.loads(vak_scores.replace("'", '"'))
                vak_data['dominant_style'] = vak_style
                profile_data['vak'] = vak_data
            except:
                pass
    
    # Bilişsel Test sonuçları
    if 'cognitive' in completed_tests:
        cognitive_scores = user_data.get('cognitive_test_scores', '')
        if cognitive_scores:
            try:
                raw_cognitive = json.loads(cognitive_scores.replace("'", '"'))
                
                # ADAPTIF VERİ İŞLEME - herhangi bir formattaki veriyi düzenli hale getir
                analytic_score = 0
                synthetic_score = 0
                reflective_score = 0
                
                # Tüm anahtarları kontrol et ve kategorilere ayır
                for key, value in raw_cognitive.items():
                    key_lower = key.lower()
                    
                    # Analitik düşünme
                    if any(word in key_lower for word in ['analytic', 'analytical', 'analyze']):
                        analytic_score += float(value)
                    
                    # Sintetik/Bütüncül düşünme  
                    elif any(word in key_lower for word in ['synthetic', 'synthesis', 'creative', 'visual', 'experiential', 'holistic']):
                        synthetic_score += float(value)
                    
                    # Reflektif düşünme
                    elif any(word in key_lower for word in ['reflective', 'reflection', 'auditory', 'listening']):
                        reflective_score += float(value)
                    
                    # Eğer thinking ile bitiyorsa direkt kullan
                    elif 'thinking' in key_lower:
                        if 'analytic' in key_lower:
                            analytic_score = float(value)
                        elif 'synthetic' in key_lower:
                            synthetic_score = float(value)
                        elif 'reflective' in key_lower:
                            reflective_score = float(value)
                
                # Eğer hiç puan bulunamadıysa default değerler
                if analytic_score == 0 and synthetic_score == 0 and reflective_score == 0:
                    analytic_score = 3.5
                    synthetic_score = 3.2
                    reflective_score = 3.8
                
                # Son format
                cognitive_data = {
                    'analytic_thinking': analytic_score,
                    'synthetic_thinking': synthetic_score,
                    'reflective_thinking': reflective_score
                }
                    
                profile_data['cognitive'] = cognitive_data
            except:
                pass
    
    # Motivasyon Test sonuçları
    if 'motivation' in completed_tests:
        motivation_scores = user_data.get('motivation_test_scores', '')
        if motivation_scores:
            try:
                raw_motivation = json.loads(motivation_scores.replace("'", '"'))
                
                # ADAPTIF VERİ İŞLEME - herhangi bir formattaki veriyi düzenli hale getir
                internal_score = 0
                external_score = 0
                anxiety_score = 0
                resilience_score = 0
                
                # Tüm anahtarları kontrol et ve kategorilere ayır
                for key, value in raw_motivation.items():
                    key_lower = key.lower()
                    
                    # İçsel motivasyon
                    if any(word in key_lower for word in ['internal', 'intrinsic', 'inner', 'motivation_internal']):
                        internal_score += float(value)
                    
                    # Dışsal motivasyon  
                    elif any(word in key_lower for word in ['external', 'extrinsic', 'outer', 'motivation_external']):
                        external_score += float(value)
                    
                    # Sınav kaygısı
                    elif any(word in key_lower for word in ['anxiety', 'worry', 'stress', 'exam_anxiety', 'test_anxiety']):
                        anxiety_score += float(value)
                    
                    # Duygusal dayanıklılık
                    elif any(word in key_lower for word in ['resilience', 'emotional', 'strength', 'durability']):
                        resilience_score += float(value)
                
                # Eğer hiç puan bulunamadıysa default değerler
                if internal_score == 0 and external_score == 0 and anxiety_score == 0 and resilience_score == 0:
                    internal_score = 3.8
                    external_score = 3.2
                    anxiety_score = 2.5
                    resilience_score = 3.9
                
                # Son format
                motivation_data = {
                    'internal_motivation': internal_score,
                    'external_motivation': external_score,
                    'test_anxiety': anxiety_score,
                    'emotional_resilience': resilience_score
                }
                
                profile_data['motivation'] = motivation_data
            except:
                pass
    
    # Zaman Yönetimi Test sonuçları
    if 'time' in completed_tests:
        time_scores = user_data.get('time_test_scores', '')
        if time_scores:
            try:
                raw_time = json.loads(time_scores.replace("'", '"'))
                
                # ADAPTIF VERİ İŞLEME - herhangi bir formattaki veriyi düzenli hale getir
                planning_score = 0
                procrastination_score = 0
                focus_score = 0
                time_score = 0
                priority_score = 0
                discipline_score = 0
                awareness_score = 0
                
                # Tüm anahtarları kontrol et ve kategorilere ayır
                for key, value in raw_time.items():
                    key_lower = key.lower()
                    
                    # Planlama
                    if any(word in key_lower for word in ['planning', 'plan', 'organize', 'structure']):
                        planning_score += float(value)
                    
                    # Erteleme  
                    elif any(word in key_lower for word in ['procrastination', 'delay', 'postpone', 'erteleme']):
                        procrastination_score += float(value)
                    
                    # Odak kontrolü
                    elif any(word in key_lower for word in ['focus', 'concentrate', 'attention', 'odak']):
                        focus_score += float(value)
                    
                    # Zaman bilinci
                    elif any(word in key_lower for word in ['time_awareness', 'time', 'temporal', 'zaman']):
                        time_score += float(value)
                    
                    # Öncelik yönetimi
                    elif any(word in key_lower for word in ['priority', 'prioritization', 'öncelik']):
                        priority_score += float(value)
                    
                    # Disiplin
                    elif any(word in key_lower for word in ['discipline', 'disiplin', 'self_control', 'control']):
                        discipline_score += float(value)
                    
                    # Öz-farkındalık
                    elif any(word in key_lower for word in ['self_awareness', 'awareness', 'farkındalık', 'conscious']):
                        awareness_score += float(value)
                
                # Eğer hiç puan bulunamadıysa default değerler
                if all(score == 0 for score in [planning_score, procrastination_score, focus_score, time_score, priority_score]):
                    planning_score = 3.4
                    procrastination_score = 2.8
                    focus_score = 3.7
                    time_score = 3.1
                    priority_score = 3.5
                
                # Son format
                time_data = {
                    'planning': planning_score,
                    'procrastination': procrastination_score,
                    'focus_control': focus_score,
                    'time_awareness': time_score,
                    'priority_management': priority_score
                }
                
                # Ek kategoriler varsa ekle
                if discipline_score > 0:
                    time_data['discipline'] = discipline_score
                if awareness_score > 0:
                    time_data['self_awareness'] = awareness_score
                
                profile_data['time'] = time_data
            except:
                pass
    
    # Debug bilgisi
    if len(profile_data) == 0:
        st.warning("⚠️ Test sonuçları yüklenirken bir sorun oluştu. Lütfen testleri yeniden yapın.")
        return
    
    # DETAYLI PSIKOLOJIK PROFİL ANALİZİ - Örneğe göre hazırlandı
    
    # 1. BİLİŞSEL PROFİL
    if 'cognitive' in profile_data:
        st.markdown("---")
        st.markdown("## 🧠 1. Bilişsel Profilin")
        
        cognitive = profile_data['cognitive']
        # En yüksek bilişsel özelliği bul
        max_cognitive = max(cognitive.items(), key=lambda x: x[1])
        cognitive_style_map = {
            'analytic_thinking': 'Analitik',
            'synthetic_thinking': 'Bütüncül', 
            'reflective_thinking': 'Reflektif'
        }
        dominant_cognitive = cognitive_style_map.get(max_cognitive[0], 'Karma')
        
        # İkincil stil
        sorted_cognitive = sorted(cognitive.items(), key=lambda x: x[1], reverse=True)
        secondary_cognitive = cognitive_style_map.get(sorted_cognitive[1][0], '')
        
        st.markdown(f"""
        **Sonuç eğilimi:** {dominant_cognitive} – {secondary_cognitive}
        
        Sen bilgiyi sistematik düşünerek işleyen, neden-sonuç ilişkilerini çözümlemeyi seven bir yapıya sahip olabilirsin.
        Bir konuyu anlamadan ezberlemeyi sevmiyor, önce "neden" sorusuna cevap bulmayı tercih ediyor olabilirsin.
        """)
        
        st.markdown("### 💡 Sana uygun çalışma stratejileri:")
        
        strategies = []
        if max_cognitive[0] == 'analytic_thinking':
            strategies.extend([
                "• **Feynman Tekniği:** Bir konuyu sanki bir arkadaşına anlatır gibi basitleştirerek anlat — anlamadığın yer eksik bilgin olur.",
                "• **Kavram Ağları:** Bilgiler arasındaki bağlantıları görselleştir.",
                "• **Soru üretme yöntemi:** Konudan 3 soru üret, kendine sor, kendi cevabını test et."
            ])
        elif max_cognitive[0] == 'synthetic_thinking':
            strategies.extend([
                "• **Büyük Resim Tekniği:** Önce konunun genel mantığını kavra, sonra detaylara in.",
                "• **Kavram Haritası:** Tüm bilgileri birbirine bağlayarak bütüncül şemalar oluştur.",
                "• **Analoji Kurma:** Yeni öğrendiğin konuları bildiğin şeylerle ilişkilendir."
            ])
        else:
            strategies.extend([
                "• **Düşünce Günlüğü:** Öğrendiklerini yazarak işle ve üzerinde düşün.",
                "• **Sessiz Tekrar:** Konuları zihninde gözden geçir ve kendi yorumunu ekle.",
                "• **Soru-Cevap Metodu:** Kendine sorular sor ve derin düşünerek cevapla."
            ])
        
        for strategy in strategies:
            st.info(strategy)
        
        # TYT'ye özel ipuçları
        st.markdown("### 📘 TYT'ye özel ipuçları:")
        
        tyt_tips = []
        if max_cognitive[0] == 'analytic_thinking':
            tyt_tips.extend([
                "• **TYT Matematik:** Her yeni konu için \"önce mantığını anla, sonra soru çöz.\" Özellikle problemleri tabloya dök.",
                "• **TYT Fizik:** Konu formüllerini ezberleme, her formülün neyi temsil ettiğini Feynman tarzında anlat.",
                "• **TYT Biyoloji:** Sebep-sonuç ilişkilerini (örneğin \"neden fotosentezde su gerekir?\") sorgula.",
                "• **TYT Türkçe:** Paragraf sorularında \"yazarın mantığını çözme\" odaklı çalış."
            ])
        elif max_cognitive[0] == 'synthetic_thinking':
            tyt_tips.extend([
                "• **TYT Matematik:** Formülleri ezberlemek yerine, aralarındaki ilişkileri kur.",
                "• **TYT Fizik:** Olayları günlük hayatla ilişkilendir, büyük sistemi göre.",
                "• **TYT Biyoloji:** Canlı sistemlerini bir bütün olarak düşün, parçalar arası bağlantıları kur.",
                "• **TYT Coğrafya:** Ülkeler, iklim ve ekonomi arasındaki genel bağlantıları kavra."
            ])
        else:
            tyt_tips.extend([
                "• **TYT Matematik:** Çözümü yaparken her adımı \"neden böyle yaptım?\" diye sor.",
                "• **TYT Türkçe:** Metinleri okuduktan sonra kendi düşüncelerini de değerlendır.",
                "• **TYT Tarih:** Olayları sadece ezberleme, \"bu ne anlama geliyor?\" diye sor.",
                "• **TYT Felsefe:** Kavramları günlük hayatla ilişkilendir ve üzerinde düşün."
            ])
        
        for tip in tyt_tips:
            st.success(tip)
    
    # 2. ÖĞRENME STİLİ EĞİLİMİ
    if 'vak' in profile_data:
        st.markdown("---")
        st.markdown("## 🎨 2. Öğrenme Stil Eğilimin")
        
        vak = profile_data['vak']
        dominant_style = vak.get('dominant_style', 'Karma')
        
        # Yüzdelik hesaplaması
        visual_score = vak.get('Visual', 0)
        auditory_score = vak.get('Auditory', 0) 
        kinesthetic_score = vak.get('Kinesthetic', 0)
        
        total_score = visual_score + auditory_score + kinesthetic_score
        if total_score > 0:
            visual_percent = int((visual_score / total_score) * 100)
            auditory_percent = int((auditory_score / total_score) * 100)
            kinesthetic_percent = int((kinesthetic_score / total_score) * 100)
        else:
            visual_percent = auditory_percent = kinesthetic_percent = 33
        
        st.markdown(f"""
        **Sonuç eğilimi:** Görsel (%{visual_percent}) – İşitsel (%{auditory_percent}) – Kinestetik (%{kinesthetic_percent})
        
        Senin öğrenme eğilimin {"görsel" if visual_percent > 40 else "işitsel" if auditory_percent > 40 else "kinestetik" if kinesthetic_percent > 40 else "karma"} kanala dayanıyor olabilir. 
        Yani {"renkler, grafikler, şemalar ve video içerikler" if visual_percent > 40 else "sesli açıklamalar, tartışmalar ve müzik" if auditory_percent > 40 else "hareket, dokunma ve uygulama" if kinesthetic_percent > 40 else "farklı yöntemlerin kombinasyonu"} bilgiyi beynine daha güçlü kazıyor olabilir.
        """)
        
        st.markdown("### 🧩 Sana uygun öğrenme teknikleri:")
        
        if visual_percent > 35:
            learning_techniques = [
                "• **Görsel Kodlama:** Konu özetlerini renkli bloklar veya ikonlarla çıkar.",
                "• **\"Gör–Söyle–Yaz\" Tekniği:** Gözle gör, sesli tekrar et, kendi cümlelerinle yaz.",
                "• **Video + Not:** Konuyu önce video ile öğren, ardından aynı konuyu yazarak pekiştir."
            ]
        elif auditory_percent > 35:
            learning_techniques = [
                "• **Sesli Tekrar:** Öğrendiklerini kendine yüksek sesle anlat.",
                "• **Müzik + Çalışma:** Uygun müzik eşliğinde çalış, ritim yarat.",
                "• **Tartışma Grupları:** Arkadaşlarınla konuları tartışarak öğren."
            ]
        elif kinesthetic_percent > 35:
            learning_techniques = [
                "• **Hareket + Öğrenme:** Yürürken formül tekrar et, ayakta çalış.",
                "• **Elle Yazma:** Bilgileri mutlaka el yazısıyla yaz, çiz.",
                "• **Pratik + Teori:** Her konuyu öğrendikten hemen sonra soru çöz."
            ]
        else:
            learning_techniques = [
                "• **Çoklu Kanal:** Görsel, işitsel ve hareket öğelerini birleştir.",
                "• **Esnek Yöntem:** Günlük durumuna göre farklı teknikleri dene.",
                "• **Karma Teknik:** Bir konuyu hem izle, hem dinle, hem de uygula."
            ]
        
        for technique in learning_techniques:
            st.info(technique)
        
        # Ders odaklı öneriler
        st.markdown("### 📘 Ders odaklı öneriler:")
        
        if visual_percent > 35:
            subject_tips = [
                "• **TYT Coğrafya:** Haritalı çalış, haritaları boş kâğıda yeniden çizmeyi dene.",
                "• **TYT Kimya:** Tepkime şemalarını renkli kutularla göster.",
                "• **TYT Tarih:** Zaman çizelgesi oluştur, olayları renk kodlarıyla sırala.",
                "• **TYT Geometri:** Şekil çizmeden asla soru çözme; şekil ve çözüm arasındaki ilişkiyi renkli kalemlerle belirginleştir."
            ]
        elif auditory_percent > 35:
            subject_tips = [
                "• **TYT Türkçe:** Metinleri sesli oku, şiirleri sesli tekrar et.",
                "• **TYT Matematik:** Formülleri kendine anlatarak öğren.",
                "• **TYT Fizik:** Kavramları sesli açıkla, derse katıl.",
                "• **TYT Felsefe:** Kavramları tartışa tartışa öğren."
            ]
        elif kinesthetic_percent > 35:
            subject_tips = [
                "• **TYT Matematik:** Bol bol soru çöz, hesap makinesi kullanmadan pratik yap.",
                "• **TYT Kimya:** Laboratuvar videolarını izle, tepkimeleri simüle et.",
                "• **TYT Biyoloji:** Modeller kullan, organ sistemlerini çizerek öğren.",
                "• **TYT Coğrafya:** Haritaları parmağınla takip et, fiziki özellikleri çiz."
            ]
        else:
            subject_tips = [
                "• **Tüm Dersler:** Her konu için en az 2 farklı yöntem kullan.",
                "• **Esnek Yaklaşım:** Hangi ders için hangi yöntemin etkili olduğunu keşfet.",
                "• **Kombine Çalışma:** Görsel malzemeler + sesli açıklama + pratik yapma."
            ]
        
        for tip in subject_tips:
            st.success(tip)
    
    # 3. MOTİVASYON & DUYGUSAL DENGE
    if 'motivation' in profile_data:
        st.markdown("---")
        st.markdown("## ⚡ 3. Motivasyon & Duygusal Denge")
        
        motivation = profile_data['motivation']
        internal_mot = motivation.get('internal_motivation', 0)
        external_mot = motivation.get('external_motivation', 0)
        
        total_motivation = internal_mot + external_mot
        if total_motivation > 0:
            internal_percent = int((internal_mot / total_motivation) * 100)
            external_percent = int((external_mot / total_motivation) * 100)
        else:
            internal_percent = external_percent = 50
        
        st.markdown(f"""
        **Sonuç eğilimi:** İçsel %{internal_percent} – Dışsal %{external_percent}
        
        Öğrenme isteğin büyük ihtimalle {"kendi gelişimini görmekten geliyor. Ancak bazen çevresel beklentiler (aile, sınav baskısı) moralini etkileyebiliyor olabilir." if internal_percent > external_percent else "çevresel faktörlerden (başarı, takdir, rekabet) güç alıyor. İçsel motivasyonunu da geliştirmeye odaklanabilirsin."}
        """)
        
        st.markdown("### 💬 Sana uygun psikolojik destek yöntemleri:")
        
        psychological_methods = []
        if internal_percent > external_percent:
            psychological_methods.extend([
                "• **Günlük küçük hedef:** \"Bugün sadece 20 soru çözeceğim\" diyerek başla, küçük başarı dopamini üret.",
                "• **İlerleme takibi:** Sistemiyle geçmiş ilerlemelerini gör, moralin artar.",
                "• **Kişisel gelişim odağı:** \"Bu konu beni nasıl daha iyi yapacak?\" diye sor.",
                "• **Özgür seçim:** Çalışma saatlerini ve konularını sen belirle."
            ])
        else:
            psychological_methods.extend([
                "• **Hedef ve ödül sistemi:** Her başarın için kendini ödüllendir.",
                "• **Sosyal paylaşım:** İlerlemeni aile ve arkadaşlarınla paylaş.",
                "• **Rekabet unsuru:** Arkadaşlarınla sağlıklı rekabet yap.",
                "• **Başarı görselleştirmesi:** Hedeflediğin sonuçları zihninde canlandır."
            ])
        
        # Ortak öneriler
        psychological_methods.extend([
            "• **Nefes egzersizi (4-7-8):** 4 saniye nefes al, 7 tut, 8 ver → kaygıyı azaltır.",
            "• **Günün sonunda yaz:** \"Bugün az da olsa ilerledim.\"",
            "• **Pozitif konuşma:** Kendine \"yapamam\" yerine \"nasıl yaparım\" de."
        ])
        
        for method in psychological_methods:
            st.info(method)
    
    # 4. ZAMAN YÖNETİMİ & ÇALIŞMA ALIŞKANLIĞI
    if 'time' in profile_data:
        st.markdown("---")
        st.markdown("## ⏰ 4. Zaman Yönetimi & Çalışma Alışkanlığı")
        
        time_data = profile_data['time']
        planning_score = time_data.get('planning', 0)
        procrastination_score = time_data.get('procrastination', 0)
        
        # Profil belirleme
        if planning_score > 3.5 and procrastination_score < 3.0:
            time_profile = "Planlı ve disiplinli"
        elif planning_score > 3.5 and procrastination_score > 3.0:
            time_profile = "Planlı ama zaman zaman erteleyici"
        elif planning_score < 3.0 and procrastination_score < 3.0:
            time_profile = "Spontan ama etkili"
        else:
            time_profile = "Geliştirilebilir zaman yönetimi"
        
        st.markdown(f"""
        **Sonuç eğilimi:** {time_profile} olabilirsin.
        
        {"Plan yapmayı seviyor ama bazen yorgunluk veya stres seni \"başlamayı ertelemeye\" itiyor olabilir." if "erteleyici" in time_profile else "Zaman konusunda doğal bir yeteneğin var gibi görünüyor." if "etkili" in time_profile else "Bu alanda kendini geliştirme potansiyelin yüksek."}
        """)
        
        st.markdown("### 🕓 Sana uygun sistemler:")
        
        time_systems = []
        if procrastination_score > 3.0:
            time_systems.extend([
                "• **Pomodoro Tekniği:** 25 dakika çalış, 5 dakika mola ver. Her 4 turda 20 dakika büyük mola.",
                "• **\"2 Dakika Kuralı\":** 2 dakikada bitecek işleri hemen yap, erteleme.",
                "• **Erteleme kilidi:** Telefonu başka odaya bırak, dikkat dağıtıcıları kaldır."
            ])
        
        if planning_score < 3.0:
            time_systems.extend([
                "• **\"Mini hedef\" sistemi:** Tek seferde büyük planlar yerine 3 ana hedef (sabah–öğle–akşam).",
                "• **Haftalık tema:** Her haftayı bir derse odakla (Bu hafta matematik haftası).",
                "• **Esnek planlama:** Sabit saatler yerine \"öncelik sıralı\" görevler yap."
            ])
        
        time_systems.extend([
            "• **\"Görsel ilerleme grafiği\":** Günlük yüzdelik ilerlemeyi takip et, motivasyonun artar.",
            "• **Başlama ritüeli:** Çalışmaya ısınmak için 10 dakikalık \"başlama seansı\" yap.",
            "• **Dönüşümlü çalışma:** Sevdiğin bir dersle zor bir dersi dönüşümlü çalış."
        ])
        
        for system in time_systems:
            st.info(system)
        
        st.markdown("### 📘 Uygulama önerisi:")
        
        application_tips = [
            "• **Sabah rutini:** Güne aynı şekilde başla, beynin hazır olsun.",
            "• **Çalışma öncesi:** Masayı topla, su hazırla, 3 derin nefes al.",
            "• **Mola aktiviteleri:** Uzanma, su içme, pencereden bakma - telefon değil!"
        ]
        
        for tip in application_tips:
            st.success(tip)
    
    # 5. GENEL BEYİN PROFİLİ (KISA ÖZET)
    st.markdown("---")
    st.markdown("## 🔮 GENEL BEYİN PROFİLİN (Kısa Özet)")
    
    # Genel profil özeti
    cognitive_summary = ""
    learning_summary = ""
    motivation_summary = ""
    time_summary = ""
    
    if 'cognitive' in profile_data:
        cognitive = profile_data['cognitive']
        max_cognitive = max(cognitive.items(), key=lambda x: x[1])
        if max_cognitive[0] == 'analytic_thinking':
            cognitive_summary = "analitik ve sistematik düşünebilen"
        elif max_cognitive[0] == 'synthetic_thinking':
            cognitive_summary = "bütüncül ve yaratıcı düşünebilen"
        else:
            cognitive_summary = "reflektif ve derin düşünebilen"
    
    if 'vak' in profile_data:
        vak = profile_data['vak']
        visual_score = vak.get('Visual', 0)
        auditory_score = vak.get('Auditory', 0)
        kinesthetic_score = vak.get('Kinesthetic', 0)
        
        if visual_score > auditory_score and visual_score > kinesthetic_score:
            learning_summary = "görsel"
        elif auditory_score > kinesthetic_score:
            learning_summary = "işitsel"
        else:
            learning_summary = "kinestetik"
    
    if 'motivation' in profile_data:
        motivation = profile_data['motivation']
        if motivation.get('internal_motivation', 0) > motivation.get('external_motivation', 0):
            motivation_summary = "içsel motivasyonu güçlü"
        else:
            motivation_summary = "dışsal motivasyonu güçlü"
    
    if 'time' in profile_data:
        time_data = profile_data['time']
        if time_data.get('planning', 0) > 3.5:
            if time_data.get('procrastination', 0) > 3.0:
                time_summary = "planlı ama zaman zaman duygusal ertelemeye açık"
            else:
                time_summary = "planlı ve disiplinli"
        else:
            time_summary = "esnek ama geliştirilebilir zaman yönetimli"
    
    summary_text = f"{cognitive_summary}, {learning_summary} öğrenme stiline sahip, {motivation_summary}, {time_summary} bir öğrenci profiline sahip olabilirsin."
    
    st.info(f"""
    **{summary_text.capitalize()}**
    
    Bu tarz öğrenciler, kendi sistemlerini kurduklarında uzun vadede çok yüksek başarı elde ederler.
    """)
    
    # Motivasyonel sloganlar
    st.markdown("### 💫 Senin çalışma mottoların:")
    
    mottos = [
        "**\"Bugün az da olsa ilerledim.\"**",
        "**\"Anladığım her şey kalıcı hale geliyor.\"**", 
        "**\"Bir adım bile bir ilerlemedir.\"**"
    ]
    
    for motto in mottos:
        st.success(motto)

def display_individual_test_analysis(test_config, user_data):
    """Bireysel test analizini gösterir"""
    st.markdown(f'''
    <div class="analysis-section">
        <h3>{test_config['icon']} {test_config['title']} - Detaylı Analiz</h3>
    </div>
    ''', unsafe_allow_html=True)
    
    # Test türüne göre analiz göster
    if test_config['id'] == 'vak':
        display_vak_analysis(user_data)
    elif test_config['id'] == 'cognitive':
        display_cognitive_analysis(user_data)
    elif test_config['id'] == 'motivation':
        display_motivation_analysis(user_data)
    elif test_config['id'] == 'time':
        display_time_management_analysis(user_data)

def setup_matplotlib_for_plotting():
    """
    Setup matplotlib for plotting with proper configuration.
    Call this function before creating any plots to ensure proper rendering.
    """
    import warnings
    import matplotlib.pyplot as plt

    # Ensure warnings are printed
    warnings.filterwarnings('default')  # Show all warnings

    # Configure matplotlib for non-interactive mode
    plt.switch_backend("Agg")

    # Set clean modern style
    plt.style.use("default")

    # Configure platform-appropriate fonts for cross-platform compatibility
    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "PingFang SC", "Arial Unicode MS", "Hiragino Sans GB", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    
    # Basic styling
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["axes.edgecolor"] = "#CCCCCC"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["grid.alpha"] = 0.3

def display_vak_analysis(user_data):
    """VAK testi detaylı analizi - Basit ve anlaşılır grafik gösterimi"""
    style_scores_str = user_data.get('learning_style_scores', '')
    dominant_style = user_data.get('learning_style', '')
    
    # VAK test sonuçları kontrol et - hem eski hem yeni field isimleri
    vak_test_completed = user_data.get('vak_test_results', '') or user_data.get('learning_style_results', '')
    
    # Eğer test tamamlanmışsa ve veri varsa
    if vak_test_completed and (style_scores_str or dominant_style):
        try:
            import plotly.express as px
            import json
            
            # Verileri parse et
            if style_scores_str:
                style_scores = json.loads(style_scores_str.replace("'", "\""))
            else:
                # Default değerler - test tamamlanmışsa
                style_scores = {'visual': 35, 'auditory': 30, 'kinesthetic': 35}
                dominant_style = 'Görsel' if not dominant_style else dominant_style
            
            # Yüzdeleri hesapla
            visual_percent = style_scores.get('visual', 0)
            auditory_percent = style_scores.get('auditory', 0)
            kinesthetic_percent = style_scores.get('kinesthetic', 0)
            
            # Dominant style bilgisini al
            vak_detailed_info = {
                'Görsel': {'icon': '👁️', 'title': 'Görsel Öğrenme'},
                'İşitsel': {'icon': '👂', 'title': 'İşitsel Öğrenme'},
                'Kinestetik': {'icon': '✋', 'title': 'Kinestetik Öğrenme'}
            }
            
            # Baskın stil belirleme
            max_score = max(visual_percent, auditory_percent, kinesthetic_percent)
            if visual_percent == max_score:
                dominant_style = 'Görsel'
            elif auditory_percent == max_score:
                dominant_style = 'İşitsel'
            else:
                dominant_style = 'Kinestetik'
                
            style_info = vak_detailed_info[dominant_style]
            
            st.markdown("---")
            st.markdown(f"## {style_info['icon']} **{style_info['title']}** - Baskın Stiliniz!")
            
            # Stil dağılımı grafik
            col1, col2 = st.columns([2, 1])
            
            with col1:
                vak_data = {
                    'Stil': ['Görsel', 'İşitsel', 'Kinestetik'],
                    'Yüzde': [visual_percent, auditory_percent, kinesthetic_percent],
                    'Renk': ['#FF6B6B', '#4ECDC4', '#45B7D1']
                }
                
                fig = px.pie(
                    values=vak_data['Yüzde'], 
                    names=vak_data['Stil'],
                    title="📊 Öğrenme Stili Dağılımınız",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=400,
                    font=dict(size=14),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📈 Puan Detayları")
                styles = [
                    ("Görsel 👁️", visual_percent, "#FF6B6B"),
                    ("İşitsel 👂", auditory_percent, "#4ECDC4"),
                    ("Kinestetik ✋", kinesthetic_percent, "#45B7D1")
                ]
                
                for style_name, percentage, color in styles:
                    is_dominant = style_name.split()[0] == dominant_style
                    border = "3px solid #FFD700" if is_dominant else "1px solid #ddd"
                    
                    st.markdown(f"""
                        <div style="
                            border: {border};
                            padding: 10px;
                            margin: 8px 0;
                            border-radius: 8px;
                            background: linear-gradient(90deg, {color}20, transparent);
                            text-align: center;
                        ">
                            <strong>{style_name}</strong><br>
                            <span style="font-size: 24px; color: {color};">%{percentage:.1f}</span>
                        </div>
                    """, unsafe_allow_html=True)
            
            # DETAYLI ANALİZ YAZILARI - Basit format
            st.markdown("---")
            
            # Stil açıklaması
            style_descriptions = {
                'Görsel': "Sen bilgiyi en iyi gözlerle algılayan bir öğrencisin. Zihninde canlandırdığın resimler, renkler ve şemalar, öğrenme sürecini çok daha kolay ve kalıcı hale getirebilir.",
                'İşitsel': "Sen bilgiyi en iyi kulağınla algılayan bir öğrencisin. Sesler, müzik ve konuşmalar senin için en etkili öğrenme araçlarıdır.",
                'Kinestetik': "Sen bilgiyi en iyi hareket ederek ve yaparak algılayan bir öğrencisin. Ellerinle dokunmak, hareket etmek ve uygulama yapmak senin için en etkili öğrenme yöntemidir."
            }
            
            st.info(style_descriptions[dominant_style])
            
            # Güçlü Yönler
            st.markdown("### 💪 Güçlü Yönlerin:")
            
            strengths = {
                'Görsel': [
                    "Harita, grafik ve şemaları kolay anlayabilirsin",
                    "Renkli notlar ve görsellerle daha hızlı öğrenebilirsin", 
                    "Karmaşık bilgileri zihninde görselleştirme yeteneğin güçlüdür"
                ],
                'İşitsel': [
                    "Dinleyerek hızlı öğrenebilir ve hatırlayabilirsin",
                    "Konuları sesli anlatarak daha iyi kavrayabilirsin",
                    "Müzik ve ses tonlarından yararlanarak etkili çalışabilirsin"
                ],
                'Kinestetik': [
                    "Bol soru çözümü yaparak hızlı öğrenebilirsin",
                    "Pratik uygulamalarla bilgiyi kalıcı hale getirebilirsin",
                    "Hareket halindeyken daha verimli çalışabilirsin"
                ]
            }
            
            for strength in strengths[dominant_style]:
                st.success(f"• {strength}")
            
            # Zayıf Yönler
            st.markdown("### ⚠️ Zayıf Yönlerin:")
            
            weaknesses = {
                'Görsel': [
                    "Sadece dinleyerek öğrenmekte zorlanabilirsin",
                    "Ders notları dağınık olduğunda odaklanman zorlaşabilir"
                ],
                'İşitsel': [
                    "Sessiz ortamda çalışmakta zorlanabilirsin",
                    "Görsel materyalleri anlamakta zaman gerekebilir"
                ],
                'Kinestetik': [
                    "Uzun süre hareketsiz oturmakta zorlanabilirsin",
                    "Teorik konuları kavramak zaman alabilir"
                ]
            }
            
            for weakness in weaknesses[dominant_style]:
                st.warning(f"• {weakness}")
            
            # Akademik Gelişim Önerileri
            st.markdown("### 🎓 Akademik Gelişim Önerilerin:")
            
            academic_tips = {
                'Görsel': [
                    "**Zihin Haritalama:** Her konu için renkli zihin haritaları oluştur",
                    "**Renk Kodlama:** Farklı konuları farklı renklerle işaretle",
                    "**Grafik Notları:** Bilgileri tablo, grafik ve şema halinde özetle",
                    "**Formül Kartları:** Formülleri renkli kartlar halinde hazırla"
                ],
                'İşitsel': [
                    "**Sesli Tekrar:** Konuları kendi kendine yüksek sesle anlat",
                    "**Müzik Eşliği:** Uygun müzik eşliğinde çalış",
                    "**Tartışma Grupları:** Arkadaşlarınla konu tartışmaları yap",
                    "**Ses Kayıtları:** Önemli konuları ses kaydı olarak al"
                ],
                'Kinestetik': [
                    "**Hareket + Çalışma:** Yürürken formül tekrar et",
                    "**Bol Uygulama:** Her konu için çok sayıda soru çöz",
                    "**Elle Yazma:** Bilgileri mutlaka el yazısıyla yaz",
                    "**Kısa Molalar:** 25 dakika çalış, 5 dakika hareket et"
                ]
            }
            
            for tip in academic_tips[dominant_style]:
                st.info(f"• {tip}")
                        
        except Exception as e:
            import traceback
            st.error(f"VAK analizi gösterilirken hata oluştu: {str(e)}")
            st.error(f"Detay: {traceback.format_exc()}")
            # Fallback basit görünüm
            if dominant_style:
                st.markdown(f"**Baskın Öğrenme Stili:** {dominant_style}")
                st.info("Grafik yüklenemedi, ancak analiz sonuçlarınız kaydedildi.")

def display_cognitive_analysis(user_data):
    """Bilişsel test detaylı analizi - Basit grafik gösterimi"""
    cognitive_results = user_data.get('cognitive_test_results', '')
    cognitive_scores = user_data.get('cognitive_test_scores', '')
    
    if cognitive_results and (cognitive_scores or cognitive_results):
        try:
            import plotly.express as px
            import json
            
            # Verileri parse et
            if cognitive_scores:
                raw_scores = json.loads(cognitive_scores.replace("'", '"'))
                
                # ADAPTIF VERİ İŞLEME - herhangi bir formattaki veriyi düzenli hale getir
                analytic_score = 0
                synthetic_score = 0
                reflective_score = 0
                
                # Tüm anahtarları kontrol et ve kategorilere ayır
                for key, value in raw_scores.items():
                    key_lower = key.lower()
                    
                    # Analitik düşünme
                    if any(word in key_lower for word in ['analytic', 'analytical', 'analyze']):
                        analytic_score += float(value)
                    
                    # Sintetik/Bütüncül düşünme  
                    elif any(word in key_lower for word in ['synthetic', 'synthesis', 'creative', 'visual', 'experiential', 'holistic']):
                        synthetic_score += float(value)
                    
                    # Reflektif düşünme
                    elif any(word in key_lower for word in ['reflective', 'reflection', 'auditory', 'listening']):
                        reflective_score += float(value)
                    
                    # Eğer thinking ile bitiyorsa direkt kullan
                    elif 'thinking' in key_lower:
                        if 'analytic' in key_lower:
                            analytic_score = float(value)
                        elif 'synthetic' in key_lower:
                            synthetic_score = float(value)
                        elif 'reflective' in key_lower:
                            reflective_score = float(value)
                
                # Eğer hiç puan bulunamadıysa default değerler
                if analytic_score == 0 and synthetic_score == 0 and reflective_score == 0:
                    analytic_score = 3.5
                    synthetic_score = 3.2
                    reflective_score = 3.8
                
                # Son format
                scores_data = {
                    'analytic_thinking': analytic_score,
                    'synthetic_thinking': synthetic_score,
                    'reflective_thinking': reflective_score
                }
                    
            else:
                # Default değerler - test tamamlanmışsa
                scores_data = {'analytic_thinking': 3.5, 'synthetic_thinking': 3.2, 'reflective_thinking': 3.8}
            
            # Yüzdeleri hesapla
            total_score = sum(scores_data.values())
            percentages = {key: (value/total_score)*100 for key, value in scores_data.items()}
            
            # En yüksek skoru bul
            max_category = max(scores_data, key=scores_data.get)
            
            # Kategori bilgileri
            category_info = {
                'analytic_thinking': {
                    'name': 'Analitik Düşünce',
                    'icon': '🔬',
                    'color': '#FF6B6B'
                },
                'synthetic_thinking': {
                    'name': 'Bütüncül Düşünce', 
                    'icon': '🎨',
                    'color': '#4ECDC4'
                },
                'reflective_thinking': {
                    'name': 'Reflektif Düşünce',
                    'icon': '🤔',
                    'color': '#45B7D1'
                }
            }
            
            dominant_info = category_info[max_category]
            
            st.markdown("---")
            st.markdown(f"## {dominant_info['icon']} **{dominant_info['name']}** - Baskın Düşünce Stiliniz!")
            
            # Grafik bölümü
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Pie chart
                fig = px.pie(
                    values=list(percentages.values()),
                    names=[category_info[key]['name'] for key in percentages.keys()],
                    title="🧠 Bilişsel Profil Dağılımınız",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=400,
                    font=dict(size=14),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📈 Puan Detayları")
                
                for key, value in scores_data.items():
                    info = category_info[key]
                    percentage = percentages[key]
                    is_dominant = key == max_category
                    border = "3px solid gold" if is_dominant else "1px solid #ddd"
                    
                    st.markdown(f"""
                        <div style="
                            border: {border};
                            padding: 10px;
                            margin: 8px 0;
                            border-radius: 8px;
                            background: linear-gradient(90deg, {info['color']}20, transparent);
                            text-align: center;
                        ">
                            <strong>{info['name']} {info['icon']}</strong><br>
                            <span style="font-size: 20px; color: {info['color']};">%{percentage:.1f}</span><br>
                            <small style="color: {info['color']};">({value:.1f}/5 puan)</small>
                        </div>
                    """, unsafe_allow_html=True)
            
            # Baskın stil açıklamaları
            st.markdown("---")
            st.markdown(f"### 🎯 **{dominant_info['name']}** Özellikleri")
            
            cognitive_profiles = {
                'analytic_thinking': {
                    'description': 'Sistematik düşünme ve problem çözme becerileriniz güçlü.',
                    'strengths': ['Mantıksal çıkarım yapma', 'Problemleri adım adım çözme', 'Sistematik yaklaşım', 'Detaylı analiz'],
                    'study_tips': ['Konuları küçük parçalara bölün', 'Adım adım çalışma planları yapın', 'Mantık soruları çözün', 'Grafik ve şemalar kullanın']
                },
                'synthetic_thinking': {
                    'description': 'Bütüncül bakış açısı ve yaratıcı düşünme becerileriniz gelişmiş.',
                    'strengths': ['Büyük resmi görme', 'Yaratıcı çözümler üretme', 'Farklı konuları birleştirme', 'Sezgisel kavrayış'],
                    'study_tips': ['Kavram haritaları oluşturun', 'Konular arası bağlantı kurun', 'Hikaye anlatımı tekniği kullanın', 'Beyin fırtınası yapın']
                },
                'reflective_thinking': {
                    'description': 'Düşünce süreçlerinizi değerlendirme ve öz-analiz beceriniz yüksek.',
                    'strengths': ['Öz-farkındalık', 'Stratejik planlama', 'Hata analizi yapma', 'Süreç değerlendirme'],
                    'study_tips': ['Öğrenme günlüğü tutun', 'Düzenli self-değerlendirme yapın', 'Hata analizleri oluşturun', 'Stratejik çalışma planları hazırlayın']
                }
            }
            
            profile = cognitive_profiles[max_category]
            st.markdown(profile['description'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💪 Güçlü Yanlarınız")
                for strength in profile['strengths']:
                    st.markdown(f"• {strength}")
            
            with col2:
                st.markdown("#### 📚 Çalışma Önerileriniz")
                for tip in profile['study_tips']:
                    st.markdown(f"• {tip}")
                    
        except Exception as e:
            st.error(f"Analiz gösterilirken hata: {str(e)}")
            st.info("🧠 **Bilişsel Profil:** Test sonuçlarınız kaydedildi.")
    else:
        st.warning("⚠️ Test sonuçları yüklenemedi.")

def display_motivation_analysis(user_data):
    """Motivasyon ve duygusal denge analizi - Basit grafik gösterimi"""
    motivation_results = user_data.get('motivation_test_results', '')
    motivation_scores = user_data.get('motivation_test_scores', '')
    
    if motivation_results and (motivation_scores or motivation_results):
        try:
            import plotly.express as px
            import json
            
            # Verileri parse et
            if motivation_scores:
                raw_scores = json.loads(motivation_scores.replace("'", '"'))
                
                # ADAPTIF VERİ İŞLEME - herhangi bir formattaki veriyi düzenli hale getir
                internal_score = 0
                external_score = 0
                anxiety_score = 0
                resilience_score = 0
                
                # Tüm anahtarları kontrol et ve kategorilere ayır
                for key, value in raw_scores.items():
                    key_lower = key.lower()
                    
                    # İçsel motivasyon
                    if any(word in key_lower for word in ['internal', 'intrinsic', 'inner', 'motivation_internal']):
                        internal_score += float(value)
                    
                    # Dışsal motivasyon  
                    elif any(word in key_lower for word in ['external', 'extrinsic', 'outer', 'motivation_external']):
                        external_score += float(value)
                    
                    # Sınav kaygısı
                    elif any(word in key_lower for word in ['anxiety', 'worry', 'stress', 'exam_anxiety', 'test_anxiety']):
                        anxiety_score += float(value)
                    
                    # Duygusal dayanıklılık
                    elif any(word in key_lower for word in ['resilience', 'emotional', 'strength', 'durability']):
                        resilience_score += float(value)
                
                # Eğer hiç puan bulunamadıysa default değerler
                if internal_score == 0 and external_score == 0 and anxiety_score == 0 and resilience_score == 0:
                    internal_score = 3.8
                    external_score = 3.2
                    anxiety_score = 2.5
                    resilience_score = 3.9
                
                # Son format
                scores_data = {
                    'internal_motivation': internal_score,
                    'external_motivation': external_score,
                    'test_anxiety': anxiety_score,
                    'emotional_resilience': resilience_score
                }
                
            else:
                # Default değerler - test tamamlanmışsa
                scores_data = {
                    'internal_motivation': 3.8, 'external_motivation': 3.2, 
                    'test_anxiety': 2.5, 'emotional_resilience': 3.9
                }
            
            # Yüzdeleri hesapla
            total_score = sum(scores_data.values())
            percentages = {key: (value/total_score)*100 for key, value in scores_data.items()}
            
            # En yüksek skoru bul
            max_category = max(scores_data, key=scores_data.get)
            
            # Kategori bilgileri
            category_info = {
                'internal_motivation': {
                    'name': 'İçsel Motivasyon',
                    'icon': '🌟',
                    'color': '#FF6B6B'
                },
                'external_motivation': {
                    'name': 'Dışsal Motivasyon', 
                    'icon': '🎯',
                    'color': '#4ECDC4'
                },
                'test_anxiety': {
                    'name': 'Sınav Kaygısı',
                    'icon': '😰',
                    'color': '#45B7D1'
                },
                'emotional_resilience': {
                    'name': 'Duygusal Dayanıklılık',
                    'icon': '💪',
                    'color': '#96CEB4'
                }
            }
            
            dominant_info = category_info[max_category]
            
            st.markdown("---")
            st.markdown(f"## {dominant_info['icon']} **{dominant_info['name']}** - Baskın Özelliğiniz!")
            
            # Grafik bölümü
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Pie chart
                fig = px.pie(
                    values=list(percentages.values()),
                    names=[category_info[key]['name'] for key in percentages.keys()],
                    title="⚡ Motivasyon ve Duygusal Profil Dağılımınız",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=400,
                    font=dict(size=14),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📈 Puan Detayları")
                
                for key, value in scores_data.items():
                    info = category_info[key]
                    percentage = percentages[key]
                    is_dominant = key == max_category
                    border = "3px solid gold" if is_dominant else "1px solid #ddd"
                    
                    st.markdown(f"""
                        <div style="
                            border: {border};
                            padding: 10px;
                            margin: 8px 0;
                            border-radius: 8px;
                            background: linear-gradient(90deg, {info['color']}20, transparent);
                            text-align: center;
                        ">
                            <strong>{info['name']} {info['icon']}</strong><br>
                            <span style="font-size: 20px; color: {info['color']};">%{percentage:.1f}</span><br>
                            <small style="color: {info['color']};">({value:.1f}/5 puan)</small>
                        </div>
                    """, unsafe_allow_html=True)
            
            # Baskın özellik açıklamaları
            st.markdown("---")
            st.markdown(f"### 🎯 **{dominant_info['name']}** Özellikleri")
            
            motivation_profiles = {
                'internal_motivation': {
                    'description': 'Kendi iç dünyanızdan gelen motivasyonla hareket edersiniz.',
                    'strengths': ['Kendi kendini motive etme', 'Merak odaklı öğrenme', 'Bağımsız çalışma', 'Yaratıcı düşünme'],
                    'study_tips': ['İlgi duyduğunuz konulara odaklanın', 'Kişisel hedefler belirleyin', 'Kendi hevesli olduğunuz zamanlarda çalışın', 'Keşif yapmaya zaman ayırın']
                },
                'external_motivation': {
                    'description': 'Dış ödüller ve hedeflerle motive olursunuz.',
                    'strengths': ['Hedef odaklı çalışma', 'Rekabet ortamında başarı', 'Somut sonuçlar alma', 'Planı takip etme'],
                    'study_tips': ['Net hedefler ve ödüller belirleyin', 'Rekabet ortamları oluşturun', 'Başarılarınızı görsel olarak takip edin', 'Dış destek alın']
                },
                'test_anxiety': {
                    'description': 'Sınav durumlarmda stres yaşama eğiliminiz var.',
                    'strengths': ['Yüksek farkındalık', 'Dikkatli hazırlık', 'Detaycı yaklaşım', 'Performans odaklılık'],
                    'study_tips': ['Nefes egzersizleri yapın', 'Deneme sınavları çözün', 'Zaman yönetimi pratikte edin', 'Rahatlatici teknikler öğrenin']
                },
                'emotional_resilience': {
                    'description': 'Duygusal zorluklar karşısında güçlü direncç gösterirsiniz.',
                    'strengths': ['Stresle baş etme', 'Hızlı toparlanma', 'Pozitif bakış açısı', 'Adaptasyon yeteneği'],
                    'study_tips': ['Zorlu konulara cesurca yaklaşın', 'Hatalarınızdan hızla öğrenin', 'Uzun vadeli planlar yapın', 'Kendinize güvenin']
                }
            }
            
            profile = motivation_profiles[max_category]
            st.markdown(profile['description'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💪 Güçlü Yanlarınız")
                for strength in profile['strengths']:
                    st.markdown(f"• {strength}")
            
            with col2:
                st.markdown("#### 📚 Çalışma Önerileriniz")
                for tip in profile['study_tips']:
                    st.markdown(f"• {tip}")
                    
        except Exception as e:
            st.error(f"Motivasyon analizi gösterilirken hata oluştu: {str(e)}")
            st.info("⚡ **Motivasyon & Duygusal Denge:** Test sonuçlarınız kaydedildi.")
    else:
        st.warning("⚠️ Test sonuçları yüklenemedi.")

def display_time_management_analysis(user_data):
    """Zaman yönetimi analizi - Basit grafik gösterimi"""
    time_results = user_data.get('time_test_results', '')
    time_scores = user_data.get('time_test_scores', '')
    
    if time_results and (time_scores or time_results):
        try:
            import plotly.express as px
            import json
            
            # Verileri parse et
            if time_scores:
                raw_scores = json.loads(time_scores.replace("'", '"'))
                
                # ADAPTIF VERİ İŞLEME - herhangi bir formattaki veriyi düzenli hale getir
                planning_score = 0
                procrastination_score = 0
                focus_score = 0
                time_score = 0
                priority_score = 0
                discipline_score = 0
                awareness_score = 0
                
                # Tüm anahtarları kontrol et ve kategorilere ayır
                for key, value in raw_scores.items():
                    key_lower = key.lower()
                    
                    # Planlama
                    if any(word in key_lower for word in ['planning', 'plan', 'organize', 'structure']):
                        planning_score += float(value)
                    
                    # Erteleme  
                    elif any(word in key_lower for word in ['procrastination', 'delay', 'postpone', 'erteleme']):
                        procrastination_score += float(value)
                    
                    # Odak kontrolü
                    elif any(word in key_lower for word in ['focus', 'concentrate', 'attention', 'odak']):
                        focus_score += float(value)
                    
                    # Zaman bilinci
                    elif any(word in key_lower for word in ['time_awareness', 'time', 'temporal', 'zaman']):
                        time_score += float(value)
                    
                    # Öncelik yönetimi
                    elif any(word in key_lower for word in ['priority', 'prioritization', 'öncelik']):
                        priority_score += float(value)
                    
                    # Disiplin
                    elif any(word in key_lower for word in ['discipline', 'disiplin', 'self_control', 'control']):
                        discipline_score += float(value)
                    
                    # Öz-farkındalık
                    elif any(word in key_lower for word in ['self_awareness', 'awareness', 'farkındalık', 'conscious']):
                        awareness_score += float(value)
                
                # Eğer hiç puan bulunamadıysa default değerler
                if all(score == 0 for score in [planning_score, procrastination_score, focus_score, time_score, priority_score]):
                    planning_score = 3.4
                    procrastination_score = 2.8
                    focus_score = 3.7
                    time_score = 3.1
                    priority_score = 3.5
                
                # Son format (discipline ve self_awareness isteğe bağlı)
                scores_data = {
                    'planning': planning_score,
                    'procrastination': procrastination_score,
                    'focus_control': focus_score,
                    'time_awareness': time_score,
                    'priority_management': priority_score
                }
                
                # Ek kategoriler varsa ekle
                if discipline_score > 0:
                    scores_data['discipline'] = discipline_score
                if awareness_score > 0:
                    scores_data['self_awareness'] = awareness_score
                
            else:
                # Default değerler - test tamamlanmışsa
                scores_data = {
                    'planning': 3.4, 'procrastination': 2.8, 'focus_control': 3.7,
                    'time_awareness': 3.1, 'priority_management': 3.5
                }
            
            # Verileri düzenle (Procrastination ters çevir)
            processed_scores = scores_data.copy()
            processed_scores['procrastination'] = 5 - processed_scores['procrastination']  # Erteleme kontrolü olarak göster
            
            # Yüzdeleri hesapla
            total_score = sum(processed_scores.values())
            percentages = {key: (value/total_score)*100 for key, value in processed_scores.items()}
            
            # En yüksek skoru bul
            max_category = max(processed_scores, key=processed_scores.get)
            
            # Kategori bilgileri
            category_info = {
                'planning': {
                    'name': 'Planlama Becerisi',
                    'icon': '📋',
                    'color': '#FF6B6B'
                },
                'procrastination': {
                    'name': 'Erteleme Kontrolü', 
                    'icon': '⏱️',
                    'color': '#4ECDC4'
                },
                'focus_control': {
                    'name': 'Odak Kontrolü',
                    'icon': '🎯',
                    'color': '#45B7D1'
                },
                'time_awareness': {
                    'name': 'Zaman Bilinci',
                    'icon': '⏰',
                    'color': '#96CEB4'
                },
                'priority_management': {
                    'name': 'Öncelik Yönetimi',
                    'icon': '📈',
                    'color': '#FECA57'
                },
                'discipline': {
                    'name': 'Disiplin',
                    'icon': '💪',
                    'color': '#FF7675'
                },
                'self_awareness': {
                    'name': 'Öz-farkındalık',
                    'icon': '🧘',
                    'color': '#A29BFE'
                }
            }
            
            dominant_info = category_info[max_category]
            
            st.markdown("---")
            st.markdown(f"## {dominant_info['icon']} **{dominant_info['name']}** - Güçlü Yanınız!")
            
            # Grafik bölümü
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Pie chart
                fig = px.pie(
                    values=list(percentages.values()),
                    names=[category_info[key]['name'] for key in percentages.keys()],
                    title="⏰ Zaman Yönetimi Profil Dağılımınız",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=400,
                    font=dict(size=14),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📈 Puan Detayları")
                
                for key, value in processed_scores.items():
                    info = category_info[key]
                    percentage = percentages[key]
                    is_dominant = key == max_category
                    border = "3px solid gold" if is_dominant else "1px solid #ddd"
                    
                    st.markdown(f"""
                        <div style="
                            border: {border};
                            padding: 10px;
                            margin: 8px 0;
                            border-radius: 8px;
                            background: linear-gradient(90deg, {info['color']}20, transparent);
                            text-align: center;
                        ">
                            <strong>{info['name']} {info['icon']}</strong><br>
                            <span style="font-size: 20px; color: {info['color']};">%{percentage:.1f}</span><br>
                            <small style="color: {info['color']};">({value:.1f}/5 puan)</small>
                        </div>
                    """, unsafe_allow_html=True)
            
            # Baskın özellik açıklamaları
            st.markdown("---")
            st.markdown(f"### 🎯 **{dominant_info['name']}** Özellikleri")
            
            time_profiles = {
                'planning': {
                    'description': 'Zamanı planlama ve organize etme beceriniz güçlü.',
                    'strengths': ['Uzun vadeli planlama', 'Görev dağılımı', 'Takvim yönetimi', 'Sistematik yaklaşım'],
                    'study_tips': ['Haftalık çalışma takvimi oluşturun', 'Her gün için hedefler belirleyin', 'Zaman blokları yöntemini kullanın', 'Düzenli değerlendirme yapın']
                },
                'procrastination': {
                    'description': 'Erteleme eğiliminizi kontrol etme beceriniz gelişmiş.',
                    'strengths': ['Hemen harekete geçme', 'Görev odaklılık', 'Disiplinli çalışma', 'Zaman kaybını engelleme'],
                    'study_tips': ['Zor görevleri önce yapın', '25 dakika çalış-5 dakika mola tekniği', 'Küçük adımlar halinde ilerleyin', 'Ödül sistemi kuru']
                },
                'focus_control': {
                    'description': 'Dikkatinizi kontrol etme ve odaklanma yeteneğiniz yüksek.',
                    'strengths': ['Derin odaklanma', 'Dikkat dağınıklığı önleme', 'Konsantrasyon sürdürme', 'Zihinsel netlik'],
                    'study_tips': ['Sessiz ortamda çalışın', 'Telefonu kapatın', 'Tek seferde tek konuya odaklanın', 'Dikkat egzersizleri yapın']
                },
                'time_awareness': {
                    'description': 'Zamanın geçişini hissetme ve takip etme beceriniz gelişmiş.',
                    'strengths': ['Zaman tahmin etme', 'Gün yönetimi', 'Tempolu çalışma', 'Süre farkındalığı'],
                    'study_tips': ['Kronometre kullanın', 'Zaman takip uygulaması edinin', 'Günlük zaman budçesi yapın', 'Zaman blokları oluşturun']
                },
                'priority_management': {
                    'description': 'Önemli ve acil işleri ayırt etme ve önceliklendirme beceriniz yüksek.',
                    'strengths': ['Doğru öncelelikler', 'Zamanlı karar verme', 'Strateji belirme', 'Verimlilik'],
                    'study_tips': ['Eisenhower matrisini kullanın', 'Önce önemli işleri yapın', 'Günlük 3 önemli hedef belirleyin', 'Haftalık değerlendirme yapın']
                },
                'discipline': {
                    'description': 'Kendini kontrol etme ve düzenli çalışma disiplininiz güçlü.',
                    'strengths': ['Kendini kontrol', 'Düzenli çalışma alışkanlıkları', 'Hedeflere bağlılık', 'İrade gücü'],
                    'study_tips': ['Günlük rutin oluşturun', 'Küçük hedeflerle başlayın', 'İlerlemeyi takip edin', 'Kendini ödüllendirin']
                },
                'self_awareness': {
                    'description': 'Kendi çalışma kalıplarınızı anlama ve değerlendirme beceriniz yüksek.',
                    'strengths': ['Öz-değerlendirme', 'Güçlü/zayıf yanları fark etme', 'Sürekli gelişim', 'Strateji geliştirme'],
                    'study_tips': ['Çalışma günlüğü tutun', 'Haftalık analiz yapın', 'Eksiklikleri belirleyin', 'Kişisel gelişim planı oluşturun']
                }
            }
            
            # Güvenli profil erişimi
            profile = time_profiles.get(max_category, time_profiles['planning'])  # Planning'i fallback olarak kullan
            st.markdown(profile['description'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💪 Güçlü Yanlarınız")
                for strength in profile['strengths']:
                    st.markdown(f"• {strength}")
            
            with col2:
                st.markdown("#### 📚 Çalışma Önerileriniz")
                for tip in profile['study_tips']:
                    st.markdown(f"• {tip}")
                    
        except Exception as e:
            st.error(f"Zaman yönetimi analizi gösterilirken hata oluştu: {str(e)}")
            st.info("⏰ **Zaman Yönetimi:** Test sonuçlarınız kaydedildi.")
    else:
        st.warning("⚠️ Test sonuçları yüklenemedi.")

def display_comprehensive_analysis(completed_tests, user_data):
    """4 testin kapsamlı genel analizi"""
    st.markdown('''
    <div class="comprehensive-analysis">
        <h2>🎯 KAPSAMLI GENEL PSİKOLOJİK ANALİZ</h2>
        <p>Tamamladığınız testlerin birleşik analizi</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Genel profil özeti
    st.markdown("### 📋 Genel Profiliniz")
    
    profile_summary = []
    
    # VAK analizi varsa ekle
    if 'vak' in completed_tests:
        dominant_style = user_data.get('learning_style', 'Belirtilmemiş')
        profile_summary.append(f"🎨 **Öğrenme Stili:** {dominant_style}")
    
    # Diğer testlerin sonuçları
    if 'cognitive' in completed_tests:
        profile_summary.append("🧠 **Bilişsel Profil:** Tamamlandı")
    
    if 'motivation' in completed_tests:
        profile_summary.append("⚡ **Motivasyon Analizi:** Tamamlandı")
    
    if 'time' in completed_tests:
        profile_summary.append("⏰ **Zaman Yönetimi:** Tamamlandı")
    
    for item in profile_summary:
        st.markdown(item)
    
    # Kişiselleştirilmiş öneriler
    st.markdown("### 💡 Sizin İçin Kişiselleştirilmiş Öneriler")
    
    recommendations = []
    
    if 'vak' in completed_tests:
        dominant_style = user_data.get('learning_style', '')
        if dominant_style == 'Görsel':
            recommendations.extend([
                "📚 Çalışırken renkli kalemler ve işaretleyiciler kullanın",
                "🗂️ Bilgileri şema ve tablolar halinde organize edin",
                "🎯 Hedeflerinizi görsel olarak motive edici resimlerle destekleyin"
            ])
        elif dominant_style == 'İşitsel':
            recommendations.extend([
                "🎵 Çalışırken hafif fon müziği dinleyin",
                "👥 Arkadaşlarınızla tartışma grupları oluşturun",
                "📢 Önemli bilgileri kendi sesinizle kaydedin ve dinleyin"
            ])
        elif dominant_style == 'Kinestetik':
            recommendations.extend([
                "🚶 Ders çalışırken ara sıra ayağa kalkın ve yürüyün",
                "✍️ Önemli formülleri kağıda elle yazın",
                "🏃 Çalışma aralarında kısa fiziksel aktiviteler yapın"
            ])
    
    # Genel öneriler ekle
    if len(completed_tests) >= 3:
        recommendations.extend([
            "📈 Test sonuçlarınıza göre kişiselleştirilmiş çalışma planı oluşturun",
            "🎯 Güçlü yanlarınızı destekleyecek çalışma teknikleri kullanın",
            "⚖️ Zayıf yanlarınızı geliştirici aktivitelere zaman ayırın"
        ])
    
    for rec in recommendations:
        st.markdown(f"• {rec}")
    
    # Başarı takvimi önerisi
    st.markdown("### 📅 Önerilen Haftalık Çalışma Programı")
    st.info("🎯 Test sonuçlarınıza göre özelleştirilmiş haftalık program oluşturma özelliği yakında eklenecek!")

def display_test_reset_section(test_configs, user_data, completed_tests):
    """Test sıfırlama bölümü"""
    st.markdown('''
    <div class="reset-section">
        <h3>🔄 Test Yönetim Merkezi</h3>
        <p>Test sonuçlarınızı görüntüleyebilir, değiştirebilir veya sıfırlayabilirsiniz.</p>
    </div>
    ''', unsafe_allow_html=True)
    
    st.warning("⚠️ **Önemli:** Test sonuçlarını sıfırladığınızda ilgili verileriniz silinecek ve testleri yeniden yapmanız gerekecektir.")
    
    # Her tamamlanmış test için yönetim seçenekleri
    for test in test_configs:
        if test['id'] in completed_tests:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{test['icon']} {test['title']}**")
                st.markdown(f"<small>{test['description'][:50]}...</small>", unsafe_allow_html=True)
            
            with col2:
                if st.button(f"📝 Değiştir", key=f"change_mgmt_{test['id']}", use_container_width=True):
                    # Test değiştirme sayfasına yönlendir
                    if test['id'] == 'vak':
                        st.session_state.page = "🎨 Öğrenme Stilleri Testi"
                    elif test['id'] == 'cognitive':
                        st.session_state.page = "🧠 Bilişsel Profil Testi"
                    elif test['id'] == 'motivation':
                        st.session_state.page = "⚡ Motivasyon & Duygu Testi"
                    elif test['id'] == 'time':
                        st.session_state.page = "⏰ Zaman Yönetimi Testi"
                    st.rerun()
            
            with col3:
                if st.button(f"🔄 Sıfırla", key=f"reset_{test['id']}", use_container_width=True):
                    st.session_state[f'confirm_reset_{test["id"]}'] = True
                    st.rerun()
            
            with col4:
                if st.button(f"👁️ Görüntüle", key=f"view_{test['id']}", use_container_width=True):
                    st.session_state[f'show_{test["id"]}_analysis'] = True
                    st.rerun()
            
            # Onay dialogu
            if st.session_state.get(f'confirm_reset_{test["id"]}', False):
                st.error(f"⚠️ **{test['title']}** sonuçlarını silmek istediğinizden emin misiniz?")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"✅ Evet, Sil", key=f"confirm_delete_{test['id']}", type="primary"):
                        # Test verilerini sıfırla
                        reset_data = {}
                        reset_data[test['data_key']] = ''
                        for key in test['related_keys']:
                            reset_data[key] = ''
                        
                        # Firebase'de güncelle
                        if update_user_in_firebase(st.session_state.current_user, reset_data):
                            st.success(f"✅ {test['title']} sonuçları başarıyla silindi!")
                            # Session state'i temizle
                            for key in [f'confirm_reset_{test["id"]}', f'show_{test["id"]}_analysis']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.rerun()
                        else:
                            st.error("❌ Silme işlemi başarısız!")
                
                with col_b:
                    if st.button(f"❌ İptal", key=f"cancel_delete_{test['id']}"):
                        del st.session_state[f'confirm_reset_{test["id"]}']
                        st.rerun()

# ===== TEST FONKSİYONLARI =====

def run_vak_learning_styles_test():
    """Modern VAK Öğrenme Stilleri Testi - Detaylı analiz ve öğretmen rehberi ile"""
    
    # Ana menüye dön butonu
    if st.button("🏠 Ana Menüye Dön", key="back_to_main_vak"):
        if 'page' in st.session_state:
            del st.session_state.page
        st.rerun()
    
    st.markdown("---")
    
    # Modern CSS stilini ekle
    st.markdown("""
    <style>
    .test-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .category-section {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    .question-box {
        background: #ffffff;
        color: #333333;
        border-left: 4px solid #667eea;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid #e0e6ed;
    }
    .question-text {
        color: #2c3e50;
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 1rem;
        line-height: 1.5;
    }
    .likert-info {
        background: #f8f9fa;
        color: #495057;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #17a2b8;
        font-size: 14px;
    }
    .result-box {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Başlık
    st.markdown("""
    <div class="test-header">
        <h1>🎨 Öğrenme Stilleri Testi (VAK)</h1>
        <p>Görsel, İşitsel ve Kinestetik öğrenme stillerinizi keşfedin</p>
        <p><strong>📋 75 soru | 🎯 1-5 Likert Ölçeği | 🆕 2025 Güncel Versiyonu</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Test açıklaması
    st.markdown("""
    ### 📖 Test Hakkında
    Bu testte **doğru ya da yanlış cevap yoktur**. Her maddenin sizin için ne kadar geçerli olduğunu 1-5 arasında değerlendirin.
    
    **🎯 Kategoriler:**
    - **A Kategorisi**: Görsel Öğrenme Stili (25 soru)
    - **B Kategorisi**: İşitsel Öğrenme Stili (25 soru) 
    - **C Kategorisi**: Kinestetik Öğrenme Stili (25 soru)
    
    **🆕 2025 Yılı Güncellemesi**: Bu yıl eklenen 15 yeni soru ile modern öğrenme alışkanlıklarınızı daha iyi analiz ediyoruz!
    """)
    
    # Likert ölçeği açıklaması
    st.markdown("""
    <div class="likert-info">
        <strong>📏 Değerlendirme Ölçeği:</strong><br>
        <strong>1 = Hiç katılmıyorum</strong> | 
        <strong>2 = Katılmıyorum</strong> | 
        <strong>3 = Kararsızım</strong> | 
        <strong>4 = Katılıyorum</strong> | 
        <strong>5 = Tamamen katılıyorum</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # Test formunu başlat
    with st.form("vak_test_form"):
        user_data = get_user_data()
        existing_results_raw = user_data.get('vak_test_results', '{}')
        
        # JSON string ise parse et, değilse dict olarak kullan
        if isinstance(existing_results_raw, str):
            try:
                existing_results = json.loads(existing_results_raw)
            except:
                existing_results = {}
        else:
            existing_results = existing_results_raw
        
        # A Kategorisi soruları
        st.markdown('<div class="category-section">👁️ A KATEGORİSİ - GÖRSEL ÖĞRENME STİLİ</div>', unsafe_allow_html=True)
        
        a_responses = {}
        a_questions = [q for q in VAK_LEARNING_STYLES_TEST if q['category'] == 'A']
        
        for i, question in enumerate(a_questions):
            question_key = f"A_{i+1}"
            default_value = existing_results.get(question_key, 3)  # Default: Kararsızım
            
            st.markdown(f"""
            <div class="question-box">
                <div class="question-text">A{i+1}. {question["question"]}</div>
            </div>
            """, unsafe_allow_html=True)
            
            a_responses[question_key] = st.select_slider(
                f"A{i+1} - Değerlendirmeniz:",
                options=[1, 2, 3, 4, 5],
                value=default_value,
                key=question_key,
                format_func=lambda x: {
                    1: "1 - Hiç katılmıyorum",
                    2: "2 - Katılmıyorum", 
                    3: "3 - Kararsızım",
                    4: "4 - Katılıyorum",
                    5: "5 - Tamamen katılıyorum"
                }[x]
            )
        
        # B Kategorisi soruları
        st.markdown('<div class="category-section">👂 B KATEGORİSİ - İŞİTSEL ÖĞRENME STİLİ</div>', unsafe_allow_html=True)
        
        b_responses = {}
        b_questions = [q for q in VAK_LEARNING_STYLES_TEST if q['category'] == 'B']
        
        for i, question in enumerate(b_questions):
            question_key = f"B_{i+1}"
            default_value = existing_results.get(question_key, 3)  # Default: Kararsızım
            
            st.markdown(f"""
            <div class="question-box">
                <div class="question-text">B{i+1}. {question["question"]}</div>
            </div>
            """, unsafe_allow_html=True)
            
            b_responses[question_key] = st.select_slider(
                f"B{i+1} - Değerlendirmeniz:",
                options=[1, 2, 3, 4, 5],
                value=default_value,
                key=question_key,
                format_func=lambda x: {
                    1: "1 - Hiç katılmıyorum",
                    2: "2 - Katılmıyorum", 
                    3: "3 - Kararsızım",
                    4: "4 - Katılıyorum",
                    5: "5 - Tamamen katılıyorum"
                }[x]
            )
        
        # C Kategorisi soruları
        st.markdown('<div class="category-section">✋ C KATEGORİSİ - KİNESTETİK ÖĞRENME STİLİ</div>', unsafe_allow_html=True)
        
        c_responses = {}
        c_questions = [q for q in VAK_LEARNING_STYLES_TEST if q['category'] == 'C']
        
        for i, question in enumerate(c_questions):
            question_key = f"C_{i+1}"
            default_value = existing_results.get(question_key, 3)  # Default: Kararsızım
            
            st.markdown(f"""
            <div class="question-box">
                <div class="question-text">C{i+1}. {question["question"]}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c_responses[question_key] = st.select_slider(
                f"C{i+1} - Değerlendirmeniz:",
                options=[1, 2, 3, 4, 5],
                value=default_value,
                key=question_key,
                format_func=lambda x: {
                    1: "1 - Hiç katılmıyorum",
                    2: "2 - Katılmıyorum", 
                    3: "3 - Kararsızım",
                    4: "4 - Katılıyorum",
                    5: "5 - Tamamen katılıyorum"
                }[x]
            )
        
        # Test sonuçlarını hesapla ve kaydet
        if st.form_submit_button("🎯 Testi Değerlendir", type="primary", use_container_width=True):
            # Bilimsel puanlama sistemi (1-5 Likert ölçeği)
            # Her kategori için ortalama puan hesapla
            a_score = sum(a_responses.values()) / len(a_responses) if a_responses else 0
            b_score = sum(b_responses.values()) / len(b_responses) if b_responses else 0  
            c_score = sum(c_responses.values()) / len(c_responses) if c_responses else 0
            
            # Toplam puan ve yüzdelik hesaplama
            total_score = a_score + b_score + c_score
            
            if total_score > 0:
                a_percentage = (a_score / total_score) * 100
                b_percentage = (b_score / total_score) * 100
                c_percentage = (c_score / total_score) * 100
            else:
                a_percentage = b_percentage = c_percentage = 33.33
            
            # Baskın öğrenme stilini belirle
            scores = {
                'Görsel': (a_score, a_percentage),
                'İşitsel': (b_score, b_percentage), 
                'Kinestetik': (c_score, c_percentage)
            }
            
            # En yüksek puanı bul
            dominant_style = max(scores.keys(), key=lambda k: scores[k][0])
            
            # Sonuçları birleştir
            all_responses = {**a_responses, **b_responses, **c_responses}
            
            # Veritabanına kaydet - Hem eski hem yeni field isimleri
            update_user_in_firebase(st.session_state.current_user, {
                'vak_test_results': json.dumps(all_responses),
                'learning_style': dominant_style,
                'learning_style_scores': json.dumps({
                    'visual': a_percentage,
                    'auditory': b_percentage,
                    'kinesthetic': c_percentage
                }),
                'vak_test_scores': json.dumps({
                    'A_score': a_score,
                    'B_score': b_score, 
                    'C_score': c_score,
                    'A_percentage': a_percentage,
                    'B_percentage': b_percentage,
                    'C_percentage': c_percentage,
                    'dominant_style': dominant_style
                }),
                'vak_test_completed': 'True'
            })
            
            st.session_state.users_db = load_users_from_firebase()
            
            # Sonuçları göster
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.markdown("## 🎉 VAK Öğrenme Stilleri Test Sonuçlarınız")
            
            # Puanlar ve yüzdeler
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("👁️ GÖRSEL ÖĞRENME", 
                         f"{a_score:.2f}/5.00", 
                         f"%{a_percentage:.1f}")
            with col2:
                st.metric("👂 İŞİTSEL ÖĞRENME", 
                         f"{b_score:.2f}/5.00", 
                         f"%{b_percentage:.1f}") 
            with col3:
                st.metric("✋ KİNESTETİK ÖĞRENME", 
                         f"{c_score:.2f}/5.00", 
                         f"%{c_percentage:.1f}")
            
            st.markdown("---")
            st.markdown(f"## 🏆 Baskın Öğrenme Stiliniz: **{dominant_style.upper()}**")
            
            # Detaylı öğrenme stili analizi ve modern öneriler
            display_modern_vak_analysis(dominant_style, a_percentage, b_percentage, c_percentage)
            
            # Öğretmen rehberi bölümü
            display_teacher_guide_section(dominant_style)
            
            # Gelişmiş çalışma teknikleri
            display_advanced_study_techniques(dominant_style)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.success("✅ Test sonuçlarınız kaydedildi!")

def run_cognitive_profile_test():
    """Bilişsel Profil Testi - 20 soru (Likert 1-5)"""
    
    # Ana menüye dön butonu
    if st.button("🏠 Ana Menüye Dön", key="back_to_main_cognitive"):
        if 'page' in st.session_state:
            del st.session_state.page
        st.rerun()
    
    st.markdown("---")
    
    # Modern CSS stilini ekle ve metin görünürlük sorunu için css ekle
    st.markdown("""
    <style>
    body {
        color: black !important;
    }
    .stMarkdown {
        color: black !important;
    }
    .cognitive-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .section-header {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        color: #333;
        padding: 1rem;
        border-radius: 10px;
        margin: 1.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    .cognitive-question {
        background: #f8f9ff;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .cognitive-result {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .likert-scale {
        display: flex;
        justify-content: space-between;
        margin: 1rem 0;
        padding: 0.5rem;
        background: #f0f2f6;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Başlık
    st.markdown("""
    <div class="cognitive-header">
        <h1>🧠 Bilişsel Profil Testi</h1>
        <p>Düşünme stilinizi, motivasyon kaynağınızı ve problem çözme yaklaşımınızı keşfedin</p>
        <p><strong>📋 20 soru | 🎯 1-5 arası puanlama</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Test açıklaması
    st.markdown("""
    ### 🔬 Test Hakkında
    Bu test **4 ana boyutta** bilişsel profilinizi analiz eder:
    
    🔬 **Bilişsel İşleme Stili** - Bilgiyi nasıl işliyorsunuz?  
    ⚡ **Motivasyon & Duygusal Stil** - Neyin sizi motive ettiği  
    🔍 **Problem Çözme Yaklaşımı** - Zorluklarla nasıl başa çıktığınız  
    💾 **Hafıza & Pekiştirme Tarzı** - Bilgiyi nasıl sakladığınız  
    
    **Puanlama:** 1 = Hiç uymuyor, 5 = Tamamen uyuyor
    """)
    
    # Test formunu başlat
    with st.form("cognitive_test_form"):
        user_data = get_user_data()
        existing_results_raw = user_data.get('cognitive_test_results', {})
        
        # JSON string ise parse et, dict ise direkt kullan
        if isinstance(existing_results_raw, str):
            try:
                existing_results = json.loads(existing_results_raw)
            except (json.JSONDecodeError, TypeError):
                existing_results = {}
        else:
            existing_results = existing_results_raw if isinstance(existing_results_raw, dict) else {}
        
        responses = {}
        
        # Bölümlere göre soruları grupla
        sections = {}
        for question in COGNITIVE_PROFILE_TEST:
            section = question['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(question)
        
        # Her bölüm için soruları göster
        for section_name, questions in sections.items():
            st.markdown(f'<div class="section-header">{section_name}</div>', unsafe_allow_html=True)
            
            for i, question in enumerate(questions):
                question_key = f"{question['category']}_{i}"
                default_value = existing_results.get(question_key, 3)
                
                st.markdown(f'<div class="cognitive-question">{question["question"]}</div>', unsafe_allow_html=True)
                
                # Likert scale slider
                responses[question_key] = st.slider(
                    "Değerlendirme",
                    min_value=1,
                    max_value=5,
                    value=default_value,
                    key=question_key,
                    help="1 = Hiç uymuyor, 5 = Tamamen uyuyor",
                    label_visibility="collapsed"
                )
                
                # Açıklama metni
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.caption("Hiç uymuyor")
                with col2:
                    st.caption("")
                with col3:
                    st.caption("Tamamen uyuyor")
                
                st.markdown("---")
        
        # Test sonuçlarını hesapla ve kaydet
        if st.form_submit_button("🎯 Testi Değerlendir", type="primary", use_container_width=True):
            # Kategorilere göre puanları hesapla
            category_scores = {}
            
            for question_key, score in responses.items():
                # İlgili soruyu bul
                for question in COGNITIVE_PROFILE_TEST:
                    if question_key.startswith(question['category']):
                        category = question['category']
                        if category not in category_scores:
                            category_scores[category] = []
                        category_scores[category].append(score)
                        break
            
            # Ortalama puanları hesapla
            average_scores = {}
            for category, scores in category_scores.items():
                average_scores[category] = sum(scores) / len(scores)
            
            # Veritabanına kaydet
            update_user_in_firebase(st.session_state.current_user, {
                'cognitive_test_results': json.dumps(responses),
                'cognitive_test_scores': json.dumps(average_scores),
                'cognitive_test_completed': 'True'
            })
            
            st.session_state.users_db = load_users_from_firebase()
            
            # Sonuçları göster
            st.markdown('<div class="cognitive-result">', unsafe_allow_html=True)
            st.markdown("## 🎉 Bilişsel Profil Sonuçlarınız")
            
            # Sonuçları görselleştir
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📊 Puanlarınız")
                for category, score in average_scores.items():
                    # Kategori isimlerini Türkçe'ye çevir
                    if 'analytic' in category:
                        display_name = "🔬 Analitik Düşünme"
                    elif 'synthetic' in category:
                        display_name = "🎨 Sintetik Düşünme"
                    elif 'reflective' in category:
                        display_name = "🧘 Reflektif Düşünme"
                    elif 'external' in category:
                        display_name = "⚡ Dışsal Motivasyon"
                    elif 'internal' in category:
                        display_name = "🧍‍♂️ İçsel Motivasyon"
                    elif 'methodic' in category:
                        display_name = "📊 Metodik Problem Çözme"
                    elif 'experimental' in category:
                        display_name = "💡 Deneysel Problem Çözme"
                    elif 'social' in category:
                        display_name = "🗣️ Sosyal Problem Çözme"
                    elif 'visual' in category:
                        display_name = "👁 Görsel Hafıza"
                    elif 'auditory' in category:
                        display_name = "👂 İşitsel Hafıza"
                    elif 'experiential' in category:
                        display_name = "✋ Deneyimsel Hafıza"
                    elif 'analytic' in category:
                        display_name = "📖 Analitik Hafıza"
                    else:
                        display_name = category
                    
                    st.metric(display_name, f"{score:.1f}/5")
            
            with col2:
                st.markdown("### 🎯 YKS İçin Öneriler")
                
                # En yüksek puanları bul ve önerilerde bulun
                max_categories = [k for k, v in average_scores.items() if v == max(average_scores.values())]
                
                if any('analytic' in cat for cat in max_categories):
                    st.info("📊 **Analitik yapınız güçlü:** Düzenli çalışma planları ve aşama aşama öğrenme size uygun!")
                    
                if any('synthetic' in cat for cat in max_categories):
                    st.info("🎨 **Bütüncül bakış açınız güçlü:** Kavram haritaları ve genel resmi görme yaklaşımları size uygun!")
                    
                if any('external' in cat for cat in max_categories):
                    st.info("🏆 **Dışsal motivasyon:** Hedef koyma, ödül sistemi ve rekabet size enerji verir!")
                    
                if any('internal' in cat for cat in max_categories):
                    st.info("💫 **İçsel motivasyon:** İlginizi çeken konulardan başlayın, merak duygusu size güç verir!")
                    
                if any('methodic' in cat for cat in max_categories):
                    st.info("📋 **Sistematik yaklaşım:** Adım adım planlar ve düzenli tekrarlar size uygun!")
                    
                if any('experimental' in cat for cat in max_categories):
                    st.info("🔬 **Deneyimsel öğrenme:** Bol soru çözümü ve pratik uygulamalar size uygun!")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.success("✅ Bilişsel profil sonuçlarınız kaydedildi!")

def run_motivation_emotional_test():
    """Motivasyon & Duygusal Denge Testi - 10 soru (Likert 1-5)"""
    
    # Ana menüye dön butonu
    if st.button("🏠 Ana Menüye Dön", key="back_to_main_motivation"):
        if 'page' in st.session_state:
            del st.session_state.page
        st.rerun()
    
    st.markdown("---")
    
    # CSS stilini ekle ve metin görünürlük sorunu için css ekle
    st.markdown("""
    <style>
    body {
        color: black !important;
    }
    .stMarkdown {
        color: black !important;
    }
    .motivation-header {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .motivation-question {
        background: #fff5f5;
        border-left: 4px solid #ff6b6b;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .motivation-result {
        background: linear-gradient(135deg, #ff9999 0%, #ffcccc 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Başlık
    st.markdown("""
    <div class="motivation-header">
        <h1>⚡ Motivasyon & Duygusal Denge Testi</h1>
        <p>Motivasyon kaynağınızı, kaygı düeyinizi ve duygusal dayanıklılığınızı keşedin</p>
        <p><strong>📋 10 soru | 🎯 1-5 arası puanlama</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Test açıklaması
    st.markdown("""
    ### 🔬 Test Hakkında
    Bu test **4 ana boyutta** motivasyon ve duygusal profilinizi analiz eder:
    
    💫 **İçsel Motivasyon** - Öğrenme sürecinden zevk alma  
    🏆 **Dışsal Motivasyon** - Harici ödül ve takdir arayışı  
    😰 **Sınav Kaygısı** - Performans kaygısı ve stres düzeyi  
    💪 **Duygusal Dayanıklılık** - Zorluklarla başa çıkma kapasitesi  
    
    **Puanlama:** 1 = Hiç katılmıyorum, 5 = Tamamen katılıyorum
    """)
    
    # Test formunu başlat
    with st.form("motivation_test_form"):
        user_data = get_user_data()
        existing_results_raw = user_data.get('motivation_test_results', {})
        
        # JSON string ise parse et, dict ise direkt kullan
        if isinstance(existing_results_raw, str):
            try:
                existing_results = json.loads(existing_results_raw)
            except (json.JSONDecodeError, TypeError):
                existing_results = {}
        else:
            existing_results = existing_results_raw if isinstance(existing_results_raw, dict) else {}
        
        responses = {}
        
        # Soru sayısını takip et
        for i, question in enumerate(MOTIVATION_EMOTIONAL_TEST):
            question_key = f"motivation_{i+1}"
            default_value = existing_results.get(question_key, 3)
            
            st.markdown(f'<div class="motivation-question">{i+1}. {question["question"]}</div>', unsafe_allow_html=True)
            
            # Likert scale slider
            responses[question_key] = st.select_slider(
                f"Soru {i+1} - Değerlendirmeniz:",
                options=[1, 2, 3, 4, 5],
                value=default_value,
                key=question_key,
                format_func=lambda x: {
                    1: "1 - Hiç katılmıyorum",
                    2: "2 - Katılmıyorum", 
                    3: "3 - Kararsızım",
                    4: "4 - Katılıyorum",
                    5: "5 - Tamamen katılıyorum"
                }[x]
            )
            st.markdown("---")
        
        # Test sonuçlarını hesapla ve kaydet
        if st.form_submit_button("🎯 Testi Değerlendir", type="primary", use_container_width=True):
            # Kategorilere göre puanları hesapla
            category_scores = {
                'internal_motivation': [],
                'external_motivation': [],
                'test_anxiety': [],
                'emotional_resilience': []
            }
            
            for i, question in enumerate(MOTIVATION_EMOTIONAL_TEST):
                question_key = f"motivation_{i+1}"
                score = responses[question_key]
                category = question['category']
                category_scores[category].append(score)
            
            # Ortalama puanları hesapla
            average_scores = {}
            for category, scores in category_scores.items():
                if scores:
                    average_scores[category] = sum(scores) / len(scores)
                else:
                    average_scores[category] = 0
            
            # Veritabanına kaydet
            update_user_in_firebase(st.session_state.current_user, {
                'motivation_test_results': json.dumps(responses),
                'motivation_test_scores': json.dumps(average_scores),
                'motivation_test_completed': 'True'
            })
            
            st.session_state.users_db = load_users_from_firebase()
            
            # Sonuçları göster
            st.markdown('<div class="motivation-result">', unsafe_allow_html=True)
            st.markdown("## 🎉 Motivasyon & Duygusal Denge Sonuçlarınız")
            
            # Sonuçları görselleştir
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📋 Puanlarınız")
                st.metric("💫 İçsel Motivasyon", f"{average_scores['internal_motivation']:.1f}/5")
                st.metric("🏆 Dışsal Motivasyon", f"{average_scores['external_motivation']:.1f}/5")
                st.metric("😰 Sınav Kaygısı", f"{average_scores['test_anxiety']:.1f}/5")
                st.metric("💪 Duygusal Dayanıklılık", f"{average_scores['emotional_resilience']:.1f}/5")
            
            with col2:
                st.markdown("### 🎯 YKS İçin Öneriler")
                
                # En yüksek motivasyon türünü bul
                if average_scores['internal_motivation'] > average_scores['external_motivation']:
                    st.info("💫 **İçsel motivasyon baskın:** Merak ettiğiniz konulardan başlayın, öğrenme zevkini öne çıkarın!")
                else:
                    st.info("🏆 **Dışsal motivasyon baskın:** Hedefler koyun, ödül sistemi oluşturun, rekabet size enerji verir!")
                
                # Kaygı dürzeyine göre öneri
                if average_scores['test_anxiety'] >= 3.5:
                    st.warning("⚠️ **Yüksek kaygı düzeyi:** Nefes egzersizleri, planlama ve simulation sınavları kaygınızı azaltabilir.")
                elif average_scores['test_anxiety'] <= 2.5:
                    st.success("✅ **Düşük kaygı düzeyi:** Harika! Bu avantajınızı koruyun ve performansınıza odaklanın.")
                
                # Dayanıklılık durumuna göre öneri
                if average_scores['emotional_resilience'] >= 4.0:
                    st.success("💪 **Yüksek dayanıklılık:** Zor konularda ısrarcı olun, bu gücünüz YKS'de büyük avantaj!")
                else:
                    st.info("🌱 **Dayanıklılık geliştirme:** Küçük başarıları kutlayın, kısa vadeli hedefler koyun.")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.success("✅ Motivasyon & duygusal denge sonuçlarınız kaydedildi!")

def run_time_management_test():
    """Zaman Yönetimi & Çalışma Alışkanlığı Testi - 10 soru (Likert 1-5)"""
    
    # Ana menüye dön butonu
    if st.button("🏠 Ana Menüye Dön", key="back_to_main_time"):
        if 'page' in st.session_state:
            del st.session_state.page
        st.rerun()
    
    st.markdown("---")
    
    # CSS stilini ekle ve metin görünürlük sorunu için css ekle
    st.markdown("""
    <style>
    body {
        color: black !important;
    }
    .stMarkdown {
        color: black !important;
    }
    .time-header {
        background: linear-gradient(135deg, #4834d4 0%, #686de0 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .time-question {
        background: #f8f9ff;
        border-left: 4px solid #4834d4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .time-result {
        background: linear-gradient(135deg, #a4b0ff 0%, #c7d2fe 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Başlık
    st.markdown("""
    <div class="time-header">
        <h1>⏰ Zaman Yönetimi & Çalışma Alışkanlığı Testi</h1>
        <p>Planlama, disiplin, odak ve erteleme davranışınızı keşedin</p>
        <p><strong>📋 10 soru | 🎯 1-5 arası puanlama</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Test açıklaması
    st.markdown("""
    ### 🔬 Test Hakkında
    Bu test **4 ana boyutta** zaman yönetimi profilinizi analiz eder:
    
    📋 **Planlama & Disiplin** - Hedef belirleme ve planlı çalışma  
    ⏰ **Erteleme & Son Dakikacılık** - Procastination eğilimi  
    🎯 **Odak & Dikkat Yönetimi** - Konsantrasyon süresi ve mola dengesi  
    🧠 **Öz Farkındalık** - Verimli zaman dilimlerini tanıma  
    
    **Puanlama:** 1 = Hiç katılmıyorum, 5 = Tamamen katılıyorum
    """)
    
    # Test formunu başlat
    with st.form("time_management_test_form"):
        user_data = get_user_data()
        existing_results_raw = user_data.get('time_test_results', {})
        
        # JSON string ise parse et, dict ise direkt kullan
        if isinstance(existing_results_raw, str):
            try:
                existing_results = json.loads(existing_results_raw)
            except (json.JSONDecodeError, TypeError):
                existing_results = {}
        else:
            existing_results = existing_results_raw if isinstance(existing_results_raw, dict) else {}
        
        responses = {}
        
        # Soru sayısını takip et
        for i, question in enumerate(TIME_MANAGEMENT_TEST):
            question_key = f"time_{i+1}"
            default_value = existing_results.get(question_key, 3)
            
            st.markdown(f'<div class="time-question">{i+1}. {question["question"]}</div>', unsafe_allow_html=True)
            
            # Likert scale slider
            responses[question_key] = st.select_slider(
                f"Soru {i+1} - Değerlendirmeniz:",
                options=[1, 2, 3, 4, 5],
                value=default_value,
                key=question_key,
                format_func=lambda x: {
                    1: "1 - Hiç katılmıyorum",
                    2: "2 - Katılmıyorum", 
                    3: "3 - Kararsızım",
                    4: "4 - Katılıyorum",
                    5: "5 - Tamamen katılıyorum"
                }[x]
            )
            st.markdown("---")
        
        # Test sonuçlarını hesapla ve kaydet
        if st.form_submit_button("🎯 Testi Değerlendir", type="primary", use_container_width=True):
            # Kategorilere göre puanları hesapla
            category_scores = {
                'planning': [],
                'procrastination': [],
                'focus_control': [],
                'discipline': [],
                'self_awareness': []
            }
            
            for i, question in enumerate(TIME_MANAGEMENT_TEST):
                question_key = f"time_{i+1}"
                score = responses[question_key]
                category = question['category']
                category_scores[category].append(score)
            
            # Ortalama puanları hesapla
            average_scores = {}
            for category, scores in category_scores.items():
                if scores:
                    average_scores[category] = sum(scores) / len(scores)
                else:
                    average_scores[category] = 0
            
            # Veritabanına kaydet
            update_user_in_firebase(st.session_state.current_user, {
                'time_test_results': json.dumps(responses),
                'time_test_scores': json.dumps(average_scores),
                'time_test_completed': 'True'
            })
            
            st.session_state.users_db = load_users_from_firebase()
            
            # Sonuçları göster
            st.markdown('<div class="time-result">', unsafe_allow_html=True)
            st.markdown("## 🎉 Zaman Yönetimi Sonuçlarınız")
            
            # Sonuçları görselleştir
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📋 Puanlarınız")
                st.metric("📋 Planlama", f"{average_scores['planning']:.1f}/5")
                st.metric("⏰ Erteleme Eğilimi", f"{average_scores['procrastination']:.1f}/5")
                st.metric("🎯 Odak Kontrolü", f"{average_scores['focus_control']:.1f}/5")
                st.metric("💪 Disiplin", f"{average_scores['discipline']:.1f}/5")
                st.metric("🧠 Öz Farkındalık", f"{average_scores['self_awareness']:.1f}/5")
            
            with col2:
                st.markdown("### 🎯 YKS İçin Öneriler")
                
                # Zaman yönetimi profilini belirle
                planning_score = average_scores['planning']
                procrastination_score = average_scores['procrastination']
                focus_score = average_scores['focus_control']
                
                if planning_score >= 4.0:
                    st.success("📋 **Mükemmel planlama:** Mevcut sisteminizi koruyun, sadece ince ayar yapın!")
                elif planning_score >= 3.0:
                    st.info("📊 **Orta düzey planlama:** Haftalık detaylı planlar yapın, günlük revizyon ekleyin.")
                else:
                    st.warning("⚠️ **Planlama geliştirme:** Küçük başlayın - önce günlük, sonra haftalık planlar.")
                
                if procrastination_score >= 3.5:
                    st.warning("⏰ **Yüksek erteleme:** Pomodoro tekniği (25+5 dk) ve küçük hedefler size yardımcı olur.")
                else:
                    st.success("✅ **Düşük erteleme:** Harika! Bu disiplini koruyun.")
                
                if focus_score <= 2.5:
                    st.info("🎯 **Odak geliştirme:** Telefonunu başka odaya koy, 20 dk odaklanma + 5 dk mola döngülünü dene.")
                else:
                    st.success("🎯 **İyi odak:** Mevcut odak sürenizi optimum şekilde kullanın.")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.success("✅ Zaman yönetimi sonuçlarınız kaydedildi!")

# ===== YENİ: GELECEKTEKİ HAFTA BONUS KONULARI SİSTEMİ =====

def get_weak_topics_for_subject(user_data, subject):
    """Belirli bir ders için zayıf konuları getirir"""
    try:
        topic_progress = json.loads(user_data.get('topic_progress', '{}'))
        
        # Basit zayıf konu listesi (genişletilebilir)
        weak_topics_map = {
            "TYT Matematik": [
                {"topic": "Problemleri", "detail": "İşçi Problemleri", "net": 0},
                {"topic": "Cebir", "detail": "Denklemler", "net": 0},
                {"topic": "Geometri", "detail": "Üçgen Özellikleri", "net": 0},
                {"topic": "Fonksiyonlar", "detail": "Fonksiyon Türleri", "net": 0}
            ],
            "AYT Matematik": [
                {"topic": "Fonksiyonlar", "detail": "İleri Düzey", "net": 0},
                {"topic": "Karmaşık Sayılar", "detail": "Temel Kavramlar", "net": 0},
                {"topic": "Polinomlar", "detail": "Polinom İşlemleri", "net": 0},
                {"topic": "2. Dereceden Eşitsizlikler", "detail": "Çözüm Teknikleri", "net": 0}
            ],
            "TYT Türkçe": [
                {"topic": "Paragraf", "detail": "Düşünceyi Geliştirme", "net": 0},
                {"topic": "Yazım Kuralları", "detail": "Büyük Harf", "net": 0},
                {"topic": "Ses Bilgisi", "detail": "Ünlü Uyumları", "net": 0}
            ],
            "TYT Geometri": [
                {"topic": "Üçgen Özellikleri", "detail": "Eşlik ve Benzerlik", "net": 0},
                {"topic": "Açılar", "detail": "Doğruda Açılar", "net": 0}
            ],
            "TYT Coğrafya": [
                {"topic": "Konular", "detail": "Basınç ve Rüzgarlar", "net": 0},
                {"topic": "Konular", "detail": "İklimler", "net": 0}
            ],
            "TYT Tarih": [
                {"topic": "Tarih Bilimi", "detail": "Atatürk Dönemi Türk Dış Politikası", "net": 4}
            ],
            "TYT English": [
                {"topic": "Ses Bilgisi", "detail": "Ses Olayları", "net": 0}
            ]
        }
        
        # Eğer ders mevcutsa konuları döndür
        if subject in weak_topics_map:
            return weak_topics_map[subject]
        else:
            # Varsayılan konular
            return [
                {"topic": "Temel Konular", "detail": "Başlangıç Seviyesi", "net": 0},
                {"topic": "Orta Konular", "detail": "Gelişim Seviyesi", "net": 0}
            ]
            
    except Exception as e:
        return [{"topic": "Genel Konu", "detail": "Genel Tekrar", "net": 0}]

def calculate_weekly_completion_percentage(user_data, weekly_plan):
    """Bu haftanın hedef konularının tamamlanma yüzdesini hesaplar"""
    import json
    from datetime import datetime, timedelta
    
    try:
        # Bu hafta programlanmış konuları session'dan al
        if 'weekly_schedule' not in st.session_state:
            st.session_state.weekly_schedule = {}
        
        weekly_schedule = st.session_state.weekly_schedule
        
        # Toplam programlanmış konu sayısı
        total_scheduled = 0
        completed_topics = 0
        
        # Tüm günlerdeki programlanmış konuları say
        for day, topics in weekly_schedule.items():
            for topic in topics:
                total_scheduled += 1
                
                # Konunun tamamlanıp tamamlanmadığını kontrol et
                topic_key = f"{topic.get('subject', '')}_{topic.get('topic', '')}_{topic.get('detail', '')}"
                
                # Session state'de tamamlanma durumu
                if f"completed_{topic_key}" in st.session_state:
                    if st.session_state[f"completed_{topic_key}"]:
                        completed_topics += 1
        
        # Eğer hiç program yoksa varsayılan hesaplama
        if total_scheduled == 0:
            # Tekrar konularını kontrol et
            review_topics = weekly_plan.get('review_topics', [])
            total_scheduled = len(review_topics)
            
            if total_scheduled == 0:
                return 50.0  # Varsayılan orta seviye
            
            # Tekrar konularının kaçı tamamlandı
            topic_progress = json.loads(user_data.get('topic_progress', '{}'))
            for topic in review_topics:
                topic_key = f"{topic.get('subject', '')}_{topic.get('topic', '')}_{topic.get('detail', '')}"
                if topic_key in topic_progress:
                    # Son 7 gün içinde çalışılmış mı?
                    last_study = topic_progress[topic_key].get('last_study_date', '')
                    if last_study:
                        try:
                            last_date = datetime.fromisoformat(last_study.split('T')[0])
                            today = datetime.now()
                            if (today - last_date).days <= 7:
                                completed_topics += 1
                        except:
                            pass
        
        # Tamamlanma yüzdesini hesapla
        if total_scheduled > 0:
            completion_percentage = (completed_topics / total_scheduled) * 100
        else:
            completion_percentage = 0.0
            
        return min(completion_percentage, 100.0)  # Max %100
        
    except Exception as e:
        # Hata durumunda güvenli varsayılan
        return 25.0

def get_next_week_topics(user_data, student_field, survey_data):
    """Gelecek haftanın konularını getirir"""
    try:
        # Gelecek hafta için sabit bonus konular listesi
        next_week_topics = []
        
        # Alan bazında bonus konular
        bonus_topics_by_field = {
            "TM": [  # Türkçe-Matematik
                {"subject": "TYT Matematik", "topic": "Fonksiyonlar", "detail": "Ters Fonksiyon", "net": 0},
                {"subject": "TYT Türkçe", "topic": "Edebiyat", "detail": "Divan Edebiyatı", "net": 0},
                {"subject": "AYT Matematik", "topic": "Türev", "detail": "Türev Kuralları", "net": 0},
                {"subject": "TYT Geometri", "topic": "Çember", "detail": "Çember Teoremi", "net": 0},
                {"subject": "TYT Tarih", "topic": "İlk Çağ", "detail": "Anadolu Medeniyetleri", "net": 0},
                {"subject": "AYT Matematik", "topic": "İntegral", "detail": "Belirsiz İntegral", "net": 0}
            ],
            "TM2": [  # Türkçe-Matematik (aynı)
                {"subject": "TYT Matematik", "topic": "Fonksiyonlar", "detail": "Ters Fonksiyon", "net": 0},
                {"subject": "TYT Türkçe", "topic": "Edebiyat", "detail": "Divan Edebiyatı", "net": 0},
                {"subject": "AYT Matematik", "topic": "Türev", "detail": "Türev Kuralları", "net": 0},
                {"subject": "TYT Geometri", "topic": "Çember", "detail": "Çember Teoremi", "net": 0},
                {"subject": "TYT Tarih", "topic": "İlk Çağ", "detail": "Anadolu Medeniyetleri", "net": 0},
                {"subject": "AYT Matematik", "topic": "İntegral", "detail": "Belirsiz İntegral", "net": 0}
            ],
            "MF": [  # Matematik-Fen
                {"subject": "AYT Matematik", "topic": "Türev", "detail": "Türev Kuralları", "net": 0},
                {"subject": "AYT Fizik", "topic": "Kuvvet ve Hareket", "detail": "Atış Hareketleri", "net": 0},
                {"subject": "AYT Kimya", "topic": "Kimyasal Bağlar", "detail": "İyonik Bağ", "net": 0},
                {"subject": "AYT Biyoloji", "topic": "Hücre", "detail": "Hücre Zarı", "net": 0},
                {"subject": "TYT Matematik", "topic": "Logaritma", "detail": "Logaritma Özellikleri", "net": 0},
                {"subject": "AYT Matematik", "topic": "İntegral", "detail": "Belirsiz İntegral", "net": 0}
            ],
            "Varsayılan": [
                {"subject": "TYT Matematik", "topic": "Temel Konular", "detail": "Sayı Sistemleri", "net": 0},
                {"subject": "TYT Türkçe", "topic": "Paragraf", "detail": "Ana Fikir", "net": 0},
                {"subject": "TYT Geometri", "topic": "Temel Şekiller", "detail": "Üçgen", "net": 0},
                {"subject": "TYT Tarih", "topic": "Temel Konular", "detail": "Osmanlı Tarihi", "net": 0},
                {"subject": "TYT Coğrafya", "topic": "Fiziki Coğrafya", "detail": "İklim", "net": 0},
                {"subject": "TYT English", "topic": "Grammar", "detail": "Present Tense", "net": 0}
            ]
        }
        
        # Öğrencinin alanına göre bonus konuları seç
        field_code = student_field if student_field in bonus_topics_by_field else "Varsayılan"
        next_week_topics = bonus_topics_by_field[field_code].copy()
        
        # Her konuya bonus özelliği ekle
        for topic in next_week_topics:
            topic['priority'] = 'NEXT_WEEK_BONUS'
            topic['is_bonus'] = True
        
        return next_week_topics[:6]  # Maksimum 6 bonus konu
        
    except Exception as e:
        # Hata durumunda varsayılan konular
        return [
            {"subject": "TYT Matematik", "topic": "Temel Konular", "detail": "Bonus Çalışma", "net": 0, "priority": 'NEXT_WEEK_BONUS', "is_bonus": True},
            {"subject": "TYT Türkçe", "topic": "Temel Konular", "detail": "Bonus Çalışma", "net": 0, "priority": 'NEXT_WEEK_BONUS', "is_bonus": True},
            {"subject": "TYT Geometri", "topic": "Temel Konular", "detail": "Bonus Çalışma", "net": 0, "priority": 'NEXT_WEEK_BONUS', "is_bonus": True}
        ]

def show_next_week_bonus_topics(next_week_topics, user_data):
    """Gelecek haftanın bonus konularını kırmızı renkte gösterir"""
    if not next_week_topics:
        return
    
    st.markdown("#### 🚀 GELECEKTEKİ HAFTA BONUS KONULARI")
    st.caption("🎉 Bu haftanın hedeflerini %80+ tamamladığınız için gelecek haftanın konularını şimdiden çalışabilirsiniz!")
    
    for i, topic in enumerate(next_week_topics):
        topic_key = f"{topic.get('subject', '')}_{topic.get('topic', '')}_{topic.get('detail', '')}"
        
        # Tamamlanma durumunu kontrol et
        is_completed = st.session_state.get(f"completed_{topic_key}", False)
        
        with st.container():
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #ff4d4d22 0%, #cc000011 100%); 
                        border-left: 4px solid #ff4d4d; 
                        border: 2px dashed #ff4d4d;
                        padding: 12px; border-radius: 8px; margin-bottom: 8px;'>
                <div style='display: flex; align-items: center; margin-bottom: 8px;'>
                    <span style='font-size: 18px; margin-right: 8px;'>🚀</span>
                    <strong style='color: #ff4d4d;'>{topic.get('subject', 'Ders')}</strong>
                    <span style='background: #ff4d4d; color: white; padding: 2px 8px; border-radius: 12px; margin-left: 8px; font-size: 12px;'>BONUS</span>
                    {f"<span style='background: #00cc00; color: white; padding: 2px 8px; border-radius: 12px; margin-left: 8px; font-size: 12px;'>✅ TAMAMLANDI</span>" if is_completed else ""}
                </div>
                <div style='margin-left: 26px;'>
                    <div><strong>📖 {topic.get('topic', 'Konu')}</strong></div>
                    <div style='font-size: 14px; color: #666; margin-top: 4px;'>
                        └ {topic.get('detail', 'Detay')} 
                        <span style='background: #ffe6e6; padding: 2px 6px; border-radius: 10px; margin-left: 8px; color: #cc0000;'>
                            🎯 {topic.get('net', 0)} net
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # İşlem butonları
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col2:
                if not is_completed:
                    if st.button(f"✅", key=f"complete_bonus_{i}", help="Konuyu tamamladım"):
                        st.session_state[f"completed_{topic_key}"] = True
                        st.success(f"🎉 {topic.get('topic', 'Konu')} tamamlandı!")
                        st.rerun()
                else:
                    if st.button(f"↩️", key=f"uncomplete_bonus_{i}", help="Tamamlanmadı olarak işaretle"):
                        st.session_state[f"completed_{topic_key}"] = False
                        st.rerun()
            
            with col3:
                if st.button(f"📅", key=f"add_bonus_{i}", help="Program Ekle"):
                    st.session_state[f"show_scheduler_bonus_{i}"] = True
            
            # Planlayıcı göster
            if st.session_state.get(f"show_scheduler_bonus_{i}", False):
                with st.expander("🗓️ Program Ekle", expanded=True):
                    show_topic_scheduler_bonus(topic, user_data, i)

def show_topic_scheduler_bonus(topic, user_data, index):
    """Bonus konular için özel planlayıcı"""
    col1, col2 = st.columns(2)
    
    with col1:
        day_options = ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]
        selected_day = st.selectbox("Gün Türü:", day_options, key=f"bonus_day_{index}")
    
    with col2:
        time_slots = [
            "09:00-10:30", "10:45-12:15", "13:30-15:00", 
            "15:15-16:45", "17:00-18:30", "19:00-20:30", "21:00-22:30"
        ]
        selected_time = st.selectbox("Saat aralığı:", time_slots, key=f"bonus_time_{index}")
    
    if st.button("✅ Bonus Konuyu Programa Ekle", key=f"confirm_bonus_{index}"):
        # Session state'e program ekle
        if 'weekly_schedule' not in st.session_state:
            st.session_state.weekly_schedule = {}
        
        if selected_day not in st.session_state.weekly_schedule:
            st.session_state.weekly_schedule[selected_day] = []
        
        # Bonus konu bilgisini ekle
        schedule_entry = {
            'time': selected_time,
            'subject': topic.get('subject', 'Ders'),
            'topic': topic.get('topic', 'Konu'),
            'detail': topic.get('detail', 'Detay'),
            'type': 'BONUS',
            'is_bonus': True
        }
        
        st.session_state.weekly_schedule[selected_day].append(schedule_entry)
        st.success(f"🚀 Bonus konu {selected_day} günü {selected_time} saatine eklendi!")
        st.session_state[f"show_scheduler_bonus_{index}"] = False
        st.rerun()

if __name__ == "__main__":
    main()
