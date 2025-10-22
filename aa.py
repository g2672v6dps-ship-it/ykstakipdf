# 🔧 HAFTALIK PLAN HATASI DÜZELTMESİ
# Öğrenciler bir konuyu "iyi" seviyeye getirdiğinde haftalık listeden kaldırılmıyor sorunu çözüldü

# ÖNCEKİ HATA: completed_topics parametresi kullanılmıyordu
# YENİ: Tamamlanmış konular filtrele niyor

def get_equal_weight_weekly_topics_FIXED(week_number, completed_topics, pending_topics):
    """Eşit Ağırlık için haftalık konuları getirir - DÜZELTİLMİŞ"""
    if week_number > 16:
        week_number = 16  # Max 16 hafta
    
    week_plan = EQUAL_WEIGHT_WEEKLY_PLAN.get(week_number, {})
    weekly_topics = []
    
    # 🆕 DÜZELTME: Tamamlanmış konu isimlerini al
    completed_topic_names = set()
    if completed_topics:
        for topic in completed_topics:
            topic_name = topic.get('topic', '') if isinstance(topic, dict) else str(topic)
            if topic_name:
                completed_topic_names.add(topic_name)
    
    # Bu haftanın planlanmış konularını al
    planned_topics = week_plan.get('topics', {})
    
    # Konuları birleştir
    for subject, topic_list in planned_topics.items():
        for topic in topic_list:
            # 🆕 DÜZELTME: Tamamlanmış konuları ATLA
            if topic in completed_topic_names:
                continue  # Bu konu zaten tamamlanmış, ekleme
            
            weekly_topics.append({
                'subject': subject,
                'topic': topic,
                'week': week_number,
                'priority': 'normal',
                'difficulty': get_topic_difficulty_by_name(topic),
                'status': 'planned',
                'net': 0,
                'detail': ''
            })
    
    # Sadece 2. hafta ve sonrasında önceki haftalardan kalan konuları ekle
    if week_number > 1:
        priority_topics = get_priority_topics_from_previous_weeks(pending_topics)
        
        # Öncelikli konuları başa ekle (zaten tamamlanmamış olduklarını biliyoruz)
        for topic in priority_topics:
            # 🆕 DÜZELTME: Öncelikli konuları da kontrol et
            topic_name = topic.get('topic', '')
            if topic_name not in completed_topic_names:
                topic['priority'] = 'high'
                weekly_topics.insert(0, topic)
    
    return weekly_topics


def get_numerical_weekly_topics_FIXED(week_number, completed_topics, pending_topics):
    """Sayısal için haftalık konuları getirir - DÜZELTİLMİŞ"""
    if week_number > 18:
        week_number = 18  # Max 18 hafta
    
    week_plan = NUMERICAL_WEEKLY_PLAN.get(week_number, {})
    weekly_topics = []
    
    # 🆕 DÜZELTME: Tamamlanmış konu isimlerini al
    completed_topic_names = set()
    if completed_topics:
        for topic in completed_topics:
            topic_name = topic.get('topic', '') if isinstance(topic, dict) else str(topic)
            if topic_name:
                completed_topic_names.add(topic_name)
    
    # Bu haftanın planlanmış konularını al
    planned_topics = week_plan.get('topics', {})
    
    # Konuları birleştir
    for subject, topic_list in planned_topics.items():
        for topic in topic_list:
            # 🆕 DÜZELTME: Tamamlanmış konuları ATLA
            if topic in completed_topic_names:
                continue
            
            weekly_topics.append({
                'subject': subject,
                'topic': topic,
                'week': week_number,
                'priority': 'normal',
                'difficulty': get_topic_difficulty_by_name(topic),
                'status': 'planned',
                'net': 0,
                'detail': ''
            })
    
    # Sadece 2. hafta ve sonrasında önceki haftalardan kalan konuları ekle
    if week_number > 1:
        priority_topics = get_priority_topics_from_previous_weeks(pending_topics)
        
        # Öncelikli konuları başa ekle
        for topic in priority_topics:
            topic_name = topic.get('topic', '')
            if topic_name not in completed_topic_names:
                topic['priority'] = 'high'
                weekly_topics.insert(0, topic)
    
    return weekly_topics


