# rag_service.py — Dalil Legal RAG & Legal Statutes Ingestion Service
# High-precision retrieval over positive Moroccan Law: Code du Travail, DOC, Loi 67-12, Loi 49-16, Moudawana

import os, re, sqlite3, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "dalillegal.db"

CORE_MOROCCAN_STATUTES = [
    {
        "doc_title": "مدونة الشغل المغربية (القانون رقم 65.99)",
        "source": "الظهير الشريف رقم 1.03.194 الصادر في 11 سبتمبر 2003",
        "lang": "ar",
        "articles": [
            ("المادة 41", "في حالة إنهاء عقد الشغل تعسفيا من قبل المشغل، يحق للأجير الحصول على تعويض عن الضرر يقدر بشهر ونصف من الأجر عن كل سنة عمل أو جزء من السنة، على ألا يتعدى سقف 36 شهرا (3 سنوات)، وذلك دون الإخلال بالتعويض عن الإشعار والتعويض عن الفصل من العمل."),
            ("المادة 43", "إنهاء عقد الشغل غير محدد المدة دون إشعار أو قبل انقضاء أجله، يوجب على الطرف المسؤول أداء تعويض عن الإشعار يساوي الأجر الذي كان سيتقاضاه الأجير لو بقي في عمله حتى نهاية أجل الإشعار المحدد في النصوص التنظيمية."),
            ("المادة 53", "يستحق الأجير المرتبط بعقد شغل غير محدد المدة تعويضا عن الفصل بعد قضائه ستة أشهر في نفس المقاولة. يحدد مبلغ التعويض عن كل سنة أو جزء من السنة من العمل الفعلي كالتالي: 96 ساعة من الأجرة عن السنوات الخمس الأولى؛ 144 ساعة عن السنوات من 6 إلى 10؛ 192 ساعة عن السنوات من 11 إلى 15؛ 240 ساعة عن فترة العمل المتجاوزة لـ 15 سنة."),
            ("المادة 62", "يجب، قبل فصل الأجير عن العمل فصلا تأديبيا، إتاحة الفرصة له للدفاع عن نفسه بالاستماع إليه من طرف المشغل أو من ينوب عنه بحضور مندوب الأجراء في أجل لا يتعدى ثمانية (8) أيام من تاريخ تبين الخطأ المنسوب إليه. ويحرر محضر في الموضوع يوقعه الطرفان وتسلم نسخة منه للأجير."),
            ("المادة 63", "يسلم مقرر الفصل إلى الأجير المعني باليد مقابل وصل، أو يوجه إليه بواسطة رسالة مضمونة مع الإشعار بالتوصل داخل أجل ثمان وأربعين (48) ساعة من تاريخ اتخاذ القرار. وتوجه نسخة منه إلى مفتش الشغل داخل نفس الأجل. ويعتبر كل فصل تم دون احترام هذه الإجراءات فصلا تعسفيا."),
            ("المادة 73", "توصيل تصفية كل حساب (Solde de tout compte) هو التوصيل الذي يسلمه الأجير للمشغل عند انتهاء عقده لأي سبب كان، لتصفية كل الأداءات اتجاهه. يجوز للأجير التراجع عن التوصيل ونقضه داخل أجل ستين (60) يوما من تاريخ توقيعه بواسطة رسالة مضمونة أو مقال أمام المحكمة."),
            ("المادة 40", "تعد من بين الأخطاء الجسيمة المرتكبة من طرف المشغل أو رئيس المقاولة ضد الأجير: السب الفادح، استعمال أي نوع من أنواع العنف أو الاعتداء البدني، التحرش الجنسي، وعدم أداء الأجر. ويعتبر مغادرة الأجير لعمله بسبب أحد هذه الأخطاء بمثابة فصل تعسفي يوجب التعويض.")
        ]
    },
    {
        "doc_title": "قانون الكراء السكني والمهني (القانون رقم 67.12)",
        "source": "الظهير الشريف رقم 1.13.111 الصادر في 19 نوفمبر 2013",
        "lang": "ar",
        "articles": [
            ("المادة 3", "يبرم عقد الكراء وجوبا بمحرر كتابي ثابت التاريخ يتضمن على الخصوص: هوية الأطراف، مواصفات المحل، بيان مرافقه، الوجيبة الكرائية وكيفية أدائها، ومبلغ الضمانة إن وجد. كما يجب إعداد بيان وصفي لحالة المحل عند تسلم المفاتيح وعند إرجاعها."),
            ("المادة 7", "لا يمكن أن يتجاوز مبلغ واجب الضمانة (الوديعة) ما يعادل واجب كراء شهرين. وترد هذه الضمانة إلى المكتري داخل أجل أقصاه شهر ابتداء من تاريخ إرجاع المفاتيح وإخلاء المحل بعد خصم ما قد يكون مستحقا للمكري من مبالغ كراء أو إصلاحات."),
            ("المادة 31", "يحق للمكري والمكتري الاتفاق على شروط مراجعة الوجيبة الكرائية ونسبة الرفع منها أو تطبيق الزيادة القانونية المحددة في هذا القانون بعد مرور كل ثلاث سنوات على الأقل من تاريخ إبرام العقد أو آخر زيادة."),
            ("المادة 32", "تحدد نسبة الزيادة في الوجيبة الكرائية بقوة القانون في 8% بالنسبة للمحلات المخصصة للسكنى، و10% بالنسبة للمحلات المخصصة للاستعمال المهني."),
            ("المادة 45", "في حالة عدم أداء الوجيبة الكرائية والتكاليف التابعة لها، يوجه المكري إنذارا بالأداء إلى المكتري يحدد له فيه أجلا لا يقل عن خمسة عشر (15) يوما ابتداء من تاريخ التوصل بالإنذار لتسوية المبالغ المستحقة قبل اللجوء إلى رئيس المحكمة للمصادقة على الإنذار والإفراغ.")
        ]
    },
    {
        "doc_title": "قانون كراء العقارات والمحلات التجارية والصناعية والحرفية (القانون رقم 49.16)",
        "source": "الظهير الشريف رقم 1.16.99 الصادر في 18 يوليو 2016",
        "lang": "ar",
        "articles": [
            ("المادة 4", "يستفيد المكتري من الحق في تجديد عقد الكراء التجاري متى أثبت انتفاعه بالمحل لمدة سنتين متتاليتين على الأقل بعقد كتابي (أو أربع سنوات بعقد شفوي)، ويكتسب المكتري بذلك ملكية الأصل التجاري والحق في الكراء."),
            ("المادة 7", "يحق للمكري رفض تجديد عقد الكراء مقابل أداء تعويض عن الإفراغ للمكتري يعادل القيمة السوقية للأصل التجاري، ويحدد بناء على التصريحات الضريبية للسنوات الثلاث الأخيرة وما صرفه المكتري من إصلاحات ونفقات نقل وفقدان الزبناء."),
            ("المادة 8", "يعفى المكري من أداء أي تعويض عن الإفراغ في حالات محددة قانونا، أهمها: عدم أداء المكتري لواجبات الكراء داخل أجل 15 يوما من تاريخ توصله بإنذار بالأداء وكان مجموع ما بذمته لا يقل عن ثلاثة أشهر من الكراء؛ أو إحداث المكتري تغييرا في المحل دون موافقة المكري يضر بالبناية.")
        ]
    },
    {
        "doc_title": "مدونة الأسرة المغربية (القانون رقم 70.03)",
        "source": "الظهير الشريف رقم 1.04.22 الصادر في 3 فبراير 2004",
        "lang": "ar",
        "articles": [
            ("المادة 84", "تشمل مستحقات الزوجة عند الطلاق: الصداق المؤخر إن وجد، نفقة العدة، والمتعة التي يراعى في تقديرها فترة الزواج والوضعية المالية للزوج وأسباب الطلاق ومدى تعسف الزوج في إيقاعه."),
            ("المادة 94", "يجوز لأحد الزوجين أو كلاهما طلب التطليق بسبب الشقاق أمام قسم قضاء الأسرة بالمحكمة الابتدائية. وتقوم المحكمة بكل المحاولات للإصلاح بينهما، وإن تعذر الإصلاح تحكم بالتطليق وبمستحقات الزوجة والأبناء في أجل لا يتعدى ستة (6) أشهر."),
            ("المادة 187", "تجب النفقة للغير بسبب الزوجية، أو القرابة، أو الالتزام. وتشمل النفقة الغذاء والكسوة والعلاج، ومصاريف تعليم الأطفال، وكل ما يعتبر من الضروريات وما جرى به العرف حسب يسر الملزم بها وحال مستحقيها."),
            ("المادة 163", "الحضانة هي حفظ الولد مما قد يضره، والقيام بتربيته ورعايته وضمان مصالحه الفضلى. وتسند الحضانة أولا للأم، ثم للأب، ثم لأم الأم، مع مراعاة مصلحة المحضون بالدرجة الأولى."),
            ("المادة 49", "لكل واحد من الزوجين ذمة مالية مستقلة عن ذمة الآخر، غير أنه يجوز لهما الاتفاق على استثمار وتوزيع الأموال التي ستكتسب أثناء قيام الزوجية في وثيقة مكتوبة مستقلة عن عقد الزواج. وإذا لم يكن هناك اتفاق، يرجع للقواعد العامة للإثبات بتقدير مجهود كل واحد من الزوجين في تنمية أموال الأسرة.")
        ]
    },
    {
        "doc_title": "ظهير الالتزامات والعقود المغربي (D.O.C - 1913)",
        "source": "الظهير الشريف المؤرخ في 9 رمضان 1331 (12 غشت 1913)",
        "lang": "ar",
        "articles": [
            ("الفصل 230", "الالتزامات التعاقدية المنشأة على وجه صحيح تقوم مقام القانون بالنسبة إلى منشئيها، ولا يجوز إلغاؤها إلا برضاهما معا أو في الحالات التي ينص عليها القانون (العقد شريعة المتعاقدين)."),
            ("الفصل 77", "كل فعل ارتكبه الإنسان عن بينة واختيار، ومن غير أن يسمح به القانون، فأحدث ضررا ماديا أو معنويا للغير، ألزم مرتكبه بتعويض هذا الضرر، إذا ثبت أن ذلك الفعل هو السبب المباشر في حصول الضرر."),
            ("الفصل 264", "الضرر هو ما لحق الدائن من خسارة حقيقية وما فاته من كسب متى كانا ناتجين مباشرة عن عدم الوفاء بالالتزام أو التأخر فيه."),
            ("الفصل 388", "تتقادم بسنتين دعوى الأجراء والخدم والعمال عن أجورهم ومستحقاتهم، بينما تتقادم الالتزامات التجارية بخمس سنوات والمدنية العامة بخمسة عشر سنة.")
        ]
    }
]

