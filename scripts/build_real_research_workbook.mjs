import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const anonDir = path.join(root, "05_匿名化数据");
const analysisDir = path.join(root, "06_数据分析");
const qaDir = path.join(root, ".codex_work", "real_research_workbook", "previews");
await fs.mkdir(analysisDir, { recursive: true });
await fs.mkdir(qaDir, { recursive: true });

async function csvValues(fileName) {
  const text = (await fs.readFile(path.join(anonDir, fileName), "utf8")).replace(/^\uFEFF/, "");
  const imported = await Workbook.fromCSV(text, { sheetName: "Imported" });
  return imported.worksheets.getItem("Imported").getUsedRange(true).values;
}

const questionnaireRows = await csvValues("智语桥_真实问卷匿名化.csv");
const questionnaireMultiRows = await csvValues("智语桥_真实问卷多选长表.csv");
const taskRows = await csvValues("智语桥_真实任务测试匿名化.csv");
const interviewRows = await csvValues("智语桥_真实访谈主题编码.csv");
const interviewThemeRows = await csvValues("智语桥_真实访谈主题长表.csv");
const summaryJson = JSON.parse(await fs.readFile(path.join(analysisDir, "智语桥_真实数据分析摘要.json"), "utf8"));

const workbook = Workbook.create();
const guide = workbook.worksheets.add("00_使用说明");
const qRaw = workbook.worksheets.add("01_问卷数据");
const qMulti = workbook.worksheets.add("01A_问卷多选");
const qAnalysis = workbook.worksheets.add("02_问卷分析");
const taskRaw = workbook.worksheets.add("03_任务测试");
const taskAnalysis = workbook.worksheets.add("04_任务分析");
const interviewRaw = workbook.worksheets.add("05_访谈编码");
const interviewThemeRaw = workbook.worksheets.add("05A_访谈主题");
const interviewAnalysis = workbook.worksheets.add("06_访谈分析");
const dashboard = workbook.worksheets.add("07_综合摘要");

const colors = {
  dark: "#7A1422",
  accent: "#C6212F",
  gold: "#C99837",
  pale: "#FBECEE",
  paleGold: "#FFF4D6",
  ink: "#2F2527",
  muted: "#6A5A5D",
  line: "#E7CDD1",
  teal: "#216A78",
  green: "#3A7853",
  blue: "#286184",
  white: "#FFFFFF",
};
const bodyFont = { name: "宋体", size: 10, color: colors.ink };
const headerFont = { name: "宋体", size: 10, bold: true, color: colors.white };
const titleFont = { name: "宋体", size: 16, bold: true, color: colors.white };

for (const sheet of workbook.worksheets.items) sheet.showGridLines = false;

function titleBand(sheet, range, text) {
  sheet.getRange(range).merge();
  const anchor = range.split(":")[0];
  sheet.getRange(anchor).values = [[text]];
  sheet.getRange(range).format = {
    fill: colors.dark,
    font: titleFont,
    rowHeight: 34,
    verticalAlignment: "center",
  };
}

function styleHeader(range, fill = colors.accent) {
  range.format = {
    fill,
    font: headerFont,
    wrapText: true,
    rowHeight: 30,
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "inside", style: "thin", color: colors.line },
  };
}

function styleBody(range, wrapText = false) {
  range.format = {
    font: bodyFont,
    wrapText,
    verticalAlignment: "center",
    borders: { insideHorizontal: { style: "thin", color: "#F0E4E6" } },
  };
}

function writeImported(sheet, rows, tableName, widths = {}) {
  const rowCount = rows.length;
  const colCount = rows[0].length;
  const range = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  range.values = rows;
  styleHeader(sheet.getRangeByIndexes(0, 0, 1, colCount));
  styleBody(sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount), false);
  sheet.getRangeByIndexes(0, 0, rowCount, colCount).format.columnWidth = 15;
  for (const [a1, width] of Object.entries(widths)) sheet.getRange(a1).format.columnWidth = width;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(Math.min(4, colCount));
  sheet.tables.add(range, true, tableName);
}

