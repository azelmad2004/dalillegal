# main.py — dalillegal.ma — Plateforme d'Intelligence Juridique Marocaine
# Droit Positif Marocain : Code du Travail (Loi 65-99), DOC, Loi 67-12, Loi 49-16, Moudawana (Loi 70-03)
# Multilingue : Darija (Arabe & Arabizi), Arabe Juridique, Français Juridique

import os, re, json, time, sqlite3
from pathlib import Path
from io import BytesIO

import bcrypt, jwt, httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import models_service
import rag_service

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
FRONTEND = ROOT / "frontend" if (ROOT / "frontend").exists() else BASE_DIR / "frontend"

load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT / ".env")

SECRET = os.getenv("JWT_SECRET", "dalil_legal_ultra_secure_secret_key_2026_morocco")

def _resoudre_chemin_db():
    p = BASE_DIR / "dalillegal.db"
    try:
        conn = sqlite3.connect(p)
        conn.close()
        return p
    except Exception:
        return Path(os.environ.get("TEMP", ".")) / "dalillegal.db"

DB = _resoudre_chemin_db()

# LLM compatible OpenAI : Groq 120B par défaut
LLM_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

LANGS = {
    "ary": "Moroccan Darija (الدارجة المغربية). Rédige en ARABE (خط عربي واضح ومفهوم). Si l'utilisateur a écrit en lettres latines simples (ex: salam, khedam), réponds en Arabe marocain naturel (بالحروف العربية) sans AUCUN caractère phonétique bizarre.",
    "ar": "Modern Standard Arabic (اللغة العربية القانونية السليمة المعتمدة في محاكم المملكة المغربية والجريدة الرسمية)",
    "fr": "French (Français juridique marocain technique et rigoureux, terminologie officielle du Bulletin Officiel du Royaume du Maroc)",
    "en": "English (Accurate Moroccan legal concepts with statutory references)",
    "es": "Spanish (Derecho positivo marroquí con citas legales precisas)",
}

