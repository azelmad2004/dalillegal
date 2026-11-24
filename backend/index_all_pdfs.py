"""
index_all_pdfs.py — Indexation complète des PDFs juridiques dans la base RAG
Lance ce script une seule fois pour ingérer tout le corpus de backend/data/
"""

import sys, os, time, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rag_service

DATA_DIR = Path(__file__).parent / "data"
DB_PATH  = Path(__file__).parent / "dalillegal.db"

# Priorité haute : documents les plus importants (loi du travail, famille, contrats, kiraé, commercial)
HIGH_PRIORITY_KEYWORDS = [
    "شغل", "عمل", "travail", "مدونة", "code", "moudawana", "famille", "أسرة",
    "كراء", "bail", "loyer", "location", "تجاري", "commercial", "عقود",
    "obligations", "contrat", "التزامات", "جنائي", "pénal", "جنايات",
    "مدني", "civil", "قضائي", "judiciaire", "نزاعات", "litiges",
    "تأمين", "assurance", "société", "شركة", "مقاولة",
    "سكن", "logement", "عقار", "immobilier", "habitat",
    "ضريبي", "fiscal", "impôt", "taxe",
    "صحة", "santé", "طبي", "médical",
    "بيئة", "environnement", "تعمير", "urbanisme",
    "استثمار", "investissement", "تجارة", "commerce",
    "مرسوم", "decret", "ظهير", "dahir", "قانون", "loi",
]

def already_indexed(filepath: Path) -> bool:
    """Vérifie si un fichier est déjà dans la base."""
    stem = filepath.stem[:60]
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        row = c.execute("SELECT id FROM law_docs WHERE title LIKE ?", (f"%{stem[:30]}%",)).fetchone()
        conn.close()
        return row is not None
    except:
        return False

def priority_score(name: str) -> int:
    """Score de priorité basé sur les mots-clés du nom de fichier."""
    n = name.lower()
    score = 0
    for kw in HIGH_PRIORITY_KEYWORDS:
        if kw.lower() in n:
            score += 2
    # Pénaliser les fichiers avec des noms cryptiques (seulement chiffres)
    if name[:3].isdigit() or name.startswith("103") or name.startswith("180"):
        score -= 1
    return score

def main():
    # Init DB (seed les 24 articles de base si vide)
    rag_service.init_rag_db()
    
    # Compter l'existant
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT count(*) FROM law_chunks").fetchone()[0]
    existing_docs = conn.execute("SELECT title FROM law_docs").fetchall()
    existing_titles = set(r[0][:40] for r in existing_docs)
    conn.close()
    print(f"Base actuelle : {existing} chunks dans {len(existing_titles)} documents")

    # Lister et trier les PDFs
    all_pdfs = list(DATA_DIR.glob("*.pdf")) + list(DATA_DIR.glob("*.PDF"))
    print(f"PDFs disponibles : {len(all_pdfs)}")

    # Trier par priorité décroissante
    all_pdfs.sort(key=lambda p: -priority_score(p.name))

    total_indexed = 0
    total_chunks  = 0
    errors        = 0
    skipped       = 0
    start         = time.time()

    for i, pdf in enumerate(all_pdfs):
        # Vérifier si déjà indexé
        stem = pdf.stem[:40]
        if any(stem[:20] in t for t in existing_titles):
            skipped += 1
            continue

        try:
            n = rag_service.index_pdf_file(pdf, title=pdf.stem[:200])
            if n > 0:
                total_indexed += 1
                total_chunks  += n
                elapsed = time.time() - start
                rate    = total_chunks / elapsed if elapsed > 0 else 0
                print(f"[{i+1}/{len(all_pdfs)}] +{n:3d} chunks | {pdf.name[:60]} | Total={total_chunks} | {rate:.1f} ch/s")
            else:
                # PDF vide ou non lisible
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"[ERR] {pdf.name[:60]}: {e}")

        # Flush toutes les 50 docs
        if (i + 1) % 50 == 0:
            conn = sqlite3.connect(DB_PATH)
            cur_chunks = conn.execute("SELECT count(*) FROM law_chunks").fetchone()[0]
            conn.close()
            print(f"\n  === Progress: {i+1}/{len(all_pdfs)} PDFs — {cur_chunks} chunks total — {errors} erreurs ===\n")

    # Stats finales
    conn = sqlite3.connect(DB_PATH)
    final_chunks = conn.execute("SELECT count(*) FROM law_chunks").fetchone()[0]
    final_docs   = conn.execute("SELECT count(*) FROM law_docs").fetchone()[0]
    conn.close()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"INDEXATION TERMINÉE en {elapsed:.1f}s")
    print(f"Documents indexés : {total_indexed} nouveaux ({skipped} ignorés, {errors} erreurs)")
    print(f"Base finale : {final_chunks} chunks dans {final_docs} documents")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
