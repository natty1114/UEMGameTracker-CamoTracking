import gspread
import json
import os
import re
import uuid
from datetime import datetime

import requests
import certifi

CONFIG_DIR = 'config'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'uem_config.json')
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'google_credentials.json')
SHEET_KEY = '1gXTcn1M0j36Ptynyp3Zy7OrXTbBdyfOO5opUKyaSIF4'
SUBMISSIONS_TAB = 'Submissions'
SUBMISSION_METADATA_TAB = 'Submission Metadata'
SOURCE_TAB = 'Sheet1'
APPS_SCRIPT_URL_KEY = 'submission_endpoint_url'
APPS_SCRIPT_SECRET_KEY = 'submission_endpoint_secret'
INSTALL_ID_KEY = 'submission_client_id'

# Sheet1 column headers in order — Submissions worksheet uses the same layout
SHEET1_HEADERS = [
    'Maps',
    'Map authors\n',
    'UEM Version (Full)',
    'Full',
    'Barebones (V 1.1.22 Unless Stated)',
    'Recommended',
    'XP Value (No Modifiers, Taken from round 1 or 2) \nNot Legend Rank',
    'Map Filters',
    'Date Tested Full\n(UK Date Format)',
    'Bugs to report/Notes',
    'Hyperlinks For AppSheet',
    'Youtube Links',
]

META_HEADERS = [
    'Timestamp',
    'Map',
    'Steam Link',
    'Submitted By',
    'Report Type',
    'Barebones UEM Version',
]

ALL_HEADERS = SHEET1_HEADERS

FULL_STATUS_VALUES = ['Yes', 'YES/BUGS (see notes)', 'No']
CURRENT_BAREBONES_VERSION = 'V 1.3.1 (build-002)'
BAREBONES_STATUS_VALUES = [
    f'Yes {CURRENT_BAREBONES_VERSION}',
    f'Yes/Bugs {CURRENT_BAREBONES_VERSION}',
    f'No {CURRENT_BAREBONES_VERSION}',
]


def _load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_submission_endpoint_state():
    config = _load_config()
    return {
        'configured': bool(str(config.get(APPS_SCRIPT_URL_KEY) or '').strip()),
        'has_secret': bool(str(config.get(APPS_SCRIPT_SECRET_KEY) or '').strip()),
        'mode': 'Apps Script endpoint' if str(config.get(APPS_SCRIPT_URL_KEY) or '').strip() else 'Local Google credentials fallback',
    }


def _get_or_create_client_id(config):
    client_id = str(config.get(INSTALL_ID_KEY) or '').strip()
    if client_id:
        return client_id
    client_id = uuid.uuid4().hex
    config[INSTALL_ID_KEY] = client_id
    _save_config(config)
    return client_id


def _submit_report_via_apps_script(steam_link, map_name, author, report_type, notes, submitter, uem_version='', bb_version=''):
    config = _load_config()
    endpoint_url = str(config.get(APPS_SCRIPT_URL_KEY) or '').strip()
    if not endpoint_url:
        return False

    payload = {
        'secret': str(config.get(APPS_SCRIPT_SECRET_KEY) or '').strip(),
        'client_id': _get_or_create_client_id(config),
        'steam_link': steam_link,
        'map_name': map_name,
        'author': author,
        'report_type': report_type,
        'notes': notes,
        'submitter': submitter,
        'uem_version': uem_version,
        'bb_version': bb_version,
    }
    response = requests.post(endpoint_url, json=payload, timeout=20, verify=certifi.where())
    response.raise_for_status()
    result = response.json()
    if not result.get('ok'):
        raise RuntimeError(result.get('error') or 'Submission failed')
    return True


def get_sheet():
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    sh = gc.open_by_key(SHEET_KEY)
    try:
        ws = sh.worksheet(SUBMISSIONS_TAB)
    except gspread.WorksheetNotFound:
        num_cols = len(ALL_HEADERS)
        ws = sh.add_worksheet(title=SUBMISSIONS_TAB, rows=100, cols=num_cols)
        col_range = f'A1:{num_cols_to_letters(num_cols)}1'
        ws.update(col_range, [ALL_HEADERS])
        ws.format(col_range, {'textFormat': {'bold': True}})
    ensure_submission_layout(ws)
    return ws

def get_metadata_sheet(spreadsheet):
    try:
        ws = spreadsheet.worksheet(SUBMISSION_METADATA_TAB)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=SUBMISSION_METADATA_TAB, rows=100, cols=len(META_HEADERS))

    if ws.col_count < len(META_HEADERS):
        ws.add_cols(len(META_HEADERS) - ws.col_count)
    header_range = f'A1:{num_cols_to_letters(len(META_HEADERS))}1'
    ws.update(header_range, [META_HEADERS])
    ws.format(header_range, {'textFormat': {'bold': True}})
    return ws

def ensure_submission_layout(ws):
    if ws.col_count < len(ALL_HEADERS):
        ws.add_cols(len(ALL_HEADERS) - ws.col_count)

    header_range = f'A1:{num_cols_to_letters(len(ALL_HEADERS))}1'
    ws.update(header_range, [ALL_HEADERS])
    ws.format(header_range, {'textFormat': {'bold': True}})

def num_cols_to_letters(n):
    result = ''
    while n > 0:
        n -= 1
        result = chr(ord('A') + n % 26) + result
        n //= 26
    return result

def _row_from_append_response(response):
    updated_range = response.get('updates', {}).get('updatedRange', '')
    match = re.search(r'![A-Z]+(\d+):', updated_range)
    if match:
        return int(match.group(1))
    return None

