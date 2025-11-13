import streamlit as st
import hashlib
import time
from datetime import datetime, timedelta
import csv
import os
import json
import random
import requests
from functools import lru_cache

# Paket yükleme durumları
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    # Pandas yoksa basit DataFrame mock
    class MockDataFrame:
        def __init__(self, data=None):
            self.data = data or []
        def to_dict(self):
            return {'data': self.data}
    pd = type('MockPandas', (), {'DataFrame': MockDataFrame})()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    supabase = None

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # Plotly yoksa basit fallback objeler oluştur
    class MockPlotly:
        def __init__(self):
            pass
        def Figure(self):
            return self
        def Scatter(self, **kwargs):
            return self
        def add_trace(self, *args):
            return self
        def update_layout(self, **kwargs):
            return self
        def pie(self, *args, **kwargs):
            return self
        def bar(self, *args, **kwargs):
            return self
        def line(self, *args, **kwargs):
            return self
    
    px = MockPlotly()
    go = MockPlotly()
    # st.plotly_chart yerine st.warning kullanılacak

# === GRAFİK CACHE SİSTEMİ ===
# Plotly grafikleri için cache sistemi
class PlotlyCache:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 dakika cache
    
    def get_chart(self, cache_key, generator_func):
        """Cache'li grafik oluşturma"""
        current_time = time.time()
        
        if (cache_key in self.cache and 
            current_time - self.cache[cache_key]['time'] < self.cache_duration):
            return self.cache[cache_key]['data']
        
        # Grafik oluştur ve cache'le
        chart_data = generator_func()
        self.cache[cache_key] = {
            'data': chart_data,
            'time': current_time
        }
        return chart_data

# Global plotly cache instance
plotly_cache = PlotlyCache()

# Güvenli plotly_chart fonksiyonu - CACHE'Lİ
def safe_plotly_chart(fig, cache_key=None, **kwargs):
    """Cache'li güvenli plotly chart"""
    if cache_key and PLOTLY_AVAILABLE:
        chart_data = plotly_cache.get_chart(cache_key, lambda: fig)
        if chart_data:
            fig = chart_data
    
    if PLOTLY_AVAILABLE:
        st.plotly_chart(fig, **kwargs)
    else:
        st.warning("📊 Grafik görüntülenemedi - Plotly yüklü değil")

# 🚀 OPTİMİZE EDİLMİŞ SAYFA YAPILANDIRMASI
st.set_page_config(
    page_title="YKS Takip Sistemi - Optimize",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}  # Menü öğelerini kaldır - download azalması
)

# === BASİT HOŞ GELDİN MESAJI FONKSİYONU ===
def check_and_show_welcome_message(username):
    """
    Kullanıcı giriş yaptıktan sonra basit başarı mesajı göster
    Popup yerine st.success() kullanarak donma sorunu çözüldü
    """
    try:
        # İlk kez mi kontrol et
        if 'welcome_message_shown' not in st.session_state:
            st.session_state.welcome_message_shown = False
        
        # Eğer daha önce gösterilmediyse mesajı göster
        if not st.session_state.welcome_message_shown:
            user_data = get_user_data()
            student_name = user_data.get('name', username)
            st.success(f"Hoşgeldin {student_name}! Sisteme başarıyla giriş yaptın.", icon="🎉")
            st.session_state.welcome_message_shown = True
    except Exception:
        # Hata durumunda da basit mesaj göster
        if not st.session_state.get('welcome_message_shown', False):
            st.success(f"Hoşgeldin {username}! Sisteme başarıyla giriş yaptın.", icon="🎉")
            st.session_state.welcome_message_shown = True

# === ADMIN PANELİ KONTROLÜ ===
def check_admin_access():
    """Admin panel erişim kontrolü"""
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    
    if st.session_state.admin_logged_in:
        return True
    
    return False

def admin_login():
    """Admin giriş sayfası"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 30px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h2 style="margin: 0; color: white;">🔐 YKS Admin Panel Girişi</h2>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Öğretmen/Veli Takip Sistemi</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("admin_login"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("👤 Kullanıcı Adı", placeholder="admin")
            password = st.text_input("🔒 Şifre", type="password", placeholder="yks2025")
            submitted = st.form_submit_button("🚀 Giriş Yap", use_container_width=True)
        
        if submitted:
            if username == "admin" and password == "yks2025":
                st.session_state.admin_logged_in = True
                st.success("✅ Giriş başarılı! Yönlendiriliyor...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Hatalı kullanıcı adı veya şifre!")

def admin_logout():
    """Admin çıkış"""
    st.session_state.admin_logged_in = False
    st.session_state.current_user = None
    st.success("👋 Admin panelinden başarıyla çıkış yapıldı!")
    time.sleep(1)
    st.rerun()

# === YAZDIR FONKSİYONLARI ===
def generate_weekly_plan_pdf(user_data, week_plan):
    """Haftalık planı sadece hedef konularıyla PDF formatında hazırla"""
    from datetime import datetime
    
    # Gerçek haftalık plan verilerini al
    if not week_plan or 'new_topics' not in week_plan:
        return "Haftalık plan verisi bulunamadı."
    
    topics = week_plan.get('new_topics', [])
    
    # Sadece hedef konuları içeren basit içerik
    pdf_content = f"""🎯 Bu Haftanın Hedef Konuları

