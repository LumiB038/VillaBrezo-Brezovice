import os
import hmac
from datetime import date
from functools import wraps
from flask import (Flask, send_from_directory, request, jsonify,
                   session, redirect, render_template)
from database import krijo_tabelat, lidhu

SITE = next(root for root, _, files in os.walk("Site") if "main.html" in files)

app = Flask(__name__, static_folder=SITE, static_url_path="")

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