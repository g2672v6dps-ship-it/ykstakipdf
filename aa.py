import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
import os
import hashlib
import time
import pytz

# Plotly kontrolü
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.error("⚠️ Plotly yüklü değil. Grafik görüntüleme için lütfen plotly yükleyin: pip install plotly")

# Firebase Admin SDK 
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    st.error("⚠️ Firebase modülü yüklü değil. pip install firebase-admin gerekli.")

# Türkiye saat dilimi
TR_TZ = pytz.timezone('Europe/Istanbul')

# Öncelik kategorileri güncellendi
PRIORITY_CATEGORIES = {
    'HIGH': {'icon': '🔥', 'color': '#FF4B4B', 'name': 'Acil'},
    'MEDIUM': {'icon': '⚡', 'color': '#FFA500', 'name': 'Öncelikli'},
    'NORMAL': {'icon': '🎯', 'color': '#0066CC', 'name': 'Normal'},
    'LOW': {'icon': '🟢', 'color': '#00CC66', 'name': 'Düşük'},
    'MINIMAL': {'icon': '⭐', 'color': '#9966CC', 'name': 'Minimal'},
    'REPEAT_HIGH': {'icon': '🔄', 'color': '#FF4B4B', 'name': 'Tekrar (Yüksek)'},
    'REPEAT_MEDIUM': {'icon': '🔄', 'color': '#FFA500', 'name': 'Tekrar (Orta)'},
    'REPEAT_NORMAL': {'icon': '🔄', 'color': '#0066CC', 'name': 'Tekrar (Normal)'}
}

# Kalıcı öğrenme durumları
MASTERY_STATUS = {
    'INITIAL': {'icon': '📚', 'color': '#808080', 'name': 'İlk Öğrenme'},
    'REVIEW_1': {'icon': '🔄', 'color': '#FFB366', 'name': '1. Tekrar (1 gün sonra)'},
    'REVIEW_2': {'icon': '📖', 'color': '#66B3FF', 'name': '2. Tekrar (3 gün sonra)'},
    'REVIEW_3': {'icon': '📝', 'color': '#66FFB3', 'name': '3. Tekrar (7 gün sonra)'},
    'REVIEW_4': {'icon': '✅', 'color': '#B3FF66', 'name': '4. Tekrar (15 gün sonra)'},
    'MASTERED': {'icon': '⭐', 'color': '#FFD700', 'name': 'Kalıcı Öğrenildi'}
}

# Kitap önerileri
BOOK_RECOMMENDATIONS = {
    "Kişisel Gelişim": [
        "📖 Atomik Alışkanlıklar - James Clear",
        "📖 Düşüncenin Gücü - Maxwell Maltz",
        "📖 Zaman Yönetimi - Brian Tracy"
    ],
    "Motivasyon": [
        "📖 Bir Ömürde Bin Hayat - İlber Ortaylı",
        "📖 Korkusuzlar - Cahit Zarifoğlu", 
        "📖 Büyük Düşün Büyük Yaşa - David Schwartz"
    ],
    "Bilim ve Teknoloji": [
        "📖 Sapiens - Yuval Noah Harari",
        "📖 Kozmos - Carl Sagan",
        "📖 İnsanın Anlam Arayışı - Viktor Frankl"
    ]
}

# Global Firebase connection
db = None

@st.cache_data
def get_firebase_connection():
    """Firebase bağlantısını başlatır"""
    global db
    
    if not FIREBASE_AVAILABLE:
        return None
        
    if db is not None:
        return db
    
    try:
        # Firebase servis anahtarınızı buraya ekleyin
        firebase_credentials = {
            "type": "service_account",
            "project_id": "yks-takip-sistemi",
            # Diğer kimlik bilgilerinizi buraya ekleyin
        }
        
        # Firebase Admin SDK'sını başlat
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_credentials)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        return db
    except Exception as e:
        st.error(f"Firebase bağlantı hatası: {e}")
        return None

def generate_user_id(username):
    """Kullanıcı adından benzersiz ID oluşturur"""
    return hashlib.md5(username.encode()).hexdigest()

def save_user_to_firebase(user_data):
    """Kullanıcıyı Firebase'e kaydeder"""
    db = get_firebase_connection()
    if db is None:
        return False
    
    try:
        user_id = generate_user_id(user_data['username'])
        doc_ref = db.collection('users').document(user_id)
        doc_ref.set(user_data)
        return True
    except Exception as e:
        st.error(f"Firebase kayıt hatası: {e}")
        return False

