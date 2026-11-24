# models_service.py — Dalil Legal Model & Document Generation Service
# Indexes 1,788 authentic Moroccan legal documents, contracts, procurations, administrative requests
# and provides AI-powered dynamic document generation with Groq and python-docx.

import os, re, uuid, time
from pathlib import Path
from io import BytesIO
import httpx
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
GENERATED_DIR = BASE_DIR / "generated_docs"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = [
    {
        "id": "contrats",
        "name_ar": "عقود وتصرفات قانونية",
        "name_fr": "Contrats & Conventions",
        "keywords": ["عقد", "كراء", "بيع", "شراء", "تنازل", "شراكة", "هبة", "اتفاق", "صلح", "مقاولة", "مأذونية", "طاكسي", "محل"]
    },
    {
        "id": "procurations",
        "name_ar": "وكالات وتفويضات",
        "name_fr": "Procurations & Mandats",
        "keywords": ["وكالة", "تفويض", "توكيل", "إنابة", "تمثيل", "سياقة", "قارب", "تحفيظ"]
    },
    {
        "id": "engagements",
        "name_ar": "التزامات وإشهادات وتصاريح",
        "name_fr": "Engagements & Déclarations sur l'honneur",
        "keywords": ["التزام", "تصريح", "إشهاد", "شهادة", "بالشرف", "إقرار", "ضياع", "سكنى", "عزوبة", "تحمل", "مسؤولية"]
    },
    {
        "id": "contentieux",
        "name_ar": "شكايات ونزاعات وإنذارات",
        "name_fr": "Plaintes, Mises en demeure & Contentieux",
        "keywords": ["شكاية", "إنذار", "دعوى", "مقال", "تبليغ", "طعن", "تعرض", "نفقة", "استرجاع", "إفراغ", "أداء", "محكمة"]
    },
    {
        "id": "travail",
        "name_ar": "شغل ومستخدمين وتوظيف",
        "name_fr": "Droit du travail & Recrutement",
        "keywords": ["أجرة", "استقالة", "تغيب", "عقد عمل", "طرد", "مغادرة", "شهادة عمل", "صولدي", "مرض", "cv", "سيرة"]
    },
    {
        "id": "societes",
        "name_ar": "شركات وتعاونيات وجمعيات",
        "name_fr": "Sociétés, Coopératives & Associations",
        "keywords": ["شركة", "تعاونية", "جمعية", "محضر", "تأسيس", "قانون أساسي", "جمع عام", "حصة", "تسيير", "سجل تجاري"]
    },
    {
        "id": "demandes",
        "name_ar": "طلبات ورخص إدارية",
        "name_fr": "Demandes & Autorisations administratives",
        "keywords": ["طلب", "رخصة", "ترخيص", "شهادة", "إعفاء", "تسجيل", "تجديد", "مغادرة", "بطاقة", "جواز", "demande"]
    }
]

_MODELS_CACHE = []
_CACHE_TIME = 0