SYSTEM = """Tu es Dalil Legal (دليل القانوني) — l'assistant juridique d'élite propulsé par l'IA, spécialisé exclusivement dans le Droit Marocain positif.

MISSION SUPRÊME :
Fournir aux justiciables, salariés, employeurs, propriétaires, locataires et juristes au Maroc des consultations juridiques exhaustives, rigoureuses, chiffrées au dirham près et strictement appuyées sur les textes législatifs et réglementaires en vigueur dans le Royaume du Maroc (Bulletin Officiel / الجريدة الرسمية).

═══════════════════════════════════════════════════════════════════
RÈGLE FONDAMENTALE DE RÉDACTION LINGUISTIQUE (TRÈS IMPORTANT) :
═══════════════════════════════════════════════════════════════════
- INTERDICTION ABSOLUE D'UTILISER DES SYMBOLES DE TRANSLITTÉRATION PHONÉTIQUE ACADÉMIQUE OU ORIENTALISTE (ex: ʿ, ā, ī, ū, ḥ, ḍ, ṭ, ṣ, ẓ, ʾ, etc.).
- Tout texte destiné à un locuteur arabophone ou marocain DOIT être écrit en ALPHABET ARABE NATUREL (خط عربي مغربي أصيل وواضح).
- Si l'utilisateur écrit en français, réponds en français juridique impeccable.
- Ne JAMAIS produire de texte latin parsemé de signes diacritiques ou phonétiques bizarres (comme "l‑mousaʿada l‑qānūniya") : cela est totalement illisible et rejeté par les utilisateurs marocains.

═══════════════════════════════════════════════════════════════════
ADAPTATION LINGUISTIQUE AUTOMATIQUE :
═══════════════════════════════════════════════════════════════════
1. DARIJA OU ARABE (Ex: "salam", "سلام", "khedam 5 snin o jraw 3liya...") :
   - Réponds en ARABE MAROCAIN (خط عربي) clair, fluide et professionnel.
   - Utilise le vocabulaire juridique marocain d'usage : "الطرد التعسفي", "التعويض عن الإشعار (Préavis)", "الصولدي (Solde de tout compte)", "العقدة (Contrat)", "المفوض القضائي (Huissier)", "مفتش الشغل (Inspecteur du travail)", "السومة الكرائية", "واجب الضمانة".
   - Explique les démarches de manière concrète (المراحل، الآجال، والوثائق اللي خاصو يوجد).

2. FRANÇAIS JURIDIQUE MAROCAIN :
   - Terminologie officielle marocaine exacte issue des Dahirs et Codes marocains.

═══════════════════════════════════════════════════════════════════
CORPUS LÉGISLATIF MAROCAIN INTÉGRÉ (CITATIONS EXACTES OBLIGATOIRES) :
═══════════════════════════════════════════════════════════════════

1. CODE DU TRAVAIL (Loi n° 65-99 promulguée par Dahir n° 1-03-194) :
   • Licenciement abusif (Art. 41) :
     - Dommages-intérêts : 1,5 mois de salaire par an ou fraction d'année d'ancienneté, plafonnés à 36 mois.
     - Indemnité de préavis : Art. 43 et Décret n° 2-04-469 du 29 décembre 2004 :
       * Cadres et assimilés : < 1 an = 1 mois | 1 à 5 ans = 2 mois | > 5 ans = 3 mois.
       * Ouvriers et employés : < 1 an = 8 jours | 1 à 5 ans = 1 mois | > 5 ans = 2 mois.
     - Indemnité légale de licenciement (Art. 52 et 53) : par an d'ancienneté (base horaire standard = salaire mensuel / 191 heures) :
       * 1 à 5 ans : 96 heures par an
       * 6 à 10 ans : 144 heures par an
       * 11 à 15 ans : 192 heures par an
       * Plus de 15 ans : 240 heures par an
     - Congés payés non pris (Art. 251 à 254 : 1,5 jour par mois de travail effectif).
   • Procédure impérative de licenciement pour faute grave (Art. 62 à 65) :
     - Entretien d'écoute préalable dans un délai maximum de 8 jours de la constatation.
     - Présence obligatoire d'un délégué du personnel si souhaité par le salarié.
     - PV signé séance tenante. Notification sous 48 heures par lettre recommandée avec AR ou remise en main propre contre décharge. Copie à l'Inspection du Travail dans les 48h. À défaut, le licenciement est réputé sans cause réelle et sérieuse (licenciement abusif).
   • Reçu pour solde de tout compte (Art. 73 à 76) : délai de dénonciation de 60 jours.

2. BAUX D'HABITATION ET PROFESSIONNELS (Loi n° 67-12) :
   • Forme (Art. 3) : Contrat écrit à date certaine et état des lieux contradictoire.
   • Caution (Art. 7) : Plafonnée impérativement à 2 mois de loyer. Restitution obligatoire dans le mois suivant la remise des clés.
   • Révision du loyer (Art. 31 à 38) : Triennale (tous les 3 ans). Augmentation légale plafonnée à 8% (habitation) et 10% (professionnel).
   • Résiliation pour impayés (Art. 45 à 52) : Mise en demeure avec délai légal de 15 jours.

3. BAUX COMMERCIAUX (Loi n° 49-16) :
   • Droit au renouvellement : Acquis après 2 ans de bail écrit (ou 4 ans de bail verbal).
   • Indemnité d'éviction (Art. 7) : Valeur marchande du fonds de commerce basée sur les déclarations fiscales des 3 dernières années + frais de déménagement et réinstallation.
   • Refus sans indemnité (Art. 8) : 3 mois de loyers impayés بعد إنذار بالأداء لمدة 15 يوما.

4. CODE DES OBLIGATIONS ET CONTRATS (DOC — Dahir du 12 août 1913) :
   • Art. 230 : Les conventions légalement formées tiennent lieu de loi ("العقد شريعة المتعاقدين").
   • Art. 77 et 78 : Responsabilité civile quasi-délictuelle (faute, dommage, causalité).
   • Art. 264 : Dommages et intérêts réparant perte subie et gain manqué.
   • Prescription : 15 ans en matière civile, 5 ans en commercial, 2 ans pour les salaires (Art. 388).

5. CODE DE LA FAMILLE (Moudawana — Loi n° 70-03) :
   • Divorce Chiqaq (Art. 94 à 97) : Procédure devant la section de justice de famille, tentative de conciliation, fixation des droits dans un délai maximum de 6 mois.
   • Droits financiers (Art. 84) : Mout'â, 'Idda, reliquat de dot.
   • Pension alimentaire (Nafâqa - Art. 187 à 205) : Logement, scolarité, soins jusqu'à 18 ans (ou 25 ans si études).
   • Garde des enfants (Hadana - Art. 163 à 179) : Priorité à la mère, puis au père.

═══════════════════════════════════════════════════════════════════
STRUCTURE DE CONSULTATION (UNIQUEMENT POUR UNE QUESTION JURIDIQUE PRÉCISE) :
═══════════════════════════════════════════════════════════════════
Si l'utilisateur envoie une simple salutation ou politesse, NE PAS utiliser cette structure.
Lorsqu'un litige ou une vraie question est posée, utilise :
1. ⚖️ **Synthèse Juridique** : Diagnostic clair en 2 à 3 phrases.
2. 📜 **Base Légale Applicable** : Articles de loi et Dahirs précis (ne jamais inventer d'article).
3. 💰 **Calculs & Délais Concrets** : Chiffrage en Dirhams (DH) ou calendrier des délais légaux.
4. 📋 **Plan d'Action Immédiat & Pièces à Préparer** : Étapes numérotées et liste à puces des justificatifs.
5. ⚠️ **Avertissement Déontologique** : Information juridique, ne dispense pas d'un avocat inscrit au Barreau.
"""

