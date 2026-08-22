/* ============================================================
   Main Event Card Vault — rating renderers
   Drop into build/template.html inside the existing <script>.

   CONTRACT: these functions render values supplied by the research packet.
   They never compute, derive, average, round-to-taste or infer a rating,
   a value, a label or a publication decision. A null renders as nothing,
   never as zero. If publish_ready is not true, nothing scored is drawn.
   ============================================================ */

var RATINGS = window.MECV_RATINGS || { cards: {}, packet_date: null };

function rateStep(score) {              // maps 0-100 onto the validated 4-step ramp
  if (score == null) return "s1";
  if (score >= 80) return "s4";
  if (score >= 60) return "s3";
  if (score >= 40) return "s2";
  return "s1";
}

function money0(n) {
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function money2(n) {
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function meter(score, extraClass) {
  if (score == null) return "";
  return '<span class="meter ' + rateStep(score) + (extraClass ? " " + extraClass : "") +
         '"><i style="width:' + Math.max(0, Math.min(100, score)) + '%"></i></span>';
}

var POSITION_TEXT = {
  below_estimated_market: "Below estimated market",
  within_estimated_market: "Within estimated market",
  above_estimated_market: "Above estimated market",
  insufficient_evidence: "Insufficient evidence"
};

var CONF_TEXT = {
  high: "High", medium: "Medium", low: "Low", insufficient_evidence: "Insufficient evidence"
};

/* ---------- the compact strip on a grid tile ---------- */

function rateStrip(card) {
  var r = RATINGS.cards[card.uid];
  if (!r || r.publish_ready !== true || r.main_event_rating == null) {
    return '<div class="rate-strip none">Not yet rated</div>';
  }
  var chg = r.weekly_change_points;
  var trend = "";
  if (chg != null && chg !== 0) {
    trend = '<span class="trend ' + (chg > 0 ? "up" : "down") + '">' + Math.abs(chg) + "</span>";
  }
  return '<div class="rate-strip">' +
      '<span class="mer">' + r.main_event_rating + '<small>/100</small></span>' +
      meter(r.main_event_rating) +
      trend +
      '<span class="conf-dot ' + (r.confidence_label || "") + '" role="img" aria-label="Confidence: ' +
        (CONF_TEXT[r.confidence_label] || "unknown") + '" title="Confidence: ' +
        (CONF_TEXT[r.confidence_label] || "unknown") + '"></span>' +
    "</div>";
}

/* ---------- the vault value range bar ---------- */

function vaultValueBar(r, askingPrice) {
  if (r.vault_value_low == null || r.vault_value_high == null) return "";

  var lo = r.vault_value_low, hi = r.vault_value_high, mid = r.vault_value_mid;
  var pts = [lo, hi];
  if (askingPrice != null) pts.push(askingPrice);
  var axMin = Math.min.apply(null, pts), axMax = Math.max.apply(null, pts);
  var pad = (axMax - axMin) * 0.18 || axMax * 0.1 || 1;
  axMin -= pad; axMax += pad;

  function pct(v) { return ((v - axMin) / (axMax - axMin)) * 100; }

  var bandL = pct(lo), bandR = pct(hi);
  var youPct = askingPrice != null ? pct(askingPrice) : null;

  // The range labels own the first line and the price label owns the second,
  // so the two can never collide however the price falls against the band.
  var html =
    '<div class="vv">' +
      '<div class="vv-head"><span>Vault Value</span>' +
        (r.market_position && r.market_position !== "insufficient_evidence"
          ? '<span class="pos">' + POSITION_TEXT[r.market_position] + "</span>" : "") +
      "</div>" +
      '<div class="vv-track">' +
        '<span class="vv-band" style="left:' + bandL + '%;right:' + (100 - bandR) + '%"></span>' +
        (mid != null ? '<span class="vv-mid" style="left:' + pct(mid) + '%"></span>' : "") +
        (youPct != null ? '<span class="vv-you" style="left:' + youPct + '%"></span>' : "") +
        '<span class="vv-lab" style="left:' + bandL + '%">' + money0(lo) + "</span>" +
        '<span class="vv-lab hi" style="left:' + bandR + '%">' + money0(hi) + "</span>" +
        (youPct != null
          ? '<span class="vv-lab you' + (youPct > 78 ? " hi" : youPct < 22 ? "" : " mid-anchor") +
              '" style="left:' + Math.max(0, Math.min(100, youPct)) + '%;top:' +
              40 + 'px">Your price ' + money2(askingPrice) + "</span>"
          : "") +
      "</div>" +
    "</div>";
  return html;
}

/* ---------- the full panel in the lightbox ---------- */

function ratePanel(card) {
  var r = RATINGS.cards[card.uid];

  if (!r || r.publish_ready !== true) {
    return '<div class="rate-panel pending">' +
        '<div class="eyebrow">Main Event Rating</div>' +
        "<p>Rating research in progress. This card does not yet have enough verified " +
        "comparable sales to publish a rating we would stand behind.</p>" +
      "</div>";
  }

  var rows = [
    ["Market Health", r.market_health, r.market_health_label],
    ["Upside Potential", r.upside_potential, r.upside_potential_label],
    ["Confidence", r.confidence, CONF_TEXT[r.confidence_label]]
  ].filter(function (x) { return x[1] != null; });

  var foot = [];
  if (r.weekly_change_note) foot.push('<span class="chg">' + esc(r.weekly_change_note) + "</span>");
  else if (r.weekly_change_points != null && r.weekly_change_points !== 0) {
    foot.push('<span class="chg">' + (r.weekly_change_points > 0 ? "+" : "") +
      r.weekly_change_points + " points this week</span>");
  } else foot.push('<span class="chg">No meaningful change this week</span>');
  if (r.market_temperature) foot.push("<span>Market: " + esc(r.market_temperature) + "</span>");
  if (r.updated_at) foot.push("<span>Last researched " + prettyDate(r.updated_at) + "</span>");

  var drivers = (r.drivers || []).map(function (d) { return "<li>" + esc(d) + "</li>"; });
  var risks   = (r.risks   || []).map(function (d) { return '<li class="risk">' + esc(d) + "</li>"; });

  return '<div class="rate-panel" data-conf="' + (r.confidence_label || "") + '">' +
      '<div class="eyebrow">Main Event Rating</div>' +
      '<div class="rate-hero">' +
        "<b>" + r.main_event_rating + "</b><span class='of'>/100</span>" +
        (r.main_event_rating_label
          ? '<span class="word">' + esc(r.main_event_rating_label) + "</span>" : "") +
      "</div>" +
      meter(r.main_event_rating) +
      vaultValueBar(r, r.asking_price) +
      '<div class="rate-rows">' +
        rows.map(function (row) {
          return '<div class="rate-row">' +
              '<span class="k">' + row[0] + "</span>" +
              '<span class="v">' + row[1] +
                (row[2] ? " <small>" + esc(String(row[2])) + "</small>" : "") + "</span>" +
              meter(row[1]) +
            "</div>";
        }).join("") +
      "</div>" +
      '<div class="rate-foot">' + foot.join('&nbsp;<span class="sep">|</span> ') + "</div>" +
      (drivers.length || risks.length
        ? '<div class="rate-why"><h4>Rating factors</h4><ul>' +
            drivers.join("") + risks.join("") + "</ul></div>"
        : "") +
      '<div class="rate-note">Main Event Card Vault estimates are based on available market ' +
        "information and comparable cards. Main Event Card Vault may own or offer this card for " +
        'sale. Collectible prices can change, and ratings do not guarantee future value. ' +
        '<a href="/ratings.html">How this rating works</a>.</div>' +
    "</div>";
}

function prettyDate(iso) {
  var M = ["January","February","March","April","May","June",
           "July","August","September","October","November","December"];
  var p = String(iso).split("-");
  if (p.length !== 3) return iso;
  return M[+p[1] - 1] + " " + (+p[2]) + ", " + p[0];
}
