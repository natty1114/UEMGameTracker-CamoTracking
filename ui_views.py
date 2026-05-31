"""Small HTML view renderers for BO3 Tracker."""


def build_setup_html(css_content):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BO3 Tracker Setup</title>
        <style>""" + css_content + """</style>
    </head>
    <body>
        <div class="box">
            <h2>System Initialization</h2>
            <div class="label">LIVE DATA FILE (CurrentGame.json)</div>
            <div class="hint-text">Example: YOURDRIVELETTER:\\SteamLibrary\\steamapps\\common\\Call of Duty Black Ops III\\players\\311210\\2942053577\\CurrentGame.json</div>
            <div class="setup-path-row">
                <input type="text" id="livePath" readonly placeholder="Select File...">
                <button class="browse" onclick="browseLive()">BROWSE</button>
            </div>

            <div class="label">HISTORY ARCHIVE FOLDER</div>
            <div class="hint-text">Select a folder where match history will be saved.</div>
            <div class="setup-path-row">
                <input type="text" id="histPath" readonly placeholder="Select Folder...">
                <button class="browse" onclick="browseHist()">BROWSE</button>
            </div>

            <button class="save" onclick="save()">INITIALIZE SYSTEM</button>

            <div class="setup-restore">
                <div class="label">RESTORE FROM BACKUP</div>
                <div class="hint-text">Use this when moving to a new install or recovering a previous setup.</div>
                <div class="setup-action-row">
                    <button class="restore" onclick="restoreTrackerConfig()">RESTORE TRACKER CONFIG</button>
                    <button class="restore" onclick="restoreStats()">RESTORE UEM STATS</button>
                </div>
            </div>

            <div class="setup-restore">
                <div class="label">REMOTE CURRENTGAME SYNC</div>
                <div class="hint-text">Connect through the website relay when this PC does not have the active CurrentGame.json. Use the same shared password as the host.</div>
                <div class="setup-path-row">
                    <input type="password" id="remotePassword" placeholder="Shared password">
                </div>
                <button class="save" onclick="saveRemoteRelay()">CONNECT VIA WEBSITE RELAY</button>
            </div>
        </div>
        <script>
            function browseLive() {
                window.pywebview.api.browse_live_file().then(path => {
                    if(path) document.getElementById('livePath').value = path;
                });
            }
            function browseHist() {
                window.pywebview.api.browse_history_folder().then(path => {
                    if(path) document.getElementById('histPath').value = path;
                });
            }
            function save() {
                const live = document.getElementById('livePath').value;
                const hist = document.getElementById('histPath').value;
                if (!live || !hist) { alert("Please select both the file and the folder."); return; }
                window.pywebview.api.save_config(live, hist);
            }
            function saveRemoteRelay() {
                const password = document.getElementById('remotePassword').value;
                const hist = document.getElementById('histPath').value;
                if (!password || !hist) { alert("Please enter password and history folder."); return; }
                window.pywebview.api.save_remote_relay_sync_config(password, hist, '', '');
            }
            function restoreTrackerConfig() {
                const confirmed = confirm(
                    'Restore BO3 Tracker config from a backup zip?\\n\\n' +
                    'This can restore your saved paths, settings, challenge progress, best matches, and local tracker files.'
                );
                if (!confirmed) return;
                window.pywebview.api.restore_tracker_config(true).then(res => {
                    alert(res.msg || (res.success ? 'Tracker config restored.' : 'Tracker config restore failed.'));
                });
            }
            function restoreStats() {
                const live = document.getElementById('livePath').value;
                if (!live) {
                    alert('Select CurrentGame.json first so the tracker can find your BO3 players folder.');
                    return;
                }
                const confirmed = confirm(
                    'Restore UEM player stats from a backup zip?\\n\\n' +
                    'This can replace stats_zm_*.cgp files in your BO3 players folder. A safety backup is created first when existing files are found.'
                );
                if (!confirmed) return;
                window.pywebview.api.restore_player_stats(live).then(res => {
                    alert(res.msg || (res.success ? 'UEM stats restored.' : 'UEM stats restore failed.'));
                });
            }
        </script>
    </body>
    </html>
    """


def build_unified_overlay_html(initial_theme_json, initial_scale_json="1.0"):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --overlay-bg: #0b0c10;
                --overlay-panel: #0b0c10;
                --overlay-border: #66fcf1;
                --overlay-title: #66fcf1;
                --overlay-text: #ffffff;
                --overlay-muted: #777777;
                --overlay-damage: #ff9d00;
                --overlay-divider: #333333;
                --overlay-fallback: #333333;
                --overlay-shadow: 0 0 10px rgba(102, 252, 241, 0.25);
                --overlay-scale: 1;
            }
            html, body {
                margin: 0; padding: 0; overflow: hidden;
                width: 100%; height: 100%;
                background-color: var(--overlay-bg) !important;
            }
            #unified-box {
                display: inline-flex; flex-direction: column;
                background: var(--overlay-panel); border: 2px solid var(--overlay-border);
                padding: calc(12px * var(--overlay-scale)); box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif; color: var(--overlay-text);
                width: 100%; min-height: 100vh; height: auto;
                box-shadow: var(--overlay-shadow);
            }
            #perk-area {
                display: flex; flex-wrap: wrap; justify-content: center;
                gap: calc(5px * var(--overlay-scale));
                margin-bottom: calc(10px * var(--overlay-scale));
                min-height: calc(45px * var(--overlay-scale));
            }
            .perk-item img {
                width: calc(40px * var(--overlay-scale));
                height: calc(40px * var(--overlay-scale));
                object-fit: contain;
                filter: drop-shadow(0 0 2px rgba(0,0,0,0.5));
            }
            .perk-fallback {
                width: calc(40px * var(--overlay-scale));
                height: calc(40px * var(--overlay-scale));
                background: var(--overlay-fallback); color: var(--overlay-text);
                display: flex; align-items: center; justify-content: center;
                font-size: calc(10px * var(--overlay-scale));
                border-radius: 50%; border: 1px solid var(--overlay-border);
            }
            #damage-area {
                border-top: 1px solid var(--overlay-divider);
                padding-top: calc(8px * var(--overlay-scale));
            }
            #rank-area,
            #xp-area,
            #progress-area {
                border-top: 1px solid var(--overlay-divider);
                padding-top: calc(8px * var(--overlay-scale));
                margin-top: calc(8px * var(--overlay-scale));
                color: var(--overlay-title);
                font-size: calc(12px * var(--overlay-scale));
                font-weight: 700;
                text-align: center;
                white-space: nowrap;
            }
            #rank-area {
                color: var(--overlay-text);
                font-size: calc(11px * var(--overlay-scale));
                line-height: 1.35;
            }
            .rank-tier {
                color: var(--overlay-title);
                font-size: calc(10px * var(--overlay-scale));
                margin-top: calc(2px * var(--overlay-scale));
            }
            .xp-muted { color: var(--overlay-muted); }
            .level-ups { color: var(--overlay-title); }
            .progress-label {
                display: flex; justify-content: space-between; align-items: center;
                color: var(--overlay-text);
                font-size: calc(10px * var(--overlay-scale));
                margin-bottom: calc(5px * var(--overlay-scale));
            }
            .progress-track {
                width: 100%; height: calc(7px * var(--overlay-scale)); overflow: hidden;
                background: rgba(255,255,255,0.14); border: 1px solid var(--overlay-divider);
                box-sizing: border-box;
            }
            .progress-fill {
                height: 100%; width: 0%;
                background: var(--overlay-title);
                box-shadow: 0 0 8px rgba(102, 252, 241, 0.35);
            }
            .title {
                font-size: calc(10px * var(--overlay-scale));
                color: var(--overlay-title);
                margin-bottom: calc(5px * var(--overlay-scale));
                letter-spacing: 1px; font-weight: bold; text-transform: uppercase;
            }
            .row {
                display: flex; justify-content: space-between;
                margin-bottom: calc(4px * var(--overlay-scale));
                font-size: calc(12px * var(--overlay-scale));
            }
            .name {
                font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                max-width: calc(120px * var(--overlay-scale));
            }
            .dmg {
                color: var(--overlay-damage); font-weight: bold;
                margin-left: calc(10px * var(--overlay-scale));
            }
            .overlay-waiting {
                color: var(--overlay-muted);
                font-size: calc(11px * var(--overlay-scale));
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <div id="unified-box">
            <div id="perk-area"></div>
            <div id="damage-area">
                <div class="title">Top Weapon Damage (Player 1)</div>
                <div id="damage-list"></div>
            </div>
            <div id="xp-area"></div>
            <div id="rank-area"></div>
            <div id="progress-area"></div>
        </div>
        <script>
            const INITIAL_OVERLAY_THEME = """ + initial_theme_json + """;
            const INITIAL_OVERLAY_SCALE = """ + initial_scale_json + """;

            function applyOverlayTheme(theme) {
                if (!theme) return;
                const root = document.documentElement;
                const keys = {
                    bg: '--overlay-bg',
                    panel: '--overlay-panel',
                    border: '--overlay-border',
                    title: '--overlay-title',
                    text: '--overlay-text',
                    muted: '--overlay-muted',
                    damage: '--overlay-damage',
                    divider: '--overlay-divider',
                    fallback: '--overlay-fallback',
                    shadow: '--overlay-shadow'
                };
                Object.keys(keys).forEach(key => {
                    if (theme[key]) root.style.setProperty(keys[key], theme[key]);
                });
            }

            function setOverlayScale(scale) {
                const parsed = Number(scale);
                const safeScale = Number.isFinite(parsed) ? Math.max(0.7, Math.min(1.5, parsed)) : 1;
                document.documentElement.style.setProperty('--overlay-scale', safeScale);
            }

            function escapeHtml(value) {
                return String(value ?? '').replace(/[&<>"']/g, ch => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#39;'
                }[ch]));
            }

            function updateOverlay(perkHtml, damageItems, xpInfo, componentSettings) {
                const components = Object.assign({ perks: true, damage: true, rank: true, xp: true, progress: true }, componentSettings || {});
                const perkArea = document.getElementById('perk-area');
                if (components.perks) {
                    perkArea.innerHTML = perkHtml;
                    perkArea.style.display = 'flex';
                } else {
                    perkArea.innerHTML = "";
                    perkArea.style.display = 'none';
                }

                const damageArea = document.getElementById('damage-area');
                let dHtml = "";
                if (damageItems && damageItems.length > 0) {
                    damageItems.forEach(i => {
                        dHtml += `<div class="row"><div class="name">${i.name}</div><div><span>K: ${i.kills}</span><span class="dmg">${i.damage_str}</span></div></div>`;
                    });
                } else {
                    dHtml = "<div class='overlay-waiting'>Waiting for data...</div>";
                }
                document.getElementById('damage-list').innerHTML = dHtml;
                damageArea.style.display = components.damage ? 'block' : 'none';

                const rankArea = document.getElementById('rank-area');
                if (components.rank && xpInfo && (xpInfo.rank_label || xpInfo.level)) {
                    const rankLabel = escapeHtml(xpInfo.rank_label || 'Rank');
                    const rankTier = escapeHtml(xpInfo.rank_tier || '');
                    const level = escapeHtml(xpInfo.level || '0');
                    const levelUps = parseInt(xpInfo.level_ups || 0, 10);
                    const tierHtml = rankTier ? `<div class="rank-tier">${rankTier}</div>` : '';
                    const levelUpsHtml = levelUps > 0 ? ` <span class="xp-muted">|</span> <span class="level-ups">+${levelUps} Lvls</span>` : '';
                    rankArea.innerHTML = `${rankLabel} <span class="xp-muted">|</span> Level ${level}${levelUpsHtml}${tierHtml}`;
                    rankArea.style.display = 'block';
                } else {
                    rankArea.innerHTML = "";
                    rankArea.style.display = 'none';
                }

                const xpArea = document.getElementById('xp-area');
                const liveMatchXp = parseInt(xpInfo?.match_xp || 0, 10);
                if (components.xp && xpInfo && liveMatchXp > 0) {
                    xpArea.innerHTML = `(+${xpInfo.match_xp} Match XP <span class="xp-muted">|</span> ${xpInfo.xpm} XP/min)`;
                    xpArea.style.display = 'block';
                } else {
                    xpArea.innerHTML = "";
                    xpArea.style.display = 'none';
                }

                const progressArea = document.getElementById('progress-area');
                const levelXp = parseInt(xpInfo?.level_xp || 0, 10);
                const requiredXp = parseInt(xpInfo?.level_xp_required || 0, 10);
                const rawPct = Number(xpInfo?.level_progress_pct || 0);
                const pct = Math.max(0, Math.min(100, Number.isFinite(rawPct) ? rawPct : 0));
                if (components.progress && xpInfo && requiredXp > 0) {
                    progressArea.innerHTML = `
                        <div class="progress-label">
                            <span>Rank Progress</span>
                            <span>${levelXp.toLocaleString()} / ${requiredXp.toLocaleString()} XP</span>
                        </div>
                        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>`;
                    progressArea.style.display = 'block';
                } else {
                    progressArea.innerHTML = "";
                    progressArea.style.display = 'none';
                }
            }

            applyOverlayTheme(INITIAL_OVERLAY_THEME);
            setOverlayScale(INITIAL_OVERLAY_SCALE);
        </script>
    </body>
    </html>
    """