def load_user_from_firebase(username):
    """Firebase'den kullanıcı yükler"""
    db = get_firebase_connection()
    if db is None:
        return None
    
    try:
        user_id = generate_user_id(username)
        doc_ref = db.collection('users').document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        st.error(f"Firebase yükleme hatası: {e}")
        return None

def update_user_in_firebase(username, update_data):
    """Firebase'de kullanıcı verisini günceller"""
    db = get_firebase_connection()
    if db is None:
        return False
    
    try:
        user_id = generate_user_id(username)
        doc_ref = db.collection('users').document(user_id)
        doc_ref.update(update_data)
        return True
    except Exception as e:
        st.error(f"Firebase güncelleme hatası: {e}")
        return False

def load_users_from_firebase():
    """Tüm kullanıcıları Firebase'den yükler"""
    db = get_firebase_connection()
    if db is None:
        return {}
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        users = {}
        for doc in docs:
            user_data = doc.to_dict()
            users[user_data['username']] = user_data
        
        return users
    except Exception as e:
        st.error(f"Firebase kullanıcı listesi yükleme hatası: {e}")
        return {}

def get_subjects_by_field_yks(field):
    """Alana göre dersleri döndürür"""
    subjects = {
        'Sayısal (MF)': ['Matematik', 'Fizik', 'Kimya', 'Biyoloji', 'Türkçe', 'Tarih-1', 'Coğrafya-1', 'Felsefe'],
        'Sözel (TM)': ['Türkçe', 'Tarih-1', 'Tarih-2', 'Coğrafya-1', 'Coğrafya-2', 'Felsefe', 'Din Kültürü', 'Matematik', 'Edebiyat'],
        'Eşit Ağırlık (EA)': ['Matematik', 'Türkçe', 'Tarih-1', 'Coğrafya-1', 'Edebiyat', 'Felsefe', 'İngilizce'],
        'Dil': ['İngilizce', 'Türkçe', 'Tarih-1', 'Coğrafya-1', 'Matematik', 'Felsefe', 'Edebiyat']
    }
    return subjects.get(field, [])

def get_current_week_info():
    """Mevcut hafta bilgilerini döndürür"""
    now = datetime.now(TR_TZ)
    
    # YKS tarihi (2025)
    yks_date = datetime(2025, 6, 15, tzinfo=TR_TZ)
    
    # Kalan günler
    days_to_yks = (yks_date - now).days
    
    # Hafta numarası (yılın kaçıncı haftası)
    week_number = now.isocalendar()[1]
    
    # Hafta başı ve sonu
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    
    return {
        'today': now,
        'yks_date': yks_date,
        'days_to_yks': days_to_yks,
        'weeks_to_yks': days_to_yks // 7,
        'months_to_yks': days_to_yks // 30,
        'week_number': week_number,
        'week_start': week_start,
        'week_end': week_end,
        'week_range': f"{week_start.strftime('%d %B')} - {week_end.strftime('%d %B')}"
    }

def generate_weekly_schedule(user_data):
    """Uyku saatine göre çalışma programı önerir"""
    survey_data = json.loads(user_data.get('yks_survey_data', '{}'))
    sleep_time = survey_data.get('sleep_time', '23:00 - 06:00 (7 saat) - Önerilen')
    
    # Kullanıcının tempoya göre dinamik saat ayarlama
    base_hours = 6  # Temel çalışma saati
    
    # Öğrencinin hızına göre saat ayarlama
    user_progress = get_user_weekly_progress(user_data)
    target_progress = 70  # Hedef haftalık ilerleme %70
    
    if user_progress < 50:  # Yavaş gidiyorsa
        adjusted_hours = base_hours + 1  # 1 saat artır
    elif user_progress < target_progress:  # Biraz yavaş
        adjusted_hours = base_hours + 0.5  # 30 dakika artır
    else:  # Normal veya hızlı
        adjusted_hours = base_hours
    
    # Uyku saatine göre program önerisi
    if 'Erken' in sleep_time or '22:00' in sleep_time or '23:00' in sleep_time:
        return f"06:00-{6+int(adjusted_hours)}:00, 17:00-20:00"
    elif 'Normal' in sleep_time or '00:00' in sleep_time:
        return f"07:00-{7+int(adjusted_hours)}:00, 18:00-21:00"
    elif 'Geç' in sleep_time or '01:00' in sleep_time:
        return f"08:00-{8+int(adjusted_hours)}:00, 19:00-22:00"
    else:  # Çok geç
        return f"09:00-{9+int(adjusted_hours)}:00, 20:00-23:00"

