/**
 * ==============================================================================
 * CONFIGURATION: ENTER YOUR SPREADSHEET ID & TAB NAME HERE
 * ==============================================================================
 */
const CONFIG = {
  // Replace with your Google Sheet ID (Found in the URL between /d/ and /edit)
  // Example: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
  SPREADSHEET_ID: "YOUR_GOOGLE_SHEET_ID_HERE", 
  
  // Replace with the exact tab name where your raw dataset is located
  DATASET_TAB_NAME: "medication_inventory", 
  
  // Automated Alert Target Tab Names
  SHEET_EXPIRING: "Expiring Medications",
  SHEET_SETTINGS: "Settings",
  SHEET_LOGS: "Alert Log",
  SHEET_DASHBOARD: "Dashboard",
  
  DEFAULT_THRESHOLD: 30, // Days before expiration
  DEFAULT_RECIPIENT: "pharmacy-admin@example.com"
};

/**
 * Custom Menu Item in Google Sheets UI
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Medication Tracker')
    .addItem('🔄 Refresh Expiry Analysis', 'processInventoryData')
    .addItem('📧 Send Email Alert Now', 'sendExpiryAlerts')
    .addSeparator()
    .addItem('📊 Update Dashboard', 'updateDashboard')
    .addItem('📁 Export Expiring CSV to Drive', 'exportExpiringCSV')
    .addSeparator()
    .addItem('⚙️ Settings Management', 'showSettingsDialog')
    .addToUi();
}

/**
 * Gets Spreadsheet Target Instance safely
 */
function getTargetSpreadsheet() {
  if (CONFIG.SPREADSHEET_ID && CONFIG.SPREADSHEET_ID !== "YOUR_GOOGLE_SHEET_ID_HERE") {
    return SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  }
  return SpreadsheetApp.getActiveSpreadsheet();
}

/**
 * Core Processing Engine: Calculates days until expiry, formats status, & populates Expiring Sheet
 */
function processInventoryData() {
  const ss = getTargetSpreadsheet();
  const inventorySheet = ss.getSheetByName(CONFIG.DATASET_TAB_NAME);
  
  if (!inventorySheet) {
    SpreadsheetApp.getUi().alert(`Error: Could not find tab named "${CONFIG.DATASET_TAB_NAME}". Please check your CONFIG settings.`);
    return;
  }
  
  setupRequiredSheets(ss);
  
  const expiringSheet = ss.getSheetByName(CONFIG.SHEET_EXPIRING);
  const data = inventorySheet.getDataRange().getValues();
  if (data.length <= 1) return;

  const headers = data[0];
  const threshold = Number(getSetting("Warning Threshold (Days)", CONFIG.DEFAULT_THRESHOLD));
  
  // Normalize Current Date to midnight for accurate calculation
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  // Find column indexes dynamically from headers
  const idIdx = headers.indexOf("Medication ID");
  const nameIdx = headers.indexOf("Medication Name");
  const categoryIdx = headers.indexOf("Category");
  const qtyIdx = headers.indexOf("Quantity in Stock");
  const expiryIdx = headers.indexOf("Expiration Date");
  const costIdx = headers.indexOf("Unit Cost");
  const criticalIdx = headers.indexOf("Critical Status");
  const locationIdx = headers.indexOf("Storage Location");

  const expiringRows = [];
  expiringRows.push([
    "Medication ID", "Medication Name", "Category", "Quantity", 
    "Expiration Date", "Days Until Expiry", "Status", "Unit Cost", 
    "Total Risk Value", "Storage Location", "Critical Status"
  ]);

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!row[idIdx]) continue;
    
    const expiryDate = new Date(row[expiryIdx]);
    if (isNaN(expiryDate.getTime())) continue; // Skip bad dates
    
    expiryDate.setHours(0, 0, 0, 0);
    const timeDiff = expiryDate.getTime() - today.getTime();
    const daysUntilExpiry = Math.ceil(timeDiff / (1000 * 3600 * 24));

    if (daysUntilExpiry <= threshold) {
      const qty = Number(row[qtyIdx]) || 0;
      const unitCost = Number(row[costIdx]) || 0;
      const totalRiskValue = qty * unitCost;
      const status = daysUntilExpiry < 0 ? "EXPIRED" : "EXPIRING SOON";
      
      expiringRows.push([
        row[idIdx],
        row[nameIdx],
        row[categoryIdx],
        qty,
        Utilities.formatDate(expiryDate, ss.getSpreadsheetTimeZone(), "yyyy-MM-dd"),
        daysUntilExpiry,
        status,
        unitCost,
        totalRiskValue,
        row[locationIdx],
        row[criticalIdx]
      ]);
    }
  }

  // Populate Expiring Medications Sheet
  expiringSheet.clearContents();
  if (expiringRows.length > 1) {
    expiringSheet.getRange(1, 1, expiringRows.length, expiringRows[0].length).setValues(expiringRows);
    expiringSheet.getRange("A1:K1").setFontWeight("bold").setBackground("#C0392B").setFontColor("#FFFFFF");
    expiringSheet.getRange(2, 8, expiringRows.length - 1, 2).setNumberFormat("$#,##0.00");
  }
  
  updateDashboard();
}