app = FastAPI(title="dalillegal.ma — Plateforme d'Intelligence Juridique")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            pw BLOB NOT NULL,
            created REAL NOT NULL
        );

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

        CREATE TABLE IF NOT EXISTS decisions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            court TEXT,
            case_no TEXT,
            year INTEGER,
            article TEXT,
            outcome TEXT,
            summary TEXT,
            created REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            masked_text TEXT,
            expires REAL NOT NULL,
            created REAL NOT NULL
        );
        """)
    cleanup_files()


def cleanup_files():
    with db() as c:
        c.execute("DELETE FROM files WHERE expires < ?", (time.time(),))


init_db()
rag_service.init_rag_db()


# ---------- AUTH ----------
class Reg(BaseModel):
    name: str
    email: str
    password: str


class Log(BaseModel):
    email: str
    password: str


def token(uid):
    return jwt.encode(
        {"sub": str(uid), "exp": time.time() + 7 * 86400},
        SECRET,
        "HS256",
    )


def user_from(auth, optional: bool = False):
    if not auth:
        if optional:
            return None
        raise HTTPException(401, "auth")
    try:
        raw = (auth or "").removeprefix("Bearer ").strip()
        uid = int(jwt.decode(raw, SECRET, ["HS256"])["sub"])
    except Exception:
        if optional:
            return None
        raise HTTPException(401, "auth")
    with db() as c:
        u = c.execute("SELECT id,name,email FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        if optional:
            return None
        raise HTTPException(401, "auth")
    return dict(u)


def execute_register(r: Reg):
    email = r.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "email")
    if len(r.password) < 6:
        raise HTTPException(400, "password")
    if not r.name.strip():
        raise HTTPException(400, "name")
    try:
        with db() as c:
            cur = c.execute(
                "INSERT INTO users(name,email,pw,created) VALUES(?,?,?,?)",
                (
                    r.name.strip()[:80],
                    email,
                    bcrypt.hashpw(r.password.encode(), bcrypt.gensalt()),
                    time.time(),
                ),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "exists")
    return {
        "token": token(cur.lastrowid),
        "user": {"id": cur.lastrowid, "username": r.name.strip(), "name": r.name.strip(), "email": email},
    }


def execute_login(r: Log):
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (r.email.strip().lower(),)).fetchone()
    if not u or not bcrypt.checkpw(r.password.encode(), u["pw"]):
        raise HTTPException(401, "credentials")
    return {
        "token": token(u["id"]),
        "user": {"id": u["id"], "username": u["name"], "name": u["name"], "email": u["email"]},
    }


# Endpoints /api/*
@app.post("/api/register")
def register_api(r: Reg):
    return execute_register(r)


@app.post("/api/login")
def login_api(r: Log):
    return execute_login(r)


@app.get("/api/me")
def me_api(authorization: str = Header(None)):
    u = user_from(authorization)
    return {"id": u["id"], "username": u["name"], "name": u["name"], "email": u["email"]}


# Endpoints /auth/* (Compatibilité multi-frontends)
@app.post("/auth/register")
def register_auth(r: Reg):
    return execute_register(r)


@app.post("/auth/login")
def login_auth(r: Log):
    return execute_login(r)


@app.get("/auth/me")
def me_auth(authorization: str = Header(None)):
    u = user_from(authorization)
    return {"id": u["id"], "username": u["name"], "name": u["name"], "email": u["email"]}


# ---------- PII ----------
PII_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[EMAIL]"),
    (re.compile(r"\b0[5-7]\d{8}\b"), "[TEL]"),
    (re.compile(r"\b[A-Z]{1,3}\d{4,8}\b"), "[CIN]"),
    (re.compile(r"\b\d{24}\b"), "[RIB]"),
]


def mask_pii(text: str) -> str:
    for pat, repl in PII_PATTERNS:
        text = pat.sub(repl, text)
    return text


# ---------- RAG local ----------
def fts_query(q: str) -> str:
    terms = re.findall(r"[\w\u0600-\u06FF]{2,}", (q or "").lower())
    stop = {"the", "and", "les", "des", "pour", "dans", "avec", "على", "من", "في", "إلى", "هو", "هي"}
    terms = [t for t in terms if t not in stop][:12]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)


def rag_search(query: str, limit: int = 6):
    q = fts_query(query)
    if not q:
        return []
    try:
        with db() as c:
            rows = c.execute(
                """
                SELECT rowid, article, text, bm25(law_fts) AS rank
                FROM law_fts
                WHERE law_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (q, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def rag_context(query: str, limit: int = 6) -> str:
    ctx = rag_service.get_rag_context(query, limit)
    if ctx:
        return ctx
    rows = rag_search(query, limit)
    if not rows:
        return ""
    parts = []
    for r in rows:
        article = r.get("article") or "Extrait"
        parts.append(f"[{article}]\n{(r.get('text') or '')[:1400]}")
    return "\n\n".join(parts)


def split_chunks(text: str):
    text = re.sub(r"\r\n?", "\n", text or "").strip()
    parts = re.split(
        r"(?=(?:Article|ARTICLE|Art\.?|المادة)\s*[0-9\u0660-\u0669]+)",
        text,
    )
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= 1800:
            out.append(p)
        else:
            for i in range(0, len(p), 1500):
                out.append(p[i:i + 1500].strip())
    return out


def ingest_law_text(title: str, source: str, lang: str, text: str):
    chunks = split_chunks(text)
    if not chunks:
        raise HTTPException(400, "empty text")
    with db() as c:
        cur = c.execute(
            "INSERT INTO law_docs(title,source,lang,created) VALUES(?,?,?,?)",
            (title[:200], source[:300], lang[:10], time.time()),
        )
        doc_id = cur.lastrowid
        for chunk in chunks:
            m = re.match(r"(?:Article|ARTICLE|Art\.?|المادة)\s*[0-9\u0660-\u0669]+", chunk)
            article = m.group(0) if m else ""
            cc = c.execute(
                "INSERT INTO law_chunks(doc_id,article,text,created) VALUES(?,?,?,?)",
                (doc_id, article, chunk, time.time()),
            )
            c.execute(
                "INSERT INTO law_fts(rowid,article,text) VALUES(?,?,?)",
                (cc.lastrowid, article, chunk),
            )
    return {"doc_id": doc_id, "chunks": len(chunks)}


class LawIn(BaseModel):
    title: str
    source: str = ""
    lang: str = "fr"
    text: str


@app.post("/api/laws/ingest_text")
def ingest_law(r: LawIn, authorization: str = Header(None)):
    user_from(authorization)
    return ingest_law_text(r.title, r.source, r.lang, r.text)


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        except Exception:
            pass
    if ext in (".docx",):
        try:
            from docx import Document
            d = Document(BytesIO(data))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception:
            pass
    if ext in (".txt", ".md", ".csv"):
        return data.decode("utf-8", errors="replace")
    if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(BytesIO(data))
            return pytesseract.image_to_string(img, lang=os.getenv("OCR_LANGS", "ara+fra"))
        except Exception:
            pass
    return "Fichier reçu mais extraction non disponible sur ce format."


@app.post("/api/laws/ingest_file")
async def ingest_law_file(
    authorization: str = Header(None),
    file: UploadFile = File(...),
    title: str = Form(...),
    source: str = Form(""),
    lang: str = Form("fr"),
):
    user_from(authorization)
    data = await file.read()
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(413, "file too large")
    text = extract_text(file.filename or "upload", data)
    return ingest_law_text(title, source, lang, text)


# ---------- CALCUL DÉTERMINISTE (CODE DU TRAVAIL MAROCAIN ART. 53) ----------
class CalcIn(BaseModel):
    monthly_salary: float
    years: float
    is_cadre: bool = False
    rate_per_year: float | None = None
    cap_months: float | None = None
    label: str = ""


@app.post("/api/calc/indemnite")
def calc_indemnite(r: CalcIn, authorization: str = Header(None)):
    user_from(authorization, optional=True)
    if r.monthly_salary < 0 or r.years < 0:
        raise HTTPException(400, "negative value")

    # Calcul Article 53 du Code du Travail (heures par an)
    # Taux horaire = salaire mensuel / 191 heures
    taux_horaire = r.monthly_salary / 191.0
    annees = r.years
    heures_totales = 0.0

    # Tranche 1 : 1 à 5 ans = 96h/an
    t1 = min(annees, 5.0)
    heures_totales += t1 * 96.0

    # Tranche 2 : 6 à 10 ans = 144h/an
    if annees > 5.0:
        t2 = min(annees - 5.0, 5.0)
        heures_totales += t2 * 144.0

    # Tranche 3 : 11 à 15 ans = 192h/an
    if annees > 10.0:
        t3 = min(annees - 10.0, 5.0)
        heures_totales += t3 * 192.0

    # Tranche 4 : > 15 ans = 240h/an
    if annees > 15.0:
        t4 = annees - 15.0
        heures_totales += t4 * 240.0

    indemnite_licenciement = round(heures_totales * taux_horaire, 2)

    # Préavis (Art. 43 et Décret 2-04-469)
    if r.is_cadre:
        mois_preavis = 1 if annees < 1 else (2 if annees <= 5 else 3)
    else:
        mois_preavis = 0.25 if annees < 1 else (1 if annees <= 5 else 2)
    indemnite_preavis = round(mois_preavis * r.monthly_salary, 2)

    # Dommages-intérêts licenciement abusif (Art. 41) : 1.5 mois par an, max 36 mois
    mois_dommages = min(annees * 1.5, 36.0)
    dommages_interets = round(mois_dommages * r.monthly_salary, 2)

    total_estime = round(indemnite_licenciement + indemnite_preavis + dommages_interets, 2)

    return {
        "label": r.label or "Indemnités de Licenciement Maroc (Loi 65-99)",
        "salaire_mensuel": r.monthly_salary,
        "anciennete_annees": r.years,
        "indemnite_licenciement_art_53": indemnite_licenciement,
        "heures_legales": round(heures_totales, 1),
        "indemnite_preavis_art_43": indemnite_preavis,
        "dommages_interets_art_41": dommages_interets,
        "total_estime_dh": total_estime,
        "articles": ["Art. 53 (Indemnité de licenciement)", "Art. 43 (Préavis)", "Art. 41 (Dommages-intérêts)"],
        "note": "Calcul rigoureusement conforme au Code du Travail marocain (Loi 65-99) et au Décret n° 2-04-469."
    }


# ---------- DOCUMENTS DOCX ----------
DOC_TEMPLATES = {
    "mise_en_demeure": {
        "fr": """MISE EN DEMEURE

{{expediteur}}
{{adresse_expediteur}}

À : {{destinataire}}
{{adresse_destinataire}}

{{ville}}, le {{date}}

Objet : {{objet}}

Madame, Monsieur,

{{corps}}

Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

{{signature}}""",
        "ar": """إنذار رسمي

{{expediteur}}
{{adresse_expediteur}}

إلى: {{destinataire}}
{{adresse_destinataire}}

{{ville}}، بتاريخ {{date}}

الموضوع: {{objet}}

{{corps}}

{{signature}}""",
    },
    "requete": {
        "fr": """REQUÊTE

À Monsieur le Président du Tribunal {{tribunal}}

Demandeur : {{demandeur}}
Défendeur : {{defendeur}}

Objet : {{objet}}

Faits :
{{faits}}

Demandes :
{{demandes}}

{{ville}}, le {{date}}

{{signature}}""",
    },
}


def fill_template(tpl: str, data: dict) -> str:
    def repl(m):
        key = m.group(1)
        return str(data.get(key, m.group(0)))
    return re.sub(r"\{\{(\w+)\}\}", repl, tpl)


def make_docx(text: str, lang: str = "fr") -> bytes:
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        doc = Document()
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            p = doc.add_paragraph(para)
            if lang in ("ar", "ary"):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except Exception:
        return text.encode("utf-8")


class DocReq(BaseModel):
    template: str
    data: dict = {}
    lang: str = "fr"


@app.get("/api/documents/templates")
def doc_templates(authorization: str = Header(None)):
    user_from(authorization)
    return {"templates": sorted(DOC_TEMPLATES.keys())}


@app.post("/api/documents/generate")
def generate_doc(r: DocReq, authorization: str = Header(None)):
    user_from(authorization)
    tpl = DOC_TEMPLATES.get(r.template)
    if not tpl:
        raise HTTPException(404, "template")
    raw = tpl.get(r.lang) or tpl.get("fr")
    if not raw:
        raise HTTPException(404, "language")
    text = fill_template(raw, r.data)
    content = make_docx(text, r.lang)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{r.template}.docx"'},
    )