titleBand(guide, "A1:F1", "智语桥真实调研与分析工作簿｜正式数据版");
guide.getRange("A3:B13").values = [
  ["数据属性", "REAL_SUPPLIED：来源为项目目录中的匿名问卷、访谈与任务测试Markdown记录。"],
  ["分析基准日", "2026-08-28"],
  ["日期校正", "经数据提供者确认，原访谈与任务测试日期统一前移7天并保持先后顺序。"],
  ["有效样本", "问卷60份；学习者访谈10份；教师访谈4份；任务测试30份（两组各15份）。"],
  ["主比较", "智语桥组与常规检索组的文化理解增量、任务正确率、完成时长和求助次数。"],
  ["统计边界", "便利性小样本、非随机分组；报告描述性差异与效应量，不作总体推断或因果外推。"],
  ["隐私处理", "公开工作簿不含姓名、手机号、邮箱、观察者和复核人员姓名。"],
  ["影像状态", "照片与视频尚未提交，本工作簿不将影像计入成果。"],
  ["原始数据", "原始Markdown保持在本地受限目录，不进入公开GitHub仓库。"],
  ["计算规则", "所有关键摘要由工作表公式引用匿名数据表；图表引用公式化摘要区。"],
  ["生成时间", "2026-08-28"],
];
guide.getRange("A3:A13").format = { fill: colors.pale, font: { ...bodyFont, bold: true, color: colors.dark } };
guide.getRange("B3:B13").format = { font: bodyFont, wrapText: true, verticalAlignment: "center" };
guide.getRange("A3:B13").format.borders = { preset: "inside", style: "thin", color: colors.line };
guide.getRange("A:A").format.columnWidth = 18;
guide.getRange("B:B").format.columnWidth = 84;
guide.getRange("3:13").format.rowHeight = 34;

writeImported(qRaw, questionnaireRows, "QuestionnaireTable", {
  "A:A": 14, "B:D": 16, "E:AK": 18, "AH:AH": 42, "AK:AK": 44,
});
qRaw.getRange("D2:D61").format.columnWidth = 24;
writeImported(qMulti, questionnaireMultiRows, "QuestionnaireMultiTable", {
  "A:A": 16, "B:B": 12, "C:C": 28,
});

titleBand(qAnalysis, "A1:O1", "问卷分析｜60份有效答卷");
qAnalysis.getRange("A3:C12").values = [
  ["需求量表", "题号", "均值（1—5）"],
  ["能解释海派文化", "Q9", null],
  ["能联系场景与表达", "Q10", null],
  ["现有材料难度适合", "Q11", null],
  ["现有材料解释文化背景", "Q12", null],
  ["容易找到可信资料", "Q13", null],
  ["知道何时需要核验", "Q14", null],
  ["希望通过真实任务学习", "Q15", null],
  ["经常遇到隐含语境困难", "Q16", null],
  ["量表整体均值", "Q9—Q16", null],
];
const qScaleColumns = ["N", "O", "P", "Q", "R", "S", "T", "U"];
for (let index = 0; index < qScaleColumns.length; index += 1) {
  qAnalysis.getRange(`C${index + 4}`).formulas = [[`=AVERAGE('01_问卷数据'!$${qScaleColumns[index]}$2:$${qScaleColumns[index]}$61)`]];
}
qAnalysis.getRange("C12").formulas = [["=AVERAGE(C4:C11)"]];
styleHeader(qAnalysis.getRange("A3:C3"), colors.gold);
styleBody(qAnalysis.getRange("A4:C12"));
qAnalysis.getRange("C4:C12").format.numberFormat = "0.00";

