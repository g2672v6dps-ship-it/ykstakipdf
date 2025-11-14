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
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    firestore = None

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

# === ADMIN DASHBOARD FONKSİYONLARI ===

def get_real_student_data_for_admin():
    """Gerçek öğrenci verilerini Firebase'den çek ve admin paneli için formatla"""
    from datetime import datetime, timedelta
    import json
    
    # Firebase'den kullanıcı verilerini al
    if 'users_db' not in st.session_state:
        st.session_state.users_db = load_users_from_firebase()
    
    users_db = st.session_state.users_db
    students = []
    

    if users_db:
        st.sidebar.write(f"• Kullanıcılar: {list(users_db.keys())}")
    
    if not users_db:
        st.warning("⚠️ Hiç öğrenci verisi bulunamadı!")
        st.info("💡 Firebase'den veri çekilemedi veya hiç kayıt yapılmamış.")
        return []
    
    for username, user_data in users_db.items():
        # Sadece gerçek öğrenci verilerini al (admin hariç)
        if username in ["admin", "adminYKS2025"]:
            continue
            
        # Veri kontrolü
        name = user_data.get('name', 'İsimsiz Öğrenci')
        surname = user_data.get('surname', '')
        full_name = f"{name} {surname}".strip()
        
        # Son giriş tarihi
        last_login_str = user_data.get('last_login')
        if last_login_str:
            try:
                last_login = datetime.fromisoformat(last_login_str.replace('Z', '+00:00'))
            except:
                last_login = datetime.now() - timedelta(days=30)
        else:
            last_login = datetime.now() - timedelta(days=30)
        
        # Haftalık performans hesaplama (varsa gerçek verilerden)
        weekly_progress = user_data.get('weekly_progress', {})
        if weekly_progress:
            # Gerçek ilerleme verisi varsa hesapla
            completed_topics = sum([len(progress.get('completed_topics', [])) 
                                  for progress in weekly_progress.values()])
            total_topics = sum([len(progress.get('planned_topics', [])) 
                              for progress in weekly_progress.values()])
            if total_topics > 0:
                weekly_performance = int((completed_topics / total_topics) * 100)
            else:
                weekly_performance = 0
        else:
            # Veri yoksa ortalama değer ver
            weekly_performance = 65
            
        # Çalışma saatleri (varsa gerçek verilerden)
        total_hours = user_data.get('total_study_hours', 0)
        if total_hours == 0:
            # Veri yoksa tahmin et
            total_hours = weekly_performance // 2 + 20
            
        # Deneme sayısı
        exam_count = user_data.get('exam_count', 0)
        if exam_count == 0:
            exam_count = max(1, weekly_performance // 20)
        
        # Durum belirleme
        days_since_login = (datetime.now() - last_login).days
        status = "Aktif" if days_since_login <= 7 else "Pasif"
        
        student = {
            "username": username,
            "name": full_name if full_name != "İsimsiz Öğrenci" else username,
            "field": user_data.get('field', 'Belirtilmemiş'),
            "last_login": last_login,
            "weekly_performance": weekly_performance,
            "total_hours": total_hours,
            "exam_count": exam_count,
            "status": status,
            "grade": user_data.get('grade', '12. Sınıf'),
            "target": user_data.get('target', 'Belirtilmemiş')
        }
        students.append(student)
    
    # Performansa göre sırala (yüksekten düşüğe)
    students.sort(key=lambda x: x['weekly_performance'], reverse=True)
    
    return students

def generate_mock_student_data():
    """Örnek öğrenci verileri oluştur"""
    import random
    from datetime import datetime, timedelta
    
    names = ["Ahmet Yılmaz", "Fatma Kaya", "Mehmet Öz", "Ayşe Demir", "Ali Çelik", 
             "Zeynep Aktaş", "Murat Şahin", "Selin Yıldız", "Emre Koç", "Büşra Arslan",
             "Cem Özkan", "Esra Polat", "Burak Avcı", "Nur Turan", "Kaan Doğan"]
    
    fields = ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"]
    
    students = []
    for i, name in enumerate(names):
        last_login = datetime.now() - timedelta(days=random.randint(0, 7))
        weekly_performance = random.randint(45, 95)
        
        student = {
            "id": i+1,
            "name": name,
            "field": random.choice(fields),
            "last_login": last_login,
            "weekly_performance": weekly_performance,
            "total_hours": random.randint(25, 65),
            "exam_count": random.randint(2, 8),
            "status": "Aktif" if last_login > datetime.now() - timedelta(days=3) else "Pasif"
        }
        students.append(student)
    
    return students

def show_admin_dashboard():
    """Admin dashboard ana sayfa"""
    # Çıkış butonu
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🚪 Çıkış", type="secondary"):
            admin_logout()
    
    # Dashboard başlık
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 25px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h1 style="margin: 0; color: white;">🏛️ YKS Admin Paneli</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Öğretmen/Veli Takip Sistemi</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tab sistemi oluştur
    tab1, tab2 = st.tabs(["📊 Öğrenci Takip", "👨‍🏫 Koç Onay Sistemi"])
    
    with tab1:
        show_student_tracking_panel()
    
    with tab2:
        admin_coach_approval_panel()

def show_student_tracking_panel():
    """Öğrenci takip paneli (eski admin dashboard içeriği)"""
    # GERÇEKFirebase verilerini çek
    students = get_real_student_data_for_admin()
    
    # Genel İstatistikler
    st.markdown("## 📊 Genel Durum")
    
    if not students:
        st.warning("⚠️ Hiç öğrenci verisi bulunamadı!")
        st.info("💡 Sistem henüz öğrenci kaydı yapmadığınız veya veri çekilemediği anlamına gelir.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    active_students = len([s for s in students if s['status'] == 'Aktif'])
    avg_performance = sum([s['weekly_performance'] for s in students]) / len(students) if students else 0
    total_hours = sum([s['total_hours'] for s in students])
    
    with col1:
        st.metric("👥 Toplam Öğrenci", len(students))
    with col2:
        st.metric("✅ Aktif Öğrenci", active_students)
    with col3:
        st.metric("📈 Ortalama Başarı", f"%{avg_performance:.1f}")
    with col4:
        st.metric("⏱️ Toplam Çalışma", f"{total_hours}h")
    
    # Öğrencilerin gerçek alan bilgilerini topla
    available_fields = list(set([s['field'] for s in students if s['field'] != 'Belirtilmemiş']))
    field_options = ["Tümü"] + sorted(available_fields)
    
    # Öğrenci Listesi
    st.markdown("---")
    st.markdown("## 👥 Öğrenci Listesi")
    
    # Filtreleme
    col1, col2, col3 = st.columns(3)
    with col1:
        field_filter = st.selectbox("🎯 Alan Filtresi", field_options)
    with col2:
        status_filter = st.selectbox("📊 Durum Filtresi", ["Tümü", "Aktif", "Pasif"])
    with col3:
        performance_filter = st.selectbox("🎯 Performans", ["Tümü", "Yüksek (80+)", "Orta (60-79)", "Düşük (<60)"])
    
    # Öğrenci tablosu
    filtered_students = students.copy()
    
    if field_filter != "Tümü":
        filtered_students = [s for s in filtered_students if s['field'] == field_filter]
    if status_filter != "Tümü":
        filtered_students = [s for s in filtered_students if s['status'] == status_filter]
    if performance_filter != "Tümü":
        if performance_filter == "Yüksek (80+)":
            filtered_students = [s for s in filtered_students if s['weekly_performance'] >= 80]
        elif performance_filter == "Orta (60-79)":
            filtered_students = [s for s in filtered_students if 60 <= s['weekly_performance'] < 80]
        elif performance_filter == "Düşük (<60)":
            filtered_students = [s for s in filtered_students if s['weekly_performance'] < 60]
    
    # Tablo görünümü
    if filtered_students:
        for student in filtered_students:
            performance = student['weekly_performance']
            
            # Performansa göre renk
            if performance >= 80:
                color = "#d4edda"
                text_color = "#155724"
                status_emoji = "🚀"
            elif performance >= 60:
                color = "#d1ecf1"
                text_color = "#0c5460" 
                status_emoji = "📈"
            else:
                color = "#fff3cd"
                text_color = "#856404"
                status_emoji = "⚠️"
            
            # Durum emoji
            activity_emoji = "🟢" if student['status'] == 'Aktif' else "🔴"
            
            st.markdown(f"""
            <div style="background: {color}; padding: 15px; border-radius: 10px; margin: 8px 0;
                        border-left: 4px solid {text_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: {text_color}; font-size: 16px;">
                            {activity_emoji} {student['name']}
                        </strong>
                        <br>
                        <span style="color: {text_color}; opacity: 0.8;">
                            📚 {student['field']} • 🎯 {student['target']} • 🏫 {student['grade']}
                            <br>
                            📅 Son Giriş: {student['last_login'].strftime('%d.%m.%Y')}
                        </span>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: {text_color}; font-weight: bold; font-size: 18px;">
                            {status_emoji} %{performance}
                        </div>
                        <div style="color: {text_color}; opacity: 0.8; font-size: 12px;">
                            ⏱️ {student['total_hours']}h | 📝 {student['exam_count']} deneme
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Filtrelere uygun öğrenci bulunamadı.")
    
    # Uyarılar
    st.markdown("---")
    st.markdown("## 🚨 Dikkat Gerektiren Durumlar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚠️ Düşük Performans")
        low_performance = [s for s in students if s['weekly_performance'] < 60]
        if low_performance:
            for student in low_performance:
                st.warning(f"🚨 {student['name']}: %{student['weekly_performance']}")
        else:
            st.success("✅ Düşük performanslı öğrenci yok")
    
    with col2:
        st.markdown("### 📴 Pasif Öğrenciler")
        inactive_students = [s for s in students if s['status'] == 'Pasif']
        if inactive_students:
            for student in inactive_students:
                days_ago = (datetime.now() - student['last_login']).days
                st.error(f"🔴 {student['name']}: {days_ago} gün önce")
        else:
            st.success("✅ Tüm öğrenciler aktif")

# Ana uygulama akışına admin sekmesi ekle
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

def play_pomodoro_finished_sound():
    """🚀 OPTİMİZE EDİLMİŞ: Sadece görsel bildirim - Download azalması"""
    st.markdown("""
    <script>
    // Sadece görsel bildirim - Base64 ses dosyası yok
    const notification = document.createElement('div');
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.background = '#ff6b6b';
    notification.style.color = 'white';
    notification.style.padding = '15px 20px';
    notification.style.borderRadius = '8px';
    notification.style.boxShadow = '0 4px 12px rgba(255, 107, 107, 0.3)';
    notification.style.zIndex = '9999';
    notification.style.transform = 'translateX(0)';
    notification.style.transition = 'transform 0.5s ease-out';
    notification.innerHTML = '🎉 Pomodoro Tamamlandı! Mola zamanı! 🔔';
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }, 3000);
    </script>
    """, unsafe_allow_html=True)

def play_break_start_sound():
    """🚀 OPTİMİZE EDİLMİŞ: Mola bildirimı - Download azalması"""
    st.markdown("""
    <script>
    // Sadece görsel bildirim - Base64 ses dosyası yok
    const notification = document.createElement('div');
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.background = '#28a745';
    notification.style.color = 'white';
    notification.style.padding = '15px 20px';
    notification.style.borderRadius = '8px';
    notification.style.boxShadow = '0 4px 12px rgba(40, 167, 69, 0.3)';
    notification.style.zIndex = '9999';
    notification.innerHTML = '⏰ Mola Başladı! Rahatlamaya zaman! 😌';
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
    </script>
    """, unsafe_allow_html=True)

# 🚀 FIREBASE CACHE SİSTEMİ (Download Optimizasyonu)
class FirebaseCache:
    """Firebase işlemleri için cache sistemi"""
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 🚀 OPTİMİZE: 1 saat cache (önceden 5 dakika)
    
    def get_users(self, limit_to_user=None):
        """🚀 OPTİMİZE: Cache'li ve lazy loading destekli kullanıcı verisi"""
        cache_key = "all_users" if not limit_to_user else f"user_{limit_to_user}"
        current_time = time.time()
        
        if (cache_key in self.cache and 
            current_time - self.cache[cache_key]['time'] < self.cache_duration):
            return self.cache[cache_key]['data']
            
        # Firebase'den çek
        try:
            if limit_to_user:
                # Sadece belirli kullanıcıyı çek (Lazy Loading)
                if firebase_connected:
                    users_data = {limit_to_user: firestore_db.collection("users").document(limit_to_user).get().to_dict()}
                    if users_data[limit_to_user] is None:
                        users_data = {}
                else:
                    users_data = {}
            else:
                # Tüm kullanıcıları çek (Admin için)
                users_data = {}
                if firebase_connected:
                    docs = firestore_db.collection("users").get()
                    for doc in docs:
                        users_data[doc.id] = doc.to_dict()
            
            self.cache[cache_key] = {
                'data': users_data,
                'time': current_time
            }
            return users_data
        except:
            return {}
    
    def get_user_data(self, username):
        """Cache'li tek kullanıcı verisi"""
        cache_key = f"user_{username}"
        current_time = time.time()
        
        if (cache_key in self.cache and 
            current_time - self.cache[cache_key]['time'] < self.cache_duration):
            return self.cache[cache_key]['data']
        
        # Firebase'den çek
        try:
            if firebase_connected:
                doc = firestore_db.collection("users").document(username).get()
                if doc.exists:
                    data = doc.to_dict()
                    self.cache[cache_key] = {
                        'data': data,
                        'time': current_time
                    }
                    return data
        except:
            pass
        
        return self.cache.get(cache_key, {}).get('data', {})
    
    def update_user_data(self, username, data):
        """Kullanıcı verisini güncelle + cache'i temizle"""
        try:
            if firebase_connected:
                firestore_db.collection("users").document(username).set(data, merge=True)
            
            # Cache'i güncelle
            cache_key = f"user_{username}"
            if cache_key in self.cache:
                self.cache[cache_key]['data'].update(data)
                self.cache[cache_key]['time'] = time.time()
            
            return True
        except:
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
firebase_cache = FirebaseCache()

# 🚀 OPTİMİZE EDİLMİŞ GRAFİK CACHE SİSTEMİ
@lru_cache(maxsize=32)
def create_cached_chart(chart_type, *args, **kwargs):
    """Grafik oluşturma cache'i"""
    if chart_type == "performance":
        return {"type": "performance_chart", "data": args, "kwargs": kwargs}
    elif chart_type == "progress":
        return {"type": "progress_chart", "data": args, "kwargs": kwargs}
    else:
        return {"type": "default_chart", "data": args, "kwargs": kwargs}

# Firebase başlatma
firebase_connected = False
firestore_db = None

if FIREBASE_AVAILABLE:
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
            
            firebase_admin.initialize_app(cred)
            firestore_db = firestore.client()
        
        firebase_connected = True
   
        
    except Exception as e:
        st.warning(f"⚠️ Firebase bağlantısı kurulamadı: {e}")
        firebase_connected = False
        firestore_db = None
else:
    st.info("📦 Firebase modülü yüklenmedi - yerel test modu aktif")

# FALLBACK: Geçici test kullanıcıları
if not firebase_connected:
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

# Firebase veritabanı fonksiyonları
def load_users_from_firebase(force_refresh=False):
    """🚀 OPTİMİZE EDİLMİŞ: Session state ile agresif cache"""
    # Session state'te varsa ve force refresh yoksa direkt döndür
    if not force_refresh and 'users_db' in st.session_state and st.session_state.users_db:
        return st.session_state.users_db
    
    # Firebase cache'den çek
    users_data = firebase_cache.get_users()
    
    # Session state'e kaydet
    st.session_state.users_db = users_data
    
    return users_data

def update_user_in_firebase(username, data):
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
    return firebase_cache.update_user_data(username, data)

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
        "gradient": "linear-gradient(135deg, #064e3b 0%, #059669 0%, #10b981 100%)",
        "icon": "🏥"
    },
    "TYT - Acil Tıp Teknisyenliği (ATT)": {
        "gradient": "linear-gradient(135deg, #991b1b 0%, #dc2626 0%, #ef4444 100%)",
        "icon": "🚑"
    },
    "TYT - Çocuk Gelişimi": {
        "gradient": "linear-gradient(135deg, #ec4899 0%, #f472b6 0%, #fbbf24 100%)",
        "icon": "👶"
    },
    "TYT - Ebe": {
        "gradient": "linear-gradient(135deg, #be185d 0%, #ec4899 0%, #f9a8d4 100%)",
        "icon": "🤱"
    },
    "TYT - Hemato terapilişi": {
        "gradient": "linear-gradient(135deg, #7f1d1d 0%, #dc2626 0%, #fecaca 100%)",
        "icon": "🩸"
    },
    "TYT - Tıbbi Laboratuvar Teknikleri": {
        "gradient": "linear-gradient(135deg, #065f46 0%, #059669 0%, #a7f3d0 100%)",
        "icon": "🔬"
    },
    "TYT - Tıbbi Görüntüleme Teknikleri": {
        "gradient": "linear-gradient(135deg, #374151 0%, #6b7280 0%, #d1d5db 100%)",
        "icon": "📱"
    },
    "TYT - Radyoterapi": {
        "gradient": "linear-gradient(135deg, #581c87 0%, #7c3aed 0%, #c4b5fd 100%)",
        "icon": "⚡"
    },
    "TYT - Diyaliz": {
        "gradient": "linear-gradient(135deg, #0f766e 0%, #14b8a6 0%, #99f6e4 100%)",
        "icon": "💧"
    },
    "TYT - Diş Protés Teknisyenliği": {
        "gradient": "linear-gradient(135deg, #0369a1 0%, #0ea5e9 0%, #bae6fd 100%)",
        "icon": "🦷"
    },
    "TYT - Otomotiv Teknolojisi": {
        "gradient": "linear-gradient(135deg, #374151 0%, #4b5563 0%, #9ca3af 100%)",
        "icon": "🚗"
    },
    "TYT - Elektrik-Elektronik Teknolojisi": {
        "gradient": "linear-gradient(135deg, #fbbf24 0%, #f59e0b 0%, #d97706 100%)",
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
        "gradient": "linear-gradient(135deg, #4338ca 0%, #6366f1 0%, #a5b4fc 100%)",
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

# YKS Konuları Sistemi - Detaylı ve Kapsamlı
YKS_TOPICS = {
    "TYT Matematik": {
        "Temel Kavramlar": {
            "Sayılar ve İşlemler": ["Doğal Sayılar", "Tam Sayılar", "Rasyonel Sayılar", "İrrasyonel Sayılar", "Gerçek Sayılar"],
            "Temel İşlemler": ["Toplama", "Çıkarma", "Çarpma", "Bölme", "Üslü Sayılar", "Köklü Sayılar"],
            "Mutlak Değer": ["Mutlak Değer Tanımı", "Mutlak Değer Özellikleri", "Mutlak Değerli Denklemler"],
            "Bölme ve Bölünebilme": ["Bölme Algoritması", "Bölünebilme Kuralları", "EBOB-EKOK"],
            "Aralık Kavramı": ["Açık Aralık", "Kapalı Aralık", "Yarı Açık Aralık", "Sonsuz Aralık"]
        },
        "Cebir": {
            "İfadeler": ["Harfli İfadeler", "Polinomlar", "Çarpanlara Ayırma"],
            "Denklemler": ["Birinci Dereceden Denklemler", "İkinci Dereceden Denklemler", "Rasyonel Denklemler", "İrrsiyonel Denklemler"],
            "Eşitsizlikler": ["Birinci Dereceden Eşitsizlikler", "İkinci Dereceden Eşitsizlikler", "Rasyonel Eşitsizlikler"],
            "Sistemler": ["İki Bilinmeyenli Denklem Sistemleri", "Üç Bilinmeyenli Denklem Sistemleri"]
        },
        "Fonksiyonlar": {
            "Fonksiyon Kavramı": ["Fonksiyon Tanımı", "Fonksiyon Türleri", "Fonksiyon İşlemleri"],
            "Grafik ve Yorumlama": ["Grafik Okuma", "Grafik Çizme", "Grafik Yorumlama"],
            "Doğrusal Fonksiyonlar": ["Doğru Denklemi", "Eğim", "Doğrusal Sistemler"],
            "Parabol": ["Parabol Denklemi", "Tepe Noktası", "Kökler", "Simetri Ekseni"]
        },
        "Üstel ve Logaritma": {
            "Üstel Fonksiyonlar": ["Üstel İfadeler", "Üstel Denklemler"],
            "Logaritma": ["Logaritma Tanımı", "Logaritma Özellikleri", "Logaritma Denklemleri"]
        },
        "Trigonometri": {
            "Açı Ölçüleri": ["Derece", "Radyan", "Grad"],
            "Trigonometrik Fonksiyonlar": ["Sinüs", "Kosinüs", "Tanjant", "Kotanjant"],
            "Trigonometrik Özdeşlikler": ["Temel Özdeşlikler", "Toplam-Fark Formülleri", "Yarım Açı Formülleri"],
            "Trigonometrik Denklemler": ["Sinüs ve Kosinüs Denklemleri", "Tanjant Denklemleri"]
        },
        "Analitik Geometri": {
            "Nokta ve Doğru": ["Nokta Koordinatları", "İki Nokta Arası Uzaklık", "Doğru Denklemi"],
            "Parabol": ["Parabol Denklemi", "Tepe Noktası", "Odak", "Doğrultman"],
            "Elips": ["Elips Denklemi", "Odak Noktaları", "Eksen Uzunlukları"],
            "Hiperbol": ["Hiperbol Denklemi", "Odak Noktaları", "Asimptotlar"]
        }
    },
    "TYT Türkçe": {
        "Ses Bilgisi": {
            "Fonemler": ["Ünlüler", "Ünsüzler", "Ünlü-Ünsüz Uyumu"],
            "Ses Olayları": ["Düşme", "Benzeşme", "İyileşme", "Ulama"],
            "Hece Yapısı": ["Açık Hece", "Kapalı Hece", "Hece Sınırları"]
        },
        "Kelime Bilgisi": {
            "Kelime Türleri": ["İsim", "Sıfat", "Zamir", "Fiil", "Zarf", "Edat"],
            "Kelime Anlamları": ["Gerçek Anlam", "Mecaz Anlam", "Terim Anlam"],
            "Kelime Türetme": ["Kök", "Gövde", "Ek", "Türetme Yolları"]
        },
        "Cümle Bilgisi": {
            "Cümle Türleri": ["Yapı Bakımından", "Yüklem Türü Bakımından", "Anlam Bakımından"],
            "Cümle Öğeleri": ["Özne", "Yüklem", "Nesne", "Yer Tamlayıcısı", "Zarf Tamlayıcısı"],
            "Cümle Çözümleme": ["Basit Cümle", "Birleşik Cümle", "Sıralı Cümle", "Bağlaçlı Cümle"]
        },
        "Anlam Bilgisi": {
            "Anlam ilişkileri": ["Eş Anlam", "Karşıt Anlam", "Eş Sesli Kelimeler"],
            "Cümlede Anlam": ["Gerçek Anlam", "Mecaz Anlam", "Terim Anlam"],
            "Deyimler": ["Deyim Kavramı", "Deyim Anlamları", "Deyim Kullanımı"]
        },
        "Paragraf": {
            "Paragraf Özellikleri": ["Ana Düşünce", "Yardımcı Düşünceler", "Başlık", "Konu"],
            "Paragraf Türleri": ["Bilgilendirici Metin", "Edebi Metin", "Haber Metni", "Reklam Metni"],
            "Paragraf Soruları": ["Ana Düşünce", "Yardımcı Düşünce", "Başlık Bulma", "Kelime Anlamı"]
        },
        "Edebiyat Bilgisi": {
            "Edebiyat Dönemleri": ["Eski Türk Edebiyatı", "Divan Edebiyatı", "Halk Edebiyatı", "Tanzimat Dönemi", "Servet-i Fünun", "Milli Edebiyat", "Cumhuriyet Dönemi"],
            "Edebiyat Türleri": ["Dizi", "Hikaye", "Tiyatro", "Makale", "Fıkra", "Mektup"],
            "Şiir Bilgisi": ["Şiir Türleri", "Şiirde Ahenk", "Şiirde Hayal", "Şiirde Duygu"]
        }
    },
    "TYT Fizik": {
        "Fizik Bilimine Giriş": {
            "Fizik Nedir": ["Fiziğin Tanımı", "Fizik Alanları", "Fizik ve Diğer Bilimler"],
            "Ölçü ve Birimler": ["SI Birimleri", "Temel ve Türetilmiş Büyüklükler", "Boyut Analizi"],
            "Vektörler": ["Vektör Tanımı", "Vektör İşlemleri", "Vektör Bileşenleri"]
        },
        "Mekanik": {
            "Hareket": ["Hız ve Sürat", "İvme", "Hareket Denklemleri", "Grafik Yorumlama"],
            "Kuvvet ve Hareket": ["Newton'un Hareket Yasaları", "Sürtünme Kuvveti", "İş-Enerji-Güç"],
            "Dairesel Hareket": ["Merkezcil Kuvvet", "Periyot ve Frekans", "Yatay-Dikey Dairesel Hareket"],
            "İmpuls-Momentum": ["İmpuls", "Momentum", "Momentumun Korunumu"]
        },
        "Elektrik ve Manyetizma": {
            "Elektrik": ["Elektrik Yükü", "Elektrik Alan", "Elektrik Potansiyel", "Kondansatör"],
            "Elektrik Devreleri": ["Akım", "Gerilim", "Direnç", "Ohm Yasası", "Kirchhoff Yasaları"],
            "Manyetizma": ["Manyetik Alan", "Manyetik Kuvvet", "Elektromanyetik İndüksiyon"]
        },
        "Dalgalar ve Titreşimler": {
            "Mekanik Dalgalar": ["Dalga Kavramı", "Dalga Türleri", "Dalga Boyu ve Frekans"],
            "Ses Dalgaları": ["Sesin Özellikleri", "Doppler Olayı", "Rezonans"],
            "Elektromanyetik Dalgalar": ["Işık", "Elektromanyetik Spektrum", "Dalga-Parçacık İkiliği"]
        },
        "Termodinamik": {
            "Sıcaklık ve Isı": ["Sıcaklık Kavramı", "Isı ve IsıTransferi", "Öz Isı"],
            "Termodinamik Yasalar": ["0. Yasa", "1. Yasa", "2. Yasa", "3. Yasa"],
            "Gaz Yasaları": ["İdeal Gaz Yasası", "Gazların Hareketi", "Boltzmann Sabiti"]
        },
        "Modern Fizik": {
            "Atom Fiziği": ["Atom Modelleri", "Kuantum Teorisi", "Atom Spektrumu"],
            "Nükleer Fizik": ["Radyoaktivite", "Nükleer Reaksiyonlar", "Nükleer Enerji"],
            "Relativite": ["Özel Relativite", "Genel Relativite", "Einstein'ın E=mc² Denklemi"]
        }
    },
    "TYT Kimya": {
        "Kimya Bilimine Giriş": {
            "Kimya Nedir": ["Kimyanın Tanımı", "Kimya Alanları", "Kimya ve Diğer Bilimler"],
            "Madde ve Özellikleri": ["Maddenin Hâlleri", "Saf Madde-Karışım", "Çözeltiler"],
            "Atom Yapısı": ["Atom Kavramı", "Atom Modelleri", "Periyodik Sistem"]
        },
        "Periyodik Sistem": {
            "Element Özellikleri": ["Atom Numarası", "Kütle Numarası", "Elektron Dizilişi"],
            "Periyodik Özellikler": ["Atom Yarıçapı", "İyonlaşma Enerjisi", "Elektronegatiflik"],
            "Kimyasal Bağlar": ["İyonik Bağlar", "Kovalent Bağlar", "Metalik Bağlar"]
        },
        "Mol Kavramı": {
            "Mol Hesaplamaları": ["Avogadro Sayısı", "Mol-Kütle İlişkisi", "Mol-Hacim İlişkisi"],
            "Kimyasal Formüller": ["Deneysel Formül", "Molekül Formülü", "Yapısal Formül"],
            "Kimyasal Hesaplamalar": ["Yüzde Bileşim", "Saflık", "Verim"]
        },
        "Gazlar": {
            "Gaz Özellikleri": ["Basınç", "Hacim", "Sıcaklık", "Miktar"],
            "Gaz Yasaları": ["Boyle Yasası", "Charles Yasası", "Avogadro Yasası", "İdeal Gaz Yasası"],
            "Gaz Karışımları": ["Kısmi Basınç", "Dalton Yasası", "Graham Yasası"]
        },
        "Çözeltiler": {
            "Çözelti Türleri": ["Doymuş-Doymamış", "Aşırı Doymuş", "Seçici Çözeltiler"],
            "Derişim Hesaplamaları": ["Kütle Yüzdesı", "Molarite", "Molalite", "ppm"],
            "Çözelti Özellikleri": ["Osmoz", "Donma Noktası Alçalması", "Kaynama Noktası Yükselmesi"]
        },
        "Kimyasal Türler": {
            "Asit-Baz": ["Asit-Baz Tanımları", "pH-pOH", "Asit-Baz Titrasyonları"],
            "Redoks": ["Oksidasyon-Redüksiyon", "Yükseltgenme Basamakları", "Redoks Denkleştirme"],
            "Çökelek Reaksiyonları": ["Çözünürlük", "Ksp", "Çökelek Oluşumu"]
        },
        "Organik Kimya": {
            "Karbon Kimyası": ["Karbon Bağları", "Hibritleşme", "İzomerlik"],
            "Organik Bileşikler": ["Alkan", "Alken", "Alkin", "Aromatik Bileşikler"],
            "Organik Reaksiyonlar": ["Yanma", "Substitüsyon", "Elektrofilik Eklenme"]
        }
    },
    "TYT Tarih": {
        "İlk Çağ Uygarlıkları": {
            "Mezopotamya": ["Sümerler", "Babiller", "Asurlar"],
            "Mısır": ["Eski Krallık", "Orta Krallık", "Yeni Krallık"],
            "Anadolu": ["Hititler", "Frigler", "Lidyalılar"],
            "İran": ["Ahameniş İmparatorluğu", "Sasani İmparatorluğu"],
            "Çin": ["Chou Hanedanı", "Chin Hanedanı", "Tang Hanedanı"]
        },
        "Antik Yunan ve Roma": {
            "Yunanistan": ["Şehir Devletleri", "Atina Demokrasisi", "Makedonya Krallığı"],
            "Roma": ["Roma Krallığı", "Roma Cumhuriyeti", "Roma İmparatorluğu"],
            "İslam Öncesi Araplar": ["Çöl Kültürü", "Arap Yarımadası", "Ticaret"]
        },
        "İslam Öncesi ve İslam Tarihi": {
            "Hz. Muhammed": ["Doğumu", "Hayatı", "Vefatı"],
            "Dört Halife Dönemi": ["Ebu Bekir", "Ömer", "Osman", "Ali"],
            "Emeviler": ["Kuruluş", "Genişleme", "Çöküş"],
            "Abbasiler": ["Kuruluş", "Altın Çağ", "Çöküş"]
        },
        "Türk Tarihi": {
            "Orta Asya": ["Göktürkler", "Uygurlar", "Kırgızlar"],
            "Selçuklular": ["Kuruluş", "Anadolu Selçuklu", "Moğol İstilası"],
            "Osmanlı Öncesi": ["Beylikler", "Anadolu Birliği"],
            "Osmanlı Devleti": ["Kuruluş", "Yükseliş", "Duraklama", "Gerileme", "Yenileşme Hareketleri"]
        },
        "Osmanlı Devleti": {
            "Kuruluş Dönemi": ["Osman Bey", "Orhan Bey", "I. Murad", "Yıldırım Bayezid"],
            "Yükselme Dönemi": ["Fatih Sultan Mehmet", "Yavuz Sultan Selim", "Kanuni Sultan Süleyman"],
            "Duraklama Dönemi": ["III. Murad", "III. Mehmet", "I. Ahmet"],
            "Gerileme Dönemi": ["IV. Murad", "Köprülüler", "Lale Devri"],
            "Yenileşme": ["III. Selim", "II. Mahmut", "Tanzimat", "Meşrutiyet"]
        },
        "Türkiye Cumhuriyeti Tarihi": {
            "Milli Mücadele": ["Erzurum ve Sivas Kongreleri", "Amasya Genelgesi", "Mudanya Ateşkesi"],
            "Cumhuriyet Dönemi": ["Cumhuriyet'in İlanı", "İnönü Savaşları", "Kurtuluş Savaşı"],
            "Atatürk Dönemi": ["Reformlar", "Tek Parti Dönemi", "İkinci Dünya Savaşı"],
            "Çok Partili Dönem": ["DP", "27 Mayıs", "CHP-AP", "12 Mart", "12 Eylül"],
            "Günümüz Türkiye": ["1980 Sonrası", "1990'lı Yıllar", "2000'ler", "Günümüz"]
        }
    },
    "TYT Coğrafya": {
        "Coğrafya Bilimine Giriş": {
            "Coğrafya Nedir": ["Coğrafyanın Tanımı", "Doğal Coğrafya", "Beşeri Coğrafya"],
            "Koordinat Sistemi": ["Enlem-Boylam", "Paralel-Meridyen", "Zaman Hesaplamaları"],
            "Harita Bilgisi": ["Harita Elemanları", "Ölçek", "Projeksiyonlar"]
        },
        "Doğal Sistemler": {
            "Yer Şekilleri": ["Kaya Türleri", "Jeolojik Zamanlar", "Jeomorfolojik Süreçler"],
            "İklim": ["İklim Elemanları", "İklim Tipleri", "Türkiye'nin İklimi"],
            "Su Kaynakları": ["Yeraltı Suları", "Yüzey Suları", "Göller", "Akarsular"],
            "Toprak": ["Toprak Oluşumu", "Toprak Türleri", "Toprak Sorunları"]
        },
        "Bitki ve Hayvan Dünyası": {
            "Biyoçeşitlilik": ["Ekoloji", "Biyomlar", "Türkiye'nin Flora ve Faunası"],
            "Çevre Sorunları": ["Hava Kirliliği", "Su Kirliliği", "Toprak Kirliliği", "İklim Değişikliği"]
        },
        "Beşeri Coğrafya": {
            "Demografi": ["Nüfus Artışı", "Nüfus Piramidi", "Göçler"],
            "Yerleşme": ["Şehirleşme", "Kırsal Yerleşme", "Türkiye'de Yerleşme"],
            "Ekonomi": ["Tarım", "Hayvancılık", "Madencilik", "Sanayi", "Turizm", "Ulaştırma"]
        },
        "Türkiye Coğrafyası": {
            "Fiziki Özellikler": ["Konum", "Yükselti", "İklim", "Bitki Örtüsü", "Yer Şekilleri"],
            "İdari Bölünme": ["İller", "İlçeler", "Belediyeler"],
            "Bölgesel Kalkınma": ["Doğu-Batı Farkı", "Kırsal-Kent Farkı", "GAP", "DOKAP", "Karadeniz Projesi"]
        },
        "Çevre ve Toplum": {
            "Çevre Sorunları": ["Küresel Çevre Sorunları", "Türkiye'nin Çevre Sorunları"],
            "Doğal Afetler": ["Deprem", "Volkanizma", "Heyelan", "Sel"],
            "Çevre Politikaları": ["Çevre Koruma", "Sürdürülebilir Kalkınma", "Çevre Hukuku"]
        }
    },
    "AYT Matematik": {
        "Trigonometri": {
            "Trigonometrik Fonksiyonlar": ["Sinüs Fonksiyonu", "Kosinüs Fonksiyonu", "Tanjant Fonksiyonu", "Kotanjant Fonksiyonu"],
            "Trigonometrik Özdeşlikler": ["Temel Özdeşlikler", "Toplam-Fark Formülleri", "Yarım Açı Formülleri", "Dönüşüm Formülleri"],
            "Trigonometrik Denklemler": ["Sinüs Denklemleri", "Kosinüs Denklemleri", "Tanjant Denklemleri", "Trigonometrik Sistemler"]
        },
        "Logaritma": {
            "Logaritma Fonksiyonu": ["Logaritma Tanımı", "Logaritma Özellikleri", "Logaritma Fonksiyonunun Grafiği"],
            "Logaritma Denklemleri": ["Basit Logaritma Denklemleri", "Logaritma Sistemleri", "Üstel-Logaritma Denklemleri"],
            "Logaritma Eşitsizlikleri": ["Logaritma Eşitsizlik Kuralları", "Logaritma Eşitsizlik Çözümleri"]
        },
        "Diziler ve Seriler": {
            "Diziler": ["Dizi Kavramı", "Aritmetik Dizi", "Geometrik Dizi", "Dizi Sınırları"],
            "Seriler": ["Seri Kavramı", "Aritmetik Seriler", "Geometrik Seriler", "Seri Testleri"],
            "Limit ve Süreklilik": ["Fonksiyon Limiti", "Süreklilik", "Sağ-Sol Limitler"]
        },
        "Türev ve Uygulamaları": {
            "Türev Kavramı": ["Türev Tanımı", "Türev Alma Kuralları", "Zincir Kuralı"],
            "Türev Uygulamaları": ["Artma-Azalma", "Maksimum-Minimum", "Konkavlık-Konvekslik"],
            "L'Hôpital Kuralı": ["Belirsizlik Türleri", "L'Hôpital Uygulaması"]
        },
        "İntegral ve Uygulamaları": {
            "Belirsiz İntegral": ["İntegral Kavramı", "İntegral Alma Kuralları", "Kısmi İntegral"],
            "Belirli İntegral": ["Belirli İntegral Hesabı", "İntegral Özellikleri"],
            "İntegral Uygulamaları": ["Alan Hesabı", "Hacim Hesabı", "Fizik Uygulamaları"]
        },
        "Analitik Geometri": {
            "Doğru Analitiği": ["Doğru Denklemi", "İki Doğru Arasındaki Açı", "Nokta-Doğru Uzaklığı"],
            "Çember": ["Çember Denklemi", "Çember-Doğru Kesişimi", "Çemberlerin Kesişimi"],
            "Parabol": ["Parabol Denklemi", "Parabol-Doğru Kesişimi"]
        }
    },
    "AYT Fizik": {
        "Elektrik ve Manyetizma": {
            "Elektrik Alan": ["Elektrik Alan Kavramı", "Gauss Yasası", "Elektrik Potansiyel"],
            "Kondansatörler": ["Kondansatör Çeşitleri", "Kondansatörde Enerji", "Kondansatör Devreleri"],
            "Manyetik Alan": ["Akımın Manyetik Etkisi", "Manyetik Kuvvet", "Manyetik Akı"],
            "Elektromanyetik İndüksiyon": ["Faraday Yasası", "Lenz Yasası", "İndüksiyon Emk'sı"],
            "Elektromanyetik Dalgalar": ["Maxwell Denklemleri", "Elektromanyetik Spektrum", "Işık Hızı"]
        },
        "Dalgalar": {
            "Mekanik Dalgalar": ["Dalga Denklemi", "Dalga Boyu ve Frekans", "Dalgalarda Girişim", "Yansıma ve Kırılma"],
            "Ses Dalgaları": ["Ses Hızı", "Doppler Olayı", "Rezonans", "Ses Şiddeti"],
            "Elektromanyetik Dalgalar": ["Işık Dalgaları", "Yansıma", "Kırılma", "Girişim", "Kırınım"]
        },
        "Modern Fizik": {
            "Atom Fiziği": ["Bohr Atom Modeli", "Atom Enerji Seviyeleri", "Spektrum Çizgileri"],
            "Kuantum Mekaniği": ["Fotoelektrik Olayı", "Compton Saçılması", "De Broglie Dalgaları"],
            "Relativite": ["Özel Relativite", "Zaman Genişlemesi", "Uzunluk Büzülmesi", "E=mc²"],
            "Nükleer Fizik": ["Radyoaktif Bozunma", "Nükleer Reaksiyonlar", "Nükleer Enerji"]
        }
    },
    "AYT Kimya": {
        "Kimyasal Türler": {
            "Çözeltiler": ["Molarite", "Molalite", " ppm", "Çözünürlük", "Donma Noktası Alçalması", "Kaynama Noktası Yükselmesi"],
            "Asit-Baz Kimyası": ["pH ve pOH", "Asit-Baz Denge", "Hidroliz", "Tampon Çözeltiler"],
            "Redoks Reaksiyonları": ["Oksidasyon Sayıları", "Redoks Dengeleme", "Elektrokimya", "Galvanik Hücre"],
            "Çökelek Reaksiyonları": ["Ksp Hesaplamaları", "Çökelek Oluşumu", "Ayırma Yöntemleri"]
        },
        "Organik Kimya": {
            "Organik Bileşiklerin Sınıflandırılması": ["Alkanlar", "Alkenler", "Alkinler", "Aromatik Bileşikler"],
            "Fonksiyonel Gruplar": ["Alkoller", "Eterler", "Aldehitler", "Ketonlar", "Karboksilik Asitler", "Esterler"],
            "İzomerlik": ["Yapı İzomerleri", "Stereoizomerler", "Optik İzomerlik"],
            "Reaksiyon Mekanizmaları": ["Substitüsyon", "Elektrofilik Eklenme", "Eliminasyon", "Polimerleşme"]
        },
        "Kimyasal Hesaplamalar": {
            "Gaz Yasaları": ["İdeal Gaz Davranışı", "Gerçek Gazlar", "Gaz Karışımları"],
            "Termokimya": ["Reaksiyon Entalpisi", "Hess Yasası", "Bağ Enerjileri"],
            "Kimyasal Kinetik": ["Reaksiyon Hızı", "Hız Denklemi", "Aktivasyon Enerjisi"],
            "Kimyasal Denge": ["Denge Sabiti", "Le Chatelier Prensibi", "Denge Hesaplamaları"]
        }
    },
    "AYT Tarih": {
        "Osmanlı Devleti": {
            "Kuruluş": ["Osman Bey", "Fatih Öncesi Gelişmeler", "İmparatorluğa Dönüşüm"],
            "Yükselme": ["Fatih Sultan Mehmet", "Yavuz Sultan Selim", "Kanuni Sultan Süleyman"],
            "Klasik Dönem": ["Devlet Teşkilatı", "Ekonomik Yapı", "Kültürel Gelişmeler"],
            "Duraklama": ["Köprülüler Dönemi", "Savaşlar", "İsyanlar"],
            "Gerileme": ["Lale Devri", "1750-1850 Arası", "Dış Baskılar"],
            "Yenileşme": ["III. Selim", "II. Mahmut", "Tanzimat", "Meşrutiyet", "I. Dünya Savaşı"]
        },
        "Osmanlı'da Yenilikler": {
            "Askeri Yenilikler": ["Yeniçeri Ocağı", "Avrupa Askeri Sistemi", "Mühendishane", "Harbiye"],
            "Eğitim": ["Medrese", "Batı Tarzı Eğitim", "Darülfünun"],
            "Matbaa ve Basın": ["Matbaa Kuruluşu", "Basının Gelişmesi", "Gazete ve Dergi"],
            "Teknoloji": ["Bürokrasi", "Adliye", "Sağlık", "Ulaşım"]
        },
        "Milli Mücadele": {
            "Kurtuluş Savaşı": ["I. Dünya Savaşı Sonrası", "İtilaf İşgalleri", "Mütareke Dönemi"],
            "Kurtuluş Savaşı Süreci": ["Mustafa Kemal'in Samsun'a Çıkışı", "Kongreler", "TBMM'nin Açılması"],
            "Savaşlar": ["Doğu Cephesi", "Güney Cephesi", "İnönü Savaşları", "Sakarya Meydan Muharebesi", "Büyük Taarruz"],
            "Mudanya Ateşkesi": ["Mudanya Görüşmeleri", "Ateşkes Antlaşması", "Lozan Barış Antlaşması"]
        },
        "Cumhuriyet Dönemi": {
            "Cumhuriyet'in İlanı": ["Saltanatın Kaldırılması", "Cumhuriyet'in İlanı", "Hilafetin Kaldırılması"],
            "Atatürk İlkeleri": ["Cumhuriyetçilik", "Milliyetçilik", "Laiklik", "Devletçilik", "Halkçılık", "İnkılapçılık"],
            "Reformlar": ["Hukuk", "Eğitim", "Kültür", "Ekonomi", "Sosyal", "Siyasi"],
            "İnönü Dönemi": ["Tek Parti Sistemi", "2. Dünya Savaşı", "Çok Partiye Geçiş"],
            "Demokratikleşme": ["DP Dönemi", "27 Mayıs", "1970'ler", "12 Eylül", "1980 Sonrası"]
        },
        "Dünya Tarihi": {
            "Modern Avrupa": ["Rönesans", "Reformasyon", "Aydınlanma", "Fransız Devrimi"],
            "19. Yüzyıl": ["Sanayi Devrimi", "Milliyetçilik Akımları", "Sosyalizm"],
            "20. Yüzyıl": ["I. Dünya Savaşı", "II. Dünya Savaşı", "Soğuk Savaş", "Küreselleşme"]
        }
    },
    "AYT Coğrafya": {
        "Doğal Sistemler": {
            "İklim Sistemleri": ["Dünya İklim Tipleri", "Türkiye İklimi", "İklim Değişikliği"],
            "Su Sistemleri": ["Su Döngüsü", "Akarsu Havzaları", "Yeraltı Suları"],
            "Toprak Sistemleri": ["Toprak Oluşumu", "Toprak Tipleri", "Arazi Kullanımı"],
            "Bitki Örtüsü": ["Biyoçeşitlilik", "Flora", "Fauna", "Ekolojik Denge"]
        },
        "Beşeri ve Ekonomik Coğrafya": {
            "Nüfus Coğrafyası": ["Dünya Nüfus Dağılımı", "Nüfus Hareketleri", "Demografik Geçiş"],
            "Yerleşme": ["Şehirleşme", "Kırsal Yerleşme", "Kentsel Fonksiyonlar"],
            "Ekonomik Coğrafya": ["Birincil Sektör", "İkincil Sektör", "Üçüncül Sektör"],
            "Turizm": ["Turizm Türleri", "Turizm Bölgeleri", "Turizmin Etkileri"]
        },
        "Çevre ve Toplum": {
            "Çevre Sorunları": ["Küresel Sorunlar", "Bölgesel Sorunlar", "Çevre Koruma"],
            "Doğal Afetler": ["Deprem", "Volkanizma", "Hidro-meteorolojik Afetler"],
            "Sürdürülebilirlik": ["Çevre Politikaları", "Yeşil Teknoloji", "Ekolojik Ayak İzi"]
        },
        "Türkiye Coğrafyası": {
            "Bölgeler": ["Doğu Anadolu", "Güneydoğu Anadolu", "Akdeniz", "Ege", "Marmara", "Karadeniz", "İç Anadolu"],
            "Bölgesel Kalkınma": ["GAP", "DOKAP", "DAP", "Bölgesel Eşitsizlikler"],
            "Ulaştırma": ["Karayolları", "Demiryolları", "Denizyolu", "Havayolu", "Bor Hatları"]
        },
        "Çevre Politikaları": {
            "Küresel Çevre": ["BM Çevre Programı", "Paris Anlaşması", "Sürdürülebilir Kalkınma"],
            "Türkiye Çevre": ["Çevre Kanunu", "Ulusal Çevre Eylem Planı", "Çevre Bakanlığı"],
            "Teknoloji ve Çevre": ["Temiz Teknoloji", "Geri Dönüşüm", "Enerji Verimliliği"]
        }
    },
    "AYT Edebiyat": {
        "Divan Edebiyatı": {
            "Divan Şiiri": ["Gazel", "Kaside", "Rubaî", "Murabba"],
            "Divan Edebiyatı Özellikleri": ["Ahenk", "Hayal", "Mazmun", "Bend ve Mısra"],
            "Divan Şairleri": ["Fuzuli", "Baki", "Nâbî", "Nedim", "Şeyh Galip"],
            "Divan Nesri": ["Tezkire", "Siyahname", "Sahname"]
        },
        "Halk Edebiyatı": {
            "Halk Şiiri": ["Koşma", "Mani", "Türkü", "Nefes"],
            "Halk Hikayesi": ["Dede Korkut", "Köroğlu", "Şah İsmail"],
            "Halk Şairleri": ["Karacaoğlan", "Yunus Emre", "Pir Sultan Abdal"],
            "Halk Edebiyatı Özellikleri": ["Yalın Dil", "Doğallık", "Halkın Değerleri"]
        },
        "Tanzimat Dönemi": {
            "Tanzimat Edebiyatı": ["Batı Etkisi", "Şiir", "Tiyatro", "Roman"],
            "Tanzimat Yazarları": ["Şinasi", "Namık Kemal", "Ziya Paşa", "Ahmet Mithat"],
            "Tanzimat Özellikleri": ["Toplumcu Düşünce", "Dil Yenilikleri", "Fikir Akımları"]
        },
        "Servet-i Fünun": {
            "Servet-i Fünun Edebiyatı": ["Toplumcu Akım", "Parola", "Fikir ve Sanat"],
            "Servet-i Fünun Yazarları": ["Tevfik Fikret", "Cenap Şahabettin", "Halit Ziya"],
            "Servet-i Fünun Özellikleri": ["Sanat Sanat İçindir", "Kafye", "Refren", "Anlaşmazlık"]
        },
        "Milli Edebiyat": {
            "Milli Edebiyat Akımı": ["Milliyetçilik", "Halkçılık", "Yerel Renkler"],
            "Milli Edebiyat Yazarları": ["Mehmet Akif", "Ömer Seyfettin", "Ali Canip"],
            "Milli Edebiyat Özellikleri": ["Dil Birliği", "Halk Edebiyatı", "Milli Mücadele"]
        },
        "Cumhuriyet Dönemi": {
            "Cumhuriyet Şiiri": ["Memduh Şevket", "Orhan Veli", "Necip Fazıl", "Attila İlhan"],
            "Cumhuriyet Romanı": ["Halide Edib", "Reşat Nuri", "Ahmet Hamdi"],
            "Modern Türk Tiyatrosu": ["Cemil", "Güngör Dilmen", "Orhan Asena"],
            "Cumhuriyet Dönemi Özellikleri": ["Dil Devrimi", "Sanat Yönetimi", "Çağdaşlık"]
        },
        "Çağdaş Türk Edebiyatı": {
            "1980 Sonrası Edebiyat": ["Postmodernizm", "İkinci Yeni", "Toplumcu Gerçekçilik"],
            "Modern Türk Şiiri": ["Edip Cansever", "İlhan Berk", "Cemal Süreya"],
            "Çağdaş Roman": ["Orhan Pamuk", "Yaşar Kemal", "Elif Şafak"],
            "Çağdaş Tiyatro": ["Turan Oflazoğlu", "Cüneyt Gökçer", "Münir Özkul"]
        }
    },
    "AYT Felsefe": {
        "Felsefeye Giriş": {
            "Felsefe Nedir": ["Felsefe Tanımı", "Felsefe-Bilim İlişkisi", "Felsefe Tarihçesi"],
            "Felsefe Dalları": ["Ontoloji", "Epistemoloji", "Aksiyoloji"],
            "Felsefik Düşünce": ["Akıl", "Deneyim", "Sezgi", "Batıl İnanç"]
        },
        "Bilgi Felsefesi": {
            "Bilgi Türleri": ["Apriori-Bildi", "Analitik-Sentetik", "Sentez"],
            "Bilginin Kaynakları": ["Duyum", "Deneyim", "Akıl", "Sezgi"],
            "Bilgi Problemleri": ["Doğruluk", "Kesinlik", "Objektiflik", "Sübjektivite"]
        },
        "Ahlak Felsefesi": {
            "Ahlak Teorileri": ["Teleoloji", "Deontoloji", "Ahlak Sistemleri"],
            "Ahlak Kavramları": ["İyi", "Kötü", "Doğru", "Yanlış"],
            "Ahlak ve Toplum": ["Birey-Toplum İlişkisi", "Yasa-Ahlak", "Ahlaki Yargılar"]
        },
        "Siyaset Felsefesi": {
            "Devlet Teorileri": ["Platon", "Aristoteles", "Hobbes", "Rousseau"],
            "Güç ve Otorite": ["Meşruiyet", "İktidar", "Direnme Hakkı"],
            "Toplum Sözleşmesi": ["Doğa Durumu", "Toplum Sözleşmesi", "Sivil Otorite"]
        },
        "Estetik": {
            "Sanat Felsefesi": ["Sanatın Tanımı", "Sanat-Etsiyet", "Sanat-Toplum"],
            "Güzel Anlayışları": ["Klasisizm", "Romantizm", "Modernizm"],
            "Sanat Eleştirisi": ["Objektiflik", "Temsil", "İfade"]
        },
        "Varlık Felsefesi": {
            "Varlık Problemleri": ["Varlık-Bir Varlık", "Varlık-Varlık Olmayan"],
            "Varoluş Felsefesi": ["Varoluş", "Yabancılaşma", "Özgürlük"],
            "Felsefi Sistemler": ["Materyalizm", "İdealizm", "Pozitivizm", "Varoluşçuluk"]
        }
    }
}

# Fonksiyon tanımları
def get_categories(subject):
    """Belirli bir ders için kategorileri getir"""
    return list(YKS_TOPICS.get(subject, {}).keys())

def get_subcategories(subject, category):
    """Belirli bir ders ve kategori için alt kategorileri getir"""
    return list(YKS_TOPICS.get(subject, {}).get(category, {}).keys())

def get_topics_detailed(subject, category, subcategory):
    """Belirli bir ders, kategori ve alt kategori için konuları getir"""
    return YKS_TOPICS.get(subject, {}).get(category, {}).get(subcategory, [])

def get_user_data():
    """Güncel kullanıcı verilerini getir"""
    if 'current_user' not in st.session_state:
        return {}
    
    username = st.session_state.current_user
    
    # Cache'den veriyi çek
    user_data = firebase_cache.get_user_data(username)
    
    # Eğer cache'de yoksa Firestore'dan çek
    if not user_data and firebase_connected:
        try:
            doc = firestore_db.collection("users").document(username).get()
            if doc.exists:
                user_data = doc.to_dict()
        except:
            pass
    
    return user_data or {}

# Haftalık Progress Fonksiyonları (Firestore için)
def save_weekly_progress(username, progress_data):
    """Haftalık progress'i Firestore'a kaydet"""
    try:
        if firebase_connected:
            firestore_db.collection("weekly_progress").document(username).set(progress_data, merge=True)
        return True
    except:
        return False

def load_weekly_progress(username):
    """Haftalık progress'i Firestore'dan yükle"""
    try:
        if firebase_connected:
            doc = firestore_db.collection("weekly_progress").document(username).get()
            return doc.to_dict() if doc.exists else {}
        return {}
    except:
        return {}

def update_last_login(username):
    """Son giriş tarihini güncelle"""
    try:
        if firebase_connected:
            firestore_db.collection("users").document(username).set({
                'last_login': datetime.now().isoformat()
            }, merge=True)
        return True
    except:
        return False

# === KOÇ ONAY SİSTEMİ FONKSİYONLARI ===

def send_to_coach_approval(user_data, weekly_plan):
    """Öğrencinin haftalık konularını koça onay için gönder"""
    current_username = st.session_state.current_user
    
    # Haftalık konuları topla
    all_topics = weekly_plan.get('new_topics', []) + weekly_plan.get('review_topics', [])
    
    if not all_topics:
        st.warning("⚠️ Gönderilecek konu bulunamadı!")
        return False
    
    # Koç onay talebi oluştur
    approval_request = {
        'student_username': current_username,
        'student_name': user_data.get('name', 'İsimsiz Öğrenci'),
        'student_field': user_data.get('field', 'Belirtilmemiş'),
        'submission_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'topics': all_topics,
        'status': 'pending',  # pending, approved, rejected
        'coach_notes': '',
        'approved_date': None,
        'week_number': datetime.now().isocalendar()[1],
        'year': datetime.now().year
    }
    
    # Firebase'e kaydet veya session state'e ekle
    try:
        if firebase_connected:
            # Firebase'e kaydet
            approval_key = f"{current_username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            firestore_db.collection("coach_approvals").document(approval_key).set(approval_request, merge=True)
        else:
            # Session state'e kaydet (fallback)
            if 'coach_approval_requests' not in st.session_state:
                st.session_state.coach_approval_requests = {}
            approval_key = f"{current_username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.coach_approval_requests[approval_key] = approval_request
        
        # Öğrenci verilerine onay durumu ekle
        student_data = get_user_data()
        student_data['coach_approval_status'] = 'pending'
        student_data['last_submission_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_user_in_firebase(current_username, student_data)
        
        st.success("✅ Haftalık programınız koçunuza gönderildi! Onay bekleniyor...")
        return True
        
    except Exception as e:
        st.error(f"❌ Gönderim hatası: {e}")
        return False

def show_coach_approval_status(user_data):
    """Öğrenciye koç onay durumunu göster"""
    current_username = st.session_state.current_user
    
    # Onay durumunu kontrol et
    approval_status = user_data.get('coach_approval_status', 'none')
    
    if approval_status == 'pending':
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 20px; border-radius: 15px; margin: 20px 0; color: white; text-align: center;">
            <h3 style="margin: 0; color: white;">⏳ Koç Onayı Bekleniyor</h3>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Programınız koçunuza gönderildi, onay bekleniyor...</p>
        </div>
        """, unsafe_allow_html=True)
        
        last_submission = user_data.get('last_submission_date', 'Bilinmiyor')
        st.info(f"📅 Son gönderim: {last_submission}")
        
    elif approval_status == 'approved':
        st.markdown("""
        <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                    padding: 20px; border-radius: 15px; margin: 20px 0; color: white; text-align: center;">
            <h3 style="margin: 0; color: white;">✅ Koçunuz Tarafından Onaylandı</h3>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Programınız koçunuz tarafından onaylandı!</p>
        </div>
        """, unsafe_allow_html=True)
        
        approved_date = user_data.get('approval_date', 'Bilinmiyor')
        st.success(f"🎉 Onay tarihi: {approved_date}")
        
    elif approval_status == 'rejected':
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                    padding: 20px; border-radius: 15px; margin: 20px 0; color: white; text-align: center;">
            <h3 style="margin: 0; color: white;">⚠️ Programınız Revize Edildi</h3>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Koçunuz programınızda değişiklik yaptı, lütfen gözden geçirin.</p>
        </div>
        """, unsafe_allow_html=True)
        
        coach_notes = user_data.get('coach_notes', 'Koç notu bulunamadı')
        st.warning(f"📝 Koç notu: {coach_notes}")

def get_student_approval_requests():
    """Tüm öğrenci onay taleplerini getir (Admin için)"""
    try:
        if firebase_connected:
            # Firebase'den çek
            docs = firestore_db.collection("coach_approvals").get()
            processed_requests = []
            for doc in docs:
                request = doc.to_dict()
                if not request:
                    continue
                    
                # Eksik alanları tamamla
                if 'student_name' not in request:
                    # Eğer student_name yoksa, student_username'dan al
                    if 'student_username' in request:
                        student_username = request['student_username']
                        try:
                            user_doc = firestore_db.collection("users").document(student_username).get()
                            if user_doc.exists:
                                user_data = user_doc.to_dict()
                                request['student_name'] = user_data.get('name', student_username)
                            else:
                                request['student_name'] = student_username
                        except:
                            request['student_name'] = request.get('student_username', 'İsimsiz Öğrenci')
                    else:
                        request['student_name'] = 'İsimsiz Öğrenci'
                
                # Eğer student_username yoksa, başka alanlardan bul
                if 'student_username' not in request:
                    if 'student_name' in request:
                        request['student_username'] = request.get('student_name', 'unknown_user')
                    else:
                        request['student_username'] = 'unknown_user'
                
                # 🔧 EKSİK ALANLARI OTOMATİK TAMAMLA
                if 'submission_date' not in request:
                    request['submission_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if 'topics' not in request:
                    request['topics'] = []
                
                if 'student_field' not in request:
                    request['student_field'] = 'Belirtilmemiş'
                
                if 'status' not in request:
                    request['status'] = 'pending'
                
                # Debug: Hangi alanların eksik olduğunu göster
                missing_fields = []
                if 'student_name' not in request: missing_fields.append('student_name')
                if 'student_username' not in request: missing_fields.append('student_username')
                if 'submission_date' not in request: missing_fields.append('submission_date')
                if 'status' not in request: missing_fields.append('status')
                if 'topics' not in request: missing_fields.append('topics')
                
                if missing_fields:
                    st.warning(f"Talepten eksik alanlar: {missing_fields} - {request.get('student_name', 'Unknown')}")
                
                # Diğer gerekli alanları kontrol et ve tamamla
                required_fields = ['submission_date', 'status', 'topics', 'student_field']
                missing_core_fields = [field for field in required_fields if field not in request]
                
                if not missing_core_fields:
                    processed_requests.append(request)
                else:
                    st.warning(f"Eksik temel alanlar nedeniyle talep atlandı: {missing_core_fields}")
            
            if processed_requests:
                st.success(f"✅ {len(processed_requests)} adet onay talebi başarıyla yüklendi.")
            else:
                st.info("📝 Hiç geçerli onay talebi bulunamadı.")
            
            return processed_requests
        else:
            # Session state'den çek (fallback)
            requests = st.session_state.get('coach_approval_requests', {})
            if requests:
                st.info("📝 Session state'den onay talepleri yüklendi.")
            return list(requests.values()) if requests else []
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return []

def approve_student_topics(approval_key, approved_topics, coach_notes, status):
    """Koçun öğrenci programını onaylaması/reddetmesi"""
    try:
        if firebase_connected:
            # Firebase'de güncelle
            firestore_db.collection("coach_approvals").document(approval_key).update({
                'status': status,
                'coach_notes': coach_notes,
                'approved_topics': approved_topics,
                'approved_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 🔧 FİX: Student_username kontrolü ile öğrenci verilerini güncelle
            doc = firestore_db.collection("coach_approvals").document(approval_key).get()
            if doc.exists:
                approval_data = doc.to_dict()
                # Student_username'i güvenli bir şekilde al
                student_username = approval_data.get('student_username', '')
                
                # Eğer student_username yoksa approval_key'den çıkar
                if not student_username and approval_key:
                    try:
                        student_username = approval_key.split('_')[0]
                    except:
                        student_username = 'unknown_user'
                
                # Student_username bulunduysa kullanıcı verilerini güncelle
                if student_username and student_username != 'unknown_user':
                    student_data = {
                        'coach_approval_status': status,
                        'coach_notes': coach_notes,
                        'approval_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'approved_topics': approved_topics
                    }
                    firestore_db.collection("users").document(student_username).set(student_data, merge=True)
                    
                    # 🔥 GÜÇLÜ CACHE TEMİZLE: Öğrencinin tüm cache'lerini temizle
                    if 'users_db' in st.session_state and student_username in st.session_state.users_db:
                        # Cache'deki user_data'yı güncelle
                        st.session_state.users_db[student_username].update(student_data)
                    
                    # Firebase cache'i güvenli temizle
                    if hasattr(st.session_state, 'firebase_cache'):
                        try:
                            # FirebaseCache objesinin clear metodu olup olmadığını kontrol et
                            if hasattr(st.session_state.firebase_cache, 'clear'):
                                st.session_state.firebase_cache.clear()
                            else:
                                # clear metodu yoksa, cache'i yeniden başlat
                                st.session_state.firebase_cache = type('obj', (object,), {})()
                        except Exception as cache_error:
                            pass                # Cache temizleme hatası olsa bile onay işlemini devam ettir
                            st.warning(f"Cache temizleme hatası: {cache_error}")
                    
                    # 🔄 SESSION STATE GÜNCELLEME: Tüm related cache'leri temizle
                    if 'user_data' in st.session_state and st.session_state.user_data.get('username') == student_username:
                        st.session_state.user_data.update(student_data)
                    
                    # Debug: Cache temizlendi mesajı
                    st.success(f"🔄 {student_username} için cache temizlendi, onay durumu güncellenmeli!")
        else:
            # Session state'de güncelle
            if 'coach_approval_requests' in st.session_state and approval_key in st.session_state.coach_approval_requests:
                st.session_state.coach_approval_requests[approval_key].update({
                    'status': status,
                    'coach_notes': coach_notes,
                    'approved_topics': approved_topics,
                    'approved_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return True
    except Exception as e:
        st.error(f"Onay işlemi hatası: {e}")
        return False

def admin_coach_approval_panel():
    """Admin panelinde koç onay sistemi"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 25px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h2 style="margin: 0; color: white;">👨‍🏫 Koç Onay Sistemi</h2>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Öğrenci Haftalık Program Onayları</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Onay taleplerini getir
    approval_requests = get_student_approval_requests()
    
    if not approval_requests:
        st.info("📝 Henüz hiç onay talebi bulunmuyor.")
        return
    
    # Talepleri filtrele
    pending_requests = [req for req in approval_requests if req['status'] == 'pending']
    processed_requests = [req for req in approval_requests if req['status'] in ['approved', 'rejected']]
    
    st.markdown("## ⏳ Bekleyen Onaylar")
    
    if not pending_requests:
        st.success("✅ Tüm onay talepleri işlendi!")
    else:
        st.warning(f"📊 {len(pending_requests)} adet bekleyen onay talebi var.")
    
    # Bekleyen talepleri göster
    for i, request in enumerate(pending_requests):
        with st.expander(f"📚 {request['student_name']} - {request['submission_date']}", expanded=i<3):
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"""
                **👤 Öğrenci:** {request['student_name']}  
                **📚 Alan:** {request['student_field']}  
                **📅 Gönderim:** {request['submission_date']}  
                **📅 Hafta:** {request['week_number']}
                """)
            
            with col2:
                st.metric("📊 Konu Sayısı", len(request['topics']))
            
            with col3:
                status_color = "#f39c12" if request['status'] == 'pending' else "#27ae60"
                st.markdown(f"""
                <div style="background: {status_color}; color: white; padding: 5px 10px; border-radius: 5px; text-align: center;">
                    {request['status'].upper()}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("### 📚 Gönderilen Konular:")
            
            # Konuları tablo olarak göster
            if request['topics']:
                topic_data = []
                for topic in request['topics']:
                    topic_data.append({
                        'Ders': topic.get('subject', 'Bilinmiyor'),
                        'Konu': topic.get('topic', 'Bilinmiyor'),
                        'Detay': topic.get('detail', ''),
                        'Öncelik': topic.get('priority', 'NORMAL')
                    })
                
                if topic_data:
                    st.dataframe(topic_data, use_container_width=True)
            
            # Onay formu
            st.markdown("### ✅ Koç Değerlendirmesi:")
            
            # Konu düzenleme
            approved_topics = request['topics'].copy()  # Mevcut konuları kopyala
            
            if st.checkbox("🔧 Konuları düzenlemek istiyorum", key=f"edit_{i}"):
                st.markdown("**🗑️ Silinecek konuları işaretleyin:**")
                topics_to_remove = []
                
                for j, topic in enumerate(approved_topics):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"{j+1}. {topic.get('subject', 'Bilinmiyor')} - {topic.get('topic', 'Bilinmiyor')}")
                    with col2:
                        if st.checkbox("Sil", key=f"remove_{i}_{j}"):
                            topics_to_remove.append(j)
                
                # Silinecek konuları çıkar
                for index in sorted(topics_to_remove, reverse=True):
                    if 0 <= index < len(approved_topics):
                        approved_topics.pop(index)
                
                st.markdown("**➕ Konu Takip'ten detaylı seçim ile konu ekleyin:**")
                
                # Cascading dropdown'lar - form dışında (cascading için gerekli)
                available_subjects = list(YKS_TOPICS.keys())
                
                # Session state ile seçimleri takip edelim
                if f'subject_key_{i}' not in st.session_state:
                    st.session_state[f'subject_key_{i}'] = 0
                if f'category_key_{i}' not in st.session_state:
                    st.session_state[f'category_key_{i}'] = 0
                if f'subcategory_key_{i}' not in st.session_state:
                    st.session_state[f'subcategory_key_{i}'] = 0
                if f'topic_key_{i}' not in st.session_state:
                    st.session_state[f'topic_key_{i}'] = 0
                
                # 1. Ders seçimi
                selected_subject_idx = st.selectbox(
                    "📚 1. Ders Seçin:",
                    options=range(len(available_subjects)),
                    format_func=lambda x: available_subjects[x],
                    index=st.session_state[f'subject_key_{i}'],
                    key=f"subject_select_{i}"
                )
                
                selected_subject = available_subjects[selected_subject_idx]
                st.session_state[f'subject_key_{i}'] = selected_subject_idx
                
                # 2. Kategori seçimi
                if selected_subject:
                    available_categories = get_categories(selected_subject)
                    selected_category_idx = st.selectbox(
                        "📖 2. Kategori Seçin:",
                        options=range(len(available_categories)),
                        format_func=lambda x: available_categories[x],
                        index=st.session_state[f'category_key_{i}'] if st.session_state[f'category_key_{i}'] < len(available_categories) else 0,
                        key=f"category_select_{i}"
                    )
                    
                    selected_category = available_categories[selected_category_idx]
                    st.session_state[f'category_key_{i}'] = selected_category_idx
                    
                    # 3. Alt kategori seçimi
                    available_subcategories = get_subcategories(selected_subject, selected_category)
                    selected_subcategory_idx = st.selectbox(
                        "📂 3. Alt Kategori Seçin:",
                        options=range(len(available_subcategories)),
                        format_func=lambda x: available_subcategories[x],
                        index=st.session_state[f'subcategory_key_{i}'] if st.session_state[f'subcategory_key_{i}'] < len(available_subcategories) else 0,
                        key=f"subcategory_select_{i}"
                    )
                    
                    selected_sub_category = available_subcategories[selected_subcategory_idx]
                    st.session_state[f'subcategory_key_{i}'] = selected_subcategory_idx
                    
                    # 4. Konu seçimi
                    available_topics = get_topics_detailed(selected_subject, selected_category, selected_sub_category)
                    selected_topic_idx = st.selectbox(
                        "🎯 4. Konu Seçin:",
                        options=range(len(available_topics)),
                        format_func=lambda x: available_topics[x],
                        index=st.session_state[f'topic_key_{i}'] if st.session_state[f'topic_key_{i}'] < len(available_topics) else 0,
                        key=f"topic_select_{i}"
                    )
                    
                    selected_topic = available_topics[selected_topic_idx]
                    st.session_state[f'topic_key_{i}'] = selected_topic_idx
                    
                    # Seçilen konunun detaylı bilgilerini göster
                    st.markdown(f"""
                    **📋 Seçilen Konu Detayları:**
                    - **Ders:** {selected_subject}
                    - **Kategori:** {selected_category}
                    - **Alt Kategori:** {selected_sub_category}
                    - **Konu:** {selected_topic}
                    """)
                    
                    # Form submit
                    with st.form(f"add_topic_form_{i}"):
                        new_detail = st.text_input(
                            "Detay (isteğe bağlı, düzenlenebilir):", 
                            value=selected_topic,
                            placeholder="Konu detayları veya notlarınızı yazın",
                            key=f"detail_{i}"
                        )
                        
                        new_priority = st.selectbox(
                            "Öncelik:", 
                            ["DÜŞÜK", "NORMAL", "YÜKSEK", "KRİTİK"],
                            key=f"priority_{i}"
                        )
                        
                        if st.form_submit_button("➕ Seçilen Konuyu Ekle", type="primary"):
                            new_topic_obj = {
                                'subject': selected_subject,
                                'category': selected_category,
                                'sub_category': selected_sub_category,
                                'topic': selected_topic,
                                'detail': new_detail,
                                'priority': new_priority,
                                'net': 0
                            }
                            approved_topics.append(new_topic_obj)
                            st.success(f"✅ {selected_subject} - {selected_topic} konusu eklendi!")
                            st.rerun()
                else:
                    st.info("⚠️ Önce bir ders seçin")
                    
            # Manuel konu ekleme için ayrı form
            st.markdown("**Veya manuel olarak ekleyin:**")
            with st.form(f"manual_add_topic_form_{i}"):
                manual_subject = st.text_input("Manuel Ders Adı:", placeholder="TYT Matematik", key=f"manual_subject_{i}")
                manual_topic = st.text_input("Manuel Konu Adı:", placeholder="Türev", key=f"manual_topic_{i}")
                manual_detail = st.text_input("Manuel Detay:", placeholder="Türev kuralları", key=f"manual_detail_{i}")
                manual_priority = st.selectbox("Manuel Öncelik:", ["DÜŞÜK", "NORMAL", "YÜKSEK", "KRİTİK"], key=f"manual_priority_{i}")
                
                if st.form_submit_button("➕ Manuel Konu Ekle", type="secondary"):
                    if manual_subject and manual_topic:
                        manual_topic_obj = {
                            'subject': manual_subject,
                            'topic': manual_topic,
                            'detail': manual_detail,
                            'priority': manual_priority,
                            'net': 0
                        }
                        approved_topics.append(manual_topic_obj)
                        st.success(f"✅ Manuel: {manual_subject} - {manual_topic} eklendi!")
                        st.rerun()
                    else:
                        st.error("⚠️ Manuel ekleme için en azından ders ve konu adı gereklidir!")
            
            # Koç notu ve onay (HER TALEBİN KENDİ TEXTAREA'SI)
            coach_notes = st.text_area(
                "📝 Koç Notu:", 
                placeholder="Programla ilgili görüşleriniz, önerileriniz...", 
                key=f"coach_notes_{i}"  # 🔧 UNIQUE KEY: Her talep için farklı
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Onayla", key=f"approve_{i}", type="primary"):
                    # Student_username yoksa alternatif olarak student_name kullan
                    username = request.get('student_username', request.get('student_name', 'unknown'))
                    approval_key = f"{username}_{request['submission_date'].replace(' ', '_').replace('-', '_').replace(':', '_')}"
                    
                    # 🔧 TEST: Onay işlemi debug için
                    st.info(f"📋 Onaylanacak konu sayısı: {len(approved_topics)}")
                    st.info(f"🔑 Approval Key: {approval_key}")
                    st.info(f"👤 Student Username: {username}")
                    
                    if approve_student_topics(approval_key, approved_topics, coach_notes, "approved"):
                        st.success("✅ Program onaylandı!")
                        # Başarı sonrası kısa bekleme
                        st.info("🔄 Değişiklikler yansıtılıyor...")
                        st.rerun()
                    else:
                        st.error("❌ Onay işlemi başarısız oldu!")
            
            with col2:
                if st.button("❌ Reddet", key=f"reject_{i}", type="secondary"):
                    # Student_username yoksa alternatif olarak student_name kullan
                    username = request.get('student_username', request.get('student_name', 'unknown'))
                    approval_key = f"{username}_{request['submission_date'].replace(' ', '_').replace('-', '_').replace(':', '_')}"
                    
                    if approve_student_topics(approval_key, approved_topics, coach_notes, "rejected"):
                        st.success("❌ Program reddedildi!")
                        st.rerun()
                    else:
                        st.error("❌ Red işlemi başarısız oldu!")
            
            st.markdown("---")
    
    # İşlenmiş talepler
    if processed_requests:
        st.markdown("## ✅ İşlenmiş Onaylar")
        
        for request in processed_requests[-5:]:  # Son 5 işlem
            status_emoji = "✅" if request['status'] == 'approved' else "❌"
            status_color = "#27ae60" if request['status'] == 'approved' else "#e74c3c"
            
            st.markdown(f"""
            <div style="background: {status_color}; color: white; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <h4 style="margin: 0; color: white;">{status_emoji} {request['student_name']}</h4>
                <p style="margin: 5px 0 0 0;">📅 {request['submission_date']} → {request.get('approved_date', 'İşlenmedi')}</p>
                <p style="margin: 5px 0 0 0;">📝 {request.get('coach_notes', 'Koç notu yok')}</p>
            </div>
            """, unsafe_allow_html=True)

# Ana uygulamayı başlat
if __name__ == "__main__":
    main()