Öğrenci: {user_data.get('name', 'Öğrenci')}
Alan: {user_data.get('field', 'Eşit Ağırlık')}
Tarih: {datetime.now().strftime('%d.%m.%Y')}

"""
    
    if topics:
        # Konuları ders bazında gruplama
        subjects = {}
        for topic in topics:
            subject = topic.get('subject', 'Diğer')
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(topic.get('topic', 'Konu adı yok'))
        
        # Her ders için konuları listele
        for subject, topic_list in subjects.items():
            pdf_content += f"\n📚 {subject}:\n"
            for topic in topic_list:
                pdf_content += f"  • {topic}\n"
    else:
        pdf_content += "\nBu hafta için henüz konu planı oluşturulmamış.\n"
    
    return pdf_content

def show_print_button(user_data, weekly_plan):
    """Yazdırma butonu göster"""
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🖨️ Haftalık Planı Yazdır/İndir", use_container_width=True, type="primary"):
            pdf_content = generate_weekly_plan_pdf(user_data, weekly_plan)
            
            # Dosya adı oluştur
            from datetime import datetime
            file_name = f"YKS_Haftalik_Plan_{datetime.now().strftime('%d_%m_%Y')}.txt"
            
            # Download butonu
            st.download_button(
                label="📥 Planı İndir (TXT)",
                data=pdf_content,
                file_name=file_name,
                mime="text/plain",
                use_container_width=True
            )
            
            st.success("✅ Plan hazırlandı! İndir butonuna tıklayın.")
            
            # Yazdırma talimatı
            st.info("""
            📋 **Yazdırma Talimatları:**
            1. Dosyayı indirin
            2. Not Defteri veya Word ile açın  
            3. Ctrl+P ile yazdırın
            4. Kağıda çıkarıp çalışma masanıza koyun!
            """)

# === SUPABASE CACHE SİSTEMİ (Firebase Cache'in yerine) ===
class SupabaseCache:
    """Supabase işlemleri için cache sistemi"""
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 🚀 OPTİMİZE: 1 saat cache
    
    def get_users(self, limit_to_user=None):
        """🚀 OPTİMİZE: Cache'li ve lazy loading destekli kullanıcı verisi"""
        cache_key = "all_users" if not limit_to_user else f"user_{limit_to_user}"
        current_time = time.time()
        
        if (cache_key in self.cache and 
            current_time - self.cache[cache_key]['time'] < self.cache_duration):
            return self.cache[cache_key]['data']
            
        # Supabase'den çek
        try:
            if supabase_connected:
                if limit_to_user:
                    # Sadece belirli kullanıcıyı çek (Lazy Loading)
                    response = supabase.table('users').select('*').eq('username', limit_to_user).execute()
                    users_data = {limit_to_user: response.data[0] if response.data else {}} if response.data else {}
                else:
                    # Tüm kullanıcıları çek (Admin için)
                    response = supabase.table('users').select('*').execute()
                    users_data = {item['username']: item for item in response.data} if response.data else {}
                
                self.cache[cache_key] = {
                    'data': users_data,
                    'time': current_time
                }
                return users_data
        except Exception as e:
            st.warning(f"Supabase veri çekme hatası: {e}")
            return {}
    
    def get_user_data(self, username):
        """Cache'li tek kullanıcı verisi"""
        cache_key = f"user_{username}"
        current_time = time.time()
        
        if (cache_key in self.cache and 
            current_time - self.cache[cache_key]['time'] < self.cache_duration):
            return self.cache[cache_key]['data']
        
        # Supabase'den çek
        try:
            if supabase_connected:
                response = supabase.table('users').select('*').eq('username', username).execute()
                if response.data:
                    user_data = response.data[0]
                    self.cache[cache_key] = {
                        'data': user_data,
                        'time': current_time
                    }
                    return user_data
        except Exception as e:
            st.warning(f"Supabase kullanıcı verisi çekme hatası: {e}")
        
        return self.cache.get(cache_key, {}).get('data', {})
    
    def update_user_data(self, username, data):
        """Kullanıcı verisini güncelle + cache'i temizle"""
        try:
            if supabase_connected:
                # Supabase'de güncelle
                response = supabase.table('users').update(data).eq('username', username).execute()
                
                # Cache'i güncelle
                cache_key = f"user_{username}"
                if cache_key in self.cache:
                    self.cache[cache_key]['data'].update(data)
                    self.cache[cache_key]['time'] = current_time
                
                return True
        except Exception as e:
            st.warning(f"Supabase güncelleme hatası: {e}")
            return False
    
    def create_user(self, username, data):
        """Yeni kullanıcı oluştur"""
        try:
            if supabase_connected:
                user_data = {'username': username, **data}
                response = supabase.table('users').insert(user_data).execute()
                
                # Cache'i güncelle
                cache_key = f"user_{username}"
                self.cache[cache_key] = {
                    'data': user_data,
                    'time': time.time()
                }
                
                return True
        except Exception as e:
            st.warning(f"Supabase kullanıcı oluşturma hatası: {e}")
            return False
    
    def clear_cache(self, pattern=None):
        """Cache'i temizle"""
        if pattern:
            # Belirli pattern'a uyan cache'i temizle
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Tüm cache'i temizle
            self.cache.clear()