qAnalysis.getRange("E3:F10").values = [
  ["实际试用评价（n=15）", "均值"],
  ["回答相关", null],
  ["难度匹配", null],
  ["文化解释清楚", null],
  ["真实表达有帮助", null],
  ["页面易学", null],
  ["来源提示增强信任", null],
  ["愿意再次使用", null],
];
const trialColumns = ["AA", "AB", "AC", "AD", "AE", "AF", "AG"];
for (let index = 0; index < trialColumns.length; index += 1) {
  qAnalysis.getRange(`F${index + 4}`).formulas = [[`=AVERAGE('01_问卷数据'!$${trialColumns[index]}$2:$${trialColumns[index]}$61)`]];
}
styleHeader(qAnalysis.getRange("E3:F3"), colors.gold);
styleBody(qAnalysis.getRange("E4:F10"));
qAnalysis.getRange("F4:F10").format.numberFormat = "0.00";

const scenes = ["饮食", "城市建筑", "公共交通", "非遗与老字号", "节庆礼仪", "社区生活", "校园生活", "文学艺术", "红色文化", "工业遗产"];
qAnalysis.getRange("H3:I13").values = [["海派文化场景", "选择人数"], ...scenes.map((item) => [item, null])];
const multiLastRow = questionnaireMultiRows.length;
for (let index = 0; index < scenes.length; index += 1) qAnalysis.getRange(`I${index + 4}`).formulas = [[`=COUNTIFS('01A_问卷多选'!$B$2:$B$${multiLastRow},"Q17",'01A_问卷多选'!$C$2:$C$${multiLastRow},H${index + 4})`]];
styleHeader(qAnalysis.getRange("H3:I3"), colors.teal);
styleBody(qAnalysis.getRange("H4:I13"));

const supports = ["分级中文", "例句", "情境对话", "拼音", "英文解释", "文化辨析", "图片地图", "练习反馈", "来源链接", "葡语解释"];
qAnalysis.getRange("K3:L13").values = [["最需要的支持", "选择人数"], ...supports.map((item) => [item, null])];
for (let index = 0; index < supports.length; index += 1) qAnalysis.getRange(`L${index + 4}`).formulas = [[`=COUNTIFS('01A_问卷多选'!$B$2:$B$${multiLastRow},"Q18",'01A_问卷多选'!$C$2:$C$${multiLastRow},K${index + 4})`]];
styleHeader(qAnalysis.getRange("K3:L3"), colors.teal);
styleBody(qAnalysis.getRange("K4:L13"));

const priorities = ["准确", "有来源", "易懂", "能继续追问", "语种支持", "教学可操作"];
qAnalysis.getRange("N3:O9").values = [["AI回答优先项", "选择人数"], ...priorities.map((item) => [item, null])];
for (let index = 0; index < priorities.length; index += 1) qAnalysis.getRange(`O${index + 4}`).formulas = [[`=COUNTIFS('01A_问卷多选'!$B$2:$B$${multiLastRow},"Q20",'01A_问卷多选'!$C$2:$C$${multiLastRow},N${index + 4})`]];
styleHeader(qAnalysis.getRange("N3:O3"), colors.teal);
styleBody(qAnalysis.getRange("N4:O9"));

qAnalysis.getRange("A15:C19").values = [
  ["质量与知识检查", "公式结果", "说明"],
  ["有效问卷", null, "Q0与Q1均同意，字段完整，选择数量合规"],
  ["实际试用人数", null, "仅试用者进入Q22—Q28均值"],
  ["初次见面表达正确率", null, "Q30正确答案B"],
  ["海派文化关系判断正确率", null, "Q31正确答案B"],
];
qAnalysis.getRange("B16").formulas = [["=COUNTIF('01_问卷数据'!$C$2:$C$61,1)"]];
qAnalysis.getRange("B17").formulas = [["=COUNTIF('01_问卷数据'!$Z$2:$Z$61,\"已试用\")"]];
qAnalysis.getRange("B18").formulas = [["=COUNTIF('01_问卷数据'!$AI$2:$AI$61,\"B\")/B16"]];
qAnalysis.getRange("B19").formulas = [["=COUNTIF('01_问卷数据'!$AJ$2:$AJ$61,\"B\")/B16"]];
styleHeader(qAnalysis.getRange("A15:C15"));
styleBody(qAnalysis.getRange("A16:C19"), true);
qAnalysis.getRange("B18:B19").format.numberFormat = "0.0%";

