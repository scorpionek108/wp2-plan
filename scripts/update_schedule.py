#!/usr/bin/env python3
"""
update_schedule.py
Skrypt automatycznie pobiera plan zajęć dla kierunku Wzornictwo Przemysłowe (2. rok)
ze strony Wydziału Mechanicznego Politechniki Lubelskiej (wm.pollub.pl),
parsuje zawartość PDF do pliku schedule.json, a pobrany plik PDF natychmiast usuwa.
"""

import os
import sys
import re
import json
import tempfile
import argparse
import hashlib
from datetime import datetime
import requests
from bs4 import BeautifulSoup

SCHEDULE_PAGE_URL = "https://wm.pollub.pl/plany-zajec"
EXACT_PDF_URL = "https://wm.pollub.pl/download/BPRE9FhwKMRsKEFpSUARTAX93R3cZUSZQW1kGNQgcJRFsc3QRfFEIET8uBhcMNxtRQw1pdFd5FwM1Ul1pHTV1T2MHZmBkH3IeFwc1KEFOWiwXRgJFIjEBPFodElxUU1Z9dQUgQTM_Mmw5F1pZcnZBWFoeF0cSXiQvKjxRUW4XCQJWfXUGJEEgOCVWcklaBSIrDQBaRFBFAEMjY093Uxo4UEtqWyElGitWNSU1b39GJEwgKD9bHA0BVhNeOzUcOlsvewEIByh-ZkYdHGdlGhxyX1oFOSgGVkJKBUVQaHkeBzpeLC5cVVcrY2FYcwR4ISJVcl9aDzEqBFZCSgJZQ0o/wp1_2_rok_zima_26-27.pdf"
OUTPUT_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schedule.json"))

# Domyślne nagłówki udające nowoczesną przeglądarkę
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}

DAYS_MAP = {
    "poniedziałek": "Poniedziałek",
    "poniedzialek": "Poniedziałek",
    "wtorek": "Wtorek",
    "środa": "Środa",
    "sroda": "Środa",
    "czwartek": "Czwartek",
    "piątek": "Piątek",
    "piatek": "Piątek",
    "sobota": "Sobota",
    "niedziela": "Niedziela"
}


def find_pdf_url() -> str:
    """
    Automatycznie przeszukuje stronę wydziału w poszukiwaniu najnowszego planu dla Wzornictwa 2. rok.
    Dzięki temu wykrywa nowe pliki wrzucone przez dziekanat w trakcie semestru.
    """
    scan_urls = [
        "https://wm.pollub.pl/plany-zajec",
        "https://wm.pollub.pl/studenci/plany-zajec"
    ]
    
    for page_url in scan_urls:
        print(f"[*] Przeszukiwanie strony wydziałowej: {page_url}")
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    text = a.get_text(strip=True).lower()
                    if not href.lower().endswith(".pdf") and "/download/" not in href.lower():
                        continue
                    
                    full_url = href if href.startswith("http") else requests.compat.urljoin(page_url, href)
                    
                    # Wzornictwo przemysłowe + 2 rok
                    is_wp = "wp" in href.lower() or "wzornictw" in href.lower() or "wzornictw" in text
                    is_year_2 = ("2_rok" in href.lower() or "rok_2" in href.lower() or 
                                 "wp1_2" in href.lower() or "2 rok" in text or "ii rok" in text or "rok ii" in text)
                    
                    if is_wp and is_year_2:
                        print(f"[+] WYKRYTO AKTUALNY PLAN NA STRONIE UCZELNI: {full_url}")
                        return full_url
        except Exception as e:
            print(f"[-] Błąd podczas skanowania {page_url}: {e}")

    # Jeśli strona wydziału chwilowo nie odpowiada, użyj znanego bezpośredniego adresu
    if EXACT_PDF_URL:
        print(f"[+] Używanie bezpośredniego adresu awaryjnego: {EXACT_PDF_URL}")
        return EXACT_PDF_URL

    return ""