def get_tyt_msu_weekly_topics_FIXED(week_number, completed_topics, pending_topics, user_data=None):
    """TYT & MSÜ için haftalık konuları getirir - DÜZELTİLMİŞ"""
    if week_number > 9:
        week_number = 9  # Max 9 hafta
    
    week_plan = TYT_MSU_WEEKLY_PLAN.get(week_number, {})
    weekly_topics = []
    
    # 🆕 DÜZELTME: Tamamlanmış konu isimlerini al
    completed_topic_names = set()
    if completed_topics:
        for topic in completed_topics:
            topic_name = topic.get('topic', '') if isinstance(topic, dict) else str(topic)
            if topic_name:
                completed_topic_names.add(topic_name)
    
    # Alt kategori bilgisini al
    sub_category = user_data.get('tyt_msu_sub_category', '') if user_data else ''
    
    # Bu haftanın planlanmış konularını al
    planned_topics = week_plan.get('topics', {})
    
    # Alt kategoriye göre konu önceliklendirmesi
    priority_subjects = []
    if sub_category.startswith('MSÜ'):
        priority_subjects = ['TYT Matematik', 'TYT Fizik', 'TYT Kimya']
    elif 'Bilgisayar' in sub_category or 'Teknoloji' in sub_category:
        priority_subjects = ['TYT Matematik', 'TYT Fizik']
    elif 'Tıbbi' in sub_category or 'Sağlık' in sub_category or 'Anestezi' in sub_category or 'ATT' in sub_category:
        priority_subjects = ['TYT Biyoloji', 'TYT Kimya']
    
    # Önce öncelikli dersleri ekle
    for subject in priority_subjects:
        if subject in planned_topics:
            topic_list = planned_topics[subject]
            for topic in topic_list:
                # 🆕 DÜZELTME: Tamamlanmış konuları ATLA
                if topic in completed_topic_names:
                    continue
                
                weekly_topics.append({
                    'subject': subject,
                    'topic': topic,
                    'week': week_number,
                    'priority': 'high',
                    'difficulty': get_topic_difficulty_by_name(topic),
                    'status': 'planned',
                    'net': 0,
                    'detail': f'⭐ {sub_category} için öncelikli'
                })
    
    # Sonra diğer dersleri ekle
    for subject, topic_list in planned_topics.items():
        if subject not in priority_subjects:
            for topic in topic_list:
                # 🆕 DÜZELTME: Tamamlanmış konuları ATLA
                if topic in completed_topic_names:
                    continue
                
                weekly_topics.append({
                    'subject': subject,
                    'topic': topic,
                    'week': week_number,
                    'priority': 'normal',
                    'difficulty': get_topic_difficulty_by_name(topic),
                    'status': 'planned',
                    'net': 0,
                    'detail': ''
                })
    
    # Önceki haftalardan kalan konular
    if week_number > 1:
        priority_topics = get_priority_topics_from_previous_weeks(pending_topics)
        
        for topic in priority_topics:
            topic_name = topic.get('topic', '')
            if topic_name not in completed_topic_names:
                topic['priority'] = 'high'
                weekly_topics.insert(0, topic)
    
    return weekly_topics


def get_verbal_weekly_topics_FIXED(week_number, completed_topics, pending_topics):
    """Sözel için haftalık konuları getirir - DÜZELTİLMİŞ"""
    if week_number > 14:
        week_number = 14  # Max 14 hafta
    
    week_plan = VERBAL_WEEKLY_PLAN.get(week_number, {})
    weekly_topics = []
    
    # 🆕 DÜZELTME: Tamamlanmış konu isimlerini al
    completed_topic_names = set()
    if completed_topics:
        for topic in completed_topics:
            topic_name = topic.get('topic', '') if isinstance(topic, dict) else str(topic)
            if topic_name:
                completed_topic_names.add(topic_name)
    
    # Bu haftanın planlanmış konularını al
    planned_topics = week_plan.get('topics', {})
    
    # Konuları birleştir
    for subject, topic_list in planned_topics.items():
        for topic in topic_list:
            # 🆕 DÜZELTME: Tamamlanmış konuları ATLA
            if topic in completed_topic_names:
                continue
            
            weekly_topics.append({
                'subject': subject,
                'topic': topic,
                'week': week_number,
                'priority': 'normal',
                'difficulty': get_topic_difficulty_by_name(topic),
                'status': 'planned',
                'net': 0,
                'detail': ''
            })
    
    # Önceki haftalardan kalan konular
    if week_number > 1:
        priority_topics = get_priority_topics_from_previous_weeks(pending_topics)
        
        for topic in priority_topics:
            topic_name = topic.get('topic', '')
            if topic_name not in completed_topic_names:
                topic['priority'] = 'high'
                weekly_topics.insert(0, topic)
    
    return weekly_topics


# 🎯 YENİ: Tamamlanmış konuları almak için yardımcı fonksiyon
def get_completed_topics_from_user_data(user_data):
    """
    Kullanıcının "iyi" seviyeye getirdiği (net >= 14) konuları döndürür
    """
    import json
    
    completed_topics = []
    
    # topic_progress'i al
    topic_progress = json.loads(user_data.get('topic_progress', '{}') or '{}')
    
    for topic_name, topic_data in topic_progress.items():
        if not isinstance(topic_data, dict):
            continue
        
        # Net sayısı 14 veya daha fazla ise "iyi" seviye (tamamlanmış)
        topic_net = topic_data.get('net', 0)
        if topic_net >= 14:
            completed_topics.append({
                'topic': topic_name,
                'subject': topic_data.get('subject', ''),
                'net': topic_net,
                'status': 'completed'
            })
    
    return completed_topics


# 📋 KULLANIM ÖRNEĞİ:
# Haftalık plan oluştururken:
"""
user_data = get_user_data()  # Kullanıcı verisini al

# Tamamlanmış konuları al
completed_topics = get_completed_topics_from_user_data(user_data)

# Tamamlanmamış (pending) konuları al
pending_topics = get_user_pending_topics(user_data)

# Mevcut hafta
current_week = user_data.get('equal_weight_current_week', 1)

# Haftalık planı oluştur (DÜZELTİLMİŞ fonksiyonla)
weekly_topics = get_equal_weight_weekly_topics_FIXED(
    week_number=current_week,
    completed_topics=completed_topics,  # ARTIK KULLANILIYOR!
    pending_topics=pending_topics
)
"""

print("✅ DÜZELTME TAMAMLANDI!")
print("")
print("📝 YAPILAN DEĞİŞİKLİKLER:")
print("1. ✅ Tamamlanmış konular (net >= 14) haftalık listeden filtreleniyor")
print("2. ✅ get_completed_topics_from_user_data() yardımcı fonksiyonu eklendi")
print("3. ✅ Tüm haftalık plan fonksiyonları (Equal Weight, Sayısal, TYT/MSÜ, Sözel) düzeltildi")
print("")
print("⚠️ SONRAKİ ADIM:")
print("Bu düzeltmeleri aa.py dosyasındaki ilgili fonksiyonlara uygulamanız gerekiyor.")
print("Satır numaraları: 3631, 3667, 3703, 3771")