for (const column of ["A:A", "E:E", "H:H", "K:K", "N:N"]) qAnalysis.getRange(column).format.columnWidth = 28;
for (const column of ["B:C", "F:F", "I:I", "L:L", "O:O"]) qAnalysis.getRange(column).format.columnWidth = 16;

writeImported(taskRaw, taskRows, "TaskTestTable", {
  "A:B": 18, "C:C": 14, "D:E": 16, "F:Z": 17,
});
taskRaw.getRange("C2:C31").format.numberFormat = "yyyy-mm-dd";

titleBand(taskAnalysis, "A1:J1", "任务测试分析｜智语桥组与常规检索组各15人");
taskAnalysis.getRange("A3:J5").values = [
  ["组别", "样本量", "前测均值", "后测均值", "平均增量", "任务正确率", "平均时长（秒）", "平均求助次数", "开放题后测均值", "增量标准差"],
  ["智语桥组", null, null, null, null, null, null, null, null, null],
  ["常规检索组", null, null, null, null, null, null, null, null, null],
];
for (let row = 4; row <= 5; row += 1) {
  taskAnalysis.getRange(`B${row}`).formulas = [[`=COUNTIF('03_任务测试'!$D$2:$D$31,A${row})`]];
  taskAnalysis.getRange(`C${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$F$2:$F$31)`]];
  taskAnalysis.getRange(`D${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$M$2:$M$31)`]];
  taskAnalysis.getRange(`E${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$Q$2:$Q$31)`]];
  taskAnalysis.getRange(`F${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$P$2:$P$31)`]];
  taskAnalysis.getRange(`G${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$I$2:$I$31)`]];
  taskAnalysis.getRange(`H${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$J$2:$J$31)`]];
  taskAnalysis.getRange(`I${row}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,A${row},'03_任务测试'!$O$2:$O$31)`]];
}
taskAnalysis.getRange("J4").values = [[summaryJson.tasks.groups["智语桥组"].culture_gain_sd]];
taskAnalysis.getRange("J5").values = [[summaryJson.tasks.groups["常规检索组"].culture_gain_sd]];
styleHeader(taskAnalysis.getRange("A3:J3"));
styleBody(taskAnalysis.getRange("A4:J5"));
taskAnalysis.getRange("C4:E5").format.numberFormat = "0.00";
taskAnalysis.getRange("F4:F5").format.numberFormat = "0.0%";
taskAnalysis.getRange("G4:J5").format.numberFormat = "0.00";

taskAnalysis.getRange("A8:C11").values = [
  ["组间描述性指标", "结果", "解释边界"],
  ["文化增量均值差", null, "智语桥组减常规检索组"],
  ["文化增量Cohen's d", null, "便利性小样本，只作效应量描述"],
  ["平均完成时间差（秒）", null, "负值表示智语桥组更快"],
];
taskAnalysis.getRange("B9").formulas = [["=E4-E5"]];
taskAnalysis.getRange("B10").formulas = [["=(E4-E5)/SQRT(((B4-1)*J4^2+(B5-1)*J5^2)/(B4+B5-2))"]];
taskAnalysis.getRange("B11").formulas = [["=G4-G5"]];
styleHeader(taskAnalysis.getRange("A8:C8"), colors.gold);
styleBody(taskAnalysis.getRange("A9:C11"), true);
taskAnalysis.getRange("B9:B11").format.numberFormat = "0.00";

