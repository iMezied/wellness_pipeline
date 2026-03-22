import mysql.connector
from config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    topic_ar VARCHAR(255) NOT NULL,
    topic_en VARCHAR(255) NOT NULL,
    pubmed_keywords VARCHAR(500) NOT NULL,
    category ENUM('nutrition','fitness','sleep','mental','longevity','herbs') DEFAULT 'nutrition',
    used TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    topic_id INT,
    status ENUM('queued','generating','composing','publishing','done','failed') DEFAULT 'queued',
    script_ar TEXT,
    pubmed_doi VARCHAR(255),
    pubmed_title VARCHAR(500),
    audio_path VARCHAR(500),
    video_path VARCHAR(500),
    final_path VARCHAR(500),
    tiktok_id VARCHAR(255),
    instagram_id VARCHAR(255),
    youtube_id VARCHAR(255),
    pinterest_id VARCHAR(255),
    snapchat_id VARCHAR(255),
    error_msg TEXT,
    cost_usd DECIMAL(6,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS pipeline_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id INT,
    stage VARCHAR(100),
    message TEXT,
    level ENUM('info','warning','error') DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
"""

# ─── Seed topics ──────────────────────────────────────────────────────────────
SEED_TOPICS = [
    ("فوائد زيت الزيتون للقلب", "Olive oil cardiovascular benefits", "olive oil cardiovascular LDL HDL", "nutrition"),
    ("تأثير النوم على التستوستيرون", "Sleep and testosterone", "sleep testosterone men hormones", "sleep"),
    ("الصيام المتقطع والدهون الحشوية", "Intermittent fasting visceral fat", "intermittent fasting visceral fat reduction", "nutrition"),
    ("التمرين في الأربعين وبناء العضل", "Resistance training men over 40", "resistance training sarcopenia men 40", "fitness"),
    ("الكركم والالتهاب المزمن", "Turmeric curcumin inflammation", "curcumin anti-inflammatory chronic", "herbs"),
    ("حبة البركة وضغط الدم", "Nigella sativa blood pressure", "nigella sativa hypertension clinical trial", "herbs"),
    ("تأثير السكر على الدماغ", "Sugar and cognitive decline", "sugar cognitive decline brain glucose", "mental"),
    ("الأوميغا 3 والاكتئاب", "Omega-3 depression clinical evidence", "omega-3 EPA DHA depression meta-analysis", "mental"),
    ("التمرين والكوليسترول", "Exercise and cholesterol", "aerobic exercise LDL HDL cholesterol", "fitness"),
    ("الماغنيسيوم والنوم", "Magnesium sleep quality", "magnesium supplementation sleep quality", "sleep"),
    ("البروتين وإنقاص الوزن", "Protein satiety weight loss", "high protein diet satiety weight loss RCT", "nutrition"),
    ("الإجهاد وهرمون الكورتيزول", "Stress cortisol immune system", "chronic stress cortisol immune function", "mental"),
    ("الألياف ومرض السكري", "Dietary fiber type 2 diabetes", "dietary fiber type 2 diabetes prevention", "nutrition"),
    ("التعرض للشمس وفيتامين D", "Sun exposure vitamin D", "vitamin D deficiency supplementation", "nutrition"),
    ("الزنجبيل والغثيان والهضم", "Ginger digestion nausea", "ginger gingerol digestion nausea RCT", "herbs"),
]

def get_conn():
    return mysql.connector.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASS
    )

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    for stmt in SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cursor.execute(stmt)

    cursor.execute("SELECT COUNT(*) FROM topics")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany(
            "INSERT INTO topics (topic_ar, topic_en, pubmed_keywords, category) VALUES (%s, %s, %s, %s)",
            SEED_TOPICS
        )

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ DB initialized")

def get_next_topic() -> dict | None:
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM topics WHERE used = 0 ORDER BY RAND() LIMIT 1"
    )
    topic = cursor.fetchone()
    cursor.close()
    conn.close()
    return topic

def mark_topic_used(topic_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE topics SET used = 1 WHERE id = %s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()

def create_video_record(topic_id: int) -> int:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO videos (topic_id, status) VALUES (%s, 'queued')",
        (topic_id,)
    )
    conn.commit()
    video_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return video_id

def update_video(video_id: int, **kwargs):
    if not kwargs:
        return
    conn = get_conn()
    cursor = conn.cursor()
    sets = ", ".join(f"{k} = %s" for k in kwargs)
    vals = list(kwargs.values()) + [video_id]
    cursor.execute(f"UPDATE videos SET {sets} WHERE id = %s", vals)
    conn.commit()
    cursor.close()
    conn.close()

def log_pipeline(video_id: int, stage: str, message: str, level: str = "info"):
    print(f"[{level.upper()}] [{stage}] {message}")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pipeline_log (video_id, stage, message, level) VALUES (%s, %s, %s, %s)",
        (video_id, stage, message, level)
    )
    conn.commit()
    cursor.close()
    conn.close()
