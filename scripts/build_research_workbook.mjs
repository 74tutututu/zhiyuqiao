import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const dataDir = path.join(root, "05_匿名化数据");
const analysisDir = path.join(root, "06_数据分析");
await fs.mkdir(dataDir, { recursive: true });
await fs.mkdir(analysisDir, { recursive: true });

function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const random = mulberry32(20260827);
const normal = () => {
  const u = Math.max(random(), 1e-12);
  const v = random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
};
const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
const rating = (mean, sd = 0.72) => Math.round(clamp(mean + normal() * sd, 1, 5));
const pick = (items) => items[Math.floor(random() * items.length)];

const languages = ["Português", "English", "Español", "日本語", "한국어", "Русский", "العربية"];
const levels = ["HSK1", "HSK1", "HSK2", "HSK2", "HSK3", "HSK3", "HSK4"];
const identities = ["来华国际学生", "来华国际学生", "海外中文学习者", "在沪外籍人士"];
const headers = [
  "respondent_id", "data_class", "consent", "group", "native_language", "hsk_level", "identity",
  "shanghai_experience", "pre_culture", "post_culture", "culture_gain", "relevance",
  "cultural_clarity", "language_accessibility", "usability", "task_correct", "completion_sec",
  "trust", "reuse_intent", "quality_flag",
];

const rows = [];
for (let index = 0; index < 120; index += 1) {
  const group = index % 2 === 0 ? "智语桥组" : "常规检索组";
  const pre = rating(2.6, 0.85);
  const gainMean = group === "智语桥组" ? 1.05 : 0.42;
  const post = Math.round(clamp(pre + gainMean + normal() * 0.68, 1, 5));
  const tool = group === "智语桥组";
  const taskCorrect = random() < (tool ? 0.80 : 0.62) ? 1 : 0;
  const completion = Math.round(clamp((tool ? 202 : 278) + normal() * 55, 90, 480));
  rows.push([
    `SYN-${String(index + 1).padStart(3, "0")}`,
    "SYNTHETIC",
    "演示同意",
    group,
    pick(languages),
    pick(levels),
    pick(identities),
    pick(["从未", "短期到访", "在沪不足1年", "在沪1年以上"]),
    pre,
    post,
    post - pre,
    tool ? rating(4.15) : rating(3.45),
    tool ? rating(4.10) : rating(3.30),
    tool ? rating(4.05) : rating(3.42),
    tool ? rating(4.18) : rating(3.52),
    taskCorrect,
    completion,
    tool ? rating(3.95) : rating(3.28),
    tool ? rating(4.10) : rating(3.38),
    "PASS",
  ]);
}

function csvEscape(value) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

