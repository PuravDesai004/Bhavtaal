/* Crisp 9:16 thermal receipt image, drawn with the browser canvas API only. */
(function () {
  function money(value) {
    return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(Math.abs(Number(value || 0)));
  }
  function draw(deal) {
    const walkedOut = deal.status === "walked_out";
    const upward = deal.direction === "upward";
    const gain = Number(deal.savings_or_gain ?? 0);
    const penalty = !walkedOut && gain < 0;
    const neutral = !walkedOut && gain === 0;
    const canvas = document.createElement("canvas");
    canvas.width = 1080; canvas.height = 1920;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#FAF6EE"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (let y = 0; y < canvas.height; y += 16) for (let x = 0; x < canvas.width; x += 16) {
      ctx.fillStyle = "rgba(24,24,27,.035)"; ctx.fillRect(x + ((x + y) % 3), y, 2, 2);
    }
    const x = 92, y = 80, w = 896, h = 1760;
    ctx.fillStyle = "#18181B"; ctx.fillRect(x + 9, y + 10, w, h);
    ctx.fillStyle = "#FFFFFF"; ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = "#18181B"; ctx.lineWidth = 6; ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = "#FAF6EE";
    for (let px = x + 10; px < x + w; px += 30) {
      ctx.beginPath(); ctx.arc(px, y, 10, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(px, y + h, 10, 0, Math.PI * 2); ctx.fill();
    }
    const center = (text, yy, font, color = "#18181B") => {
      ctx.fillStyle = color; ctx.font = font; ctx.textAlign = "center"; ctx.fillText(text, 540, yy, 800);
    };
    const rule = (yy) => { ctx.save(); ctx.setLineDash([10, 11]); ctx.strokeStyle = "#8B857B"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(145, yy); ctx.lineTo(935, yy); ctx.stroke(); ctx.restore(); };
    center("MolBhaav", 205, "700 62px 'Space Grotesk', sans-serif");
    center(walkedOut ? "STREET SMART · WALKOUT RECEIPT" : "STREET SMART · DEAL RECEIPT", 260, "600 23px 'JetBrains Mono', monospace", "#706C64");
    rule(305);
    center(`${deal.arena_label || "BAZAAR"}  ·  ${deal.date_ist || "TODAY"}`, 365, "600 24px 'JetBrains Mono', monospace");
    center(deal.boss?.boss_name || "Your Opponent", 445, "700 48px 'Space Grotesk', sans-serif");
    center(deal.boss?.item || "Negotiated deal", 492, "500 25px 'Plus Jakarta Sans', sans-serif", "#706C64");
    rule(545);
    center(upward ? "OPENING OFFER" : "OPENING ASK", 625, "600 23px 'JetBrains Mono', monospace", "#706C64");
    center(`₹${money(deal.starting_price)}`, 710, "700 65px 'JetBrains Mono', monospace");
    const arrowLabel = walkedOut
      ? "✕  SHUTTER DOWN  ✕"
      : penalty
        ? (upward ? "↓  PENALTY  ↓" : "↑  PENALTY  ↑")
        : neutral
          ? "→  LOCKED AT  →"
          : (upward ? "↑  LOCKED AT  ↑" : "↓  LOCKED AT  ↓");
    center(arrowLabel, 790, "700 24px 'JetBrains Mono', monospace", walkedOut || penalty ? "#DC2626" : neutral ? "#706C64" : upward ? "#2563EB" : "#15803D");
    center(`₹${money(deal.final_price)}`, 900, "700 84px 'JetBrains Mono', monospace");
    const gainLabel = walkedOut
      ? "NO DEAL"
      : penalty
        ? (upward ? `DROPPED ₹${money(gain)}` : `PENALTY +₹${money(gain)}`)
        : neutral ? "OPENING PRICE" : `${upward ? "GAINED" : "SAVED"} ₹${money(gain)}`;
    const stampColor = neutral ? "#706C64" : penalty || walkedOut ? "#DC2626" : "#15803D";
    const stampFill = neutral ? "#F3F0E8" : penalty || walkedOut ? "#FDE7E4" : "#E7F3E8";
    ctx.save(); ctx.translate(540, 1000); ctx.rotate(-.035); ctx.fillStyle = stampFill; ctx.strokeStyle = stampColor; ctx.lineWidth = 3; ctx.fillRect(-250, -38, 500, 76); ctx.strokeRect(-250, -38, 500, 76); ctx.fillStyle = stampColor; ctx.font = "700 30px 'JetBrains Mono', monospace"; ctx.textAlign = "center"; ctx.fillText(gainLabel, 0, 10, 470); ctx.restore();
    rule(1075);
    center(`${deal.player_name || "JugaadKing"}  ·  ${Number(deal.efficiency_pct || 0).toFixed(0)}% DEAL EFFICIENCY`, 1140, "600 22px 'JetBrains Mono', monospace");
    const rank = Number(deal.rank ?? 0);
    if (walkedOut) center("WALKOUT — NO RANK", 1250, "700 40px 'Space Grotesk', sans-serif", "#DC2626");
    else if (rank <= 0) center("UNRANKED", 1250, "700 40px 'Space Grotesk', sans-serif", "#706C64");
    else {
      center(`RANK #${rank}`, 1250, "700 56px 'Space Grotesk', sans-serif");
      const percentile = Math.max(0, Math.min(100, Number(deal.percentile ?? 0)));
      center(`TOP ${Math.max(1, Math.round(100 - percentile))}% OF ${deal.arena_id === "daily_market" ? "TODAY'S" : "ALL-TIME"} HAGGLERS`, 1298, "600 22px 'JetBrains Mono', monospace", "#706C64");
    }
    rule(1365);
    center("YOUR BOSS IS STILL TALKING…", 1435, "700 23px 'JetBrains Mono', monospace");
    for (let i = 0; i < 45; i += 1) {
      const barH = 18 + ((i * 37 + Number(deal.final_price || 0)) % 70);
      ctx.fillStyle = i % 5 === 0 ? "#DC2626" : "#18181B";
      ctx.fillRect(150 + i * 17, 1510 - barH / 2, 7, barH);
    }
    center("TRY TO BEAT THIS DEAL", 1640, "700 30px 'Space Grotesk', sans-serif");
    center("MOLBHAAV · NO LOGIN · ALL STREET SMART", 1720, "600 18px 'JetBrains Mono', monospace", "#706C64");
    return canvas;
  }
  window.ReceiptCanvas = {
    async download(deal) {
      await Promise.resolve(document.fonts?.ready).catch(() => {});
      const canvas = draw(deal);
      const filename = `molbhaav-receipt-${deal.deal_id || "deal"}.png`;
      const trigger = (href, revoke) => {
        const link = document.createElement("a");
        link.download = filename;
        link.href = href;
        document.body.append(link);
        try { link.click(); } finally {
          link.remove();
          if (revoke) setTimeout(() => URL.revokeObjectURL(href), 1500);
        }
      };
      if (typeof canvas.toBlob === "function") {
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
        if (blob) {
          trigger(URL.createObjectURL(blob), true);
          return;
        }
      }
      trigger(canvas.toDataURL("image/png"), false);
    },
    render(deal) { return draw(deal); }
  };
})();