# Global cache objesi
supabase_cache = SupabaseCache()

# Supabase başlatma
supabase_connected = False
supabase_client = None

if SUPABASE_AVAILABLE:
    try:
        # Environment variable'lardan Supabase bilgilerini al
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            supabase_client = create_client(supabase_url, supabase_key)
            supabase_connected = True
            st.success("✅ Supabase bağlantısı kuruldu!")
        else:
            st.warning("⚠️ Supabase environment variable'ları bulunamadı!")
            supabase_connected = False
    except Exception as e:
        st.warning(f"⚠️ Supabase bağlantısı kurulamadı: {e}")
        supabase_connected = False
        supabase_client = None
else:
    st.info("📦 Supabase modülü yüklenmedi - yerel test modu aktif")

# FALLBACK: Geçici test kullanıcıları
if not supabase_connected:
    st.info("🔧 Yerel test sistemi kullanılıyor...")
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
    st.success("✅ Test kullanıcıları hazırlandı!")

# Supabase veritabanı fonksiyonları
def load_users_from_supabase(force_refresh=False):
    """🚀 OPTİMİZE EDİLMİŞ: Session state ile agresif cache"""
    # Session state'te varsa ve force refresh yoksa direkt döndür
    if not force_refresh and 'users_db' in st.session_state and st.session_state.users_db:
        return st.session_state.users_db
    
    # Supabase cache'den çek
    users_data = supabase_cache.get_users()
    
    # Session state'e kaydet
    st.session_state.users_db = users_data
    
    return users_data

def update_user_in_supabase(username, data):
    """🚀 OPTİMİZE EDİLMİŞ: Cache'li kullanıcı verisi güncelleme"""
    # Session state'i güncelle
    if 'users_db' in st.session_state:
        if username in st.session_state.users_db:
            st.session_state.users_db[username].update(data)
        else:
            # Yeni kullanıcı - ekle
            st.session_state.users_db[username] = data
    
    # Haftalık plan cache'ini temizle
    if 'weekly_plan_cache' in st.session_state:
        del st.session_state.weekly_plan_cache
    
    # Cache'li güncelleme
    return supabase_cache.update_user_data(username, data)