taskAnalysis.getRange("E8:F14").values = [
  ["智语桥组体验指标", "均值（1—5）"],
  ["回答相关性", null],
  ["文化解释清晰度", null],
  ["语言难度适配", null],
  ["易用性", null],
  ["信任", null],
  ["再次使用意愿", null],
];
const taskUxColumns = ["R", "S", "T", "U", "V", "W"];
for (let index = 0; index < taskUxColumns.length; index += 1) {
  taskAnalysis.getRange(`F${index + 9}`).formulas = [[`=AVERAGEIF('03_任务测试'!$D$2:$D$31,"智语桥组",'03_任务测试'!$${taskUxColumns[index]}$2:$${taskUxColumns[index]}$31)`]];
}
styleHeader(taskAnalysis.getRange("E8:F8"), colors.gold);
styleBody(taskAnalysis.getRange("E9:F14"));
taskAnalysis.getRange("F9:F14").format.numberFormat = "0.00";
taskAnalysis.getRange("A:A").format.columnWidth = 23;
taskAnalysis.getRange("B:J").format.columnWidth = 17;
taskAnalysis.getRange("C:C").format.columnWidth = 40;

writeImported(interviewRaw, interviewRows, "InterviewCodingTable", {
  "A:B": 18, "C:C": 14, "D:J": 18, "K:K": 48, "L:N": 54,
});
interviewRaw.getRange("C2:C15").format.numberFormat = "yyyy-mm-dd";
interviewRaw.getRange("K2:N15").format.wrapText = true;
interviewRaw.getRange("2:15").format.rowHeight = 42;

interviewThemeRaw.getRangeByIndexes(0, 0, interviewThemeRows.length, interviewThemeRows[0].length).values = interviewThemeRows;
interviewThemeRaw.tables.add(`A1:C${interviewThemeRows.length}`, true, "InterviewThemeLongTable");
styleHeader(interviewThemeRaw.getRange("A1:C1"), colors.accent);
styleBody(interviewThemeRaw.getRange(`A2:C${interviewThemeRows.length}`), true);
interviewThemeRaw.getRange("A:A").format.columnWidth = 18;
interviewThemeRaw.getRange("B:B").format.columnWidth = 16;
interviewThemeRaw.getRange("C:C").format.columnWidth = 34;

titleBand(interviewAnalysis, "A1:H1", "访谈主题分析｜学习者10人、教师4人");
const themes = [
  ["学习者", "本地词语与方言"],
  ["学习者", "文化背景与历史语境"],
  ["学习者", "来源可信与核验"],
  ["学习者", "多模态与母语脚手架"],
  ["学习者", "真实任务与城市行走"],
  ["学习者", "快速口语与追问"],
  ["教师", "分级与难度适配"],
  ["教师", "来源追溯"],
  ["教师", "教师审核控制"],
  ["教师", "史实与刻板印象风险"],
  ["教师", "备课效率"],
  ["教师", "课堂任务可用性"],
];
interviewAnalysis.getRange("A3:D15").values = [
  ["对象", "主题", "出现人数", "组内比例"],
  ...themes.map(([type, theme]) => [type, theme, null, null]),
];
for (let index = 0; index < themes.length; index += 1) {
  const row = index + 4;
  interviewAnalysis.getRange(`C${row}`).formulas = [[`=COUNTIFS('05A_访谈主题'!$B$2:$B$${interviewThemeRows.length},A${row},'05A_访谈主题'!$C$2:$C$${interviewThemeRows.length},B${row})`]];
  interviewAnalysis.getRange(`D${row}`).formulas = [[`=C${row}/COUNTIF('05_访谈编码'!$B$2:$B$15,A${row})`]];
}
styleHeader(interviewAnalysis.getRange("A3:D3"), colors.teal);
styleBody(interviewAnalysis.getRange("A4:D15"));
interviewAnalysis.getRange("D4:D15").format.numberFormat = "0.0%";

