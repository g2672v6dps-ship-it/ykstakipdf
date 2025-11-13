# 🚀 YKS Takip Sistemi - Supabase Deployment Kılavuzu

## 📋 Gereksinimler

### Supabase Projesi Oluşturma:
1. [Supabase.com](https://supabase.com) adresine git
2. Yeni proje oluştur
3. Proje URL'sini ve ANON KEY'i kopyala

### Database Tabloları Oluşturma:

SQL Editor'da aşağıdaki tabloları oluştur:

```sql
-- Users tablosu
CREATE TABLE users (
    username VARCHAR(255) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    grade VARCHAR(50) NOT NULL,
    field VARCHAR(50) NOT NULL,
    target_department VARCHAR(255),
    tyt_last_net INTEGER DEFAULT 0,
    tyt_avg_net INTEGER DEFAULT 0,
    ayt_last_net INTEGER DEFAULT 0,
    ayt_avg_net INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    total_study_time INTEGER DEFAULT 0,
    topic_progress TEXT DEFAULT '{}',
    topic_completion_dates TEXT DEFAULT '{}',
    completed_topics TEXT DEFAULT '{}',
    weekly_progress TEXT DEFAULT '{}',
    is_profile_complete BOOLEAN DEFAULT FALSE,
    is_learning_style_set BOOLEAN DEFAULT FALSE,
    coach_approval_status VARCHAR(50) DEFAULT 'none',
    coach_notes TEXT DEFAULT '',
    approval_date TIMESTAMP,
    approved_topics TEXT DEFAULT '[]'
);

-- Coach approvals tablosu
CREATE TABLE coach_approvals (
    id SERIAL PRIMARY KEY,
    approval_key VARCHAR(255) UNIQUE NOT NULL,
    student_username VARCHAR(255) NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    student_field VARCHAR(50) NOT NULL,
    submission_date TIMESTAMP NOT NULL,
    topics TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    coach_notes TEXT DEFAULT '',
    approved_topics TEXT DEFAULT '[]',
    approved_date TIMESTAMP,
    week_number INTEGER,
    year INTEGER
);

-- RLS (Row Level Security) aktifleştir
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE coach_approvals ENABLE ROW LEVEL SECURITY;

-- Public read/write yetkileri
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT USING (auth.uid()::text = username);

CREATE POLICY "Users can update their own data" ON users
    FOR UPDATE USING (auth.uid()::text = username);

CREATE POLICY "Users can insert their own data" ON users
    FOR INSERT WITH CHECK (auth.uid()::text = username);

-- Coach approvals için policy'ler
CREATE POLICY "Allow all access for coach_approvals" ON coach_approvals
    FOR ALL USING (true);
```

## 🔧 Local Development

### 1. Repository Oluştur:
```bash
git init
git add .
git commit -m "Initial commit: YKS Supabase migration"
git branch -M main
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### 2. Environment Variables (Local):
`.streamlit/secrets.toml` dosyasını oluştur:
```toml
SUPABASE_URL = "your-project-url"
SUPABASE_ANON_KEY = "your-anon-key"
```

## 🌐 Streamlit Cloud Deployment

### 1. GitHub Repository'yi Bağla:
- [share.streamlit.io](https://share.streamlit.io) adresine git
- GitHub hesabınla giriş yap
- Repository'yi seç
- Ana dosyayı: `yks_supabase.py` olarak ayarla

### 2. Secrets Ayarla:
Streamlit Cloud'da:
- App settings → Secrets menüsüne git
- Aşağıdaki secret'ları ekle:
```toml
SUPABASE_URL = "https://xyzcompany.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Deploy:
- Deploy butonuna tıkla
- Build başarılı olana kadar bekle
- URL'yi paylaş!

## 🔄 Migration Adımları

### Firebase → Supabase Değişiklikleri:

1. **Firebase Service Account Key** → **Supabase URL + ANON KEY**
2. **Realtime Database** → **PostgREST API**
3. **firebase_admin SDK** → **supabase-py SDK**
4. **db.reference()** → **supabase.table().select()**

### Kod Değişiklikleri:
- `firebase_connected` → `supabase_connected`
- `db_ref` → `supabase_client`
- Tüm CRUD operasyonları Supabase syntax'a uyarlandı
- Cache sistemi Supabase için optimize edildi

## ⚠️ Önemli Notlar

1. **Güvenlik**: ANON KEY'i asla GitHub'a yükleme
2. **RLS**: Supabase'de Row Level Security'yi aktifleştir
3. **Backup**: Mevcut Firebase verilerini Supabase'e migrate et
4. **Test**: Local'de test et, sonra deploy et

## 🆘 Sorun Giderme

### Supabase Bağlantı Hatası:
- URL ve ANON KEY'i kontrol et
- Proje durumunu kontrol et (aktif mi?)
- Network bağlantısını kontrol et

### Database Hatası:
- Tabloların oluşturulduğunu kontrol et
- RLS policy'lerini kontrol et
- Permission'ları kontrol et

### Cache Hatası:
- Browser cache'ini temizle
- Session state'i temizle
- Force refresh kullan

## 📞 Destek

Sorun yaşarsan:
1. Console log'larını kontrol et
2. Network tab'ında API çağrılarını incele
3. Supabase dashboard'da logs'ları kontrol et