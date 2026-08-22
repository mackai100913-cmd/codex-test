const pptxgen = require("pptxgenjs");

const INK   = "1F2A24";
const SAGE  = "3F6B4E";
const SAGE2 = "6E9179";
const TERRA = "B5562C";
const WHITE = "FFFFFF";
const MUT   = "5A6B61";
const CARD  = "F1F4F1";
const CARD2 = "FBF3EE";
const LINE  = "D6DED8";

const JP = "Meiryo";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5
pres.author = "Atelier Sage";
pres.title  = "SWITCH 商品設計";

const W = 13.3, H = 7.5;
const M = 0.62;

/* ---------- helpers (fresh objects every call) ---------- */
function title(slide, text, opt) {
  opt = opt || {};
  slide.addText(text, {
    x: M, y: opt.y || 0.42, w: W - M * 2, h: 0.75,
    fontSize: opt.size || 32, bold: true, color: opt.color || INK,
    fontFace: JP, margin: 0, valign: "middle",
  });
}
function lead(slide, text, opt) {
  opt = opt || {};
  slide.addText(text, {
    x: M, y: opt.y || 1.2, w: opt.w || (W - M * 2), h: 0.5,
    fontSize: 14, color: opt.color || MUT, fontFace: JP, margin: 0, valign: "middle",
  });
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill || CARD }, line: { color: fill || CARD, width: 0 },
  });
}
function numDot(slide, x, y, n, color, d) {
  d = d || 0.46;
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color: color || SAGE }, line: { color: color || SAGE, width: 0 },
  });
  slide.addText(String(n), {
    x, y, w: d, h: d, fontSize: 15, bold: true, color: WHITE,
    align: "center", valign: "middle", fontFace: "Arial", margin: 0,
  });
}
function newSlide(dark) {
  const s = pres.addSlide();
  s.background = { color: dark ? INK : WHITE };
  return s;
}

/* =========================================================
   1. TITLE
   ========================================================= */
{
  const s = newSlide(true);
  s.addShape(pres.ShapeType.ellipse, {
    x: 9.4, y: -1.5, w: 6.2, h: 6.2,
    fill: { color: SAGE, transparency: 72 }, line: { width: 0 },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: 11.0, y: 3.6, w: 3.6, h: 3.6,
    fill: { color: TERRA, transparency: 80 }, line: { width: 0 },
  });

  s.addText("機能性D2Cサプリ ／ 第1弾プロダクト 商品設計", {
    x: M, y: 1.55, w: 8.6, h: 0.4, fontSize: 13, color: SAGE2, fontFace: JP,
    charSpacing: 2, margin: 0,
  });
  s.addText("SWITCH", {
    x: M, y: 1.98, w: 8.6, h: 1.55, fontSize: 72, bold: true, color: WHITE,
    fontFace: "Arial", charSpacing: 3, margin: 0, valign: "middle",
  });
  s.addText("食べたものを、効かせる。", {
    x: M, y: 3.56, w: 8.6, h: 0.7, fontSize: 29, color: WHITE, fontFace: JP, margin: 0, valign: "middle",
  });
  s.addText(
    "タンパク質を足さずに、食べたものを効かせる。\nだから肌も荒れず、老化も加速させない。",
    { x: M, y: 4.42, w: 8.6, h: 1.0, fontSize: 15, color: SAGE2, fontFace: JP, lineSpacing: 26, margin: 0 }
  );
  s.addText("北極星：若さを保つ（見た目＋中身）　／　2026-07", {
    x: M, y: 6.45, w: 8.6, h: 0.4, fontSize: 11, color: MUT, fontFace: JP, margin: 0,
  });
  s.addNotes("SWITCHの商品設計プレゼン。全リサーチ(Track-A〜I)を収束させた第1弾プロダクト。");
}