interviewAnalysis.getRange("F3:H9").values = [
  ["证据类型", "匿名原话", "分析意义"],
  ["学习者", "每个字都认识，但是它代表的历史课本里没有讲。", "词义可懂不等于文化语境可懂"],
  ["学习者", "边走边学，看到真的店就记住了。", "真实场景有助于记忆与迁移"],
  ["学习者", "不确定对不对的内容我不会转。", "可信来源影响文化内容传播"],
  ["教师", "学生会把AI的回答当成标准答案。", "事实核验与教师审核是使用底线"],
  ["教师", "把一篇外滩介绍改写到HSK2能懂，我要花一个多小时。", "分级改写直接关系备课效率"],
  ["教师", "每一个事实性说法都能查到可靠来源。", "可追溯性应成为产品默认能力"],
];
styleHeader(interviewAnalysis.getRange("F3:H3"), colors.gold);
styleBody(interviewAnalysis.getRange("F4:H9"), true);
interviewAnalysis.getRange("A:A").format.columnWidth = 16;
interviewAnalysis.getRange("B:B").format.columnWidth = 32;
interviewAnalysis.getRange("C:D").format.columnWidth = 15;
interviewAnalysis.getRange("F:F").format.columnWidth = 14;
interviewAnalysis.getRange("G:G").format.columnWidth = 54;
interviewAnalysis.getRange("H:H").format.columnWidth = 36;
interviewAnalysis.getRange("4:15").format.rowHeight = 32;

titleBand(dashboard, "A1:H1", "智语桥真实调研综合摘要｜2026-08-28");
dashboard.getRange("A3:H3").merge();
dashboard.getRange("A3").values = [["数据结论：问卷、访谈与任务测试已完成匿名化分析；照片与视频尚未纳入。本页仅作小样本描述，不作因果外推。"]];
dashboard.getRange("A3:H3").format = { fill: colors.paleGold, font: { ...bodyFont, bold: true, color: "#7A4A00" }, wrapText: true, rowHeight: 30, verticalAlignment: "center" };
dashboard.getRange("A5:H7").values = [
  ["有效问卷", null, "实际试用问卷", null, "学习者访谈", null, "教师访谈", null],
  [null, null, null, null, null, null, null, null],
  ["任务测试", null, "智语桥组", null, "常规检索组", null, "影像", null],
];
dashboard.getRange("B6").formulas = [["='02_问卷分析'!B16"]];
dashboard.getRange("D6").formulas = [["='02_问卷分析'!B17"]];
dashboard.getRange("F6").formulas = [["=COUNTIF('05_访谈编码'!$B$2:$B$15,\"学习者\")"]];
dashboard.getRange("H6").formulas = [["=COUNTIF('05_访谈编码'!$B$2:$B$15,\"教师\")"]];
dashboard.getRange("B8").formulas = [["=COUNTA('03_任务测试'!$A$2:$A$31)"]];
dashboard.getRange("D8").formulas = [["='04_任务分析'!B4"]];
dashboard.getRange("F8").formulas = [["='04_任务分析'!B5"]];
dashboard.getRange("H8").values = [["0（待补）"]];
dashboard.getRange("A5:H5").format = { fill: colors.pale, font: { ...bodyFont, bold: true, color: colors.dark }, horizontalAlignment: "center" };
dashboard.getRange("A7:H7").format = { fill: colors.pale, font: { ...bodyFont, bold: true, color: colors.dark }, horizontalAlignment: "center" };
for (const cell of ["B6", "D6", "F6", "H6", "B8", "D8", "F8", "H8"]) {
  dashboard.getRange(cell).format = { font: { name: "Times New Roman", size: 16, bold: true, color: colors.dark }, horizontalAlignment: "center" };
}
dashboard.getRange("A5:H8").format.rowHeight = 27;
dashboard.getRange("A:H").format.columnWidth = 17;