def _validation_request(sheet_id, row_index, col_index, values):
    return {
        'setDataValidation': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': row_index - 1,
                'endRowIndex': row_index,
                'startColumnIndex': col_index - 1,
                'endColumnIndex': col_index,
            },
            'rule': {
                'condition': {
                    'type': 'ONE_OF_LIST',
                    'values': [{'userEnteredValue': value} for value in values],
                },
                'strict': True,
                'showCustomUi': True,
            },
        },
    }

def _format_request(sheet_id, row_index, col_index, bg_color, text_color):
    return {
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': row_index - 1,
                'endRowIndex': row_index,
                'startColumnIndex': col_index - 1,
                'endColumnIndex': col_index,
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': bg_color,
                    'textFormat': {'foregroundColor': text_color},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE',
                },
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat.foregroundColor,horizontalAlignment,verticalAlignment)',
        },
    }

def _status_colors(value):
    value = (value or '').lower()
    if value.startswith('yes/bugs') or value.startswith('yes bugs'):
        return (
            {'red': 0.984, 'green': 0.847, 'blue': 0.455},
            {'red': 0.247, 'green': 0.161, 'blue': 0.0},
        )
    if value.startswith('yes'):
        return (
            {'red': 0.851, 'green': 0.941, 'blue': 0.784},
            {'red': 0.0, 'green': 0.424, 'blue': 0.216},
        )
    if value.startswith('no'):
        return (
            {'red': 0.733, 'green': 0.0, 'blue': 0.0},
            {'red': 1.0, 'green': 1.0, 'blue': 1.0},
        )
    return None

def _copy_sheet_dropdown_style(ws, row_index):
    requests = []
    sh = ws.spreadsheet
    copied_source_validation = False
    try:
        source_ws = sh.worksheet(SOURCE_TAB)
    except gspread.WorksheetNotFound:
        source_ws = sh.sheet1 if sh.sheet1.title != SUBMISSIONS_TAB else None

    if source_ws:
        source_sheet_id = source_ws.id
        for col_index in (4, 5):
            requests.append(
                {
                    'copyPaste': {
                        'source': {
                            'sheetId': source_sheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': 2,
                            'startColumnIndex': col_index - 1,
                            'endColumnIndex': col_index,
                        },
                        'destination': {
                            'sheetId': ws.id,
                            'startRowIndex': row_index - 1,
                            'endRowIndex': row_index,
                            'startColumnIndex': col_index - 1,
                            'endColumnIndex': col_index,
                        },
                        'pasteType': 'PASTE_DATA_VALIDATION',
                    },
                }
            )
        copied_source_validation = True

    if not copied_source_validation:
        requests.extend([
            _validation_request(ws.id, row_index, 4, FULL_STATUS_VALUES),
            _validation_request(ws.id, row_index, 5, BAREBONES_STATUS_VALUES),
        ])

        full_color = _status_colors(ws.cell(row_index, 4).value)
        bare_color = _status_colors(ws.cell(row_index, 5).value)
        if full_color:
            requests.append(_format_request(ws.id, row_index, 4, *full_color))
        if bare_color:
            requests.append(_format_request(ws.id, row_index, 5, *bare_color))

    if requests:
        sh.batch_update({'requests': requests})

def submit_report(steam_link, map_name, author, report_type, notes, submitter, uem_version='', bb_version=''):
    if _submit_report_via_apps_script(steam_link, map_name, author, report_type, notes, submitter, uem_version, bb_version):
        return True

    ws = get_sheet()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().strftime('%d/%m/%Y')

    # Map report_type to dropdown text for Full / Barebones status columns.
    if report_type == 'Works':
        full_val = 'Yes'
        bare_val = f'Yes {bb_version}' if bb_version else ''
    elif report_type == 'WorksBugs':
        full_val = 'YES/BUGS (see notes)'
        bare_val = f'Yes/Bugs {bb_version}' if bb_version else ''
    elif report_type == 'Barebones':
        full_val = ''
        bare_val = f'Yes {bb_version}' if bb_version else ''
    elif report_type == 'BarebonesBugs':
        full_val = ''
        bare_val = f'Yes/Bugs {bb_version}' if bb_version else ''
    elif report_type == 'Broken':
        full_val = 'No'
        bare_val = f'No {bb_version}' if bb_version else ''
    elif report_type == 'Suggestion':
        full_val = ''
        bare_val = ''
    else:
        full_val = ''
        bare_val = ''

    link_formula = f'=HYPERLINK("{steam_link}", "{map_name}")' if steam_link and map_name else map_name
    row = [
        link_formula,                # Maps (HYPERLINK formula)
        author,                      # Map authors\n
        uem_version,                 # UEM Version (Full)
        full_val,                    # Full
        bare_val,                    # Barebones (V 1.1.22 Unless Stated)
        '',                          # Recommended
        '',                          # XP Value...
        '',                          # Map Filters
        today,                       # Date Tested Full\n(UK Date Format)
        notes,                       # Bugs to report/Notes
        steam_link,                  # Hyperlinks For AppSheet
        '',                          # Youtube Links
    ]
    table_range = f'A1:{num_cols_to_letters(len(ALL_HEADERS))}1'
    response = ws.append_row(row, value_input_option='USER_ENTERED', table_range=table_range)
    row_index = _row_from_append_response(response) or len(ws.col_values(1))
    _copy_sheet_dropdown_style(ws, row_index)

    metadata_ws = get_metadata_sheet(ws.spreadsheet)
    metadata_ws.append_row(
        [timestamp, map_name, steam_link, submitter, report_type, bb_version],
        value_input_option='USER_ENTERED',
        table_range=f'A1:{num_cols_to_letters(len(META_HEADERS))}1',
    )
    return True