const csv = [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\r\n") + "\r\n";
const csvPath = path.join(dataDir, "智语桥_合成验证数据_SYNTHETIC.csv");
await fs.writeFile(csvPath, "\ufeff" + csv, "utf8");

const workbook = Workbook.create();
const guide = workbook.worksheets.add("使用说明");
const codebook = workbook.worksheets.add("编码本");
const raw = workbook.worksheets.add("合成验证数据");
const summary = workbook.worksheets.add("分析摘要");

const dark = "#7A1422";
const accent = "#C6212F";
const pale = "#FBECEE";
const gold = "#C99837";
const line = "#E7CDD1";
const bodyFont = { name: "宋体", size: 10, color: "#2F2527" };
const headerFont = { name: "宋体", size: 10, bold: true, color: "#FFFFFF" };

for (const sheet of [guide, codebook, raw, summary]) {
  sheet.showGridLines = false;
}

guide.getRange("A1:F1").merge();
guide.getRange("A1").values = [["智语桥调研与分析工作簿｜合成验证版"]];
guide.getRange("A1:F1").format = { fill: dark, font: { name: "宋体", size: 16, bold: true, color: "#FFFFFF" }, rowHeight: 34, verticalAlignment: "center" };
guide.getRange("A3:B9").values = [
  ["数据属性", "SYNTHETIC：仅用于验证研究设计、公式、图表和申报材料版式，不是实际调研结果。"],
  ["随机种子", "20260827，可复现生成120条演示记录。"],
  ["替换方法", "将真实匿名数据按同名列粘贴到“合成验证数据”，更新数据行范围后核对摘要公式。"],
  ["主比较", "智语桥组 vs 常规检索组：文化理解增量、任务正确率、完成时长。"],
  ["正式报告", "删除或明确标注合成结果；不得写成已完成真实用户实验。"],
  ["隐私要求", "真实联系方式和录音不得进入本工作簿或公开仓库。"],
  ["生成时间", "2026-08-27"],
];
guide.getRange("A3:A9").format = { fill: pale, font: { name: "宋体", size: 10, bold: true, color: dark } };
guide.getRange("B3:B9").format = { font: bodyFont, wrapText: true };
guide.getRange("A3:B9").format.borders = { preset: "inside", style: "thin", color: line };
guide.getRange("A:A").format.columnWidth = 18;
guide.getRange("B:B").format.columnWidth = 78;
guide.getRange("3:9").format.rowHeight = 34;

const definitions = [
  ["变量", "中文含义", "类型/范围", "正式采集说明"],
  ["respondent_id", "匿名编号", "文本", "REAL-001起，不含姓名"],
  ["data_class", "数据类别", "SYNTHETIC/REAL", "正式数据必须填REAL"],
  ["consent", "知情同意", "同意/不同意", "不同意者不纳入"],
  ["group", "比较组", "智语桥组/常规检索组", "按实际分组记录"],
  ["native_language", "母语", "分类", "允许其他"],
  ["hsk_level", "中文水平", "HSK1—HSK6+", "可增加零基础/不清楚"],
  ["pre_culture", "文化理解前测", "1—5", "量表均值或单项"],
  ["post_culture", "文化理解后测", "1—5", "与前测同题"],
  ["culture_gain", "理解增量", "-4—4", "后测减前测"],
  ["task_correct", "任务正确", "0/1", "按评分规则双人复核"],
  ["completion_sec", "任务完成时长", "秒", "90—480为建议审查区间"],
  ["relevance", "回答相关性", "1—5", "试用后量表"],
  ["cultural_clarity", "文化解释清晰度", "1—5", "试用后量表"],
  ["language_accessibility", "语言难度适配", "1—5", "试用后量表"],
  ["usability", "易用性", "1—5", "试用后量表"],
  ["trust", "信任", "1—5", "结合来源/审核提示"],
  ["reuse_intent", "再次使用意愿", "1—5", "试用后量表"],
  ["quality_flag", "质量标记", "PASS/REVIEW/EXCLUDE", "须保留复核理由"],
];
codebook.getRange(`A1:D${definitions.length}`).values = definitions;
codebook.getRange("A1:D1").format = { fill: dark, font: headerFont, rowHeight: 28, horizontalAlignment: "center" };
codebook.getRange(`A2:D${definitions.length}`).format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };
codebook.getRange("A:A").format.columnWidth = 25;
codebook.getRange("B:B").format.columnWidth = 24;
codebook.getRange("C:C").format.columnWidth = 22;
codebook.getRange("D:D").format.columnWidth = 42;
codebook.freezePanes.freezeRows(1);