def build_graph_overlay_html(initial_theme_json, initial_scale_json, chart_js_content):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --overlay-bg: #0b0c10;
                --overlay-panel: #0b0c10;
                --overlay-border: #66fcf1;
                --overlay-title: #66fcf1;
                --overlay-text: #ffffff;
                --overlay-muted: #777777;
                --overlay-damage: #ff9d00;
                --overlay-divider: #333333;
                --overlay-shadow: 0 0 10px rgba(102, 252, 241, 0.25);
                --overlay-scale: 1;
            }
            html, body {
                margin: 0; padding: 0; overflow: hidden;
                width: 100%; height: 100%;
                background-color: var(--overlay-bg) !important;
            }
            #graph-box {
                display: inline-flex; flex-direction: column;
                background: var(--overlay-panel); border: 2px solid var(--overlay-border);
                padding: calc(8px * var(--overlay-scale)); box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif; color: var(--overlay-text);
                width: 100%; min-height: 100vh; height: auto;
                box-shadow: var(--overlay-shadow);
            }
            .graph-container {
                border-top: 1px solid var(--overlay-divider);
                padding-top: calc(6px * var(--overlay-scale));
                margin-top: calc(6px * var(--overlay-scale));
            }
            .graph-title {
                font-size: calc(10px * var(--overlay-scale));
                color: var(--overlay-title);
                margin-bottom: calc(4px * var(--overlay-scale));
                letter-spacing: 1px; font-weight: bold; text-transform: uppercase;
                text-align: center;
            }
            .graph-canvas-wrap {
                width: 100%; height: calc(90px * var(--overlay-scale));
            }
            .graph-canvas-wrap canvas {
                width: 100% !important; height: 100% !important;
            }
            .graph-empty {
                color: var(--overlay-muted);
                font-size: calc(11px * var(--overlay-scale));
                font-style: italic; text-align: center;
                padding: calc(20px * var(--overlay-scale));
            }
            .graph-empty-top {
                border-top: 1px solid var(--overlay-divider);
                padding-top: calc(6px * var(--overlay-scale));
                margin-top: calc(6px * var(--overlay-scale));
            }
        </style>
        <script>/* chart.js */""" + chart_js_content + """</script>
    </head>
    <body>
        <div id="graph-box">
            <div id="graph-xpm-container" class="graph-container" style="display:none">
                <div class="graph-title">XP per Minute</div>
                <div class="graph-canvas-wrap"><canvas id="xpmChart"></canvas></div>
            </div>
            <div id="graph-roundxp-container" class="graph-container" style="display:none">
                <div class="graph-title">XP per Round</div>
                <div class="graph-canvas-wrap"><canvas id="roundXpChart"></canvas></div>
            </div>
            <div id="graph-zpm-container" class="graph-container" style="display:none">
                <div class="graph-title">Zombies per Minute</div>
                <div class="graph-canvas-wrap"><canvas id="zpmChart"></canvas></div>
            </div>
            <div id="graph-empty" class="graph-empty graph-empty-top" style="display:none">Enable a graph in overlay settings</div>
        </div>
        <script>
            const INITIAL_GRAPH_THEME = """ + initial_theme_json + """;
            const INITIAL_GRAPH_SCALE = """ + initial_scale_json + """;

            let xpmChartInstance = null;
            let roundXpChartInstance = null;
            let zpmChartInstance = null;

            function applyGraphOverlayTheme(theme) {
                if (!theme) return;
                const root = document.documentElement;
                const keys = {
                    bg: '--overlay-bg', panel: '--overlay-panel',
                    border: '--overlay-border', title: '--overlay-title',
                    text: '--overlay-text', muted: '--overlay-muted',
                    damage: '--overlay-damage', divider: '--overlay-divider',
                    fallback: '--overlay-fallback', shadow: '--overlay-shadow'
                };
                Object.keys(keys).forEach(key => {
                    if (theme[key]) root.style.setProperty(keys[key], theme[key]);
                });
            }

            function setGraphOverlayScale(scale) {
                const parsed = Number(scale);
                const safeScale = Number.isFinite(parsed) ? Math.max(0.7, Math.min(1.5, parsed)) : 1;
                document.documentElement.style.setProperty('--overlay-scale', safeScale);
            }

            function getGraphColors() {
                const root = getComputedStyle(document.documentElement);
                return {
                    line: root.getPropertyValue('--overlay-title').trim() || '#66fcf1',
                    grid: root.getPropertyValue('--overlay-divider').trim() || '#333',
                    text: root.getPropertyValue('--overlay-text').trim() || '#fff',
                    muted: root.getPropertyValue('--overlay-muted').trim() || '#777',
                    bar: root.getPropertyValue('--overlay-damage').trim() || '#ff9d00',
                    bg: root.getPropertyValue('--overlay-bg').trim() || '#0b0c10',
                };
            }

            function createOrUpdateChart(canvasId, labels, data, type, existingInstance) {
                const canvas = document.getElementById(canvasId);
                if (!canvas) return null;
                const colors = getGraphColors();

                if (existingInstance) {
                    existingInstance.data.labels = labels;
                    existingInstance.data.datasets[0].data = data;
                    existingInstance.update('none');
                    return existingInstance;
                }

                const isBar = type === 'bar';
                return new Chart(canvas.getContext('2d'), {
                    type: type,
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            borderColor: colors.line,
                            backgroundColor: isBar ? colors.bar : colors.line + '30',
                            borderWidth: 1.5,
                            pointRadius: 0,
                            pointHitRadius: 0,
                            fill: !isBar,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false, grid: { display: false } },
                            y: {
                                display: true,
                                grid: { color: colors.grid, drawBorder: false },
                                ticks: { color: colors.muted, font: { size: 8 }, maxTicksLimit: 5, beginAtZero: true }
                            }
                        }
                    }
                });
            }

            function showGraphComponent(component, visible) {
                const el = document.getElementById(component);
                if (el) el.style.display = visible ? 'block' : 'none';
                const emptyEl = document.getElementById('graph-empty');
                if (emptyEl) {
                    const anyVisible = ['graph-xpm-container', 'graph-roundxp-container', 'graph-zpm-container']
                        .some(id => { const e = document.getElementById(id); return e && e.style.display !== 'none'; });
                    emptyEl.style.display = anyVisible ? 'none' : 'block';
                }
            }

            function updateGraphOverlay(data) {
                if (!data) return;
                if (data.xpmLabels && data.xpmData) {
                    xpmChartInstance = createOrUpdateChart('xpmChart', data.xpmLabels, data.xpmData, 'line', xpmChartInstance);
                }
                if (data.roundXpLabels && data.roundXpData) {
                    roundXpChartInstance = createOrUpdateChart('roundXpChart', data.roundXpLabels, data.roundXpData, 'bar', roundXpChartInstance);
                }
                if (data.zpmLabels && data.zpmData) {
                    zpmChartInstance = createOrUpdateChart('zpmChart', data.zpmLabels, data.zpmData, 'line', zpmChartInstance);
                }
                if (data.components) {
                    showGraphComponent('graph-xpm-container', data.components.xpm_graph);
                    showGraphComponent('graph-roundxp-container', data.components.roundxp_graph);
                    showGraphComponent('graph-zpm-container', data.components.zpm_graph);
                }
            }

            applyGraphOverlayTheme(INITIAL_GRAPH_THEME);
            setGraphOverlayScale(INITIAL_GRAPH_SCALE);
        </script>
    </body>
    </html>
    """


def build_challenge_overlay_html(initial_theme_json, initial_scale_json="1.0"):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --overlay-bg: #0b0c10;
                --overlay-panel: #0b0c10;
                --overlay-border: #66fcf1;
                --overlay-title: #66fcf1;
                --overlay-text: #ffffff;
                --overlay-muted: #777777;
                --overlay-damage: #ff9d00;
                --overlay-divider: #333333;
                --overlay-shadow: 0 0 10px rgba(102, 252, 241, 0.25);
                --overlay-scale: 1;
            }
            html, body {
                margin: 0; padding: 0; overflow: hidden;
                width: 100%; height: 100%;
                background-color: var(--overlay-bg) !important;
            }
            #challenge-box {
                display: inline-flex; flex-direction: column;
                background: var(--overlay-panel); border: 2px solid var(--overlay-border);
                padding: calc(10px * var(--overlay-scale)); box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif; color: var(--overlay-text);
                width: 100%; min-height: 100vh; height: auto;
                box-shadow: var(--overlay-shadow);
            }
            .challenge-overlay-title {
                color: var(--overlay-title);
                font-size: calc(10px * var(--overlay-scale));
                font-weight: 800;
                text-transform: uppercase;
                margin-bottom: calc(8px * var(--overlay-scale));
                letter-spacing: 1px;
            }
            .challenge-item {
                border-top: 1px solid var(--overlay-divider);
                padding-top: calc(7px * var(--overlay-scale));
                margin-top: calc(7px * var(--overlay-scale));
            }
            .challenge-item:first-child {
                border-top: 0;
                padding-top: 0;
                margin-top: 0;
            }
            .challenge-head {
                display: flex;
                justify-content: space-between;
                gap: calc(8px * var(--overlay-scale));
                align-items: flex-start;
                margin-bottom: calc(4px * var(--overlay-scale));
            }
            .challenge-name {
                color: var(--overlay-text);
                font-size: calc(12px * var(--overlay-scale));
                font-weight: 800;
                line-height: 1.2;
            }
            .challenge-cat {
                color: var(--overlay-title);
                font-size: calc(9px * var(--overlay-scale));
                font-weight: 800;
                text-transform: uppercase;
                white-space: nowrap;
            }
            .challenge-desc {
                color: var(--overlay-muted);
                font-size: calc(10px * var(--overlay-scale));
                line-height: 1.25;
                margin-bottom: calc(6px * var(--overlay-scale));
            }
            .challenge-progress-label {
                display: flex;
                justify-content: space-between;
                gap: calc(8px * var(--overlay-scale));
                color: var(--overlay-text);
                font-size: calc(10px * var(--overlay-scale));
                margin-bottom: calc(4px * var(--overlay-scale));
            }
            .challenge-track {
                width: 100%;
                height: calc(7px * var(--overlay-scale));
                overflow: hidden;
                background: rgba(255,255,255,0.14);
                border: 1px solid var(--overlay-divider);
                box-sizing: border-box;
            }
            .challenge-fill {
                height: 100%;
                width: 0%;
                background: var(--overlay-title);
                box-shadow: 0 0 8px rgba(102, 252, 241, 0.35);
            }
            .challenge-complete .challenge-fill {
                background: var(--overlay-damage);
            }
            .challenge-empty {
                color: var(--overlay-muted);
                font-size: calc(11px * var(--overlay-scale));
                font-style: italic;
                line-height: 1.35;
            }
        </style>
    </head>
    <body>
        <div id="challenge-box">
            <div class="challenge-overlay-title">Tracked Challenges</div>
            <div id="challenge-list"><div class="challenge-empty">Select up to 3 challenges in the tracker.</div></div>
        </div>
        <script>
            const INITIAL_CHALLENGE_THEME = """ + initial_theme_json + """;
            const INITIAL_CHALLENGE_SCALE = """ + initial_scale_json + """;

            function applyChallengeOverlayTheme(theme) {
                if (!theme) return;
                const root = document.documentElement;
                const keys = {
                    bg: '--overlay-bg',
                    panel: '--overlay-panel',
                    border: '--overlay-border',
                    title: '--overlay-title',
                    text: '--overlay-text',
                    muted: '--overlay-muted',
                    damage: '--overlay-damage',
                    divider: '--overlay-divider',
                    shadow: '--overlay-shadow'
                };
                Object.keys(keys).forEach(key => {
                    if (theme[key]) root.style.setProperty(keys[key], theme[key]);
                });
            }

            function setChallengeOverlayScale(scale) {
                const parsed = Number(scale);
                const safeScale = Number.isFinite(parsed) ? Math.max(0.7, Math.min(1.5, parsed)) : 1;
                document.documentElement.style.setProperty('--overlay-scale', safeScale);
            }

            function escapeHtml(value) {
                return String(value ?? '').replace(/[&<>"']/g, ch => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#39;'
                }[ch]));
            }

            function updateChallengeOverlay(items) {
                const list = document.getElementById('challenge-list');
                const rows = Array.isArray(items) ? items.slice(0, 3) : [];
                if (!rows.length) {
                    list.innerHTML = "<div class='challenge-empty'>Select up to 3 challenges in the tracker.</div>";
                    return;
                }
                list.innerHTML = rows.map(item => {
                    const pct = Math.max(0, Math.min(100, Number(item.progress_pct || 0)));
                    const progress = Number(item.progress || 0).toLocaleString();
                    const target = Number(item.target || 0).toLocaleString();
                    const doneClass = item.completed ? ' challenge-complete' : '';
                    return `
                        <div class="challenge-item${doneClass}">
                            <div class="challenge-head">
                                <div class="challenge-name">${escapeHtml(item.title || 'Challenge')}</div>
                                <div class="challenge-cat">${escapeHtml(item.cat || '')}</div>
                            </div>
                            <div class="challenge-desc">${escapeHtml(item.desc || '')}</div>
                            <div class="challenge-progress-label">
                                <span>${item.completed ? 'Complete' : 'Progress'}</span>
                                <span>${progress} / ${target}</span>
                            </div>
                            <div class="challenge-track"><div class="challenge-fill" style="width:${pct}%"></div></div>
                        </div>`;
                }).join('');
            }

            applyChallengeOverlayTheme(INITIAL_CHALLENGE_THEME);
            setChallengeOverlayScale(INITIAL_CHALLENGE_SCALE);
        </script>
    </body>
    </html>
    """