def get_user_weekly_progress(user_data):
    """Kullanıcının haftalık ilerlemesini hesaplar"""
    # Konu takip verilerinden ilerleme hesapla
    topic_tracking = json.loads(user_data.get('topic_tracking_data', '{}'))
    if not topic_tracking:
        return 60  # Varsayılan
    
    # 5+ net olan konuları say
    completed_topics = sum(1 for topic_data in topic_tracking.values() 
                          if topic_data.get('net_score', 0) >= 5)
    
    # Pomodoro verisini de dahil et
    pomodoro_data = json.loads(user_data.get('pomodoro_data', '{}'))
    weekly_sessions = sum(1 for session in pomodoro_data.values() 
                         if session.get('completed', False))
    
    # Basit bir formula ile ilerleme yüzdesi hesapla
    progress = min(100, (completed_topics * 10 + weekly_sessions * 5))
    return max(30, progress)  # Minimum %30

def calculate_current_yks_score(user_data):
    """Mevcut YKS puanını hesaplar"""
    topic_tracking = json.loads(user_data.get('topic_tracking_data', '{}'))
    
    if not topic_tracking:
        return 300  # Varsayılan başlangıç puanı
    
    total_net = sum(topic_data.get('net_score', 0) for topic_data in topic_tracking.values())
    estimated_score = 300 + (total_net * 2)  # Her net için 2 puan
    
    return min(500, max(300, estimated_score))

def show_progress_analytics(user_data):
    """📊 Gidişat ve İlerleme Analizi - GÜNCEL VE ADAPTIF"""
    st.subheader("📊 Gidişat Analizi ve İlerleme Takibi")
    
    # YKS'ye kalan süre
    week_info = get_current_week_info()
    days_to_yks = week_info['days_to_yks']
    weeks_to_yks = days_to_yks // 7
    months_to_yks = days_to_yks // 30
    
    # Zaman kartları
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📅 Kalan Ay", months_to_yks)
    with col2:
        st.metric("📅 Kalan Hafta", weeks_to_yks)
    with col3:
        st.metric("📅 Kalan Gün", days_to_yks)
    
    st.markdown("---")
    
    # Mevcut puan hesaplama
    current_score = calculate_current_yks_score(user_data)
    
    # YENİ: ADAPTIF YILLIK PLAN SİSTEMİ
    show_adaptive_yearly_plan(user_data, current_score, months_to_yks)
    
    st.markdown("---")
    
    # Çalışma programı önerisi (Otomatik güncellenen)
    suggested_schedule = generate_weekly_schedule(user_data)
    
    st.subheader("⏰ Önerilen Çalışma Saatleri")
    user_progress = get_user_weekly_progress(user_data)
    
    if user_progress < 50:
        st.warning(f"📈 İlerlemeniz yavaş ({user_progress:.1f}%). Çalışma saatleriniz otomatik olarak artırıldı!")
    elif user_progress < 70:
        st.info(f"📊 İlerlemeniz normal ({user_progress:.1f}%). Çalışma saatleriniz uygun seviyede.")
    else:
        st.success(f"🚀 Harika ilerleme ({user_progress:.1f}%)! Mevcut temponu koru.")
    
    st.info(f"""
    **📚 Günlük Çalışma Programı:** {suggested_schedule}
    
    **⏰ Haftalık Program:**
    - Pazartesi-Cuma: Yoğun çalışma
    - Cumartesi: Hafta tekrarı (4 saat)
    - Pazar: Dinlenme veya hafif tekrar (2 saat)
    
    *Bu program ilerlemenize göre otomatik güncellenir.*
    """)