/* =========================================================
   2. ターゲットとインサイト
   ========================================================= */
{
  const s = newSlide();
  title(s, "誰の、何を解くのか");
  lead(s, "過酷な努力に挫折した「ライトな筋トレ・美容先行投資層」20〜40代 男女");

  const items = [
    ["①論文", "筋トレ継続動機の因子分析（日本健康教育学会誌 2019）\n継続理由の上位は 体力向上4.02・体型維持3.98・健康3.90。\n「モテたい（外観）」は主動機ではない。", SAGE],
    ["②リサーチ", "男性美容の動機は加点（モテ）でなく減点回避（清潔感）。\nZ世代男性の美容関心71.9%に対し実践は34%。\n関心と実践のギャップこそ最大の商機。", SAGE],
    ["③5WHY", "なぜ飲む→維持したい→衰えたくない→\"老けた\"判定が怖い\n→老化は不可抗力→自分で打てる介入に価値が集中\n真因：老化に能動的に手を打てている感覚に金を払う。", TERRA],
  ];
  let y = 1.95;
  items.forEach(([tag, body, col], i) => {
    card(s, M, y, W - M * 2, 1.42, i === 2 ? CARD2 : CARD);
    numDot(s, M + 0.34, y + 0.48, i + 1, col);
    s.addText(tag, {
      x: M + 1.0, y: y + 0.16, w: 2.0, h: 0.42, fontSize: 15, bold: true,
      color: col, fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(body, {
      x: M + 3.0, y: y + 0.16, w: W - M * 2 - 3.4, h: 1.1, fontSize: 12.5,
      color: INK, fontFace: JP, lineSpacing: 20, margin: 0, valign: "middle",
    });
    y += 1.58;
  });

  s.addText("▶  この商品が売るのは「筋肉」でも「肌」でもなく、コントロールできているという感覚。", {
    x: M, y: 6.72, w: W - M * 2, h: 0.45, fontSize: 14, bold: true, color: TERRA,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("3視点フレーム（論文・リサーチドリブン・5WHY）で導いた本質インサイト。");
}

/* =========================================================
   3. 3つの壁
   ========================================================= */
{
  const s = newSlide();
  title(s, "商品化を阻んだ「3つの壁」");
  lead(s, "当初構想のままでは実現不可能だった。この3つをどう解いたかが、そのまま設計になっている。");

  const walls = [
    ["壁 01", "ニキビ予防は\n言えない", "ニキビは皮膚疾患。\n機能性表示食品は疾病の\n予防・治療を暗示する\n表現が禁止されている。", "消費者庁ガイドライン"],
    ["壁 02", "極小粒に筋肉成分は\n入らない", "1,000mg超でカプセル3〜4粒。\nロイシン2.5g / HMB3g /\nクレアチン3g / コラーゲン5g\n— 物理的に1つも入らない。", "OEM各社ヒアリング"],
    ["壁 03", "筋肉と抗老化が\n矛盾する", "ロイシンはmTORを活性化し\n筋肉を作る。しかしmTORの\n慢性活性化は老化を早める。\n同じ経路が善であり悪。", "Nature ダイジェスト"],
  ];
  const cw = 3.92, gap = 0.42;
  walls.forEach((w4, i) => {
    const x = M + i * (cw + gap);
    card(s, x, 1.95, cw, 4.35, CARD);
    s.addText(w4[0], {
      x: x + 0.32, y: 2.18, w: cw - 0.6, h: 0.35, fontSize: 12, bold: true,
      color: TERRA, fontFace: "Arial", charSpacing: 2, margin: 0,
    });
    s.addText(w4[1], {
      x: x + 0.32, y: 2.58, w: cw - 0.6, h: 1.0, fontSize: 19, bold: true,
      color: INK, fontFace: JP, lineSpacing: 27, margin: 0,
    });
    s.addText(w4[2], {
      x: x + 0.32, y: 3.72, w: cw - 0.6, h: 1.6, fontSize: 12.5, color: INK,
      fontFace: JP, lineSpacing: 21, margin: 0,
    });
    s.addText(w4[3], {
      x: x + 0.32, y: 5.72, w: cw - 0.6, h: 0.34, fontSize: 10.5, color: MUT,
      fontFace: JP, margin: 0,
    });
  });

  s.addText("この3つを正面から解いた結果、コンセプトが一本に定まった。", {
    x: M, y: 6.62, w: W - M * 2, h: 0.45, fontSize: 14, bold: true, color: SAGE,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("壁を隠さず、解き方を設計の中心に据えたことが差別化になっている。");
}

/* =========================================================
   4. 壁①の解
   ========================================================= */
{
  const s = newSlide();
  numDot(s, M, 0.52, 1, TERRA, 0.52);
  s.addText("言えない言葉を、強みに変える", {
    x: M + 0.78, y: 0.42, w: W - M * 2 - 0.78, h: 0.75, fontSize: 32, bold: true,
    color: INK, fontFace: JP, margin: 0, valign: "middle",
  });
  lead(s, "壁① ニキビ予防は法規上まったく言えない");

  card(s, M, 1.95, 6.0, 2.05, CARD2);
  s.addText("法的な着地点", {
    x: M + 0.34, y: 2.16, w: 5.3, h: 0.36, fontSize: 13, bold: true, color: TERRA, fontFace: JP, margin: 0,
  });
  s.addText(
    "亜鉛・ビタミンB6 の栄養機能表示\n「皮膚や粘膜の健康維持を助ける栄養素です」\n\n定型文として合法的に言える。",
    { x: M + 0.34, y: 2.56, w: 5.3, h: 1.3, fontSize: 13.5, color: INK, fontFace: JP, lineSpacing: 22, margin: 0 }
  );

  card(s, M + 6.42, 1.95, 6.0, 2.05, CARD);
  s.addText("さらに強い、引き算の訴求", {
    x: M + 6.76, y: 2.16, w: 5.3, h: 0.36, fontSize: 13, bold: true, color: SAGE, fontFace: JP, margin: 0,
  });
  s.addText(
    "「粉を飲まないから、そもそも荒れない」\n\nプロテインの大量摂取で肌が荒れた層に\n直接刺さる、構造的な優位。",
    { x: M + 6.76, y: 2.56, w: 5.3, h: 1.3, fontSize: 13.5, color: INK, fontFace: JP, lineSpacing: 22, margin: 0 }
  );

  card(s, M, 4.28, W - M * 2, 1.95, CARD);
  s.addText("なぜ競合はまねできないのか", {
    x: M + 0.36, y: 4.5, w: 11.4, h: 0.4, fontSize: 15, bold: true, color: INK, fontFace: JP, margin: 0,
  });
  s.addText(
    [
      { text: "プロテイン・EAA企業は「量を売る」ビジネスモデル。", options: { breakLine: true, bullet: true } },
      { text: "したがって「量を減らす」提案は、自社の売上構造そのものの否定になる。", options: { breakLine: true, bullet: true } },
      { text: "引き算の訴求は、後発の大手ほど追随しにくい。", options: { bullet: true } },
    ],
    { x: M + 0.36, y: 4.98, w: 11.4, h: 1.15, fontSize: 13.5, color: INK, fontFace: JP, paraSpaceAfter: 6, margin: 0 }
  );

  s.addText("×  ニキビが治る・防ぐ　　　○  皮膚や粘膜の健康維持を助ける", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: TERRA,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("疾病表現の禁止を逆手に取り、引き算の訴求へ転換した。");
}

/* =========================================================
   5. 壁②の解 — 最大の突破口
   ========================================================= */
{
  const s = newSlide();
  numDot(s, M, 0.52, 2, SAGE, 0.52);
  s.addText("足さずに、効かせる", {
    x: M + 0.78, y: 0.42, w: W - M * 2 - 0.78, h: 0.75, fontSize: 32, bold: true,
    color: INK, fontFace: JP, margin: 0, valign: "middle",
  });
  lead(s, "壁② 極小タブレットに筋肉の材料は物理的に入らない　→　発想を反転させた");

  // before / after
  card(s, M, 1.95, 5.55, 2.5, CARD);
  s.addText("従来の発想", {
    x: M + 0.32, y: 2.14, w: 4.9, h: 0.36, fontSize: 12, bold: true, color: MUT, fontFace: JP, margin: 0,
  });
  s.addText("材料を供給する", {
    x: M + 0.32, y: 2.52, w: 4.9, h: 0.5, fontSize: 22, bold: true, color: MUT, fontFace: JP, margin: 0,
  });
  s.addText("ロイシン2.5g / HMB3g / クレアチン3g\n→ 粉をがぶ飲みするしかない\n→ 肌荒れ・お腹の不調・面倒", {
    x: M + 0.32, y: 3.08, w: 4.9, h: 1.2, fontSize: 12.5, color: MUT, fontFace: JP, lineSpacing: 21, margin: 0,
  });

  s.addShape(pres.ShapeType.rightArrow, {
    x: 6.32, y: 2.92, w: 0.72, h: 0.52, fill: { color: TERRA }, line: { width: 0 },
  });

  card(s, 7.15, 1.95, 5.53, 2.5, CARD2);
  s.addText("SWITCH の発想", {
    x: 7.47, y: 2.14, w: 4.9, h: 0.36, fontSize: 12, bold: true, color: TERRA, fontFace: JP, margin: 0,
  });
  s.addText("食べた材料を効かせる", {
    x: 7.47, y: 2.52, w: 4.9, h: 0.5, fontSize: 22, bold: true, color: INK, fontFace: JP, margin: 0,
  });
  s.addText("ビタミンD・B6・亜鉛はすべてmg・μg単位\n→ 小粒2粒に収まる\n→ 制約と価値提案が完全に一致した", {
    x: 7.47, y: 3.08, w: 4.9, h: 1.2, fontSize: 12.5, color: INK, fontFace: JP, lineSpacing: 21, margin: 0,
  });

  // mechanism row
  const mech = [
    ["ビタミンD", "mTOR（筋タンパク合成のスイッチ）を活性化し、食事のタンパク質が効きやすい体にする"],
    ["ビタミンB6", "アミノ酸代謝に必須。食べたタンパク質を使える形に回す"],
    ["亜鉛", "タンパク質合成に関与。あわせて皮膚の健康維持も担う"],
  ];
  let mx = M;
  const mw = 3.92;
  mech.forEach(([k, v], i) => {
    card(s, mx, 4.72, mw, 1.52, CARD);
    s.addText(k, {
      x: mx + 0.3, y: 4.9, w: mw - 0.6, h: 0.36, fontSize: 14, bold: true, color: SAGE, fontFace: JP, margin: 0,
    });
    s.addText(v, {
      x: mx + 0.3, y: 5.28, w: mw - 0.6, h: 0.85, fontSize: 11.5, color: INK, fontFace: JP, lineSpacing: 18, margin: 0,
    });
    mx += mw + 0.42;
  });

  s.addText("これは発注者が最初に語っていたコア価値「飲むだけで質の良い食事に変わる」そのものだった。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: TERRA,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("最大の突破口。物理的制約が、むしろコンセプトを研ぎ澄ませた。");
}

/* =========================================================
   6. 壁③の解
   ========================================================= */
{
  const s = newSlide();
  numDot(s, M, 0.52, 3, SAGE, 0.52);
  s.addText("アクセルを踏み続けない、という優位", {
    x: M + 0.78, y: 0.42, w: W - M * 2 - 0.78, h: 0.75, fontSize: 32, bold: true,
    color: INK, fontFace: JP, margin: 0, valign: "middle",
  });
  lead(s, "壁③ ロイシン（mTORのアクセル）と抗老化（mTORのブレーキ）は同じ経路で矛盾する");

  card(s, M, 1.95, W - M * 2, 1.62, CARD);
  s.addText("矛盾の正体", {
    x: M + 0.36, y: 2.14, w: 11.4, h: 0.36, fontSize: 14, bold: true, color: INK, fontFace: JP, margin: 0,
  });
  s.addText(
    "ロイシンは mTORC1 を活性化して筋タンパク合成を促す（アクセル）。一方で mTOR の慢性活性化は老化を早めるとされ、\nタンパク質・BCAA の制限はむしろ寿命を延ばしうる。つまり同じスイッチが、筋肉には善・長寿には悪として働く。",
    { x: M + 0.36, y: 2.52, w: 11.4, h: 0.9, fontSize: 13, color: INK, fontFace: JP, lineSpacing: 21, margin: 0 }
  );

  card(s, M, 3.82, 5.95, 2.4, CARD);
  s.addText("既存のプロテイン / EAA", {
    x: M + 0.32, y: 4.02, w: 5.3, h: 0.36, fontSize: 13, bold: true, color: MUT, fontFace: JP, margin: 0,
  });
  s.addText("大量のアミノ酸を常時流し込む\n\n＝ mTOR のアクセルを踏みっぱなし\n抗老化の観点では不利になりうる", {
    x: M + 0.32, y: 4.42, w: 5.3, h: 1.5, fontSize: 13, color: MUT, fontFace: JP, lineSpacing: 22, margin: 0,
  });

  card(s, M + 6.37, 3.82, 5.95, 2.4, CARD2);
  s.addText("SWITCH", {
    x: M + 6.69, y: 4.02, w: 5.3, h: 0.36, fontSize: 13, bold: true, color: TERRA, fontFace: "Arial", margin: 0,
  });
  s.addText("アミノ酸を供給しない設計\n\n＝ そもそも mTOR を踏み続けない\n食事が入ったときだけ効率を上げる（間欠的）", {
    x: M + 6.69, y: 4.42, w: 5.3, h: 1.5, fontSize: 13, color: INK, fontFace: JP, lineSpacing: 22, margin: 0,
  });

  s.addText("▶  これは偶然ではなく、この商品の抗老化上の優位性である。「増やす」ではなく「賢く使い分ける」。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: TERRA,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("3つ目の壁も、設計上の優位に転換した。");
}

/* =========================================================
   7. 処方（チャート）
   ========================================================= */
{
  const s = newSlide();
  title(s, "処方設計 ─ 1日2粒");
  lead(s, "有効成分 合計 約620mg。賦形剤込みで 1粒400mg × 2粒 に収まる。");

  s.addChart(
    pres.ChartType.doughnut,
    [{
      name: "配合",
      labels: ["ニュートロックスサン 250mg", "ビタミンC（リポソーム）200mg", "BJ抽出物 150mg", "亜鉛・B6・D 約20mg"],
      values: [250, 200, 150, 20],
    }],
    {
      x: 0.5, y: 1.85, w: 5.0, h: 4.5,
      chartColors: [TERRA, SAGE2, SAGE, INK],
      holeSize: 55,
      showLegend: true, legendPos: "b", legendFontSize: 10, legendFontFace: JP, legendColor: INK,
      showValue: false,
      showTitle: false,
      dataBorder: { pt: 2, color: WHITE },
    }
  );

  const rows = [
    ["ブラックジンジャー由来PMF", "12mg", "脂肪の消費・脚の筋肉の維持", "機能性関与成分 ①", TERRA],
    ["ニュートロックスサン", "250mg", "紫外線で生じる活性酸素から肌を守る", "機能性関与成分 ②", TERRA],
    ["亜鉛", "10mg", "皮膚の健康維持・タンパク質合成", "栄養機能表示", SAGE],
    ["ビタミンB6", "1.4mg", "皮膚の健康維持・アミノ酸代謝", "栄養機能表示", SAGE],
    ["ビタミンD", "25μg", "mTOR活性化＝食事タンパクを効かせる", "栄養機能表示", SAGE],
    ["ビタミンC（リポソーム化）", "200mg", "コラーゲン生成・抗酸化", "配合成分", MUT],
  ];
  let ry = 1.95;
  rows.forEach((r) => {
    card(s, 5.95, ry, 6.75, 0.68, CARD);
    s.addText(r[0], {
      x: 6.18, y: ry + 0.05, w: 2.65, h: 0.32, fontSize: 11.5, bold: true, color: INK,
      fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(r[3], {
      x: 6.18, y: ry + 0.35, w: 2.65, h: 0.26, fontSize: 8.5, color: r[4],
      fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(r[1], {
      x: 8.85, y: ry + 0.04, w: 0.85, h: 0.6, fontSize: 12, bold: true, color: r[4],
      fontFace: "Arial", margin: 0, valign: "middle",
    });
    s.addText(r[2], {
      x: 9.72, y: ry + 0.04, w: 2.75, h: 0.6, fontSize: 10.5, color: MUT,
      fontFace: JP, margin: 0, valign: "middle",
    });
    ry += 0.76;
  });

  s.addText("量が必要な成分（アミノ酸類）を意図的に外した。入っているのは「スイッチ」と「盾」だけ。", {
    x: M, y: 6.62, w: W - M * 2, h: 0.45, fontSize: 13.5, bold: true, color: SAGE,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("関与成分は2つ。残りは栄養機能表示と配合成分で構成する。");
}

/* =========================================================
   8. 言える / 言えない
   ========================================================= */
{
  const s = newSlide();
  title(s, "言える言葉と、言えない言葉");
  lead(s, "薬機法・景表法リスクを制作前に封じる。この表を社内ルールとして配布する。");

  card(s, M, 1.95, 5.95, 3.6, CARD2);
  s.addText("×  使ってはいけない", {
    x: M + 0.34, y: 2.16, w: 5.3, h: 0.44, fontSize: 17, bold: true, color: TERRA, fontFace: JP, margin: 0,
  });
  s.addText(
    [
      { text: "ニキビが治る / ニキビを防ぐ", options: { breakLine: true, bullet: true } },
      { text: "筋肉が増える / バルクアップする", options: { breakLine: true, bullet: true } },
      { text: "日焼けしない / SPF・紫外線をブロック", options: { breakLine: true, bullet: true } },
      { text: "痩せる / ダイエットできる", options: { breakLine: true, bullet: true } },
      { text: "疾病の予防・治療を暗示するすべての表現", options: { bullet: true } },
    ],
    { x: M + 0.34, y: 2.72, w: 5.3, h: 2.6, fontSize: 14, color: INK, fontFace: JP, paraSpaceAfter: 13, margin: 0, valign: 'top' }
  );

  card(s, M + 6.37, 1.95, 5.95, 3.6, CARD);
  s.addText("○  使ってよい", {
    x: M + 6.71, y: 2.16, w: 5.3, h: 0.44, fontSize: 17, bold: true, color: SAGE, fontFace: JP, margin: 0,
  });
  s.addText(
    [
      { text: "皮膚や粘膜の健康維持を助ける（亜鉛・B6）", options: { breakLine: true, bullet: true } },
      { text: "脚の筋肉の維持（BJ由来PMF）", options: { breakLine: true, bullet: true } },
      { text: "日常活動時のエネルギー代謝で脂肪を消費しやすくする", options: { breakLine: true, bullet: true } },
      { text: "紫外線刺激から肌を守る（要・届出DB照合）", options: { breakLine: true, bullet: true } },
      { text: "塗る日焼け止めの「代替」ではなく「補完」と明記", options: { bullet: true } },
    ],
    { x: M + 6.71, y: 2.72, w: 5.3, h: 2.6, fontSize: 14, color: INK, fontFace: JP, paraSpaceAfter: 13, margin: 0, valign: 'top' }
  );

  s.addText("誠実さを、信頼の堀にする。紅麹以降の市場では透明性そのものが競争優位になる。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: INK,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("全広告はこの表に従って法務チェックを通す。");
}

/* =========================================================
   9. ビジネスモデル
   ========================================================= */
{
  const s = newSlide();
  title(s, "売り方は、他業界から借りる");
  lead(s, "サプリ競合は無視。遠い業界の顧客ハック構造だけを5つ転用した。");

  const models = [
    ["Duolingo", "月7,400万人の約70%が1週間以上ストリークを維持。継続＝資産、フリーズ＝保険。", "飲んだら1タップ。連続記録が伸びアバターが育つ。月2回のフリーズで責めずに戻す。", SAGE],
    ["ボトルキープ", "名入れボトルを店に預ける＝置き資産と再来店予約を同時に作る。", "初回に名入れ「マイ・キープ缶」。以降はリフィルのみ。解約＝自分の缶を空にする痛み。", TERRA],
    ["オイシックス", "ハイタッチ対応は支援でなく伴走。入口で小さな成功体験を刻む。", "「食事制限しなくて大丈夫。あなたの“まあいっか”を栄養で埋めます」と免罪符を配る。", SAGE],
    ["Calm", "儀式化＋履歴の可視化。年6,500円〜終身42,900円の情緒課金。", "飲む行為を3秒の朝の儀式に。「2ヶ月で体は変わる。今日はその1日目」＋積立プラン。", TERRA],
    ["マクドナルド × 松下 × 資生堂", "料理を標準化製造に再定義。新概念は対面教育網で普及させる。", "毎日1タップ3秒のミッションに標準化。新概念は指名制アドバイザーのLINE伴走で教育。", SAGE],
  ];

  let my = 1.95;
  models.forEach((m, i) => {
    card(s, M, my, W - M * 2, 0.80, i % 2 === 1 ? CARD2 : CARD);
    s.addText(m[0], {
      x: M + 0.3, y: my + 0.04, w: 2.35, h: 0.72, fontSize: 12.5, bold: true,
      color: m[3], fontFace: JP, margin: 0, valign: "middle", lineSpacing: 17,
    });
    s.addText(m[1], {
      x: M + 2.75, y: my + 0.04, w: 4.15, h: 0.72, fontSize: 10.5, color: MUT,
      fontFace: JP, lineSpacing: 16, margin: 0, valign: "middle",
    });
    s.addShape(pres.ShapeType.rightArrow, {
      x: M + 7.0, y: my + 0.28, w: 0.3, h: 0.24,
      fill: { color: m[3] }, line: { width: 0 },
    });
    s.addText(m[2], {
      x: M + 7.48, y: my + 0.04, w: 4.5, h: 0.72, fontSize: 10.5, color: INK,
      fontFace: JP, lineSpacing: 16, margin: 0, valign: "middle",
    });
    my += 0.85;
  });

  s.addText("▶  この商品は「サプリ」ではなく、3秒で完了する“若さの積立”デイリーミッション＋指名制の伴走。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: TERRA,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("サプリ業界の常識からは出てこない組み合わせ。ここが模倣されにくさの源泉。");
}

/* =========================================================
   10. 顧客体験
   ========================================================= */
{
  const s = newSlide();
  title(s, "顧客体験は、3秒で終わる");
  lead(s, "タイパ至上の層は、効果より前に「面倒くささ」で脱落する。だから考える余地を消す。");

  const steps = [
    ["朝", "洗面台の\n自分の名前入りの缶が\n目に入る"],
    ["飲む", "2粒を水で。\n粉を溶かす手間はゼロ"],
    ["1タップ", "スマホで記録。\nこれがデイリーミッション"],
    ["育つ", "アバターが成長し\n「7日連続。積み上がっています」"],
  ];
  const sw = 2.85, sg = 0.42;
  steps.forEach((st, i) => {
    const x = M + i * (sw + sg);
    card(s, x, 2.05, sw, 2.35, CARD);
    numDot(s, x + 0.3, 2.28, i + 1, i === 3 ? TERRA : SAGE, 0.5);
    s.addText(st[0], {
      x: x + 0.95, y: 2.28, w: sw - 1.2, h: 0.5, fontSize: 17, bold: true,
      color: INK, fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(st[1], {
      x: x + 0.3, y: 2.95, w: sw - 0.6, h: 1.25, fontSize: 12, color: INK,
      fontFace: JP, lineSpacing: 19, margin: 0,
    });
    if (i < 3) {
      s.addShape(pres.ShapeType.rightArrow, {
        x: x + sw + 0.06, y: 3.05, w: 0.3, h: 0.28,
        fill: { color: SAGE2 }, line: { width: 0 },
      });
    }
  });

  card(s, M, 4.72, W - M * 2, 1.5, CARD2);
  s.addText("声のかけ方（トーン＆マナー）", {
    x: M + 0.36, y: 4.9, w: 11.4, h: 0.36, fontSize: 14, bold: true, color: TERRA, fontFace: JP, margin: 0,
  });
  s.addText(
    "初回：「食事制限は、しなくて大丈夫です」　／　飲み忘れ：「おかえりなさい。今日から、また積み上げましょう」\n" +
    "効果を聞かれたら：「2ヶ月で体は変わります。今日はその◯日目です」　／　訴求：「モテる体に」ではなく「自分で管理できている、という感覚を」",
    { x: M + 0.36, y: 5.3, w: 11.4, h: 0.8, fontSize: 12, color: INK, fontFace: JP, lineSpacing: 20, margin: 0 }
  );

  s.addText("責める表現は一切使わない。数値は2階層目に隠し、トップは「今日やったか」だけを見せる。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 13.5, bold: true, color: SAGE,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("Apple流の1画面1ジョブ。ホームには今日の1タップ以外を置かない。");
}

/* =========================================================
   11. 価格
   ========================================================= */
{
  const s = newSlide();
  title(s, "価格とユニットエコノミクス");
  lead(s, "初期ハードルを下げてLTVを取る。主力は3ヶ月コース。");

  const plans = [
    ["初回", "¥2,480", "＋名入れキープ缶\n心理的・金銭的ハードルを下げる", SAGE, false],
    ["3ヶ月コース", "¥13,440", "月あたり¥4,480 ／ 主力プラン\n3ヶ月まとめでLTV約1.5倍の事例", TERRA, true],
    ["通常（月額）", "¥4,980", "1日あたり約166円", SAGE, false],
    ["年間プラン", "¥49,800", "「若さの積立」情緒コミット", SAGE, false],
  ];
  const pw = 2.95, pg = 0.28;
  plans.forEach((p, i) => {
    const x = M + i * (pw + pg);
    const y = p[4] ? 1.9 : 2.05;
    const h = p[4] ? 2.6 : 2.3;
    card(s, x, y, pw, h, p[4] ? CARD2 : CARD);
    s.addText(p[0], {
      x: x + 0.26, y: y + 0.2, w: pw - 0.52, h: 0.36, fontSize: 13, bold: true,
      color: p[3], fontFace: JP, margin: 0,
    });
    s.addText(p[1], {
      x: x + 0.26, y: y + 0.62, w: pw - 0.52, h: 0.72, fontSize: p[4] ? 34 : 30, bold: true,
      color: INK, fontFace: "Arial", margin: 0, valign: "middle",
    });
    s.addText(p[2], {
      x: x + 0.26, y: y + 1.42, w: pw - 0.52, h: 0.9, fontSize: 11, color: MUT,
      fontFace: JP, lineSpacing: 17, margin: 0,
    });
  });

  const kpis = [
    ["月次解約率", "3%以下", "D2C定期の理想水準（標準3〜5%）"],
    ["原価率", "30%以下", "事業条件。成否はほぼ原料単価で決まる"],
    ["獲得目標", "月1,000件", "CPA ¥10,000"],
  ];
  let kx = M;
  const kw = 3.92;
  kpis.forEach((k) => {
    card(s, kx, 4.85, kw, 1.4, CARD);
    s.addText(k[0], {
      x: kx + 0.3, y: 5.0, w: kw - 0.6, h: 0.32, fontSize: 11.5, color: MUT, fontFace: JP, margin: 0,
    });
    s.addText(k[1], {
      x: kx + 0.3, y: 5.32, w: kw - 0.6, h: 0.52, fontSize: 24, bold: true, color: SAGE,
      fontFace: "Arial", margin: 0, valign: "middle",
    });
    s.addText(k[2], {
      x: kx + 0.3, y: 5.85, w: kw - 0.6, h: 0.3, fontSize: 10, color: MUT, fontFace: JP, margin: 0,
    });
    kx += kw + 0.42;
  });

  s.addText("注意　原価率30%の成否は、ほぼニュートロックスサンの単価で決まる。最初に潰すべき唯一の未知数。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: TERRA,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("価格は暫定。P0の見積もり結果で最終確定する。");
}

/* =========================================================
   12. ローンチ計画
   ========================================================= */
{
  const s = newSlide();
  title(s, "ローンチまで 6〜8ヶ月");
  lead(s, "届出は販売の60営業日前までに提出する必要がある。ここが全体のクリティカルパス。");

  const phases = [
    ["P0", "見積もり", "〜2週", "原料3社・OEM3社へ依頼"],
    ["P1", "処方確定", "〜1.5ヶ月", "配合量・粒サイズ・リポソーム可否"],
    ["P2", "届出準備", "〜4ヶ月", "SR収集・書類作成・提出"],
    ["P3", "試作・官能", "並行", "モニター20名でNGゼロ"],
    ["P4", "アプリ / LINE", "並行", "ストリーク・1タップ・免罪符配信"],
    ["P5", "パッケージ", "〜5ヶ月", "名入れキープ缶＋リフィル"],
    ["P6", "ローンチ", "6〜8ヶ月", "初回¥2,480で獲得開始"],
  ];

  let py = 1.95;
  phases.forEach((p, i) => {
    const isLast = i === phases.length - 1;
    card(s, M, py, W - M * 2, 0.62, isLast ? CARD2 : CARD);
    s.addShape(pres.ShapeType.ellipse, {
      x: M + 0.24, y: py + 0.13, w: 0.36, h: 0.36,
      fill: { color: isLast ? TERRA : SAGE }, line: { width: 0 },
    });
    s.addText(p[0], {
      x: M + 0.24, y: py + 0.13, w: 0.36, h: 0.36, fontSize: 10.5, bold: true, color: WHITE,
      align: "center", valign: "middle", fontFace: "Arial", margin: 0,
    });
    s.addText(p[1], {
      x: M + 0.78, y: py + 0.06, w: 2.4, h: 0.5, fontSize: 14, bold: true, color: INK,
      fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(p[2], {
      x: M + 3.2, y: py + 0.06, w: 1.7, h: 0.5, fontSize: 12.5, bold: true,
      color: isLast ? TERRA : SAGE, fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(p[3], {
      x: M + 5.0, y: py + 0.06, w: 6.8, h: 0.5, fontSize: 12, color: MUT,
      fontFace: JP, margin: 0, valign: "middle",
    });
    py += 0.7;
  });

  s.addNotes("P2の届出準備が最長。P0の見積もりを最優先で走らせる。");
}

/* =========================================================
   13. リスクと次アクション
   ========================================================= */
{
  const s = newSlide();
  title(s, "リスクと、いま打つ手");

  card(s, M, 1.4, 6.2, 4.85, CARD);
  s.addText("主要リスク", {
    x: M + 0.34, y: 1.6, w: 5.5, h: 0.4, fontSize: 16, bold: true, color: INK, fontFace: JP, margin: 0,
  });
  const risks = [
    ["高", "ニキビ訴求が薬機法に抵触", "禁止ワード表を社内ルール化。全広告を法務チェック", TERRA],
    ["高", "原料が高額で原価率30%超", "P0で即見積もり。超えるなら日焼け訴求を第2弾へ", TERRA],
    ["中", "「飲む日焼け止めは効かない」批判", "塗る型の代替でなく補完と明記。誠実さを堀にする", SAGE],
    ["中", "実感が遅く2ヶ月以内に解約", "3ヶ月コースを主力に。期待値を先に握る", SAGE],
    ["中", "機能性表示食品への不信（紅麹以降）", "GMP・第三者検査・原産地を全開示", SAGE],
  ];
  let riy = 2.08;
  risks.forEach((r) => {
    s.addShape(pres.ShapeType.roundRect, {
      x: M + 0.34, y: riy + 0.06, w: 0.46, h: 0.3, rectRadius: 0.06,
      fill: { color: r[3] }, line: { width: 0 },
    });
    s.addText(r[0], {
      x: M + 0.34, y: riy + 0.06, w: 0.46, h: 0.3, fontSize: 10, bold: true, color: WHITE,
      align: "center", valign: "middle", fontFace: JP, margin: 0,
    });
    s.addText(r[1], {
      x: M + 0.92, y: riy, w: 5.1, h: 0.34, fontSize: 12.5, bold: true, color: INK,
      fontFace: JP, margin: 0, valign: "middle",
    });
    s.addText(r[2], {
      x: M + 0.92, y: riy + 0.34, w: 5.1, h: 0.42, fontSize: 10.5, color: MUT,
      fontFace: JP, margin: 0, valign: "middle",
    });
    riy += 0.83;
  });

  card(s, M + 6.62, 1.4, 5.7, 4.85, CARD2);
  s.addText("次アクション（P0）", {
    x: M + 6.96, y: 1.6, w: 5.0, h: 0.4, fontSize: 16, bold: true, color: TERRA, fontFace: JP, margin: 0,
  });
  const acts = [
    "ニュートロックスサン供給元へ単価・最小ロット照会  ← 最優先",
    "丸善製薬へ BJ抽出物の見積もり依頼（150mg/日）",
    "OEM 3社へ小粒2粒設計＋リポソームVC可否を相談",
    "機能性表示食品DBで既存届出の表現を実地照合",
    "名入れ金属缶のサプライヤー探索",
    "禁止ワード表を確定し、社内・制作会社へ配布",
  ];
  let ay = 2.14;
  acts.forEach((a, i) => {
    s.addShape(pres.ShapeType.ellipse, {
      x: M + 6.96, y: ay + 0.05, w: 0.32, h: 0.32,
      fill: { color: i === 0 ? TERRA : SAGE }, line: { width: 0 },
    });
    s.addText(String(i + 1), {
      x: M + 6.96, y: ay + 0.05, w: 0.32, h: 0.32, fontSize: 9, bold: true, color: WHITE,
      align: "center", valign: "middle", fontFace: "Arial", margin: 0,
    });
    s.addText(a, {
      x: M + 7.34, y: ay, w: 4.7, h: 0.62, fontSize: 12, color: INK,
      fontFace: JP, lineSpacing: 18, margin: 0, valign: "middle",
      bold: i === 0,
    });
    ay += 0.72;
  });

  s.addText("机上調査はここが限界。次は「現実」の見積もりで、唯一の未知数を潰す。", {
    x: M, y: 6.55, w: W - M * 2, h: 0.5, fontSize: 14, bold: true, color: INK,
    fontFace: JP, margin: 0, valign: "middle",
  });
  s.addNotes("リスクは重大度順。P0の1番目が全体の意思決定を左右する。");
}

/* =========================================================
   14. CLOSING
   ========================================================= */
{
  const s = newSlide(true);
  s.addShape(pres.ShapeType.ellipse, {
    x: 9.8, y: 4.5, w: 5.2, h: 5.2,
    fill: { color: SAGE, transparency: 76 }, line: { width: 0 },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: 10.6, y: -1.2, w: 4.4, h: 4.4,
    fill: { color: TERRA, transparency: 82 }, line: { width: 0 },
  });

  s.addText("SWITCH", {
    x: M, y: 1.45, w: 11.0, h: 1.0, fontSize: 44, bold: true, color: WHITE,
    fontFace: "Arial", charSpacing: 3, margin: 0,
  });
  s.addText(
    "タンパク質を足さずに、\n食べたものを効かせる。",
    { x: M, y: 2.55, w: 11.0, h: 1.7, fontSize: 40, bold: true, color: WHITE, fontFace: JP, lineSpacing: 56, margin: 0 }
  );
  s.addText("だから肌も荒れず、老化も加速させない。", {
    x: M, y: 4.35, w: 11.0, h: 0.6, fontSize: 20, color: SAGE2, fontFace: JP, margin: 0,
  });
  s.addText(
    "プロテイン企業は「量」を売るビジネスモデルであるがゆえに、この引き算にはついてこられない。",
    { x: M, y: 5.35, w: 11.0, h: 0.5, fontSize: 14, color: MUT, fontFace: JP, margin: 0 }
  );
  s.addText("Atelier Sage　／　北極星：若さを保つ（見た目＋中身）", {
    x: M, y: 6.5, w: 11.0, h: 0.4, fontSize: 11, color: MUT, fontFace: JP, margin: 0,
  });
  s.addNotes("クロージング。競合が構造上まねできない理由を最後に置く。");
}

pres.writeFile({ fileName: "SWITCH_商品設計.pptx" }).then((f) => console.log("saved:", f));
