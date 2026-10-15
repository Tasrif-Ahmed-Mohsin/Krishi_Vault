// KrishiVault pitch deck for GP FutureMakers 2026 (Round 2, concept pitch): 10 slides, 7 minutes.
// Every figure comes from the KrishiVault engine (krishivault-pipeline) or a source named on the slide.
//
// Run (needs: npm install pptxgenjs react react-dom react-icons sharp):
//   node build_deck.js <out.pptx> <hook.mp4> <poster.jpg> <close.jpg> <pptx-skill-dir>
// Then scripts/pitch_deck/finish_deck.ps1 sets the video to play on entry (PowerPoint COM).

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const [OUT, VIDEO, POSTER, CLOSE_BG, SKILL] = process.argv.slice(2);
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));

// ---------------------------------------------------------------- theme
const THEME = {
  name: "KrishiVault Harvest",
  headFontFace: "Georgia",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "12241B", // text
    lt1: "FFFFFF",
    dk2: "0F3323", // forest: dark slides, titles
    lt2: "F1F5EF", // pale sage: light slides
    accent1: "E8A317", // harvest gold
    accent2: "2E7D4F", // leaf green: gains
    accent3: "B5402B", // brick: losses
    accent4: "8A6743", // potato brown
    accent5: "1F78B4", // telco blue
    accent6: "66766D", // muted
    hlink: "E8A317",
    folHlink: "E8A317",
  },
};
const HEX = THEME.colors;
const BN = "Nirmala UI"; // Bangla script

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "KrishiVault: store or sell, and until when?";
pres.subject = "GP FutureMakers 2026 concept pitch";
pres.author = "Team KrishiVault";
pres.company = "KrishiVault";
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, M = 0.6;
const RECT = pres.shapes.RECTANGLE;

// ---------------------------------------------------------------- helpers
const shadow = (o = 0.14) => ({ type: "outer", blur: 7, offset: 2, angle: 90, color: "000000", opacity: o });
const icons = {};
async function icon(name, hex, px = 256) {
  const key = `${name}-${hex}`;
  if (!icons[key]) {
    const svg = RDS.renderToStaticMarkup(React.createElement(lu[name], { color: "#" + hex, size: String(px) }));
    const buf = await sharp(Buffer.from(svg)).resize(px, px).png().toBuffer();
    icons[key] = "image/png;base64," + buf.toString("base64");
  }
  return icons[key];
}
const img64 = (p) => "image/jpeg;base64," + fs.readFileSync(p).toString("base64");

function text(slide, t, o) {
  slide.addText(t, { isTextBox: true, margin: 0, valign: "top", ...o });
}
function card(slide, x, y, w, h, o = {}) {
  slide.addShape(RECT, {
    x, y, w, h,
    fill: { color: o.fill || C.background1, ...(o.transparency != null ? { transparency: o.transparency } : {}) },
    line: o.line === false ? { type: "none" } : { color: o.lineColor || "D9E2D6", width: 0.75 },
    shadow: o.shadow === false ? undefined : shadow(o.shadowOpacity),
    objectName: o.name,
  });
}
// a square icon tile: the deck's motif (sharp corners, like a stamped receipt)
async function tile(slide, x, y, s, iconName, o = {}) {
  slide.addShape(RECT, {
    x, y, w: s, h: s, fill: { color: o.fill || C.accent1 }, line: { type: "none" },
    shadow: shadow(0.18), objectName: o.name || `${iconName} tile`,
  });
  const pad = s * 0.22;
  slide.addImage({ data: await icon(iconName, o.iconHex || HEX.dk2), x: x + pad, y: y + pad, w: s - 2 * pad, h: s - 2 * pad, altText: o.alt || iconName });
}
function header(slide, kicker, title) {
  slide.addText(kicker, { placeholder: "kicker" });
  slide.addText(title, { placeholder: "title" });
}

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "KV Dark Full",
  background: { color: C.text2 },
  objects: [],
});
// content layouts: kicker and title placeholders, footer and slide number
function masterWithHeader(title, bg, kickerColor, titleColor, footColor) {
  pres.defineSlideMaster({
    title,
    background: { color: bg },
    margin: [0.5, M, 0.6, M],
    objects: [
      { text: { text: "KrishiVault  ·  কৃষিভল্ট", options: { x: M, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: footColor, margin: 0 } } },
      { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.42, w: W - 2 * M, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: kickerColor, margin: 0, valign: "top", align: "left" }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.74, w: W - 2 * M, h: 1.0, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: titleColor, margin: 0, valign: "top", align: "left" }, text: "" } },
    ],
    slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: footColor, align: "right" },
  });
}
masterWithHeader("KV Content Light", C.background2, C.accent2, C.text2, C.accent6);
masterWithHeader("KV Content Dark", C.text2, C.accent1, C.background1, "A9BDB0");