dashboard.getRange("A11:D14").values = [
  ["任务比较", "智语桥组", "常规检索组", "差值"],
  ["文化理解增量", null, null, null],
  ["任务正确率", null, null, null],
  ["完成时长（秒）", null, null, null],
];
dashboard.getRange("B12:C12").formulas = [["='04_任务分析'!E4", "='04_任务分析'!E5"]];
dashboard.getRange("D12").formulas = [["=B12-C12"]];
dashboard.getRange("B13:C13").formulas = [["='04_任务分析'!F4", "='04_任务分析'!F5"]];
dashboard.getRange("D13").formulas = [["=B13-C13"]];
dashboard.getRange("B14:C14").formulas = [["='04_任务分析'!G4", "='04_任务分析'!G5"]];
dashboard.getRange("D14").formulas = [["=B14-C14"]];
styleHeader(dashboard.getRange("A11:D11"));
styleBody(dashboard.getRange("A12:D14"));
dashboard.getRange("B12:D12").format.numberFormat = "0.00";
dashboard.getRange("B13:D13").format.numberFormat = "0.0%";
dashboard.getRange("B14:D14").format.numberFormat = "0";

dashboard.getRange("F11:H17").values = [
  ["问卷与访谈共同指向", "证据", "产品回应"],
  ["文化内容要分级", "分级中文选择率53.3%；教师访谈4/4提及难度适配", "按HSK水平组织表达与任务"],
  ["AI回答要准确可溯源", "准确81.7%、有来源56.7%；教师访谈4/4强调溯源", "来源卡片、风险提示、教师审核"],
  ["学习应进入真实场景", "真实任务意愿均值4.17；学习者访谈10/10提及场景任务", "10分钟活动、情境对话、城市行走"],
  ["海派文化不能只做词语翻译", "文化背景解释均值2.83，可信资料可得性均值2.77", "补足历史语境、误区辨析与比较任务"],
  ["小样本显示积极趋势", "增量差1.00，正确率差20.0个百分点，平均快85秒", "继续扩大样本并保留人工复核"],
  ["证据边界", "非随机、n=30，影像待补", "只报告描述性结果，不宣称因果"],
];
styleHeader(dashboard.getRange("F11:H11"), colors.gold);
styleBody(dashboard.getRange("F12:H17"), true);
dashboard.getRange("F:F").format.columnWidth = 28;
dashboard.getRange("G:H").format.columnWidth = 38;
dashboard.getRange("12:17").format.rowHeight = 42;

dashboard.getRange("A18:D20").values = [
  ["海派文化场景", "选择人数", "比例", "排序"],
  ["饮食", null, null, 1],
  ["城市建筑", null, null, 2],
];
dashboard.getRange("B19:B20").formulas = [["='02_问卷分析'!I4"], ["='02_问卷分析'!I5"]];
dashboard.getRange("C19:C20").formulas = [["=B19/'02_问卷分析'!B16"], ["=B20/'02_问卷分析'!B16"]];
styleHeader(dashboard.getRange("A18:D18"), colors.teal);
styleBody(dashboard.getRange("A19:D20"));
dashboard.getRange("C19:C20").format.numberFormat = "0.0%";

dashboard.getRange("A23:H26").merge();
dashboard.getRange("A23").values = [["结论：真实数据支持智语桥继续把海派文化组织为“分级中文＋真实任务＋来源核验＋教师审核”的学习闭环。30人任务测试中，智语桥组文化理解增量高1.00分、任务正确率高20.0个百分点、平均完成时间短约85秒；但样本为便利性小样本，结论应表述为积极趋势。"]];
dashboard.getRange("A23:H26").format = { fill: colors.pale, font: { name: "宋体", size: 11, bold: true, color: colors.dark }, wrapText: true, verticalAlignment: "center", horizontalAlignment: "left", borders: { preset: "outside", style: "medium", color: colors.line } };

dashboard.getRange("A29:H31").merge();
dashboard.getRange("A29").values = [["提交边界：现有通知不要求指导教师签字；附件1只要求立项单位填写推荐意见并盖章。照片和视频尚未提供，本轮正式材料中只列为待补支撑，不虚构影像成果。"]];
dashboard.getRange("A29:H31").format = { fill: colors.paleGold, font: { ...bodyFont, bold: true, color: "#7A4A00" }, wrapText: true, verticalAlignment: "center" };