raw.getRange(`A1:T${rows.length + 1}`).values = [headers, ...rows];
raw.getRange("A1:T1").format = { fill: accent, font: headerFont, wrapText: true, rowHeight: 42, horizontalAlignment: "center" };
raw.getRange(`A2:T${rows.length + 1}`).format = { font: bodyFont, verticalAlignment: "center" };
raw.getRange("A:T").format.columnWidth = 16;
raw.getRange("A:A").format.columnWidth = 14;
raw.getRange("B:B").format.columnWidth = 14;
raw.getRange("G:H").format.columnWidth = 18;
raw.getRange("C2:C121").format.fill = pale;
raw.freezePanes.freezeRows(1);
raw.freezePanes.freezeColumns(4);
raw.tables.add("A1:T121", true, "SyntheticSurveyTable");

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["智语桥方法验证摘要（SYNTHETIC）"]];
summary.getRange("A1:H1").format = { fill: dark, font: { name: "宋体", size: 16, bold: true, color: "#FFFFFF" }, rowHeight: 34, verticalAlignment: "center" };
summary.getRange("A3:H3").merge();
summary.getRange("A3").values = [["注意：下列数值由固定随机种子生成，仅证明分析链路可运行；不得作为真实成效申报。"]];
summary.getRange("A3:H3").format = { fill: "#FFF4D6", font: { name: "宋体", size: 10, bold: true, color: "#7A4A00" }, rowHeight: 28, verticalAlignment: "center" };
summary.getRange("A5:G7").values = [
  ["组别", "样本量", "前测均值", "后测均值", "平均增量", "任务正确率", "平均时长（秒）"],
  ["智语桥组", null, null, null, null, null, null],
  ["常规检索组", null, null, null, null, null, null],
];
for (let rowIndex = 6; rowIndex <= 7; rowIndex += 1) {
  summary.getRange(`B${rowIndex}`).formulas = [[`=COUNTIF('合成验证数据'!$D$2:$D$121,A${rowIndex})`]];
  summary.getRange(`C${rowIndex}`).formulas = [[`=AVERAGEIF('合成验证数据'!$D$2:$D$121,A${rowIndex},'合成验证数据'!$I$2:$I$121)`]];
  summary.getRange(`D${rowIndex}`).formulas = [[`=AVERAGEIF('合成验证数据'!$D$2:$D$121,A${rowIndex},'合成验证数据'!$J$2:$J$121)`]];
  summary.getRange(`E${rowIndex}`).formulas = [[`=AVERAGEIF('合成验证数据'!$D$2:$D$121,A${rowIndex},'合成验证数据'!$K$2:$K$121)`]];
  summary.getRange(`F${rowIndex}`).formulas = [[`=AVERAGEIF('合成验证数据'!$D$2:$D$121,A${rowIndex},'合成验证数据'!$P$2:$P$121)`]];
  summary.getRange(`G${rowIndex}`).formulas = [[`=AVERAGEIF('合成验证数据'!$D$2:$D$121,A${rowIndex},'合成验证数据'!$Q$2:$Q$121)`]];
}
summary.getRange("A5:G5").format = { fill: accent, font: headerFont, wrapText: true, rowHeight: 32, horizontalAlignment: "center" };
summary.getRange("A6:G7").format = { font: bodyFont, rowHeight: 26 };
summary.getRange("C6:E7").format.numberFormat = "0.00";
summary.getRange("F6:F7").format.numberFormat = "0.0%";
summary.getRange("G6:G7").format.numberFormat = "0";
summary.getRange("A:A").format.columnWidth = 20;
summary.getRange("B:G").format.columnWidth = 17;
summary.getRange("A10:B16").values = [
  ["智语桥组体验指标", "均值"],
  ["回答相关性", null],
  ["文化解释清晰度", null],
  ["语言难度适配", null],
  ["易用性", null],
  ["信任", null],
  ["再次使用意愿", null],
];
const sourceCols = ["L", "M", "N", "O", "R", "S"];
for (let rowIndex = 11; rowIndex <= 16; rowIndex += 1) {
  const sourceCol = sourceCols[rowIndex - 11];
  summary.getRange(`B${rowIndex}`).formulas = [[`=AVERAGEIF('合成验证数据'!$D$2:$D$121,"智语桥组",'合成验证数据'!$${sourceCol}$2:$${sourceCol}$121)`]];
}
summary.getRange("A10:B10").format = { fill: gold, font: headerFont, rowHeight: 28 };
summary.getRange("A11:B16").format = { font: bodyFont, rowHeight: 24 };
summary.getRange("B11:B16").format.numberFormat = "0.00";
summary.getRange("A18:G20").merge();
summary.getRange("A18").values = [["推荐正式采集：学习者有效样本不少于60份，并尽量保持比较组平衡；教师/志愿者访谈3—5人，学习者访谈8—12人。小样本只报告描述性结果与置信区间，不将合成演示结果写成真实显著性结论。"]];
summary.getRange("A18:G20").format = { fill: pale, font: { name: "宋体", size: 10, color: dark }, wrapText: true, verticalAlignment: "center" };

summary.getRange("A23:D25").values = [
  ["组别", "前测均值", "后测均值", "平均增量"],
  ["智语桥组", null, null, null],
  ["常规检索组", null, null, null],
];
summary.getRange("B24:D24").formulas = [["=C6", "=D6", "=E6"]];
summary.getRange("B25:D25").formulas = [["=C7", "=D7", "=E7"]];
summary.getRange("A23:D23").format = { fill: pale, font: { name: "宋体", size: 9, bold: true, color: dark } };
summary.getRange("A24:D25").format = { font: { name: "宋体", size: 9, color: "#6A5A5D" } };
summary.getRange("B24:D25").format.numberFormat = "0.00";

const gainChart = summary.charts.add("bar", summary.getRange("A23:D25"));
gainChart.title = "文化理解：前后测与增量（合成验证）";
gainChart.hasLegend = true;
gainChart.yAxis = { numberFormatCode: "0.0", min: 0, max: 5 };
gainChart.setPosition("I2", "Q16");

const uxChart = summary.charts.add("bar", summary.getRange("A10:B16"));
uxChart.title = "智语桥组体验指标（1—5分，合成验证）";
uxChart.hasLegend = false;
uxChart.xAxis = { axisType: "textAxis" };
uxChart.yAxis = { numberFormatCode: "0.0", min: 0, max: 5 };
uxChart.setPosition("I18", "Q32");

const preview = await workbook.render({ sheetName: "分析摘要", range: "A1:Q32", scale: 1.2, format: "png" });
await fs.writeFile(path.join(analysisDir, "智语桥_分析摘要预览_SYNTHETIC.png"), new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
const xlsxPath = path.join(analysisDir, "智语桥_调研与分析工作簿_SYNTHETIC.xlsx");
await output.save(xlsxPath);

const inspection = await workbook.inspect({ kind: "sheet,table,formula,drawing", maxChars: 7000, tableMaxRows: 4, tableMaxCols: 8 });
await fs.writeFile(path.join(analysisDir, "智语桥_工作簿结构检查.ndjson"), inspection.ndjson || String(inspection), "utf8");
console.log(JSON.stringify({ csvPath, xlsxPath, rows: rows.length }, null, 2));