def download_and_parse_pdf(pdf_url: str, local_file: str = None) -> list:
    """
    Pobiera PDF, przetwarza go i usuwa plik tymczasowy.
    Zwraca listę zajęć.
    """
    temp_pdf_path = None
    try:
        if local_file and os.path.exists(local_file):
            print(f"[*] Korzystanie z lokalnego pliku: {local_file}")
            pdf_path_to_read = local_file
        else:
            print(f"[*] Pobieranie pliku PDF z: {pdf_url}")
            resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            
            # Bezpieczny plik tymczasowy
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                tf.write(resp.content)
                temp_pdf_path = tf.name
            pdf_path_to_read = temp_pdf_path
            print(f"[+] Zapisano do pamięci tymczasowej ({os.path.getsize(temp_pdf_path)} bajtów)")

        classes = extract_classes_from_pdf(pdf_path_to_read)
        return classes

    finally:
        # Gwarancja usunięcia pliku PDF zgodnie z życzeniem
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"[+] Plik PDF został pomyślnie usunięty z dysku.")
            except Exception as e:
                print(f"[-] Błąd podczas usuwania pliku tymczasowego: {e}")


def extract_classes_from_pdf(pdf_path: str) -> list:
    """Wyciąga strukturę zajęć z pliku PDF za pomocą pdfplumber lub pypdf."""
    lessons = []
    text_content = ""
    
    # 1. Próba użycia pdfplumber (najlepsze do tabel)
    try:
        import pdfplumber
        print("[*] Parsowanie z użyciem pdfplumber...")
        with pdfplumber.open(pdf_path) as pdf:
            current_day = "Poniedziałek"
            item_id = 1
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            parsed_row = parse_table_row(row, current_day, item_id)
                            if parsed_row:
                                lessons.append(parsed_row)
                                item_id += 1
                text = page.extract_text() or ""
                text_content += "\n" + text
    except ImportError:
        print("[!] Brak pdfplumber, próba z pypdf...")
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                text_content += "\n" + (page.extract_text() or "")
        except ImportError:
            print("[-] Brak bibliotek pdfplumber i pypdf. Zainstaluj requirements.txt!")

    # Jeśli z tabel nic nie wpadło, spróbuj parsowania tekstu wyrażeniami regularnymi
    if not lessons and text_content:
        lessons = parse_text_lines(text_content)

    return lessons


def parse_table_row(row: list, default_day: str, item_id: int):
    """Pomocniczy parser wiersza tabeli planu."""
    if not row or not any(row):
        return None
    cleaned = [str(c).strip().replace("\n", " ") for c in row if c is not None]
    row_text = " ".join(cleaned)
    
    # Wykrywanie godzin np. 08:00 - 09:30 lub 8.00 - 9.30
    time_match = re.search(r'(\d{1,2}[:.]\d{2})\s*[-–—]\s*(\d{1,2}[:.]\d{2})', row_text)
    if not time_match:
        return None
    
    start_time = time_match.group(1).replace(".", ":").zfill(5)
    end_time = time_match.group(2).replace(".", ":").zfill(5)
    
    # Sprawdź czy w wierszu jest nazwa dnia
    day = default_day
    for d_key, d_val in DAYS_MAP.items():
        if re.search(rf'\b{d_key}\b', row_text, re.I):
            day = d_val
            break

    # Wykrycie sali
    room_match = re.search(r'(sala\s*[0-9A-Za-z/]+|lab[a-z.]*\s*[0-9A-Za-z/]+|aula\s*[A-Za-z0-9]+|pracownia[^\s,]*)', row_text, re.I)
    room = room_match.group(1) if room_match else "Sala dydaktyczna"

    # Wykrycie typu
    type_str = "project"
    if re.search(r'\b(wykład|wykl|w)\b', row_text, re.I):
        type_str = "lecture"
    elif re.search(r'\b(lab|laboratorium|l)\b', row_text, re.I):
        type_str = "lab"
    elif re.search(r'\b(studio|pracownia|rys)\b', row_text, re.I):
        type_str = "studio"
    elif re.search(r'\b(seminarium|sem|ćw|cwiczenia)\b', row_text, re.I):
        type_str = "seminar"

    # Tydzień A / B / Parzysty / Nieparzysty
    week = "all"
    if re.search(r'\b(tydz[.]?\s*A|tydzień\s*A|A|nieparz[a-z.]*)\b', row_text, re.I):
        week = "A"
    elif re.search(r'\b(tydz[.]?\s*B|tydzień\s*B|B|parz[a-z.]*)\b', row_text, re.I):
        week = "B"

    # Grupa 1 / 2
    group = "all"
    if re.search(r'\b(gr[.]?\s*1|grupa\s*1)\b', row_text, re.I):
        group = "1"
    elif re.search(r'\b(gr[.]?\s*2|grupa\s*2)\b', row_text, re.I):
        group = "2"

    # Nazwa przedmiotu (usuwamy godziny i salę z tekstu)
    name = row_text
    name = re.sub(r'\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2}', '', name)
    name = re.sub(r'sala\s*[0-9A-Za-z/]+', '', name, flags=re.I)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > 60:
        name = name[:57] + "..."

    return {
        "id": item_id,
        "name": name or "Zajęcia specjalistyczne",
        "type": type_str,
        "day": day,
        "start": start_time,
        "end": end_time,
        "room": room,
        "teacher": "Prowadzący (wg planu)",
        "week": week,
        "group": group,
        "description": "Zajęcia kierunkowe - Wzornictwo Przemysłowe 2. rok",
        "note": "Sprawdź wymagane materiały i narzędzia przed zajęciami.",
        "status": "upcoming"
    }