def clean_title(filename: str) -> str:
    """Nettoie le nom de fichier pour un affichage juridique soigné."""
    name = Path(filename).stem
    name = re.sub(r"^\d+[\s\-_+]*", "", name)  # supprime les préfixes numériques "01-", "02+"
    name = re.sub(r"[\-_+]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def detect_category(filename: str) -> dict:
    fname_lower = filename.lower()
    for cat in CATEGORIES:
        for kw in cat["keywords"]:
            if kw.lower() in fname_lower:
                return cat
    return {
        "id": "divers",
        "name_ar": "وثائق ومراسلات متنوعة",
        "name_fr": "Documents divers",
        "keywords": []
    }

def get_all_models():
    """Charge et indexe les 1,788 fichiers du dossier models."""
    global _MODELS_CACHE, _CACHE_TIME
    if _MODELS_CACHE and (time.time() - _CACHE_TIME < 3600):
        return _MODELS_CACHE

    if not MODELS_DIR.exists():
        return []

    items = []
    for f in os.listdir(MODELS_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext not in (".docx", ".pdf"):
            continue
        filepath = MODELS_DIR / f
        try:
            stat = filepath.stat()
            size_kb = round(stat.st_size / 1024, 1)
        except Exception:
            size_kb = 0

        cat = detect_category(f)
        clean = clean_title(f)
        
        items.append({
            "filename": f,
            "title": clean,
            "category_id": cat["id"],
            "category_ar": cat["name_ar"],
            "category_fr": cat["name_fr"],
            "extension": ext,
            "size_kb": size_kb
        })

    _MODELS_CACHE = sorted(items, key=lambda x: x["title"])
    _CACHE_TIME = time.time()
    return _MODELS_CACHE

def norm_ar(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[أإآ]", "ا", s)
    s = re.sub(r"[ة]", "ه", s)
    s = re.sub(r"[ى]", "ي", s)
    return s


def search_models(query: str, category_id: str = None, limit: int = 25):
    """Recherche plein texte tolérante en arabe et français parmi les modèles."""
    all_items = get_all_models()
    if not query and not category_id:
        return all_items[:limit]

    # Mots vides et mots génériques à faible poids juridique
    generic_stopwords = {
        "بطاقة", "الوطنية", "تعريف", "رقم", "السيد", "السيدة", "انا", "الموقع", "اسفله",
        "حامل", "الساكن", "شارع", "تاريخ", "الدار", "البيضاء", "الرباط", "فاس", "مراكش", "طنجة",
        "مدينة", "موديل", "نوع", "سنة", "سنوات", "شهريا", "درهم", "لينوب", "عني", "في", "على",
        "من", "الى", "مع", "هذا", "هذه", "اريد", "بغيت", "نموذج", "صاوب", "كتب", "ليا", "وثيقة"
    }

    # Mots-clés juridiques déterminants (poids fort)
    high_priority_keywords = {
        "عقد", "وكالة", "استقالة", "كراء", "بيع", "شراء", "تنازل", "شكاية", "انذار",
        "التزام", "اقرار", "اشهاد", "صلح", "هبة", "شراكة", "مأذونية", "سيارة", "شقة",
        "محل", "منزل", "عمل", "قارب", "طرد", "نفقة", "سياقة", "محضر", "تأسيس", "تعاونية"
    }

    raw_terms = [t for t in re.split(r"[\s,;،.]+", (query or "").lower().strip()) if len(t) > 1]
    norm_terms = [norm_ar(t) for t in raw_terms]

    results = []
    for item in all_items:
        if category_id and item["category_id"] != category_id:
            continue
        
        if not norm_terms:
            results.append((0, item))
            continue

        item_norm_title = norm_ar(item["title"])
        item_norm_file = norm_ar(item["filename"])
        target = f"{item_norm_file} {item_norm_title} {norm_ar(item['category_ar'])}"

        score = 0
        for nt in norm_terms:
            if nt in generic_stopwords:
                # Faible score pour les mots courants
                if nt in item_norm_title:
                    score += 1
                continue

            if nt in target:
                base_score = 10 if nt in high_priority_keywords else 3
                if nt in item_norm_title:
                    base_score *= 2
                score += base_score

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


def find_best_model_for_prompt(prompt: str):
    """Trouve automatiquement le modèle le plus pertinent pour une demande utilisateur."""
    # 1. Extraction des 20 premiers mots souvent porteurs de l'intention (ex: أريد نموذج وكالة لبيع سيارة)
    first_sentence = re.split(r"[.\n،]", prompt or "")[0].strip()
    targeted_query = first_sentence if len(first_sentence) > 5 else prompt

    results = search_models(targeted_query, limit=5)
    if results:
        return results[0]

    # 2. Fallback sur le prompt complet
    fallback = search_models(prompt, limit=3)
    return fallback[0] if fallback else None

def extract_template_text(filename: str) -> str:
    """Extrait le texte brut d'un modèle docx ou pdf pour analyse par l'IA."""
    filepath = MODELS_DIR / filename
    if not filepath.exists():
        return ""
    
    ext = filepath.suffix.lower()
    if ext == ".docx":
        try:
            doc = docx.Document(filepath)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception:
            return ""
    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(filepath)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:15000]
        except Exception:
            return ""
    return ""

def create_styled_docx(title: str, text_content: str, lang: str = "ar") -> bytes:
    """Génère un document Word (.docx) professionnel avec style marocain haut de gamme."""
    doc = docx.Document()
    
    # Configuration des marges
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    is_rtl = lang in ("ar", "ary")

    # Titre du document
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run(title)
    title_run.font.name = "Arial" if is_rtl else "Calibri"
    title_run.font.size = Pt(16)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x1F, 0x1E, 0x1D)
    title_p.paragraph_format.space_after = Pt(20)

    # Corps du document
    paras = text_content.strip().split("\n")
    for raw in paras:
        line = raw.strip()
        if not line:
            doc.add_paragraph().paragraph_format.space_after = Pt(6)
            continue

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_rtl else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_after = Pt(8)

        # Détection des sous-titres / articles
        is_heading = bool(re.match(r"^(المادة|الفصل|البند|الموضوع|الطرف الأول|الطرف الثاني|أنا الموقع|Article)\b", line))
        
        run = p.add_run(line)
        run.font.name = "Arial" if is_rtl else "Calibri"
        run.font.size = Pt(12) if not is_heading else Pt(13)
        run.font.bold = is_heading
        if is_heading:
            run.font.color.rgb = RGBColor(0x8A, 0x65, 0x2A)  # Couleur or/bronze

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()

async def generate_filled_document(
    template_filename: str,
    user_request: str,
    groq_api_key: str,
    groq_url: str = "https://api.groq.com/openai/v1/chat/completions",
    model: str = "openai/gpt-oss-120b",
    lang: str = "ar"
) -> dict:
    """Utilise l'authentique modèle Word existant et Groq pour générer un document sur-mesure."""
    template_text = extract_template_text(template_filename) if template_filename else ""
    template_clean_title = clean_title(template_filename) if template_filename else "وثيقة قانونية مخصصة"

    system_prompt = f"""Tu es le juriste expert en rédaction d'actes juridiques et administratifs au Maroc de dalillegal.ma.
Ta mission est de rédiger un acte juridique/administratif complet, prêt à l'emploi et parfaitement conforme à la pratique notariale et administrative marocaine.

Directives absolues :
1. Rédige l'intégralité du document (du titre aux signatures).
2. Si un modèle de base est fourni, respecte scrupuleusement sa structure juridique marocaine authentique tout en insérant les informations fournies par l'utilisateur.
3. Remplis les champs avec les données fournies par l'utilisateur. Pour les données manquantes (ex: numéro CIN précis s'il n'est pas fourni), insère des pointillés clairs comme : ....................
4. Ne mets aucun commentaire méta, pas d'introduction ("Voici votre document :") ni de conclusion ("J'espère que cela vous convient"). Donne UNIQUEMENT le texte exact du document.
5. Langue : Rédige en langue {lang} (arabe juridique marocain standard ou français juridique selon la demande).
"""

    user_content = f"""MODÈLE DE BASE ({template_clean_title}) :
{template_text[:4000] if template_text else "Pas de modèle spécifique, rédige un acte standard marocain."}

DEMANDE ET DONNÉES DE L'UTILISATEUR :
{user_request}

Rédige maintenant le document juridique complet :"""

    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 2500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    }
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    generated_text = ""
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(groq_url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                generated_text = data["choices"][0]["message"]["content"].strip()
            else:
                generated_text = f"Erreur génération IA ({resp.status_code}): {resp.text[:200]}\n\nTexte du modèle de base :\n{template_text}"
    except Exception as e:
        generated_text = f"Erreur réseau IA : {str(e)}\n\nTexte du modèle de base :\n{template_text}"

    # Sauvegarde du document Word stylé
    file_id = f"doc_{uuid.uuid4().hex[:12]}"
    out_filename = f"{template_clean_title}.docx"
    docx_bytes = create_styled_docx(template_clean_title, generated_text, lang)
    
    save_path = GENERATED_DIR / f"{file_id}.docx"
    with open(save_path, "wb") as f:
        f.write(docx_bytes)

    return {
        "file_id": file_id,
        "title": template_clean_title,
        "filename": out_filename,
        "download_url": f"/api/models/download_generated/{file_id}",
        "preview_text": generated_text[:1200],
        "created": time.time()
    }
