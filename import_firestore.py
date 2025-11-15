"""
🔄 Firestore Veri Yükleme Modülü
Firebase Realtime Database'den Firestore'a veri aktarımı
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# ---------- FIRESTORE BAĞLANTI ----------
import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_READY = False
firestore_db = None

try:
    # Streamlit secrets'ten firebase_key'i al
    config = dict(st.secrets["firebase_key"])  # AttrDict --> dict

    # Firebase daha önce başlatılmadıysa başlat
    if not firebase_admin._apps:
        cred = credentials.Certificate(config)
        firebase_admin.initialize_app(cred)

    firestore_db = firestore.client()
    FIREBASE_READY = True

except Exception as e:
    FIREBASE_READY = False
    firestore_db = None
    st.error(f"❌ Firebase Bağlantı Hatası: {e}")


# ---------- ANA SAYFA ----------
def import_page():
    """🔄 Firestore Veri Yükleme Sayfası"""

    st.markdown("""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                padding: 25px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h1 style="margin: 0; color: white;">🔄 Firestore Veri Yükle</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Firebase Realtime DB → Firestore aktarım ekranı</p>
    </div>
    """, unsafe_allow_html=True)

    # Firestore bağlantısını kontrol et
    if not FIREBASE_READY:
        st.error("❌ Firebase bağlantısı bulunamadı! Lütfen secrets yapılandırmasını kontrol edin.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📋 Yükleme Türü")
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

        st.markdown("### 📥 Veri Kaynağı")
        data_source = st.radio(
            "Kaynak seçin:",
            [
                "📄 JSON Dosyası Yükle",
                "📋 Manuel Veri Girişi",
            ],
            index=0
        )

    with col2:
        st.markdown("### 📊 Firestore Durumu")
        try:
            docs = firestore_db.stream()
            count = sum(1 for _ in docs)
            st.metric("📁 Kayıtlı Belge", count)
        except:
            st.metric("📁 Kayıtlı Belge", "0")

    st.markdown("---")

    if data_source == "📄 JSON Dosyası Yükle":
        json_upload_section()
    else:
        manual_input_section()


# ---------- JSON YÜKLEME ----------
def json_upload_section():
    st.markdown("### 📄 JSON Dosyası Yükle")

    uploaded_file = st.file_uploader(
        "JSON formatında veri dosyası yükleyin:",
        type=['json']
    )

    if uploaded_file is not None:
        try:
            data = json.loads(uploaded_file.read())
            st.success("✅ JSON başarıyla yüklendi.")

            if st.checkbox("🔍 JSON İçeriğini Göster"):
                st.json(data)

            if st.button("🔄 Firestore'a Yükle", type="primary"):
                upload_to_firestore(data)

        except Exception as e:
            st.error(f"❌ JSON okuma hatası: {e}")


# ---------- MANUEL ÖĞRENCİ EKLEME ----------
def manual_input_section():
    st.markdown("### 📋 Manuel Öğrenci Ekle")

    with st.form("manual_add"):
        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input("👤 Kullanıcı Adı")
            password = st.text_input("🔒 Şifre", type="password")
            name = st.text_input("📝 Ad Soyad")
            field = st.selectbox("📚 Alan", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])

        with col2:
            grade = st.selectbox("🏫 Sınıf", ["9", "10", "11", "12", "Mezun"])
            target = st.text_input("🎯 Hedef Bölüm")
            weekly_hours = st.number_input("⏰ Haftalık Çalışma Saati", 0, 200)
            total_hours = st.number_input("📊 Toplam Çalışma Saati", 0, 5000)

        submitted = st.form_submit_button("✅ Firestore'a Kaydet")

        if submitted:
            if not username or not password:
                st.error("❌ Kullanıcı adı ve şifre zorunludur!")
                return

            data = {
                "username": username,
                "password": password,
                "name": name,
                "field": field,
                "grade": grade,
                "target": target,
                "weekly_hours": weekly_hours,
                "total_hours": total_hours,
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "status": "Aktif"
            }

            upload_single_student(data)


# ---------- FIRESTORE'A KAYDETME ----------
def upload_to_firestore(data):
    try:
        success = 0
        error = 0

        for username, user_data in data.items():
            user_data["username"] = username
            if upload_single_student(user_data):
                success += 1
            else:
                error += 1

        st.success(f"✅ {success} kayıt yüklendi")
        if error:
            st.error(f"❌ {error} kayıt yüklenemedi")

    except Exception as e:
        st.error(f"❌ Yükleme hatası: {e}")


def upload_single_student(data):
    try:
        username = data["username"]
        firestore_db.collection("users").document(username).set(data, merge=True)
        return True
    except Exception as e:
        st.error(f"❌ {username} eklenemedi → {e}")
        return False
