(function () {
  "use strict";

  var API_URL = "/api/recommend";
  var BOOKING_URL = "rezervo.html";
  var EURO = "\u20AC";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function todayISO() {
    var d = new Date();
    var month = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + month + "-" + day;
  }

  function makeField(labelText, input) {
    var wrap = el("div", "vb-field");
    var label = el("label", null, labelText);
    wrap.appendChild(label);
    wrap.appendChild(input);
    return wrap;
  }

  function makeInput(type, value, min) {
    var input = document.createElement("input");
    input.type = type;
    if (value !== undefined) input.value = value;
    if (min !== undefined) input.min = min;
    return input;
  }

  // ---------- Ndertimi i dritares ----------
  var toggleBtn = el("button", "vb-chat-toggle");
  toggleBtn.type = "button";
  toggleBtn.setAttribute("aria-label", "Hap asistentin");
  toggleBtn.innerHTML = '<i class="fa fa-comments"></i>';

  var panel = el("div", "vb-chat");
  var header = el("div", "vb-chat-header");
  header.appendChild(el("span", null, "Asistenti i Villa Brezo"));
  var closeBtn = el("button", "vb-chat-close", "\u00D7");
  closeBtn.type = "button";
  closeBtn.setAttribute("aria-label", "Mbyll");
  header.appendChild(closeBtn);

  var messages = el("div", "vb-chat-messages");

  var form = el("form", "vb-chat-form");
  var adultsInput = makeInput("number", "2", "1");
  var childrenInput = makeInput("number", "0", "0");
  var checkInInput = makeInput("date", undefined, todayISO());
  var checkOutInput = makeInput("date", undefined, todayISO());
  var submitBtn = el("button", "vb-submit", "Rekomando paketa");
  submitBtn.type = "submit";

  form.appendChild(makeField("Te rritur", adultsInput));
  form.appendChild(makeField("Femije", childrenInput));
  form.appendChild(makeField("Hyrja (opsionale)", checkInInput));
  form.appendChild(makeField("Dalja (opsionale)", checkOutInput));
  form.appendChild(submitBtn);

  panel.appendChild(header);
  panel.appendChild(messages);
  panel.appendChild(form);
  document.body.appendChild(toggleBtn);
  document.body.appendChild(panel);

  // ---------- Funksione ndihmese ----------
  function scrollDown() {
    messages.scrollTop = messages.scrollHeight;
  }

  function addMessage(text, who) {
    var cls = who === "user" ? "vb-msg vb-msg-user" : "vb-msg vb-msg-bot";
    messages.appendChild(el("div", cls, text));
    scrollDown();
  }

  function buildBookingUrl(rec, ctx) {
    var params = new URLSearchParams();
    if (rec.room_id) params.set("room", rec.room_id);
    params.set("persona", ctx.adults + ctx.children);
    if (ctx.checkIn && ctx.checkOut) {
      params.set("check_in", ctx.checkIn);
      params.set("check_out", ctx.checkOut);
    }
    params.set("package", rec.title);
    return BOOKING_URL + "?" + params.toString();
  }

  function addCard(rec, ctx) {
    var card = el("div", "vb-card");
    card.appendChild(el("h4", null, rec.title));
    if (rec.description) card.appendChild(el("p", null, rec.description));
    card.appendChild(el("p", null, rec.reason));
    card.appendChild(
      el("p", "vb-price", rec.price_per_night + EURO + " / nate")
    );
    if (rec.nights !== undefined) {
      card.appendChild(
        el("p", null, rec.nights + " net, totali: " + rec.total_price + EURO)
      );
    }
    var link = el("a", "vb-book", "Rezervo");
    link.href = buildBookingUrl(rec, ctx);
    card.appendChild(link);
    messages.appendChild(card);
    scrollDown();
  }

  // Karta kur dhoma eshte e zene dhe boti sugjeron data te reja
  function addSuggestion(s, ctx) {
    var card = el("div", "vb-card");
    if (s.total_price !== undefined) {
      card.appendChild(
        el("p", null, s.nights + " net, totali: " + s.total_price + EURO)
      );
    }

    var yes = el("a", "vb-book", "Po, rezervo");
    yes.href = buildBookingUrl(
      { room_id: s.room_id, title: s.package },
      {
        adults: ctx.adults,
        children: ctx.children,
        checkIn: s.check_in,
        checkOut: s.check_out
      }
    );

    var no = el("a", "vb-book", "Jo, faleminderit");
    no.href = "#";
    no.style.background = "#777";
    no.style.marginLeft = "6px";
    no.addEventListener("click", function (e) {
      e.preventDefault();
      addMessage("Ne rregull. Provoni data tjera dhe do t'ju rekomandoj paketat.", "bot");
    });

    card.appendChild(yes);
    card.appendChild(no);
    messages.appendChild(card);
    scrollDown();
  }

  var greeted = false;
  function openPanel() {
    panel.classList.add("vb-open");
    if (!greeted) {
      greeted = true;
      addMessage(
        "Pershendetje! Me trego sa te rritur dhe femije jeni (dhe datat, nese i dini), dhe do t'ju rekomandoj paketat qe jane aktive tani.",
        "bot"
      );
    }
  }

  toggleBtn.addEventListener("click", function () {
    if (panel.classList.contains("vb-open")) {
      panel.classList.remove("vb-open");
    } else {
      openPanel();
    }
  });
  closeBtn.addEventListener("click", function () {
    panel.classList.remove("vb-open");
  });

  // ---------- Dergimi i formes ----------
  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var adults = parseInt(adultsInput.value, 10);
    var children = parseInt(childrenInput.value, 10);
    var checkIn = checkInInput.value;
    var checkOut = checkOutInput.value;

    if (isNaN(adults) || adults < 1) {
      addMessage("Duhet te kete se paku 1 i rritur.", "bot");
      return;
    }
    if (isNaN(children) || children < 0) {
      addMessage("Numri i femijeve nuk eshte i sakte.", "bot");
      return;
    }
    if ((checkIn && !checkOut) || (!checkIn && checkOut)) {
      addMessage("Plotesoni edhe daten e hyrjes edhe te daljes, ose lini te dyja bosh.", "bot");
      return;
    }
    if (checkIn && checkOut && checkOut <= checkIn) {
      addMessage("Data e daljes duhet te jete pas dates se hyrjes.", "bot");
      return;
    }

    var summary = adults + " te rritur, " + children + " femije";
    if (checkIn && checkOut) summary += ", " + checkIn + " deri " + checkOut;
    addMessage(summary, "user");

    var ctx = {
      adults: adults,
      children: children,
      checkIn: checkIn,
      checkOut: checkOut
    };

    var params = new URLSearchParams({ adults: adults, children: children });
    if (checkIn && checkOut) {
      params.set("check_in", checkIn);
      params.set("check_out", checkOut);
    }

    submitBtn.disabled = true;
    fetch(API_URL + "?" + params.toString())
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        var data = result.data;
        if (!result.ok) {
          addMessage(data.mesazhi || "Ndodhi nje gabim. Provoni prape.", "bot");
          return;
        }
        addMessage(data.mesazhi, "bot");
        if (data.suggestion) addSuggestion(data.suggestion, ctx);
        (data.recommendations || []).forEach(function (rec) {
          addCard(rec, ctx);
        });
      })
      .catch(function () {
        addMessage("Nuk u lidha me serverin. Provoni prape pas pak.", "bot");
      })
      .finally(function () {
        submitBtn.disabled = false;
      });
  });
})();