def parse_text_lines(text: str) -> list:
    """Fallbackowy parser analizujący linie tekstu."""
    items = []
    current_day = "Poniedziałek"
    item_id = 1
    
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
            
        # Zmiana dnia
        for d_key, d_val in DAYS_MAP.items():
            if line.lower().startswith(d_key):
                current_day = d_val
                break
                
        time_match = re.search(r'(\d{1,2}[:.]\d{2})\s*[-–—]\s*(\d{1,2}[:.]\d{2})', line)
        if time_match:
            start_t = time_match.group(1).replace(".", ":").zfill(5)
            end_t = time_match.group(2).replace(".", ":").zfill(5)
            subject = line.replace(time_match.group(0), "").strip()
            
            items.append({
                "id": item_id,
                "name": subject[:40] if subject else "Zajęcia projektowe",
                "type": "project",
                "day": current_day,
                "start": start_t,
                "end": end_t,
                "room": "Politechnika Lubelska",
                "teacher": "Prowadzący katedry",
                "week": "all",
                "group": "all",
                "description": subject,
                "note": "Szczegóły w karcie przedmiotu.",
                "status": "upcoming"
            })
            item_id += 1
            
    return items


def main():
    parser = argparse.ArgumentParser(description="Synchronizacja planu zajęć Politechniki Lubelskiej WP2")
    parser.add_argument("--url", help="Bezpośredni link URL do pliku PDF")
    parser.add_argument("--file", help="Lokalna ścieżka do pobranego wcześniej pliku PDF")
    args = parser.parse_args()

    print("=" * 60)
    print("  WP2 Plan - Auto Synchronizacja Planu Politechniki")
    print(f"  Czas uruchomienia: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    pdf_url = args.url or find_pdf_url()
    lessons = download_and_parse_pdf(pdf_url, local_file=args.file)

    if not lessons:
        print("[!] Nie udało się wyodrębnić nowych zajęć lub plan nie uległ zmianie.")
        print("[*] Zachowywanie istniejącego schedule.json.")
        return

    # Przygotowanie struktury docelowej
    output_data = {
        "metadata": {
            "faculty": "Wydział Mechaniczny Politechniki Lubelskiej",
            "field": "Wzornictwo Przemysłowe",
            "year": 2,
            "semester": "Zimowy 2026/2027",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_url": pdf_url or "https://wm.pollub.pl/plany-zajec",
            "items_count": len(lessons)
        },
        "schedule": lessons
    }

    # Zapis do schedule.json
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] Zaktualizowano {OUTPUT_JSON_PATH} (zajęć: {len(lessons)})")
    print("=" * 60)


if __name__ == "__main__":
    main()

