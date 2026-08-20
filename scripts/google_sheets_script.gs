/**
 * Search Total Human — генератор Google Таблицы из data/monitoring_data.json
 * Данные подтягиваются напрямую с GitHub (raw), поэтому таблицу можно
 * обновлять полностью автоматически по расписанию — без ручного копирования.
 *
 * Установка (один раз):
 * 1. В Google Таблице: Расширения → Apps Script.
 * 2. Удалите содержимое Code.gs, вставьте содержимое этого файла целиком.
 * 3. Сохраните (Ctrl+S).
 * 4. Выберите функцию buildSheet в выпадающем списке сверху → "Выполнить".
 *    Разрешите запрошенный доступ (внешний запрос к GitHub + доступ к таблице).
 * 5. Выберите функцию installWeeklyTrigger → "Выполнить" один раз.
 *    Это ставит автоматический еженедельный запуск buildSheet —
 *    дальше скрипт сам подтягивает свежие данные без вашего участия.
 *
 * Обновление данных:
 * Данные (data/monitoring_data.json) обновляются агентом в репозитории
 * на GitHub. Таблица подхватывает изменения при следующем автозапуске
 * (или сразу, если вручную выполнить buildSheet).
 */

const DATA_URL = "https://raw.githubusercontent.com/antonlyaksa-byte/search-total-human/master/data/monitoring_data.json";

function fetchData_() {
  const response = UrlFetchApp.fetch(DATA_URL, { muteHttpExceptions: true });
  if (response.getResponseCode() !== 200) {
    throw new Error("Не удалось загрузить данные с GitHub: HTTP " + response.getResponseCode());
  }
  return JSON.parse(response.getContentText());
}

function installWeeklyTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "buildSheet")
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger("buildSheet")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(8)
    .create();

  SpreadsheetApp.getUi().alert("Готово: автообновление по понедельникам в ~8:00 включено.");
}

const SHEET_DATA_NAME = "База знаний";
const SHEET_STATS_NAME = "Статистика";

const HEADERS = [
  ["№", 40],
  ["Тема", 130],
  ["Название материала", 260],
  ["Тип", 90],
  ["Краткое содержание", 380],
  ["Источник / Автор", 150],
  ["Ссылка", 220],
  ["Язык", 50],
  ["Год", 60],
  ["Дата добавления", 100],
  ["Прочитано", 90],
  ["Полезность информации", 110],
];
const READ_COL = HEADERS.length - 1;
const USEFUL_COL = HEADERS.length; // last column

const COLOR_HEADER_BG = "#2B579A";
const COLOR_HEADER_FONT = "#FFFFFF";
const COLOR_TX_BG = "#E8F0FE";
const COLOR_HC_BG = "#FCE8E6";
const COLOR_BORDER = "#D9D9D9";
const COLOR_LINK = "#0563C1";

function buildSheet() {
  const data = fetchData_();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  buildDataSheet_(ss, data);
  buildStatsSheet_(ss);
  SpreadsheetApp.getUi().alert(`Готово: ${data.length} записей загружено в "${SHEET_DATA_NAME}".`);
}

function readPreviousReadState_(sheet) {
  const state = {};
  if (!sheet) return state;
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) return state;

  const header = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const readColIdx = header.indexOf("Прочитано");
  const idColIdx = header.indexOf("№");
  if (readColIdx === -1 || idColIdx === -1) return state;

  const values = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
  values.forEach(row => {
    const id = row[idColIdx];
    if (id !== "" && id !== null) state[id] = row[readColIdx] === true;
  });
  return state;
}

function readPreviousUsefulState_(sheet) {
  const state = {};
  if (!sheet) return state;
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) return state;

  const header = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const usefulColIdx = header.indexOf("Полезность информации");
  const idColIdx = header.indexOf("№");
  if (usefulColIdx === -1 || idColIdx === -1) return state;

  const values = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
  values.forEach(row => {
    const id = row[idColIdx];
    if (id !== "" && id !== null) state[id] = row[usefulColIdx];
  });
  return state;
}

