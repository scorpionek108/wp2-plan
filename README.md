# 📐 WP2 Plan • Wzornictwo Przemysłowe (Politechnika Lubelska)

Mobilna aplikacja internetowa (PWA) z planem zajęć dla studentów 2. roku Wzornictwa Przemysłowego na Politechnice Lubelskiej.

Aplikacja **automatycznie aktualizuje plan zajęć ze strony wydziałowej** za pomocą wbudowanego darmowego automatu w chmurze (GitHub Actions), nie wymagając żadnych płatnych serwerów.

---

## 🚀 Jak to działa?

```
┌───────────────────────────────────────┐
│ Strona uczelni (wm.pollub.pl)         │
└──────────────────┬────────────────────┘
                   │
                   ▼ (1. Raz dziennie robot sprawdza plan)
┌───────────────────────────────────────┐
│ GitHub Actions (darmowy automat)      │
│ ├─ Pobiera PDF do pamięci             │
│ ├─ Parsuje zajęcia, godziny, sale     │
│ ├─ KASUJE plik PDF z dysku            │
│ └─ Zapisuje dane do "schedule.json"   │
└──────────────────┬────────────────────┘
                   │
                   ▼ (2. Udostępnia przez GitHub Pages)
┌───────────────────────────────────────┐
│ Aplikacja w telefonie (PWA)           │
│ ├─ Pobiera "schedule.json"            │
│ ├─ Filtruje Tydzień A/B i Twoją grupę │
│ └─ Działa w 100% offline bez internetu│
└───────────────────────────────────────┘
```

---

## 📱 Jak zainstalować na telefonie?

Gdy projekt jest opublikowany na darmowym **GitHub Pages** (lub dowolnym hostingu):

### Na telefonie z Androidem (Google Chrome / Brave):
1. Otwórz link do aplikacji w przeglądarce.
2. Kliknij wyskakujący komunikat **„Dodaj do ekranu głównego”** lub menu z trzema kropkami `⋮` ➔ **„Zainstaluj aplikację”**.
3. Aplikacja pojawi się w Twoim menu z własną ikoną i będzie otwierać się na pełnym ekranie (bez pasków przeglądarki).

### Na telefonie iPhone (Safari):
1. Otwórz link w przeglądarce **Safari**.
2. Kliknij ikonę udostępniania na dole (kwadrat ze strzałką w górę).
3. Wybierz opcję **„Do ekranu początkowego”** (Add to Home Screen).

---

## 🛠️ Jak uruchomić to w chmurze za darmo (Krok po kroku)

### Krok 1: Wrzucenie repozytorium na GitHub
1. Utwórz nowe repozytorium na [github.com](https://github.com) (np. o nazwie `wp2-plan`).
2. Wypchnij pliki z tego folderu do repozytorium:
   ```bash
   git init
   git add .
   git commit -m "Inicjalizacja aplikacji WP2 Plan"
   git branch -M main
   git remote add origin https://github.com/<twoj-login>/wp2-plan.git
   git push -u origin main
   ```

### Krok 2: Włączenie darmowego hostingu (GitHub Pages)
1. W ustawieniach repozytorium na GitHubie wejdź w zakładkę **Settings** ➔ **Pages**.
2. W sekcji **Build and deployment** wybierz `Branch: main`, folder `/ (root)` i kliknij **Save**.
3. Po minucie otrzymasz publiczny link: `https://<twoj-login>.github.io/wp2-plan/`.

### Krok 3: Włączenie uprawnień do automatycznej aktualizacji
1. W repozytorium wejdź w **Settings** ➔ **Actions** ➔ **General**.
2. Na samym dole w sekcji **Workflow permissions** zaznacz **„Read and write permissions”** i kliknij **Save**.
   *(Dzięki temu automat będzie mógł aktualizować plik `schedule.json` po zmianach na uczelni).*

Gotowe! Automat w `.github/workflows/update_plan.yml` będzie sam sprawdzał plany codziennie w nocy. Możesz go też wywołać w dowolnej chwili ręcznie w zakładce **Actions** ➔ **Run workflow**.

---

## 📂 Struktura plików

* [`index.html`](index.html) – interfejs aplikacji (PWA) z filtrowaniem tygodni A/B i grup oraz obsługą trybu offline.
* [`schedule.json`](schedule.json) – lekki plik z aktualnym planem zajęć w formacie JSON.
* [`sw.js`](sw.js) – Service Worker odpowiadający za działanie aplikacji offline.
* [`manifest.json`](manifest.json) – manifest aplikacji PWA (nazwa, kolory, ikona).
* [`icons/icon.svg`](icons/icon.svg) – wektorowa ikona aplikacji wzornictwa przemysłowego.
* [`scripts/update_schedule.py`](scripts/update_schedule.py) – skrypt w Pythonie pobierający PDF, parsujący tabelę i usuwający PDF.
* [`.github/workflows/update_plan.yml`](.github/workflows/update_plan.yml) – harmonogram automatycznego uruchamiania skryptu na darmowym serwerze GitHub Actions.