def show_adaptive_yearly_plan(user_data, current_score, months_to_yks):
    """Adaptif yıllık plan sistemi"""
    st.subheader("🎯 YKS'ye Kadar Dinamik Yol Haritası")
    
    # Öğrenci tempositemi hesapla
    user_progress = get_user_weekly_progress(user_data)
    target_weekly_progress = 70  # Hedef haftalık %70
    
    # Tempo farkı hesapla
    tempo_farki = user_progress - target_weekly_progress
    
    # Tempo durumunu belirle
    if tempo_farki >= 15:  # %85+ ilerleme
        tempo_status = "Hızlı"
        ay_offset = -1  # Planı 1 ay öne al
        tempo_color = "success"
        tempo_emoji = "🚀"
    elif tempo_farki >= -10:  # %60-84 ilerleme  
        tempo_status = "Normal"
        ay_offset = 0  # Plan normal
        tempo_color = "info"
        tempo_emoji = "📈"
    else:  # %60 altı ilerleme
        tempo_status = "Yavaş"
        ay_offset = 1  # Planı 1 ay geriye al
        tempo_color = "warning"
        tempo_emoji = "⚡"
    
    # Tempo durumu göster
    if tempo_status == "Hızlı":
        st.success(f"{tempo_emoji} **{tempo_status} İlerleme** - Planınız 1 ay öne alındı! Deneme sınavlarına daha erken başlayabilirsiniz.")
    elif tempo_status == "Normal":
        st.info(f"{tempo_emoji} **{tempo_status} İlerleme** - Planınız yolunda gidiyor.")
    else:
        st.warning(f"{tempo_emoji} **{tempo_status} İlerleme** - Planınız 1 ay geriye alındı. Daha fazla çalışma gerekli.")
    
    # Öğrenci alanını al
    student_field = user_data.get('field', 'Sayısal (MF)')
    
    # ADAPTIF AYLIK PLAN OLUŞTUR
    create_adaptive_monthly_plan(student_field, ay_offset, current_score, tempo_status)