# ---------- FICHIERS / OCR ----------
@app.post("/api/files/extract")
async def extract_file(
    authorization: str = Header(None),
    file: UploadFile = File(...),
):
    user = user_from(authorization)
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "file too large")
    text = extract_text(file.filename or "upload", data)
    masked = mask_pii(text)
    with db() as c:
        c.execute(
            "INSERT INTO files(user_id,filename,masked_text,expires,created) VALUES(?,?,?,?,?)",
            (
                user["id"],
                (file.filename or "upload")[:200],
                masked[:50000],
                time.time() + 48 * 3600,
                time.time(),
            ),
        )
    return {
        "filename": file.filename,
        "chars": len(text),
        "pii_masked": text != masked,
        "text": text[:20000],
        "masked_text": masked[:20000],
        "note": "Le texte masqué est stocké localement 48h. Le texte brut n'est pas stocké.",
    }


# ---------- MODÈLES DE DOCUMENTS & GÉNÉRATION IA ----------
@app.get("/api/models/categories")
def get_models_categories():
    all_m = models_service.get_all_models()
    cat_counts = {}
    for m in all_m:
        cid = m.get("category_id", "divers")
        cat_counts[cid] = cat_counts.get(cid, 0) + 1
    cats = []
    for c in models_service.CATEGORIES:
        cats.append({
            **c,
            "count": cat_counts.get(c["id"], 0)
        })
    return {"categories": cats, "total_models": len(all_m)}