// ================================================================= slides
async function build() {
  // ------------------------------------------------------------ 1. hook: the farmer
  pres.addSection({ title: "Hook" });
  const s1 = pres.addSlide({ masterName: "KV Dark Full", sectionTitle: "Hook" });
  s1.addMedia({ type: "video", path: VIDEO, cover: img64(POSTER), x: 0, y: 0, w: W, h: H, objectName: "Farmer video" });
  // shown after the clip ends (finish_deck.ps1 adds the fade): the line the speaker says
  s1.addShape(RECT, { x: 0.55, y: 4.6, w: 9.5, h: 2.3, fill: { color: C.text2, transparency: 10 }, line: { type: "none" }, shadow: shadow(0.3), objectName: "Hook caption panel" });
  text(s1, [
    { text: "He grows the crop.", options: { breakLine: true } },
    { text: "Someone else gets paid for waiting.", options: { color: C.accent1 } },
  ], { x: 0.95, y: 4.88, w: 8.9, h: 1.2, fontFace: THEME.headFontFace, fontSize: 32, bold: true, color: C.background1, objectName: "Hook caption" });
  text(s1, "KrishiVault makes sure the farmer can wait.", { x: 0.95, y: 6.18, w: 8.9, h: 0.45, fontSize: 18, color: "D7E3DA", objectName: "Hook promise" });
  s1.addNotes(NOTES[1]);

  // ------------------------------------------------------------ 2. problem: the rise never reaches him
  pres.addSection({ title: "Problem" });
  const s2 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Problem" });
  header(s2, "THE PROBLEM  ·  11.6 MILLION TONNES OF POTATO A YEAR", "The price rise is real. It never reaches the farmer.");
  card(s2, M, 1.95, 7.55, 4.75, { name: "Price chart card" });
  text(s2, "Retail potato price, ৳ per kg (WFP, national median)", { x: M + 0.3, y: 2.12, w: 7, h: 0.32, fontSize: 14, bold: true, color: C.text1 });
  const months = ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  s2.addChart(pres.charts.LINE, [
    { name: "2024: normal crop", labels: months, values: [35, null, null, null, null, null, null, 54.5, 56.25, 67.5, 66.41] },
    { name: "2025: big crop", labels: months, values: [25, null, 21.21, 20, 22.28, 24.64, 23.3, 22.65, 20.02, null, 23.7] },
  ], {
    x: M + 0.15, y: 2.5, w: 7.25, h: 3.7, objectName: "WFP price chart",
    chartColors: [HEX.accent2, HEX.accent3], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8,
    displayBlanksAs: "gap",
    showLegend: true, legendPos: "t", legendFontSize: 12, legendColor: HEX.dk1, legendFontFace: "+mn-lt",
    catAxisLabelColor: HEX.accent6, valAxisLabelColor: HEX.accent6, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valAxisMinVal: 0, valAxisMaxVal: 80, valAxisMajorUnit: 20, valAxisLabelFormatCode: "৳0",
    valGridLine: { color: "E3E9E0", size: 0.75 }, catGridLine: { style: "none" },
    catAxisLineShow: false, valAxisLineShow: false,
  });
  // callouts on the chart
  text(s2, [{ text: "৳35 → ৳67.50", options: { bold: true, color: C.accent2, breakLine: true } }, { text: "nearly doubled by November", options: { color: C.text1 } }],
    { x: M + 2.55, y: 3.2, w: 2.45, h: 0.6, fontSize: 13, align: "right" });
  text(s2, [{ text: "Stuck at ৳20–25", options: { bold: true, color: C.accent3, breakLine: true } }, { text: "the crop was 7% above trend", options: { color: C.text1 } }],
    { x: M + 3.1, y: 4.3, w: 2.6, h: 0.6, fontSize: 13 });
  text(s2, "Mar–Aug 2024: too few markets reported. Sources: WFP via HDX; BBS 2024-25.", { x: M + 0.3, y: 6.3, w: 7, h: 0.28, fontSize: 10, color: C.accent6 });

  const stats = [
    ["64%", "of the harvest is sold right away, at the season's lowest price"],
    ["97.6%", "of cold-stored potatoes are bought by traders, not farmers"],
    ["33%", "of all the value added goes to wholesalers"],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 1.95 + i * 1.5;
    card(s2, 8.5, y, 4.23, 1.3, { name: `Stat card ${i + 1}` });
    text(s2, stats[i][0], { x: 8.75, y: y + 0.2, w: 1.75, h: 0.9, fontFace: THEME.headFontFace, fontSize: 34, bold: true, color: i === 0 ? C.accent3 : C.text2, valign: "middle", fit: "shrink" });
    text(s2, stats[i][1], { x: 10.5, y: y + 0.17, w: 2.05, h: 0.96, fontSize: 13.5, color: C.text1, valign: "middle" });
  }
  text(s2, "Value-chain study, Kahaloo (Bogura) and Munshiganj, 2016 fieldwork.", { x: 8.5, y: 6.42, w: 4.23, h: 0.28, fontSize: 10, color: C.accent6 });
  s2.addNotes(NOTES[2]);

  // ------------------------------------------------------------ 3. three traps
  const s3 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Problem" });
  header(s3, "WHY HE SELLS AT THE BOTTOM", "Three traps force the sale, and nobody gets him out");
  const traps = [
    ["LuHandCoins", "The cash trap", "Input loans and the trader's advance (dadon) fall due at harvest. He has to sell now, at the lowest price of the year.", "Debts due on day 1"],
    ["LuWarehouse", "The flat-rent trap", "Cold storage costs about ৳300 a sack for 1 month or 9. Afraid of a fall, he sells after 1 to 3 months, having paid for 9.", "৳300 a sack, 1 month or 9"],
    ["LuChartLine", "The blind-bet trap", "Crop size sets the price: 2024 doubled, 2025 stayed flat. Nobody tells him which kind of year it is.", "−৳25,280 storing 36 sacks in 2025"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * (3.91 + 0.2);
    card(s3, x, 1.95, 3.91, 3.55, { name: `Trap card ${i + 1}` });
    await tile(s3, x + 0.3, 2.25, 0.72, traps[i][0], { fill: C.accent1 });
    text(s3, traps[i][1], { x: x + 1.2, y: 2.25, w: 2.55, h: 0.72, fontFace: THEME.headFontFace, fontSize: 21, bold: true, color: C.text2, valign: "middle" });
    text(s3, traps[i][2], { x: x + 0.3, y: 3.2, w: 3.35, h: 1.3, fontSize: 15, color: C.text1 });
    s3.addShape(RECT, { x: x + 0.3, y: 4.62, w: 3.31, h: 0.62, fill: { color: i === 2 ? C.accent3 : C.accent2, transparency: 88 }, line: { type: "none" }, objectName: `Trap figure ${i + 1}` });
    text(s3, traps[i][3], { x: x + 0.45, y: 4.62, w: 3.1, h: 0.62, fontSize: 15.5, bold: true, color: i === 2 ? C.accent3 : C.accent2, valign: "middle" });
  }
  card(s3, M, 5.7, W - 2 * M, 1.05, { fill: C.text2, line: false, name: "Insight band" });
  text(s3, [
    { text: "A price alert does not pay today's debt. ", options: { bold: true, color: C.accent1 } },
    { text: "Traders have the cash to wait, the sums and the information. The farmer has none of the three.", options: { color: C.background1 } },
  ], { x: M + 0.35, y: 5.7, w: W - 2 * M - 0.7, h: 1.05, fontSize: 18, valign: "middle" });
  s3.addNotes(NOTES[3]);

  // ------------------------------------------------------------ 4. solution: the loop
  pres.addSection({ title: "Solution" });
  const s4 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Solution" });
  header(s4, "THE SOLUTION  ·  KNOW · CALCULATE · DECIDE · ACT", "One call turns a harvest into a plan, and the cash to wait");
  const steps = [
    ["LuPhoneCall", "1  Call", "He calls or dials USSD with two numbers: sacks harvested, cash needed now."],
    ["LuCalculator", "2  Decide", "Sell 19 sacks now, store 17 until December. Net profit ৳12,940, not ৳5,610."],
    ["LuReceiptText", "3  Vault", "The cold storage weighs the sacks and sends a digital receipt by SMS, in his name."],
    ["LuLandmark", "4  Cash", "A bank lends against the receipt and holds the sacks. No forced sale today."],
    ["LuBellRing", "5  Sell", "A price alert, by call or SMS, says how many sacks to sell and to whom. The sale pays storage, bank, then him."],
  ];
  const sw = 2.25, sg = 0.22;
  for (let i = 0; i < 5; i++) {
    const x = M + i * (sw + sg);
    card(s4, x, 1.95, sw, 3.0, { name: `Step ${i + 1}` });
    await tile(s4, x + 0.25, 2.2, 0.66, steps[i][0], { fill: i === 1 ? C.accent1 : C.text2, iconHex: i === 1 ? HEX.dk2 : HEX.accent1 });
    text(s4, steps[i][1], { x: x + 0.25, y: 3.0, w: sw - 0.4, h: 0.42, fontFace: THEME.headFontFace, fontSize: 19, bold: true, color: C.text2 });
    text(s4, steps[i][2], { x: x + 0.25, y: 3.45, w: sw - 0.42, h: 1.4, fontSize: 13.5, color: C.text1 });
    if (i < 4) s4.addImage({ data: await icon("LuChevronRight", HEX.accent6), x: x + sw - 0.02, y: 3.28, w: 0.26, h: 0.26, altText: "next" });
  }
  // the seven parts and the rules
  card(s4, M, 5.15, 7.6, 1.6, { name: "Seven parts card" });
  text(s4, "SEVEN PARTS, ONE LOOP", { x: M + 0.3, y: 5.3, w: 7, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  const parts = ["Price and crop outlook", "Store-or-sell engine", "Crop-backed loans", "Buyer matching", "Group storage and selling", "Export intelligence", "Profit calculator"];
  let px = M + 0.3, py = 5.68;
  for (let i = 0; i < parts.length; i++) {
    const pw = parts[i].length * 0.07 + 0.32; // Calibri 12.5 pt, with padding
    if (px + pw > M + 7.3) { px = M + 0.3; py += 0.47; }
    s4.addShape(RECT, { x: px, y: py, w: pw, h: 0.36, fill: { color: C.background2 }, line: { color: "CFDACB", width: 0.75 }, objectName: `Part ${i + 1}` });
    text(s4, parts[i], { x: px, y: py, w: pw, h: 0.36, fontSize: 12.5, color: C.text1, align: "center", valign: "middle" });
    px += pw + 0.12;
  }
  card(s4, 8.45, 5.15, W - M - 8.45, 1.6, { fill: C.text2, line: false, name: "Rules card" });
  text(s4, "RULES WE NEVER BREAK", { x: 8.75, y: 5.3, w: 3.8, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent1 });
  text(s4, [
    { text: "We never lend or hold money: banks do", options: { bullet: { indent: 14 }, breakLine: true } },
    { text: "No paid placement in the advice", options: { bullet: { indent: 14 }, breakLine: true } },
    { text: "Ranges and the bad case, never promises", options: { bullet: { indent: 14 } } },
  ], { x: 8.75, y: 5.68, w: 3.85, h: 1.0, fontSize: 13.5, color: C.background1, paraSpaceAfter: 3 });
  s4.addNotes(NOTES[4]);

  // ------------------------------------------------------------ 5. AI and technical rationale + live demo
  const s5 = pres.addSlide({ masterName: "KV Content Dark", sectionTitle: "Solution" });
  header(s5, "AI AND TECHNICAL RATIONALE  ·  LIVE DEMO", "AI listens and speaks Bangla. Exact sums decide.");
  const lanes = [
    ["LuAudioLines", "UNDERSTAND", "AI", [
      "Google Bangla speech-to-text",
      "Our parser reads dialect: মণ, বস্তা, টেকা",
      "Gemini fills gaps; every number must have been said",
    ]],
    ["LuSigma", "DECIDE", "statistics + exact sums", [
      "Price outlook driven by crop size (BBS + WFP)",
      "2,000 simulated price paths, always a range",
      "Rent, 8.65% weight loss, interest, net profit",
    ]],
    ["LuLock", "SPEAK", "AI, under a lock", [
      "Bangla answer from the engine's numbers",
      "Number lock: any changed figure is thrown out",
      "Google Bangla voice, SMS, keypad always works",
    ]],
  ];
  const lg = 0.42, lw = (W - 2 * M - 2 * lg) / 3;
  for (let i = 0; i < 3; i++) {
    const x = M + i * (lw + lg);
    card(s5, x, 1.95, lw, 2.95, { fill: "163F2C", lineColor: "2C5A43", shadowOpacity: 0.35, name: `${lanes[i][1]} lane` });
    await tile(s5, x + 0.25, 2.18, 0.62, lanes[i][0], { fill: i === 1 ? C.accent1 : C.background1, iconHex: HEX.dk2 });
    text(s5, lanes[i][1], { x: x + 1.05, y: 2.18, w: 2.4, h: 0.34, fontSize: 17, bold: true, charSpacing: 2, color: i === 1 ? C.accent1 : C.background1 });
    text(s5, lanes[i][2], { x: x + 1.05, y: 2.52, w: 2.45, h: 0.3, fontSize: 13, italic: true, color: "A9BDB0" });
    text(s5, lanes[i][3].map((t, k) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: k < 2 } })),
      { x: x + 0.25, y: 3.05, w: lw - 0.45, h: 1.75, fontSize: 14, color: "E6EEE8", paraSpaceAfter: 5 });
    if (i < 2) s5.addImage({ data: await icon("LuArrowRight", HEX.accent1), x: x + lw + 0.07, y: 3.25, w: 0.28, h: 0.28, altText: "then" });
  }
  // why this design
  text(s5, "WHY THIS DESIGN", { x: M, y: 5.12, w: 6, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent1 });
  text(s5, [
    { text: "He can't read an SMS: ", options: { bold: true, color: C.background1 } },
    { text: "voice first, in his dialect; the keypad always works.", options: { color: "D7E3DA", breakLine: true } },
    { text: "Money must be exact: ", options: { bold: true, color: C.background1 } },
    { text: "a language model never sets a taka figure.", options: { color: "D7E3DA", breakLine: true } },
    { text: "The future is uncertain: ", options: { bold: true, color: C.background1 } },
    { text: "ranges from simulated paths, not one price.", options: { color: "D7E3DA", breakLine: true } },
    { text: "Price data is thin: ", options: { bold: true, color: C.background1 } },
    { text: "ML (XGBoost, LSTM) only once 15 years of DAM prices are backtested.", options: { color: "D7E3DA" } },
  ], { x: M, y: 5.45, w: 7.4, h: 1.45, fontSize: 14, paraSpaceAfter: 3 });
  // live now
  card(s5, 8.3, 5.05, W - M - 8.3, 1.75, { fill: C.accent1, line: false, shadowOpacity: 0.35, name: "Live demo card" });
  text(s5, "LIVE NOW  ·  CLICK TO OPEN", { x: 8.55, y: 5.18, w: 4, h: 0.28, fontSize: 11.5, bold: true, charSpacing: 2, color: C.text2 });
  // the link is set on the shapes by finish_deck.ps1 (a text hyperlink would take the theme's link colour)
  text(s5, "koryu.ninja", { x: 8.55, y: 5.45, w: 4, h: 0.55, fontFace: THEME.headFontFace, fontSize: 28, bold: true, color: C.text2, objectName: "Demo link" });
  text(s5, "Dashboard, voice call, USSD menu, real SMS and phone call. 160 tests pass.", { x: 8.55, y: 6.05, w: 3.95, h: 0.62, fontSize: 12.5, color: C.text2, objectName: "Demo details" });
  s5.addNotes(NOTES[5]);

  // ------------------------------------------------------------ 6. proof
  pres.addSection({ title: "Proof" });
  const s6 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Proof" });
  header(s6, "PROOF  ·  FAIR REPLAYS, NO HINDSIGHT", "Tested on two real seasons it had never seen");
  // 2024
  card(s6, M, 1.95, 4.55, 4.45, { name: "2024 replay card" });
  text(s6, "MARCH 2024  ·  NORMAL CROP", { x: M + 0.3, y: 2.12, w: 4, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  text(s6, "“Sell 11 sacks, store 25 until December”", { x: M + 0.3, y: 2.45, w: 4.0, h: 0.62, fontFace: THEME.headFontFace, fontSize: 17, bold: true, color: C.text2 });
  s6.addChart(pres.charts.BAR, [{ name: "Net profit on 36 sacks", labels: ["Sold all at harvest", "With KrishiVault"], values: [11740, 29450] }], {
    x: M + 0.1, y: 3.12, w: 2.85, h: 3.15, barDir: "col", objectName: "2024 net profit chart",
    chartColors: [HEX.accent6, HEX.accent2], invertedColors: [HEX.accent6, HEX.accent2], varyColors: true,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", dataLabelFontSize: 13, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt", dataLabelFontBold: true,
    catAxisLabelColor: HEX.accent6, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt",
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, valAxisMaxVal: 36000, valAxisMinVal: 0,
    showLegend: false, barGapWidthPct: 70,
  });
  text(s6, "2.5×", { x: M + 2.95, y: 3.35, w: 1.5, h: 0.8, fontFace: THEME.headFontFace, fontSize: 44, bold: true, color: C.accent2, align: "center" });
  text(s6, "net profit, after the ৳14 a kg growing cost", { x: M + 2.95, y: 4.15, w: 1.5, h: 1.0, fontSize: 12.5, color: C.text1, align: "center" });
  // 2025
  const x2 = M + 4.55 + 0.25;
  card(s6, x2, 1.95, 4.0, 4.45, { name: "2025 replay card" });
  text(s6, "MARCH 2025  ·  BIG CROP", { x: x2 + 0.3, y: 2.12, w: 3.5, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent3 });
  text(s6, "“Sell now.”", { x: x2 + 0.3, y: 2.45, w: 3.4, h: 0.62, fontFace: THEME.headFontFace, fontSize: 17, bold: true, color: C.text2 });
  text(s6, "Storing all 36 sacks would have lost up to", { x: x2 + 0.3, y: 3.2, w: 3.4, h: 0.35, fontSize: 14, color: C.text1 });
  text(s6, "৳25,280", { x: x2 + 0.3, y: 3.55, w: 3.4, h: 0.8, fontFace: THEME.headFontFace, fontSize: 40, bold: true, color: C.accent3 });
  text(s6, "and at least ৳17,110, whichever month he sold. The advice kept that loss out of his pocket.", { x: x2 + 0.3, y: 4.4, w: 3.4, h: 0.8, fontSize: 14, color: C.text1 });
  card(s6, x2 + 0.3, 5.3, 3.4, 0.85, { fill: C.background2, shadow: false, lineColor: "D9E2D6", name: "Trust note" });
  text(s6, "An advisor that says “don't store” when storing loses is one a farmer can trust.", { x: x2 + 0.45, y: 5.3, w: 3.15, h: 0.85, fontSize: 12.5, italic: true, color: C.text2, valign: "middle" });
  // backtest
  const x3 = x2 + 4.0 + 0.25;
  card(s6, x3, 1.95, W - M - x3, 4.45, { fill: C.text2, line: false, name: "Backtest card" });
  text(s6, "PRICE OUTLOOK BACKTEST", { x: x3 + 0.28, y: 2.12, w: 3, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent1 });
  const bt = [["11%", "average price miss, against 52% for the usual seasonal pattern"], ["92%", "of months inside its 8-in-10 range"], ["2 of 2", "store-or-sell calls right"]];
  for (let i = 0; i < 3; i++) {
    const y = 2.55 + i * 1.22;
    text(s6, bt[i][0], { x: x3 + 0.28, y, w: 2.9, h: 0.6, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.accent1 });
    text(s6, bt[i][1], { x: x3 + 0.28, y: y + 0.58, w: 2.95, h: 0.6, fontSize: 12.5, color: "E6EEE8" });
  }
  text(s6, "Engine replays: 36 sacks, ৳300 rent, 8.65% weight loss, ৳14/kg growing cost (DAE Bogura 2024-25), WFP retail prices. Two seasons is a first test, not proof: next, 15 years of DAM prices.",
    { x: M, y: 6.48, w: W - 2 * M, h: 0.45, fontSize: 10.5, color: C.accent6 });
  s6.addNotes(NOTES[6]);

  // ------------------------------------------------------------ 7. differentiation and moat
  const s7 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Proof" });
  header(s7, "WHY KRISHIVAULT  ·  DIFFERENTIATION AND DEFENSIBILITY", "Others solve one piece. KrishiVault closes the loop.");
  const yes = await icon("LuCircleCheck", HEX.accent2, 128), no = await icon("LuCircleX", "B9C4BC", 128), part = await icon("LuCircleMinus", HEX.accent4, 128);
  const cols = ["Traders", "Price apps", "Banks, MFIs", "KrishiVault"];
  const rows = [
    ["Cash at harvest without selling", [part, "buys at the low"], [no, ""], [no, "wants land"], [yes, "loan on the receipt"]],
    ["Price outlook, 1 to 9 months", [no, "keeps it private"], [part, "today's price"], [no, ""], [yes, "with a range"]],
    ["Store-or-sell sums after every cost", [no, ""], [no, ""], [no, ""], [yes, "per sack, in taka"]],
    ["Verified stock in cold storage", [part, "holds 97.6%"], [no, ""], [no, "can't check it"], [yes, "digital receipt"]],
    ["Works on a button phone, in Bangla", [yes, "in person"], [no, "smartphone"], [no, "branch visit"], [yes, "voice, USSD, SMS"]],
  ];
  const tx = M, ty = 1.95, c0 = 2.75, cw = 1.27, kvw = 1.55, rh = 0.77;
  const tw = c0 + 3 * cw + kvw;
  card(s7, tx, ty, tw, 0.5 + rows.length * rh + 0.08, { name: "Comparison card" });
  s7.addShape(RECT, { x: tx + c0 + 3 * cw, y: ty, w: kvw, h: 0.5 + rows.length * rh + 0.08, fill: { color: C.accent1, transparency: 82 }, line: { type: "none" }, objectName: "KrishiVault column" });
  for (let j = 0; j < 4; j++) {
    const x = tx + c0 + j * cw;
    text(s7, cols[j], { x, y: ty + 0.1, w: j === 3 ? kvw : cw, h: 0.34, fontSize: 13, bold: true, align: "center", color: j === 3 ? C.text2 : C.accent6, valign: "middle" });
  }
  for (let r = 0; r < rows.length; r++) {
    const y = ty + 0.5 + r * rh;
    if (r > 0) s7.addShape(pres.shapes.LINE, { x: tx + 0.2, y, w: tw - 0.4, h: 0, line: { color: "E3E9E0", width: 0.75 } });
    text(s7, rows[r][0], { x: tx + 0.25, y, w: c0 - 0.35, h: rh, fontSize: 13.5, bold: true, color: C.text1, valign: "middle" });
    for (let j = 0; j < 4; j++) {
      const [ic, note] = rows[r][j + 1];
      const x = tx + c0 + j * cw, w = j === 3 ? kvw : cw;
      s7.addImage({ data: ic, x: x + w / 2 - 0.13, y: y + 0.09, w: 0.26, h: 0.26, altText: ic === yes ? "yes" : ic === no ? "no" : "partly" });
      if (note) text(s7, note, { x: x + 0.04, y: y + 0.38, w: w - 0.08, h: 0.32, fontSize: 10.5, align: "center", color: j === 3 ? C.text2 : C.accent6, bold: j === 3 });
    }
  }
  // moat
  const mx = tx + tw + 0.3, mw = W - M - mx;
  text(s7, "WHY IT IS HARD TO COPY", { x: mx, y: 1.97, w: mw, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  const moat = [
    ["LuRoute", "The loop is the product", "Sums, receipt, loan, alert, split at sale. One piece alone does not break the trap."],
    ["LuHandshake", "Both sides are paid to stay", "Cold storages fill space; banks get stock they can check."],
    ["LuShieldCheck", "Trust built into the code", "Ranges, the bad case said aloud, the number lock."],
    ["LuDatabase", "Data that compounds", "Every consented call adds district data nobody else has."],
  ];
  for (let i = 0; i < 4; i++) {
    const y = 2.4 + i * 1.02;
    await tile(s7, mx, y + 0.05, 0.5, moat[i][0], { fill: C.text2, iconHex: HEX.accent1 });
    text(s7, moat[i][1], { x: mx + 0.68, y, w: mw - 0.68, h: 0.32, fontSize: 15, bold: true, color: C.text2 });
    text(s7, moat[i][2], { x: mx + 0.68, y: y + 0.33, w: mw - 0.68, h: 0.62, fontSize: 12.5, color: C.text1 });
  }
  text(s7, "Warehouse-receipt lending already lets farmers wait in India (Arya.ag). Bangladesh has the cold storages; KrishiVault adds the sums, the receipt and the phone.",
    { x: M, y: 6.5, w: W - 2 * M, h: 0.4, fontSize: 12.5, italic: true, color: C.accent6 });
  s7.addNotes(NOTES[7]);

  // ------------------------------------------------------------ 8. execution, scale, business
  pres.addSection({ title: "Execution and impact" });
  const s8 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Execution and impact" });
  header(s8, "EXECUTION  ·  SCALE  ·  BUSINESS MODEL", "Pilot in Kahaloo next harvest. Break even in year two.");
  const phases = [
    ["PHASE 1  ·  MONTHS 1–4", "Kahaloo, Bogura", "50–100 farmers, 1–2 cold storages, 1 lender. First 100 tonnes of crop-backed loans."],
    ["PHASE 2  ·  MONTHS 5–12", "Bogura + Munshiganj", "1,000+ farmers, 10 cold storages, group storage and buyer lots."],
    ["PHASE 3  ·  YEAR 2 ON", "National", "Rangpur, Dinajpur, Cumilla, Thakurgaon. Onion and maize; export market."],
  ];
  const phw = 3.91;
  for (let i = 0; i < 3; i++) {
    const x = M + i * (phw + 0.2);
    card(s8, x, 1.95, phw, 1.6, { fill: i === 0 ? C.text2 : C.background1, line: i !== 0, name: `Phase ${i + 1}` });
    text(s8, phases[i][0], { x: x + 0.28, y: 2.08, w: phw - 0.5, h: 0.28, fontSize: 11.5, bold: true, charSpacing: 2, color: i === 0 ? C.accent1 : C.accent2 });
    text(s8, phases[i][1], { x: x + 0.28, y: 2.38, w: phw - 0.5, h: 0.4, fontFace: THEME.headFontFace, fontSize: 19, bold: true, color: i === 0 ? C.background1 : C.text2 });
    text(s8, phases[i][2], { x: x + 0.28, y: 2.8, w: phw - 0.5, h: 0.7, fontSize: 13, color: i === 0 ? "E6EEE8" : C.text1 });
    if (i < 2) s8.addImage({ data: await icon("LuChevronRight", HEX.accent6), x: x + phw - 0.02, y: 2.62, w: 0.24, h: 0.24, altText: "then" });
  }
  // who pays
  card(s8, M, 3.75, 4.35, 3.0, { name: "Who pays card" });
  text(s8, "WHO PAYS: NEVER THE FARMER", { x: M + 0.28, y: 3.9, w: 4, h: 0.28, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  const fees = [["Cold storage", "4% of rent", "৳12 / sack"], ["Bank or MFI", "1.5% of loan", "৳4.50 / sack"], ["Buyer", "1% sourcing fee", "≈৳12 / sack"], ["Grameenphone", "call revenue share", "≈৳30 / farmer"], ["Govt, media", "glut and stock data", "subscription"]];
  for (let i = 0; i < fees.length; i++) {
    const y = 4.3 + i * 0.47;
    text(s8, fees[i][0], { x: M + 0.28, y, w: 1.3, h: 0.4, fontSize: 13, bold: true, color: C.text1, valign: "middle" });
    text(s8, fees[i][1], { x: M + 1.58, y, w: 1.45, h: 0.4, fontSize: 12, color: C.accent6, valign: "middle" });
    text(s8, fees[i][2], { x: M + 2.95, y, w: 1.2, h: 0.4, fontSize: 13, bold: true, color: C.text2, align: "right", valign: "middle" });
  }
  // projection chart
  const cx = M + 4.35 + 0.25;
  card(s8, cx, 3.75, 4.3, 3.0, { name: "Projection card" });
  text(s8, "PROJECTION, ৳ LAKH", { x: cx + 0.28, y: 3.9, w: 3.8, h: 0.28, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  s8.addChart(pres.charts.BAR, [
    { name: "Revenue", labels: ["Year 1", "Year 2", "Year 3"], values: [17.24, 126.3, 492.2] },
    { name: "Operating cost", labels: ["Year 1", "Year 2", "Year 3"], values: [18.5, 58, 145] },
  ], {
    x: cx + 0.1, y: 4.2, w: 4.1, h: 2.5, barDir: "col", barGrouping: "clustered", objectName: "Projection chart",
    chartColors: [HEX.accent2, HEX.accent6], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", dataLabelFontSize: 10.5, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.accent6, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, valAxisMaxVal: 580, valAxisMinVal: 0,
    showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.dk1, legendFontFace: "+mn-lt", barGapWidthPct: 60,
  });
  // the ask
  const ax = cx + 4.3 + 0.25, aw = W - M - ax;
  card(s8, ax, 3.75, aw, 3.0, { fill: C.text2, line: false, name: "Ask card" });
  text(s8, "TO START", { x: ax + 0.28, y: 3.9, w: aw - 0.5, h: 0.28, fontSize: 12, bold: true, charSpacing: 2, color: C.accent1 });
  text(s8, "৳20 lakh", { x: ax + 0.28, y: 4.2, w: aw - 0.5, h: 0.7, fontFace: THEME.headFontFace, fontSize: 34, bold: true, color: C.accent1 });
  text(s8, [
    { text: "Year 1: 2,000 farmers, 5 cold storages", options: { bullet: { indent: 14 }, breakLine: true } },
    { text: "Break-even: month 14–16", options: { bullet: { indent: 14 }, breakLine: true } },
    { text: "No storage to build, no money lent", options: { bullet: { indent: 14 } } },
  ], { x: ax + 0.28, y: 4.95, w: aw - 0.4, h: 1.75, fontSize: 13, color: C.background1, paraSpaceAfter: 6 });
  s8.addNotes(NOTES[8]);

  // ------------------------------------------------------------ 9. impact
  const s9 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Execution and impact" });
  header(s9, "IMPACT  ·  AI FOR SOCIAL GOOD", "When farmers can wait, the whole chain gets fairer");
  const impact = [
    ["LuWallet", "FARMER INCOME", "2.5×", "net profit in a normal year (2024 replay), and no storage loss in a glut year"],
    ["LuTrendingUp", "AT SCALE", "৳118 crore", "more to farmers in a normal year at year-3 scale: 2.4 million sacks × ৳492 (an illustration, not a forecast)"],
    ["LuSprout", "FOOD AND RESILIENCE", "Less waste", "curing reminders, generator-backed storage, and no storing into a glut year"],
    ["LuLandmark", "GOVERNMENT", "Stock it can see", "a glut warning from crop data, receipts with a name, district figures from farmers who agree"],
  ];
  const iw = 2.88, ig = 0.2;
  for (let i = 0; i < 4; i++) {
    const x = M + i * (iw + ig);
    card(s9, x, 1.95, iw, 3.55, { name: `Impact ${i + 1}` });
    await tile(s9, x + 0.28, 2.22, 0.62, impact[i][0], { fill: i === 1 ? C.accent1 : C.text2, iconHex: i === 1 ? HEX.dk2 : HEX.accent1 });
    text(s9, impact[i][1], { x: x + 0.28, y: 3.0, w: iw - 0.45, h: 0.28, fontSize: 11.5, bold: true, charSpacing: 2, color: C.accent2 });
    text(s9, impact[i][2], { x: x + 0.28, y: 3.3, w: iw - 0.45, h: 0.62, fontFace: THEME.headFontFace, fontSize: i < 2 ? 30 : 22, bold: true, color: C.text2, valign: "middle", fit: "shrink" });
    text(s9, impact[i][3], { x: x + 0.28, y: 4.0, w: iw - 0.48, h: 1.42, fontSize: 14.5, color: C.text1 });
  }
  card(s9, M, 5.7, W - 2 * M, 1.05, { fill: C.text2, line: false, name: "Inclusion band" });
  await tile(s9, M + 0.28, 5.92, 0.6, "LuSmartphone", { fill: C.accent1 });
  text(s9, [
    { text: "Built for farmers like the one in our video, who can't read an SMS: ", options: { bold: true, color: C.accent1 } },
    { text: "a voice call in his own dialect, a two-number USSD menu. Any button phone, no internet.", options: { color: C.background1 } },
  ], { x: M + 1.1, y: 5.7, w: W - 2 * M - 1.4, h: 1.05, fontSize: 16, valign: "middle" });
  s9.addNotes(NOTES[9]);

  // ------------------------------------------------------------ 10. close
  pres.addSection({ title: "Close" });
  const s10 = pres.addSlide({ masterName: "KV Dark Full", sectionTitle: "Close" });
  const pw10 = 5.33; // the farmer, on the left, looking toward the message
  s10.addImage({ data: img64(CLOSE_BG), x: 0, y: 0, w: pw10, h: H, altText: "The farmer from our field video", objectName: "Farmer still" });
  const tx10 = pw10 + 0.65, tw10 = W - tx10 - M;
  text(s10, "NEXT MARCH", { x: tx10, y: 0.75, w: tw10, h: 0.32, fontSize: 13, bold: true, charSpacing: 3, color: C.accent1 });
  text(s10, "He will ask the same question. This time he gets the sums, the cash to wait, and a receipt with his own name on it.",
    { x: tx10, y: 1.18, w: tw10, h: 2.45, fontFace: THEME.headFontFace, fontSize: 28, bold: true, color: C.background1 });
  text(s10, [{ text: "আলু রাখবেন না বেচবেন, কবে বেচবেন:", options: { breakLine: true } }, { text: "হিসাব করে বলে কৃষিভল্ট।" }],
    { x: tx10, y: 3.62, w: tw10, h: 0.95, fontFace: BN, fontSize: 20, bold: true, color: C.accent1, lineSpacingMultiple: 0.95 });
  text(s10, "Store or sell, and until when: KrishiVault does the sums.", { x: tx10, y: 4.6, w: tw10, h: 0.4, fontSize: 15, italic: true, color: "D7E3DA" });
  card(s10, tx10, 5.2, tw10, 1.3, { fill: C.accent1, line: false, shadowOpacity: 0.35, name: "Ask card" });
  text(s10, "OUR ASK", { x: tx10 + 0.3, y: 5.35, w: 3, h: 0.28, fontSize: 12, bold: true, charSpacing: 3, color: C.text2 });
  text(s10, "Help us open the first cold storage and the first lender in Kahaloo, on Grameenphone's voice line.",
    { x: tx10 + 0.3, y: 5.65, w: tw10 - 0.55, h: 0.75, fontSize: 16, bold: true, color: C.text2 });
  text(s10, [
    { text: "Try it: ", options: { color: "A9BDB0" } },
    { text: "koryu.ninja", options: { color: C.accent1, bold: true, underline: { style: "sng" } } },
  ], { x: tx10, y: 6.8, w: 4, h: 0.35, fontSize: 14, color: C.background1, objectName: "Close link" });
  s10.addNotes(NOTES[10]);

  await pres.writeFile({ fileName: OUT });
  await tidyCharts(OUT);
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}

// Data labels on one line (PowerPoint wraps "29,450" in narrow charts) and months without prices left blank.
async function tidyCharts(file) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n))) {
    let xml = await zip.file(name).async("string");
    xml = xml.replace(/(<c:dLbls>(?:(?!<\/c:dLbls>).)*?<c:txPr>)<a:bodyPr\/>/gs, '$1<a:bodyPr wrap="none"/>');
    xml = xml.replace(/<c:pt idx="\d+"><c:v><\/c:v><\/c:pt>/g, "");
    zip.file(name, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

// ================================================================= speaker notes
const NOTES = require("./speaker_notes.js");

build().catch((e) => { console.error(e); process.exit(1); });