def create_user_in_supabase(username, data):
    """Yeni kullanıcı oluştur"""
    try:
        if supabase_connected:
            return supabase_cache.create_user(username, data)
        else:
            # Session state'e ekle (fallback)
            if 'fallback_users' in st.session_state:
                st.session_state.fallback_users[username] = data
            return True
    except Exception as e:
        st.error(f"Kullanıcı oluşturma hatası: {e}")
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
FIELDNAMES = ['username', 'password', 'name', 'surname', 'grade', 'field', 'target_department', 'tyt_last_net', 'tyt_avg_net', 'ayt_last_net', 'ayt_avg_net', 
              # Net aralık ve seviye bilgileri
              'tyt_last_range', 'tyt_avg_range', 'ayt_last_range', 'ayt_avg_range',
              'tyt_last_level', 'tyt_avg_level', 'ayt_last_level', 'ayt_avg_level',
              # Diğer alanlar
              'learning_style', 'learning_style_scores', 'created_at',  'detailed_nets', 'deneme_analizleri','study_program', 'topic_progress', 'topic_completion_dates', 'yks_survey_data', 'pomodoro_history'
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
# 🚀 OPTİMİZE EDİLMİŞ ARKA PLAN SİSTEMİ (Download Azaltma)
BACKGROUND_STYLES = {
    "Tıp": {
        "gradient": "linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)",
        "icon": "🩺"
    },
    "Mühendislik": {
        "gradient": "linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)",
        "icon": "⚙️"
    },
    "Hukuk": {
        "gradient": "linear-gradient(135deg, #556270 0%, #4ecdc4 100%)",
        "icon": "⚖️"
    },
    "Öğretmenlik": {
        "gradient": "linear-gradient(135deg, #ffd89b 0%, #19547b 100%)",
        "icon": "👨‍🏫"
    },
    "İktisat": {
        "gradient": "linear-gradient(135deg, #834d9b 0%, #d04ed6 100%)",
        "icon": "📈"
    },
    "Mimarlık": {
        "gradient": "linear-gradient(135deg, #5614b0 0%, #dbd65c 100%)",
        "icon": "🏛️"
    },
    "Psikoloji": {
        "gradient": "linear-gradient(135deg, #654ea3 0%, #eaafc8 100%)",
        "icon": "🧠"
    },
    "Diş Hekimliği": {
        "gradient": "linear-gradient(135deg, #ff5e62 0%, #ff9966 100%)",
        "icon": "🦷"
    },
    # 🎖️ MSÜ (Askeri) Alt Kategorileri - Resim yok, gradient var
    "MSÜ - Kara Astsubay Meslek Yüksekokulu": {
        "gradient": "linear-gradient(135deg, #2d5016 0%, #4a7c59 50%, #5e8b3a 100%)",
        "icon": "🎖️"
    },
    "MSÜ - Deniz Astsubay Yüksekokulu": {
        "gradient": "linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 50%, #075985 100%)",
        "icon": "⚓"
    },
    "MSÜ - Hava Astsubay Yüksekokulu": {
        "gradient": "linear-gradient(135deg, #1e40af 0%, #60a5fa 50%, #2563eb 100%)",
        "icon": "✈️"
    },
    
    # 🎓 TYT (Meslek Yüksekokulu) Alt Kategorileri - Resim yok, gradient var
    "TYT - Bilgisayar Programcılığı": {
        "gradient": "linear-gradient(135deg, #1e1b4b 0%, #5b21b6 50%, #7c3aed 100%)",
        "icon": "💻"
    },
    "TYT - Anestezi Teknisyenliği": {
        "gradient": "linear-gradient(135deg, #064e3b 0%, #059669 50%, #10b981 100%)",
        "icon": "🏥"
    },
    "TYT - Acil Tıp Teknisyenliği (ATT)": {
        "gradient": "linear-gradient(135deg, #991b1b 0%, #dc2626 50%, #ef4444 100%)",
        "icon": "🚑"
    },
    "TYT - Çocuk Gelişimi": {
        "gradient": "linear-gradient(135deg, #ec4899 0%, #f472b6 50%, #fbbf24 100%)",
        "icon": "👶"
    },
    "TYT - Ebe": {
        "gradient": "linear-gradient(135deg, #be185d 0%, #ec4899 50%, #f9a8d4 100%)",
        "icon": "🤱"
    },
    "TYT - Hemato terapilişi": {
        "gradient": "linear-gradient(135deg, #7f1d1d 0%, #dc2626 50%, #fecaca 100%)",
        "icon": "🩸"
    },
    "TYT - Tıbbi Laboratuvar Teknikleri": {
        "gradient": "linear-gradient(135deg, #065f46 0%, #059669 50%, #a7f3d0 100%)",
        "icon": "🔬"
    },
    "TYT - Tıbbi Görüntüleme Teknikleri": {
        "gradient": "linear-gradient(135deg, #374151 0%, #6b7280 50%, #d1d5db 100%)",
        "icon": "📱"
    },
    "TYT - Radyoterapi": {
        "gradient": "linear-gradient(135deg, #581c87 0%, #7c3aed 50%, #c4b5fd 100%)",
        "icon": "⚡"
    },
    "TYT - Diyaliz": {
        "gradient": "linear-gradient(135deg, #0f766e 0%, #14b8a6 50%, #99f6e4 100%)",
        "icon": "💧"
    },
    "TYT - Diş Protés Teknisyenliği": {
        "gradient": "linear-gradient(135deg, #0369a1 0%, #0ea5e9 50%, #bae6fd 100%)",
        "icon": "🦷"
    },
    "TYT - Otomotiv Teknolojisi": {
        "gradient": "linear-gradient(135deg, #374151 0%, #4b5563 50%, #9ca3af 100%)",
        "icon": "🚗"
    },
    "TYT - Elektrik-Elektronik Teknolojisi": {
        "gradient": "linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%)",
        "icon": "⚡"
    },
    "TYT - Makine Teknolojisi": {
        "gradient": "linear-gradient(135deg, #1f2937 0%, #374151 50%, #6b7280 100%)",
        "icon": "⚙️"
    },
    "TYT - İnşaat Teknolojisi": {
        "gradient": "linear-gradient(135deg, #a16207 0%, #d97706 50%, #fbbf24 100%)",
        "icon": "🏗️"
    },
    "TYT - Diğer Meslek Yüksekokulu": {
        "gradient": "linear-gradient(135deg, #4338ca 0%, #6366f1 50%, #a5b4fc 100%)",
        "icon": "🎓"
    },
    
    "Varsayılan": {
        "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "icon": "🎯"
    }
}

# 🎯 Hedef Bölüm Zorluk Sistemi (Net Aralığına Göre)
TARGET_DEPARTMENT_DIFFICULTY = {
    "Tıp": {
        "difficulty_level": 5,  # En zor
        "required_nets": {"TYT": 115, "AYT": 75},
        "study_intensity": "maksimum",
        "weekly_topic_multiplier": 1.5
    },
    "Diş Hekimliği": {
        "difficulty_level": 5,
        "required_nets": {"TYT": 110, "AYT": 70},
        "study_intensity": "maksimum", 
        "weekly_topic_multiplier": 1.4
    },
    "Mühendislik": {
        "difficulty_level": 4,
        "required_nets": {"TYT": 105, "AYT": 65},
        "study_intensity": "yüksek",
        "weekly_topic_multiplier": 1.3
    },
    "Hukuk": {
        "difficulty_level": 4,
        "required_nets": {"TYT": 100, "AYT": 60},
        "study_intensity": "yüksek",
        "weekly_topic_multiplier": 1.2
    },
    "Mimarlık": {
        "difficulty_level": 3,
        "required_nets": {"TYT": 95, "AYT": 55},
        "study_intensity": "orta-yüksek",
        "weekly_topic_multiplier": 1.1
    },
    "Psikoloji": {
        "difficulty_level": 3,
        "required_nets": {"TYT": 90, "AYT": 50},
        "study_intensity": "orta-yüksek",
        "weekly_topic_multiplier": 1.1
    },
    "İktisat": {
        "difficulty_level": 2,
        "required_nets": {"TYT": 85, "AYT": 45},
        "study_intensity": "orta",
        "weekly_topic_multiplier": 1.0
    },
    "Öğretmenlik": {
        "difficulty_level": 2,
        "required_nets": {"TYT": 80, "AYT": 40},
        "study_intensity": "orta",
        "weekly_topic_multiplier": 1.0
    },
    "Varsayılan": {
        "difficulty_level": 1,
        "required_nets": {"TYT": 75, "AYT": 35},
        "study_intensity": "normal",
        "weekly_topic_multiplier": 0.9
    }
}

# 📚 Sınıf Bazlı Program Sistemi
GRADE_BASED_PROGRAMS = {
    "11. Sınıf": {
        "focus": "temel_kavramlar_ve_konu_ogrenme",
        "study_pace": "normal",
        "weekly_topic_base": 12,  # 11. sınıf için daha fazla konu
        "review_ratio": 0.2,  # %20 tekrar, %80 yeni konu
        "exam_frequency": "ayda_1",
        "special_notes": "Temel kavramları sağlam öğrenme dönemi"
    },
    "12. Sınıf": {
        "focus": "konu_tamamlama_ve_deneme_odak",
        "study_pace": "hızlandırılmış", 
        "weekly_topic_base": 10,  # Standart
        "review_ratio": 0.3,  # %30 tekrar, %70 yeni konu
        "exam_frequency": "2_haftada_1",
        "special_notes": "Konu tamamlama ve deneme stratejileri dönemi"
    },
    "Mezun": {
        "focus": "eksik_kapama_ve_performans_artırma",
        "study_pace": "maksimum",
        "weekly_topic_base": 8,  # Daha az yeni konu, daha fazla tekrar
        "review_ratio": 0.4,  # %40 tekrar, %60 yeni konu  
        "exam_frequency": "haftada_1",
        "special_notes": "Eksikleri kapatma ve performans maksimizasyonu dönemi"
    }
}

# 🎯 Konu Zorluk Puanlama Sistemi (1-5 arası)
TOPIC_DIFFICULTY_SYSTEM = {
    1: {"name": "Çok Kolay", "color": "#27ae60", "icon": "😊", "study_time": "15-20 dk"},
    2: {"name": "Kolay", "color": "#2ecc71", "icon": "🙂", "study_time": "20-30 dk"},
    3: {"name": "Orta", "color": "#f39c12", "icon": "😐", "study_time": "30-45 dk"},
    4: {"name": "Zor", "color": "#e67e22", "icon": "😰", "study_time": "45-60 dk"},
    5: {"name": "Çok Zor", "color": "#e74c3c", "icon": "😱", "study_time": "60+ dk"}
}

# Kullanıcı verilerini getiren fonksiyon
def get_user_data():
    """Kullanıcı verilerini güvenli şekilde getirir"""
    current_username = st.session_state.get('current_user')
    if not current_username:
        return {}
    
    if supabase_connected:
        return supabase_cache.get_user_data(current_username)
    else:
        # Fallback: Session state veya fallback users'dan al
        fallback_users = st.session_state.get('fallback_users', {})
        if current_username in fallback_users:
            return fallback_users[current_username]
        
        users_db = st.session_state.get('users_db', {})
        return users_db.get(current_username, {})
    
    return {}

# Diğer tüm fonksiyonlar ve içerik buraya eklenmeli
# Bu dosya devam edecek...

# Ana uygulama fonksiyonu
def main():
    """Ana uygulama fonksiyonu"""
    
    # Admin panel kontrolü
    admin_mode = st.sidebar.checkbox("🔐 Admin Panel", help="Öğretmen/Veli girişi")
    
    if admin_mode:
        if not check_admin_access():
            admin_login()
            return
        else:
            show_admin_dashboard()
            return

# Bu kısa versiyon - tam dosya çok büyük olduğu için tüm içeriği ekleyeceğim
# Devamını sonraki mesajlarda ekleyeceğim
print("Supabase'e geçiş dosyası oluşturuluyor...")
print("Dosya boyutu çok büyük olduğu için parçalar halinde oluşturacağım...")

# Ana uygulamayı başlat
if __name__ == "__main__":
    main()# Bu 26 bin satırlık dosyanın Supabase'e tam geçişi - Devam ediyor...

# Fonksiyonlar eklenmeli...
# Daha fazla içerik eklenmeli...

# === KULLANICI VERİSİ YÖNETİM FONKSİYONLARI ===
def login_user(username, password):
    """Kullanıcı girişi"""
    if supabase_connected:
        try:
            # Supabase'den kullanıcı verilerini çek
            response = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
            if response.data:
                user_data = response.data[0]
                st.session_state.current_user = username
                st.session_state.user_data = user_data
                
                # Son giriş tarihini güncelle
                current_time = datetime.now().isoformat()
                update_user_in_supabase(username, {'last_login': current_time})
                
                return True
            return False
        except Exception as e:
            st.error(f"Giriş hatası: {e}")
            return False
    else:
        # Fallback: Session state veya fallback users
        fallback_users = st.session_state.get('fallback_users', {})
        if username in fallback_users and fallback_users[username]['password'] == password:
            user_data = fallback_users[username]
            st.session_state.current_user = username
            st.session_state.user_data = user_data
            return True
        return False

def register_user(username, password, name, surname, grade, field, target_department):
    """Yeni kullanıcı kaydı"""
    user_data = {
        'username': username,
        'password': password,
        'name': name,
        'surname': surname,
        'grade': grade,
        'field': field,
        'target_department': target_department,
        'created_at': datetime.now().isoformat(),
        'student_status': 'ACTIVE',
        'topic_progress': '{}',
        'topic_completion_dates': '{}',
        'topic_repetition_history': '{}',
        'topic_mastery_status': '{}',
        'pending_review_topics': '{}',
        'total_study_time': 0,
        'created_by': 'USER_REGISTRATION'
    }
    
    return create_user_in_supabase(username, user_data)

def get_user_data():
    """Kullanıcı verilerini getir"""
    current_username = st.session_state.get('current_user')
    if not current_username:
        return {}
    
    return supabase_cache.get_user_data(current_username)

# === HAFTALIK PLAN YÖNETİMİ ===
def get_current_week_number():
    """Mevcut hafta numarasını hesapla"""
    current_date = datetime.now()
    start_date = datetime(current_date.year, 1, 1)  # Yıl başı
    week_number = ((current_date - start_date).days // 7) + 1
    return min(week_number, 16)  # Maksimum 16 hafta

def generate_weekly_plan(user_data):
    """Kullanıcı için haftalık plan oluştur"""
    current_week = get_current_week_number()
    
    # Basit haftalık plan
    weekly_plan = {
        'current_week': current_week,
        'new_topics': [],
        'review_topics': [],
        'focus_areas': [],
        'target_hours': 40  # Haftalık hedef saat
    }
    
    # Kullanıcı alanına göre konuları ekle
    user_field = user_data.get('field', 'Sayısal')
    
    # Basit konu örnekleri
    if user_field == 'Sayısal':
        weekly_plan['new_topics'] = [
            {'subject': 'TYT Matematik', 'topic': 'Türev', 'difficulty': 4, 'priority': 'high'},
            {'subject': 'TYT Fizik', 'topic': 'Newton Yasaları', 'difficulty': 3, 'priority': 'medium'},
            {'subject': 'TYT Kimya', 'topic': 'Mol Kavramı', 'difficulty': 2, 'priority': 'low'}
        ]
    elif user_field == 'Eşit Ağırlık':
        weekly_plan['new_topics'] = [
            {'subject': 'TYT Matematik', 'topic': 'Fonksiyonlar', 'difficulty': 3, 'priority': 'high'},
            {'subject': 'TYT Türkçe', 'topic': 'Paragraf', 'difficulty': 2, 'priority': 'medium'},
            {'subject': 'TYT Tarih', 'topic': 'Kurtuluş Savaşı', 'difficulty': 3, 'priority': 'medium'}
        ]
    
    return weekly_plan

# === ANA UYGULAMA AKIŞI ===
def show_login_page():
    """Giriş sayfası"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 40px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h1 style="margin: 0; color: white;">🎯 YKS Takip Sistemi</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Supabase ile çalışan YKS Öğrenci Takip Sistemi</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("👤 Kullanıcı Adı")
            password = st.text_input("🔒 Şifre", type="password")
            
            if st.form_submit_button("🚀 Giriş Yap", use_container_width=True):
                if login_user(username, password):
                    st.success("✅ Giriş başarılı! Yönlendiriliyor...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Hatalı kullanıcı adı veya şifre!")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("👤 Kullanıcı Adı")
            new_password = st.text_input("🔒 Şifre", type="password")
            name = st.text_input("📝 Ad")
            surname = st.text_input("📝 Soyad")
            grade = st.selectbox("🎓 Sınıf", ["11. Sınıf", "12. Sınıf", "Mezun"])
            field = st.selectbox("📚 Alan", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])
            target_department = st.text_input("🎯 Hedef Bölüm")
            
            if st.form_submit_button("✅ Kayıt Ol", use_container_width=True):
                if register_user(new_username, new_password, name, surname, grade, field, target_department):
                    st.success("✅ Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
                else:
                    st.error("❌ Kayıt başarısız!")

def show_main_dashboard():
    """Ana dashboard"""
    user_data = get_user_data()
    
    if not user_data:
        st.error("❌ Kullanıcı verileri bulunamadı!")
        return
    
    # Hoş geldin mesajı
    check_and_show_welcome_message(user_data.get('name', 'Öğrenci'))
    
    # Başlık
    user_field = user_data.get('field', 'Belirtilmemiş')
    target_dept = user_data.get('target_department', 'Belirtilmemiş')
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 30px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h2 style="margin: 0; color: white;">🎯 {user_data.get('name', 'Öğrenci')} {user_data.get('surname', '')}</h2>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Alan: {user_field} | Hedef: {target_dept}</p>
        <p style="margin: 5px 0 0 0; opacity: 0.8;">Sınıf: {user_data.get('grade', 'Belirtilmemiş')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Ana sekmeler
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Haftalık Plan", "📊 İlerleme", "📚 Konu Takibi", "⚙️ Ayarlar"])
    
    with tab1:
        show_weekly_plan_tab(user_data)
    
    with tab2:
        show_progress_tab(user_data)
    
    with tab3:
        show_topic_tracking_tab(user_data)
    
    with tab4:
        show_settings_tab(user_data)

def show_weekly_plan_tab(user_data):
    """Haftalık plan sekmesi"""
    st.markdown("## 📋 Haftalık Plan")
    
    # Haftalık plan oluştur
    weekly_plan = generate_weekly_plan(user_data)
    
    # Plan özet bilgileri
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📅 Mevcut Hafta", f"{weekly_plan['current_week']}/16")
    with col2:
        st.metric("📚 Yeni Konular", len(weekly_plan['new_topics']))
    with col3:
        st.metric("🔄 Tekrar Konular", len(weekly_plan['review_topics']))
    with col4:
        st.metric("⏱️ Hedef Saat", f"{weekly_plan['target_hours']}h")
    
    st.markdown("---")
    
    # Yeni konular
    if weekly_plan['new_topics']:
        st.markdown("### 🎯 Bu Haftanın Yeni Konuları")
        
        for i, topic in enumerate(weekly_plan['new_topics'], 1):
            priority_color = {
                'high': '#dc3545',
                'medium': '#fd7e14', 
                'low': '#28a745'
            }.get(topic.get('priority', 'medium'), '#6c757d')
            
            st.markdown(f"""
            <div style="border-left: 4px solid {priority_color}; padding: 15px; margin: 10px 0; 
                        background-color: #f8f9fa; border-radius: 5px;">
                <h4 style="margin: 0; color: #333;">{i}. {topic['subject']} - {topic['topic']}</h4>
                <p style="margin: 5px 0; color: #666;">Zorluk: {topic.get('difficulty', 3)}/5 | Öncelik: {topic.get('priority', 'medium')}</p>
            </div>
            """, unsafe_allow_html=True)

def show_progress_tab(user_data):
    """İlerleme sekmesi"""
    st.markdown("## 📊 İlerleme Takibi")
    
    # Örnek grafikler ve istatistikler
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Haftalık Çalışma Saati")
        # Örnek veri
        hours_data = [20, 25, 30, 35, 40, 38, 42]
        st.line_chart(hours_data)
    
    with col2:
        st.markdown("### 🎯 Konu Tamamlanma Oranı")
        # Örnek pasta grafiği verisi
        completion_data = {
            'Tamamlanan': 65,
            'Devam Eden': 25,
            'Başlanmamış': 10
        }
        st.bar_chart(completion_data)

def show_topic_tracking_tab(user_data):
    """Konu takibi sekmesi"""
    st.markdown("## 📚 Konu Takibi")
    
    # Konu ekleme formu
    with st.form("add_topic_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            subject = st.selectbox("📖 Ders", [
                "TYT Matematik", "TYT Türkçe", "TYT Tarih", "TYT Coğrafya",
                "TYT Fizik", "TYT Kimya", "TYT Biyoloji", "AYT Matematik"
            ])
        
        with col2:
            topic_name = st.text_input("📝 Konu Adı")
        
        topic_detail = st.text_area("📋 Konu Detayları (Opsiyonel)")
        difficulty = st.slider("⚡ Zorluk (1-5)", 1, 5, 3)
        
        if st.form_submit_button("✅ Konu Ekle"):
            # Konuyu kullanıcı verilerine ekle
            if topic_name:
                topic_data = {
                    'subject': subject,
                    'topic': topic_name,
                    'detail': topic_detail,
                    'difficulty': difficulty,
                    'status': 'started',
                    'added_date': datetime.now().isoformat()
                }
                
                # Kullanıcı verilerini güncelle
                current_progress = user_data.get('topic_progress', '{}')
                if isinstance(current_progress, str):
                    import json
                    current_progress = json.loads(current_progress)
                
                current_progress[topic_name] = topic_data
                update_user_in_supabase(user_data['username'], {'topic_progress': json.dumps(current_progress)})
                
                st.success("✅ Konu eklendi!")
                st.rerun()
    
    st.markdown("---")
    
    # Mevcut konular
    st.markdown("### 📋 Mevcut Konular")
    topic_progress = user_data.get('topic_progress', '{}')
    if isinstance(topic_progress, str):
        import json
        topic_progress = json.loads(topic_progress)
    
    if topic_progress:
        for topic_name, topic_data in topic_progress.items():
            if isinstance(topic_data, dict):
                status_color = {
                    'started': '#ffc107',
                    'completed': '#28a745',
                    'paused': '#dc3545'
                }.get(topic_data.get('status', 'started'), '#6c757d')
                
                st.markdown(f"""
                <div style="border: 1px solid {status_color}; padding: 10px; margin: 5px 0; 
                            border-radius: 5px; background-color: white;">
                    <h5 style="margin: 0; color: #333;">{topic_data.get('subject', 'Bilinmiyor')} - {topic_name}</h5>
                    <p style="margin: 5px 0; color: #666;">Zorluk: {topic_data.get('difficulty', 3)}/5</p>
                    <span style="background-color: {status_color}; color: white; padding: 3px 8px; 
                                 border-radius: 3px; font-size: 0.8em;">{topic_data.get('status', 'started').upper()}</span>
                </div>
                """, unsafe_allow_html=True)

def show_settings_tab(user_data):
    """Ayarlar sekmesi"""
    st.markdown("## ⚙️ Ayarlar")
    
    # Profil güncelleme
    with st.form("update_profile_form"):
        st.markdown("### 👤 Profil Bilgileri")
        
        new_name = st.text_input("📝 Ad", value=user_data.get('name', ''))
        new_surname = st.text_input("📝 Soyad", value=user_data.get('surname', ''))
        new_target = st.text_input("🎯 Hedef Bölüm", value=user_data.get('target_department', ''))
        new_field = st.selectbox("📚 Alan", 
                               ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"],
                               index=["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"].index(user_data.get('field', 'Sayısal')))
        
        if st.form_submit_button("✅ Profili Güncelle"):
            updated_data = {
                'name': new_name,
                'surname': new_surname,
                'target_department': new_target,
                'field': new_field
            }
            
            if update_user_in_supabase(user_data['username'], updated_data):
                st.success("✅ Profil güncellendi!")
                st.rerun()
            else:
                st.error("❌ Profil güncelleme başarısız!")
    
    st.markdown("---")
    
    # Hesap işlemleri
    st.markdown("### 🔧 Hesap İşlemleri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.clear()
            st.success("✅ Başarıyla çıkış yapıldı!")
            time.sleep(1)
            st.rerun()
    
    with col2:
        if st.button("🗑️ Verileri Temizle", use_container_width=True):
            empty_data = {
                'topic_progress': '{}',
                'topic_completion_dates': '{}',
                'total_study_time': 0
            }
            update_user_in_supabase(user_data['username'], empty_data)
            st.success("✅ Veriler temizlendi!")
            st.rerun()

# === ADMİN PANELİ ===
def show_admin_dashboard():
    """Admin panel ana sayfa"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 25px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h2 style="margin: 0; color: white;">🏛️ Admin Paneli</h2>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Öğrenci Takip Sistemi Yönetimi</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Genel istatistikler
    if supabase_connected:
        try:
            # Tüm kullanıcıları getir
            response = supabase.table('users').select('*').execute()
            all_users = response.data if response.data else []
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Toplam Kullanıcı", len(all_users))
            
            with col2:
                active_users = len([u for u in all_users if u.get('student_status') == 'ACTIVE'])
                st.metric("✅ Aktif Kullanıcı", active_users)
            
            with col3:
                fields_count = {}
                for user in all_users:
                    field = user.get('field', 'Belirtilmemiş')
                    fields_count[field] = fields_count.get(field, 0) + 1
                
                most_common_field = max(fields_count, key=fields_count.get) if fields_count else "Yok"
                st.metric("📚 En Popüler Alan", most_common_field)
            
            with col4:
                total_study_time = sum([u.get('total_study_time', 0) for u in all_users])
                st.metric("⏱️ Toplam Çalışma", f"{total_study_time}h")
            
            # Kullanıcı listesi
            st.markdown("### 👥 Kullanıcı Listesi")
            
            if all_users:
                # Kullanıcıları tablo olarak göster
                user_data_for_table = []
                for user in all_users:
                    user_data_for_table.append({
                        'Kullanıcı Adı': user.get('username', ''),
                        'Ad Soyad': f"{user.get('name', '')} {user.get('surname', '')}",
                        'Alan': user.get('field', ''),
                        'Sınıf': user.get('grade', ''),
                        'Hedef': user.get('target_department', ''),
                        'Durum': user.get('student_status', ''),
                        'Kayıt Tarihi': user.get('created_at', '')[:10] if user.get('created_at') else ''
                    })
                
                st.dataframe(user_data_for_table, use_container_width=True)
            else:
                st.info("📝 Henüz hiç kullanıcı kaydı yok.")
        
        except Exception as e:
            st.error(f"❌ Veri çekme hatası: {e}")
    else:
        st.warning("⚠️ Supabase bağlantısı yok - sadece test verileri gösteriliyor")

# Ana uygulamayı başlat
def main():
    """Ana uygulama fonksiyonu"""
    
    # Admin panel kontrolü
    admin_mode = st.sidebar.checkbox("🔐 Admin Panel", help="Yönetici girişi")
    
    if admin_mode:
        if not check_admin_access():
            admin_login()
            return
        else:
            show_admin_dashboard()
            return
    
    # Normal kullanıcı kontrolü
    if 'current_user' not in st.session_state:
        show_login_page()
        return
    
    # Ana dashboard
    show_main_dashboard()

# Ana uygulamayı çalıştır
if __name__ == "__main__":
    main()
