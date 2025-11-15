"""
🔄 Firestore Veri Yükleme Modülü
Firebase Realtime Database'den Firestore'a veri aktarımı
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------
# 🔥 FIREBASE + FIRESTORE BAŞLATMA  
# -----------------------------------------------------------

import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_READY = False
firestore_db = None

try:
    # Streamlit secrets içinden firebase_key'i al
    firebase_key = st.secrets.get("firebase_key", None)

    if firebase_key is None:
        st.error("❌ Firebase anahtarı Streamlit Secrets içinde bulunamadı!")
    else:
        # JSON STRING → Python dict
        firebase_key_dict = json.loads(firebase_key)

        # Firebase initialize
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_key_dict)
            firebase_admin.initialize_app(cred)

        firestore_db = firestore.client()
        FIREBASE_READY = True

except Exception as e:
    st.error(f"❌ Firebase Bağlantı Hatası: {str(e)}")
    FIREBASE_READY = False
    firestore_db = None


# -----------------------------------------------------------
# 🔄 ANA SAYFA
# -----------------------------------------------------------

def import_page():
    """🔄 Firestore Veri Yükleme Sayfası"""

    st.markdown("""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                padding: 25px; border-radius: 20px; margin: 20px 0; color: white; text-align: center;">
        <h1 style="margin: 0; color: white;">🔄 Firestore Veri Yükle</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Firebase Realtime DB'den Firestore'a Veri Aktarımı</p>
    </div>
    """, unsafe_allow_html=True)

    if not FIREBASE_READY:
        st.error("❌ Firebase bağlantısı kurulamadı!")
        st.stop()

    # Kullanıcı seçenekleri
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📋 Yükleme Seçenekleri")

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

        data_source = st.radio(
            "Veri kaynağını seçin:",
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
            doc_count = len(list(docs))
            st.metric("📁 Mevcut Belgeler", doc_count)
        except:
            st.metric("📁 Mevcut Belgeler", "0")

    st.markdown("---")

    if data_source == "📄 JSON Dosyası Yükle":
        json_upload_section()
    else:
        manual_input_section()


# -----------------------------------------------------------
# 📄 JSON İÇE AKTARMA
# -----------------------------------------------------------

def json_upload_section():
    st.markdown("### 📄 JSON Dosyası Yükle")

    uploaded_file = st.file_uploader("JSON dosyasını yükleyin:", type=["json"])

    if uploaded_file:
        try:
            json_data = json.loads(uploaded_file.read())
            st.success("✅ JSON başarıyla yüklendi!")

            if st.checkbox("🔍 Veri Önizlemesi"):
                st.json(json_data)

            if st.button("🔄 Firestore'a Yükle"):
                upload_to_firestore(json_data)

        except Exception as e:
            st.error(f"❌ JSON okuma hatası: {str(e)}")


# -----------------------------------------------------------
# 📋 MANUEL GİRİŞ
# -----------------------------------------------------------

def manual_input_section():
    st.markdown("### 📋 Manuel Veri Girişi")

    with st.form("manual_form"):
        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input("👤 Kullanıcı Adı")
            password = st.text_input("🔒 Şifre", type="password")
            name = st.text_input("📝 Ad Soyad")

        with col2:
            field = st.selectbox("📚 Alan", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])
            grade = st.selectbox("🏫 Sınıf", ["9", "10", "11", "12", "Mezun"])
            target = st.text_input("🎯 Hedef Bölüm")

        submitted = st.form_submit_button("📥 Kaydet")

        if submitted:
            if not username:
                st.error("❌ Kullanıcı adı zorunlu!")
                return

            data = {
                "username": username,
                "password": password,
                "name": name,
                "field": field,
                "grade": grade,
                "target": target,
                "created_date": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "status": "Aktif"
            }

            upload_single_student(data)


# -----------------------------------------------------------
# 🔄 FIRESTORE’A AKTARMA
# -----------------------------------------------------------

def upload_to_firestore(data):
    try:
        success = 0
        fail = 0

        for username, udata in data.items():
            udata["username"] = username
            if upload_single_student(udata):
                success += 1
            else:
                fail += 1

        st.success(f"✅ Başarılı: {success}")
        if fail > 0:
            st.error(f"❌ Hatalı: {fail}")

    except Exception as e:
        st.error(f"❌ Yükleme hatası: {str(e)}")


# -----------------------------------------------------------
# 👤 TEK ÖĞRENCİ KAYDETME
# -----------------------------------------------------------

def upload_single_student(student_data):
    try:
        username = student_data["username"]
        firestore_db.collection("users").document(username).set(student_data, merge=True)
        return True

    except Exception as e:
        st.error(f"❌ {username} kaydedilemedi: {str(e)}")
        return False
