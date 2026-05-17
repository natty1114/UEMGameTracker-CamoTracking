import webview

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HELP - UEM Database</title>
    <style>
        :root {
            --bg: #121212; --card: #1e1e1e; --text: #e0e0e0; --dim: #aaa;
            --gold: #d4af37; --green: #5cb85c; --red: #d9534f;
            --border: #333; --btn: #222;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg); color: var(--text);
            font-family: 'Segoe UI', sans-serif; padding: 24px 32px;
            line-height: 1.7;
        }
        h1 { color: var(--gold); font-size: 1.6rem; text-transform: uppercase; letter-spacing: 2px; border-bottom: 2px solid var(--gold); padding-bottom: 12px; margin-bottom: 20px; }
        h2 { color: var(--gold); font-size: 1.15rem; margin: 18px 0 8px; text-transform: uppercase; letter-spacing: 1px; }
        p { margin-bottom: 10px; color: var(--text); }
        .section { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; }
        .keys { display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; font-size: 0.9rem; margin: 8px 0; }
        .key { color: var(--gold); font-weight: bold; white-space: nowrap; }
        .val { color: var(--dim); }
        code { background: #000; color: var(--green); padding: 1px 6px; border-radius: 3px; font-size: 0.85rem; }
        .tag { display: inline-block; background: #000; color: var(--gold); border: 1px solid var(--border); border-radius: 4px; padding: 1px 8px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
        footer { margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--border); color: var(--dim); font-size: 0.8rem; text-align: center; }
    </style>
</head>
<body>
    <h1>UEM DATABASE - HELP</h1>

    <div class="section">
        <h2>What is this?</h2>
        <p>The UEM (Ultimate Exile Mod) Database lets you browse custom Zombies maps that support the UEM mod. Each card shows a map's details including its author, UEM version, XP multiplier, and support status.</p>
    </div>

    <div class="section">
        <h2>Filters &amp; Search</h2>
        <div class="keys">
            <span class="key">Status</span><span class="val">Filter by <span class="tag">Full Support</span>, <span class="tag">Barebones</span>, or <span class="tag">Broken</span></span>
            <span class="key">Version</span><span class="val">Filter by specific UEM version number</span>
            <span class="key">XP</span><span class="val">Show only <span class="tag">Nerfed</span> (&lt;1.03x) or <span class="tag">Non-nerfed</span> (1.03+) maps</span>
            <span class="key">Search</span><span class="val">Search by map name, author, tags, or Steam link</span>
            <span class="key">Favorites</span><span class="val">Show only maps you've starred</span>
        </div>
    </div>

    <div class="section">
        <h2>Favorites</h2>
        <p>Click the star on any card image to add it to your favorites list. Starred maps show a filled star. Use the <span class="tag">Favorites</span> filter to show only your favorited maps. Favorites are saved automatically and persist between sessions.</p>
    </div>

    <div class="section">
        <h2>Submitting Reports</h2>
        <p>Use the plus button in the header to submit a report, confirm compatibility, or suggest a new map. Paste a Steam Workshop link first; the app will auto-fill the map name and author from the local database or Steam when possible.</p>
        <div class="keys">
            <span class="key">Report Type</span><span class="val">Choose full support, barebones, barebones with bugs, broken, or suggestion</span>
            <span class="key">Full Version</span><span class="val">Only recent full UEM versions are shown, with the current version selected by default</span>
            <span class="key">Barebones Version</span><span class="val">Only recent barebones versions are shown, with the current version selected by default</span>
            <span class="key">Notes</span><span class="val">Add bug details or testing notes for the sheet reviewer</span>
        </div>
    </div>

    <div class="section">
        <h2>Google Sheets Workflow</h2>
        <p>Submitted rows are written to the <code>Submissions</code> tab using the same A:L columns as the main sheet. The Full and Barebones status cells use the same dropdown-style values as the main tracker, so rows can be copied directly into the main sheet without dragging extra fields along.</p>
        <p>Submission tracking details are stored separately on the <code>Submission Metadata</code> tab. That keeps timestamp, submitter, report type, and barebones-version metadata away from the copyable submission rows.</p>
    </div>

    <div class="section">
        <h2>Card Actions</h2>
        <div class="keys">
            <span class="key">Details</span><span class="val">Opens a modal with full map info including notes/bugs</span>
            <span class="key">Steam</span><span class="val">Opens the map's Steam Workshop page in your browser</span>
            <span class="key">YouTube</span><span class="val">Opens a YouTube video (if available) for the map</span>
        </div>
    </div>

    <div class="section">
        <h2>Themes</h2>
        <p>Use the theme dropdown in the header to switch between 19 visual themes. Each theme changes the color palette, font, and cursor. Your theme choice is saved and restored next time you open the app.</p>
    </div>

    <div class="section">
        <h2>Pagination</h2>
        <p>12 maps are shown per page. Use the arrow buttons in the footer to navigate between pages, or jump +/-5 pages with the quick buttons.</p>
    </div>

    <footer>UEM CLASSIFIED DATABASE V.3.2 // HELP v1.1</footer>
</body>
</html>
"""

def main():
    window = webview.create_window('UEM Database - Help', html=HTML, width=720, height=780, background_color='#121212')
    webview.start()

if __name__ == '__main__':
    main()
