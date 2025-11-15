"""
🔄 Firestore Veri Yükleme Modülü
Firebase Realtime Database'den Firestore'a veri aktarımı
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import firestore

def import_page():
    """🔄 Firestore Veri Yükleme Sayfası"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                padding: 25px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h1 style="margin: 0; color: white;">🔄 Firestore Veri Yükle</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Firebase Realtime DB'den Firestore'a Veri Aktarımı</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Firebase bağlantı kontrolü
    try:
        # Mevcut firestore bağlantısını kullan
        if 'firestore_db' in globals():
            firestore_connected = True
        else:
            st.error("❌ Firebase bağlantısı bulunamadı!")
            return
    except Exception as e:
        st.error(f"❌ Firebase bağlantı hatası: {str(e)}")
        return
    
    # Kullanıcı girişi
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Yükleme Seçenekleri")
        
        # Yükleme türü seçimi
        import_type = st.radio(
            "Hangi veriyi yüklemek istiyorsunuz?",
            [
                "👥 Tüm Öğrenciler",
                "📊 Sadece Öğrenci Bilgileri", 
                "📈 Sadece Çalışma Verileri",
                "⏰ Sadece Zaman Verileri",
                "🎯 Sadece Onay Verileri"
            ],
            index=0
        )
        
        # Kaynak veri girişi
        st.markdown("### 📥 Kaynak Veri")
        
        data_source = st.radio(
            "Veri kaynağını seçin:",
            [
                "📄 JSON Dosyası Yükle",
                "📋 Manuel Veri Girişi",
                "🔗 Realtime Database'den Çek (Beta)"
            ],
            index=0
        )
    
    with col2:
        st.markdown("### 📊 İstatistikler")
        
        # Mevcut Firestore durumu
        try:
            docs = firestore_db.get()
            current_docs = len([doc for doc in docs if doc.exists])
            st.metric("📁 Mevcut Belgeler", current_docs)
        except:
            st.metric("📁 Mevcut Belgeler", "0")
    
    st.markdown("---")
    
    # Veri giriş yöntemine göre formlar
    if data_source == "📄 JSON Dosyası Yükle":
        json_upload_section()
    elif data_source == "📋 Manuel Veri Girişi":
        manual_input_section()
    elif data_source == "🔗 Realtime Database'den Çek (Beta)":
        realtime_collect_section()

def json_upload_section():
    """JSON dosyası yükleme bölümü"""
    st.markdown("### 📄 JSON Dosyası Yükle")
    
    uploaded_file = st.file_uploader(
        "JSON formatında veri dosyası seçin:",
        type=['json'],
        help="Firebase Realtime Database'den export edilen JSON dosyası"
    )
    
    if uploaded_file is not None:
        try:
            # JSON dosyasını oku
            json_data = json.loads(uploaded_file.read())
            
            st.success(f"✅ JSON dosyası başarıyla yüklendi!")
            
            # Veri önizlemesi
            if st.checkbox("🔍 Veri Önizlemesini Göster"):
                st.json(json_data)
            
            # Yükleme onayı
            if st.button("🔄 Firestore'a Yükle", type="primary"):
                upload_to_firestore(json_data)
                
        except json.JSONDecodeError:
            st.error("❌ Geçersiz JSON dosyası formatı!")
        except Exception as e:
            st.error(f"❌ Dosya okuma hatası: {str(e)}")

def manual_input_section():
    """Manuel veri girişi bölümü"""
    st.markdown("### 📋 Manuel Veri Girişi")
    
    # Öğrenci bilgileri formu
    with st.form("manual_student_data"):
        st.markdown("#### 👤 Öğrenci Bilgileri")
        
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("👤 Kullanıcı Adı", placeholder="ogrenci10")
            password = st.text_input("🔒 Şifre", type="password")
            name = st.text_input("📝 Ad Soyad", placeholder="Elif")
            
        with col2:
            field = st.selectbox("📚 Alan", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])
            grade = st.selectbox("🏫 Sınıf", ["9", "10", "11", "12", "Mezun"])
            target_department = st.text_input("🎯 Hedef Bölüm", placeholder="Yazılım Mühendisliği")
        
        # Çalışma verileri
        st.markdown("#### 📊 Çalışma Verileri")
        
        col3, col4 = st.columns(2)
        
        with col3:
            weekly_hours = st.number_input("⏰ Haftalık Çalışma Saati", min_value=0.0, value=15.0)
            total_hours = st.number_input("📊 Toplam Çalışma Saati", min_value=0.0, value=100.0)
            
        with col4:
            tyt_last_net = st.number_input("🧮 TYT Son Net", min_value=0.0, value=25.0)
            ayt_last_net = st.number_input("🎯 AYT Son Net", min_value=0.0, value=20.0)
        
        # Gönder butonu
        submitted = st.form_submit_button("✅ Firestore'a Kaydet", type="primary")
        
        if submitted:
            if not username or not password:
                st.error("❌ Kullanıcı adı ve şifre zorunludur!")
                return
                
            # Veriyi hazırla
            student_data = {
                'username': username,
                'password': password,
                'name': name,
                'field': field,
                'grade': grade,
                'target_department': target_department,
                'weekly_hours': weekly_hours,
                'total_hours': total_hours,
                'tyt_last_net': tyt_last_net,
                'ayt_last_net': ayt_last_net,
                'created_date': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat(),
                'status': 'Aktif'
            }
            
            upload_single_student(student_data)

def realtime_collect_section():
    """Realtime Database'den veri çekme (Beta)"""
    st.markdown("### 🔗 Realtime Database'den Çek (Beta)")
    
    st.warning("⚠️ Bu özellik şu anda geliştirme aşamasındadır!")
    
    if st.button("📡 Realtime Database'den Veri Çek", disabled=True):
        st.info("🔄 Bu özellik yakında aktif olacak...")

def upload_to_firestore(data):
    """Veriyi Firestore'a yükle"""
    try:
        with st.spinner("🔄 Firestore'a veri yükleniyor..."):
            success_count = 0
            error_count = 0
            
            # Veriyi process et
            if isinstance(data, dict):
                # Tek kullanıcı verisi
                if 'username' in data:
                    result = upload_single_student(data)
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    # Birden fazla kullanıcı
                    for username, user_data in data.items():
                        user_data['username'] = username
                        result = upload_single_student(user_data)
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
            elif isinstance(data, list):
                # Liste formatında veriler
                for item in data:
                    if isinstance(item, dict) and 'username' in item:
                        result = upload_single_student(item)
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
            
            # Sonuç göster
            if success_count > 0:
                st.success(f"✅ {success_count} kayıt başarıyla yüklendi!")
            if error_count > 0:
                st.error(f"❌ {error_count} kayıt yüklenirken hata oluştu!")
                
            # İstatistikleri güncelle
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Yükleme hatası: {str(e)}")

def upload_single_student(student_data):
    """Tek öğrenci verisini Firestore'a yükle"""
    try:
        if 'firestore_db' in globals():
            username = student_data['username']
            
            # Firestore'a kaydet
            firestore_db.document(username).set(student_data, merge=True)
            
            return True
        else:
            st.error("❌ Firestore bağlantısı bulunamadı!")
            return False
            
    except Exception as e:
        st.error(f"❌ {student_data.get('username', 'Bilinmeyen')} için hata: {str(e)}")
        return False