def create_adaptive_monthly_plan(student_field, ay_offset, current_score, tempo_status):
    """Adaptif aylık plan oluşturur"""
    
    # Temel plan tarihleri (Normal tempo için)
    base_plan = {
        'Ekim': {'focus': 'Temel Konular', 'milestone': None},
        'Kasım': {'focus': 'TYT Matematik & Türkçe', 'milestone': None},
        'Aralık': {'focus': 'Fen Bilimleri Temeli', 'milestone': None},
        'Ocak': {'focus': 'AYT Hazırlık', 'milestone': None},
        'Şubat': {'focus': 'Eksik Konular', 'milestone': None},
        'Mart': {'focus': 'Genel Tekrar', 'milestone': None},
        'Nisan': {'focus': 'Deneme & Revizyon', 'milestone': '🎯 DENEMELER BAŞLIYOR!'},
        'Mayıs': {'focus': 'Son Tekrar & Deneme', 'milestone': '📝 YKS\'YE HAZIRLIK!'},
        'Haziran': {'focus': 'Final Tekrar', 'milestone': '🏆 YKS ZAMANI!'}
    }
    
    # Alan bazlı özelleştirme
    if student_field == 'Sayısal (MF)':
        base_plan['Kasım']['focus'] = 'Matematik Temeli'
        base_plan['Aralık']['focus'] = 'Fizik & Kimya'
        base_plan['Ocak']['focus'] = 'Biyoloji & AYT Mat'
    elif student_field == 'Sözel (TM)':
        base_plan['Kasım']['focus'] = 'Türkçe & Edebiyat'
        base_plan['Aralık']['focus'] = 'Tarih Temeli'
        base_plan['Ocak']['focus'] = 'Coğrafya & Felsefe'
    elif student_field == 'Eşit Ağırlık (EA)':
        base_plan['Kasım']['focus'] = 'Matematik & Türkçe'
        base_plan['Aralık']['focus'] = 'Sosyal Bilimler'
        base_plan['Ocak']['focus'] = 'Edebiyat & İngilizce'
    
    # Offset ile planı ayarla
    months = list(base_plan.keys())
    
    # Grafik verileri hazırla
    month_names = []
    score_projections = []
    colors = []
    
    current_month_index = 0  # Ekim başlangıç
    projected_score = current_score
    
    for i, month in enumerate(months):
        adjusted_index = max(0, min(len(months)-1, i + ay_offset))
        adjusted_month = months[adjusted_index]
        
        month_names.append(month)
        score_projections.append(projected_score)
        
        # Renk kodlama
        if tempo_status == "Hızlı":
            colors.append('#00CC66')  # Yeşil
        elif tempo_status == "Normal":
            colors.append('#0066CC')  # Mavi
        else:
            colors.append('#FF6B6B')  # Kırmızı
        
        # Score projeksiyonu (aylık +15 puan varsayım)
        projected_score = min(500, projected_score + 15)
    
    # Plotly grafik oluştur
    if PLOTLY_AVAILABLE:
        fig = go.Figure()
        
        # Mevcut puan
        fig.add_trace(go.Scatter(
            x=['Şu An'], 
            y=[current_score],
            mode='markers',
            marker=dict(size=15, color='red'),
            name='Mevcut Puanınız'
        ))
        
        # Gelişim projeksiyonu
        fig.add_trace(go.Scatter(
            x=month_names, 
            y=score_projections,
            mode='lines+markers',
            line=dict(color=colors[0], width=3),
            marker=dict(size=8, color=colors),
            name=f'Tahmini Gelişim ({tempo_status})'
        ))
        
        fig.update_layout(
            title=f"📈 {tempo_status} İlerleme - YKS Tahmini Gelişim Grafiği",
            xaxis_title="Aylar",
            yaxis_title="YKS Puanı",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Aylık detay planı
    st.subheader("📅 Aylık Odak Alanları")
    
    for i, month in enumerate(months):
        plan_data = base_plan[month]
        
        # Ay offsetine göre milestone ayarla
        if plan_data['milestone']:
            if ay_offset == -1:  # Hızlı - milestones öne alınır
                if month == 'Mart':
                    milestone_text = '🎯 DENEMELER BAŞLIYOR! (1 ay erken)'
                else:
                    milestone_text = plan_data['milestone']
            elif ay_offset == 1:  # Yavaş - milestones geriye alınır
                if month == 'Mayıs':
                    milestone_text = '🎯 DENEMELER BAŞLIYOR! (1 ay geç)'
                else:
                    milestone_text = plan_data['milestone']
            else:
                milestone_text = plan_data['milestone']
        else:
            milestone_text = None
        
        with st.expander(f"📅 {month} 2024/25", expanded=(i < 2)):
            st.write(f"**🎯 Odak:** {plan_data['focus']}")
            if milestone_text:
                st.markdown(f"**{milestone_text}**")
            
            # Tempo bazlı öneriler
            if tempo_status == "Hızlı":
                st.success("🚀 Hızlı ilerliyorsunuz! Bonus konular ekleyebilirsiniz.")
            elif tempo_status == "Yavaş":
                st.warning("⚡ Tempo artırmalısınız. Günlük çalışma saatinizi artırın.")
            else:
                st.info("📈 Planınız yolunda. Bu tempoyu koruyun.")
    
    # Genel öneri
    st.markdown("---")
    st.markdown("### 💡 Dinamik Öneriler")
    
    if tempo_status == "Hızlı":
        st.success("""
        🚀 **Hızlı İlerleme Önerileri:**
        - Deneme sınavlarına Mart ayında başlayabilirsiniz
        - Bonus konular ve zor problemlere odaklanın
        - İleri seviye kaynaklara geçiş yapın
        """)
    elif tempo_status == "Yavaş":
        st.warning("""
        ⚡ **İlerleme Hızlandırma Önerileri:**
        - Günlük çalışma saatinizi 1-2 saat artırın
        - Zayıf konularınıza odaklanın
        - Deneme sınavlarını Mayıs'a ertelemeyi düşünün
        """)
    else:
        st.info("""
        📈 **Normal İlerleme:**
        - Mevcut tempoya devam edin
        - Nisan ayında deneme sınavlarına başlayın
        - Düzenli tekrar programını sürdürün
        """)

def create_dynamic_weekly_plan(user_data, student_field, survey_data):
    """Dinamik haftalık plan oluşturur"""
    week_info = get_current_week_info()
    
    # Basit bir haftalık plan döndür
    weekly_plan = {
        'week_info': week_info,
        'week_target': 10,  # Haftalık hedef konu sayısı
        'success_target': 0.7,  # %70 başarı hedefi
        'review_topics': [],  # Tekrar konuları
        'projections': {
            'overall_progress': get_user_weekly_progress(user_data),
            'tyt_progress': get_user_weekly_progress(user_data) * 0.8,
            'ayt_progress': get_user_weekly_progress(user_data) * 0.6,
            'estimated_completion': 'Nisan 2025'
        }
    }
    
    return weekly_plan

def calculate_weekly_completion_percentage(user_data, weekly_plan=None):
    """Haftalık tamamlanma yüzdesini hesaplar"""
    if weekly_plan is None:
        # Basit varsayılan plan oluştur
        weekly_plan = {'week_target': 10}
    
    # Kullanıcının bu haftaki ilerlemesi
    user_progress = get_user_weekly_progress(user_data)
    target = weekly_plan.get('week_target', 10)
    
    # Tamamlanma yüzdesi hesapla
    completion = min(100, (user_progress / target) * 100)
    return max(15, completion)  # Minimum %15

def main():
    """Ana uygulama fonksiyonu"""
    st.set_page_config(
        page_title="YKS Takip Sistemi",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS stilleri
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .success-card {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        padding: 15px;
        border-radius: 8px;
        color: white;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Ana sayfa
    st.title("🎯 YKS Takip Sistemi")
    st.markdown("**Akıllı Çalışma Planı & İlerleme Takibi**")
    
    # Kullanıcı girişi
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    """Giriş sayfası"""
    st.subheader("🔐 Giriş Yapın veya Kayıt Olun")
    
    tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("👤 Kullanıcı Adı")
            password = st.text_input("🔒 Şifre", type="password")
            
            if st.form_submit_button("🔓 Giriş Yap", type="primary"):
                if login_user(username, password):
                    st.success("✅ Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı!")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("👤 Yeni Kullanıcı Adı")
            new_password = st.text_input("🔒 Yeni Şifre", type="password")
            confirm_password = st.text_input("🔒 Şifre Tekrar", type="password")
            field = st.selectbox("🎓 Alan Seçimi", 
                               ["Sayısal (MF)", "Sözel (TM)", "Eşit Ağırlık (EA)", "Dil"])
            
            if st.form_submit_button("📝 Kayıt Ol", type="primary"):
                if new_password != confirm_password:
                    st.error("❌ Şifreler eşleşmiyor!")
                elif len(new_password) < 4:
                    st.error("❌ Şifre en az 4 karakter olmalı!")
                elif register_user(new_username, new_password, field):
                    st.success("✅ Kayıt başarılı! Giriş yapabilirsiniz.")
                else:
                    st.error("❌ Bu kullanıcı adı zaten var!")

def login_user(username, password):
    """Kullanıcı girişi"""
    user_data = load_user_from_firebase(username)
    
    if user_data and user_data.get('password') == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.current_user = user_data
        return True
    return False

def register_user(username, password, field):
    """Kullanıcı kaydı"""
    # Kullanıcı var mı kontrol et
    if load_user_from_firebase(username):
        return False
    
    # Yeni kullanıcı oluştur
    user_data = {
        'username': username,
        'password': password,
        'field': field,
        'created_at': datetime.now().isoformat(),
        'topic_tracking_data': '{}',
        'pomodoro_data': '{}',
        'yks_survey_data': '{}'
    }
    
    return save_user_to_firebase(user_data)

def show_main_app():
    """Ana uygulama"""
    # Sidebar
    with st.sidebar:
        st.markdown(f"👋 Hoş geldin **{st.session_state.username}**")
        st.markdown(f"🎓 Alan: **{st.session_state.current_user.get('field')}**")
        
        if st.button("🚪 Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Ana sekmeler
    tab1, tab2, tab3 = st.tabs(["📊 Ana Sayfa", "📅 Haftalık Plan", "📈 Gidişat Analizi"])
    
    with tab1:
        show_main_dashboard()
    
    with tab2:
        show_weekly_planning()
    
    with tab3:
        show_progress_analytics(st.session_state.current_user)

def show_main_dashboard():
    """Ana dashboard"""
    st.subheader("📊 Genel Durum")
    
    user_data = st.session_state.current_user
    
    # Metrikler
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        progress = get_user_weekly_progress(user_data)
        st.metric("📈 Haftalık İlerleme", f"%{progress:.1f}")
    
    with col2:
        current_score = calculate_current_yks_score(user_data)
        st.metric("🎯 Tahmini Puan", f"{current_score:.0f}")
    
    with col3:
        week_info = get_current_week_info()
        st.metric("📅 YKS'ye Kalan", f"{week_info['days_to_yks']} gün")
    
    with col4:
        target_score = 450  # Hedef puan
        remaining = target_score - current_score
        st.metric("🚀 Hedefe Kalan", f"{max(0, remaining):.0f} puan")

def show_weekly_planning():
    """Haftalık planlama"""
    st.subheader("📅 Bu Haftanın Planı")
    
    user_data = st.session_state.current_user
    
    # Basit haftalık plan göster
    week_info = get_current_week_info()
    st.info(f"📅 Bu hafta: {week_info['week_range']}")
    
    # Önerilen çalışma programı
    schedule = generate_weekly_schedule(user_data)
    st.subheader("⏰ Önerilen Çalışma Saatleri")
    st.success(f"📚 **Günlük Program:** {schedule}")

if __name__ == "__main__":
    main()
