import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# 1) Firebase Admin başlat
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# 2) ogrenci3_fixed.json dosyasını oku
json_path = "ogrenci3_fixed.json"

if not os.path.exists(json_path):
    print(f"❌ Dosya bulunamadı: {json_path}")
    raise SystemExit

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# data şu yapıda: { "ogrenci3": { ... } }
user_data = data.get("ogrenci3", {})

if not user_data:
    print("❌ 'ogrenci3' verisi bulunamadı!")
    raise SystemExit

# Ek olarak şifreyi garanti altına alalım
user_data["username"] = "ogrenci3"
user_data["password"] = "ogrenci3123"

# 3) Firestore'a yaz
db.collection("users").document("ogrenci3").set(user_data)

print("🔥 Firestore → 'ogrenci3' tüm verisiyle başarıyla yüklendi!")
