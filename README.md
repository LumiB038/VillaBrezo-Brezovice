# Villa Brezo - Brezovice

Faqe interneti per Villa Brezo me sistem rezervimi, panel admini dhe asistent
qe rekomandon paketat aktive.

## Teknologjite
Python (Flask), SQLite, HTML, CSS, JavaScript.

## Si nisesh projektin
1. `python -m venv venv` dhe aktivizoje (`venv\Scripts\Activate.ps1`)
2. `pip install flask`
3. `python app.py`
4. Hap `http://127.0.0.1:5000`

Admin paneli: `http://127.0.0.1:5000/admin/login`
Fjalekalimi merret nga variabla `ADMIN_PASSWORD`.

## Publikimi ne Vercel
Projekti ka konfigurimin `vercel.json`, hyrjen `api/index.py` dhe varesine
`requirements.txt`. Importoje repository-n ne Vercel dhe vendos variablat
`SECRET_KEY` dhe `ADMIN_PASSWORD` te Project Settings > Environment Variables.

SQLite nuk eshte databaze e perhershme ne Vercel Serverless. Per testim te
faqes mund te publikohet, por per rezervime reale perdor nje databaze te
jashtme dhe lidhjen e saj me API-te.

## Funksionalitetet
- **Rezervimi:** forma ne `rezervo.html` dergon te dhenat ne `/api/rezervo`. Serveri
  kontrollon datat, kapacitetin dhe nese dhoma eshte e zene.
- **Admini:** shikon, konfirmon, anulon, edito dhe fshin rezervimet.
- **Asistenti (bot):** `chatbot.js` therret `/api/recommend` me numrin e personave
  dhe datat. Serveri kthen paketat aktive qe i pershtaten, me paketat familjare
  te para nese ka femije, dhe heq ato qe dhoma e tyre eshte e zene.

## Struktura
- `app.py` - serveri dhe API-te
- `database.py` - tabelat SQLite
- `Site/Website` - faqet, CSS, JS dhe faqet e adminit (`Admins`)
