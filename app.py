import os
import hmac
from datetime import date
from functools import wraps
from flask import (Flask, send_from_directory, request, jsonify,
                   session, redirect, render_template)
from database import krijo_tabelat, lidhu

SITE = next(root for root, _, files in os.walk("Site") if "main.html" in files)

app = Flask(__name__, static_folder=SITE, static_url_path="",
            template_folder=os.path.join(SITE, "Admins"))

# ---- NDRYSHOJI KËTO DY VLERA ----
app.secret_key = os.environ.get("SECRET_KEY", "ndrysho-kete-fjale-te-gjate-dhe-te-rastesishme")
ADMIN_FJALEKALIMI = os.environ.get("ADMIN_PASSWORD", "VillaBrezo2026!")
# ---------------------------------

krijo_tabelat()


def kerkon_hyrje(f):
    @wraps(f)
    def mbeshtjellesi(*args, **kwargs):
        if not session.get("admin"):
            if request.path.startswith("/api/"):
                return jsonify(mesazhi="Nuk keni leje."), 401
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return mbeshtjellesi


@app.route("/")
def home():
    return send_from_directory(SITE, "main.html")


# ---------- REZERVIMI I MYSAFIRIT ----------
@app.route("/api/rezervo", methods=["POST"])
def rezervo():
    d = request.get_json(silent=True) or {}

    try:
        dhoma_id = int(d.get("dhoma_id"))
        persona = int(d.get("persona"))
        emri = d.get("emri", "").strip()
        mbiemri = d.get("mbiemri", "").strip()
        email = d.get("email", "").strip()
        telefoni = d.get("telefoni", "").strip()
        kerkesat = d.get("kerkesat", "").strip()
        hyrja = date.fromisoformat(d.get("data_hyrjes", ""))
        dalja = date.fromisoformat(d.get("data_daljes", ""))
    except (TypeError, ValueError):
        return jsonify(mesazhi="Të dhënat nuk janë të plota ose janë të pasakta."), 400

    if not (emri and mbiemri and telefoni) or "@" not in email:
        return jsonify(mesazhi="Plotësoni saktë emrin, email-in dhe telefonin."), 400
    if hyrja < date.today() or dalja <= hyrja:
        return jsonify(mesazhi="Datat e zgjedhura nuk janë të vlefshme."), 400
    if persona < 1:
        return jsonify(mesazhi="Numri i personave duhet të jetë së paku 1."), 400

    conn = lidhu()
    dhoma = conn.execute("SELECT * FROM dhomat WHERE id = ?", (dhoma_id,)).fetchone()
    if not dhoma:
        conn.close()
        return jsonify(mesazhi="Dhoma nuk u gjet."), 400
    if persona > dhoma["kapaciteti"]:
        conn.close()
        return jsonify(mesazhi=f"Kjo dhomë pranon maksimumi {dhoma['kapaciteti']} persona."), 400

    zene = conn.execute("""
        SELECT 1 FROM rezervimet
        WHERE dhoma_id = ? AND statusi != 'anuluar'
          AND data_hyrjes < ? AND data_daljes > ?
    """, (dhoma_id, dalja.isoformat(), hyrja.isoformat())).fetchone()
    if zene:
        conn.close()
        return jsonify(mesazhi="Kjo dhomë është e zënë në datat e zgjedhura. Provoni data tjera."), 409

    net = (dalja - hyrja).days
    total = net * dhoma["cmimi"]

    conn.execute("""
        INSERT INTO rezervimet
        (dhoma_id, emri, mbiemri, email, telefoni, data_hyrjes, data_daljes,
         persona, kerkesat, cmimi_total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dhoma_id, emri, mbiemri, email, telefoni,
          hyrja.isoformat(), dalja.isoformat(), persona, kerkesat, total))
    conn.commit()
    conn.close()

    return jsonify(mesazhi=f"Rezervimi u dërgua me sukses! {net} net, totali: €{total:.0f}. Do t'ju kontaktojmë së shpejti."), 201


# ---------- BOTI: REKOMANDIMI I PAKETAVE ----------
def room_is_free(conn, room_id, check_in, check_out):
    """Kthen True nese dhoma nuk ka rezervim aktiv qe perplaset me keto data."""
    busy = conn.execute("""
        SELECT 1 FROM rezervimet
        WHERE dhoma_id = ? AND statusi != 'anuluar'
          AND data_hyrjes < ? AND data_daljes > ?
    """, (room_id, check_out, check_in)).fetchone()
    return busy is None


@app.route("/api/recommend")
def recommend():
    # HAPI 1: lexojme numrin e te rriturve dhe te femijeve
    try:
        adults = int(request.args.get("adults", 1))
        children = int(request.args.get("children", 0))
    except ValueError:
        return jsonify(mesazhi="Numri i te rriturve dhe i femijeve duhet te jete numer."), 400

    if adults < 1 or children < 0:
        return jsonify(mesazhi="Duhet te kete se paku 1 i rritur."), 400
    guests = adults + children

    # HAPI 2: lexojme datat (jane opsionale)
    check_in = request.args.get("check_in", "").strip()
    check_out = request.args.get("check_out", "").strip()
    nights = None
    reference_date = date.today()

    if check_in or check_out:
        try:
            hyrja = date.fromisoformat(check_in)
            dalja = date.fromisoformat(check_out)
        except ValueError:
            return jsonify(mesazhi="Datat nuk jane te sakta."), 400
        if dalja <= hyrja:
            return jsonify(mesazhi="Data e daljes duhet te jete pas dates se hyrjes."), 400
        nights = (dalja - hyrja).days
        reference_date = hyrja

    ref = reference_date.isoformat()

    # HAPI 3: marrim nga databaza paketat aktive qe e mbajne numrin e personave
    # dhe qe jane brenda periudhes (valid_from / valid_to), nese ato jane te mbushura
    conn = lidhu()
    packages = conn.execute("""
        SELECT * FROM packages
        WHERE is_active = 1
          AND max_guests >= ?
          AND (valid_from IS NULL OR valid_from = '' OR valid_from <= ?)
          AND (valid_to IS NULL OR valid_to = '' OR valid_to >= ?)
    """, (guests, ref, ref)).fetchall()

    # HAPI 4: nese nuk ka asnje pakete, themi pse (shume persona, ose jashte periudhes)
    if not packages:
        max_row = conn.execute(
            "SELECT MAX(max_guests) AS m FROM packages WHERE is_active = 1"
        ).fetchone()
        conn.close()
        max_cap = max_row["m"]
        if max_cap is None:
            msg = "Momentalisht nuk ka paketa aktive."
        elif guests > max_cap:
            msg = (f"Per {guests} persona nuk kemi paketa. Paketat tona pranojne "
                   f"deri ne {max_cap} persona. Na kontaktoni per grupe me te medha.")
        else:
            msg = "Nuk ka paketa aktive per kete periudhe."
        return jsonify(recommendations=[], mesazhi=msg)

    # HAPI 5: nese ka data, mbajme vetem paketat qe dhoma e tyre eshte e lire
    available = []
    for p in packages:
        if nights is not None and p["room_id"]:
            if not room_is_free(conn, p["room_id"], check_in, check_out):
                continue
        available.append(p)
    conn.close()

    if not available:
        return jsonify(recommendations=[],
                       mesazhi="Dhoma eshte e zene ne keto data. Provoni data tjera.")

    # HAPI 6: rendisim (familjare te para nese ka femije, pastaj me e afert me
    # numrin e personave, pastaj me e lira) dhe kthejme 3 te parat
    def sort_key(p):
        family_first = 0 if (children > 0 and p["is_family"]) else 1
        return (family_first, p["max_guests"] - guests, p["price_per_night"])

    available.sort(key=sort_key)

    results = []
    for p in available[:3]:
        if children > 0 and p["is_family"]:
            reason = f"Paketa familjare per {adults} te rritur dhe {children} femije."
        else:
            reason = f"Pershtatet per {guests} persona (deri ne {p['max_guests']})."
        item = {
            "id": p["id"],
            "title": p["title"],
            "description": p["description"],
            "price_per_night": p["price_per_night"],
            "room_id": p["room_id"],
            "reason": reason,
        }
        if nights is not None:
            item["nights"] = nights
            item["total_price"] = nights * p["price_per_night"]
        results.append(item)

    return jsonify(recommendations=results, mesazhi="Ja rekomandimet tona:")


# ---------- PANELI ADMIN ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    gabim = None
    if request.method == "POST":
        dhene = request.form.get("fjalekalimi", "")
        if hmac.compare_digest(dhene.encode(), ADMIN_FJALEKALIMI.encode()):
            session["admin"] = True
            return redirect("/admin")
        gabim = "Fjalëkalimi është i gabuar."
    return render_template("login.html", gabim=gabim)


@app.route("/admin/dil")
def admin_dil():
    session.clear()
    return redirect("/admin/login")


@app.route("/admin")
@kerkon_hyrje
def admin():
    return render_template("admin.html")


# READ
@app.route("/api/admin/rezervimet")
@kerkon_hyrje
def admin_rezervimet():
    conn = lidhu()
    rreshtat = conn.execute("""
        SELECT r.*, d.emri AS dhoma
        FROM rezervimet r JOIN dhomat d ON d.id = r.dhoma_id
        ORDER BY r.id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rreshtat])


