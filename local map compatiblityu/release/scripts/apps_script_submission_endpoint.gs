const SECRET = "replace-with-a-long-random-secret";
const SUBMISSIONS_TAB = "Submissions";
const METADATA_TAB = "Submission Metadata";
const RATE_LIMIT_TAB = "Submission Rate Limits";
const MIN_SECONDS_PER_CLIENT = 60;
const MIN_SECONDS_PER_STEAM_ID = 300;

const SHEET1_HEADERS = [
  "Maps",
  "Map authors\n",
  "UEM Version (Full)",
  "Full",
  "Barebones (V 1.1.22 Unless Stated)",
  "Recommended",
  "XP Value (No Modifiers, Taken from round 1 or 2) \nNot Legend Rank",
  "Map Filters",
  "Date Tested Full\n(UK Date Format)",
  "Bugs to report/Notes",
  "Hyperlinks For AppSheet",
  "Youtube Links",
];

const META_HEADERS = [
  "Timestamp",
  "Map",
  "Steam Link",
  "Submitted By",
  "Report Type",
  "Barebones UEM Version",
  "Client ID",
  "Steam ID",
];

function doPost(e) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    return jsonResponse({ ok: false, error: "Server is busy. Try again in a moment." });
  }

  try {
    const data = JSON.parse((e.postData && e.postData.contents) || "{}");
    if (clean(data.secret, 500) !== SECRET) {
      return jsonResponse({ ok: false, error: "Unauthorized" });
    }
    if (clean(data.website, 200)) {
      return jsonResponse({ ok: false, error: "Rejected" });
    }

    const steamLink = clean(data.steam_link, 500);
    const steamId = extractSteamId(steamLink);
    if (!steamId) {
      return jsonResponse({ ok: false, error: "Valid Steam Workshop link required." });
    }

    const clientId = clean(data.client_id, 100) || "unknown";
    const now = new Date();
    const rateCheck = checkRateLimit(clientId, steamId, now);
    if (!rateCheck.ok) {
      return jsonResponse(rateCheck);
    }

    const mapName = clean(data.map_name, 300);
    const author = clean(data.author, 500);
    const reportType = clean(data.report_type, 80);
    const notes = clean(data.notes, 2000);
    const submitter = clean(data.submitter, 120);
    const uemVersion = clean(data.uem_version, 120);
    const bbVersion = clean(data.bb_version, 120);
    const status = statusValues(reportType, bbVersion);
    const today = Utilities.formatDate(now, Session.getScriptTimeZone(), "dd/MM/yyyy");

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const submissions = ensureSheet(ss, SUBMISSIONS_TAB, SHEET1_HEADERS);
    const metadata = ensureSheet(ss, METADATA_TAB, META_HEADERS);

    submissions.appendRow([
      mapName ? `=HYPERLINK("${escapeFormulaText(steamLink)}", "${escapeFormulaText(mapName)}")` : steamLink,
      author,
      uemVersion,
      status.full,
      status.barebones,
      "",
      "",
      "",
      today,
      notes,
      steamLink,
      "",
    ]);

    metadata.appendRow([
      now,
      mapName,
      steamLink,
      submitter,
      reportType,
      bbVersion,
      clientId,
      steamId,
    ]);
    recordRateLimit(clientId, steamId, now);

    return jsonResponse({ ok: true });
  } catch (err) {
    return jsonResponse({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function ensureSheet(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  if (sheet.getMaxColumns() < headers.length) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), headers.length - sheet.getMaxColumns());
  }
  const current = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  const needsHeaders = current.every(value => String(value || "").trim() === "");
  if (needsHeaders) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold");
  }
  return sheet;
}

function statusValues(reportType, bbVersion) {
  if (reportType === "Works") {
    return { full: "Yes", barebones: bbVersion ? `Yes ${bbVersion}` : "" };
  }
  if (reportType === "WorksBugs") {
    return { full: "YES/BUGS (see notes)", barebones: bbVersion ? `Yes/Bugs ${bbVersion}` : "" };
  }
  if (reportType === "Barebones") {
    return { full: "", barebones: bbVersion ? `Yes ${bbVersion}` : "" };
  }
  if (reportType === "BarebonesBugs") {
    return { full: "", barebones: bbVersion ? `Yes/Bugs ${bbVersion}` : "" };
  }
  if (reportType === "Broken") {
    return { full: "No", barebones: bbVersion ? `No ${bbVersion}` : "" };
  }
  return { full: "", barebones: "" };
}

function checkRateLimit(clientId, steamId, now) {
  const sheet = getRateLimitSheet();
  const values = sheet.getDataRange().getValues();
  const nowMs = now.getTime();
  for (let i = 1; i < values.length; i++) {
    const keyType = values[i][0];
    const keyValue = values[i][1];
    const timestamp = values[i][2];
    if (!(timestamp instanceof Date)) {
      continue;
    }
    const ageSeconds = (nowMs - timestamp.getTime()) / 1000;
    if (keyType === "client" && keyValue === clientId && ageSeconds < MIN_SECONDS_PER_CLIENT) {
      return { ok: false, error: "Please wait a minute before sending another report." };
    }
    if (keyType === "steam" && keyValue === steamId && ageSeconds < MIN_SECONDS_PER_STEAM_ID) {
      return { ok: false, error: "This Steam map was submitted recently. Try again later." };
    }
  }
  return { ok: true };
}

function recordRateLimit(clientId, steamId, now) {
  const sheet = getRateLimitSheet();
  sheet.appendRow(["client", clientId, now]);
  sheet.appendRow(["steam", steamId, now]);
  trimRateLimitSheet(sheet);
}

function getRateLimitSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(RATE_LIMIT_TAB);
  if (!sheet) {
    sheet = ss.insertSheet(RATE_LIMIT_TAB);
    sheet.hideSheet();
    sheet.appendRow(["Type", "Value", "Timestamp"]);
  }
  return sheet;
}

function trimRateLimitSheet(sheet) {
  const maxRowsToKeep = 1000;
  const extraRows = sheet.getLastRow() - maxRowsToKeep;
  if (extraRows > 1) {
    sheet.deleteRows(2, extraRows);
  }
}

function extractSteamId(url) {
  const match = String(url || "").match(/[?&]id=(\d{5,})/);
  return match ? match[1] : "";
}

function escapeFormulaText(value) {
  return String(value || "").replace(/"/g, '""');
}

function clean(value, maxLength) {
  return String(value || "").trim().slice(0, maxLength);
}

function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
