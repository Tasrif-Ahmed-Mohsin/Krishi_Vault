// KrishiVault pitch deck for GP FutureMakers 2026 (Round 2, concept pitch): 10 slides, 7 minutes.
// Every figure comes from the KrishiVault engine (krishivault-pipeline) or a source named on the slide.
//
// Run (needs: npm install pptxgenjs react react-dom react-icons sharp):
//   python make_hook_assets.py <frame.jpg> <hook dir> 2.78 3.05   (slide 1 still and newsprint)
//   node build_deck.js <out.pptx> <hook.mp4> <poster.jpg> <close.jpg> <hook dir> <pptx-skill-dir>
// Then finish_deck.ps1 sets the video to play on entry and fades in the clippings (PowerPoint COM).

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const [OUT, VIDEO, POSTER, CLOSE_BG, HOOK_DIR, SKILL] = process.argv.slice(2);
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
const MARK = "F2B635"; // yellow highlighter behind key words (dark text on it)

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
// title with the key words highlighted: [before, marked, after]
function header(slide, kicker, [before, marked, after = ""]) {
  slide.addText(kicker, { placeholder: "kicker" });
  slide.addText([
    ...(before ? [{ text: before }] : []),
    { text: marked, options: { highlight: MARK, color: C.text2 } },
    ...(after ? [{ text: after }] : []),
  ], { placeholder: "title" });
}
const marked = (t, extra = {}) => ({ text: t, options: { highlight: MARK, color: C.text2, ...extra } });

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
  // ------------------------------------------------------------ 1. hook: the farmer, then the clippings
  pres.addSection({ title: "Hook" });
  const s1 = pres.addSlide({ masterName: "KV Dark Full", sectionTitle: "Hook" });
  s1.addMedia({ type: "video", path: VIDEO, cover: img64(POSTER), x: 0, y: 0, w: W, h: H, objectName: "Farmer video" });
  // everything below appears after the clip ends (finish_deck.ps1 fades it in and groups each "Ev N" clipping):
  // a still of the farmer, his face clear on the left; four newspaper clippings on the darkened right
  s1.addImage({ path: path.join(HOOK_DIR, "hook_after.jpg"), x: 0, y: 0, w: W, h: H, altText: "The farmer from our field interview", objectName: "Hook still" });
  text(s1, "HE IS NOT ALONE", { x: M, y: 4.92, w: 5.8, h: 0.3, fontSize: 13, bold: true, charSpacing: 3, color: C.accent1, objectName: "Hook kicker" });
  text(s1, [
    { text: "He grows the crop.", options: { color: C.background1, breakLine: true } },
    marked("Someone else gets paid for waiting."),
  ], { x: M, y: 5.28, w: 5.9, h: 1.45, fontFace: THEME.headFontFace, fontSize: 26, bold: true, objectName: "Hook caption" });
  const INK = "1C1C1C", PRESS = "Times New Roman";
  const clippings = [
    ["news", "The Business Standard", "13 FEBRUARY 2025", "Farmers strain under losses, selling potatoes at half the production cost", "Farm-gate ৳7–9 a kg, against a ৳17.26 production cost."],
    ["news", "The Daily Star", "15 OCTOBER 2025", "Potato farmers left in the lurch as prices crash", "Wholesale ৳8 a kg, half the cost. After 15 November, unsold sacks pass to the cold-storage owners."],
    ["news", "Dhaka Tribune", "1 JULY 2026", "Potato farmers protest cold storage rent hike in Rangpur", "Rent raised to ৳450 a sack, while potatoes sell at ৳14–15 a kg against a ৳25–26 cost."],
    ["journal", "Universal Journal of Agricultural Research", "2014  ·  HAJONG AND OTHERS", "Storage System of Potato in Bangladesh", "High charges, an uncertain price and no money keep farmers out of cold storage. Prices bottom at harvest, peak in December."],
  ];
  const gx0 = 6.95, cgap = 0.22, cw1 = (W - M - gx0 - cgap) / 2, ch1 = 3.05, gy0 = 0.55, PADIN = 30 / 300;
  for (let i = 0; i < 4; i++) {
    const [kind, name, date, headline, body] = clippings[i];
    const x = gx0 + (i % 2) * (cw1 + cgap), y = gy0 + Math.floor(i / 2) * (ch1 + 0.25), n = i + 1;
    const ix = x + 0.2, iw = cw1 - 0.4;
    s1.addImage({ path: path.join(HOOK_DIR, kind === "news" ? "news_paper.png" : "journal_paper.png"), x: x - PADIN, y: y - PADIN, w: cw1 + 2 * PADIN, h: ch1 + 2 * PADIN, altText: "Newsprint", objectName: `Ev ${n} paper` });
    const np = kind === "news" ? 0.36 : 0.5;
    text(s1, name, { x: ix, y: y + 0.16, w: iw, h: np, fontFace: PRESS, fontSize: kind === "news" ? 16 : 12.5, bold: true, color: INK, align: "center", valign: "middle", objectName: `Ev ${n} nameplate` });
    const r1 = y + 0.16 + np + 0.04;
    s1.addShape(pres.shapes.LINE, { x: ix, y: r1, w: iw, h: 0, line: { color: INK, width: 1.5 }, objectName: `Ev ${n} rule 1` });
    text(s1, date, { x: ix, y: r1 + 0.04, w: iw, h: 0.22, fontFace: PRESS, fontSize: 9.5, charSpacing: 1, color: "3A3A3A", align: "center", valign: "middle", objectName: `Ev ${n} dateline` });
    const r2 = r1 + 0.29;
    s1.addShape(pres.shapes.LINE, { x: ix, y: r2, w: iw, h: 0, line: { color: INK, width: 0.5 }, objectName: `Ev ${n} rule 2` });
    text(s1, headline, { x: ix, y: r2 + 0.1, w: iw, h: 1.05, fontFace: PRESS, fontSize: 15.5, bold: true, color: "111111", objectName: `Ev ${n} headline` });
    text(s1, body, { x: ix, y: r2 + 1.18, w: iw, h: y + ch1 - 0.18 - (r2 + 1.18), fontFace: PRESS, fontSize: 12, color: "2E2E2E", objectName: `Ev ${n} body` });
  }
  s1.addNotes(NOTES[1]);

  // ------------------------------------------------------------ 2. problem: the numbers and the three traps
  pres.addSection({ title: "Problem" });
  const s2 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Problem" });
  header(s2, "THE PROBLEM  ·  11.6 MILLION TONNES OF POTATO A YEAR", ["The price rise is real. ", "It never reaches the farmer."]);
  const stats = [
    ["64%", "of the harvest is sold right away, at the season's lowest price ¹", C.accent3],
    ["97.6%", "of cold-stored potatoes are bought by traders, not farmers ¹", C.text2],
    ["≈ 2×", "shop price after a normal crop: ৳35 in Feb, ৳67.50 by Nov 2024 ²", C.accent2],
    ["৳20–25", "all through 2025, after a big crop: storing lost money ²", C.accent3],
  ];
  const stw = (W - 2 * M - 3 * 0.2) / 4, sty = 1.8, sth = 1.3;
  for (let i = 0; i < 4; i++) {
    const x = M + i * (stw + 0.2);
    card(s2, x, sty, stw, sth, { name: `Stat card ${i + 1}` });
    text(s2, stats[i][0], { x: x + 0.22, y: sty + 0.12, w: stw - 0.4, h: 0.55, fontFace: THEME.headFontFace, fontSize: 26, bold: true, color: stats[i][2], valign: "middle", fit: "shrink" });
    text(s2, stats[i][1], { x: x + 0.22, y: sty + 0.68, w: stw - 0.4, h: 0.56, fontSize: 12, color: C.text1 });
  }
  const traps = [
    ["LuHandCoins", "The cash trap", "Loans and the trader's advance (dadon) fall due at harvest. He must sell now, at the year's lowest price.", "Debts due on day 1"],
    ["LuWarehouse", "The flat-rent trap", "About ৳300 a sack for 1 month or 9. Afraid of a fall, he sells after 1 to 3 months, having paid for 9.", "৳300 a sack, 1 month or 9"],
    ["LuChartLine", "The blind-bet trap", "Crop size sets the price: 2024 doubled, 2025 stayed flat. Nobody tells him which kind of year it is.", "−৳25,280 storing 36 sacks in 2025"],
  ];
  const tw3 = (W - 2 * M - 2 * 0.2) / 3, ty3 = 3.3, th3 = 2.2;
  for (let i = 0; i < 3; i++) {
    const x = M + i * (tw3 + 0.2);
    card(s2, x, ty3, tw3, th3, { name: `Trap card ${i + 1}` });
    await tile(s2, x + 0.25, ty3 + 0.2, 0.55, traps[i][0], { fill: C.accent1 });
    text(s2, traps[i][1], { x: x + 0.95, y: ty3 + 0.2, w: tw3 - 1.15, h: 0.55, fontFace: THEME.headFontFace, fontSize: 18, bold: true, color: C.text2, valign: "middle" });
    text(s2, traps[i][2], { x: x + 0.25, y: ty3 + 0.88, w: tw3 - 0.5, h: 0.78, fontSize: 13, color: C.text1 });
    s2.addShape(RECT, { x: x + 0.25, y: ty3 + 1.7, w: tw3 - 0.5, h: 0.36, fill: { color: i === 2 ? C.accent3 : C.accent2, transparency: 88 }, line: { type: "none" }, objectName: `Trap figure ${i + 1}` });
    text(s2, traps[i][3], { x: x + 0.38, y: ty3 + 1.7, w: tw3 - 0.7, h: 0.36, fontSize: 13.5, bold: true, color: i === 2 ? C.accent3 : C.accent2, valign: "middle" });
  }
  card(s2, M, 5.7, W - 2 * M, 0.8, { fill: C.text2, line: false, name: "Insight band" });
  text(s2, [
    marked("A price alert does not pay today's debt.", { bold: true }),
    { text: " " },
    { text: "Traders have the cash, the sums and the information to wait. The farmer has none.", options: { color: C.background1 } },
  ], { x: M + 0.3, y: 5.7, w: W - 2 * M - 0.6, h: 0.8, fontSize: 16, valign: "middle" });
  text(s2, "¹ Value-chain study, Kahaloo (Bogura) and Munshiganj, 2016 fieldwork.   ² WFP retail prices (HDX); the 2025 loss is our engine's replay. Production: BBS 2024-25.",
    { x: M, y: 6.6, w: W - 2 * M, h: 0.26, fontSize: 10, color: C.accent6 });
  s2.addNotes(NOTES[2]);

  // ------------------------------------------------------------ 3. what KrishiVault is
  pres.addSection({ title: "Solution" });
  const s3 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Solution" });
  header(s3, "WHAT KRISHIVAULT IS  ·  KNOW · CALCULATE · DECIDE · ACT", ["One service that ", "answers each trap"]);
  card(s3, M, 1.75, W - 2 * M, 1.05, { fill: C.text2, line: false, name: "Definition band" });
  text(s3, [
    marked("KrishiVault is a voice-first service for potato farmers."),
    { text: " " },
    { text: "It tells him how many sacks to sell now and how many to store, until when, and lets a bank lend against the stored sacks, so he can afford to wait.", options: { color: C.background1 } },
  ], { x: M + 0.35, y: 1.75, w: W - 2 * M - 0.7, h: 1.05, fontFace: THEME.headFontFace, fontSize: 17, bold: true, valign: "middle" });
  const answers = [
    ["The cash trap", "Debts fall due at harvest", "Cash without selling", "A bank lends against a digital cold-storage receipt in his name."],
    ["The flat-rent trap", "Pays for 9 months, sells in 2", "The sums, sack by sack", "Sell how many now, store how many, until when: after rent, 8.65% loss and interest."],
    ["The blind-bet trap", "Can't tell a 2024 from a 2025", "An outlook with a range", "Driven by crop size; in a glut year it says \"sell now\"."],
    ["He can't read an SMS", "From our field interview", "A Bangla voice call", "Two numbers on any button phone; USSD and SMS as well."],
  ];
  const lx = M, lw3 = 2.75, aw3 = 4.65, gx = 0.45, ay = 3.0, ah = 0.74;
  text(s3, "THE TRAP", { x: lx, y: ay - 0.02, w: lw3, h: 0.26, fontSize: 11.5, bold: true, charSpacing: 2, color: C.accent3 });
  text(s3, "KRISHIVAULT'S ANSWER", { x: lx + lw3 + gx, y: ay - 0.02, w: aw3, h: 0.26, fontSize: 11.5, bold: true, charSpacing: 2, color: C.accent2 });
  for (let i = 0; i < 4; i++) {
    const y = ay + 0.32 + i * (ah + 0.1);
    s3.addShape(RECT, { x: lx, y, w: lw3, h: ah, fill: { color: C.accent3, transparency: 90 }, line: { type: "none" }, objectName: `Trap ${i + 1}` });
    text(s3, [{ text: answers[i][0], options: { bold: true, color: C.accent3, breakLine: true } }, { text: answers[i][1], options: { color: C.text1 } }],
      { x: lx + 0.2, y, w: lw3 - 0.3, h: ah, fontSize: 13, valign: "middle" });
    s3.addImage({ data: await icon("LuArrowRight", HEX.accent2), x: lx + lw3 + gx / 2 - 0.13, y: y + ah / 2 - 0.13, w: 0.26, h: 0.26, altText: "answered by" });
    card(s3, lx + lw3 + gx, y, aw3, ah, { name: `Answer ${i + 1}`, shadowOpacity: 0.1 });
    text(s3, [{ text: answers[i][2], options: { bold: true, color: C.text2, breakLine: true } }, { text: answers[i][3], options: { color: C.text1 } }],
      { x: lx + lw3 + gx + 0.2, y, w: aw3 - 0.35, h: ah, fontSize: 13, valign: "middle" });
  }
  const fx = lx + lw3 + gx + aw3 + 0.3, fw = W - M - fx;
  card(s3, fx, ay, fw, 4 * ah + 3 * 0.1 + 0.32, { name: "Facts card" });
  const facts = [
    ["FOR", "Smallholder potato farmers. First in Kahaloo, Bogura."],
    ["THROUGH", "Grameenphone voice line, USSD and SMS. Cold storages and banks use the web."],
    ["PAID BY", "Cold storages, banks and buyers. Never the farmer."],
    ["NEVER", "Lends or holds money, or sells a place in the advice."],
  ];
  for (let i = 0; i < 4; i++) {
    const y = ay + 0.16 + i * 0.83;
    text(s3, facts[i][0], { x: fx + 0.25, y, w: fw - 0.45, h: 0.24, fontSize: 11, bold: true, charSpacing: 2, color: i === 3 ? C.accent3 : C.accent2 });
    text(s3, facts[i][1], { x: fx + 0.25, y: y + 0.25, w: fw - 0.45, h: 0.58, fontSize: 13, color: C.text1 });
  }
  s3.addNotes(NOTES[3]);

  // ------------------------------------------------------------ 4. solution: the loop
  const s4 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Solution" });
  header(s4, "HOW IT WORKS  ·  ONE FARMER, ONE SEASON", ["One call turns a harvest into ", "a plan, and the cash to wait"]);
  const steps = [
    ["LuPhoneCall", "1  Call", "He calls or dials USSD with two numbers: sacks harvested, cash needed now."],
    ["LuCalculator", "2  Decide", "The engine answers in taka: sell 19 sacks now, store 17 until December."],
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
  card(s4, 8.45, 5.15, W - M - 8.45, 1.6, { fill: C.text2, line: false, name: "Result card" });
  text(s4, "HIS SEASON, IN TAKA (36 SACKS)", { x: 8.75, y: 5.3, w: 3.9, h: 0.3, fontSize: 12, bold: true, charSpacing: 2, color: C.accent1 });
  text(s4, [
    { text: "৳25,020 in hand today: ", options: { bold: true, color: C.accent1 } },
    { text: "the cash he needed", options: { color: C.background1, breakLine: true } },
    { text: "Net profit ৳12,940 ", options: { bold: true, color: C.accent1 } },
    { text: "on average, not ৳5,610", options: { color: C.background1, breakLine: true } },
    { text: "Bad case said aloud: ", options: { bold: true, color: C.accent1 } },
    { text: "−৳4,970 (1 in 10)", options: { color: C.background1 } },
  ], { x: 8.75, y: 5.66, w: 3.9, h: 1.0, fontSize: 13.5, paraSpaceAfter: 3 });
  s4.addNotes(NOTES[4]);

  // ------------------------------------------------------------ 5. AI and technical rationale + live demo
  const s5 = pres.addSlide({ masterName: "KV Content Dark", sectionTitle: "Solution" });
  header(s5, "AI AND TECHNICAL RATIONALE  ·  LIVE DEMO", ["AI listens and speaks Bangla. ", "Exact sums decide."]);
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
  header(s6, "PROOF  ·  FAIR REPLAYS, NO HINDSIGHT", ["Tested on ", "two real seasons", " it had never seen"]);
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
  header(s7, "WHY KRISHIVAULT  ·  DIFFERENTIATION AND DEFENSIBILITY", ["Others solve one piece. ", "KrishiVault closes the loop."]);
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
  header(s8, "EXECUTION  ·  SCALE  ·  BUSINESS MODEL", ["", "Potato first, in Kahaloo.", " Break even in year two."]);
  const phases = [
    ["PHASE 1  ·  MONTHS 1–4", "Kahaloo, Bogura", "Potato. 50–100 farmers, 1–2 cold storages, 1 lender. First 100 tonnes of crop-backed loans."],
    ["PHASE 2  ·  MONTHS 5–12", "Bogura + Munshiganj", "Potato. 1,000+ farmers, 10 cold storages, group storage and buyer lots."],
    ["PHASE 3  ·  YEAR 2 ON", "National", "Rangpur, Dinajpur, Cumilla, Thakurgaon. Onion and maize join; export market."],
  ];
  const phw = 3.91, phy = 1.85, phh = 1.4;
  for (let i = 0; i < 3; i++) {
    const x = M + i * (phw + 0.2);
    card(s8, x, phy, phw, phh, { fill: i === 0 ? C.text2 : C.background1, line: i !== 0, name: `Phase ${i + 1}` });
    text(s8, phases[i][0], { x: x + 0.28, y: phy + 0.12, w: phw - 0.5, h: 0.28, fontSize: 11.5, bold: true, charSpacing: 2, color: i === 0 ? C.accent1 : C.accent2 });
    text(s8, phases[i][1], { x: x + 0.28, y: phy + 0.4, w: phw - 0.5, h: 0.4, fontFace: THEME.headFontFace, fontSize: 19, bold: true, color: i === 0 ? C.background1 : C.text2 });
    text(s8, phases[i][2], { x: x + 0.28, y: phy + 0.8, w: phw - 0.5, h: 0.56, fontSize: 12.5, color: i === 0 ? "E6EEE8" : C.text1 });
    if (i < 2) s8.addImage({ data: await icon("LuChevronRight", HEX.accent6), x: x + phw - 0.02, y: phy + 0.58, w: 0.24, h: 0.24, altText: "then" });
  }
  // the crop path: potato first, then the same engine for other stored crops
  const cpy = phy + phh + 0.18, cph = 0.76;
  card(s8, M, cpy, W - 2 * M, cph, { name: "Crop path card" });
  text(s8, [{ text: "START WITH POTATO,", options: { breakLine: true } }, { text: "THEN EXPAND" }],
    { x: M + 0.28, y: cpy, w: 2.1, h: cph, fontSize: 11.5, bold: true, charSpacing: 1, color: C.accent2, valign: "middle" });
  const crops = [
    ["Potato  ·  now", "the biggest stored crop", true],
    ["Onion  ·  next", "same engine, new season", false],
    ["Maize  ·  later", "in the national phase", false],
    ["Any stored crop", "new costs, the same sums", false],
  ];
  const chx0 = M + 2.35, chw = (W - M - 0.2 - chx0 - 3 * 0.3) / 4;
  for (let i = 0; i < 4; i++) {
    const x = chx0 + i * (chw + 0.3);
    s8.addShape(RECT, { x, y: cpy + 0.1, w: chw, h: cph - 0.2, fill: { color: crops[i][2] ? MARK : C.background2 }, line: { type: "none" }, objectName: `Crop ${i + 1}` });
    text(s8, [{ text: crops[i][0], options: { bold: true, color: C.text2, breakLine: true } }, { text: crops[i][1], options: { color: C.text1 } }],
      { x: x + 0.15, y: cpy + 0.1, w: chw - 0.25, h: cph - 0.2, fontSize: 12, valign: "middle" });
    if (i < 3) s8.addImage({ data: await icon("LuArrowRight", HEX.accent2), x: x + chw + 0.04, y: cpy + cph / 2 - 0.11, w: 0.22, h: 0.22, altText: "then" });
  }
  // who pays
  const by = cpy + cph + 0.2, bh = 6.78 - by;
  card(s8, M, by, 4.35, bh, { name: "Who pays card" });
  text(s8, "WHO PAYS: NEVER THE FARMER", { x: M + 0.28, y: by + 0.13, w: 4, h: 0.28, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  const fees = [["Cold storage", "4% of rent", "৳12 / sack"], ["Bank or MFI", "1.5% of loan", "৳4.50 / sack"], ["Buyer", "1% sourcing fee", "≈৳12 / sack"], ["Grameenphone", "call revenue share", "≈৳30 / farmer"], ["Govt, media", "glut and stock data", "subscription"]];
  for (let i = 0; i < fees.length; i++) {
    const y = by + 0.47 + i * 0.36;
    text(s8, fees[i][0], { x: M + 0.28, y, w: 1.3, h: 0.34, fontSize: 13, bold: true, color: C.text1, valign: "middle" });
    text(s8, fees[i][1], { x: M + 1.58, y, w: 1.45, h: 0.34, fontSize: 12, color: C.accent6, valign: "middle" });
    text(s8, fees[i][2], { x: M + 2.95, y, w: 1.2, h: 0.34, fontSize: 13, bold: true, color: C.text2, align: "right", valign: "middle" });
  }
  // projection chart
  const cx = M + 4.35 + 0.25;
  card(s8, cx, by, 4.3, bh, { name: "Projection card" });
  text(s8, "PROJECTION, ৳ LAKH", { x: cx + 0.28, y: by + 0.13, w: 3.8, h: 0.28, fontSize: 12, bold: true, charSpacing: 2, color: C.accent2 });
  s8.addChart(pres.charts.BAR, [
    { name: "Revenue", labels: ["Year 1", "Year 2", "Year 3"], values: [17.24, 126.3, 492.2] },
    { name: "Operating cost", labels: ["Year 1", "Year 2", "Year 3"], values: [18.5, 58, 145] },
  ], {
    x: cx + 0.1, y: by + 0.4, w: 4.1, h: bh - 0.48, barDir: "col", barGrouping: "clustered", objectName: "Projection chart",
    chartColors: [HEX.accent2, HEX.accent6], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", dataLabelFontSize: 10.5, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.accent6, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, valAxisMaxVal: 580, valAxisMinVal: 0,
    showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.dk1, legendFontFace: "+mn-lt", barGapWidthPct: 60,
  });
  // the ask
  const ax = cx + 4.3 + 0.25, aw = W - M - ax;
  card(s8, ax, by, aw, bh, { fill: C.text2, line: false, name: "Ask card" });
  text(s8, "TO START", { x: ax + 0.28, y: by + 0.13, w: aw - 0.5, h: 0.28, fontSize: 12, bold: true, charSpacing: 2, color: C.accent1 });
  text(s8, "৳20 lakh", { x: ax + 0.28, y: by + 0.4, w: aw - 0.5, h: 0.65, fontFace: THEME.headFontFace, fontSize: 32, bold: true, color: C.accent1 });
  text(s8, [
    { text: "Year 1: 2,000 farmers, 5 cold storages", options: { bullet: { indent: 14 }, breakLine: true } },
    { text: "Break-even: month 14–16", options: { bullet: { indent: 14 }, breakLine: true } },
    { text: "No storage to build, no money lent", options: { bullet: { indent: 14 } } },
  ], { x: ax + 0.28, y: by + 1.08, w: aw - 0.4, h: bh - 1.15, fontSize: 13, color: C.background1, paraSpaceAfter: 5 });
  s8.addNotes(NOTES[8]);

  // ------------------------------------------------------------ 9. impact
  const s9 = pres.addSlide({ masterName: "KV Content Light", sectionTitle: "Execution and impact" });
  header(s9, "IMPACT  ·  AI FOR SOCIAL GOOD", ["When farmers can wait, ", "the whole chain gets fairer"]);
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
    marked("Built for farmers like the one in our video, who can't read an SMS:", { bold: true }),
    { text: " " },
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
  text(s10, [{ text: "He will ask the same question. This time he gets " }, marked("the sums, the cash to wait, and a receipt with his own name on it.")],
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
