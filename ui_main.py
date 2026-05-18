"""Main dashboard HTML renderer for BO3 Tracker."""


def build_main_app_html(css_content, app_config, app_version, global_stats_prompt_version, chart_js_content=""):
    
    overlays_on = app_config.get('overlays_enabled', False)
    chk_str = "checked" if overlays_on else ""
    xp_debug_on = app_config.get('xp_debugger_enabled', False)
    xp_debug_chk_str = "checked" if xp_debug_on else ""
    xp_recovery_on = app_config.get('xp_overflow_recovery_enabled', False)
    xp_recovery_chk_str = "checked" if xp_recovery_on else ""
    workshop_images_on = app_config.get('workshop_images_enabled', True)
    workshop_images_chk_str = "checked" if workshop_images_on else ""
    workshop_images_js = "true" if workshop_images_on else "false"
    global_stats_on = app_config.get('global_stats_enabled', False)
    global_stats_chk_str = "checked" if global_stats_on else ""
    global_stats_js = "true" if global_stats_on else "false"
    global_stats_prompt_needed = app_config.get('global_stats_prompt_version') != global_stats_prompt_version
    global_stats_prompt_js = "true" if global_stats_prompt_needed else "false"
    discord_presence_on = app_config.get('discord_presence_enabled', False)
    discord_presence_chk_str = "checked" if discord_presence_on else ""
    overlay_components = app_config.get('overlay_components') or {}
    if not isinstance(overlay_components, dict):
        overlay_components = {}
    overlay_perks_chk_str = "checked" if overlay_components.get('perks', True) else ""
    overlay_damage_chk_str = "checked" if overlay_components.get('damage', True) else ""
    overlay_rank_chk_str = "checked" if overlay_components.get('rank', True) else ""
    overlay_xp_chk_str = "checked" if overlay_components.get('xp', True) else ""
    overlay_progress_chk_str = "checked" if overlay_components.get('progress', True) else ""
    graph_overlay_on = app_config.get('graph_overlay_enabled', False)
    graph_overlay_chk_str = "checked" if graph_overlay_on else ""
    graph_xpm_chk_str = "checked" if overlay_components.get('xpm_graph', False) else ""
    graph_roundxp_chk_str = "checked" if overlay_components.get('roundxp_graph', False) else ""
    graph_zpm_chk_str = "checked" if overlay_components.get('zpm_graph', False) else ""
    try:
        overlay_size_percent = int(float(app_config.get('overlay_size_percent', 100)))
    except (TypeError, ValueError):
        overlay_size_percent = 100
    overlay_size_percent = max(70, min(150, overlay_size_percent))
    overlay_size_value = str(overlay_size_percent)

    return """
    <!DOCTYPE html>
    <html>
    <head>
    <script>/* chart.js */""" + chart_js_content + """</script>

        <!-- FIREWALL 1: External CSS is now isolated -->
        <style>""" + css_content + """</style>

        <!-- Theme CSS injected here (after style.css so it can override) -->
        <style id="theme-injector"></style>

        <!-- FIREWALL 2: Theme-specific CSS handled by theme files in /themes/ -->
        <style id="dynamic-camo-styles"></style>
    </head>
    <body>
        <div class="privacy-modal-backdrop" id="global-stats-modal">
            <div class="privacy-modal">
                <h2>Contribute Anonymous Global Stats?</h2>
                <p>Version """ + global_stats_prompt_version + """ can help build a community global stats database from your archived match summaries. This is optional and can be changed later in Settings.</p>
                <ul>
                    <li>No personally identifiable information is collected.</li>
                    <li>No Steam ID, Windows username, file paths, profile files, or raw archive JSON are uploaded.</li>
                    <li>The app sends anonymous match summaries such as map, round, time, kills, XP, weapons, and career counters.</li>
                    <li>Uploads are deduplicated by anonymous hashes so changing the EXE should not create duplicate games.</li>
                </ul>
                <div class="privacy-modal-actions">
                    <button class="nav-btn-small modal-btn-muted" onclick="setGlobalStatsConsent(false)">NO THANKS</button>
                    <button class="nav-btn-small modal-btn-accent" onclick="setGlobalStatsConsent(true)">OPT IN</button>
                </div>
            </div>
        </div>
        <div class="sidebar">
            <div class="header" id="live-btn" onclick="switchTab('live')" data-i18n="navigation.live_game">LIVE GAME</div>
            <div class="nav-btn" id="camo-btn" onclick="switchTab('camo')" data-i18n="navigation.camo_matrix">CAMO MATRIX</div>
            <div class="nav-btn" id="career-btn" onclick="switchTab('career')" data-i18n="navigation.career_profile">CAREER PROFILE</div>
            <div class="nav-btn" id="bestmatches-btn" onclick="switchTab('bestmatches')" data-i18n="navigation.best_matches">BEST MATCHES</div>
            <div class="nav-btn" id="chal-btn" onclick="switchTab('challenges')" data-i18n="navigation.challenges">CHALLENGES</div>
            <div class="nav-btn" id="mapcompat-btn" onclick="openMapCompat()" data-i18n="navigation.map_compat">MAP COMPAT</div>
            <div class="sidebar-section-label" data-i18n="navigation.match_logs">MATCH LOGS</div>
            <div class="history-filters">
                <input id="history-search" class="history-filter-input" type="search" placeholder="Search map, player, ID" oninput="queueHistoryFilterUpdate()">
                <select id="history-map-filter" class="history-filter-input" onchange="applyHistoryFilters()">
                    <option value="">All maps</option>
                </select>
                <div class="history-date-row">
                    <input id="history-date-from" class="history-filter-input" type="date" onchange="applyHistoryFilters()" title="From date">
                    <input id="history-date-to" class="history-filter-input" type="date" onchange="applyHistoryFilters()" title="To date">
                </div>
                <select id="history-xp-range" class="history-filter-input" onchange="applyHistoryFilters()">
                    <option value="">All XP earned</option>
                </select>
                <div class="history-filter-actions">
                    <select id="history-sort" class="history-filter-input" onchange="applyHistoryFilters()">
                        <option value="newest">Newest</option>
                        <option value="oldest">Oldest</option>
                        <option value="map">Map A-Z</option>
                        <option value="round">Highest round</option>
                        <option value="xp">Highest XP</option>
                        <option value="xp_low">Lowest XP</option>
                    </select>
                    <button class="nav-btn-small history-clear-btn" onclick="clearHistoryFilters()">CLEAR</button>
                </div>
                <div id="history-filter-summary" class="history-filter-summary"></div>
            </div>
            <div class="list" id="history-list"></div>
            
            <div id="history-pagination" class="history-pagination">
                <button class="nav-btn-small history-page-btn history-page-prev" onclick="changeHistoryPage(-1)" data-i18n="buttons.prev">PREV</button>
                <span id="hist-page-info" class="history-page-info">1 / 1</span>
                <button class="nav-btn-small history-page-btn history-page-next" onclick="changeHistoryPage(1)" data-i18n="buttons.next">NEXT</button>
            </div>
            <div class="update-notice" id="update-notice">
                <strong id="update-title" data-i18n="update.available">UPDATE AVAILABLE</strong>
                <div id="update-summary" data-i18n="update.summary">A new BO3 Tracker build is ready.</div>
                <button class="nav-btn-small" onclick="startUpdate()" data-i18n="buttons.update_now">UPDATE NOW</button>
            </div>
            <div class="config-btn" id="help-btn" onclick="switchTab('help')" data-i18n="navigation.help_faq">HELP & FAQ</div>
            <div class="config-btn" id="customization-btn" onclick="switchTab('customization')" data-i18n="navigation.customization">CUSTOMIZATION</div>
            <div class="config-btn" id="settings-btn" onclick="switchTab('settings')" data-i18n="navigation.settings">SETTINGS</div>
            <button type="button" class="donate-btn" onclick="openDonateLink()" title="Donate via PayPal">
                <span class="donate-badge" aria-hidden="true">P</span>
                <span data-i18n="buttons.donate_paypal">DONATE VIA PAYPAL</span>
            </button>
            <div class="app-version-label"><span data-i18n="common.version">VERSION</span> """ + app_version + """</div>
        </div>
        
        <div class="main-view">
            <div id="tab-live" class="tab-content active">
                <div id="d_status_bar" class="status-bar">CONNECTING...</div>
                <div id="d_nerf"></div>

                <div class="card live-mission-card">
                    <div id="live-workshop-container" class="live-workshop-container initially-hidden">
                        <img id="live-workshop-img" class="live-workshop-img initially-hidden" src="">
                    </div>
                    <div class="live-card-content">
                        <div class="card-title live-card-title-row">
                            <span data-i18n="live.current_mission">CURRENT MISSION</span>
                            <button id="best-match-btn" class="nav-btn-small best-match-action" onclick="addBestMatch()" data-i18n="buttons.add_best_match">ADD BEST MATCH</button>
                        </div>
                        <div class="live-mission-row">
                            <div class="live-mission-left">
                                <div>
                                    <div id="d_map" class="stat-big live-map-name">-</div>
                                    <div class="stat-sub"><span data-i18n="live.round">ROUND</span> <span id="d_round" class="round-value">0</span></div>
                                </div>
                            </div>
                         </div>
                         <div class="live-mission-details">
                              <div class="detail-row"><span data-i18n="live.time">TIME</span><span id="d_time">00:00</span></div>
                              <div class="detail-row"><span data-i18n="live.avg_round">AVG ROUND</span><span id="d_avg_time">0s</span></div> 
                              <div class="detail-row"><span>ZPM</span><span id="d_zpm">0</span></div>
                              <div class="detail-row"><span data-i18n="live.mode">MODE</span><span id="d_mode">-</span></div>
                              <div class="detail-row"><span data-i18n="common.version">VERSION</span><span id="d_version" class="version-value">-</span></div>
                         </div>
                    </div>
                 </div>

                <div id="player-tabs-container" class="player-tabs-container"></div>

                <div id="player-specific-content" class="initially-hidden">
                    <div class="stat-grid-2">
<div class="card">
                            <div class="card-title" data-i18n="live.service_record">SERVICE RECORD</div>
                            <div class="rank-summary-row">
                                <div class="rank-icon-row">
                                    <div id="d_prest_box" class="rank-icon-box initially-hidden">
                                        <img id="d_prest_icon" class="rank-icon-img" src="">
                                        <div class="rank-icon-label" data-i18n="common.prestige">PRESTIGE</div>
                                    </div>
                                    <div id="d_lvl_box" class="rank-icon-box initially-hidden">
                                        <img id="d_lvl_icon" class="rank-icon-img" src="">
                                        <div class="rank-icon-label" data-i18n="common.level">LEVEL</div>
                                    </div>
                                </div>
                                <div>
                                    <div id="d_rmain" class="stat-rank">-</div>
                                    <div id="d_title" class="rank-title">-</div>
                                    <div id="d_rsub" class="rank-subtitle">-</div>
                                </div>
                            </div>
                            <div class="rank-xp-section">
                                
                                <div class="detail-row xp-detail-row">
                                    <div class="xp-detail-header">
                                        <span><span data-i18n="live.xp_earned">XP EARNED</span> 
                                        <button onclick="toggleXpmGraph()" class="graph-toggle-btn graph-toggle-xpm">📊 XPM</button>
                                        <button onclick="toggleRoundXpGraph()" class="graph-toggle-btn graph-toggle-roundxp">📈 <span data-i18n="live.round_xp">ROUND XP</span></button>
                                        </span>
                                        <button onclick="toggleZpmGraph()" class="graph-toggle-btn graph-toggle-zpm" data-i18n="live.zpm">ZPM</button>
                                        <span id="d_xp">0</span>
                                    </div>

                                    <div id="xpm-graph-container" class="xpm-container-base initially-hidden">
                                        <button class="graph-popout-btn" onclick="toggleGraphPopout('xpm-graph-container', 'chart-scroll-wrapper', 'xpm')" data-i18n="buttons.popout_xpm">Pop-Out XPM</button>
                                        <button class="graph-popout-btn" onclick="toggleZpmOverlay()" data-i18n="buttons.overlay_zpm">Overlay ZPM</button>
                                        <div id="chart-scroll-wrapper" class="xpm-scroll-wrapper"> 
                                            <canvas id="xpmChart"></canvas> 
                                        </div>
                                    </div>

                                    <div id="roundxp-graph-container" class="xpm-container-base initially-hidden">
                                        <button class="graph-popout-btn" onclick="toggleGraphPopout('roundxp-graph-container', 'roundxp-scroll-wrapper', 'roundxp')" data-i18n="buttons.popout_round_xp">Pop-Out Round XP</button>
                                        <div id="roundxp-scroll-wrapper" class="xpm-scroll-wrapper"> 
                                            <canvas id="roundXpChart"></canvas> 
                                        </div>
                                    </div>
                                </div>
                                    <div id="zpm-graph-container" class="xpm-container-base initially-hidden">
                                        <button class="graph-popout-btn" onclick="toggleGraphPopout('zpm-graph-container', 'zpm-scroll-wrapper', 'zpm')" data-i18n="buttons.popout_zpm">Pop-Out ZPM</button>
                                        <div id="zpm-scroll-wrapper" class="xpm-scroll-wrapper"> 
                                            <canvas id="zpmChart"></canvas> 
                                        </div>
                                    </div>
                                <div class="detail-row"><span data-i18n="live.multiplier">MULTIPLIER</span><span id="d_mult" class="highlight-value">x1.0</span></div>
                                <div class="detail-row"><span data-i18n="common.gobblegums">GOBBLEGUMS</span><span id="d_gums" class="gum-value">0</span></div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-title" data-i18n="live.combat_efficiency">COMBAT EFFICIENCY</div>
                            <div class="stat-metric-grid">
                                <div><div class="stat-label" data-i18n="live.eliminations">ELIMINATIONS</div><div id="d_kills" class="stat-big">0</div></div>
                                <div><div class="stat-label" data-i18n="live.score">SCORE</div><div id="d_score" class="stat-big score-value">0</div></div>
                            </div>
                            <div class="detail-row"><span data-i18n="live.accuracy">ACCURACY</span><span><span id="d_acc">0</span>%</span></div>
                            <div class="detail-row"><span data-i18n="live.melee_equip">MELEE / EQUIP</span><span><span id="d_melee">0</span> / <span id="d_equip">0</span></span></div>
                            <div class="detail-row"><span data-i18n="live.downs">DOWNS</span><span id="d_downs" class="danger-value">0</span></div>
                        </div>
                    </div>

                    <div class="card full-width">
                        <div class="card-title" data-i18n="live.active_perks">ACTIVE PERKS</div>
                        <div id="d_perks" class="perk-container"></div>
                    </div>

                    <div class="card full-width">
                        <div class="card-title" data-i18n="live.armory_loadout">ARMORY & LOADOUT</div>
                        <div class="loadout-summary">
                            <span><span data-i18n="live.lethal">LETHAL</span>: <b id="d_leth" class="loadout-value">-</b></span>
                            <span><span data-i18n="live.tactical">TACTICAL</span>: <b id="d_tact" class="loadout-value">-</b></span>
                        </div>
                        <table>
                            <thead><tr><th data-i18n="common.weapon">WEAPON</th><th data-i18n="common.kills">KILLS</th><th data-i18n="common.hs">HS</th><th data-i18n="common.damage">DAMAGE</th><th data-i18n="common.status">STATUS</th></tr></thead>
                            <tbody id="d_weaps"></tbody>
                        </table>
                    </div>
                </div>
            </div>
           
           <div id="tab-camo" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1 data-i18n="camo.heading">Armory Matrix</h1>
                        <div class="header-subtitle"><span data-i18n="common.status">STATUS</span>: <span id="status-txt">DISCONNECTED</span></div>
                    </div>
                    <div class="header-actions">
                        <div id="user-display" class="user-badge" data-i18n="camo.guest">GUEST</div>
                        <button class="nav-btn-small btn-accent-spaced" onclick="askParentToBrowse()" data-i18n="buttons.load_file">LOAD FILE</button>
                    </div>
                </div>
               
                <div class="controls initially-hidden" id="controls-area">
                    <button class="nav-btn-small" onclick="changeMap(-1)" data-i18n="buttons.prev">PREV</button>
                    <select id="map-select" onchange="onMapSelect()"></select>
                    <button class="nav-btn-small" onclick="changeMap(1)" data-i18n="buttons.next">NEXT</button>
                    <input type="text" id="search-input" placeholder="Find weapon..." data-i18n-placeholder="common.find_weapon" onkeyup="onSearch()">
                </div>
               
                <div id="content-area">
                    <div class="empty-state">
                        <h3 data-i18n="camo.initialization_required">INITIALIZATION REQUIRED</h3>
                        <p data-i18n="camo.load_profile_help">Load your profile JSON to view and edit camo progress.</p>
                    </div>
                </div>
            </div>

            <div id="tab-career" class="tab-content">
                <div class="header-camo career-profile-header">
                    <div class="header-title-media">
                        <h1 data-i18n="career.heading">Career Dossier</h1>
                        <img id="emblem-display" class="emblem-display-header initially-hidden" src="">
                        <video id="emblem-display-video" class="emblem-display-header initially-hidden" autoplay loop muted playsinline></video>
                        <img id="card-display" class="card-display-header initially-hidden" src="">
                        <video id="card-display-video" class="card-display-header initially-hidden" autoplay loop muted playsinline></video>
                    </div>
                    <div class="header-actions">
                        <div class="header-subtitle" data-i18n="career.lifetime_stats">LIFETIME STATISTICS (PLAYER 1)</div>
                        <button class="nav-btn-small button-tall" onclick="openMapSelectionPage()" data-i18n="map_details.heading_short">MAP DETAILS</button>
                        <button class="nav-btn-small button-tall" onclick="switchTab('weaponusage')" data-i18n="weapon_usage.heading_short">WEAPON USAGE</button>
                    </div>
                </div>

                <div class="card career-rank-card" id="career-rank-card">
                    <div class="career-rank-content">
                        <div class="card-title" data-i18n="career.current_rank">CURRENT RANK</div>
                        <div class="rank-summary-row">
                            <div class="rank-icon-row">
                                <div id="career-prest-box" class="rank-icon-box initially-hidden">
                                    <img id="career-prest-icon" class="rank-icon-img" src="">
                                    <div class="rank-icon-label" data-i18n="common.prestige">PRESTIGE</div>
                                </div>
                                <div id="career-lvl-box" class="rank-icon-box initially-hidden">
                                    <img id="career-lvl-icon" class="rank-icon-img" src="">
                                    <div class="rank-icon-label" data-i18n="common.level">LEVEL</div>
                                </div>
                            </div>
                            <div>
                                <div id="career-rmain" class="career-rmain">-</div>
                                <div id="career-rsub" class="career-rsub">-</div>
                                <div id="career-title" class="career-title"></div>
                                <div id="career-map-name" class="career-map-name"></div>
                            </div>
                        </div>
                        <div class="progress-bar career-progress-bar">
                            <div id="career-xp-bar" class="fill career-xp-fill"></div>
                        </div>
                        <div class="career-xp-meta">
                            <span id="career-xp-text">0 / 0 XP</span>
                            <span id="career-xp-pct" class="career-xp-pct">0%</span>
                        </div>
                    </div>
                </div>

                <div class="stat-grid-2">
                    <div class="card">
                        <div class="card-title" data-i18n="career.combat_record">COMBAT RECORD</div>
                        <div class="detail-row"><span data-i18n="career.total_kills">TOTAL KILLS</span><span id="life_kills" class="highlight-large-value">0</span></div>
                        <div class="detail-row"><span data-i18n="common.headshots">HEADSHOTS</span><span id="life_headshots">0</span></div>
                        <div class="detail-row"><span data-i18n="career.precision">PRECISION</span><span id="life_hs_pct" class="orange-value">0%</span></div>
        <div class="subsection-divider">
                            <div class="detail-row"><span data-i18n="career.favorite_weapons">FAVORITE WEAPONS</span><span id="life_fav_gun" class="align-right">None</span></div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title" data-i18n="career.survivalist">SURVIVALIST</div>
                        <div class="detail-row"><span data-i18n="career.rounds_survived">ROUNDS SURVIVED</span><span id="life_rounds">0</span></div>
                        <div class="detail-row"><span data-i18n="career.time_played">TIME PLAYED</span><span id="life_time">0h 0m</span></div>
                        <div class="detail-row"><span data-i18n="career.matches_logged">MATCHES LOGGED</span><span id="life_matches">0</span></div>
                        <div class="detail-row"><span data-i18n="career.kills_per_down">KILLS PER DOWN</span><span id="life_kpd">0.0</span></div>
                    </div>
                </div>
                
                <div class="stat-grid-2">
    <div class="card">
        <div class="card-title" data-i18n="career.logistics">LOGISTICS</div>
        <div class="detail-row"><span data-i18n="career.doors_opened">DOORS OPENED</span><span id="life_doors">0</span></div>
        <div class="detail-row"><span data-i18n="common.gobblegums">GOBBLEGUMS</span><span id="life_gums" class="gum-value">0</span></div>
        <div class="detail-row"><span data-i18n="career.mystery_box">MYSTERY BOX</span><span id="life_box">0</span></div>
        <div class="detail-row"><span data-i18n="career.player_points_gained">PLAYER POINTS GAINED</span><span id="life_pts" class="gold-value">0</span></div>
    </div>
    <div class="card">
        <div class="card-title" data-i18n="career.personal_bests">PERSONAL BESTS (ROUNDS)</div>
        <div id="life_map_list" class="compact-scroll-list short-scroll-list">
        </div>
    </div>
</div>

               <div class="stat-grid-2 spaced-grid">
    <div class="card">
        <div class="card-title card-title-row">
            <span data-i18n="career.most_played_maps">MOST PLAYED MAPS</span>
            <select id="map-sort-toggle" class="compact-select" onchange="renderMostPlayedMaps()">
                <option value="matches" data-i18n="career.by_matches">By Matches</option>
                <option value="time" data-i18n="career.by_time">By Time</option>
            </select>
        </div>
        <div id="life_most_played" class="compact-scroll-list medium-scroll-list">
            <div class='muted-loading' data-i18n="career.loading_map_records">Loading map records...</div>
        </div>
    </div>
                    
                    <div class="card">
                        <div class="card-title" data-i18n="career.top_maps_xp">TOP MAPS BY HIGHEST MATCH XP</div>
                        <div id="top_xp_maps_list" class="compact-scroll-list medium-scroll-list">
                            <div class='muted-loading' data-i18n="career.loading_xp_records">Loading XP records...</div>
                        </div>
                    </div>
                </div>

            </div>

            <div id="tab-mapselection" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1 data-i18n="map_details.heading">Map Details</h1>
                        <div class="header-subtitle" data-i18n="map_details.selection_subtitle">SELECT AN ARCHIVED MAP TO INSPECT PLAYER 1 PERFORMANCE</div>
                    </div>
                    <div class="header-actions">
                        <button class="nav-btn-small button-tall" onclick="switchTab('career')" data-i18n="buttons.back_to_career">BACK TO CAREER</button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title card-title-row">
                        <span data-i18n="map_details.archived_maps">Archived Maps</span>
                        <div class="map-selection-controls">
                            <input id="map-selection-search" class="compact-search" type="text" placeholder="Find map..." data-i18n-placeholder="map_details.find_map" oninput="renderMapSelectionPage()">
                            <select id="map-selection-sort" class="compact-select" onchange="renderMapSelectionPage()">
                                <option value="matches" data-i18n="common.matches">Matches</option>
                                <option value="round" data-i18n="map_details.highest_round">Highest Round</option>
                                <option value="time" data-i18n="career.time_played">Time Played</option>
                                <option value="recent" data-i18n="map_details.recently_played">Recently Played</option>
                                <option value="name" data-i18n="map_details.map_name">Map Name</option>
                            </select>
                            <button class="nav-btn-small" onclick="refreshMapSelection()" data-i18n="buttons.refresh">REFRESH</button>
                        </div>
                    </div>
                    <div id="map-selection-grid" class="map-selection-grid">
                        <div class="muted-loading" data-i18n="career.loading_map_records">Loading map records...</div>
                    </div>
                    <div id="map-selection-pagination" class="map-selection-pagination"></div>
                </div>
            </div>

            <div id="tab-mapdetail" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1 id="map-detail-title" data-i18n="map_details.detail_heading">Map Detail</h1>
                        <div class="header-subtitle" data-i18n="map_details.detail_subtitle">PER-MAP ARCHIVED PERFORMANCE (PLAYER 1)</div>
                    </div>
                    <div class="header-actions">
                        <button class="nav-btn-small button-tall" onclick="openMapSelectionPage()" data-i18n="buttons.back_to_map_selection">MAP SELECTION</button>
                        <button class="nav-btn-small button-tall" onclick="switchTab('career')" data-i18n="buttons.back_to_career">BACK TO CAREER</button>
                        <button id="map-detail-workshop-btn" class="nav-btn-small button-tall initially-hidden" onclick="openMapDetailWorkshop()" data-i18n="buttons.open_workshop">OPEN WORKSHOP</button>
                    </div>
                </div>

                <div id="map-detail-body">
                    <div class="card">
                        <div class="muted-empty" data-i18n="map_details.select_map_hint">Select a map from Career Profile to inspect its archived performance.</div>
                    </div>
                </div>
            </div>

            <div id="tab-weaponusage" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1 data-i18n="weapon_usage.heading">Player 1 Weapon Usage</h1>
                        <div class="header-subtitle" data-i18n="weapon_usage.archived_stats">ARCHIVED WEAPON STATISTICS</div>
                    </div>
                    <button class="nav-btn-small button-tall" onclick="switchTab('career')" data-i18n="buttons.back_to_career">BACK TO CAREER</button>
                </div>

                <div class="stat-grid-3 weapon-usage-summary-grid">
                    <div class="card">
                        <div class="card-title" data-i18n="weapon_usage.weapons_used">WEAPONS USED</div>
                        <div id="weapon_usage_count" class="stat-big">0</div>
                    </div>
                    <div class="card">
                        <div class="card-title" data-i18n="weapon_usage.weapon_kills">WEAPON KILLS</div>
                        <div id="weapon_usage_kills" class="stat-big">0</div>
                    </div>
                    <div class="card">
                        <div class="card-title" data-i18n="weapon_usage.weapon_headshots">WEAPON HEADSHOTS</div>
                        <div id="weapon_usage_headshots" class="stat-big">0</div>
                    </div>
                </div>

                <div class="card weapon-category-card">
                    <div class="card-title" data-i18n="weapon_usage.kills_by_category">KILLS BY WEAPON CATEGORY</div>
                    <div class="weapon-category-chart-layout">
                        <div class="weapon-category-chart-wrap">
                            <canvas id="weaponCategoryKillsChart"></canvas>
                        </div>
                        <div id="weapon-category-kills-legend" class="weapon-category-legend">
                            <div class="muted-empty">Loading category mix...</div>
                        </div>
                    </div>
                </div>

                <div class="card weapon-category-card">
                    <div class="card-title" data-i18n="weapon_usage.damage_by_category">DAMAGE BY WEAPON CATEGORY</div>
                    <div class="weapon-category-chart-layout">
                        <div class="weapon-category-chart-wrap">
                            <canvas id="weaponCategoryDamageChart"></canvas>
                        </div>
                        <div id="weapon-category-damage-legend" class="weapon-category-legend">
                            <div class="muted-empty">Loading category mix...</div>
                        </div>
                    </div>
                </div>

                <div id="weapon-detail-card" class="card weapon-detail-card initially-hidden">
                    <div class="card-title card-title-row">
                        <span id="weapon-detail-title" data-i18n="weapon_usage.weapon_profile">WEAPON PROFILE</span>
                        <button class="nav-btn-small weapon-detail-close" onclick="closeWeaponDetail()" data-i18n="buttons.close">CLOSE</button>
                    </div>
                    <div id="weapon-detail-body">
                        <div class="muted-empty">Select a weapon to inspect its archived performance.</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title card-title-row">
                        <span data-i18n="weapon_usage.all_player_weapons">ALL PLAYER 1 WEAPONS</span>
                        <div class="weapon-usage-controls">
                            <input id="weapon-usage-search" class="compact-search" type="text" placeholder="Find weapon..." data-i18n-placeholder="common.find_weapon" oninput="renderWeaponUsageTable()">
                            <select id="weapon-usage-sort" class="compact-select" onchange="renderWeaponUsageTable()">
                                <option value="kills" data-i18n="common.kills">Kills</option>
                                <option value="headshots" data-i18n="common.headshots">Headshots</option>
                                <option value="damage" data-i18n="common.damage">Damage</option>
                                <option value="matches" data-i18n="common.matches">Matches</option>
                                <option value="headshot_pct" data-i18n="common.headshot_pct">Headshot %</option>
                            </select>
                        </div>
                    </div>
                    <div class="weapon-usage-table-wrap">
                        <table class="weapon-usage-table">
                            <thead>
                                <tr>
                                    <th data-i18n="common.weapon">Weapon</th>
                                    <th data-i18n="common.category">Category</th>
                                    <th data-i18n="common.kills">Kills</th>
                                    <th data-i18n="common.headshots">Headshots</th>
                                    <th data-i18n="common.hs_pct_short">HS%</th>
                                    <th data-i18n="common.damage">Damage</th>
                                    <th data-i18n="common.matches">Matches</th>
                                    <th data-i18n="weapon_usage.pap_uses">PaP Uses</th>
                                    <th data-i18n="weapon_usage.best_round">Best Round</th>
                                </tr>
                            </thead>
                            <tbody id="weapon-usage-list">
                                <tr><td colspan="9" class="muted-empty" data-i18n="weapon_usage.loading">Loading weapon usage...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div id="tab-bestmatches" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1 data-i18n="best_matches.heading">Best Matches</h1>
                        <div class="header-subtitle" data-i18n="best_matches.subtitle">PINNED MATCH RECORDS</div>
                    </div>
                    <button class="nav-btn-small button-tall" onclick="loadBestMatches()" data-i18n="buttons.refresh">REFRESH</button>
                </div>
                <div class="card">
                    <div class="card-title" data-i18n="best_matches.saved_links">SAVED MATCH LINKS</div>
                    <div id="best-matches-list" class="stacked-list">
                        <div class="muted-empty" data-i18n="best_matches.loading">Loading best matches...</div>
                    </div>
                </div>
            </div>

            <div id="tab-challenges" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1 data-i18n="challenges.heading">Active Operations</h1>
                        <div class="header-subtitle" data-i18n="challenges.subtitle">COMPLETE CHALLENGES TO UNLOCK REWARDS</div>
                    </div>
                    <div>
                        <button class="nav-btn-small" onclick="filterChallenges('operations')" data-i18n="challenges.operations">OPERATIONS</button>
                        <button class="nav-btn-small" onclick="filterChallenges('weekly')" data-i18n="challenges.weekly">WEEKLY</button>
                        <button class="nav-btn-small" onclick="filterChallenges('themes')" data-i18n="challenges.theme_intel">THEME INTEL</button>
                        <button class="nav-btn-small" onclick="filterChallenges('lifetime')" data-i18n="challenges.lifetime">LIFETIME</button>
                        <button class="nav-btn-small danger-action-spaced" onclick="resetOps()" data-i18n="buttons.reset">RESET</button>
                    </div>
                </div>
                <div id="challenge-list" class="chal-grid"></div>
            </div>

            <div id="tab-customization" class="tab-content">
                <div class="header-camo">
                    <h1 data-i18n="customization.heading">Customization</h1>
                </div>

                <div class="card">
                    <div class="card-title" data-settings-copy="visualCard" data-i18n="customization.themes">THEMES</div>
                    <div class="setting-help" data-settings-copy="visualHelp" data-i18n="customization.themes_help">Select a visual theme for the tracker:</div>
                    <div class="settings-inline-control">
                        <select id="theme-selector" class="flex-select">
                            <option value="default">Default Tactical</option>
                        </select>
                        <button class="nav-btn-small" onclick="applySelectedTheme()" data-i18n="buttons.apply">APPLY</button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title" data-settings-copy="cardIdentityCard" data-i18n="customization.playercards">PLAYERCARD SELECTIONS</div>
                    <div class="setting-help" data-settings-copy="cardIdentityHelp" data-i18n="customization.playercards_help">Select your active Calling Card:</div>
                    <div class="settings-inline-control align-center">
                        <div class="flex-fill">
                            <select id="card-selector" class="full-select" onchange="previewCard(this.value)">
                                <option value="default">None Equipped</option>
                            </select>
                            <img id="card-preview" src="" class="card-selector-img initially-hidden">
                            <video id="card-preview-video" class="card-selector-img initially-hidden" autoplay loop muted playsinline></video>
                        </div>
                        <button class="nav-btn-small button-xl" onclick="applySelectedCard()" data-i18n="buttons.equip">EQUIP</button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title" data-i18n="customization.emblems">EMBLEMS</div>
                    <div class="setting-help" data-i18n="customization.emblems_help">Select your active Emblem:</div>
                    <div class="settings-inline-control align-center">
                        <div class="flex-fill">
                            <select id="emblem-selector" class="full-select" onchange="previewEmblem(this.value)">
                                <option value="default">None Equipped</option>
                            </select>
                            <img id="emblem-preview" src="" class="emblem-selector-img initially-hidden">
                            <video id="emblem-preview-video" class="emblem-selector-img initially-hidden" autoplay loop muted playsinline></video>
                        </div>
                        <button class="nav-btn-small button-xl" onclick="applySelectedEmblem()" data-i18n="buttons.equip">EQUIP</button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title" data-settings-copy="overlayCard" data-i18n="customization.overlay_control">OVERLAY CONTROL</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-settings-copy="overlayTitle" data-i18n="customization.enable_live_overlay">Enable Live Overlay</div>
                            <div class="setting-description" data-settings-copy="overlayDescription" data-i18n="customization.overlay_description">Displays Perks and Top Damage in a single, smart-resizing window.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleOverlays(this)" """ + chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="overlay-component-settings">
                        <div class="setting-help" data-i18n="customization.overlay_sections">Overlay sections</div>
                        <div class="settings-row overlay-component-row overlay-size-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.overlay_size">Overlay Size</div>
                                <div class="setting-description" data-i18n="customization.overlay_size_description">Adjust the live overlay window and HUD scale.</div>
                            </div>
                            <div class="overlay-size-control">
                                <input id="overlay-size-slider" class="range-slider" type="range" min="70" max="150" step="5" value=""" + overlay_size_value + """ oninput="previewOverlaySize(this.value)" onchange="saveOverlaySize(this.value)">
                                <span id="overlay-size-value" class="range-value">""" + overlay_size_value + """%</span>
                            </div>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.perks">Perks</div>
                                <div class="setting-description" data-i18n="customization.perks_description">Show active perk icons.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleOverlayComponent('perks', this)" """ + overlay_perks_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.top_damage">Top Damage</div>
                                <div class="setting-description" data-i18n="customization.top_damage_description">Show the top weapon damage list.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleOverlayComponent('damage', this)" """ + overlay_damage_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.rank_level">Rank & Level</div>
                                <div class="setting-description" data-i18n="customization.rank_level_description">Show Master Prestige, level, and level-ups.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleOverlayComponent('rank', this)" """ + overlay_rank_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.match_xp">Match XP</div>
                                <div class="setting-description" data-i18n="customization.match_xp_description">Show match XP and XP/min.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleOverlayComponent('xp', this)" """ + overlay_xp_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.rank_progress">Rank Progress</div>
                                <div class="setting-description" data-i18n="customization.rank_progress_description">Show a mini bar for current level XP progress.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleOverlayComponent('progress', this)" """ + overlay_progress_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="card" style="margin-top:10px">
                    <div class="card-title" data-i18n="customization.graph_overlay">GRAPH OVERLAY</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-i18n="customization.enable_graph_overlay">Enable Graph Overlay</div>
                            <div class="setting-description" data-i18n="customization.graph_overlay_description">Separate window with mini live graphs (XPM, Round XP, ZPM).</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleGraphOverlays(this)" """ + graph_overlay_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="overlay-component-settings">
                        <div class="setting-help" data-i18n="customization.graph_sections">Graph sections</div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.xp_per_minute">XP per Minute</div>
                                <div class="setting-description" data-i18n="customization.xp_per_minute_description">Line chart of XP gained per minute of play.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleGraphOverlayComponent('xpm_graph', this)" """ + graph_xpm_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.xp_per_round">XP per Round</div>
                                <div class="setting-description" data-i18n="customization.xp_per_round_description">Bar chart showing XP gained each round.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleGraphOverlayComponent('roundxp_graph', this)" """ + graph_roundxp_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="settings-row overlay-component-row">
                            <div>
                                <div class="setting-title" data-i18n="customization.zombies_per_minute">Zombies per Minute</div>
                                <div class="setting-description" data-i18n="customization.zombies_per_minute_description">Line chart of ZPM (kill efficiency) over time.</div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" onchange="toggleGraphOverlayComponent('zpm_graph', this)" """ + graph_zpm_chk_str + """>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <div id="tab-settings" class="tab-content">
                <div class="header-camo">
                    <h1 data-settings-copy="heading" data-i18n="settings.heading">System Configuration</h1>
                </div>

                <div class="card">
                    <div class="card-title" data-settings-copy="updatesCard" data-i18n="settings.app_updates">APP UPDATES</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title">BO3 Tracker Version """ + app_version + """</div>
                            <div id="update-settings-status" class="update-status" data-i18n="settings.update_status">Checking GitHub releases in the background.</div>
                        </div>
                        <button class="nav-btn-small button-xl" onclick="checkForUpdates(true)" data-i18n="buttons.check">CHECK</button>
                    </div>
                    <button class="nav-btn-small full-width-action" onclick="rollbackLastUpdate()" data-i18n="buttons.rollback_last_update">ROLLBACK LAST UPDATE</button>
                </div>
                
                <div class="card">
                    <div class="card-title" data-settings-copy="backupCard" data-i18n="settings.backup_uem_stats">UEM STATS BACKUP</div>
                    <div class="setting-help" data-settings-copy="backupHelp" data-i18n="settings.backup_help">Create or restore a zip archive containing your local UEM player stats (stats_zm_0.cgp to stats_zm_4.cgp).</div>
                    <button class="nav-btn-small button-xl" onclick="backupStats()" data-i18n="buttons.create_backup">CREATE BACKUP</button>
                    <button class="nav-btn-small full-width-action" onclick="restoreStats()" data-i18n="buttons.restore_backup">RESTORE FROM BACKUP</button>
                </div>

                <div class="card">
                    <div class="card-title" data-i18n="settings.backup_tracker_config">TRACKER CONFIG BACKUP</div>
                    <div class="setting-help" data-i18n="settings.tracker_backup_help">Create or restore a recovery zip containing tracker settings, challenge progress, map operations, best matches, XP cache, damage history, map weapons, and other local tracker config files.</div>
                    <button class="nav-btn-small button-xl" onclick="backupTrackerConfig()" data-i18n="buttons.create_config_backup">CREATE CONFIG BACKUP</button>
                    <button class="nav-btn-small full-width-action" onclick="restoreTrackerConfig()" data-i18n="buttons.restore_config_backup">RESTORE CONFIG BACKUP</button>
                </div>

                <div class="card">
                    <div class="card-title" data-settings-copy="dataCard" data-i18n="settings.data_management">DATA MANAGEMENT</div>
                    <button class="nav-btn-small danger-full-action" onclick="reconfigure()" data-i18n="buttons.reset_file_paths">RESET FILE PATHS</button>
                    <p class="setting-note" data-settings-copy="dataNote" data-i18n="settings.data_note">Use this if you moved your game installation or history folder.</p>
                </div>

                <div class="card">
                    <div class="card-title" data-i18n="settings.language_support">LANGUAGE SUPPORT</div>
                    <div class="settings-row language-settings-row">
                        <div>
                            <div class="setting-title" data-i18n="settings.display_language">Display Language</div>
                            <div class="setting-description" data-i18n="settings.display_language_description">Select the language preference used by supported screens and future translation updates.</div>
                            <div id="language-status" class="setting-status">Status: English</div>
                        </div>
                        <select id="language-selector" class="settings-select" onchange="changeLanguage(this.value)">
                            <option value="en">English</option>
                        </select>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title" data-settings-copy="mediaCard" data-i18n="settings.dashboard_media">DASHBOARD MEDIA</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-settings-copy="mediaTitle" data-i18n="settings.show_workshop_images">Show Steam Workshop Images</div>
                            <div class="setting-description" data-settings-copy="mediaDescription" data-i18n="settings.show_workshop_images_description">Displays map preview images on the live dashboard and career rank card when a Steam Workshop link is available.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleWorkshopImages(this)" """ + workshop_images_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title" data-i18n="settings.discord_presence_card">ULTIMATE EXPERIENCE MOD COMMUNITY TOOL DISCORD PRESENCE</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-i18n="settings.enable_discord_presence">Enable Ultimate Experience Mod Community Tool Discord Card</div>
                            <div class="setting-description" data-i18n="settings.discord_presence_description">Shows tracker data on your Discord profile, including map, round, prestige/level, match XP, weapon usage, kills, and XP progress.</div>
                            <div id="discord-presence-status" class="setting-status" data-i18n="status.not_connected">Status: Not connected</div>
                        </div>
                        <label class="switch">
                            <input id="discord-presence-toggle" type="checkbox" onchange="saveDiscordPresenceSettings()" """ + discord_presence_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <details class="advanced-settings">
                        <summary data-i18n="settings.advanced_discord_settings">Advanced Discord settings</summary>
                        <div class="settings-row discord-presence-fields">
                            <input id="discord-client-id" class="settings-input" placeholder="Discord application client ID" data-i18n-placeholder="settings.discord_client_id_placeholder" onchange="saveDiscordPresenceSettings()">
                            <input id="discord-large-image" class="settings-input" placeholder="Optional large image asset key" data-i18n-placeholder="settings.discord_large_image_placeholder" onchange="saveDiscordPresenceSettings()">
                        </div>
                    </details>
                </div>

                <div class="card">
                    <div class="card-title" data-i18n="settings.t7_discord_presence_card">OFFICIAL UEM/T7 DISCORD PRESENCE</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-i18n="settings.enable_t7_discord_presence">Enable Official UEM/T7 Discord Card</div>
                            <div class="setting-description" data-i18n="settings.t7_discord_presence_description">Controls the built-in UEM/T7 Discord card from BO3's players/t7.json. If this is on, Discord may show it instead of the tracker card. Restart BO3/UEM after changing this.</div>
                            <div id="t7-discord-status" class="setting-status" data-i18n="status.checking_t7_json">Status: Checking t7.json...</div>
                        </div>
                        <label class="switch">
                            <input id="t7-discord-toggle" type="checkbox" onchange="saveT7DiscordPresenceSetting()">
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title" data-i18n="settings.camo_database">CAMO DATABASE</div>
                    <div class="setting-help" data-i18n="settings.camo_database_help">Checks https://uemmaps.com/custom_camos.json at most once per day on startup and only downloads when the server reports a change.</div>
                    <div id="custom-camos-status" class="setting-status" data-i18n="status.automatic_daily_check_enabled">Status: Automatic daily check enabled</div>
                    <button class="nav-btn-small full-width-action" onclick="syncCustomCamosNow()" data-i18n="buttons.sync_camo_database_now">SYNC CAMO DATABASE NOW</button>
                </div>
                
                <div class="card">
                    <div class="card-title" data-settings-copy="globalCard" data-i18n="settings.global_anonymous_stats">GLOBAL ANONYMOUS STATS</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-settings-copy="globalTitle" data-i18n="settings.contribute_anonymous_stats">Contribute Anonymous Global Stats</div>
                            <div class="setting-description" data-settings-copy="globalDescription" data-i18n="settings.global_description">Uploads anonymous archived match summaries to the UEMM global tracker database. No personally identifiable info, Steam ID, usernames, file paths, or raw profile/archive files are sent.</div>
                            <div id="global-stats-status" class="setting-status" data-i18n="status.not_synced_this_session">Status: Not synced this session</div>
                        </div>
                        <label class="switch">
                            <input id="global-stats-toggle" type="checkbox" onchange="toggleGlobalStats(this)" """ + global_stats_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <button class="nav-btn-small full-width-action" onclick="syncGlobalStatsNow()" data-i18n="buttons.sync_now">SYNC NOW</button>
                    <br>
                    <div class="settings-links">
                        <a href="https://uemmaps.com/tracker/tracker.html" target="_blank" data-i18n="settings.view_global_stats_board">View Global Stats Board</a> &bull;
                        <a href="https://uemmaps.com/tracker/recentmatches.html" target="_blank" data-i18n="settings.view_recent_matches">View Recent Matches</a>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title" data-settings-copy="xpCard" data-i18n="settings.xp_debugger">XP DEBUGGER</div>
                    <div class="settings-row">
                        <div>
                            <div class="setting-title" data-settings-copy="xpTitle" data-i18n="settings.enable_xp_debug_window">Enable XP Round Debug Window</div>
                            <div class="setting-description" data-settings-copy="xpDescription" data-i18n="settings.xp_description">Shows live game ID, map, player, round, level XP, tick XP, round XP, and rank changes.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleXpDebugger(this)" """ + xp_debug_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="settings-row warning-row">
                        <div>
                            <div class="setting-title" data-i18n="settings.experimental_xp_overflow_recovery">Experimental XP Overflow Recovery</div>
                            <div class="setting-description warning-text" data-i18n="settings.xp_overflow_warning">Warning: estimates across impossible negative XP/rank snapshots. Leave off unless you are seeing overflow-style level jumps.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleXpOverflowRecovery(this)" """ + xp_recovery_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <div id="tab-help" class="tab-content">
                <div class="help-content">
                    <h1 data-i18n="help.heading">OPERATIONAL GUIDE</h1>

                    <div class="help-dashboard">
                        <div class="card help-card help-changelog-card">
                            <div class="card-title" data-i18n="help.latest_changelog">LATEST CHANGELOG</div>
                            <div class="changelog-header-row">
                                <div>
                                    <div class="setting-title"><span data-i18n="help.current_version">Current Version</span> """ + app_version + """</div>
                                    <div id="changelog-status" class="update-status" data-i18n="help.loading_changelog">Loading latest GitHub release notes...</div>
                                </div>
                                <button class="nav-btn-small button-tall" onclick="loadChangelog(true)" data-i18n="buttons.refresh">REFRESH</button>
                            </div>
                            <div id="changelog-release-title"></div>
                            <div id="changelog-notes" class="changelog-notes-panel">
                                <span data-i18n="help.changelog_placeholder">Changelog will appear here when GitHub responds.</span>
                            </div>
                        </div>

                        <div class="card help-card">
                            <div class="card-title" data-i18n="help.quick_start">QUICK START</div>
                            <div class="help-step-list">
                                <div><b>1.</b> <span data-i18n="help.quick_start_1">Point setup at CurrentGame.json and your history archive folder.</span></div>
                                <div><b>2.</b> <span data-i18n="help.quick_start_2">Keep the tracker open while playing so live stats, XP, challenges, and match logs update.</span></div>
                                <div><b>3.</b> <span data-i18n="help.quick_start_3">Load your camo profile JSON in Camo Matrix when you want local camo progress editing.</span></div>
                                <div><b>4.</b> <span data-i18n="help.quick_start_4">Use Customization for themes, playercards, emblems, and overlay controls.</span></div>
                            </div>
                        </div>

                        <div class="card help-card">
                            <div class="card-title" data-i18n="help.core_features">CORE FEATURES</div>
                            <ul class="compact-help-list">
                                <li data-i18n="help.feature_live_game"><b>Live Game:</b> Tracks rank, XP, perks, weapons, damage, and round timing.</li>
                                <li data-i18n="help.feature_camo_matrix"><b>Camo Matrix:</b> Edits your loaded camo profile locally and supports priority stars.</li>
                                <li data-i18n="help.feature_career_profile"><b>Career Profile:</b> Summarizes archived maps, records, XP, and long-term stats.</li>
                                <li data-i18n="help.feature_challenges"><b>Challenges:</b> Unlocks calling cards, emblems, themes, weekly goals, and map operations.</li>
                                <li data-i18n="help.feature_best_matches"><b>Best Matches:</b> Lets you pin standout games from the live dashboard.</li>
                            </ul>
                        </div>

                        <div class="card help-card help-faq-card">
                            <div class="card-title" data-i18n="help.faq_troubleshooting">FAQ & TROUBLESHOOTING</div>
                            <div class="help-link-strip">
                                <a href="https://uemmaps.com/tracker/tracker.html" target="_blank" data-i18n="settings.view_global_stats_board">Global Stats Board</a>
                                <a href="https://uemmaps.com/tracker/recentmatches.html" target="_blank" data-i18n="settings.view_recent_matches">Recent Matches</a>
                                <a href="https://uemmaps.com/" target="_blank" data-i18n="help.uem_maps_upload">UEM Maps login and camo upload</a>
                            </div>
                            <div class="help-faq-grid">
                                <details>
                                    <summary data-i18n="help.faq_stats_title">Stats are not updating live</summary>
                                    <p data-i18n="help.faq_stats_body">Check the configured CurrentGame.json path in Settings. Some maps or mods only write new values at round end, during pauses, or after the game has fully initialized.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_match_title">My match is not in the sidebar</summary>
                                    <p data-i18n="help.faq_match_body">The history folder must still exist and be writable. The tracker saves files as Game_*.json after live data changes, so brand-new games may not appear until stats start moving.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_camo_site_title">Camo progress is not on the website</summary>
                                    <p data-i18n="help.faq_camo_site_body">The Camo Matrix edits your local loaded JSON immediately. To sync it online, log in at uemmaps.com and upload the updated camo file.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_missing_assets_title">Custom camos or images are missing</summary>
                                    <p data-i18n="help.faq_missing_assets_body">Use Settings to sync the camo database. If local icons are missing, keep the camoimages, perk icons, rank icons, callingcards, and emblems folders beside the app.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_challenges_reopen_title">Challenges look wrong after reopening</summary>
                                    <p data-i18n="help.faq_challenges_reopen_body">Current live-game progress is saved between launches so reopening should not double count. If you need a clean slate, use the challenge reset button.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_weekly_map_title">Weekly or map challenges are not progressing</summary>
                                    <p data-i18n="help.faq_weekly_map_body">Weekly challenges only count eligible activity during the current rotation. Map operations require the matching Steam Workshop map link, and weapon operations require the expected weapon data to appear in the live file.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_overlay_title">The overlay is blank or too busy</summary>
                                    <p data-i18n="help.faq_overlay_body">Enable the Live Overlay in Customization, then toggle individual overlay sections like perks, top damage, rank, match XP, and rank progress.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_xp_title">XP or rank gains look strange</summary>
                                    <p data-i18n="help.faq_xp_body">Use the XP Debugger in Settings to inspect round XP and rank snapshots. Only enable Experimental XP Overflow Recovery when you see impossible negative XP or rank reset snapshots.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_workshop_title">Steam Workshop images are not showing</summary>
                                    <p data-i18n="help.faq_workshop_body">Workshop images need a Steam Workshop link in the live/archive data and the Dashboard Media toggle enabled in Settings.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_global_title">Global stats are not uploading</summary>
                                    <p data-i18n="help.faq_global_body">Global stats are opt-in. Enable them in Settings, then use Sync Now. Uploads are anonymous match summaries, not raw profile files, usernames, Steam IDs, or local paths.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_updates_title">How do updates and rollback work?</summary>
                                    <p data-i18n="help.faq_updates_body">Use Settings to check for GitHub releases. When available, the updater closes and restarts the tracker. Rollback restores the app version saved before the last update when a backup is available.</p>
                                </details>
                                <details>
                                    <summary data-i18n="help.faq_backup_title">When should I create a backup?</summary>
                                    <p data-i18n="help.faq_backup_body">Create a backup before big edits, updates, or moving installs. The backup packages local UEM player stats files such as stats_zm_0.cgp through stats_zm_4.cgp.</p>
                                </details>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
        
        <input type="hidden" id="current-user-path" value="">

        <script>
        // --- NEW GRAPHING VARIABLES ---
        let xpmChartInstance = null;
        let roundXpChartInstance = null; // New chart instance variable
        let zpmChartInstance = null;
        let currentGraphLabels = [];
        let currentGraphData = [];
        let currentRoundXpLabels = []; // Stores the new Round XP labels
        let currentRoundXpData = [];   // Stores the new Round XP values
        let currentZpmLabels = [];
        let currentZpmData = [];
        let zpmOverlayEnabled = false;
        let currentThemeName = 'default';
            let workshopImagesEnabled = """ + workshop_images_js + """;
            let globalStatsEnabled = """ + global_stats_js + """;
            let showGlobalStatsPrompt = """ + global_stats_prompt_js + """;
        let activeLocale = {};
        let activeLanguage = 'en';
        let defaultI18nText = {};

        function openMapCompat() {
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.open_map_compat();
            }
        }

        function openDonateLink() {
            window.open('https://www.paypal.com/paypalme/UEMMaptesting', '_blank', 'noopener');
        }

        const GRAPH_THEMES = {
            default: {
                line: '#66fcf1', lineFill: 'rgba(102, 252, 241, 0.12)',
                point: '#ff9d00', pointBorder: '#fff',
                bar: '#ff9d00', barBorder: '#e68a00',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#66fcf1'
            },
            void: {
                line: '#b19cd9', lineFill: 'rgba(148, 0, 211, 0.14)',
                point: '#e0b0ff', pointBorder: '#4b0082',
                bar: '#9400d3', barBorder: '#e0b0ff',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#e0b0ff'
            },
            '115_Origins': {
                line: '#00a8ff', lineFill: 'rgba(0, 168, 255, 0.14)',
                point: '#58a6ff', pointBorder: '#d7f3ff',
                bar: '#00a8ff', barBorder: '#58a6ff',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#58a6ff'
            },
            RedHex: {
                line: '#ff3333', lineFill: 'rgba(255, 0, 0, 0.13)',
                point: '#ffcccc', pointBorder: '#ff0000',
                bar: '#ff0000', barBorder: '#800000',
                zpm: '#ffcc00', zpmFill: 'rgba(255, 204, 0, 0.08)',
                tooltip: '#ff3333'
            },
            'Golden Divinium': {
                line: '#ffd700', lineFill: 'rgba(255, 215, 0, 0.16)',
                point: '#fffac0', pointBorder: '#b8860b',
                bar: '#ffd700', barBorder: '#b8860b',
                zpm: '#fffac0', zpmFill: 'rgba(255, 250, 192, 0.08)',
                tooltip: '#ffd700'
            },
            retro: {
                line: '#00f2ff', lineFill: 'rgba(0, 242, 255, 0.13)',
                point: '#ff00ff', pointBorder: '#00f2ff',
                bar: '#ff00ff', barBorder: '#00f2ff',
                zpm: '#00ff66', zpmFill: 'rgba(0, 255, 102, 0.08)',
                tooltip: '#ff00ff'
            },
            matrix: {
                line: '#00ff00', lineFill: 'rgba(0, 255, 0, 0.12)',
                point: '#000000', pointBorder: '#00ff00',
                bar: '#00ff00', barBorder: '#008800',
                zpm: '#88ff88', zpmFill: 'rgba(136, 255, 136, 0.08)',
                tooltip: '#00ff00'
            },
            trench: {
                line: '#c9bca7', lineFill: 'rgba(201, 188, 167, 0.12)',
                point: '#8b0000', pointBorder: '#c9bca7',
                bar: '#8b0000', barBorder: '#c9bca7',
                zpm: '#d4b56a', zpmFill: 'rgba(212, 181, 106, 0.08)',
                tooltip: '#c9bca7'
            },
            neon_pulse: {
                line: '#00f5ff', lineFill: 'rgba(0, 245, 255, 0.13)',
                point: '#ff00ff', pointBorder: '#00f5ff',
                bar: '#00f5ff', barBorder: '#ff00ff',
                zpm: '#ff00ff', zpmFill: 'rgba(255, 0, 255, 0.08)',
                tooltip: '#00f5ff'
            },
            Darkwood: {
                line: '#e2c13d', lineFill: 'rgba(226, 193, 61, 0.14)',
                point: '#f3d446', pointBorder: '#4b2716',
                bar: '#b98552', barBorder: '#e2c13d',
                zpm: '#f6d86b', zpmFill: 'rgba(246, 216, 107, 0.08)',
                tooltip: '#e2c13d'
            },
            'Cherry Blossom': {
                line: '#e91e63', lineFill: 'rgba(244, 143, 177, 0.16)',
                point: '#fff8fa', pointBorder: '#e91e63',
                bar: '#f48fb1', barBorder: '#e91e63',
                zpm: '#ff6b9a', zpmFill: 'rgba(255, 107, 154, 0.10)',
                tooltip: '#e91e63'
            },
            'DeadOps Arcade': {
                line: '#00f5ff', lineFill: 'rgba(0, 245, 255, 0.14)',
                point: '#ffd340', pointBorder: '#ff304f',
                bar: '#ff304f', barBorder: '#ffd340',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#ffd340'
            },
            'Pacific Paradise': {
                line: '#2e8b57', lineFill: 'rgba(46, 139, 87, 0.12)',
                point: '#ff69b4', pointBorder: '#ff1493',
                bar: '#ff69b4', barBorder: '#ff1493',
                zpm: '#98fb98', zpmFill: 'rgba(152, 251, 152, 0.08)',
                tooltip: '#2e8b57'
            },
            Clouds: {
                line: '#74d9ff', lineFill: 'rgba(116, 217, 255, 0.14)',
                point: '#ffe08a', pointBorder: '#ffffff',
                bar: '#ffe08a', barBorder: '#74d9ff',
                zpm: '#ffffff', zpmFill: 'rgba(255, 255, 255, 0.08)',
                tooltip: '#ffe08a'
            },
            'Dog Pack': {
                line: '#f2c16b', lineFill: 'rgba(242, 193, 107, 0.15)',
                point: '#fff8e8', pointBorder: '#8b5a36',
                bar: '#d88945', barBorder: '#f2c16b',
                zpm: '#ffe0a6', zpmFill: 'rgba(255, 224, 166, 0.10)',
                tooltip: '#f2c16b'
            },
            'Shi No Numa': {
                line: '#b7d97b', lineFill: 'rgba(183, 217, 123, 0.13)',
                point: '#f0d66a', pointBorder: '#26301d',
                bar: '#7e8e55', barBorder: '#d8c889',
                zpm: '#d8c889', zpmFill: 'rgba(216, 200, 137, 0.09)',
                tooltip: '#f0d66a'
            },
            'Glacial Frost': {
                line: '#7de9ff', lineFill: 'rgba(125, 233, 255, 0.12)',
                point: '#d8fbff', pointBorder: '#ffffff',
                bar: '#38c8ff', barBorder: '#7de9ff',
                zpm: '#a7f6ff', zpmFill: 'rgba(167, 246, 255, 0.08)',
                tooltip: '#d8fbff'
            },
            cartoon_graffiti_theme: {
                line: '#ff3bd4', lineFill: 'rgba(255, 59, 212, 0.14)',
                point: '#ffe94f', pointBorder: '#1a0826',
                bar: '#23f6ff', barBorder: '#1a0826',
                zpm: '#56ff7b', zpmFill: 'rgba(86, 255, 123, 0.08)',
                tooltip: '#ffe94f'
            },
            factory: {
                line: '#68ff5a', lineFill: 'rgba(104, 255, 90, 0.14)',
                point: '#ffb347', pointBorder: '#060807',
                bar: '#8d4423', barBorder: '#68ff5a',
                zpm: '#b8ff6a', zpmFill: 'rgba(184, 255, 106, 0.08)',
                tooltip: '#ffb347'
            }
        };

        const SETTINGS_COPY_DEFAULT = {
            heading: "System Configuration",
            updatesCard: "APP UPDATES",
            visualCard: "VISUAL CUSTOMIZATION",
            visualHelp: "Select a visual theme for the tracker:",
            cardIdentityCard: "PLAYER CARD IDENTITY",
            cardIdentityHelp: "Select your active Calling Card:",
            backupCard: "UEM STATS BACKUP",
            backupHelp: "Create a zip archive containing your local UEM player stats (stats_zm_0.cgp to stats_zm_4.cgp).",
            dataCard: "DATA MANAGEMENT",
            dataNote: "Use this if you moved your game installation or history folder.",
            mediaCard: "DASHBOARD MEDIA",
            mediaTitle: "Show Steam Workshop Images",
            mediaDescription: "Displays map preview images on the live dashboard and career rank card when a Steam Workshop link is available.",
            globalCard: "GLOBAL ANONYMOUS STATS",
            globalTitle: "Contribute Anonymous Global Stats",
            globalDescription: "Uploads anonymous archived match summaries to the UEMM global tracker database. No personally identifiable info, Steam ID, usernames, file paths, or raw profile/archive files are sent.",
            overlayCard: "OVERLAY CONTROL",
            overlayTitle: "Enable Live Overlay",
            overlayDescription: "Displays Perks and Top Damage in a single, smart-resizing window.",
            xpCard: "XP DEBUGGER",
            xpTitle: "Enable XP Round Debug Window",
            xpDescription: "Shows live game ID, map, player, round, level XP, tick XP, round XP, and rank changes."
        };

        const THEME_SETTINGS_COPY = {
            "115_Origins": {
                heading: "Excavation Console",
                updatesCard: "115 FIELD UPDATES",
                visualCard: "DIG SITE VISUALS",
                visualHelp: "Choose the active excavation overlay:",
                cardIdentityCard: "CREW EMBLEM",
                cardIdentityHelp: "Select the calling card shown on your field profile:",
                backupCard: "ARCHIVE CRATE",
                backupHelp: "Pack your local UEM player stats into a secure dig-site archive.",
                dataCard: "ROUTE RESET",
                dataNote: "Use this if the excavation moved and your game or history paths changed.",
                mediaCard: "WORKSHOP RECON",
                mediaTitle: "Show Expedition Images",
                mediaDescription: "Displays workshop map previews on the mission dashboard and career rank dossier.",
                globalCard: "ANONYMOUS 115 NETWORK",
                globalTitle: "Share Anonymous Field Reports",
                globalDescription: "Uploads anonymous archived match summaries to the global tracker. No identity, Steam ID, file paths, or raw profile files are sent.",
                overlayCard: "TACTICAL HUD",
                overlayTitle: "Enable Expedition Overlay",
                overlayDescription: "Shows Perks and Top Damage in a compact live field window.",
                xpCard: "115 XP ANALYZER",
                xpTitle: "Enable Round Telemetry Window",
                xpDescription: "Shows live game ID, map, player, round, XP ticks, round XP, and rank changes."
            },
            "Cherry Blossom": {
                heading: "Blossom Preferences",
                updatesCard: "SEASONAL UPDATES",
                visualCard: "SAKURA STYLE",
                visualHelp: "Choose the tracker look for this session:",
                cardIdentityCard: "HANAMI CARD",
                cardIdentityHelp: "Select the calling card displayed with your profile:",
                backupCard: "PETAL ARCHIVE",
                backupHelp: "Create a soft backup bundle for your local UEM player stats.",
                dataCard: "PATH GARDEN",
                dataNote: "Use this if your game installation or history folder has been replanted.",
                mediaCard: "MAP BLOSSOMS",
                mediaTitle: "Show Workshop Scenery",
                mediaDescription: "Adds workshop map previews to the live dashboard and career rank card.",
                globalCard: "ANONYMOUS GARDEN STATS",
                globalTitle: "Share Anonymous Bloom Reports",
                globalDescription: "Sends anonymous archived match summaries to the global tracker without identity, Steam ID, paths, or raw files.",
                overlayCard: "LIVE BLOSSOM OVERLAY",
                overlayTitle: "Enable Petal Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live window.",
                xpCard: "ROUND BLOOM DEBUGGER",
                xpTitle: "Enable XP Bloom Window",
                xpDescription: "Shows live round, level XP, tick XP, round XP, and rank movement."
            },
            Clouds: {
                heading: "Cloud Control",
                updatesCard: "SKY UPDATES",
                visualCard: "CLOUD DECK",
                visualHelp: "Choose the active sky theme:",
                cardIdentityCard: "SKYLINE CARD",
                cardIdentityHelp: "Select the calling card shown on your cloud profile:",
                backupCard: "CLOUD ARCHIVE",
                backupHelp: "Create a clean backup bundle for your local UEM player stats.",
                dataCard: "FLIGHT PATHS",
                dataNote: "Use this if your game installation or history folder drifted somewhere new.",
                mediaCard: "SKY PREVIEWS",
                mediaTitle: "Show Workshop Sky Views",
                mediaDescription: "Displays workshop previews on the dashboard and career rank card.",
                globalCard: "ANONYMOUS SKY STATS",
                globalTitle: "Share Anonymous Cloud Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "SKY OVERLAY",
                overlayTitle: "Enable Cloud Overlay",
                overlayDescription: "Displays Perks and Top Damage in a bright compact live window.",
                xpCard: "XP ALTIMETER",
                xpTitle: "Enable XP Altimeter Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank movement."
            },
            "Dog Pack": {
                heading: "Dog Pack Setup",
                updatesCard: "PACK UPDATES",
                visualCard: "COZY THEME",
                visualHelp: "Choose the active pack theme:",
                cardIdentityCard: "DOGHOUSE CARD",
                cardIdentityHelp: "Select the calling card shown on your profile:",
                backupCard: "TREAT JAR BACKUP",
                backupHelp: "Create a clean backup bundle for your local UEM player stats.",
                dataCard: "WALK ROUTES",
                dataNote: "Use this if your game installation or history folder wandered somewhere new.",
                mediaCard: "PACK PREVIEWS",
                mediaTitle: "Show Workshop Snapshots",
                mediaDescription: "Displays workshop previews on the dashboard and career rank card.",
                globalCard: "ANONYMOUS PACK STATS",
                globalTitle: "Share Anonymous Match Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "PACK OVERLAY",
                overlayTitle: "Enable Dog Pack Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact warm live window.",
                xpCard: "XP WALK LOG",
                xpTitle: "Enable XP Walk Log Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank movement."
            },
            "Shi No Numa": {
                heading: "Swamp Outpost",
                updatesCard: "FIELD RADIO UPDATES",
                visualCard: "SWAMP CAMOUFLAGE",
                visualHelp: "Choose the active swamp outpost theme:",
                cardIdentityCard: "FIELD DOSSIER CARD",
                cardIdentityHelp: "Select the calling card pinned to your field dossier:",
                backupCard: "SUPPLY CRATE BACKUP",
                backupHelp: "Create a sealed backup bundle for your local UEM player stats.",
                dataCard: "MUDDY PATHS",
                dataNote: "Use this if your game installation or history folder moved to a new outpost.",
                mediaCard: "RECON PHOTOS",
                mediaTitle: "Show Workshop Recon",
                mediaDescription: "Displays workshop previews on the mission dashboard and career rank dossier.",
                globalCard: "ANONYMOUS FIELD REPORTS",
                globalTitle: "Share Anonymous Swamp Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "OUTPOST OVERLAY",
                overlayTitle: "Enable Swamp Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live field window.",
                xpCard: "XP FIELD LOG",
                xpTitle: "Enable XP Field Log Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank movement."
            },
            "Darkwood": {
                heading: "Woodland Cabinet",
                updatesCard: "LEDGER UPDATES",
                visualCard: "VARNISH AND THEME",
                visualHelp: "Select the finish for the tracker cabinet:",
                cardIdentityCard: "CREST DISPLAY",
                cardIdentityHelp: "Choose the calling card mounted on your profile:",
                backupCard: "OAK ARCHIVE",
                backupHelp: "Seal your local UEM player stats into a backup archive.",
                dataCard: "CABINET PATHS",
                dataNote: "Use this if the game installation or history drawer moved.",
                mediaCard: "WORKSHOP PORTRAITS",
                mediaTitle: "Show Map Portraits",
                mediaDescription: "Displays workshop previews on the dashboard and career rank card.",
                globalCard: "ANONYMOUS LEDGER",
                globalTitle: "Contribute Anonymous Match Ledgers",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, paths, or raw profile files.",
                overlayCard: "DESK OVERLAY",
                overlayTitle: "Enable Live Desk Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live panel.",
                xpCard: "XP LEDGER",
                xpTitle: "Enable Round Ledger Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank changes."
            },
            "DeadOps Arcade": {
                heading: "Arcade Cabinet Setup",
                updatesCard: "CABINET PATCHES",
                visualCard: "ATTRACT MODE",
                visualHelp: "Pick the neon cabinet skin:",
                cardIdentityCard: "PLAYER BADGE",
                cardIdentityHelp: "Choose the badge shown on your player card:",
                backupCard: "HIGH-SCORE BACKUP",
                backupHelp: "Save your local UEM player stats into a cabinet archive.",
                dataCard: "COIN-OP PATHS",
                dataNote: "Use this if the game or history folder moved to another cabinet.",
                mediaCard: "ARCADE SCREENS",
                mediaTitle: "Show Workshop Screens",
                mediaDescription: "Displays workshop map art on the live dashboard and career rank display.",
                globalCard: "ANONYMOUS SCOREBOARD",
                globalTitle: "Share Anonymous Run Scores",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "POWER-UP OVERLAY",
                overlayTitle: "Enable Arcade Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live HUD.",
                xpCard: "SCORE DEBUGGER",
                xpTitle: "Enable XP Score Window",
                xpDescription: "Shows round, level XP, tick XP, round XP, and rank changes."
            },
            "Golden Divinium": {
                heading: "Divinium Vault",
                updatesCard: "VAULT UPDATES",
                visualCard: "GILDED DISPLAY",
                visualHelp: "Select the active vault presentation:",
                cardIdentityCard: "RELIC CARD",
                cardIdentityHelp: "Choose the calling card placed in your vault profile:",
                backupCard: "SEALED STAT CACHE",
                backupHelp: "Create a gold-sealed backup of your local UEM player stats.",
                dataCard: "VAULT ROUTES",
                dataNote: "Use this if your game installation or history vault moved.",
                mediaCard: "WORKSHOP RELICS",
                mediaTitle: "Show Map Relics",
                mediaDescription: "Displays workshop previews on the live dashboard and career rank card.",
                globalCard: "ANONYMOUS DIVINIUM LEDGER",
                globalTitle: "Contribute Anonymous Vault Records",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw profile data.",
                overlayCard: "GILDED OVERLAY",
                overlayTitle: "Enable Divinium Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live window.",
                xpCard: "XP TRANSMUTER",
                xpTitle: "Enable Round XP Transmuter",
                xpDescription: "Shows live XP ticks, round XP, level movement, and rank changes."
            },
            matrix: {
                heading: "Matrix Control Node",
                updatesCard: "SYSTEM PATCHES",
                visualCard: "SIMULATION SKIN",
                visualHelp: "Select the active matrix render:",
                cardIdentityCard: "SIGNAL IDENTITY",
                cardIdentityHelp: "Choose the calling card broadcast with your profile:",
                backupCard: "DATA SNAPSHOT",
                backupHelp: "Compress local UEM player stats into an archive packet.",
                dataCard: "PATH REWIRE",
                dataNote: "Use this if the game installation or history stream changed route.",
                mediaCard: "WORKSHOP SIGNALS",
                mediaTitle: "Show Map Signals",
                mediaDescription: "Displays workshop previews on the live dashboard and career rank node.",
                globalCard: "ANONYMOUS GRID STATS",
                globalTitle: "Transmit Anonymous Match Data",
                globalDescription: "Sends anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "LIVE CODE OVERLAY",
                overlayTitle: "Enable Matrix Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live readout.",
                xpCard: "XP TRACE",
                xpTitle: "Enable Round Trace Window",
                xpDescription: "Shows live game ID, round, XP ticks, round XP, and rank deltas."
            },
            neon_pulse: {
                heading: "Neon Control Deck",
                updatesCard: "PULSE UPDATES",
                visualCard: "NEON PROFILE",
                visualHelp: "Select the active city glow:",
                cardIdentityCard: "SIGNATURE CARD",
                cardIdentityHelp: "Choose the calling card lighting up your profile:",
                backupCard: "SYNC BACKUP",
                backupHelp: "Create a bright backup package for your local UEM player stats.",
                dataCard: "ROUTE CONTROL",
                dataNote: "Use this if your game installation or history route changed.",
                mediaCard: "CITY FEEDS",
                mediaTitle: "Show Workshop Feeds",
                mediaDescription: "Displays workshop previews across the live dashboard and career rank card.",
                globalCard: "ANONYMOUS PULSE STATS",
                globalTitle: "Share Anonymous Pulse Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, paths, or raw files.",
                overlayCard: "NEON OVERLAY",
                overlayTitle: "Enable Pulse Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live neon panel.",
                xpCard: "XP PULSE MONITOR",
                xpTitle: "Enable Pulse Debug Window",
                xpDescription: "Shows live XP ticks, round XP, rank movement, and session telemetry."
            },
            "Pacific Paradise": {
                heading: "Island Preferences",
                updatesCard: "TIDE UPDATES",
                visualCard: "PARADISE LOOK",
                visualHelp: "Choose the active island theme:",
                cardIdentityCard: "RESORT CARD",
                cardIdentityHelp: "Select the calling card on your player profile:",
                backupCard: "DRIFTWOOD BACKUP",
                backupHelp: "Create a calm archive for your local UEM player stats.",
                dataCard: "HARBOR PATHS",
                dataNote: "Use this if your game installation or history folder changed shore.",
                mediaCard: "POSTCARD PREVIEWS",
                mediaTitle: "Show Workshop Postcards",
                mediaDescription: "Displays workshop map previews on the dashboard and career rank card.",
                globalCard: "ANONYMOUS ISLAND STATS",
                globalTitle: "Share Anonymous Tide Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, paths, or raw files.",
                overlayCard: "BREEZE OVERLAY",
                overlayTitle: "Enable Paradise Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live window.",
                xpCard: "XP TIDE WATCH",
                xpTitle: "Enable Tide Debug Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank changes."
            },
            RedHex: {
                heading: "Red Hex Command",
                updatesCard: "HEX PATCHES",
                visualCard: "COMBAT INTERFACE",
                visualHelp: "Select the active red-grid skin:",
                cardIdentityCard: "OPERATIVE MARK",
                cardIdentityHelp: "Choose the calling card stamped onto your profile:",
                backupCard: "BLACKSITE BACKUP",
                backupHelp: "Create a hardened archive of your local UEM player stats.",
                dataCard: "TARGET PATHS",
                dataNote: "Use this if the game install or history file route changed.",
                mediaCard: "TACTICAL PREVIEWS",
                mediaTitle: "Show Workshop Recon",
                mediaDescription: "Displays workshop map previews on the dashboard and career rank card.",
                globalCard: "ANONYMOUS HEX INTEL",
                globalTitle: "Upload Anonymous Combat Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "COMBAT OVERLAY",
                overlayTitle: "Enable Hex Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live tactical window.",
                xpCard: "XP THREAT METER",
                xpTitle: "Enable Hex Debug Window",
                xpDescription: "Shows live XP ticks, round XP, rank changes, and combat telemetry."
            },
            retro: {
                heading: "Retro Setup Terminal",
                updatesCard: "CARTRIDGE PATCHES",
                visualCard: "SCREEN MODE",
                visualHelp: "Select the active retro display:",
                cardIdentityCard: "PLAYER INSERT",
                cardIdentityHelp: "Choose the calling card loaded into your profile:",
                backupCard: "SAVE STATE BACKUP",
                backupHelp: "Create a save-state archive for your local UEM player stats.",
                dataCard: "LOAD PATHS",
                dataNote: "Use this if the game installation or history folder changed slots.",
                mediaCard: "CRT PREVIEWS",
                mediaTitle: "Show Workshop Screens",
                mediaDescription: "Displays workshop map previews on the dashboard and career rank screen.",
                globalCard: "ANONYMOUS SCORE SYNC",
                globalTitle: "Share Anonymous Score Data",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, paths, or raw files.",
                overlayCard: "ARCADE HUD",
                overlayTitle: "Enable Retro Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live pixel panel.",
                xpCard: "XP SCOREBOARD",
                xpTitle: "Enable XP Score Window",
                xpDescription: "Shows round, XP ticks, round XP, level movement, and rank changes."
            },
            trench: {
                heading: "Trench Field Desk",
                updatesCard: "FIELD ORDERS",
                visualCard: "BATTLEFIELD VISUALS",
                visualHelp: "Select the active front-line theme:",
                cardIdentityCard: "SERVICE CARD",
                cardIdentityHelp: "Choose the calling card pinned to your profile:",
                backupCard: "FIELD BACKUP",
                backupHelp: "Create a packed archive of your local UEM player stats.",
                dataCard: "SUPPLY ROUTES",
                dataNote: "Use this if the game installation or history route changed.",
                mediaCard: "RECON PHOTOS",
                mediaTitle: "Show Workshop Recon",
                mediaDescription: "Displays workshop previews on the live dashboard and career rank card.",
                globalCard: "ANONYMOUS FIELD REPORTS",
                globalTitle: "Send Anonymous Front Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw files.",
                overlayCard: "FRONT-LINE OVERLAY",
                overlayTitle: "Enable Trench Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live field window.",
                xpCard: "XP FIELD LOG",
                xpTitle: "Enable Field Debug Window",
                xpDescription: "Shows round telemetry, XP ticks, round XP, and rank changes."
            },
            void: {
                heading: "Void Calibration",
                updatesCard: "SIGNAL UPDATES",
                visualCard: "VOID SKIN",
                visualHelp: "Select the active void atmosphere:",
                cardIdentityCard: "ECHO CARD",
                cardIdentityHelp: "Choose the calling card drifting with your profile:",
                backupCard: "NULLSPACE BACKUP",
                backupHelp: "Create a quiet archive of your local UEM player stats.",
                dataCard: "VOID PATHS",
                dataNote: "Use this if your game installation or history folder shifted.",
                mediaCard: "DIMENSION PREVIEWS",
                mediaTitle: "Show Workshop Echoes",
                mediaDescription: "Displays workshop map previews on the dashboard and career rank card.",
                globalCard: "ANONYMOUS VOID STATS",
                globalTitle: "Share Anonymous Echo Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, paths, or raw files.",
                overlayCard: "ECHO OVERLAY",
                overlayTitle: "Enable Void Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live window.",
                xpCard: "XP ECHO TRACE",
                xpTitle: "Enable Void Debug Window",
                xpDescription: "Shows live XP ticks, round XP, rank movement, and round telemetry."
            },
            cartoon_graffiti_theme: {
                heading: "Graffiti Studio",
                updatesCard: "TAG UPDATES",
                visualCard: "SPRAY WALL",
                visualHelp: "Choose the active graffiti skin:",
                cardIdentityCard: "TAG CARD",
                cardIdentityHelp: "Select the calling card spray-painted on your profile:",
                backupCard: "CAN ARCHIVE",
                backupHelp: "Create a graffiti archive of your local UEM player stats.",
                dataCard: "ALLEY PATHS",
                dataNote: "Use this if your game or history folder moved to a new wall.",
                mediaCard: "MURAL PREVIEWS",
                mediaTitle: "Show Workshop Murals",
                mediaDescription: "Displays workshop map art on the dashboard and career rank card.",
                globalCard: "ANONYMOUS WALL STATS",
                globalTitle: "Share Anonymous Tag Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, paths, or raw files.",
                overlayCard: "SPRAY OVERLAY",
                overlayTitle: "Enable Graffiti Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact spray-can live window.",
                xpCard: "XP TAG TRACKER",
                xpTitle: "Enable Graffiti Debug Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank tags."
            },
            factory: {
                heading: "Factory Control Panel",
                updatesCard: "FACTORY UPDATES",
                visualCard: "INDUSTRIAL FINISH",
                visualHelp: "Select the active factory floor overlay:",
                cardIdentityCard: "CREW BADGE",
                cardIdentityHelp: "Choose the calling card stamped on your factory profile:",
                backupCard: "ASSEMBLY ARCHIVE",
                backupHelp: "Pack your local UEM player stats into a reinforced factory crate.",
                dataCard: "CONVEYOR PATHS",
                dataNote: "Use this if the factory floor moved and your game or history paths changed.",
                mediaCard: "BLUEPRINT PREVIEWS",
                mediaTitle: "Show Workshop Schematics",
                mediaDescription: "Displays workshop previews on the dashboard and career rank dossier.",
                globalCard: "ANONYMOUS FACTORY STATS",
                globalTitle: "Contribute Anonymous Production Reports",
                globalDescription: "Uploads anonymous archived match summaries without identity, Steam ID, file paths, or raw profile data.",
                overlayCard: "HUD CONTROL PANEL",
                overlayTitle: "Enable Factory Overlay",
                overlayDescription: "Displays Perks and Top Damage in a compact live telemetry window.",
                xpCard: "XP CONDUIT ANALYZER",
                xpTitle: "Enable XP Conduit Window",
                xpDescription: "Shows live round data, XP ticks, round XP, and rank movement."
            }
        };

        function applySettingsCopy(themeName) {
            const copy = Object.assign({}, SETTINGS_COPY_DEFAULT, THEME_SETTINGS_COPY[themeName] || {});
            document.querySelectorAll("[data-settings-copy]").forEach(el => {
                const key = el.getAttribute("data-settings-copy");
                if (copy[key]) el.textContent = copy[key];
            });
        }

        function getGraphTheme() {
            return GRAPH_THEMES[currentThemeName] || GRAPH_THEMES.default;
        }

        function applyGraphTheme() {
            const theme = getGraphTheme();
            const isFrost = currentThemeName === 'Glacial Frost';

            if (xpmChartInstance) {
                const ds = xpmChartInstance.data.datasets[0];
                ds.borderColor = theme.line;
                ds.backgroundColor = theme.lineFill;
                ds.pointBackgroundColor = theme.point;
                ds.pointBorderColor = theme.pointBorder;
                ds.pointStyle = isFrost ? 'rectRot' : 'circle';
                const zpmDs = xpmChartInstance.data.datasets.find(d => d.id === 'zpm-overlay');
                if (zpmDs) {
                    zpmDs.borderColor = theme.zpm;
                    zpmDs.backgroundColor = theme.zpmFill;
                    zpmDs.pointBackgroundColor = theme.zpm;
                    zpmDs.pointBorderColor = theme.pointBorder;
                    zpmDs.pointStyle = isFrost ? 'rectRot' : 'circle';
                }
                xpmChartInstance.options.plugins.tooltip.titleColor = theme.tooltip;
                xpmChartInstance.options.plugins.tooltip.borderColor = theme.tooltip;
                xpmChartInstance.update('none');
            }

            if (roundXpChartInstance) {
                const ds = roundXpChartInstance.data.datasets[0];
                ds.borderColor = isFrost ? '#eefaff' : theme.barBorder;
                roundXpChartInstance.options.plugins.tooltip.titleColor = theme.tooltip;
                roundXpChartInstance.update('none');
            }

            if (zpmChartInstance) {
                const ds = zpmChartInstance.data.datasets[0];
                ds.borderColor = theme.zpm;
                ds.backgroundColor = theme.zpmFill;
                ds.pointBackgroundColor = theme.zpm;
                ds.pointBorderColor = theme.pointBorder;
                ds.pointStyle = isFrost ? 'rectRot' : 'circle';
                zpmChartInstance.options.plugins.tooltip.titleColor = theme.zpm;
                zpmChartInstance.options.plugins.tooltip.borderColor = theme.zpm;
                zpmChartInstance.update('none');
            }
        }

        function getZpmDataset() {
            const theme = getGraphTheme();
            return {
                id: 'zpm-overlay',
                label: 'Zombies Per Minute',
                data: currentZpmData,
                borderColor: theme.zpm,
                backgroundColor: theme.zpmFill,
                borderWidth: 2,
                fill: false,
                tension: 0.2,
                pointBackgroundColor: theme.zpm,
                pointBorderColor: theme.pointBorder,
                pointRadius: 4,
                pointHoverRadius: 7,
                pointStyle: currentThemeName === 'Glacial Frost' ? 'rectRot' : 'circle',
                pointBorderWidth: 2,
                yAxisID: 'zpmAxis'
            };
        }

        function syncXpmOverlayDataset() {
            if (!xpmChartInstance) return;
            const existingIndex = xpmChartInstance.data.datasets.findIndex(d => d.id === 'zpm-overlay');
            if (zpmOverlayEnabled) {
                const zpmDataset = getZpmDataset();
                if (existingIndex >= 0) {
                    xpmChartInstance.data.datasets[existingIndex] = zpmDataset;
                } else {
                    xpmChartInstance.data.datasets.push(zpmDataset);
                }
                xpmChartInstance.options.scales.zpmAxis.display = true;
            } else {
                if (existingIndex >= 0) xpmChartInstance.data.datasets.splice(existingIndex, 1);
                xpmChartInstance.options.scales.zpmAxis.display = false;
            }
        }

        function sizeGraphCanvas(canvas, wrapper, labelCount) {
            const availableWidth = Math.max(wrapper.clientWidth || wrapper.parentElement.clientWidth || 0, 1);
            const targetWidth = Math.max(availableWidth, labelCount * 22);
            canvas.style.width = targetWidth + 'px';
            canvas.style.minWidth = '100%';
            wrapper.style.width = '100%';
            wrapper.style.overflowX = targetWidth > availableWidth ? 'auto' : 'hidden';
            wrapper.style.overflowY = 'hidden';
        }

        function toggleXpmGraph() {
            const container = document.getElementById('xpm-graph-container');
            const otherContainer = document.getElementById('roundxp-graph-container');
            const zpmContainer = document.getElementById('zpm-graph-container');
            if (container.style.display === 'none' || container.style.display === '') {
                otherContainer.style.display = 'none'; // Close the other one
                if (zpmContainer) zpmContainer.style.display = 'none';
                container.style.display = 'block';
                setTimeout(() => { renderXpmChart(); }, 50);
            } else {
                container.style.display = 'none';
            }
        }

        function toggleZpmOverlay() {
            zpmOverlayEnabled = !zpmOverlayEnabled;
            renderXpmChart();
        }

        // --- NEW: TOGGLE ROUND XP GRAPH ---
        function toggleRoundXpGraph() {
            const container = document.getElementById('roundxp-graph-container');
            const otherContainer = document.getElementById('xpm-graph-container');
            const zpmContainer = document.getElementById('zpm-graph-container');
            
            if (container.style.display === 'none' || container.style.display === '') {
                otherContainer.style.display = 'none'; // Close the other one
                if (zpmContainer) zpmContainer.style.display = 'none';
                container.style.display = 'block';
                setTimeout(() => { renderRoundXpChart(); }, 50);
            } else {
                container.style.display = 'none';
            }
        }

        function toggleZpmGraph() {
            const container = document.getElementById('zpm-graph-container');
            const xpmContainer = document.getElementById('xpm-graph-container');
            const roundContainer = document.getElementById('roundxp-graph-container');
            if (!container) return;

            if (container.style.display === 'none' || container.style.display === '') {
                if (xpmContainer) xpmContainer.style.display = 'none';
                if (roundContainer) roundContainer.style.display = 'none';
                container.style.display = 'block';
                setTimeout(() => { renderZpmChart(); }, 50);
            } else {
                container.style.display = 'none';
            }
        }

        // --- NEW: SMARTER POPOUT LOGIC ---
        let graphPopoutStates = {}; // Remembers locations for MULTIPLE graphs

        function toggleGraphPopout(containerId, wrapperId, chartType) {
            const container = document.getElementById(containerId);
            const wrapper = document.getElementById(wrapperId);
            
            container.classList.toggle('graph-popout-mode');
            
            if (container.classList.contains('graph-popout-mode')) {
                // Save exactly where this specific graph was
                graphPopoutStates[containerId] = {
                    parent: container.parentNode,
                    sibling: container.nextSibling
                };
                // Move it to the very top layer of the body
                document.body.appendChild(container);
                wrapper.style.height = '85vh'; 
            } else {
                // Put it back exactly where it belongs
                const state = graphPopoutStates[containerId];
                if (state && state.parent) {
                    state.parent.insertBefore(container, state.sibling);
                }
                wrapper.style.height = '300px';
            }
            
            // Just resize the chart to fit its new home, no need to redraw!
            setTimeout(() => {
                if (chartType === 'xpm' && xpmChartInstance) xpmChartInstance.resize();
                if (chartType === 'roundxp' && roundXpChartInstance) roundXpChartInstance.resize();
                if (chartType === 'zpm' && zpmChartInstance) zpmChartInstance.resize();
            }, 50);
        }

        // --- UPDATED XPM CHART (No Flickering!) ---
        function renderXpmChart() {
            const canvas = document.getElementById('xpmChart');
            const wrapper = document.getElementById('chart-scroll-wrapper');
            if (!canvas || !wrapper) return;
            
            sizeGraphCanvas(canvas, wrapper, currentGraphLabels.length);
            
            // If the chart already exists, just update the data silently!
            if (xpmChartInstance) {
                xpmChartInstance.data.labels = currentGraphLabels;
                xpmChartInstance.data.datasets[0].data = currentGraphData;
                syncXpmOverlayDataset();
                xpmChartInstance.resize();
                xpmChartInstance.update('none'); // 'none' prevents the animation from restarting
                return;
            }
            
            // Otherwise, create it for the first time
            const ctx = canvas.getContext('2d');
            const theme = getGraphTheme();
            xpmChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: currentGraphLabels,
                    datasets: [{
                        label: 'XP Per Minute',
                        data: currentGraphData,
                        borderColor: theme.line,
                        backgroundColor: theme.lineFill,
                        borderWidth: 2, fill: true, tension: 0.2,
                        pointBackgroundColor: theme.point, pointRadius: 5,
                        pointHoverRadius: 8, pointBorderColor: theme.pointBorder,
                        pointBorderWidth: 2, pointHitRadius: 15,
                        pointStyle: currentThemeName === 'Glacial Frost' ? 'rectRot' : 'circle'
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    interaction: { mode: 'nearest', axis: 'x', intersect: true },
                    plugins: { 
                        legend: { display: false },
                        tooltip: { 
                            enabled: true, mode: 'nearest', intersect: true,
                            backgroundColor: 'rgba(0,0,0,0.9)', titleColor: theme.tooltip,
                            bodyColor: '#fff', borderColor: theme.tooltip, borderWidth: 1,
                            callbacks: {
                                title: function(t) { return `Round ${t[0].label}`; },
                                label: function(c) { return `XP/min: ${c.parsed.y.toLocaleString()}`; }
                            }
                        }
                    },
                    scales: { 
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' }, title: { display: true, text: 'XP per Minute', color: '#888' }},
                        zpmAxis: { display: zpmOverlayEnabled, position: 'right', beginAtZero: true, grid: { drawOnChartArea: false }, ticks: { color: theme.zpm }, title: { display: true, text: 'Zombies/min', color: theme.zpm }},
                        x: { grid: { color: '#333' }, ticks: { color: '#aaa', maxRotation: 45, minRotation: 45, autoSkip: true, maxTicksLimit: 8, stepSize: 1 }, title: { display: true, text: 'Round', color: '#888' }}
                    },
                    elements: { point: { hoverBorderWidth: 3, hoverBorderColor: '#fff' } },
                    layout: { padding: { top: 10, bottom: 10, left: 5, right: 5 } }
                }
            });
            syncXpmOverlayDataset();
            xpmChartInstance.update('none');
        }

        // --- UPDATED ROUND XP CHART (No Flickering!) ---
        function renderRoundXpChart() {
            const canvas = document.getElementById('roundXpChart');
            const wrapper = document.getElementById('roundxp-scroll-wrapper');
            if (!canvas || !wrapper) return;
            
            sizeGraphCanvas(canvas, wrapper, currentRoundXpLabels.length);
            
            // If the chart already exists, just update the data silently!
            if (roundXpChartInstance) {
                roundXpChartInstance.data.labels = currentRoundXpLabels;
                roundXpChartInstance.data.datasets[0].data = currentRoundXpData;
                roundXpChartInstance.resize();
                roundXpChartInstance.update('none'); 
                return;
            }
            
            // Otherwise, create it for the first time
            const ctx = canvas.getContext('2d');
            const theme = getGraphTheme();
            roundXpChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: currentRoundXpLabels, 
                    datasets: [{
                        label: 'XP Gained',
                        data: currentRoundXpData, 
                        backgroundColor: function(context) {
                            const t = getGraphTheme();
                            if (currentThemeName === 'Glacial Frost') {
                                const chart = context.chart;
                                const {ctx, chartArea} = chart;
                                if (!chartArea) return '#38c8ff';
                                const grad = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                                grad.addColorStop(0, '#38c8ff');
                                grad.addColorStop(0.5, '#7de9ff');
                                grad.addColorStop(1, '#d8fbff');
                                return grad;
                            }
                            return t.bar;
                        },
                        borderColor: function(context) {
                            const t = getGraphTheme();
                            if (currentThemeName === 'Glacial Frost') return '#eefaff';
                            return t.barBorder;
                        },
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    plugins: { 
                        legend: { display: false },
                        tooltip: { mode: 'index', intersect: false, titleColor: theme.tooltip } 
                    },
                    scales: { 
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' }, title: { display: true, text: 'XP Gained', color: '#888' }},
                        x: { grid: { display: false }, ticks: { color: '#aaa' }, title: { display: true, text: 'Round', color: '#888' }}
                    }
                }
            });
        }

        function renderZpmChart() {
            const canvas = document.getElementById('zpmChart');
            const wrapper = document.getElementById('zpm-scroll-wrapper');
            if (!canvas || !wrapper) return;

            sizeGraphCanvas(canvas, wrapper, currentZpmLabels.length);

            if (zpmChartInstance) {
                zpmChartInstance.data.labels = currentZpmLabels;
                zpmChartInstance.data.datasets[0].data = currentZpmData;
                zpmChartInstance.resize();
                zpmChartInstance.update('none');
                return;
            }

            const ctx = canvas.getContext('2d');
            const theme = getGraphTheme();
            zpmChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: currentZpmLabels,
                    datasets: [{
                        label: 'Zombies Per Minute',
                        data: currentZpmData,
                        borderColor: theme.zpm,
                        backgroundColor: theme.zpmFill,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.2,
                        pointBackgroundColor: theme.zpm,
                        pointRadius: 5,
                        pointHoverRadius: 8,
                        pointBorderColor: theme.pointBorder,
                        pointBorderWidth: 2,
                        pointHitRadius: 15,
                        pointStyle: currentThemeName === 'Glacial Frost' ? 'rectRot' : 'circle'
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    interaction: { mode: 'nearest', axis: 'x', intersect: true },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            enabled: true, mode: 'nearest', intersect: true,
                            backgroundColor: 'rgba(0,0,0,0.9)', titleColor: theme.zpm,
                            bodyColor: '#fff', borderColor: theme.zpm, borderWidth: 1,
                            callbacks: {
                                title: function(t) { return `Round ${t[0].label}`; },
                                label: function(c) { return `ZPM: ${Number(c.parsed.y).toLocaleString()}`; }
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' }, title: { display: true, text: 'Zombies per Minute', color: '#888' }},
                        x: { grid: { color: '#333' }, ticks: { color: '#aaa', maxRotation: 45, minRotation: 45, autoSkip: true, maxTicksLimit: 8, stepSize: 1 }, title: { display: true, text: 'Round', color: '#888' }}
                    },
                    layout: { padding: { top: 10, bottom: 10, left: 5, right: 5 } }
                }
            });
        }
            let isLive = true;
            let lastRound = 0;
            let GLOBAL_NAMES = [];
            let GLOBAL_MAPS = {};
            let MAP_KEYS = [];
            let currentMapIndex = 0;
            let currentStarredWeapons = [];
            let currentChalFilter = 'operations';

            let currentPlayerIndex = 0;
               let cachedPlayers = [];
               let currentGameId = "";

               // --- NEW PAGINATION CODE ---
            let currentHistoryPage = 1;
            let totalHistoryPages = 1;
            let currentHistoryFilters = { query: "", map: "", date_from: "", date_to: "", xp_min: "", xp_max: "", sort: "newest" };
            let historyFilterTimer = null;
            let pendingUpdateInfo = null;

               function changeHistoryPage(dir) {
                   currentHistoryPage += dir;
                   if (currentHistoryPage < 1) currentHistoryPage = 1;
                   if (currentHistoryPage > totalHistoryPages) currentHistoryPage = totalHistoryPages;
                   
                   document.getElementById('history-list').innerHTML = "";
                   updateSidebar();
               }

               function readHistoryFilters() {
                   const xpRange = document.getElementById('history-xp-range')?.value || "";
                   const xpParts = xpRange ? xpRange.split("-") : ["", ""];
                   currentHistoryFilters = {
                       query: (document.getElementById('history-search')?.value || "").trim(),
                       map: document.getElementById('history-map-filter')?.value || "",
                       date_from: document.getElementById('history-date-from')?.value || "",
                       date_to: document.getElementById('history-date-to')?.value || "",
                       xp_min: xpParts[0] || "",
                       xp_max: xpParts[1] || "",
                       sort: document.getElementById('history-sort')?.value || "newest"
                   };
                   return currentHistoryFilters;
               }

               function applyHistoryFilters() {
                   currentHistoryPage = 1;
                   const listEl = document.getElementById('history-list');
                   if (listEl) {
                       listEl.innerHTML = "";
                       listEl.dataset.signature = "";
                   }
                   readHistoryFilters();
                   updateSidebar();
               }

               function queueHistoryFilterUpdate() {
                   clearTimeout(historyFilterTimer);
                   historyFilterTimer = setTimeout(applyHistoryFilters, 250);
               }

               function clearHistoryFilters() {
                   const ids = ['history-search', 'history-map-filter', 'history-date-from', 'history-date-to', 'history-xp-range'];
                   ids.forEach(id => {
                       const el = document.getElementById(id);
                       if (el) el.value = "";
                   });
                   const sortEl = document.getElementById('history-sort');
                   if (sortEl) sortEl.value = "newest";
                   applyHistoryFilters();
               }
               // ---------------------------

            function toggleOverlays(checkbox) {
                window.pywebview.api.toggle_overlay_system(checkbox.checked);
            }

            function toggleOverlayComponent(component, checkbox) {
                window.pywebview.api.toggle_overlay_component(component, checkbox.checked);
            }

            function toggleGraphOverlays(checkbox) {
                window.pywebview.api.toggle_graph_overlay_system(checkbox.checked);
            }

            function toggleGraphOverlayComponent(component, checkbox) {
                window.pywebview.api.toggle_graph_overlay_component(component, checkbox.checked);
            }

            function previewOverlaySize(value) {
                const display = document.getElementById('overlay-size-value');
                if (display) display.innerText = `${value}%`;
            }

            function saveOverlaySize(value) {
                previewOverlaySize(value);
                window.pywebview.api.set_overlay_size(value).then(result => {
                    if (result && result.success) previewOverlaySize(result.overlay_size_percent);
                });
            }

            function toggleXpDebugger(checkbox) {
                window.pywebview.api.toggle_xp_debugger(checkbox.checked);
            }

            function toggleXpOverflowRecovery(checkbox) {
                window.pywebview.api.toggle_xp_overflow_recovery(checkbox.checked);
            }

            function hideWorkshopImages() {
                const targets = [
                    ['live-workshop-container', 'live-workshop-img']
                ];
                targets.forEach(([containerId, imgId]) => {
                    const container = document.getElementById(containerId);
                    const img = document.getElementById(imgId);
                    if (img) {
                        img.removeAttribute('src');
                        img.style.display = 'none';
                    }
                    if (container) container.style.display = 'none';
                });
            }

            function toggleWorkshopImages(checkbox) {
                workshopImagesEnabled = checkbox.checked;
                if (!workshopImagesEnabled) hideWorkshopImages();
                window.pywebview.api.toggle_workshop_images(checkbox.checked);
            }

            function setLanguageStatus(text) {
                const el = document.getElementById('language-status');
                if (el) el.innerText = text;
            }

            function getLocaleValue(path) {
                return path.split('.').reduce((value, key) => {
                    if (value && typeof value === 'object' && key in value) return value[key];
                    return undefined;
                }, activeLocale);
            }

            function localeText(path, fallback) {
                const translated = getLocaleValue(path);
                return translated || fallback;
            }

            function captureDefaultTranslations() {
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    if (key && !(key in defaultI18nText)) {
                        defaultI18nText[key] = el.textContent;
                    }
                });
                document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                    const key = el.getAttribute('data-i18n-placeholder');
                    const storeKey = `placeholder:${key}`;
                    if (key && !(storeKey in defaultI18nText)) {
                        defaultI18nText[storeKey] = el.getAttribute('placeholder') || '';
                    }
                });
            }

            function applyLocaleStrings() {
                captureDefaultTranslations();
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    const translated = getLocaleValue(key);
                    el.textContent = translated || defaultI18nText[key] || el.textContent;
                });
                document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                    const key = el.getAttribute('data-i18n-placeholder');
                    const translated = getLocaleValue(key);
                    el.setAttribute('placeholder', translated || defaultI18nText[`placeholder:${key}`] || '');
                });
            }

            async function loadLocaleStrings(languageCode) {
                activeLanguage = languageCode || 'en';
                activeLocale = await window.pywebview.api.get_locale_strings(languageCode || 'en') || {};
                applyLocaleStrings();
            }

            async function loadLanguageSelector() {
                const select = document.getElementById('language-selector');
                if (!select) return;
                const options = await window.pywebview.api.get_language_options();
                select.innerHTML = '';
                options.forEach(item => {
                    const opt = document.createElement('option');
                    opt.value = item.code;
                    opt.textContent = item.label;
                    select.appendChild(opt);
                });
                const current = await window.pywebview.api.get_active_language();
                select.value = current || 'en';
                await loadLocaleStrings(select.value);
                const label = select.options[select.selectedIndex] ? select.options[select.selectedIndex].textContent : 'English';
                setLanguageStatus('Status: ' + label);
            }

            async function changeLanguage(languageCode) {
                const res = await window.pywebview.api.set_active_language(languageCode);
                await loadLocaleStrings(res && res.language ? res.language : languageCode);
                const select = document.getElementById('language-selector');
                const label = select && select.options[select.selectedIndex] ? select.options[select.selectedIndex].textContent : languageCode;
                setLanguageStatus(res && res.success ? ('Status: ' + label) : 'Status: Could not save language');
                renderChangelog();
            }

            function setGlobalStatsStatus(text) {
                const el = document.getElementById('global-stats-status');
                if (el) el.innerText = text;
            }

            async function setGlobalStatsConsent(enabled) {
                globalStatsEnabled = !!enabled;
                const modal = document.getElementById('global-stats-modal');
                if (modal) modal.style.display = 'none';
                const toggle = document.getElementById('global-stats-toggle');
                if (toggle) toggle.checked = globalStatsEnabled;
                const res = await window.pywebview.api.set_global_stats_opt_in(globalStatsEnabled);
                setGlobalStatsStatus(res && res.msg ? res.msg : (globalStatsEnabled ? 'Enabled.' : 'Disabled.'));
            }

            async function toggleGlobalStats(checkbox) {
                globalStatsEnabled = checkbox.checked;
                const res = await window.pywebview.api.set_global_stats_opt_in(globalStatsEnabled);
                setGlobalStatsStatus(res && res.msg ? res.msg : (globalStatsEnabled ? 'Enabled.' : 'Disabled.'));
            }

            async function syncGlobalStatsNow() {
                setGlobalStatsStatus('Sync requested...');
                const res = await window.pywebview.api.sync_global_stats_now();
                setGlobalStatsStatus(res && res.msg ? res.msg : 'Sync request sent.');
            }

            function setCustomCamosStatus(text) {
                const el = document.getElementById('custom-camos-status');
                if (el) el.innerText = text;
            }

            async function syncCustomCamosNow() {
                setCustomCamosStatus('Checking remote camo database...');
                const res = await window.pywebview.api.sync_custom_camos_now();
                setCustomCamosStatus(res && res.msg ? res.msg : 'Custom camos sync complete.');
            }

            function setDiscordPresenceStatus(text) {
                const el = document.getElementById('discord-presence-status');
                if (el) el.innerText = text;
            }

            async function loadDiscordPresenceSettings() {
                const settings = await window.pywebview.api.get_discord_presence_settings();
                const toggle = document.getElementById('discord-presence-toggle');
                const clientId = document.getElementById('discord-client-id');
                const largeImage = document.getElementById('discord-large-image');
                if (toggle) toggle.checked = !!(settings && settings.enabled);
                if (clientId) clientId.value = settings && settings.client_id ? settings.client_id : '';
                if (largeImage) largeImage.value = settings && settings.large_image ? settings.large_image : '';
                setDiscordPresenceStatus(localeText('common.status', 'Status') + ': ' + ((settings && settings.status) || localeText('status.not_connected_value', 'Not connected')));
            }

            async function saveDiscordPresenceSettings() {
                const toggle = document.getElementById('discord-presence-toggle');
                const clientId = document.getElementById('discord-client-id');
                const largeImage = document.getElementById('discord-large-image');
                setDiscordPresenceStatus(localeText('status.saving', 'Status: Saving...'));
                const res = await window.pywebview.api.save_discord_presence_settings(
                    toggle ? toggle.checked : false,
                    clientId ? clientId.value : '',
                    largeImage ? largeImage.value : ''
                );
                setDiscordPresenceStatus(localeText('common.status', 'Status') + ': ' + (res && res.msg ? res.msg : localeText('status.saved_value', 'Saved.')));
            }

            function setT7DiscordStatus(text) {
                const el = document.getElementById('t7-discord-status');
                if (el) el.innerText = text;
            }

            async function loadT7DiscordPresenceSetting() {
                const res = await window.pywebview.api.get_t7_discord_presence_settings();
                const toggle = document.getElementById('t7-discord-toggle');
                if (toggle) {
                    toggle.disabled = !(res && res.success);
                    toggle.checked = !!(res && res.enabled);
                }
                setT7DiscordStatus(localeText('common.status', 'Status') + ': ' + (res && res.msg ? res.msg : localeText('status.could_not_read_t7_json_value', 'Could not read t7.json.')));
            }

            async function saveT7DiscordPresenceSetting() {
                const toggle = document.getElementById('t7-discord-toggle');
                if (toggle && !toggle.checked) {
                    const confirmed = confirm(
                        localeText('settings.confirm_disable_t7_discord_title', 'Turn off the official UEM/T7 Discord Presence?') + '\\n\\n' +
                        localeText('settings.confirm_disable_t7_discord_body', 'This changes discord_enabled in BO3\\'s players/t7.json and may stop the built-in UEM/T7 Discord card from showing. Restart BO3/UEM after changing it.')
                    );
                    if (!confirmed) {
                        toggle.checked = true;
                        setT7DiscordStatus(localeText('status.t7_left_enabled', 'Status: Official UEM/T7 Discord presence was left enabled.'));
                        return;
                    }
                }
                setT7DiscordStatus(localeText('status.saving', 'Status: Saving...'));
                const res = await window.pywebview.api.set_t7_discord_presence(toggle ? toggle.checked : false);
                if (toggle && res && typeof res.enabled === 'boolean') toggle.checked = res.enabled;
                setT7DiscordStatus(localeText('common.status', 'Status') + ': ' + (res && res.msg ? res.msg : localeText('status.could_not_update_t7_json_value', 'Could not update t7.json.')));
            }

            function maybeShowGlobalStatsPrompt() {
                if (!showGlobalStatsPrompt) return;
                const modal = document.getElementById('global-stats-modal');
                if (modal) modal.style.display = 'flex';
            }

            function setUpdateStatus(text) {
                const settingsEl = document.getElementById('update-settings-status');
                if (settingsEl) settingsEl.innerText = text;
            }

            function showUpdateNotice(info) {
                pendingUpdateInfo = info;
                const notice = document.getElementById('update-notice');
                const title = document.getElementById('update-title');
                const summary = document.getElementById('update-summary');
                if (!notice) return;
                if (!info || !info.update_available) {
                    notice.style.display = 'none';
                    return;
                }
                const version = escapeHtml(info.version || 'new version');
                if (title) title.innerText = `UPDATE ${version} AVAILABLE`;
                if (summary) summary.innerText = info.name || 'A new BO3 Tracker build is ready.';
                notice.style.display = 'block';
                setUpdateStatus(`Update ${info.version} is available.`);
            }

            async function checkForUpdates(showCurrent) {
                if (showCurrent) setUpdateStatus('Checking GitHub releases...');
                try {
                    const info = await window.pywebview.api.check_for_updates();
                    if (info && info.update_available) {
                        showUpdateNotice(info);
                    } else {
                        showUpdateNotice(null);
                        if (showCurrent) {
                            setUpdateStatus(info && info.msg ? info.msg : 'You are on the latest version.');
                        }
                    }
                } catch(e) {
                    if (showCurrent) setUpdateStatus('Could not check GitHub releases right now.');
                }
            }

            async function startUpdate() {
                if (!pendingUpdateInfo) {
                    await checkForUpdates(true);
                    if (!pendingUpdateInfo) return;
                }
                setUpdateStatus('Starting updater...');
                const res = await window.pywebview.api.launch_updater(pendingUpdateInfo);
                if (!res || !res.success) {
                    setUpdateStatus(res && res.msg ? res.msg : 'Updater could not be started.');
                }
            }

            async function rollbackLastUpdate() {
                const confirmed = confirm('Rollback to the app version saved before the last update? BO3 Tracker will close and restart if a backup is available.');
                if (!confirmed) return;
                setUpdateStatus('Starting rollback...');
                const res = await window.pywebview.api.rollback_last_update();
                if (!res || !res.success) {
                    setUpdateStatus(res && res.msg ? res.msg : 'Rollback could not be started.');
                }
            }

            function formatReleaseNotes(notes) {
                const raw = String(notes || '').trim();
                if (!raw) return '<div class="muted-empty">No release notes were published for this version.</div>';
                return escapeHtml(raw)
                    .replace(/\\r\\n/g, '\\n')
                    .replace(/\\n{3,}/g, '\\n\\n')
                    .replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>')
                    .replace(/^###\\s+(.+)$/gm, '<div class="release-heading release-heading-small">$1</div>')
                    .replace(/^##\\s+(.+)$/gm, '<div class="release-heading">$1</div>')
                    .replace(/^#\\s+(.+)$/gm, '<div class="release-heading">$1</div>')
                    .replace(/^- (.+)$/gm, '<div class="release-bullet">&bull; $1</div>')
                    .replace(/\\n/g, '<br>');
            }

            let latestChangelogInfo = null;

            function extractLocalizedReleaseNotes(notes, languageCode) {
                const raw = String(notes || '').trim();
                if (!raw) return '';
                const blocks = {};
                const blockRegex = /<!--\\s*(?:changelog|lang):([a-z]{2}(?:-[a-z0-9]+)?)\\s*-->([\\s\\S]*?)<!--\\s*\\/(?:changelog|lang):\\1\\s*-->/gi;
                let match;
                while ((match = blockRegex.exec(raw)) !== null) {
                    blocks[String(match[1] || '').toLowerCase()] = String(match[2] || '').trim();
                }
                const codes = Object.keys(blocks);
                if (!codes.length) return raw;
                const requested = String(languageCode || 'en').toLowerCase();
                const base = requested.split('-')[0];
                return blocks[requested] || blocks[base] || blocks.en || blocks[codes[0]] || raw;
            }

            function renderChangelog() {
                const status = document.getElementById('changelog-status');
                const title = document.getElementById('changelog-release-title');
                const notes = document.getElementById('changelog-notes');
                const info = latestChangelogInfo;
                if (!notes || !info || !info.success) return;
                const version = info.version || 'latest';
                if (title) title.innerText = `${info.name || 'BO3 Tracker'} (${version})`;
                if (status) status.innerText = info.is_current ? `Latest release matches this app (${version}).` : `Latest GitHub release is ${version}.`;
                if (status && info.is_older_than_app) status.innerText = `Latest GitHub release is ${version}; this app is """ + app_version + """.`;
                notes.innerHTML = formatReleaseNotes(extractLocalizedReleaseNotes(info.notes, activeLanguage));
            }

            async function loadChangelog(forceRefresh=false) {
                const status = document.getElementById('changelog-status');
                const title = document.getElementById('changelog-release-title');
                const notes = document.getElementById('changelog-notes');
                if (!notes) return;
                if (status) status.innerText = forceRefresh ? 'Refreshing GitHub release notes...' : 'Loading latest GitHub release notes...';
                try {
                    const info = await window.pywebview.api.get_latest_changelog();
                    if (!info || !info.success) {
                        if (status) status.innerText = info && info.msg ? info.msg : 'Could not load GitHub release notes.';
                        notes.innerHTML = '<div class="muted-empty">Release notes are unavailable right now.</div>';
                        return;
                    }
                    latestChangelogInfo = info;
                    renderChangelog();
                } catch(e) {
                    if (status) status.innerText = 'Could not load GitHub release notes.';
                    notes.innerHTML = '<div class="muted-empty">Release notes are unavailable right now.</div>';
                }
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

            function switchTab(tabName) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.sb-item').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.config-btn').forEach(el => el.classList.remove('active'));
                
                document.getElementById('tab-' + tabName).classList.add('active');
                
                if(tabName === 'live') {
                    isLive = true;
                    document.getElementById('live-btn').classList.add('active');
                    
                    // --- NEW: REDRAW GRAPH WHEN RETURNING ---
                    const graphContainer = document.getElementById('xpm-graph-container');
                    const zpmContainer = document.getElementById('zpm-graph-container');
                    if (graphContainer && graphContainer.style.display === 'block') {
                        // A tiny 50ms delay ensures the tab is fully visible before Chart.js does its math
                        setTimeout(() => { renderXpmChart(); }, 50); 
                    }
                    if (zpmContainer && zpmContainer.style.display === 'block') {
                        setTimeout(() => { renderZpmChart(); }, 50);
                    }
                    // ----------------------------------------
                    
                } else if(tabName === 'camo') {
                    isLive = false;
                    document.getElementById('camo-btn').classList.add('active');
                } else if(tabName === 'career') {
                    isLive = false;
                    document.getElementById('career-btn').classList.add('active');
                    loadCareerData();
                } else if(tabName === 'mapselection') {
                    isLive = false;
                    document.getElementById('career-btn').classList.add('active');
                    renderMapSelectionPage();
                } else if(tabName === 'mapdetail') {
                    isLive = false;
                    document.getElementById('career-btn').classList.add('active');
                } else if(tabName === 'weaponusage') {
                    isLive = false;
                    document.getElementById('career-btn').classList.add('active');
                    loadWeaponUsage();
                } else if(tabName === 'bestmatches') {
                    isLive = false;
                    document.getElementById('bestmatches-btn').classList.add('active');
                    loadBestMatches();
                } else if(tabName === 'challenges') {
                    isLive = false;
                    document.getElementById('chal-btn').classList.add('active');
                    loadChallenges(); 
                } else if(tabName === 'customization') {
                    isLive = false;
                    document.getElementById('customization-btn').classList.add('active');
                    loadThemeList();
                    loadCardList();
                    loadEmblemList();
                } else if(tabName === 'settings') {
                    isLive = false;
                    document.getElementById('settings-btn').classList.add('active');
                    loadLanguageSelector();
                } else {
                    isLive = false; 
                    if (tabName === 'help') {
                        document.getElementById('help-btn').classList.add('active');
                        loadChangelog(false);
                    }
                }
            }
            
            // --- THEME & CARD FUNCTIONS ---
            async function loadThemeList() {
                const themes = await window.pywebview.api.get_available_themes();
                const select = document.getElementById('theme-selector');
                select.innerHTML = '<option value="default">Default Tactical</option>';
                themes.forEach(t => {
                    const display = t.charAt(0).toUpperCase() + t.slice(1);
                    select.innerHTML += `<option value="${t}">${display}</option>`;
                });
                const current = await window.pywebview.api.get_active_theme();
                if(current) select.value = current;
            }

            async function loadCardList() {
                const cards = await window.pywebview.api.get_unlocked_calling_cards();
                const select = document.getElementById('card-selector');
                select.innerHTML = '<option value="default">None Equipped</option>';
                cards.forEach(c => {
                    if(c !== 'default' && !c.includes('void') && !c.includes('origins') && !c.includes('redhex') && !c.includes('gold') && !c.includes('retro') && !c.includes('matrix')) {
                        select.innerHTML += `<option value="${c}">${c.replace('_',' ').toUpperCase()}</option>`;
                    }
                });
                const current = await window.pywebview.api.get_active_card();
                if(current) {
                    select.value = current;
                    previewCard(current);
                }
            }

            async function loadEmblemList() {
                const emblems = await window.pywebview.api.get_unlocked_emblems();
                const select = document.getElementById('emblem-selector');
                select.innerHTML = '<option value="default">None Equipped</option>';
                emblems.forEach(e => {
                    if(e !== 'default') {
                        select.innerHTML += `<option value="${e}">${e.replace('_',' ').toUpperCase()}</option>`;
                    }
                });
                const current = await window.pywebview.api.get_active_emblem();
                if(current) {
                    select.value = current;
                    previewEmblem(current);
                }
            }

            function showMedia(src, imgId, vidId) {
                const img = document.getElementById(imgId);
                const vid = document.getElementById(vidId);
                
                if (!src) {
                    img.style.display = 'none';
                    vid.style.display = 'none';
                    return;
                }

                if (src.startsWith('data:video')) {
                    img.style.display = 'none';
                    vid.src = src;
                    vid.style.display = 'block';
                    vid.play().catch(e => console.log("Autoplay blocked/failed", e)); 
                } else {
                    vid.style.display = 'none';
                    vid.pause();
                    img.src = src;
                    img.style.display = 'block';
                }
            }

            async function previewCard(cardName) {
                if(cardName === 'default') {
                    showMedia(null, 'card-preview', 'card-preview-video');
                    return;
                }
                const src = await window.pywebview.api.get_card_image(cardName);
                showMedia(src, 'card-preview', 'card-preview-video');
            }

            async function previewEmblem(emblemName) {
                if(emblemName === 'default') {
                    showMedia(null, 'emblem-preview', 'emblem-preview-video');
                    return;
                }
                const src = await window.pywebview.api.get_emblem_image(emblemName);
                showMedia(src, 'emblem-preview', 'emblem-preview-video');
            }

            async function applySelectedCard() {
                const sel = document.getElementById('card-selector');
                await window.pywebview.api.set_active_card(sel.value);
                alert("Player Card Equipped!");
            }

            async function applySelectedEmblem() {
                const sel = document.getElementById('emblem-selector');
                await window.pywebview.api.set_active_emblem(sel.value);
                alert("Emblem Equipped!");
            }

            async function applySelectedTheme() {
                const select = document.getElementById('theme-selector');
                const themeName = select.value;
                const cssContent = await window.pywebview.api.get_theme_content(themeName);
                document.getElementById('theme-injector').innerHTML = cssContent;
                await window.pywebview.api.set_active_theme(themeName);
                currentThemeName = themeName || 'default';
                applyGraphTheme();
                applySettingsCopy(currentThemeName);
                applyLocaleStrings();
                alert("Theme Applied: " + themeName);
            }

            // --- NEW: BACKUP LOGIC ---
            async function backupStats() {
                try {
                    const res = await window.pywebview.api.backup_player_stats();
                    if (res.success) {
                        alert(res.msg);
                    } else {
                        alert("Backup Failed: " + res.msg);
                    }
                } catch(e) {
                    alert("An error occurred during backup.");
                    console.error(e);
                }
            }

            async function restoreStats() {
                const confirmed = confirm(
                    'Restore UEM player stats from a backup zip?\\n\\n' +
                    'This can replace stats_zm_*.cgp files in your BO3 players folder. ' +
                    'The tracker will create a safety backup first when existing files are found.'
                );
                if (!confirmed) return;

                try {
                    const res = await window.pywebview.api.restore_player_stats();
                    if (res.success) {
                        alert(res.msg);
                    } else {
                        alert("Restore Failed: " + res.msg);
                    }
                } catch(e) {
                    alert("An error occurred during restore.");
                    console.error(e);
                }
            }

            async function backupTrackerConfig() {
                try {
                    const res = await window.pywebview.api.backup_tracker_config();
                    if (res.success) {
                        alert(res.msg);
                    } else {
                        alert("Config Backup Failed: " + res.msg);
                    }
                } catch(e) {
                    alert("An error occurred during tracker config backup.");
                    console.error(e);
                }
            }

            async function restoreTrackerConfig() {
                const confirmed = confirm(
                    'Restore BO3 Tracker config from a backup zip?\\n\\n' +
                    'This can replace tracker settings and local progress files. ' +
                    'The tracker will create a safety backup first when existing files are found.'
                );
                if (!confirmed) return;

                try {
                    const res = await window.pywebview.api.restore_tracker_config(true);
                    if (res.success) {
                        alert(res.msg);
                    } else {
                        alert("Config Restore Failed: " + res.msg);
                    }
                } catch(e) {
                    alert("An error occurred during tracker config restore.");
                    console.error(e);
                }
            }

            async function addBestMatch() {
                const btn = document.getElementById('best-match-btn');
                try {
                    if (btn) btn.disabled = true;
                    const res = await window.pywebview.api.add_current_best_match(currentGameId);
                    alert(res.msg || (res.success ? "Best match saved." : "Could not save best match."));
                    const bestTab = document.getElementById('tab-bestmatches');
                    if (res.success && bestTab && bestTab.classList.contains('active')) {
                        loadBestMatches();
                    }
                } catch(e) {
                    alert("Could not save best match: " + e);
                } finally {
                    if (btn) btn.disabled = false;
                }
            }

            async function loadBestMatches() {
                const container = document.getElementById('best-matches-list');
                if (!container) return;
                try {
                    const matches = await window.pywebview.api.get_best_matches();
                    if (!matches || matches.length === 0) {
                        container.innerHTML = "<div class='muted-empty'>No best matches saved yet. Use Add Best Match on the live dashboard.</div>";
                        return;
                    }
                    let html = "";
                    matches.forEach(item => {
                        const xpText = item.match_xp && item.match_xp > 0 ? `${parseInt(item.match_xp).toLocaleString()} XP` : "XP not recorded";
                        const missingText = item.exists ? "" : "<span class='missing-archive-label'>MISSING ARCHIVE</span>";
                        html += `
                            <div class="sb-item best-match-row" onclick="loadHistory('${escapeHtml(item.id)}', this)">
                                <div class="best-match-row-inner">
                                    <div class="min-content">
                                        <div class="sb-map">${escapeHtml(item.map)}${missingText}</div>
                                        <div class="sb-date">Round ${escapeHtml(item.round)} // ${escapeHtml(item.time)} // ${escapeHtml(item.date)}</div>
                                        <div class="sb-id" title="${escapeHtml(item.id)}">${escapeHtml(item.id)}</div>
                                    </div>
                                    <div class="best-match-actions">
                                        <div class="best-match-xp">${xpText}</div>
                                        <button class="nav-btn-small remove-best-match-btn" onclick="removeBestMatch(event, '${escapeHtml(item.id)}')">REMOVE</button>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    container.innerHTML = html;
                } catch(e) {
                    container.innerHTML = "<div class='error-empty'>Could not load best matches.</div>";
                    console.error("Best Matches Load Error", e);
                }
            }

            async function removeBestMatch(event, gameId) {
                event.stopPropagation();
                if (!confirm("Remove this match from Best Matches?")) return;
                try {
                    const res = await window.pywebview.api.remove_best_match(gameId);
                    if (!res.success) {
                        alert(res.msg || "Could not remove best match.");
                        return;
                    }
                    loadBestMatches();
                } catch(e) {
                    alert("Could not remove best match: " + e);
                }
            }

            // --- CHALLENGE LOGIC ---
            function filterChallenges(cat) {
                currentChalFilter = cat;
                const container = document.getElementById('challenge-list');
                container.innerHTML = ""; 
                loadChallenges();
            }

            async function loadChallenges() {
                const list = await window.pywebview.api.get_challenges();
                const container = document.getElementById('challenge-list');
                
                if (currentChalFilter === 'themes') {
                    const themeGroups = {};
                    const legacyThemeGroups = [
                        { name: 'Void Mastery', prefix: 'c_void_' },
                        { name: 'Origins Mastery', prefix: 'c_org_' },
                        { name: 'Red Hex Mastery', prefix: 'c_red_' },
                        { name: 'Gold Mastery', prefix: 'c_gold_' },
                        { name: 'Retro Mastery', prefix: 'c_retro_' },
                        { name: 'Matrix Mastery', prefix: 'c_mat_' },
                    ];
                    
                    list.forEach(c => {
                        if (c.id.startsWith('c_auto_th_')) {
                            const match = c.id.match(/^c_auto_th_(.+)_[0-9]+$/);
                            if (match) {
                                const tName = match[1];
                                const displayName = tName
                                    .replace(/_/g, ' ')
                                    .split(' ')
                                    .map(part => part ? part.charAt(0).toUpperCase() + part.slice(1) : part)
                                    .join(' ');
                                if (!themeGroups[displayName]) {
                                    themeGroups[displayName] = `c_auto_th_${tName}`;
                                }
                            }
                        }
                    });
                    
                    let html = "";
                    legacyThemeGroups.forEach(group => {
                        const themeChallenges = list.filter(c => c.id.startsWith(group.prefix));
                        if(themeChallenges.length > 0) {
                            html += `<div class="theme-header">${group.name.toUpperCase()}</div>`;
                            themeChallenges.forEach(c => html += renderChallengeCardInner(c, true));
                        }
                    });
                    for (const [name, prefix] of Object.entries(themeGroups)) {
                        const themeChallenges = list.filter(c => c.id.startsWith(prefix));
                        if(themeChallenges.length > 0) {
                            html += `<div class="theme-header">${name} MASTERY</div>`;
                            themeChallenges.forEach(c => html += renderChallengeCardInner(c, true));
                        }
                    }
                    container.innerHTML = html;
                    return;
                }

                const filtered = list.filter(c => {
                    // Only exclude theme challenges from operations/weekly, not from lifetime
                    if (currentChalFilter !== 'lifetime' && (
                        c.id.startsWith('c_void') || c.id.startsWith('c_org') || c.id.startsWith('c_red') || 
                        c.id.startsWith('c_gold') || c.id.startsWith('c_retro') || c.id.startsWith('c_mat') ||
                        c.id.startsWith('c_auto_th_'))) {
                        return false; 
                    }
                    if(currentChalFilter === 'lifetime') return c.cat === 'lifetime';
                    if(currentChalFilter === 'operations') return c.cat === 'operations';
                    if(currentChalFilter === 'weekly') return c.cat === 'weekly';
                    return true;
                });

                if (currentChalFilter === 'operations') {
                    container.innerHTML = renderOperationsChallenges(filtered);
                    return;
                }

                filtered.forEach(c => {
                    const existingCard = document.getElementById(`chal-${c.id}`);
                    const newHTML = renderChallengeCardInner(c, false);
                    
                    if (existingCard) {
                        if (existingCard.innerHTML !== newHTML) {
                             existingCard.innerHTML = newHTML;
                             existingCard.className = `chal-card ${c.completed?'done':''}`;
                        }
                    } else {
                        const div = document.createElement('div');
                        div.id = `chal-${c.id}`;
                        div.className = `chal-card ${c.completed?'done':''}`;
                        div.innerHTML = newHTML;
                        container.appendChild(div);
                    }
                });
            }

            function isMapChallenge(c) {
                return c && (c.map_challenge || c.map_steam_link || c.steam_link || c.workshop_id);
            }

            function getMapChallengeKey(c) {
                return String(c.map_steam_link || c.steam_link || c.workshop_id || c.map_name || 'unknown-map').trim();
            }

            function renderOperationsChallenges(challenges) {
                const normal = [];
                const mapGroups = {};

                challenges.forEach(c => {
                    if (!isMapChallenge(c)) {
                        normal.push(c);
                        return;
                    }
                    const key = getMapChallengeKey(c);
                    if (!mapGroups[key]) {
                        mapGroups[key] = {
                            name: String(c.map_name || 'Unknown Workshop Map').trim(),
                            link: String(c.map_steam_link || c.steam_link || c.workshop_id || '').trim(),
                            challenges: []
                        };
                    }
                    mapGroups[key].challenges.push(c);
                });

                let html = "";
                normal.forEach(c => {
                    html += `<div id="chal-${escapeHtml(c.id)}" class="chal-card ${c.completed?'done':''}">${renderChallengeCardInner(c, false)}</div>`;
                });

                Object.values(mapGroups).forEach(group => {
                    const href = normalizeWorkshopLink(group.link);
                    const linkHtml = href
                        ? `<a class="map-challenge-heading-link" href="${escapeHtml(href)}" target="_blank">${escapeHtml(href)}</a>`
                        : `<span class="map-challenge-heading-link muted">No Steam Workshop link</span>`;
                    html += `
                        <div class="map-challenge-section">
                            <div class="map-challenge-heading">
                                <div class="map-challenge-heading-name">${escapeHtml(group.name)}</div>
                                ${linkHtml}
                            </div>
                            <div class="map-challenge-grid">
                    `;
                    group.challenges.forEach(c => {
                        html += `<div id="chal-${escapeHtml(c.id)}" class="chal-card ${c.completed?'done':''}">${renderChallengeCardInner(c, false)}</div>`;
                    });
                    html += `
                            </div>
                        </div>
                    `;
                });

                return html || `<div class="muted-empty">No challenges found.</div>`;
            }

            function renderChallengeCardInner(c, isThemeView) {
                const pct = Math.min(100, Math.round((c.progress / c.target) * 100));
                const isDone = c.completed;
                let btnText = "LOCKED";
                let btnClass = "";
                let action = "";
                let rewardTxt = "";

                if(c.reward_type === 'theme') rewardTxt = `🏆 THEME: ${c.reward_val.toUpperCase()}`;
                else if(c.reward_type === 'xp') rewardTxt = `⭐ XP: ${c.reward_val}`;
                else if(c.reward_type === 'calling_card') rewardTxt = `📇 CARD: ${c.reward_val}`;
                else if(c.reward_type === 'emblem') rewardTxt = `◆ EMBLEM: ${c.reward_val}`;
                else rewardTxt = `REWARD: ${c.reward_val}`;

                if (isDone) {
                    if (c.reward_type === 'theme') {
                        btnText = "EQUIP THEME";
                        btnClass = "active";
                        action = `applyTheme('${c.reward_val}')`;
                    } else if (c.reward_type === 'calling_card') {
                        btnText = "UNLOCKED"; 
                        btnClass = "active";
                    } else if (c.reward_type === 'emblem') {
                        btnText = "UNLOCKED";
                        btnClass = "active";
                    } else {
                        btnText = "COMPLETED";
                        btnClass = "active"; 
                    }
                }

                if (isThemeView) {
                     return `
                    <div class="chal-card ${isDone?'done':''}">
                        <div class="challenge-card-head">
                            <div class="challenge-title">${c.title}</div>
                            <div class="challenge-category">${c.cat ? c.cat.toUpperCase() : ''}</div>
                        </div>
                        <div class="challenge-desc">${c.desc}</div>
                        <div class="challenge-reward">${rewardTxt}</div>
                        <div class="progress-bar"><div class="fill" style="width:${pct}%"></div></div>
                        <div class="challenge-progress-text">${parseInt(c.progress)} / ${c.target}</div>
                        <button class="chal-btn ${btnClass}" onclick="${action}">${btnText}</button>
                    </div>`;
                }

                return `
                        <div class="challenge-card-head">
                            <div class="challenge-title">${c.title}</div>
                            <div class="challenge-category">${c.cat ? c.cat.toUpperCase() : ''}</div>
                        </div>
                        <div class="challenge-desc">${c.desc}</div>
                        <div class="challenge-reward">${rewardTxt}</div>
                        <div class="progress-bar"><div class="fill" style="width:${pct}%"></div></div>
                        <div class="challenge-progress-text">${parseInt(c.progress)} / ${c.target}</div>
                        <button class="chal-btn ${btnClass}" onclick="${action}">${btnText}</button>
                `;
            }

            function normalizeWorkshopLink(value) {
                const raw = String(value || '').trim();
                if (!raw || raw === '0') return '';
                if (new RegExp('^https?://', 'i').test(raw)) return raw;
                return `https://steamcommunity.com/sharedfiles/filedetails/?id=${encodeURIComponent(raw)}`;
            }

            async function resetOps() {
                if(confirm("Are you sure you want to reset all challenge progress? This cannot be undone.")) {
                    await window.pywebview.api.reset_challenges_api();
                    alert("Challenges Reset.");
                    loadChallenges(); 
                }
            }
            
            let careerMapData = null; // Store the map data for toggling
            let mapSelectionData = [];
            let mapSelectionPage = 1;
            const mapSelectionPageSize = 24;
            let currentMapDetail = null;
            let mapDetailRoundChartInstance = null;
            let mapDetailPage = 1;
            const mapDetailPageSize = 25;
            let mapDetailTotalMatches = 0;
            let mapDetailCurrentMap = "";
            
            async function loadCareerData() {
                 // Fetch and display Top XP Maps
                 loadTopXPMaps(); 

                 const activeCard = await window.pywebview.api.get_active_card();
                 if(activeCard && activeCard !== 'default') {
                     const src = await window.pywebview.api.get_card_image(activeCard);
                     showMedia(src, 'card-display', 'card-display-video');
                 } else {
                     showMedia(null, 'card-display', 'card-display-video');
                 }

                 const activeEmblem = await window.pywebview.api.get_active_emblem();
                 if(activeEmblem && activeEmblem !== 'default') {
                     const emblemSrc = await window.pywebview.api.get_emblem_image(activeEmblem);
                     showMedia(emblemSrc, 'emblem-display', 'emblem-display-video');
                 } else {
                     showMedia(null, 'emblem-display', 'emblem-display-video');
                 }

                 try {
                     const levelInfo = await window.pywebview.api.get_career_level_info();
                     if(levelInfo && !levelInfo.error) {
                         const prestBox = document.getElementById('career-prest-box');
                         const prestImg = document.getElementById('career-prest-icon');
                         if(levelInfo.prest_icon || levelInfo.leg_icon || levelInfo.abso_icon || levelInfo.ult_icon) {
                             prestBox.style.display = 'block';
                             
                             const oldIcons = prestBox.querySelectorAll('.custom-tier-icon');
                             oldIcons.forEach(icon => icon.remove());

                             if(levelInfo.prest_icon) {
                                 prestImg.src = levelInfo.prest_icon;
                                 prestImg.style.display = 'inline-block';
                             } else {
                                 prestImg.style.display = 'none';
                             }

                             const addIcon = (src) => {
                                 if (!src) return;
                                 const img = document.createElement('img');
                                 img.src = src;
                                 img.className = 'custom-tier-icon';
                                 let targetHeight = prestImg.clientHeight;
                                 if (targetHeight === 0) {
                                     img.style.height = '28px';
                                 } else {
                                     img.style.height = targetHeight + 'px';
                                 }
                                 img.style.width = 'auto';
                                 img.style.objectFit = 'contain';
                                 img.style.marginRight = '6px';
                                 prestBox.insertBefore(img, prestImg);
                             };

                             addIcon(levelInfo.leg_icon);
                             addIcon(levelInfo.abso_icon);
                             addIcon(levelInfo.ult_icon);
                         }
                         const lvlBox = document.getElementById('career-lvl-box');
                         const lvlImg = document.getElementById('career-lvl-icon');
                         if(levelInfo.lvl_icon) {
                             lvlImg.src = levelInfo.lvl_icon;
                             lvlBox.style.display = 'block';
                         }
                         document.getElementById('career-rmain').innerText = levelInfo.r_main;
                         document.getElementById('career-rsub').innerText = levelInfo.r_sub;
                         document.getElementById('career-title').innerText = levelInfo.title;
                         document.getElementById('career-map-name').innerText = 'Map: ' + levelInfo.map_name;
                         document.getElementById('career-xp-text').innerText = parseInt(levelInfo.current_xp).toLocaleString() + ' / ' + parseInt(levelInfo.xp_required).toLocaleString() + ' XP';
                         document.getElementById('career-xp-pct').innerText = levelInfo.progress_pct + '%';
                         document.getElementById('career-xp-bar').style.width = levelInfo.progress_pct + '%';
                          if(levelInfo.progress_pct >= 100) {
                              document.getElementById('career-xp-bar').classList.add('max');
                          } else {
                              document.getElementById('career-xp-bar').classList.remove('max');
                          }
                          const workshopContainer = document.getElementById('career-workshop-container');
                          const workshopImg = document.getElementById('career-workshop-img');
                          workshopImg.style.display = 'none';
                          workshopContainer.style.display = 'none';
                      }
                 } catch(e) { console.error("Career Level Load Error", e); }

                 try {
                    const data = await window.pywebview.api.get_lifetime_stats();
                    if(data && !data.error) {
                        document.getElementById('life_kills').innerText = parseInt(data.totals.kills).toLocaleString();
                        document.getElementById('life_headshots').innerText = parseInt(data.totals.headshots).toLocaleString();
                        document.getElementById('life_hs_pct').innerText = data.ratios.hs_percent + "%";
                        let favGunsText = "None (0)";
if (data.favorite_weapons && data.favorite_weapons.length > 0) {
    // Joins the top 3 weapons with a line break so they stack neatly on the right side
    favGunsText = data.favorite_weapons.map(w => w.name + " (" + w.kills.toLocaleString() + ")").join("<br>");
}
document.getElementById('life_fav_gun').innerHTML = favGunsText;
                        
                        document.getElementById('life_rounds').innerText = parseInt(data.totals.rounds).toLocaleString();
                        document.getElementById('life_time').innerText = data.time_str;
                        document.getElementById('life_matches').innerText = data.totals.matches;
                        document.getElementById('life_kpd').innerText = data.ratios.kpd;
                        
                        document.getElementById('life_doors').innerText = parseInt(data.totals.doors).toLocaleString();
                        document.getElementById('life_gums').innerText = parseInt(data.totals.gums).toLocaleString();
                        document.getElementById('life_box').innerText = parseInt(data.totals.box).toLocaleString();
                        document.getElementById('life_pts').innerText = parseInt(data.totals.pts).toLocaleString();
                        
                       let mapHtml = "";
                        const sortedMaps = Object.entries(data.best_map_rounds).sort((a, b) => b[1] - a[1]);
                        for (const [map, rnd] of sortedMaps) {
                            mapHtml += `<div class="compact-stat-row map-detail-link" data-map="${escapeHtml(map)}" onclick="openMapDetailFromElement(this)">
                                <span>${escapeHtml(map)}</span><span class="score-value">${parseInt(rnd || 0).toLocaleString()}</span>
                            </div>`;
                        }
                        document.getElementById('life_map_list').innerHTML = mapHtml;

                        // --- NEW CODE FOR MOST PLAYED MAPS ---
                        careerMapData = data; 
                        renderMostPlayedMaps(); 
                        // -------------------------------------
                    }
                } catch(e) { console.error("Career Load Error", e); }
            }
            
            // ---> PASTE THE NEW FUNCTION RIGHT HERE <---
            function renderMostPlayedMaps() {
                if (!careerMapData) return;
                const sortBy = document.getElementById('map-sort-toggle').value;
                let playedHtml = "";
                
                if (sortBy === 'matches' && careerMapData.top_played_maps && careerMapData.top_played_maps.length > 0) {
                    careerMapData.top_played_maps.forEach(entry => {
                        playedHtml += `<div class="compact-list-row map-detail-link" data-map="${escapeHtml(entry.name)}" onclick="openMapDetailFromElement(this)">
                            <span class="list-name">${escapeHtml(entry.name)}</span>
                            <span class="list-highlight">${parseInt(entry.count || 0).toLocaleString()} Matches</span>
                        </div>`;
                    });
                } else if (sortBy === 'time' && careerMapData.top_played_maps_time && careerMapData.top_played_maps_time.length > 0) {
                    careerMapData.top_played_maps_time.forEach(entry => {
                        playedHtml += `<div class="compact-list-row map-detail-link" data-map="${escapeHtml(entry.name)}" onclick="openMapDetailFromElement(this)">
                            <span class="list-name">${escapeHtml(entry.name)}</span>
                            <span class="list-highlight">${escapeHtml(entry.time_str)}</span>
                        </div>`;
                    });
                } else {
                    playedHtml = "<div class='compact-empty'>No map data recorded yet.</div>";
                }
                
                document.getElementById('life_most_played').innerHTML = playedHtml;
            }
            // -------------------------------------------

            async function openMapSelectionPage() {
                switchTab('mapselection');
                if (mapSelectionData && mapSelectionData.length > 0) {
                    renderMapSelectionPage();
                    return;
                }
                const grid = document.getElementById('map-selection-grid');
                if (grid) grid.innerHTML = `<div class="muted-loading">${escapeHtml(localeText('map_details.loading_every_map', 'Loading every archived map...'))}</div>`;
                try {
                    const data = await window.pywebview.api.get_map_selection("0");
                    if (data && !data.error) {
                        mapSelectionData = data.maps || [];
                        mapSelectionPage = 1;
                    } else {
                        mapSelectionData = [];
                        if (grid) grid.innerHTML = `<div class="muted-empty">${escapeHtml((data && data.error) || localeText('map_details.no_map_records', 'No map records found.'))}</div>`;
                    }
                } catch(e) {
                    console.error("Map Selection Load Error", e);
                    mapSelectionData = [];
                    if (grid) grid.innerHTML = `<div class="error-empty">${escapeHtml(localeText('map_details.load_records_error', 'Could not load map records.'))}</div>`;
                }
                renderMapSelectionPage();
            }

            function renderMapSelectionPage() {
                const grid = document.getElementById('map-selection-grid');
                const pagination = document.getElementById('map-selection-pagination');
                if (!grid) return;
                if (!mapSelectionData) {
                    grid.innerHTML = `<div class="muted-loading">${escapeHtml(localeText('career.loading_map_records', 'Loading map records...'))}</div>`;
                    return;
                }

                const query = (document.getElementById('map-selection-search')?.value || '').trim().toLowerCase();
                const sortMode = document.getElementById('map-selection-sort')?.value || 'matches';
                let rows = mapSelectionData.filter(row => !query || String(row.name || '').toLowerCase().includes(query));

                rows.sort((a, b) => {
                    if (sortMode === 'round') return b.best_round - a.best_round || a.name.localeCompare(b.name);
                    if (sortMode === 'time') return parseInt(b.time_sec || 0) - parseInt(a.time_sec || 0) || a.name.localeCompare(b.name);
                    if (sortMode === 'recent') return parseInt(b.last_played_ts || 0) - parseInt(a.last_played_ts || 0) || a.name.localeCompare(b.name);
                    if (sortMode === 'name') return a.name.localeCompare(b.name);
                    return b.matches - a.matches || b.best_round - a.best_round || a.name.localeCompare(b.name);
                });

                if (rows.length === 0) {
                    grid.innerHTML = `<div class="muted-empty">${escapeHtml(localeText('map_details.no_map_records', 'No map records found.'))}</div>`;
                    if (pagination) pagination.innerHTML = '';
                    return;
                }

                const totalPages = Math.max(1, Math.ceil(rows.length / mapSelectionPageSize));
                if (mapSelectionPage > totalPages) mapSelectionPage = totalPages;
                if (mapSelectionPage < 1) mapSelectionPage = 1;
                const pageRows = rows.slice((mapSelectionPage - 1) * mapSelectionPageSize, mapSelectionPage * mapSelectionPageSize);

                grid.innerHTML = pageRows.map(row => `
                    <div class="map-selection-card" data-map="${escapeHtml(row.name)}" onclick="openMapDetailFromElement(this)">
                        <div class="map-selection-thumb">
                            ${row.workshop_image ? `<img src="${escapeHtml(row.workshop_image)}" alt="">` : `<div class="map-selection-thumb-fallback">${escapeHtml(localeText('common.map', 'MAP'))}</div>`}
                        </div>
                        <div class="map-selection-name" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</div>
                        <div class="map-selection-stats">
                            <span>${parseInt(row.matches || 0).toLocaleString()} ${escapeHtml(localeText('common.matches', 'matches'))}</span>
                            <span>${escapeHtml(localeText('common.round', 'Round'))} ${parseInt(row.best_round || 0).toLocaleString()}</span>
                            <span>${escapeHtml(row.time_str)}</span>
                            ${row.last_played ? `<span>${escapeHtml(localeText('map_details.last_played_short', 'Last'))}: ${escapeHtml(row.last_played)}</span>` : ''}
                        </div>
                    </div>
                `).join('');

                if (pagination) {
                    pagination.innerHTML = `
                        <button class="nav-btn-small" onclick="changeMapSelectionPage(-1)" ${mapSelectionPage <= 1 ? 'disabled' : ''}>${escapeHtml(localeText('buttons.prev', 'PREV'))}</button>
                        <span>${rows.length.toLocaleString()} ${escapeHtml(localeText('map_details.maps', 'maps'))} // ${escapeHtml(localeText('map_details.page', 'Page'))} ${mapSelectionPage} / ${totalPages}</span>
                        <button class="nav-btn-small" onclick="changeMapSelectionPage(1)" ${mapSelectionPage >= totalPages ? 'disabled' : ''}>${escapeHtml(localeText('buttons.next', 'NEXT'))}</button>
                    `;
                }
            }

            function changeMapSelectionPage(dir) {
                mapSelectionPage += dir;
                renderMapSelectionPage();
            }

            async function refreshMapSelection() {
                mapSelectionData = [];
                const grid = document.getElementById('map-selection-grid');
                if (grid) grid.innerHTML = `<div class="muted-loading">${escapeHtml(localeText('map_details.refreshing_records', 'Refreshing map records...'))}</div>`;
                try {
                    const data = await window.pywebview.api.refresh_map_selection("0");
                    if (data && !data.error) {
                        mapSelectionData = data.maps || [];
                    } else {
                        mapSelectionData = [];
                        if (grid) grid.innerHTML = `<div class="muted-empty">${escapeHtml((data && data.error) || localeText('map_details.no_map_records', 'No map records found.'))}</div>`;
                    }
                } catch(e) {
                    console.error("Map Selection Refresh Error", e);
                    mapSelectionData = [];
                    if (grid) grid.innerHTML = `<div class="error-empty">${escapeHtml(localeText('map_details.refresh_records_error', 'Could not refresh map records.'))}</div>`;
                }
                renderMapSelectionPage();
            }

            function openMapDetailFromElement(el) {
                if (!el) return;
                openMapDetail(el.dataset.map || "");
            }

            function openMapDetailWorkshop() {
                if (currentMapDetail && currentMapDetail.steam_link) {
                    const href = normalizeWorkshopLink(currentMapDetail.steam_link);
                    if (href) window.open(href, '_blank');
                }
            }

            async function openMapDetail(mapName) {
                const cleanName = String(mapName || "").trim();
                if (!cleanName) return;
                const title = document.getElementById('map-detail-title');
                const body = document.getElementById('map-detail-body');
                const workshopBtn = document.getElementById('map-detail-workshop-btn');

                if (currentMapDetail && currentMapDetail.map === cleanName) {
                    mapDetailPage = 1;
                    switchTab('mapdetail');
                    return;
                }

                title.innerText = cleanName;
                workshopBtn.style.display = 'none';
                body.innerHTML = `<div class="card"><div class="muted-loading">${escapeHtml(localeText('map_details.loading_detail', 'Loading {map} map detail...')).replace('{map}', escapeHtml(cleanName))}</div></div>`;
                switchTab('mapdetail');

                mapDetailPage = 1;
                mapDetailTotalMatches = 0;
                mapDetailCurrentMap = cleanName;

                try {
                    const data = await window.pywebview.api.get_map_detail(cleanName, "0", 1, mapDetailPageSize);
                    if (!data || data.error) {
                        body.innerHTML = `<div class="card"><div class="muted-empty">${escapeHtml((data && data.error) || localeText('map_details.load_detail_error', 'Could not load map detail.'))}</div></div>`;
                        return;
                    }
                    currentMapDetail = data;
                    mapDetailTotalMatches = data.total_matches || 0;
                    renderMapDetail(data);
                } catch(e) {
                    console.error("Map Detail Load Error", e);
                    body.innerHTML = `<div class="card"><div class="error-empty">${escapeHtml(localeText('map_details.load_detail_error', 'Could not load map detail.'))}</div></div>`;
                }
            }

            function renderMapDetail(data) {
                const title = document.getElementById('map-detail-title');
                const body = document.getElementById('map-detail-body');
                const workshopBtn = document.getElementById('map-detail-workshop-btn');
                const summary = data.summary || {};
                const totals = data.totals || {};
                const weapons = data.weapons || [];
                const recent = data.recent_matches || [];
                const imageStyle = data.workshop_image
                    ? ` style="--map-detail-image: url(&quot;${escapeHtml(data.workshop_image)}&quot;)"`
                    : "";

                title.innerText = data.map || localeText('map_details.detail_heading', 'Map Detail');
                workshopBtn.style.display = normalizeWorkshopLink(data.steam_link) ? 'inline-block' : 'none';

                const weaponRows = weapons.slice(0, 8).map(w => `
                    <div class="map-detail-weapon-row">
                        <div>
                            <div class="map-detail-weapon-name">${escapeHtml(w.name || 'Unknown')}</div>
                            <div class="map-detail-weapon-meta">${parseInt(w.matches || 0).toLocaleString()} ${escapeHtml(localeText('common.matches', 'matches'))} // ${escapeHtml(localeText('map_details.best_round_lower', 'best round'))} ${parseInt(w.best_round || 0).toLocaleString()} // ${escapeHtml(localeText('common.hs', 'HS'))} ${escapeHtml(w.headshot_pct || 0)}%</div>
                        </div>
                        <div class="map-detail-weapon-stat">${parseInt(w.kills || 0).toLocaleString()} ${escapeHtml(localeText('common.kills', 'kills'))}</div>
                        <div class="map-detail-weapon-stat">${parseInt(w.damage || 0).toLocaleString()} ${escapeHtml(localeText('map_details.damage_short', 'dmg'))}</div>
                    </div>
                `).join('');

                const recentRows = mapDetailRows(recent);

                body.innerHTML = `
                    <div class="card map-detail-hero">
                        <div class="map-detail-media"${imageStyle}>
                            <div class="map-detail-pill">${parseInt(summary.matches || 0).toLocaleString()} ${escapeHtml(localeText('map_details.archived_matches', 'Archived Matches'))}</div>
                            <div class="map-detail-hero-title">${escapeHtml(localeText('common.round', 'Round'))} ${parseInt(summary.highest_round || 0).toLocaleString()} ${escapeHtml(localeText('map_details.pb', 'PB'))}</div>
                            <div class="map-detail-hero-subline">${escapeHtml(data.time_str || '0h 0m')} ${escapeHtml(localeText('map_details.total_lower', 'total'))} // ${parseInt(summary.best_xp || 0).toLocaleString()} ${escapeHtml(localeText('map_details.best_xp_lower', 'best XP'))} // ${parseInt(totals.kills || 0).toLocaleString()} ${escapeHtml(localeText('common.kills', 'kills'))}</div>
                        </div>
                        <div class="map-detail-summary-grid">
                            <div class="map-detail-metric accent"><span>${escapeHtml(localeText('common.matches', 'Matches'))}</span><strong>${parseInt(summary.matches || 0).toLocaleString()}</strong></div>
                            <div class="map-detail-metric gold"><span>${escapeHtml(localeText('map_details.highest_round', 'Highest Round'))}</span><strong>${parseInt(summary.highest_round || 0).toLocaleString()}</strong></div>
                            <div class="map-detail-metric"><span>${escapeHtml(localeText('map_details.average_round', 'Average Round'))}</span><strong>${escapeHtml(summary.average_round || 0)}</strong></div>
                            <div class="map-detail-metric orange"><span>${escapeHtml(localeText('map_details.best_xp', 'Best XP'))}</span><strong>${parseInt(summary.best_xp || 0).toLocaleString()}</strong></div>
                            <div class="map-detail-metric"><span>${escapeHtml(localeText('map_details.average_xp', 'Average XP'))}</span><strong>${parseInt(summary.average_xp || 0).toLocaleString()}</strong></div>
                            <div class="map-detail-metric green"><span>KPM / XPM</span><strong>${escapeHtml(summary.kpm || 0)} / ${parseInt(summary.xpm || 0).toLocaleString()}</strong></div>
                        </div>
                    </div>

                    <div class="stat-grid-3">
                        <div class="card">
                            <div class="card-title">${escapeHtml(localeText('map_details.survival_pace', 'Survival Pace'))}</div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.total_rounds', 'Total Rounds'))}</span><span>${parseInt(totals.rounds || 0).toLocaleString()}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.total_time', 'Total Time'))}</span><span>${escapeHtml(data.time_str || '0h 0m')}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.best_kpm', 'Best KPM'))}</span><span>${escapeHtml(summary.best_kpm || 0)}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.best_xpm', 'Best XPM'))}</span><span>${parseInt(summary.best_xpm || 0).toLocaleString()}</span></div>
                        </div>
                        <div class="card">
                            <div class="card-title">${escapeHtml(localeText('map_details.combat_output', 'Combat Output'))}</div>
                            <div class="detail-row"><span>${escapeHtml(localeText('career.total_kills', 'Total Kills'))}</span><span>${parseInt(totals.kills || 0).toLocaleString()}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('common.headshots', 'Headshots'))}</span><span>${parseInt(totals.headshots || 0).toLocaleString()}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('common.headshot_pct', 'Headshot %'))}</span><span>${escapeHtml(summary.headshot_pct || 0)}%</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('live.downs', 'Downs'))}</span><span>${parseInt(totals.downs || 0).toLocaleString()}</span></div>
                        </div>
                        <div class="card">
                            <div class="card-title">${escapeHtml(localeText('map_details.xp_economy', 'XP Economy'))}</div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.total_xp', 'Total XP'))}</span><span>${parseInt(totals.match_xp || 0).toLocaleString()}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.average_xp', 'Average XP'))}</span><span>${parseInt(summary.average_xp || 0).toLocaleString()}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.average_xpm', 'Average XPM'))}</span><span>${parseInt(summary.xpm || 0).toLocaleString()}</span></div>
                            <div class="detail-row"><span>${escapeHtml(localeText('map_details.average_kpm', 'Average KPM'))}</span><span>${escapeHtml(summary.kpm || 0)}</span></div>
                        </div>
                    </div>

                    <div class="map-detail-grid">
                        <div class="card">
                            <div class="card-title">${escapeHtml(localeText('map_details.best_weapons_on_map', 'Best Weapons On This Map'))}</div>
                            <div class="map-detail-weapon-list">${weaponRows || `<div class="muted-empty">${escapeHtml(localeText('map_details.no_weapon_data', 'No weapon data recorded for this map.'))}</div>`}</div>
                        </div>
                        <div class="card">
                            <div class="card-title">${escapeHtml(localeText('map_details.recent_match_rounds', 'Recent Match Rounds'))}</div>
                            <div class="map-detail-chart-wrap"><canvas id="mapDetailRoundChart"></canvas></div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">${escapeHtml(localeText('map_details.recent_matches', 'Recent Matches'))}</div>
                        <div class="map-detail-table-wrap">
                            <table>
                                <thead><tr><th>${escapeHtml(localeText('common.date', 'Date'))}</th><th>${escapeHtml(localeText('common.round', 'Round'))}</th><th>XP</th><th>${escapeHtml(localeText('common.kills', 'Kills'))}</th><th>KPM</th><th>XPM</th></tr></thead>
                                <tbody id="map-detail-match-rows">${recentRows || `<tr><td colspan="6" class="muted-empty">${escapeHtml(localeText('map_details.no_recent_matches', 'No recent matches found.'))}</td></tr>`}</tbody>
                            </table>
                        </div>
                        <div id="map-detail-load-more-wrap" style="text-align:center;margin-top:12px;${data.has_more ? '' : 'display:none;'}">
                            <button class="nav-btn-small button-tall" onclick="loadMoreMapMatches()" id="map-detail-load-more-btn">${escapeHtml(localeText('buttons.load_more', 'LOAD MORE'))} (${Math.max(0, mapDetailTotalMatches - mapDetailPage * mapDetailPageSize)} ${escapeHtml(localeText('map_details.remaining', 'remaining'))})</button>
                        </div>
                    </div>
                `;

                setTimeout(() => renderMapDetailRoundChart(data.round_history || []), 30);
            }

            function renderMapDetailRoundChart(rows) {
                const canvas = document.getElementById('mapDetailRoundChart');
                if (!canvas || typeof Chart === 'undefined') return;
                const labels = (rows || []).map((row, index) => `#${index + 1}`);
                const values = (rows || []).map(row => parseInt(row.round || 0));
                if (mapDetailRoundChartInstance) {
                    mapDetailRoundChartInstance.destroy();
                    mapDetailRoundChartInstance = null;
                }
                mapDetailRoundChartInstance = new Chart(canvas.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [{
                            label: 'Round',
                            data: values,
                            backgroundColor: '#66fcf1',
                            borderColor: '#45a29e',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            y: { beginAtZero: true, ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.08)' } }
                        }
                    }
                });
            }

            async function loadMoreMapMatches() {
                if (!mapDetailCurrentMap) return;
                mapDetailPage++;
                const btn = document.getElementById('map-detail-load-more-btn');
                if (btn) btn.disabled = true;
                try {
                    const data = await window.pywebview.api.get_map_detail(mapDetailCurrentMap, "0", mapDetailPage, mapDetailPageSize);
                    if (!data || data.error) {
                        mapDetailPage--;
                        if (btn) btn.disabled = false;
                        return;
                    }
                    const tbody = document.getElementById('map-detail-match-rows');
                    if (tbody && data.recent_matches) {
                        data.recent_matches.forEach(row => {
                            const tr = document.createElement('tr');
                            tr.dataset.gameId = row.game_id;
                            tr.onclick = function() { loadHistory(this.dataset.gameId, this); };
                            tr.innerHTML = `
                                <td>${escapeHtml(row.date)}</td>
                                <td>${escapeHtml(localeText('common.round', 'Round'))} ${parseInt(row.round || 0).toLocaleString()}</td>
                                <td>${parseInt(row.match_xp || 0).toLocaleString()}</td>
                                <td>${parseInt(row.kills || 0).toLocaleString()}</td>
                                <td>${escapeHtml(row.kpm || 0)}</td>
                                <td>${parseInt(row.xpm || 0).toLocaleString()}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                    }
                    const wrap = document.getElementById('map-detail-load-more-wrap');
                    const remaining = Math.max(0, mapDetailTotalMatches - mapDetailPage * mapDetailPageSize);
                    if (wrap && remaining > 0) {
                        wrap.style.display = '';
                        const btn2 = document.getElementById('map-detail-load-more-btn');
                        if (btn2) {
                            btn2.disabled = false;
                            btn2.textContent = `${localeText('buttons.load_more', 'LOAD MORE')} (${remaining} ${localeText('map_details.remaining', 'remaining')})`;
                        }
                    } else if (wrap) {
                        wrap.style.display = 'none';
                    }
                } catch(e) {
                    console.error("Load More Map Matches Error", e);
                    mapDetailPage--;
                    if (btn) btn.disabled = false;
                }
            }

            let weaponUsageData = [];
            let weaponCategoryBreakdown = [];
            let weaponCategoryKillsChartInstance = null;
            let weaponCategoryDamageChartInstance = null;
            let selectedWeaponDetailName = "";
            let weaponDetailKillsChartInstance = null;
            let weaponDetailMapChartInstance = null;
            const weaponCategoryColors = {
                assault_rifle: '#5eead4',
                smg: '#60a5fa',
                lmg: '#f59e0b',
                pistol: '#f472b6',
                shotgun: '#fb7185',
                sniper: '#a78bfa',
                launcher: '#f97316',
                special: '#84cc16',
                melee: '#eab308',
                other: '#94a3b8'
            };

            function weaponCategoryLabel(category, fallback) {
                const key = String(category || 'other');
                return localeText(`weapon_categories.${key}`, fallback || key.replaceAll('_', ' ').toUpperCase());
            }

            function mapDetailRows(matches) {
                return (matches || []).slice().reverse().map(row => `
                    <tr data-game-id="${escapeHtml(row.game_id)}" onclick="loadHistory(this.dataset.gameId, this)">
                        <td>${escapeHtml(row.date)}</td>
                        <td>${escapeHtml(localeText('common.round', 'Round'))} ${parseInt(row.round || 0).toLocaleString()}</td>
                        <td>${parseInt(row.match_xp || 0).toLocaleString()}</td>
                        <td>${parseInt(row.kills || 0).toLocaleString()}</td>
                        <td>${escapeHtml(row.kpm || 0)}</td>
                        <td>${parseInt(row.xpm || 0).toLocaleString()}</td>
                    </tr>
                `).join('');
            }

            async function loadWeaponUsage() {
                const tbody = document.getElementById('weapon-usage-list');
                        if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="muted-empty">Loading weapon usage...</td></tr>';
                try {
                    const data = await window.pywebview.api.get_player_weapon_usage();
                    if (!data || data.error) {
                        if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="error-empty">${escapeHtml(data && data.error ? data.error : 'Weapon usage could not be loaded.')}</td></tr>`;
                        return;
                    }
                    weaponUsageData = data.weapons || [];
                    weaponCategoryBreakdown = data.category_breakdown || [];
                    const totals = data.totals || {};
                    document.getElementById('weapon_usage_count').innerText = parseInt(totals.weapon_count || 0).toLocaleString();
                    document.getElementById('weapon_usage_kills').innerText = parseInt(totals.kills || 0).toLocaleString();
                    document.getElementById('weapon_usage_headshots').innerText = parseInt(totals.headshots || 0).toLocaleString();
                    renderWeaponCategoryKillsChart();
                    renderWeaponCategoryDamageChart();
                    renderWeaponUsageTable();
                } catch(e) {
                    console.error("Weapon Usage Load Error", e);
                    if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="error-empty">Weapon usage could not be loaded.</td></tr>';
                }
            }

            function renderWeaponCategoryKillsChart() {
                const canvas = document.getElementById('weaponCategoryKillsChart');
                const legend = document.getElementById('weapon-category-kills-legend');
                if (!canvas || !legend || typeof Chart === 'undefined') return;

                const rows = (weaponCategoryBreakdown || [])
                    .filter(row => parseInt(row.kills || 0) > 0);
                if (rows.length === 0) {
                    legend.innerHTML = '<div class="muted-empty">No weapon category kills recorded yet.</div>';
                    if (weaponCategoryKillsChartInstance) {
                        weaponCategoryKillsChartInstance.destroy();
                        weaponCategoryKillsChartInstance = null;
                    }
                    return;
                }

                const totalKills = rows.reduce((sum, row) => sum + parseInt(row.kills || 0), 0);
                const labels = rows.map(row => weaponCategoryLabel(row.category, row.label || String(row.category || 'Other').replaceAll('_', ' ')));
                const values = rows.map(row => parseInt(row.kills || 0));
                const colors = rows.map(row => weaponCategoryColors[row.category] || weaponCategoryColors.other);

                legend.innerHTML = rows.map((row, index) => {
                    const kills = parseInt(row.kills || 0);
                    const pct = totalKills > 0 ? ((kills / totalKills) * 100).toFixed(1) : '0.0';
                    return `<div class="weapon-category-legend-item">
                        <span class="weapon-category-swatch" style="background:${colors[index]}"></span>
                        <span class="weapon-category-label">${escapeHtml(weaponCategoryLabel(row.category, row.label || row.category || 'Other'))}</span>
                        <span class="weapon-category-value">${kills.toLocaleString()} (${pct}%)</span>
                    </div>`;
                }).join('');

                const ctx = canvas.getContext('2d');
                const chartData = {
                    labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                        borderColor: 'rgba(10, 12, 18, 0.9)',
                        borderWidth: 2,
                        hoverOffset: 6
                    }]
                };

                if (weaponCategoryKillsChartInstance) {
                    weaponCategoryKillsChartInstance.data = chartData;
                    weaponCategoryKillsChartInstance.update('none');
                    return;
                }

                weaponCategoryKillsChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: chartData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '62%',
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const value = parseInt(context.raw || 0);
                                        const pct = totalKills > 0 ? ((value / totalKills) * 100).toFixed(1) : '0.0';
                                        return `${context.label}: ${value.toLocaleString()} kills (${pct}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            function renderWeaponCategoryDamageChart() {
                const canvas = document.getElementById('weaponCategoryDamageChart');
                const legend = document.getElementById('weapon-category-damage-legend');
                if (!canvas || !legend || typeof Chart === 'undefined') return;

                const rows = (weaponCategoryBreakdown || [])
                    .filter(row => parseInt(row.damage || 0) > 0);
                if (rows.length === 0) {
                    legend.innerHTML = '<div class="muted-empty">No weapon damage data recorded yet.</div>';
                    if (weaponCategoryDamageChartInstance) {
                        weaponCategoryDamageChartInstance.destroy();
                        weaponCategoryDamageChartInstance = null;
                    }
                    return;
                }

                const totalDamage = rows.reduce((sum, row) => sum + parseInt(row.damage || 0), 0);
                const labels = rows.map(row => weaponCategoryLabel(row.category, row.label || String(row.category || 'Other').replaceAll('_', ' ')));
                const values = rows.map(row => parseInt(row.damage || 0));
                const colors = rows.map(row => weaponCategoryColors[row.category] || weaponCategoryColors.other);

                legend.innerHTML = rows.map((row, index) => {
                    const damage = parseInt(row.damage || 0);
                    const pct = totalDamage > 0 ? ((damage / totalDamage) * 100).toFixed(1) : '0.0';
                    return `<div class="weapon-category-legend-item">
                        <span class="weapon-category-swatch" style="background:${colors[index]}"></span>
                        <span class="weapon-category-label">${escapeHtml(weaponCategoryLabel(row.category, row.label || row.category || 'Other'))}</span>
                        <span class="weapon-category-value">${damage.toLocaleString()} (${pct}%)</span>
                    </div>`;
                }).join('');

                const ctx = canvas.getContext('2d');
                const chartData = {
                    labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                        borderColor: 'rgba(10, 12, 18, 0.9)',
                        borderWidth: 2,
                    }]
                };

                if (weaponCategoryDamageChartInstance) {
                    weaponCategoryDamageChartInstance.data = chartData;
                    weaponCategoryDamageChartInstance.update('none');
                    return;
                }

                weaponCategoryDamageChartInstance = new Chart(ctx, {
                    type: 'pie',
                    data: chartData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const value = parseInt(context.raw || 0);
                                        const pct = totalDamage > 0 ? ((value / totalDamage) * 100).toFixed(1) : '0.0';
                                        return `${context.label}: ${value.toLocaleString()} damage (${pct}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            function renderWeaponUsageTable() {
                const tbody = document.getElementById('weapon-usage-list');
                if (!tbody) return;
                const search = (document.getElementById('weapon-usage-search')?.value || '').toLowerCase();
                const sortBy = document.getElementById('weapon-usage-sort')?.value || 'kills';
                const rows = weaponUsageData
                    .filter(w => `${String(w.name || '')} ${String(w.category || '')}`.toLowerCase().includes(search))
                    .sort((a, b) => parseFloat(b[sortBy] || 0) - parseFloat(a[sortBy] || 0));

                if (rows.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" class="muted-empty">No weapons found.</td></tr>';
                    return;
                }

                tbody.innerHTML = rows.map(w => {
                    const bestMap = w.best_map ? ` on ${escapeHtml(w.best_map)}` : '';
                    const weaponArg = encodeURIComponent(String(w.name || 'Unknown')).replaceAll("'", "%27");
                    const selectedClass = selectedWeaponDetailName === String(w.name || '') ? ' selected' : '';
                    return `<tr class="weapon-usage-row${selectedClass}" onclick="loadWeaponDetail(decodeURIComponent('${weaponArg}'))" title="Open weapon profile">
                        <td class="weapon-name-cell">${escapeHtml(w.name || 'Unknown')}</td>
                        <td>${escapeHtml(weaponCategoryLabel(w.category, String(w.category || 'other').replaceAll('_', ' ').toUpperCase()))}</td>
                        <td>${parseInt(w.kills || 0).toLocaleString()}</td>
                        <td>${parseInt(w.headshots || 0).toLocaleString()}</td>
                        <td>${parseFloat(w.headshot_pct || 0).toFixed(1)}%</td>
                        <td>${parseInt(w.damage || 0).toLocaleString()}</td>
                        <td>${parseInt(w.matches || 0).toLocaleString()}</td>
                        <td>${parseInt(w.pap_uses || 0).toLocaleString()}</td>
                        <td>Round ${parseInt(w.best_round || 0).toLocaleString()}${bestMap}</td>
                    </tr>`;
                }).join('');
            }

            function closeWeaponDetail() {
                selectedWeaponDetailName = "";
                const card = document.getElementById('weapon-detail-card');
                if (card) card.classList.add('initially-hidden');
                if (weaponDetailKillsChartInstance) {
                    weaponDetailKillsChartInstance.destroy();
                    weaponDetailKillsChartInstance = null;
                }
                if (weaponDetailMapChartInstance) {
                    weaponDetailMapChartInstance.destroy();
                    weaponDetailMapChartInstance = null;
                }
                renderWeaponUsageTable();
            }

            async function loadWeaponDetail(weaponName) {
                selectedWeaponDetailName = String(weaponName || '');
                renderWeaponUsageTable();
                const card = document.getElementById('weapon-detail-card');
                const body = document.getElementById('weapon-detail-body');
                const title = document.getElementById('weapon-detail-title');
                if (!card || !body || !title || !selectedWeaponDetailName) return;

                card.classList.remove('initially-hidden');
                title.innerText = selectedWeaponDetailName;
                body.innerHTML = `<div class="muted-empty">${escapeHtml(localeText('weapon_usage.loading_weapon_profile', 'Loading weapon profile...'))}</div>`;
                card.scrollIntoView({ behavior: 'smooth', block: 'start' });

                try {
                    const detail = await window.pywebview.api.get_weapon_detail(selectedWeaponDetailName, "0");
                    if (!detail || detail.error) {
                        body.innerHTML = `<div class="error-empty">${escapeHtml(detail && detail.error ? detail.error : localeText('weapon_usage.profile_load_error', 'Weapon profile could not be loaded.'))}</div>`;
                        return;
                    }
                    renderWeaponDetail(detail);
                } catch(e) {
                    console.error("Weapon Detail Load Error", e);
                    body.innerHTML = `<div class="error-empty">${escapeHtml(localeText('weapon_usage.profile_load_error', 'Weapon profile could not be loaded.'))}</div>`;
                }
            }

            function renderWeaponDetail(detail) {
                const body = document.getElementById('weapon-detail-body');
                if (!body) return;

                const totals = detail.totals || {};
                const best = detail.best_match || {};
                const weapon = detail.weapon || {};
                const matches = detail.matches || [];
                const maps = detail.map_breakdown || [];
                const aatBreakdown = detail.aat_breakdown || [];
                const categoryKey = String(weapon.category || 'other');
                const category = localeText(`weapon_categories.${categoryKey}`, categoryKey.replaceAll('_', ' ').toUpperCase());
                const bestText = best.map
                    ? `${best.map} // ${localeText('common.round', 'Round')} ${parseInt(best.round || 0).toLocaleString()} // ${parseInt(best.kills || 0).toLocaleString()} ${localeText('common.kills', 'kills')}`
                    : localeText('weapon_usage.no_match_record', 'No match record');
                const topAat = totals.top_aat ? escapeHtml(totals.top_aat) : escapeHtml(localeText('weapon_usage.none_recorded', 'None recorded'));
                const aatMeta = aatBreakdown.length
                    ? `<span>AAT: ${escapeHtml(aatBreakdown.map(row => `${row.name} (${row.count})`).join(', '))}</span>`
                    : '';

                const recentRows = matches.slice(-8).reverse().map(row => `
                    <tr>
                        <td>${escapeHtml(row.date || '')}</td>
                        <td>${escapeHtml(row.map || 'Unknown')}</td>
                        <td>${escapeHtml(localeText('common.round', 'Round'))} ${parseInt(row.round || 0).toLocaleString()}</td>
                        <td>${parseInt(row.kills || 0).toLocaleString()}</td>
                        <td>${parseInt(row.headshots || 0).toLocaleString()}</td>
                        <td>${parseFloat(row.headshot_pct || 0).toFixed(1)}%</td>
                        <td>${parseInt(row.damage || 0).toLocaleString()}</td>
                        <td>${escapeHtml(row.aat || '-')}</td>
                    </tr>
                `).join('');

                body.innerHTML = `
                    <div class="weapon-detail-meta">
                        <span>${escapeHtml(category)}</span>
                        ${weapon.console_name ? `<span>${escapeHtml(weapon.console_name)}</span>` : ''}
                        <span>${parseInt(totals.matches || 0).toLocaleString()} ${escapeHtml(localeText('common.matches', 'matches'))}</span>
                        ${aatMeta}
                    </div>
                    <div class="stat-grid-3 weapon-detail-summary-grid">
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('common.kills', 'Kills'))}</span><strong>${parseInt(totals.kills || 0).toLocaleString()}</strong></div>
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('common.headshots', 'Headshots'))}</span><strong>${parseInt(totals.headshots || 0).toLocaleString()}</strong></div>
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('common.headshot_pct', 'Headshot %'))}</span><strong>${parseFloat(totals.headshot_pct || 0).toFixed(1)}%</strong></div>
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('common.damage', 'Damage'))}</span><strong>${parseInt(totals.damage || 0).toLocaleString()}</strong></div>
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('weapon_usage.pap_uses', 'PaP Uses'))}</span><strong>${parseInt(totals.pap_uses || 0).toLocaleString()}</strong></div>
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('weapon_usage.aat_uses', 'AAT Uses'))}</span><strong>${parseInt(totals.aat_uses || 0).toLocaleString()} // ${topAat}</strong></div>
                        <div class="weapon-detail-stat"><span>${escapeHtml(localeText('weapon_usage.best_match', 'Best Match'))}</span><strong>${escapeHtml(bestText)}</strong></div>
                    </div>
                    <div class="weapon-detail-chart-grid">
                        <div class="weapon-detail-chart-wrap">
                            <div class="weapon-detail-chart-title">${escapeHtml(localeText('weapon_usage.kills_over_time', 'Kills Over Time'))}</div>
                            <canvas id="weaponDetailKillsChart"></canvas>
                        </div>
                        <div class="weapon-detail-chart-wrap">
                            <div class="weapon-detail-chart-title">${escapeHtml(localeText('weapon_usage.kills_by_map', 'Kills By Map'))}</div>
                            <canvas id="weaponDetailMapChart"></canvas>
                        </div>
                    </div>
                    <div class="weapon-detail-table-wrap">
                        <table class="weapon-detail-table">
                            <thead>
                                <tr><th>${escapeHtml(localeText('common.date', 'Date'))}</th><th>${escapeHtml(localeText('common.map', 'Map'))}</th><th>${escapeHtml(localeText('common.round', 'Round'))}</th><th>${escapeHtml(localeText('common.kills', 'Kills'))}</th><th>${escapeHtml(localeText('common.headshots', 'Headshots'))}</th><th>${escapeHtml(localeText('common.hs_pct_short', 'HS%'))}</th><th>${escapeHtml(localeText('common.damage', 'Damage'))}</th><th>AAT</th></tr>
                            </thead>
                            <tbody>${recentRows || `<tr><td colspan="8" class="muted-empty">${escapeHtml(localeText('weapon_usage.no_archived_matches', 'No archived matches found for this weapon.'))}</td></tr>`}</tbody>
                        </table>
                    </div>
                `;

                setTimeout(() => {
                    renderWeaponDetailKillsChart(matches);
                    renderWeaponDetailMapChart(maps);
                }, 30);
            }

            function renderWeaponDetailKillsChart(matches) {
                const canvas = document.getElementById('weaponDetailKillsChart');
                if (!canvas || typeof Chart === 'undefined') return;
                const labels = (matches || []).map((row, index) => row.map ? `${index + 1}. ${row.map}` : `${index + 1}`);
                const values = (matches || []).map(row => parseInt(row.kills || 0));
                if (weaponDetailKillsChartInstance) {
                    weaponDetailKillsChartInstance.destroy();
                    weaponDetailKillsChartInstance = null;
                }
                weaponDetailKillsChartInstance = new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [{
                            label: 'Kills',
                            data: values,
                            borderColor: '#66fcf1',
                            backgroundColor: 'rgba(102, 252, 241, 0.12)',
                            borderWidth: 2,
                            pointRadius: 3,
                            tension: 0.25,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: '#888', maxRotation: 0, autoSkip: true }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            y: { beginAtZero: true, ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.08)' } }
                        }
                    }
                });
            }

            function renderWeaponDetailMapChart(maps) {
                const canvas = document.getElementById('weaponDetailMapChart');
                if (!canvas || typeof Chart === 'undefined') return;
                const rows = (maps || []).slice(0, 8);
                const labels = rows.map(row => row.map || 'Unknown');
                const values = rows.map(row => parseInt(row.kills || 0));
                if (weaponDetailMapChartInstance) {
                    weaponDetailMapChartInstance.destroy();
                    weaponDetailMapChartInstance = null;
                }
                weaponDetailMapChartInstance = new Chart(canvas.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [{
                            label: 'Kills',
                            data: values,
                            backgroundColor: '#f59e0b',
                            borderColor: '#ffd700',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: '#888', maxRotation: 0, autoSkip: true }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            y: { beginAtZero: true, ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.08)' } }
                        }
                    }
                });
            }
            
            async function loadTopXPMaps() {
    try {
        const topMaps = await window.pywebview.api.get_top_10_xp_maps("0");
        const container = document.getElementById('top_xp_maps_list');
        
        if (!topMaps || topMaps.length === 0) {
            container.innerHTML = "<div class='list-empty'>No match XP data recorded yet.</div>";
            return;
        }

        let html = '<div class="stack-column">';
        topMaps.forEach(entry => {
            html += `<div class="xp-map-row map-detail-link" data-map="${escapeHtml(entry.map)}" onclick="openMapDetailFromElement(this)">
                <span class="xp-map-name">${escapeHtml(entry.map)}</span>
                <span class="xp-map-value">${parseInt(entry.xp || 0).toLocaleString()} XP</span>
            </div>`;
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch(e) { 
        console.error("Top XP Load Error", e); 
    }
}
            
            async function init() {
                updateSidebar();
                switchTab('live');
                
                await window.pywebview.api.force_sync_challenges();
                
                const savedTheme = await window.pywebview.api.get_active_theme();
                currentThemeName = savedTheme || 'default';
                if (savedTheme && savedTheme !== 'default') {
                    const css = await window.pywebview.api.get_theme_content(savedTheme);
                    document.getElementById('theme-injector').innerHTML = css;
                }
                applyGraphTheme();
                applySettingsCopy(currentThemeName);
                const savedLanguage = await window.pywebview.api.get_active_language();
                await loadLocaleStrings(savedLanguage || 'en');
                await loadDiscordPresenceSettings();
                await loadT7DiscordPresenceSetting();
                maybeShowGlobalStatsPrompt();
                checkForUpdates(false);
                 
                setInterval(async () => {
                    if (isLive) {
                        try {
                            const data = await window.pywebview.api.get_live_stats();
                            if (isLive) updateData(data); 
                        } catch(e) {}
                    }
                    updateSidebar();
                    
                    const chalTab = document.getElementById('tab-challenges');
                    if (chalTab && chalTab.classList.contains('active')) {
                        loadChallenges();
                    }
                    const bestTab = document.getElementById('tab-bestmatches');
                    if (bestTab && bestTab.classList.contains('active')) {
                        loadBestMatches();
                    }
                }, 3000);
            }
            
            // --- NEW: MULTI-PLAYER TAB LOGIC ---
            function switchPlayerTab(index) {
                currentPlayerIndex = index;
                document.querySelectorAll('.player-tab').forEach((el, i) => {
                    el.classList.toggle('active', i === index);
                });
                if (cachedPlayers && cachedPlayers.length > index) {
                    updatePlayerUI(cachedPlayers[index]);
                }
            }

            function buildPlayerTabs(players) {
                const container = document.getElementById('player-tabs-container');
                if (!container) return;
                if (players.length !== container.children.length) {
                    container.innerHTML = "";
                    players.forEach((p, i) => {
                        const btn = document.createElement('button');
                        btn.className = `player-tab ${i === currentPlayerIndex ? 'active' : ''}`;
                        const name = p.name ? escapeHtml(p.name) : '';
                        btn.innerHTML = `PLAYER ${i + 1}${name ? `<br><span class="player-tab-name">${name}</span>` : ''}`;
                        btn.onclick = () => switchPlayerTab(i);
                        container.appendChild(btn);
                    });
                }
                
                const content = document.getElementById('player-specific-content');
                if (content) {
                    if (players.length > 0) {
                        content.style.display = 'block';
                        if (currentPlayerIndex >= players.length) currentPlayerIndex = 0;
                    } else {
                        content.style.display = 'none';
                    }
                }
            }

            function updateData(d) {
                if(!d || !d.game) return;
                currentGameId = d.game.id || "";

                const currentRound = parseInt(d.game.round);
                if (currentRound > lastRound && lastRound !== 0) {
                    if (currentRound % 5 === 0) {
                        triggerMilestoneAnim(currentRound);
                    }
                }
                lastRound = currentRound;

                const setTxt = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };
                const setHtml = (id, val) => { const el = document.getElementById(id); if(el) el.innerHTML = val || ''; };
                
                setTxt('d_status_bar', d.game.status);
                const statusBar = document.getElementById('d_status_bar');
                if(statusBar) statusBar.style.borderLeftColor = d.game.color;
                setTxt('d_map', d.game.map);
                setTxt('d_round', d.game.round);
                setTxt('d_time', d.game.time);
                setTxt('d_avg_time', d.game.avg_time + "s");
                setTxt('d_zpm', d.game.zpm);
                setTxt('d_mode', d.game.mode);
                setTxt('d_version', d.game.version);
                setHtml('d_nerf', d.game.nerf);

                try {
                    var workshopContainer = document.getElementById('live-workshop-container');
                    var workshopImg = document.getElementById('live-workshop-img');
                    if (workshopContainer && workshopImg) {
                        if (!workshopImagesEnabled) {
                            workshopImg.removeAttribute('src');
                            workshopImg.style.display = 'none';
                            workshopContainer.style.display = 'none';
                        } else {
                            var sl = d.game.steam_link;
                            if (sl && sl !== '0' && sl !== '') {
                            if (window._workshopCache && window._workshopCache[sl]) {
                                workshopImg.src = window._workshopCache[sl];
                                workshopImg.style.display = 'block';
                                workshopContainer.style.display = 'block';
                            } else {
                                (function(link) {
                                    window.pywebview.api.get_workshop_image(link).then(function(imgSrc) {
                                        if (imgSrc && workshopImg) {
                                            workshopImg.src = imgSrc;
                                            workshopImg.style.display = 'block';
                                            workshopContainer.style.display = 'block';
                                            if (!window._workshopCache) window._workshopCache = {};
                                            window._workshopCache[link] = imgSrc;
                                        }
                                    }).catch(function() {});
                                })(sl);
                            }
                            } else {
                                workshopImg.style.display = 'none';
                                workshopContainer.style.display = 'none';
                            }
                        }
                    }
                } catch(e) {}

                try {
                    cachedPlayers = d.players || [];
                    buildPlayerTabs(cachedPlayers);
                    
                    if (cachedPlayers.length > 0) {
                        updatePlayerUI(cachedPlayers[currentPlayerIndex]);
                    }
                } catch(e) { console.error("Error updating player data:", e); }
            }

            function updatePlayerUI(p) {
                if (!p) return;
                const setTxt = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };
                const setHtml = (id, val) => { const el = document.getElementById(id); if(el) el.innerHTML = val || ''; };
                
                const prestBox = document.getElementById('d_prest_box');
                const prestImg = document.getElementById('d_prest_icon');
                if (prestBox && (p.prest_icon || p.leg_icon || p.abso_icon || p.ult_icon)) {
                    prestBox.style.display = 'block';
                    
                    const oldIcons = prestBox.querySelectorAll('.custom-tier-icon');
                    oldIcons.forEach(icon => icon.remove());

                    if (p.prest_icon && prestImg) {
                        prestImg.src = p.prest_icon;
                        prestImg.style.display = 'inline-block';
                    } else if (prestImg) {
                        prestImg.style.display = 'none';
                    }

                    const addIcon = (src) => {
                        if (!src || !prestImg) return;
                        const img = document.createElement('img');
                        img.src = src;
                        img.className = 'custom-tier-icon';
                        
                        let targetHeight = prestImg.clientHeight;
                        if (targetHeight === 0) {
                            img.style.height = '28px'; 
                        } else {
                            img.style.height = targetHeight + 'px';
                        }

                        img.style.width = 'auto';
                        img.style.objectFit = 'contain';
                        img.style.marginRight = '6px';
                        
                        prestBox.insertBefore(img, prestImg);
                    };

                    addIcon(p.leg_icon);
                    addIcon(p.abso_icon);
                    addIcon(p.ult_icon);

                } else if (prestBox) {
                    prestBox.style.display = 'none';
                }

                const lvlBox = document.getElementById('d_lvl_box');
                const lvlImg = document.getElementById('d_lvl_icon');
                if (lvlBox && lvlImg) {
                    if (p.lvl_icon) {
                        lvlImg.src = p.lvl_icon;
                        lvlBox.style.display = 'block';
                    } else {
                        lvlBox.style.display = 'none';
                    }
                }

                setTxt('d_rmain', p.r_main);
                setTxt('d_title', p.title);
                setTxt('d_rsub', p.r_sub);
                setTxt('d_gums', p.gums);
                setTxt('d_xp', p.xp);
                setTxt('d_mult', p.mult);
                setTxt('d_kills', p.k);
                setTxt('d_score', p.pts);
                setTxt('d_acc', p.acc);
                setTxt('d_melee', p.melee);
                setTxt('d_equip', p.equip);
                setTxt('d_downs', p.downs);
                setTxt('d_leth', p.leth);
                setTxt('d_tact', p.tact);
                setHtml('d_perks', p.perks);
                setHtml('d_weaps', p.weaps);

               // --- NEW GRAPH DATA BINDING ---
                currentGraphLabels = p.graph_labels || [];
                currentGraphData = p.graph_data || [];
                currentRoundXpLabels = p.round_xp_labels || [];
                currentRoundXpData = p.round_xp_data || [];
                currentZpmLabels = p.zpm_labels || [];
                currentZpmData = p.zpm_data || [];
                
                const graphContainer = document.getElementById('xpm-graph-container');
                const roundXpContainer = document.getElementById('roundxp-graph-container');
                const zpmContainer = document.getElementById('zpm-graph-container');
                const liveTab = document.getElementById('tab-live');
                
                // ONLY render if the graph is open AND the live tab is actually visible!
                if (graphContainer.style.display === 'block' && liveTab.classList.contains('active')) {
                    renderXpmChart();
                }
                if (roundXpContainer.style.display === 'block' && liveTab.classList.contains('active')) {
                    renderRoundXpChart();
                }
                if (zpmContainer && zpmContainer.style.display === 'block' && liveTab.classList.contains('active')) {
                    renderZpmChart();
                }
                // ------------------------------
             }   
               function triggerMilestoneAnim(round) {
                const overlay = document.createElement('div');
                overlay.className = 'milestone-overlay';
                overlay.innerHTML = `<div class="milestone-text">ROUND ${round} REACHED</div>`;
                document.body.appendChild(overlay);
                setTimeout(() => {
                    overlay.remove();
                }, 3000);
            }
            
            async function updateSidebar() {
                try {
                    // Fetch the specific page from Python
                    const response = await window.pywebview.api.get_history_list(currentHistoryPage, readHistoryFilters());
                    const newHistory = response.items;
                    totalHistoryPages = response.total_pages;
                    currentHistoryPage = response.current_page;
                    
                    // Update the page text (e.g. "1 / 4")
                    const pageInfo = document.getElementById('hist-page-info');
                    if (pageInfo) pageInfo.innerText = `${currentHistoryPage} / ${totalHistoryPages}`;
                    const summaryEl = document.getElementById('history-filter-summary');
                    if (summaryEl) {
                        const filtered = response.filtered_items ?? newHistory.length;
                        const total = response.total_items ?? filtered;
                        summaryEl.innerText = filtered === total ? `${total} archived matches` : `${filtered} of ${total} matches`;
                    }

                    const mapSelect = document.getElementById('history-map-filter');
                    if (mapSelect && Array.isArray(response.maps)) {
                        const currentMap = mapSelect.value;
                        const optionsSignature = response.maps.join('|');
                        if (mapSelect.dataset.optionsSignature !== optionsSignature) {
                            mapSelect.innerHTML = `<option value="">All maps</option>` + response.maps.map(map => {
                                const safeMap = escapeHtml(map);
                                return `<option value="${safeMap}">${safeMap}</option>`;
                            }).join('');
                            mapSelect.dataset.optionsSignature = optionsSignature;
                            mapSelect.value = currentMap;
                        }
                    }

                    const xpSelect = document.getElementById('history-xp-range');
                    if (xpSelect && Array.isArray(response.xp_ranges)) {
                        const currentXpRange = xpSelect.value;
                        const optionsSignature = response.xp_ranges.map(range => `${range.value}:${range.label}`).join('|');
                        if (xpSelect.dataset.optionsSignature !== optionsSignature) {
                            xpSelect.innerHTML = `<option value="">All XP earned</option>` + response.xp_ranges.map(range => {
                                const safeValue = escapeHtml(range.value);
                                const safeLabel = escapeHtml(range.label);
                                return `<option value="${safeValue}">${safeLabel}</option>`;
                            }).join('');
                            xpSelect.dataset.optionsSignature = optionsSignature;
                            xpSelect.value = currentXpRange;
                        }
                    }

                    const listEl = document.getElementById('history-list');
                    const listSignature = newHistory.map(item => `${item.id}:${item.map}:${item.date}:${item.round || 0}:${item.match_xp || 0}`).join('|');
                    
                    if (listEl.dataset.signature !== listSignature || (newHistory.length === 0 && !listEl.querySelector('.history-empty'))) {
                        
                        listEl.innerHTML = "";
                        listEl.dataset.signature = listSignature;

                        newHistory.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'sb-item';
                            const roundText = Number(item.round || 0) > 0 ? `R${item.round} // ` : "";
                            const xpText = Number(item.match_xp || 0) > 0 ? `${Number(item.match_xp).toLocaleString()} XP` : "XP not recorded";
                            div.innerHTML = `
                                <div class="sb-map">${escapeHtml(item.map)}</div>
                                <div class="sb-date">${roundText}${escapeHtml(item.date)}</div>
                                <div class="sb-xp">${escapeHtml(xpText)}</div>
                                <div class="sb-id" title="${escapeHtml(item.id)}">${escapeHtml(item.id)}</div>
                            `;
                            div.onclick = () => loadHistory(item.id, div);
                            listEl.appendChild(div);
                        });
                        if (newHistory.length === 0) {
                            listEl.innerHTML = `<div class="history-empty">No matches found.</div>`;
                        }
                    }
                } catch(e) { console.error("Error updating sidebar:", e); }
            }
            
            async function loadHistory(id, el) {
                switchTab('live'); 
                isLive = false;
                document.querySelectorAll('.sb-item').forEach(i => i.classList.remove('active'));
                if (el) el.classList.add('active');
                const data = await window.pywebview.api.get_history_report(id);
                if (!data || data.status === 'ERROR' || !data.game) {
                    document.getElementById('d_status_bar').innerText = "ARCHIVED MATCH NOT FOUND";
                    document.getElementById('d_status_bar').style.borderLeftColor = "#ff4444";
                    return;
                }
                if (!isLive) {
                    updateData(data);
                    document.getElementById('d_status_bar').innerText = "ARCHIVED MATCH RECORD";
                    document.getElementById('d_status_bar').style.borderLeftColor = "#999";
                }
            }

            function askParentToBrowse() {
                window.pywebview.api.browse_user_json().then(path => {
                    if(path) {
                        updateStatus("DECRYPTING...", "#ff9d00");
                        document.getElementById('current-user-path').value = path;
                        window.pywebview.api.get_camo_content(path).then(renderCamoData);
                    }
                });
            }
            
            function askParentToUpdate(w_id, c_idx) {
                const userPath = document.getElementById('current-user-path').value;
                if(!userPath) { alert("No user file loaded."); return; }
                updateLocalUI(w_id, c_idx);
                window.pywebview.api.update_camo_progress(userPath, w_id, c_idx);
            }
            
            function toggleStar(event, w_id) {
                event.stopPropagation(); 
                let targetWeapon = null;
                for (let mapKey in GLOBAL_MAPS) {
                    let weaponList = GLOBAL_MAPS[mapKey].weapons;
                    targetWeapon = weaponList.find(w => w.id == w_id);
                    if (targetWeapon) break;
                }
                
                if (targetWeapon) {
                    if (!targetWeapon.is_starred && currentStarredWeapons.length >= 3) {
                        alert("Max 3 priority weapons."); return; 
                    }
                    targetWeapon.is_starred = !targetWeapon.is_starred;
                    rebuildStarredList();
                    renderCurrentMap();
                    window.pywebview.api.toggle_star(w_id).then(res => {
                        if (!res.success) {
                            targetWeapon.is_starred = !targetWeapon.is_starred;
                            rebuildStarredList();
                            renderCurrentMap();
                            alert(res.msg);
                        }
                    });
                }
            }
            
            function rebuildStarredList() {
                currentStarredWeapons = [];
                for(let m in GLOBAL_MAPS) {
                    GLOBAL_MAPS[m].weapons.forEach(w => {
                        if(w.is_starred) currentStarredWeapons.push(w);
                    });
                }
            }

            function updateLocalUI(w_id, c_idx) {
                // --- NEW FIX: Update the internal memory so searching doesn't reset it ---
                for (let mapKey in GLOBAL_MAPS) {
                    let weapon = GLOBAL_MAPS[mapKey].weapons.find(w => w.id == w_id);
                    if (weapon) {
                        weapon.camo_val = c_idx;
                        weapon.camo_name = GLOBAL_NAMES[c_idx] || "Unknown Camo";
                        break;
                    }
                }
                // -------------------------------------------------------------------------

                const items = document.querySelectorAll(`.camo-option[data-wid='${w_id}']`);
                items.forEach(i => i.classList.remove('active'));
                const selected = document.querySelectorAll(`.camo-option[data-wid='${w_id}'][data-idx='${c_idx}']`);
                selected.forEach(s => s.classList.add('active'));
                
                const txt = document.getElementById(`txt-${w_id}`);
                const txtStar = document.getElementById(`txt-${w_id}-star`);
                
                if(GLOBAL_NAMES[c_idx]) {
                    if(txt) txt.innerText = GLOBAL_NAMES[c_idx];
                    if(txtStar) txtStar.innerText = GLOBAL_NAMES[c_idx];
                }
                const imgNormal = document.getElementById(`img-div-${w_id}`);
                const imgStar = document.getElementById(`img-div-${w_id}-star`);
                if (imgNormal) imgNormal.className = `camo-display-img asset-${c_idx}`;
                if (imgStar) imgStar.className = `camo-display-img asset-${c_idx}`;

                const barNormal = document.getElementById(`bar-${w_id}`);
                const barStar = document.getElementById(`bar-${w_id}-star`);
                let pct = (c_idx / 20) * 100;
                if (barNormal) barNormal.style.width = pct + "%";
                if (barStar) barStar.style.width = pct + "%";
            }
            
            function updateStatus(msg, color) {
                const el = document.getElementById('status-txt');
                el.innerText = msg;
                if(color) el.style.color = color;
            }
            
            function initControls(maps) {
                GLOBAL_MAPS = maps;
                MAP_KEYS = Object.keys(maps).sort();
                const sel = document.getElementById('map-select');
                sel.innerHTML = "";
                MAP_KEYS.forEach((key, idx) => {
                    const opt = document.createElement('option');
                    opt.value = idx;
                    opt.innerText = key;
                    sel.appendChild(opt);
                });
                document.getElementById('controls-area').style.display = "flex";
                currentMapIndex = 0;
                renderCurrentMap();
            }
            
            function changeMap(dir) {
                currentMapIndex += dir;
                if(currentMapIndex < 0) currentMapIndex = MAP_KEYS.length - 1;
                if(currentMapIndex >= MAP_KEYS.length) currentMapIndex = 0;
                document.getElementById('map-select').value = currentMapIndex;
                renderCurrentMap();
            }
            
            function onMapSelect() {
                const sel = document.getElementById('map-select');
                currentMapIndex = parseInt(sel.value);
                renderCurrentMap();
            }
            
            function onSearch() { renderCurrentMap(); }
            
            function createWeaponCard(w, isPriority=false) {
                let trayHtml = `<div class="camo-tray">`;
                for(let i=0; i < GLOBAL_NAMES.length; i++) {
                    let isActive = (i === w.camo_val) ? 'active' : '';
                    trayHtml += `
                        <div class="camo-option ${isActive}" 
                             data-wid="${w.id}" data-idx="${i}" title="${GLOBAL_NAMES[i]}"
                             onclick="askParentToUpdate('${w.id}', ${i})">
                             <div class="camo-img-ref asset-${i}"></div>
                        </div>
                    `;
                }
                trayHtml += `</div>`;
                
                let wPct = (w.camo_val / 20) * 100;
                let starClass = w.is_starred ? "active" : "";
                let domIdSuffix = isPriority ? "-star" : "";
                
                return `
                    <div class="camo-card">
                        <div class="star-btn ${starClass}" onclick="toggleStar(event, '${w.id}')">★</div>
                        <div class="card-head">
                            <div><div class="w-name">${w.name}</div><div class="w-type">${w.type}</div></div>
                            <div class="game-tag">${w.gametype}</div>
                        </div>
                        <div class="w-packed">${w.packed}</div>
                        <div class="progress-bar"><div id="bar-${w.id}${domIdSuffix}" class="fill" style="width:${wPct}%"></div></div>
                        <div class="camo-display">
                            <div class="camo-img-box">
                                <div id="img-div-${w.id}${domIdSuffix}" class="camo-display-img asset-${w.camo_val}"></div>
                            </div>
                            <div>
                                <div class="camo-label">CURRENT CAMO</div>
                                <div class="camo-text" id="txt-${w.id}${domIdSuffix}">${w.camo_name}</div>
                            </div>
                        </div>
                        ${trayHtml}
                    </div>
                `;
            }

            function renderCurrentMap() {
                try {
                    if(MAP_KEYS.length === 0) return;
                    const mapName = MAP_KEYS[currentMapIndex];
                    const mapData = GLOBAL_MAPS[mapName];
                    const searchText = document.getElementById('search-input').value.toLowerCase();
                    const container = document.getElementById('content-area');
                    container.innerHTML = "";
                    
                    if (currentStarredWeapons.length > 0) {
                        const prioSection = document.createElement('div');
                        prioSection.className = "priority-section";
                        let prioHtml = `<div class="grid">`;
                        currentStarredWeapons.forEach(w => {
                            prioHtml += createWeaponCard(w, true);
                        });
                        prioHtml += `</div>`;
                        prioSection.innerHTML = prioHtml;
                        container.appendChild(prioSection);
                    }

                    const section = document.createElement('div');
                    const filteredWeapons = mapData.weapons.filter(w => {
                        if (w.is_starred) return false; 
                        const n = String(w.name || "").toLowerCase();
                        const t = String(w.type || "").toLowerCase();
                        return n.includes(searchText) || t.includes(searchText);
                    });
                    
                    let pct = 0;
                    if(mapData.total_levels > 0) pct = Math.round((mapData.current_levels / mapData.total_levels) * 100);
                    
                    let html = `
                        <div class="map-title map-title-row">
                            <span class="map-title-name">${mapName}</span>
                            <span class="map-title-progress">${pct}% COMPLETED</span>
                        </div>
                        <div class="progress-bar map-progress-bar"><div class="fill ${pct==100?'max':''}" style="width:${pct}%"></div></div>
                        <div class="grid">
                    `;
                    
                    if(filteredWeapons.length === 0) {
                        html += `<div class="empty-grid-message">No weapons found matching search.</div></div>`;
                    } else {
                        filteredWeapons.forEach(w => {
                            html += createWeaponCard(w, false);
                        });
                        html += `</div>`;
                    }
                    section.innerHTML = html;
                    container.appendChild(section);
                    
                } catch (e) {
                    console.error(e);
                    document.getElementById('content-area').innerHTML = "<div class='render-error'>RENDER ERROR: " + e.message + "</div>";
                }
            }
            
            function renderCamoData(data) {
                if(data.error) { alert(data.error); updateStatus("ERROR", "red"); return; }
                GLOBAL_NAMES = data.camo_names;
                
                currentStarredWeapons = [];
                for(let m in data.maps) {
                    data.maps[m].weapons.forEach(w => {
                        if(w.is_starred) currentStarredWeapons.push(w);
                    });
                }

                let cssStr = "";
                if (data.camo_icons) {
                    data.camo_icons.forEach((src, idx) => {
                        if(src) cssStr += `.asset-${idx} { background-image: url('${src}'); } `;
                    });
                }
                document.getElementById('dynamic-camo-styles').innerHTML = cssStr;
                document.getElementById('user-display').innerText = data.username.toUpperCase();
                updateStatus("READY", "#66fcf1");
                if(Object.keys(data.maps).length === 0) return;
                initControls(data.maps);
            }
            
            function reconfigure() {
                if(confirm("Reconfigure paths?")) {
                    window.pywebview.api.reset_config().then(() => window.pywebview.api.launch_setup());
                }
            }
            
            window.addEventListener('pywebviewready', init);
        </script>
    </body>
    </html>
    """