function buildDataSheet_(ss, data) {
  let sheet = ss.getSheetByName(SHEET_DATA_NAME);
  const previousReadState = readPreviousReadState_(sheet);
  const previousUsefulState = readPreviousUsefulState_(sheet);
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet(SHEET_DATA_NAME);
  }

  const numCols = HEADERS.length;
  const numRows = data.length + 1;

  // Заголовки
  const headerRange = sheet.getRange(1, 1, 1, numCols);
  headerRange.setValues([HEADERS.map(h => h[0])]);
  headerRange.setFontWeight("bold").setFontColor(COLOR_HEADER_FONT)
    .setBackground(COLOR_HEADER_BG).setHorizontalAlignment("center")
    .setVerticalAlignment("middle").setWrap(true);
  sheet.setRowHeight(1, 34);

  HEADERS.forEach((h, i) => sheet.setColumnWidth(i + 1, h[1]));

  // Данные
  const rows = data.map(item => [
    item.id, item.topic, item.title, item.type, item.summary,
    item.source, item.url, item.lang, item.year, item.added,
  ]);
  if (rows.length) {
    const dataRange = sheet.getRange(2, 1, rows.length, rows[0].length);
    dataRange.setValues(rows);
    dataRange.setVerticalAlignment("top").setWrap(true).setFontFamily("Arial").setFontSize(10);
    sheet.getRangeList(["A2:A" + numRows, "D2:D" + numRows, "H2:H" + numRows, "I2:I" + numRows, "J2:J" + numRows])
      .setHorizontalAlignment("center");

    // Чекбокс "Прочитано" — сохраняем отметки с прошлой пересборки по id
    const readRange = sheet.getRange(2, READ_COL, rows.length, 1);
    readRange.insertCheckboxes();
    const readValues = data.map(item => [previousReadState[item.id] === true]);
    readRange.setValues(readValues);
    readRange.setHorizontalAlignment("center").setVerticalAlignment("middle");

    // Выпадающий список "Полезность информации" (1-5) — сохраняем оценки с прошлой пересборки по id
    const usefulRange = sheet.getRange(2, USEFUL_COL, rows.length, 1);
    const usefulRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(["1", "2", "3", "4", "5"], true)
      .setAllowInvalid(false)
      .build();
    usefulRange.setDataValidation(usefulRule);
    const usefulValues = data.map(item => [previousUsefulState[item.id] || ""]);
    usefulRange.setValues(usefulValues);
    usefulRange.setHorizontalAlignment("center").setVerticalAlignment("middle");

    // Ссылки — кликабельные, синие, подчёркнутые
    const linkCol = 7;
    const richValues = data.map(item => [
      SpreadsheetApp.newRichTextValue().setText(item.url).setLinkUrl(item.url).build(),
    ]);
    sheet.getRange(2, linkCol, rows.length, 1).setRichTextValues(richValues);
    sheet.getRange(2, linkCol, rows.length, 1).setFontColor(COLOR_LINK).setFontLine("underline");

    // Заливка по теме
    for (let r = 0; r < data.length; r++) {
      const bg = data[r].topic === "Total Experience" ? COLOR_TX_BG
        : data[r].topic === "Человекоцентричность" ? COLOR_HC_BG
        : null;
      if (bg) sheet.getRange(r + 2, 2).setBackground(bg);
    }
  }

  sheet.getRange(1, 1, numRows, numCols).setBorder(true, true, true, true, true, true, COLOR_BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setFrozenRows(1);
  const existingFilter = sheet.getFilter();
  if (existingFilter) existingFilter.remove();
  sheet.getRange(1, 1, numRows, numCols).createFilter();
}

function buildStatsSheet_(ss) {
  let sheet = ss.getSheetByName(SHEET_STATS_NAME);
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet(SHEET_STATS_NAME);
  }

  const d = `'${SHEET_DATA_NAME}'`;
  const rows = [
    ["Метрика", "Значение"],
    ["Всего записей", `=COUNTA(${d}!A2:A10000)`],
    ["Total Experience", `=COUNTIF(${d}!B2:B10000,"Total Experience")`],
    ["Человекоцентричность", `=COUNTIF(${d}!B2:B10000,"Человекоцентричность")`],
    ["Статей", `=COUNTIF(${d}!D2:D10000,"Статья")`],
    ["Отчётов", `=COUNTIF(${d}!D2:D10000,"Отчёт")`],
    ["На русском", `=COUNTIF(${d}!H2:H10000,"RU")`],
    ["На английском", `=COUNTIF(${d}!H2:H10000,"EN")`],
    ["Последнее обновление", Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd")],
  ];

  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
  sheet.getRange(1, 1, 1, 2).setFontWeight("bold").setFontColor(COLOR_HEADER_FONT).setBackground(COLOR_HEADER_BG);
  sheet.getRange(2, 1, rows.length - 1, 1).setFontWeight("normal");
  sheet.getRange(2, 2, rows.length - 1, 1).setFontWeight("bold");
  sheet.setColumnWidth(1, 220);
  sheet.setColumnWidth(2, 140);
}