# UPDATE (statusi)
@app.route("/api/admin/rezervimet/<int:rid>/statusi", methods=["POST"])
@kerkon_hyrje
def admin_statusi(rid):
    statusi = (request.get_json(silent=True) or {}).get("statusi")
    if statusi not in ("në pritje", "konfirmuar", "anuluar"):
        return jsonify(mesazhi="Status i pavlefshëm."), 400
    conn = lidhu()
    conn.execute("UPDATE rezervimet SET statusi = ? WHERE id = ?", (statusi, rid))
    conn.commit()
    conn.close()
    return jsonify(mesazhi="U ruajt.")


# UPDATE (datat dhe personat)
@app.route("/api/admin/rezervimet/<int:rid>", methods=["PUT"])
@kerkon_hyrje
def admin_edito(rid):
    d = request.get_json(silent=True) or {}
    try:
        persona = int(d.get("persona"))
        hyrja = date.fromisoformat(d.get("data_hyrjes", ""))
        dalja = date.fromisoformat(d.get("data_daljes", ""))
    except (TypeError, ValueError):
        return jsonify(mesazhi="Të dhënat janë të pasakta."), 400

    if dalja <= hyrja or persona < 1:
        return jsonify(mesazhi="Datat ose numri i personave nuk janë të vlefshëm."), 400

    conn = lidhu()
    r = conn.execute("SELECT * FROM rezervimet WHERE id = ?", (rid,)).fetchone()
    if not r:
        conn.close()
        return jsonify(mesazhi="Rezervimi nuk u gjet."), 404

    dhoma = conn.execute("SELECT * FROM dhomat WHERE id = ?", (r["dhoma_id"],)).fetchone()
    if persona > dhoma["kapaciteti"]:
        conn.close()
        return jsonify(mesazhi=f"Kjo dhomë pranon maksimumi {dhoma['kapaciteti']} persona."), 400

    zene = conn.execute("""
        SELECT 1 FROM rezervimet
        WHERE dhoma_id = ? AND statusi != 'anuluar' AND id != ?
          AND data_hyrjes < ? AND data_daljes > ?
    """, (r["dhoma_id"], rid, dalja.isoformat(), hyrja.isoformat())).fetchone()
    if zene:
        conn.close()
        return jsonify(mesazhi="Dhoma është e zënë në këto data."), 409

    total = (dalja - hyrja).days * dhoma["cmimi"]
    conn.execute("""
        UPDATE rezervimet
        SET data_hyrjes = ?, data_daljes = ?, persona = ?, cmimi_total = ?
        WHERE id = ?
    """, (hyrja.isoformat(), dalja.isoformat(), persona, total, rid))
    conn.commit()
    conn.close()
    return jsonify(mesazhi="U ndryshua.")


# DELETE
@app.route("/api/admin/rezervimet/<int:rid>", methods=["DELETE"])
@kerkon_hyrje
def admin_fshij(rid):
    conn = lidhu()
    conn.execute("DELETE FROM rezervimet WHERE id = ?", (rid,))
    conn.commit()
    conn.close()
    return jsonify(mesazhi="U fshi.")


if __name__ == "__main__":
    app.run(debug=True)