@app.get("/api/models/search")
def search_models_api(q: str = "", category: str = None, limit: int = 25):
    items = models_service.search_models(q, category, limit)
    return {"total": len(items), "models": items}


@app.get("/api/models/download/{filename:path}")
def download_original_model(filename: str):
    fpath = models_service.MODELS_DIR / filename
    if not fpath.exists() or not fpath.is_file():
        raise HTTPException(404, "Modèle introuvable")
    return FileResponse(
        path=str(fpath),
        filename=filename,
        media_type="application/octet-stream"
    )


class GenerateModelReq(BaseModel):
    template: str | None = None
    prompt: str
    lang: str = "ar"


@app.post("/api/models/generate")
async def generate_model_api(r: GenerateModelReq, authorization: str = Header(None)):
    user_from(authorization, optional=True)
    tpl_name = r.template
    if not tpl_name:
        best = models_service.find_best_model_for_prompt(r.prompt)
        if best:
            tpl_name = best["filename"]

    res = await models_service.generate_filled_document(
        template_filename=tpl_name,
        user_request=r.prompt,
        groq_api_key=LLM_KEY,
        groq_url=LLM_URL,
        model=LLM_MODEL,
        lang=r.lang
    )
    return res


@app.get("/api/models/download_generated/{file_id}")
def download_generated_doc(file_id: str):
    safe_id = re.sub(r"[^a-zA-Z0-9_]", "", file_id)
    fpath = models_service.GENERATED_DIR / f"{safe_id}.docx"
    if not fpath.exists():
        raise HTTPException(404, "Document généré introuvable ou expiré")
    return FileResponse(
        path=str(fpath),
        filename=f"{safe_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ---------- RAG STATUTS JURIDIQUES MAROCAINS ----------
@app.get("/api/rag/stats")
def rag_stats():
    return rag_service.get_rag_stats()


@app.get("/api/rag/search")
def search_rag_api(q: str = "", limit: int = 5):
    return {"results": rag_service.search_laws(q, limit)}


# ---------- CHAT / LLM (GROQ STREAMING + RAG + AUTO DOC GENERATION) ----------
class Msg(BaseModel):
    role: str
    content: str


class Chat(BaseModel):
    messages: list[Msg] | None = None
    message: str | None = None
    lang: str = "fr"
    conversation_id: str | None = None


def sse(o):
    return f"data: {json.dumps(o, ensure_ascii=False)}\n\n"


DOC_TRIGGER_REGEX = re.compile(
    r"(?:عقد|وكالة|استقالة|شكاية|التزام|نموذج|صاوب|كتب\s+ليا|صنع|وثيقة|شهادة|إنذار|مقال|تنازل|contrat|procuration|mise\s+en\s+demeure|attestation|demande|lettre)",
    re.IGNORECASE
)


def build_messages(r: Chat):
    query = r.message or ""
    msgs = r.messages or []
    if not query and msgs:
        for m in reversed(msgs):
            if m.role == "user":
                query = m.content
                break

    # Détection de simple salutation
    q_stripped = (query or "").strip()
    words = q_stripped.split()
    is_greeting = len(words) <= 5 and bool(re.search(
        r"^(salam|slm|salut|bonjour|bonsoir|hello|hi|hey|coucou|سلام|أهلا|مرحبا|صباح الخير|مساء الخير|لاباس|لباس|كيداير|cv|ca va)\b",
        q_stripped,
        re.IGNORECASE
    ))

    if is_greeting:
        rag_results = []
        context = ""
        user_lang = r.lang if r.lang in LANGS else "ar"
        system = SYSTEM.format(lang=LANGS.get(user_lang, LANGS["ar"]))
        system += """
\n\n👋 L'UTILISATEUR ENVOIE UNE SIMPLE SALUTATION :
Réponds EXCLUSIVEMENT par un message d'accueil chaleureux, poli et très bref (1 à 2 phrases) DANS LA MÊME LANGUE QUE LA SALUTATION :
- Si salué en Arabe ou Darija (ex: "salam", "سلام", "slm", "labas") :
  "وعليكم السلام ورحمة الله! مرحباً بك في دليل القانوني (Dalil Legal). تفضل بطرح استشارتك أو مسألتك القانونية وسأقوم بإفادتك بالمواد القانونية والإجراءات اللازمة."
- Si salué en Français (ex: "bonjour", "salut", "bonsoir") :
  "Bonjour et bienvenue sur Dalil Legal ! Comment puis-je vous aider aujourd'hui dans votre démarche juridique au Maroc ?"
INTERDICTION TOTALE :
- N'affiche AUCUNE section numérotée (Synthèse, Base légale, Calculs, etc.).
- N'affiche AUCUN avertissement déontologique.
- N'utilise AUCUN symbole de translittération phonétique bizarre (ʿ, ā, ḥ, etc.). Sois direct, accueillant et professionnel.
"""
    else:
        # RAG : Injection de textes légaux applicables
        rag_results = rag_service.search_laws(query, limit=4)
        context = rag_service.get_rag_context(query) if rag_results else ""
        system = SYSTEM.format(lang=LANGS.get(r.lang, LANGS["fr"]))
        if context:
            system += (
                "\n\n⚖️ EXTRAITS OFFICIELS DU DROIT MAROCAIN ISSUS DU CORPUS LOCAL (RAG) :\n"
                + context
                + "\n\nINSTRUCTION IMPÉRATIVE : Tu DOIS citer explicitement les articles ci-dessus dans ta réponse avec leurs numéros exacts (ex: 'selon l'article 41 du Code du Travail'). Ne jamais paraphraser sans mentionner la source légale."
            )

    # Détection de demande de modèle d'acte
    best_model = None
    if DOC_TRIGGER_REGEX.search(query):
        best_model = models_service.find_best_model_for_prompt(query)
        if best_model:
            tpl_text = models_service.extract_template_text(best_model["filename"])
            system += f"""
\n📄 L'UTILISATEUR SOUHAITE UN ACTE / MODÈLE JURIDIQUE.
UN MODÈLE AUTHENTIQUE EST DISPONIBLE DANS LA BASE : "{best_model['title']}".
Structure et contenu de référence du modèle :
{tpl_text[:2000]}

Consigne : Rédige pour l'utilisateur une consultation claire suivie du projet complet de cet acte, en précisant que le document Word officiel prêt à signer est en cours de génération pour lui."""

    out = [{"role": "system", "content": system}]
    if msgs:
        for m in msgs[-15:]:
            role = "assistant" if m.role in ("assistant", "bot") else "user"
            out.append({"role": role, "content": mask_pii(m.content[:4000])})
    elif query:
        out.append({"role": "user", "content": mask_pii(query[:4000])})

    return out, best_model, rag_results


async def executer_chat_stream(r: Chat, authorization: str):
    user_from(authorization, optional=True)
    if not LLM_KEY and "groq.com" in LLM_URL:
        return StreamingResponse(
            iter([sse({"error": "LLM_API_KEY / GROQ_API_KEY missing in .env"})]),
            media_type="text/event-stream",
        )

    messages, matched_model, rag_results = build_messages(r)
    query = r.message or ""
    if not query and r.messages:
        for m in reversed(r.messages):
            if m.role == "user":
                query = m.content
                break

    payload = {
        "model": LLM_MODEL,
        "stream": True,
        "temperature": 0.25,
        "max_tokens": 1500,
        "messages": messages,
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT
    }
    if LLM_KEY:
        headers["Authorization"] = f"Bearer {LLM_KEY}"

    async def gen():
        full_text = ""

        # Émettre les sources RAG si disponibles (avant les tokens)
        if rag_results:
            sources_payload = []
            for r_item in rag_results[:4]:
                art = r_item.get("article") or "مقتضى قانوني"
                txt = r_item.get("text") or ""
                # Extraire le nom du document du début du texte
                doc_name = txt.split(" — ")[0] if " — " in txt else ""
                sources_payload.append({
                    "article": art,
                    "doc": doc_name[:80],
                    "excerpt": txt[len(doc_name)+3:][:300] if doc_name else txt[:300]
                })
            yield sse({"rag_sources": sources_payload})
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                async with c.stream("POST", LLM_URL, json=payload, headers=headers) as g:
                    if g.status_code != 200:
                        body = (await g.aread()).decode(errors="replace")[:400]
                        yield sse({"error": f"Groq {g.status_code}: {body}"})
                        return
                    async for line in g.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        d = line[5:].strip()
                        if d == "[DONE]":
                            break
                        try:
                            t = json.loads(d)["choices"][0]["delta"].get("content")
                        except Exception:
                            continue
                        if t:
                            full_text += t
                            yield sse({"t": t})
        except Exception as e:
            yield sse({"error": str(e)[:300]})

        # Génération automatique du fichier Word si un acte/modèle a été demandé
        if matched_model and LLM_KEY:
            try:
                doc_res = await models_service.generate_filled_document(
                    template_filename=matched_model["filename"],
                    user_request=query or full_text[:400],
                    groq_api_key=LLM_KEY,
                    groq_url=LLM_URL,
                    model=LLM_MODEL,
                    lang=r.lang
                )
                yield sse({"doc_ready": doc_res})
            except Exception as doc_err:
                # Échec silencieux de la génération automatique
                pass

        yield sse({"done": True})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/chat")
async def chat_api(r: Chat, authorization: str = Header(None)):
    return await executer_chat_stream(r, authorization)


@app.post("/chat/stream")
async def chat_stream_alias(r: Chat, authorization: str = Header(None)):
    return await executer_chat_stream(r, authorization)


# ---------- SANTÉ & STATUT ----------
@app.get("/api/health")
@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "dalillegal.ma",
        "model": LLM_MODEL,
        "design_system": "Pure White & Champagne Gold (Luxury)",
        "languages": ["Darija (Arabe & Arabizi)", "Arabe Juridique", "Français Juridique"]
    }


# ---------- FRONTEND SPA & STATIC FILES ----------
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="web")
else:
    @app.get("/")
    def root():
        return {
            "ok": True,
            "app": "dalillegal.ma",
            "docs": "/docs",
            "note": "Frontend directory non trouvé.",
        }