/**
 * Sends Automated Daily Expiry Email with Statistics and attached CSV
 */
function sendExpiryAlerts() {
  processInventoryData();
  const ss = getTargetSpreadsheet();
  const expiringSheet = ss.getSheetByName(CONFIG.SHEET_EXPIRING);
  const data = expiringSheet.getDataRange().getValues();
  
  const recipients = getSetting("Email Recipients", CONFIG.DEFAULT_RECIPIENT);
  
  if (data.length <= 1) {
    logAlert("Email Alert", recipients, 0, 0, "SKIPPED", "No expiring medications found.");
    return;
  }

  let expiringCount = 0;
  let criticalCount = 0;
  let totalValueAtRisk = 0;
  const categoriesMap = {};
  const criticalItems = [];

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    expiringCount++;
    const category = row[2];
    const qty = row[3];
    const expDate = row[4];
    const daysLeft = row[5];
    const riskVal = row[8];
    const isCritical = row[10] === true || String(row[10]).toLowerCase() === 'true';

    totalValueAtRisk += riskVal;
    categoriesMap[category] = (categoriesMap[category] || 0) + 1;

    const itemObj = { name: row[1], expDate: expDate, stock: qty, daysLeft: daysLeft };

    if (isCritical) {
      criticalCount++;
      criticalItems.push(itemObj);
    }
  }

  criticalItems.sort((a, b) => a.daysLeft - b.daysLeft);
  const topCritical = criticalItems.slice(0, 5);

  let topItemsHtml = "";
  topCritical.forEach((item) => {
    topItemsHtml += `<li><b>${item.name}</b> - Expires: <code>${item.expDate}</code> | Days Left: <b>${item.daysLeft}</b> | Stock: <b>${item.stock}</b></li>`;
  });
  if (!topItemsHtml) topItemsHtml = "<li>No critical items expiring soon.</li>";

  const emailSubject = `[MEDICATION ALERT] ${expiringCount} Medications Expiring Within 30 Days`;
  const emailBody = `
    <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
      <h2 style="color: #C0392B; border-bottom: 2px solid #C0392B; padding-bottom: 5px;">Medication Inventory Expiration Alert</h2>
      <p>Dear Pharmacy Administrator,</p>
      <p>This is an automated notification regarding impending medication expirations.</p>
      
      <div style="background-color: #F8F9F9; padding: 15px; border-left: 4px solid #C0392B; margin: 15px 0;">
        <h3 style="margin-top:0; color: #2C3E50;">SUMMARY METRICS</h3>
        <ul>
          <li><b>Total Expiring Items:</b> ${expiringCount}</li>
          <li><b>Critical Items Needing Attention:</b> <span style="color:red; font-weight:bold;">${criticalCount}</span></li>
          <li><b>Affected Categories:</b> ${Object.keys(categoriesMap).length}</li>
          <li><b>Total Stock Value At Risk:</b> $${totalValueAtRisk.toFixed(2)}</li>
        </ul>
      </div>

      <h3 style="color: #2C3E50;">TOP CRITICAL ITEMS EXPIRING SOON:</h3>
      <ol>${topItemsHtml}</ol>

      <p>📎 <i>The complete list of expiring items has been attached to this email as a CSV file.</i></p>
      <hr>
      <p style="font-size: 11px; color: #7F8C8D;">Medication Inventory System | Automated via Google Apps Script</p>
    </div>
  `;

  const csvBlob = generateCSVBlob(data);

  try {
    MailApp.sendEmail({
      to: recipients,
      subject: emailSubject,
      htmlBody: emailBody,
      attachments: [csvBlob]
    });
    logAlert("Email Alert", recipients, expiringCount, criticalCount, "SUCCESS", "Email alert sent successfully.");
  } catch (err) {
    logAlert("Email Alert", recipients, expiringCount, criticalCount, "FAILED", err.toString());
  }
}

/**
 * Builds Summary Dashboard
 */
function updateDashboard() {
  const ss = getTargetSpreadsheet();
  let dashSheet = ss.getSheetByName(CONFIG.SHEET_DASHBOARD);
  if (!dashSheet) {
    dashSheet = ss.insertSheet(CONFIG.SHEET_DASHBOARD, 0);
  }

  const inventorySheet = ss.getSheetByName(CONFIG.DATASET_TAB_NAME);
  const expiringSheet = ss.getSheetByName(CONFIG.SHEET_EXPIRING);

  if (!inventorySheet || !expiringSheet) return;

  const invData = inventorySheet.getDataRange().getValues();
  const expData = expiringSheet.getDataRange().getValues();

  const totalMeds = Math.max(0, invData.length - 1);
  let expiringSoonCount = 0;
  let expiredCount = 0;

  for (let i = 1; i < expData.length; i++) {
    const daysLeft = expData[i][5];
    if (daysLeft < 0) {
      expiredCount++;
    } else {
      expiringSoonCount++;
    }
  }

  dashSheet.clear();
  dashSheet.getRange("A1:D1").merge().setValue("MEDICATION INVENTORY DASHBOARD")
    .setFontSize(16).setFontWeight("bold").setBackground("#2C3E50").setFontColor("#FFFFFF")
    .setHorizontalAlignment("center");

  dashSheet.getRange("A3:A5").setValues([
    ["Total Medications in Stock:"],
    ["Count Expiring (≤30 Days):"],
    ["Count Already Expired:"]
  ]).setFontWeight("bold");

  dashSheet.getRange("B3:B5").setValues([
    [totalMeds],
    [expiringSoonCount],
    [expiredCount]
  ]).setFontWeight("bold").setFontColor("#C0392B");

  dashSheet.setColumnWidth(1, 230);
  dashSheet.setColumnWidth(2, 100);
}