def build_xp_debugger_html():
    return """
    <html>
    <head>
        <style>
            body { margin:0; background:#07070d; color:#eee; font-family:Consolas, monospace; font-size:12px; }
            header { display:flex; justify-content:space-between; align-items:center; padding:12px 14px; border-bottom:1px solid #28213a; background:#11101a; }
            h1 { font-size:15px; margin:0; color:#c084fc; letter-spacing:0; }
            .status { color:#66fcf1; font-size:11px; }
            table { width:100%; border-collapse:collapse; }
            th, td { padding:7px 8px; border-bottom:1px solid #1e1b2c; text-align:left; white-space:nowrap; }
            th { color:#aaa; background:#0d0c14; position:sticky; top:0; }
            tr.rank-change td { color:#ffcc66; }
            tr.xp-recovery td { color:#66fcf1; }
            .num { text-align:right; }
            .zero { color:#ff7777; }
        </style>
    </head>
    <body>
        <header>
            <h1>XP Round Debugger</h1>
            <div class="status" id="status">Waiting for live XP updates...</div>
        </header>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Game ID</th>
                    <th>Map</th>
                    <th>Player</th>
                    <th class="num">Round</th>
                    <th class="num">Ult</th>
                    <th class="num">Abs</th>
                    <th class="num">Leg</th>
                    <th class="num">Prestige</th>
                    <th class="num">Level</th>
                    <th class="num">Level XP</th>
                    <th class="num">Tick XP</th>
                    <th class="num">Round XP</th>
                    <th class="num">Match XP</th>
                    <th>XP Math</th>
                    <th>Rank Change</th>
                </tr>
            </thead>
            <tbody id="rows"></tbody>
        </table>
        <script>
            function fmt(n) {
                if (n === null || n === undefined) return "";
                return Number(n).toLocaleString();
            }

            function esc(v) {
                return String(v ?? "").replace(/[&<>"']/g, ch => ({
                    "&": "&amp;",
                    "<": "&lt;",
                    ">": "&gt;",
                    '"': "&quot;",
                    "'": "&#39;"
                }[ch]));
            }

            function updateXpDebug(rows) {
                const body = document.getElementById("rows");
                document.getElementById("status").innerText = rows.length + " round snapshots";
                body.innerHTML = rows.map(r => {
                    const tickClass = r.tick_xp === 0 ? "zero" : "";
                    const roundClass = r.round_xp === 0 ? "zero" : "";
                    const rowClass = r.xp_recovery ? "xp-recovery" : (r.rank_changed ? "rank-change" : "");
                    return `<tr class="${rowClass}">
                        <td>${esc(r.updated_at)}</td>
                        <td title="${esc(r.game_id)}">${esc(r.short_game_id)}</td>
                        <td>${esc(r.map_name)}</td>
                        <td>${esc(r.player_id)}</td>
                        <td class="num">${fmt(r.round)}</td>
                        <td class="num">${fmt(r.ultimate)}</td>
                        <td class="num">${fmt(r.absolute)}</td>
                        <td class="num">${fmt(r.legend)}</td>
                        <td class="num">${fmt(r.prestige)}</td>
                        <td class="num">${fmt(r.level)}</td>
                        <td class="num">${fmt(r.current_xp)}</td>
                        <td class="num ${tickClass}">${fmt(r.tick_xp)}</td>
                        <td class="num ${roundClass}">${fmt(r.round_xp)}</td>
                        <td class="num">${fmt(r.total_match_xp)}</td>
                        <td>${esc(r.xp_math_label)}</td>
                        <td>${esc(r.rank_change_label)}</td>
                    </tr>`;
                }).join("");
            }
        </script>
    </body>
    </html>
    """