def init_rag_db():
    """Initialise les tables FTS5 et indexe les textes fondamentaux s'ils ne sont pas présents."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # WAL mode pour lectures simultanées pendant indexation
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Création des tables
    c.executescript("""
    CREATE TABLE IF NOT EXISTS law_docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source TEXT,
        lang TEXT,
        created REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS law_chunks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        article TEXT,
        text TEXT NOT NULL,
        created REAL NOT NULL
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS law_fts USING fts5(
        article,
        text,
        tokenize='unicode61'
    );
    """)
    
    # Vérification si les statuts fondamentaux sont déjà injectés
    count = c.execute("SELECT count(*) FROM law_chunks").fetchone()[0]
    if count == 0:
        seed_core_statutes(conn)
    
    conn.close()

def seed_core_statutes(conn):
    """Injecte les lois et articles fondamentaux dans la base RAG SQLite."""
    c = conn.cursor()
    for doc in CORE_MOROCCAN_STATUTES:
        c.execute(
            "INSERT INTO law_docs(title, source, lang, created) VALUES(?,?,?,?)",
            (doc["doc_title"], doc["source"], doc["lang"], time.time())
        )
        doc_id = c.lastrowid
        for art, text in doc["articles"]:
            full_chunk = f"{doc['doc_title']} — {art} : {text}"
            c.execute(
                "INSERT INTO law_chunks(doc_id, article, text, created) VALUES(?,?,?,?)",
                (doc_id, art, full_chunk, time.time())
            )
            chunk_id = c.lastrowid
            c.execute(
                "INSERT INTO law_fts(rowid, article, text) VALUES(?,?,?)",
                (chunk_id, art, full_chunk)
            )
    conn.commit()

def index_pdf_file(filepath: Path, title: str = "", source: str = "الجريدة الرسمية للمملكة المغربية"):
    """Extrait et indexe un PDF officiel depuis backend/data dans la base RAG."""
    if not filepath.exists():
        return 0
    try:
        import pypdf
        reader = pypdf.PdfReader(filepath)
        full_text = []
        for i, page in enumerate(reader.pages[:40]):  # Jusqu'à 40 pages par document pour préserver les perfs
            t = page.extract_text() or ""
            if t.strip():
                full_text.append(t.strip())
        
        all_text = "\n".join(full_text)
        if not all_text.strip():
            return 0

        # Découpage par articles
        chunks = re.split(r"(?=(?:المادة|الفصل|Article|Art\.)\s*[0-9\u0660-\u0669]+)", all_text)
        doc_name = title or filepath.stem
        
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        c = conn.cursor()
        c.execute(
            "INSERT INTO law_docs(title, source, lang, created) VALUES(?,?,?,?)",
            (doc_name[:200], source[:200], "ar", time.time())
        )
        doc_id = c.lastrowid
        
        inserted = 0
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) < 40:
                continue
            m = re.match(r"(?:المادة|الفصل|Article|Art\.)\s*[0-9\u0660-\u0669]+", chunk)
            art = m.group(0) if m else "مقتضى قانوني"
            
            clean_chunk = f"{doc_name} — {chunk[:1600]}"
            c.execute(
                "INSERT INTO law_chunks(doc_id, article, text, created) VALUES(?,?,?,?)",
                (doc_id, art, clean_chunk, time.time())
            )
            cid = c.lastrowid
            c.execute(
                "INSERT INTO law_fts(rowid, article, text) VALUES(?,?,?)",
                (cid, art, clean_chunk)
            )
            inserted += 1

        conn.commit()
        conn.close()
        return inserted
    except Exception as e:
        print(f"Error indexing {filepath.name}: {e}")
        return 0

def prepare_fts_query(q: str) -> str:
    """Nettoie, normalise et enrichit la requête pour SQLite FTS5 (arabe, français, darija)."""
    terms = re.findall(r"[\w\u0600-\u06FF]{2,}", (q or "").lower())
    stop_words = {
        "the", "and", "les", "des", "pour", "dans", "avec", "sur", "par", "une", "un", "est", "sont", "que", "qui",
        "على", "من", "في", "إلى", "عن", "مع", "هذا", "هذه", "التي", "الذي", "بين", "كل", "عبر",
        "كيف", "ماذا", "هل", "هو", "هي", "شحال", "واش", "شنو", "ديال", "فاش", "باش", "علاش", "كفاش"
    }
    filtered = [t for t in terms if t not in stop_words][:8]
    if not filtered:
        return ""

    expanded = set()
    for t in filtered:
        clean = t.replace('"', '').replace("'", "")
        expanded.add(f'{clean}*')
        
        # Enlever / ajouter le préfixe 'ال' pour l'arabe
        if clean.startswith("ال") and len(clean) > 3:
            expanded.add(f'{clean[2:]}*')
        elif len(clean) >= 3 and re.search(r"[\u0600-\u06FF]", clean):
            expanded.add(f'ال{clean}*')

        # Synonymes & correspondances juridiques bilingues
        if any(k in clean for k in ["طرد", "licenciement", "licencier"]):
            expanded.update(["فصل*", "الفصل*", "تعسف*", "التعسف*"])
        if any(k in clean for k in ["كراء", "bail", "loyer", "locataire"]):
            expanded.update(["كراء*", "الكراء*", "إفراغ*", "الوجيبة*"])
        if any(k in clean for k in ["أجر", "اجر", "salaire"]):
            expanded.update(["أجر*", "أجرة*", "الأجر*", "salaire*"])
        if any(k in clean for k in ["طلاق", "divorce", "نفقة", "moudawana"]):
            expanded.update(["تطليق*", "شقاق*", "نفقة*", "حضانة*"])
        if any(k in clean for k in ["شركة", "societe", "sarl"]):
            expanded.update(["شركة*", "الشركات*", "تجاري*"])

    return " OR ".join(sorted(expanded))

def search_laws(query: str, limit: int = 5) -> list:
    """Recherche plein texte dans le corpus juridique avec ranking BM25."""
    init_rag_db()
    fts_q = prepare_fts_query(query)
    if not fts_q:
        return []

    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)  # 5s timeout pour éviter le blocage lors de l'indexation
        conn.execute("PRAGMA journal_mode=WAL")      # WAL mode: lecture simultanée possible pendant les écritures
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        rows = c.execute(
            """
            SELECT rowid, article, text, bm25(law_fts) AS rank
            FROM law_fts
            WHERE law_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_q, limit)
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return results
    except Exception:
        return []

def get_rag_context(query: str, limit: int = 4) -> str:
    """Construit un bloc de contexte juridique officiel pour le prompt LLM."""
    results = search_laws(query, limit=limit)
    if not results:
        return ""
    
    parts = []
    for r in results:
        art = r.get("article") or "مقتضى قانوني"
        txt = r.get("text") or ""
        parts.append(f"⚖️ [{art}]\n{txt[:1200]}")
    
    return "\n\n".join(parts)

def get_rag_stats() -> dict:
    """Retourne les statistiques de la base RAG."""
    init_rag_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    docs_cnt = c.execute("SELECT count(*) FROM law_docs").fetchone()[0]
    chunks_cnt = c.execute("SELECT count(*) FROM law_chunks").fetchone()[0]
    conn.close()
    return {
        "total_documents": docs_cnt,
        "total_law_chunks": chunks_cnt,
        "status": "ready"
    }