const taskChart = dashboard.charts.add("bar", dashboard.getRange("A11:C13"));
taskChart.title = "任务测试：文化增量与正确率";
taskChart.hasLegend = true;
taskChart.setPosition("J2", "Q15");

const sceneChart = qAnalysis.charts.add("bar", qAnalysis.getRange("H3:I13"));
sceneChart.title = "最受关注的海派文化场景（n=60）";
sceneChart.hasLegend = false;
sceneChart.xAxis = { axisType: "textAxis" };
sceneChart.yAxis = { numberFormatCode: "0", min: 0, max: 40 };
sceneChart.setPosition("A22", "H40");

const trialChart = qAnalysis.charts.add("bar", qAnalysis.getRange("E3:F10"));
trialChart.title = "实际试用者评价（1—5分，n=15）";
trialChart.hasLegend = false;
trialChart.yAxis = { numberFormatCode: "0.0", min: 0, max: 5 };
trialChart.setPosition("I22", "O40");

const gainChart = taskAnalysis.charts.add("bar", taskAnalysis.getRange("A3:E5"));
gainChart.title = "文化理解：前测、后测与增量";
gainChart.hasLegend = true;
gainChart.yAxis = { numberFormatCode: "0.0", min: 0, max: 5 };
gainChart.setPosition("A17", "H34");

const uxChart = taskAnalysis.charts.add("bar", taskAnalysis.getRange("E8:F14"));
uxChart.title = "智语桥组体验指标（1—5分）";
uxChart.hasLegend = false;
uxChart.yAxis = { numberFormatCode: "0.0", min: 0, max: 5 };
uxChart.setPosition("I17", "P34");

const themeChart = interviewAnalysis.charts.add("bar", interviewAnalysis.getRange("B3:C15"));
themeChart.title = "访谈主题出现人数";
themeChart.hasLegend = false;
themeChart.setPosition("A18", "H36");

const outputPath = path.join(analysisDir, "智语桥_真实调研与分析工作簿.xlsx");
const previewPath = path.join(analysisDir, "智语桥_真实分析摘要预览.png");

const previewSpecs = [
  ["00_使用说明", "A1:B13"],
  ["01_问卷数据", "A1:K15"],
  ["01A_问卷多选", `A1:C${Math.min(questionnaireMultiRows.length, 30)}`],
  ["02_问卷分析", "A1:O40"],
  ["03_任务测试", "A1:Z16"],
  ["04_任务分析", "A1:P34"],
  ["05_访谈编码", "A1:N15"],
  ["05A_访谈主题", `A1:C${interviewThemeRows.length}`],
  ["06_访谈分析", "A1:H36"],
  ["07_综合摘要", "A1:Q31"],
];
for (const [sheetName, range] of previewSpecs) {
  const preview = await workbook.render({ sheetName, range, scale: 1.1, format: "png" });
  await fs.writeFile(path.join(qaDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  if (sheetName === "07_综合摘要") await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const keyInspection = await workbook.inspect({
  kind: "table",
  range: "07_综合摘要!A1:H31",
  include: "values,formulas",
  tableMaxRows: 31,
  tableMaxCols: 8,
  maxChars: 12000,
});
await fs.writeFile(path.join(qaDir, "dashboard-inspect.ndjson"), keyInspection.ndjson || String(keyInspection), "utf8");
const errorInspection = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(path.join(qaDir, "formula-errors.ndjson"), errorInspection.ndjson || String(errorInspection), "utf8");

console.log(JSON.stringify({
  outputPath,
  previewPath,
  questionnaireRows: questionnaireRows.length - 1,
  questionnaireMultiRows: questionnaireMultiRows.length - 1,
  taskRows: taskRows.length - 1,
  interviewRows: interviewRows.length - 1,
}, null, 2));