/**
 * Helper to ensure required helper sheets exist
 */
function setupRequiredSheets(ss) {
  if (!ss.getSheetByName(CONFIG.SHEET_EXPIRING)) ss.insertSheet(CONFIG.SHEET_EXPIRING);
  
  if (!ss.getSheetByName(CONFIG.SHEET_SETTINGS)) {
    const setSheet = ss.insertSheet(CONFIG.SHEET_SETTINGS);
    setSheet.appendRow(["Setting Name", "Value", "Description"]);
    setSheet.appendRow(["Email Recipients", CONFIG.DEFAULT_RECIPIENT, "Email addresses separated by comma"]);
    setSheet.appendRow(["Warning Threshold (Days)", CONFIG.DEFAULT_THRESHOLD, "Days threshold before expiry"]);
    setSheet.getRange("A1:C1").setFontWeight("bold").setBackground("#34495E").setFontColor("#FFFFFF");
  }

  if (!ss.getSheetByName(CONFIG.SHEET_LOGS)) {
    const logSheet = ss.insertSheet(CONFIG.SHEET_LOGS);
    logSheet.appendRow(["Timestamp", "Event Type", "Recipients", "Expiring Count", "Critical Count", "Status", "Details"]);
    logSheet.getRange("A1:G1").setFontWeight("bold").setBackground("#27AE60").setFontColor("#FFFFFF");
  }
}

function getSetting(key, defaultValue) {
  const ss = getTargetSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_SETTINGS);
  if (!sheet) return defaultValue;
  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === key) return data[i][1];
  }
  return defaultValue;
}

function logAlert(eventType, recipients, expCount, critCount, status, details) {
  const ss = getTargetSpreadsheet();
  let logSheet = ss.getSheetByName(CONFIG.SHEET_LOGS);
  if (logSheet) {
    logSheet.appendRow([new Date(), eventType, recipients, expCount, critCount, status, details]);
  }
}

function generateCSVBlob(data) {
  let csvContent = "";
  data.forEach(row => {
    csvContent += row.map(cell => `"${cell}"`).join(",") + "\n";
  });
  return Utilities.newBlob(csvContent, 'text/csv', 'Expiring_Medications_Detailed.csv');
}

function exportExpiringCSV() {
  const ss = getTargetSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_EXPIRING);
  const blob = generateCSVBlob(sheet.getDataRange().getValues());
  DriveApp.createFile(blob);
  SpreadsheetApp.getUi().alert("Exported Expiring_Medications_Detailed.csv directly to your Google Drive!");
}

function showSettingsDialog() {
  const html = HtmlService.createHtmlOutput(`
    <div style="font-family: Arial, sans-serif; padding: 15px;">
      <h3 style="color: #2C3E50;">Configure Email & Thresholds</h3>
      <label>Email Recipients (comma separated):</label><br>
      <input type="text" id="recipients" value="${getSetting("Email Recipients", CONFIG.DEFAULT_RECIPIENT)}" style="width: 95%; padding: 5px; margin-top:5px;"><br><br>
      <label>Warning Threshold (Days):</label><br>
      <input type="number" id="threshold" value="${getSetting("Warning Threshold (Days)", CONFIG.DEFAULT_THRESHOLD)}" style="width: 95%; padding: 5px; margin-top:5px;"><br><br>
      <button onclick="save()" style="background-color: #27AE60; color: white; padding: 8px 15px; border: none; cursor: pointer; border-radius: 4px;">Save Configuration</button>
      <script>
        function save() {
          const rec = document.getElementById('recipients').value;
          const thresh = document.getElementById('threshold').value;
          google.script.run.withSuccessHandler(() => google.script.host.close()).saveSettingsValues(rec, thresh);
        }
      </script>
    </div>
  `).setWidth(420).setHeight(280);
  SpreadsheetApp.getUi().showModalDialog(html, 'Settings Management');
}

function saveSettingsValues(recipients, threshold) {
  const ss = getTargetSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_SETTINGS);
  if (sheet) {
    sheet.getRange("B2").setValue(recipients);
    sheet.getRange("B3").setValue(threshold);
    SpreadsheetApp.getUi().alert("Settings updated successfully!");
  }
}