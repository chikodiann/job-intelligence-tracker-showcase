"""Frontend HTML/CSS/JavaScript single-page UI for Job Intelligence Dashboard & Application Tracker."""

from typing import Any, Optional

def get_dashboard_html(candidate_profile: Optional[Any] = None) -> str:
    candidate_name = candidate_profile.name if (candidate_profile and getattr(candidate_profile, "name", None)) else "Candidate"
    if candidate_profile and getattr(candidate_profile, "primary_skills", None):
        skills_sample = ", ".join(sorted(list(candidate_profile.primary_skills))[:4])
    else:
        skills_sample = "target technical skills"
    section_3_desc = f"Strongest engineering alignment with {candidate_name}'s {skills_sample} stack."

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Job Intelligence Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-color: #0b0f19;
      --card-bg: #151c2c;
      --card-hover: #1e293b;
      --border-color: #243049;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-green: #10b981;
      --accent-green-bg: rgba(16, 185, 129, 0.15);
      --accent-purple: #8b5cf6;
      --accent-purple-bg: rgba(139, 92, 246, 0.15);
      --accent-cyan: #06b6d4;
      --accent-cyan-bg: rgba(6, 182, 212, 0.15);
      --accent-amber: #f59e0b;
      --accent-amber-bg: rgba(245, 158, 11, 0.15);
      --accent-red: #ef4444;
      --accent-red-bg: rgba(239, 68, 68, 0.15);
      --accent-blue: #3b82f6;
      --font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-color);
      color: var(--text-main);
      font-family: var(--font-family);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Header */
    header {
      background: rgba(21, 28, 44, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 1rem 2rem;
    }

    .header-container {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .brand-title {
      font-size: 1.35rem;
      font-weight: 700;
      background: linear-gradient(135deg, #60a5fa, #a78bfa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .live-clock {
      font-size: 0.875rem;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.05);
      padding: 0.35rem 0.85rem;
      border-radius: 20px;
      border: 1px solid var(--border-color);
    }

    /* Main Container */
    main {
      max-width: 1400px;
      margin: 2rem auto;
      padding: 0 2rem;
      flex: 1;
      width: 100%;
    }

    /* Navigation Bar */
    nav {
      display: flex;
      gap: 1rem;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 2rem;
    }

    .nav-tab {
      padding: 0.75rem 1.25rem;
      font-size: 0.95rem;
      font-weight: 500;
      color: var(--text-muted);
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s ease;
      background: none;
      border-top: 0;
      border-left: 0;
      border-right: 0;
    }

    .nav-tab:hover {
      color: var(--text-main);
    }

    .nav-tab.active {
      color: var(--accent-cyan);
      border-bottom-color: var(--accent-cyan);
    }

    .nav-tab .badge {
      background: var(--border-color);
      color: var(--text-main);
      padding: 0.1rem 0.5rem;
      border-radius: 10px;
      font-size: 0.75rem;
      margin-left: 0.35rem;
    }

    /* Summary Cards Grid */
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }

    .summary-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .summary-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }

    .summary-label {
      font-size: 0.825rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
    }

    .summary-value {
      font-size: 2rem;
      font-weight: 700;
      color: var(--text-main);
    }

    .summary-subtext {
      font-size: 0.775rem;
      color: var(--text-muted);
    }

    /* Section Styles */
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      margin-top: 1.5rem;
    }

    .section-title {
      font-size: 1.25rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }

    .section-desc {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 1rem;
    }

    /* Jobs & Applications Grid */
    .jobs-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }

    @media (max-width: 768px) {
      .jobs-grid {
        grid-template-columns: 1fr;
      }
    }

    /* Job Card */
    .job-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.35rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1rem;
      transition: all 0.2s ease;
      position: relative;
    }

    .job-card.dismissed {
      opacity: 0.5;
      background: rgba(15, 23, 42, 0.6);
      border-color: rgba(239, 68, 68, 0.2);
    }

    .job-card:hover {
      border-color: var(--accent-blue);
      box-shadow: 0 6px 20px rgba(59, 130, 246, 0.1);
    }

    .job-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.5rem;
    }

    .job-title {
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--text-main);
      line-height: 1.3;
    }

    .company-name {
      font-size: 0.875rem;
      color: #60a5fa;
      font-weight: 500;
      margin-top: 0.25rem;
    }

    .source-tag {
      font-size: 0.725rem;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }

    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      align-items: center;
      font-size: 0.775rem;
    }

    .pill {
      padding: 0.2rem 0.55rem;
      border-radius: 20px;
      font-weight: 500;
      font-size: 0.725rem;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }

    .pill-eligible { background: var(--accent-green-bg); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }
    .pill-unknown { background: var(--accent-amber-bg); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }
    .pill-ineligible { background: var(--accent-red-bg); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); }
    .pill-priority { background: var(--accent-purple-bg); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); font-weight: 600; }
    .pill-tech { background: var(--accent-cyan-bg); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.3); font-weight: 600; }
    .pill-fresh { background: rgba(255, 255, 255, 0.06); color: var(--text-muted); }
    .pill-reviewing { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); font-weight: 600; }
    .pill-dismissed { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
    
    /* Application Status Badges */
    .pill-app-APPLIED { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); font-weight: 600; }
    .pill-app-ASSESSMENT { background: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.4); font-weight: 600; }
    .pill-app-INTERVIEW { background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.5); font-weight: 600; }
    .pill-app-OFFER { background: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.5); font-weight: 700; }
    .pill-app-ACCEPTED { background: rgba(16, 185, 129, 0.35); color: #10b981; border: 1px solid #10b981; font-weight: 700; }
    .pill-app-REJECTED { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
    .pill-app-WITHDRAWN { background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.4); }

    .why-box {
      background: rgba(0, 0, 0, 0.25);
      border-left: 3px solid var(--accent-cyan);
      padding: 0.65rem 0.85rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.8rem;
      color: #cbd5e1;
    }

    .gap-box {
      background: rgba(239, 68, 68, 0.05);
      border-left: 3px solid var(--accent-red);
      padding: 0.5rem 0.85rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.775rem;
      color: #fca5a5;
    }

    .action-box {
      background: rgba(245, 158, 11, 0.1);
      border-left: 3px solid var(--accent-amber);
      padding: 0.5rem 0.85rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.8rem;
      color: #fef08a;
    }

    .card-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.5rem;
      flex-wrap: wrap;
    }

    .btn {
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.35rem;
      transition: all 0.2s ease;
      border: none;
    }

    .btn-primary { background: linear-gradient(135deg, #2563eb, #3b82f6); color: #ffffff; }
    .btn-primary:hover { background: linear-gradient(135deg, #1d4ed8, #2563eb); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35); }
    .btn-secondary { background: rgba(255, 255, 255, 0.07); color: var(--text-main); border: 1px solid var(--border-color); }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.12); }
    .btn-applied { background: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.4); }
    .btn-applied:hover { background: rgba(16, 185, 129, 0.3); }
    .btn-dismiss { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }
    .btn-dismiss:hover { background: rgba(239, 68, 68, 0.25); }
    .btn-reviewing { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .btn-reviewing:hover { background: rgba(245, 158, 11, 0.25); }

    /* Modals */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 2rem;
    }

    .modal-overlay.active { display: flex; }

    .modal-content {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      width: 100%;
      max-width: 850px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
      overflow: hidden;
    }

    .modal-header {
      padding: 1.5rem 2rem;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      background: rgba(0, 0, 0, 0.2);
    }

    .modal-close {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 1.5rem;
      cursor: pointer;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
    }

    .modal-close:hover { color: var(--text-main); background: rgba(255, 255, 255, 0.1); }

    .modal-body {
      padding: 2rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 1rem;
      background: rgba(0, 0, 0, 0.2);
      padding: 1rem;
      border-radius: 10px;
      border: 1px solid var(--border-color);
    }

    .detail-item { display: flex; flex-direction: column; }
    .detail-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
    .detail-val { font-size: 0.95rem; font-weight: 600; color: var(--text-main); margin-top: 0.2rem; }

    .desc-box {
      font-size: 0.875rem;
      line-height: 1.6;
      color: #cbd5e1;
      white-space: pre-line;
      background: rgba(0, 0, 0, 0.15);
      padding: 1.25rem;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      max-height: 300px;
      overflow-y: auto;
    }

    /* Filter & Search Bar */
    .controls-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 0.85rem;
      margin-bottom: 1.5rem;
      background: var(--card-bg);
      padding: 1.25rem;
      border-radius: 12px;
      border: 1px solid var(--border-color);
    }

    .search-input, .select-input, .textarea-input {
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.6rem 0.85rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-family: inherit;
    }

    .search-input:focus, .select-input:focus, .textarea-input:focus { outline: none; border-color: var(--accent-cyan); }

    /* Pagination Controls */
    .pagination-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border-color);
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    .pagination-btns { display: flex; gap: 0.5rem; align-items: center; }

    /* Markdown Report View */
    .report-box {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 2rem;
      font-family: monospace;
      white-space: pre-wrap;
      color: #e2e8f0;
      line-height: 1.5;
      font-size: 0.875rem;
      overflow-x: auto;
    }

    /* Toast Notifications */
    #toast-container {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      pointer-events: none;
    }

    .toast {
      pointer-events: auto;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.75rem 1.25rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-main);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      gap: 0.6rem;
      animation: toastIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .toast-success { border-color: var(--accent-green); background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .toast-error { border-color: var(--accent-red); background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
    .toast-info { border-color: var(--accent-amber); background: rgba(245, 158, 11, 0.2); color: #fde047; }

    @keyframes toastIn {
      from { opacity: 0; transform: translateY(1rem); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Pipeline Status Banner */
    .pipeline-banner {
      background: linear-gradient(135deg, rgba(21, 28, 44, 0.95), rgba(30, 41, 59, 0.95));
      border: 1px solid var(--accent-cyan);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 2rem;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      transition: all 0.3s ease;
    }

    .pipeline-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }

    .pipeline-greeting {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-main);
    }

    .pipeline-state-badge {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
      background: var(--accent-cyan-bg);
      color: var(--accent-cyan);
      border: 1px solid var(--accent-cyan);
    }

    .pipeline-state-badge.complete {
      background: var(--accent-green-bg);
      color: var(--accent-green);
      border-color: var(--accent-green);
    }

    .pipeline-state-badge.error {
      background: var(--accent-red-bg);
      color: var(--accent-red);
      border-color: var(--accent-red);
    }

    .pipeline-subtext {
      font-size: 0.875rem;
      color: var(--text-muted);
      margin-bottom: 1rem;
    }

    .pipeline-progress-track {
      background: rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      height: 6px;
      width: 100%;
      overflow: hidden;
      margin-bottom: 1rem;
    }

    .pipeline-progress-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
      width: 0%;
      transition: width 0.4s ease;
      border-radius: 6px;
    }

    .pipeline-sources-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .source-chip {
      font-size: 0.75rem;
      font-weight: 500;
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: rgba(255, 255, 255, 0.03);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s ease;
    }

    .source-chip.fetching {
      border-color: var(--accent-amber);
      color: var(--accent-amber);
      background: var(--accent-amber-bg);
      animation: pulseChip 1.5s infinite ease-in-out;
    }

    .source-chip.completed {
      border-color: var(--accent-green);
      color: var(--accent-green);
      background: var(--accent-green-bg);
    }

    .source-chip.failed {
      border-color: var(--accent-red);
      color: var(--accent-red);
      background: var(--accent-red-bg);
    }

    @keyframes pulseChip {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }
  </style>

</head>
<body>

  <div id="toast-container"></div>

  <header>
    <div class="header-container">
      <div class="brand-title">
        <span>⚡</span> Job Intelligence & Application Tracker
      </div>
      <div class="live-clock" id="liveClock">Loading time...</div>
    </div>
  </header>

  <main>
    <!-- Live Pipeline Progress Banner -->
    <div id="pipeline-status-banner" class="pipeline-banner" style="display: none;">
      <div class="pipeline-header">
        <div class="pipeline-greeting" id="pipelineGreeting">Good afternoon 👋</div>
        <div class="pipeline-state-badge" id="pipelineStateBadge">Starting...</div>
      </div>
      <div class="pipeline-subtext" id="pipelineSubtext">Preparing your personalized job search...</div>
      <div class="pipeline-progress-track">
        <div class="pipeline-progress-fill" id="pipelineProgressFill"></div>
      </div>
      <div class="pipeline-sources-grid" id="pipelineSourcesGrid"></div>
    </div>

    <!-- Navigation Tabs -->
    <nav>

      <button class="nav-tab active" onclick="switchTab('dashboard')" id="tab-dashboard">
        📊 Dashboard
      </button>
      <button class="nav-tab" onclick="switchTab('all-jobs')" id="tab-all-jobs">
        💼 All Jobs <span class="badge" id="badge-all-count">0</span>
      </button>
      <button class="nav-tab" onclick="switchTab('tracker')" id="tab-tracker">
        📌 Application Tracker <span class="badge" id="badge-apps-count">0</span>
      </button>
      <button class="nav-tab" onclick="switchTab('analytics')" id="tab-analytics">
        📈 Application Analytics
      </button>
      <button class="nav-tab" onclick="switchTab('reports')" id="tab-reports">
        📝 Daily Reports
      </button>
    </nav>

    <!-- TAB 1: DASHBOARD OVERVIEW -->
    <div id="view-dashboard">
      <!-- Application Summary Cards -->
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">Total Applications</div>
          <div class="summary-value" id="stat-app-total">0</div>
          <div class="summary-subtext">Submitted & Tracked</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Applied This Week</div>
          <div class="summary-value" style="color: #60a5fa;" id="stat-app-week">0</div>
          <div class="summary-subtext">Last 7 Days</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Awaiting Response</div>
          <div class="summary-value" style="color: var(--accent-amber);" id="stat-app-awaiting">0</div>
          <div class="summary-subtext">Submitted (No Stage Yet)</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Interviews</div>
          <div class="summary-value" style="color: #c084fc;" id="stat-app-interviews">0</div>
          <div class="summary-subtext">Active Interview Funnel</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Offers</div>
          <div class="summary-value" style="color: var(--accent-green);" id="stat-app-offers">0</div>
          <div class="summary-subtext">Received Offers</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Rejections</div>
          <div class="summary-value" style="color: var(--accent-red);" id="stat-app-rejections">0</div>
          <div class="summary-subtext">Closed Applications</div>
        </div>
      </div>

      <!-- Main Sections -->
      <!-- 1. APPLY FIRST -->
      <div class="section-header">
        <div class="section-title">
          <span>🎯</span> 1. APPLY FIRST
        </div>
      </div>
      <div class="section-desc">Highest-priority eligible target backend engineering positions to apply for immediately.</div>
      <div class="jobs-grid" id="grid-apply-first">
        <div class="summary-subtext">Loading Apply First jobs...</div>
      </div>

      <!-- 2. FASTEST POTENTIAL CASH -->
      <div class="section-header">
        <div class="section-title">
          <span>⚡</span> 2. FASTEST POTENTIAL CASH
        </div>
      </div>
      <div class="section-desc">Short-term contracts, hourly positions, and fast-hiring roles with strong technical match.</div>
      <div class="jobs-grid" id="grid-fast-cash">
        <div class="summary-subtext">Loading Fast Cash jobs...</div>
      </div>

      <!-- 3. BEST TECHNICAL MATCH -->
      <div class="section-header">
        <div class="section-title">
          <span>☕</span> 3. BEST TECHNICAL MATCH
        </div>
      </div>
      <div class="section-desc">__SECTION_3_DESC__</div>
      <div class="jobs-grid" id="grid-tech-match">
        <div class="summary-subtext">Loading Technical Match jobs...</div>
      </div>

      <!-- 4. BEST LONG-TERM CAREER -->
      <div class="section-header">
        <div class="section-title">
          <span>🚀</span> 4. BEST LONG-TERM CAREER
        </div>
      </div>
      <div class="section-desc">Full-time engineering roles offering long-term career stability.</div>
      <div class="jobs-grid" id="grid-long-term">
        <div class="summary-subtext">Loading Long-Term Career jobs...</div>
      </div>

      <!-- 5. NEW TODAY -->
      <div class="section-header">
        <div class="section-title">
          <span>✨</span> 5. NEW TODAY
        </div>
      </div>
      <div class="section-desc">Newly discovered target and adjacent opportunities.</div>
      <div class="jobs-grid" id="grid-new-today">
        <div class="summary-subtext">Loading New Today jobs...</div>
      </div>
    </div>

    <!-- TAB 2: ALL JOBS -->
    <div id="view-all-jobs" style="display: none;">
      <div class="controls-bar">
        <input type="text" id="searchInput" class="search-input" style="grid-column: span 2;" placeholder="Search title, company, description, or stack (e.g. Java, Spring)..." oninput="onFilterChange()">
        
        <select id="sortSelect" class="select-input" onchange="onFilterChange()">
          <option value="PRIORITY_DESC">Sort: Priority Score (High to Low)</option>
          <option value="TECH_DESC">Sort: Tech Match (High to Low)</option>
          <option value="NEWEST">Sort: Newest Posted / Discovered</option>
          <option value="URGENCY_DESC">Sort: Most Urgent Cash</option>
          <option value="COMPANY_ASC">Sort: Company (A-Z)</option>
          <option value="TITLE_ASC">Sort: Title (A-Z)</option>
        </select>

        <select id="eligibilityFilter" class="select-input" onchange="onFilterChange()">
          <option value="ALL">All Remote Eligibility</option>
          <option value="ELIGIBLE">Eligible Only (Worldwide/EMEA)</option>
          <option value="UNKNOWN">Eligibility Unconfirmed</option>
          <option value="INELIGIBLE">Ineligible Only</option>
        </select>

        <select id="reviewFilter" class="select-input" onchange="onFilterChange()">
          <option value="ALL">All Review States</option>
          <option value="UNREVIEWED">Unreviewed Only</option>
          <option value="REVIEWING">Reviewing Only</option>
          <option value="DISMISSED">Dismissed Only</option>
          <option value="APPLIED">Applied Only</option>
        </select>

        <select id="sourceFilter" class="select-input" onchange="onFilterChange()">
          <option value="ALL">All Sources</option>
          <option value="remotive">Remotive</option>
          <option value="jobicy">Jobicy</option>
          <option value="weworkremotely">WeWorkRemotely</option>
        </select>

        <select id="tierFilter" class="select-input" onchange="onFilterChange()">
          <option value="ALL">All Match Tiers</option>
          <option value="STRONG_MATCH">Strong Match</option>
          <option value="GOOD_MATCH">Good Match</option>
          <option value="TRANSFERABLE">Transferable</option>
          <option value="SKILL_GAP">Skill Gap</option>
        </select>

        <select id="techScoreFilter" class="select-input" onchange="onFilterChange()">
          <option value="0">Min Tech Score: Any</option>
          <option value="50">Min Tech Score: 50+</option>
          <option value="70">Min Tech Score: 70+</option>
          <option value="80">Min Tech Score: 80+</option>
        </select>
      </div>

      <div class="jobs-grid" id="grid-all-jobs">
        <div class="summary-subtext">Loading all stored jobs...</div>
      </div>

      <!-- Pagination -->
      <div class="pagination-bar" id="paginationBar">
        <div id="paginationSummary">Showing 0 - 0 of 0 jobs</div>
        <div class="pagination-btns">
          <button class="btn btn-secondary" id="btnPrevPage" onclick="changePage(-1)">← Previous</button>
          <span id="pageIndicator" style="padding: 0 0.5rem;">Page 1 of 1</span>
          <button class="btn btn-secondary" id="btnNextPage" onclick="changePage(1)">Next →</button>
        </div>
      </div>
    </div>

    <!-- TAB 3: APPLICATION TRACKER PAGE -->
    <div id="view-tracker" style="display: none;">
      <div class="controls-bar" style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
        <select id="appStatusFilter" class="select-input" onchange="renderApplicationsView()" style="min-width: 250px;">
          <option value="ALL">All Application Statuses</option>
          <option value="APPLIED">Awaiting Response (Applied)</option>
          <option value="ASSESSMENT">Assessments</option>
          <option value="INTERVIEW">Interviews</option>
          <option value="OFFER">Offers</option>
          <option value="REJECTED">Rejected</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="WITHDRAWN">Withdrawn</option>
        </select>
        <button class="btn btn-primary" onclick="exportToExcel()" style="display: inline-flex; align-items: center; gap: 0.5rem; background: linear-gradient(135deg, #10b981, #059669); border: none; font-weight: 600; padding: 0.6rem 1.25rem; border-radius: 8px; cursor: pointer; color: #fff;">
          📊 Export to Excel
        </button>
      </div>

      <div class="jobs-grid" id="grid-applications">
        <div class="summary-subtext">Loading tracked applications...</div>
      </div>
    </div>

    <!-- TAB 4: APPLICATION ANALYTICS PAGE -->
    <div id="view-analytics" style="display: none;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem;">
          <span>📈</span> Application Analytics & Job Search Funnel
        </h2>
        <button class="btn btn-primary" onclick="exportToExcel()" style="display: inline-flex; align-items: center; gap: 0.5rem; background: linear-gradient(135deg, #10b981, #059669); border: none; font-weight: 600; padding: 0.6rem 1.25rem; border-radius: 8px; cursor: pointer; color: #fff;">
          📊 Export to Excel
        </button>
      </div>
      <!-- 1. Top-Level Metrics Grid -->
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">Total Applications</div>
          <div class="summary-value" id="an-total">0</div>
          <div class="summary-subtext">All Tracked Applications</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Applied Today</div>
          <div class="summary-value" style="color: #60a5fa;" id="an-today">0</div>
          <div class="summary-subtext">Submitted Today</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Applied Yesterday</div>
          <div class="summary-value" style="color: #93c5fd;" id="an-yesterday">0</div>
          <div class="summary-subtext">Submitted Yesterday</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Last 7 Days</div>
          <div class="summary-value" style="color: #c084fc;" id="an-7days">0</div>
          <div class="summary-subtext">Rolling 7-Day Window</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Last 30 Days</div>
          <div class="summary-value" style="color: var(--accent-cyan);" id="an-30days">0</div>
          <div class="summary-subtext">Rolling 30-Day Window</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Awaiting Response</div>
          <div class="summary-value" style="color: var(--accent-amber);" id="an-awaiting">0</div>
          <div class="summary-subtext">Active (No Final Outcome Yet)</div>
        </div>
      </div>

      <!-- 2. Daily Application Activity & Weekly Summary -->
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin-bottom: 2.5rem;">
        <!-- Daily Activity Section -->
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div style="font-weight: 600; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>📅</span> Daily Application Activity
            </div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-primary" id="btnDaily7" onclick="setDailyRange(7)" style="padding: 0.25rem 0.65rem; font-size: 0.775rem;">Last 7 Days</button>
              <button class="btn btn-secondary" id="btnDaily30" onclick="setDailyRange(30)" style="padding: 0.25rem 0.65rem; font-size: 0.775rem;">Last 30 Days</button>
            </div>
          </div>

          <!-- Bar Chart Container -->
          <div id="dailyChart" style="height: 180px; display: flex; align-items: flex-end; gap: 0.5rem; padding: 1rem 0; border-bottom: 1px solid var(--border-color); margin-bottom: 1rem;">
            <div class="summary-subtext">Loading daily chart...</div>
          </div>

          <!-- Daily Table -->
          <div style="max-height: 180px; overflow-y: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color); text-align: left; color: var(--text-muted);">
                  <th style="padding: 0.5rem;">DATE</th>
                  <th style="padding: 0.5rem; text-align: right;">APPLICATIONS</th>
                </tr>
              </thead>
              <tbody id="dailyTableBody">
                <!-- Rows rendered via JS -->
              </tbody>
            </table>
          </div>
        </div>

        <!-- Weekly Summary & Search Volume Progress -->
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>🚀</span> Weekly Job-Search Summary
            </div>

            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border: 1px solid var(--border-color);">
              <div style="font-size: 0.775rem; color: #60a5fa; text-transform: uppercase; font-weight: 600; margin-bottom: 0.5rem;">THIS WEEK</div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.85rem;">
                <div>Applications: <strong id="wk-tw-apps">0</strong></div>
                <div>Assessments: <strong id="wk-tw-assess">0</strong></div>
                <div>Interviews: <strong id="wk-tw-int">0</strong></div>
                <div>Offers: <strong id="wk-tw-offers">0</strong></div>
                <div style="grid-column: span 2;">Rejections: <strong id="wk-tw-rej">0</strong></div>
              </div>
            </div>

            <div style="background: rgba(0,0,0,0.15); border-radius: 8px; padding: 1rem; border: 1px solid var(--border-color);">
              <div style="font-size: 0.775rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 0.5rem;">PREVIOUS WEEK</div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.85rem; color: var(--text-muted);">
                <div>Applications: <strong id="wk-pw-apps" style="color: var(--text-main);">0</strong></div>
                <div>Assessments: <strong id="wk-pw-assess" style="color: var(--text-main);">0</strong></div>
                <div>Interviews: <strong id="wk-pw-int" style="color: var(--text-main);">0</strong></div>
                <div>Offers: <strong id="wk-pw-offers" style="color: var(--text-main);">0</strong></div>
                <div style="grid-column: span 2;">Rejections: <strong id="wk-pw-rej" style="color: var(--text-main);">0</strong></div>
              </div>
            </div>
          </div>

          <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); text-align: center;">
            <div style="font-size: 0.775rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">SEARCH VOLUME CHANGE</div>
            <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent-cyan);" id="wk-volume-change">--</div>
          </div>
        </div>
      </div>

      <!-- 3. Status Breakdown & Funnel Conversion Rates -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2.5rem;">
        <!-- Status Breakdown -->
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem;">
          <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            <span>📊</span> Application Status Breakdown
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.75rem;" id="statusBreakdownGrid">
            <!-- Rendered via JS -->
          </div>
        </div>

        <!-- Funnel Progression & Conversion Rates -->
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem;">
          <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            <span>🔻</span> Application Funnel & Conversion Rates
          </div>
          <div style="display: flex; flex-direction: column; gap: 0.75rem;" id="funnelContainer">
            <!-- Rendered via JS -->
          </div>
        </div>
      </div>

      <!-- 4. Source & Category Performance -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2.5rem;">
        <!-- Source Performance Table -->
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem;">
          <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            <span>🌐</span> Source Performance
          </div>
          <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
            <thead>
              <tr style="border-bottom: 1px solid var(--border-color); text-align: left; color: var(--text-muted);">
                <th style="padding: 0.5rem;">SOURCE</th>
                <th style="padding: 0.5rem; text-align: center;">APPS</th>
                <th style="padding: 0.5rem; text-align: center;">INT</th>
                <th style="padding: 0.5rem; text-align: center;">OFFERS</th>
                <th style="padding: 0.5rem; text-align: center;">REJ</th>
                <th style="padding: 0.5rem; text-align: right;">INT RATE</th>
              </tr>
            </thead>
            <tbody id="sourceTableBody">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>

        <!-- Role / Category Performance Table -->
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem;">
          <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            <span>💼</span> Role / Category Performance
          </div>
          <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
            <thead>
              <tr style="border-bottom: 1px solid var(--border-color); text-align: left; color: var(--text-muted);">
                <th style="padding: 0.5rem;">CATEGORY</th>
                <th style="padding: 0.5rem; text-align: center;">APPS</th>
                <th style="padding: 0.5rem; text-align: center;">ASSESS</th>
                <th style="padding: 0.5rem; text-align: center;">INT</th>
                <th style="padding: 0.5rem; text-align: center;">OFFERS</th>
                <th style="padding: 0.5rem; text-align: right;">REJ</th>
              </tr>
            </thead>
            <tbody id="categoryTableBody">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- 5. Next Actions Visibility -->
      <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; margin-bottom: 2.5rem;">
        <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
          <span>⏳</span> Next Actions
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem;">
          <!-- Overdue -->
          <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 10px; padding: 1rem;">
            <div style="color: #fca5a5; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.75rem; display: flex; align-items: center; justify-content: space-between;">
              <span>⚠️ OVERDUE</span>
              <span class="badge" id="cnt-overdue" style="background: var(--accent-red); color: white;">0</span>
            </div>
            <div id="list-overdue" style="display: flex; flex-direction: column; gap: 0.5rem;"></div>
          </div>

          <!-- Due Today -->
          <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 10px; padding: 1rem;">
            <div style="color: #fcd34d; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.75rem; display: flex; align-items: center; justify-content: space-between;">
              <span>🔔 DUE TODAY</span>
              <span class="badge" id="cnt-due-today" style="background: var(--accent-amber); color: black;">0</span>
            </div>
            <div id="list-due-today" style="display: flex; flex-direction: column; gap: 0.5rem;"></div>
          </div>

          <!-- Due in Next 7 Days -->
          <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 10px; padding: 1rem;">
            <div style="color: #93c5fd; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.75rem; display: flex; align-items: center; justify-content: space-between;">
              <span>📅 DUE IN NEXT 7 DAYS</span>
              <span class="badge" id="cnt-due-7days" style="background: var(--accent-blue); color: white;">0</span>
            </div>
            <div id="list-due-7days" style="display: flex; flex-direction: column; gap: 0.5rem;"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 5: REPORTS -->
    <div id="view-reports" style="display: none;">
      <div class="section-header">
        <div class="section-title">
          <span>📝</span> Latest Markdown Intelligence Report
        </div>
      </div>
      <div class="report-box" id="reportContent">Loading report content...</div>
    </div>
  </main>

  <!-- Job Detail Modal -->
  <div class="modal-overlay" id="jobModal" onclick="closeModalOnOverlay(event)">
    <div class="modal-content">
      <div class="modal-header">
        <div>
          <h2 class="job-title" id="modalTitle" style="font-size: 1.25rem;">Job Title</h2>
          <div class="company-name" id="modalCompany">Company Name</div>
        </div>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Priority Score</span>
            <span class="detail-val" id="modalPriority" style="color: #a78bfa;">0/100</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Tech Match Score</span>
            <span class="detail-val" id="modalTech" style="color: var(--accent-cyan);">0/100</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Income Urgency</span>
            <span class="detail-val" id="modalUrgency" style="color: var(--accent-amber);">0/100</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Freshness Factor</span>
            <span class="detail-val" id="modalFreshness">1.0x</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Remote Eligibility</span>
            <span class="detail-val" id="modalEligibility">ELIGIBLE</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Compensation</span>
            <span class="detail-val" id="modalComp">Undisclosed</span>
          </div>
        </div>

        <div>
          <span class="detail-label">Geographic Eligibility Rationale</span>
          <div class="why-box" id="modalEligibilityReason" style="margin-top: 0.35rem; border-left-color: var(--accent-green);">
            Eligibility info...
          </div>
        </div>

        <div>
          <span class="detail-label">Why Recommended</span>
          <div class="why-box" id="modalWhy" style="margin-top: 0.35rem;">
            Why match info...
          </div>
        </div>

        <div>
          <span class="detail-label">Gaps & Concerns</span>
          <div class="gap-box" id="modalGap" style="margin-top: 0.35rem;">
            Potential gaps info...
          </div>
        </div>

        <div>
          <span class="detail-label">Matched & Transferable Skills</span>
          <div style="font-size: 0.85rem; color: #cbd5e1; margin-top: 0.35rem;" id="modalSkills">
            Skills...
          </div>
        </div>

        <div>
          <span class="detail-label">Job Description</span>
          <div class="desc-box" id="modalDesc" style="margin-top: 0.35rem;">
            Full job description text...
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 1rem; margin-top: 0.5rem; flex-wrap: wrap; gap: 0.75rem;">
          <div style="font-size: 0.8rem; color: var(--text-muted);" id="modalSourceMeta">Source: Remotive | ID: 12345</div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button id="modalBtnReviewing" class="btn btn-reviewing" onclick="onModalSetReviewState('REVIEWING')">👀 Reviewing</button>
            <button id="modalBtnDismiss" class="btn btn-dismiss" onclick="onModalSetReviewState('DISMISSED')">🚫 Dismiss</button>
            <button id="modalBtnApplied" class="btn btn-applied" onclick="onModalMarkApplied()">✓ Mark as Applied</button>
            <a href="#" target="_blank" rel="noopener noreferrer" id="modalApplyBtn" class="btn btn-primary">
              Apply ↗
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Application Details & Edit Modal -->
  <div class="modal-overlay" id="appEditModal" onclick="closeAppModalOnOverlay(event)">
    <div class="modal-content">
      <div class="modal-header">
        <div>
          <h2 class="job-title" id="appModalTitle" style="font-size: 1.2rem;">Application Lifecycle</h2>
          <div class="company-name" id="appModalCompany">Company Name</div>
        </div>
        <button class="modal-close" onclick="closeAppModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Date Applied</span>
            <span class="detail-val" id="appModalAppliedAt" style="color: #60a5fa;">Date</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Current Status</span>
            <span class="detail-val" id="appModalStatusVal">APPLIED</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Interview Stage</span>
            <span class="detail-val" id="appModalStageVal">NONE</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Last Updated</span>
            <span class="detail-val" id="appModalUpdatedVal">Just now</span>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div>
            <label class="detail-label" style="display: block; margin-bottom: 0.35rem;">Application Status</label>
            <select id="editAppStatus" class="select-input" style="width: 100%;">
              <option value="APPLIED">APPLIED (Awaiting Response)</option>
              <option value="ASSESSMENT">ASSESSMENT (Take-home / Coding Test)</option>
              <option value="INTERVIEW">INTERVIEW (Recruiter / Tech / Final)</option>
              <option value="OFFER">OFFER (Offer Received)</option>
              <option value="ACCEPTED">ACCEPTED (Offer Accepted)</option>
              <option value="REJECTED">REJECTED (Not Selected)</option>
              <option value="WITHDRAWN">WITHDRAWN (Candidate Withdrew)</option>
            </select>
          </div>
          <div>
            <label class="detail-label" style="display: block; margin-bottom: 0.35rem;">Interview Stage</label>
            <select id="editAppStage" class="select-input" style="width: 100%;">
              <option value="NONE">NONE</option>
              <option value="STAGE_1">STAGE_1 (Initial Recruiter Screen)</option>
              <option value="STAGE_2">STAGE_2 (Technical Deep Dive / Live Code)</option>
              <option value="STAGE_3">STAGE_3 (System Design / Architecture)</option>
              <option value="FINAL">FINAL (Executive / Culture Fit)</option>
              <option value="OTHER">OTHER</option>
            </select>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1rem;">
          <div>
            <label class="detail-label" style="display: block; margin-bottom: 0.35rem;">Next Action Description</label>
            <input type="text" id="editAppNextAction" class="search-input" style="width: 100%;" placeholder="e.g. Technical interview scheduled for Friday, Follow up with recruiter...">
          </div>
          <div>
            <label class="detail-label" style="display: block; margin-bottom: 0.35rem;">Next Action Date</label>
            <input type="date" id="editAppNextDate" class="search-input" style="width: 100%;">
          </div>
        </div>

        <div>
          <label class="detail-label" style="display: block; margin-bottom: 0.35rem;">Interview & Salary Notes</label>
          <textarea id="editAppNotes" class="textarea-input" style="width: 100%; height: 100px;" placeholder="Add details about interview questions, compensation discussions, team feedback, or follow-up notes..."></textarea>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 1rem; margin-top: 0.5rem;">
          <button class="btn btn-secondary" onclick="openJobModalFromApp()">View Job Details</button>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary" onclick="closeAppModal()">Cancel</button>
            <button class="btn btn-primary" onclick="saveApplicationChanges()">Save Application Changes</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Utility functions
    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // Live Clock
    function updateClock() {
      const now = new Date();
      document.getElementById('liveClock').textContent = now.toLocaleDateString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Global State
    let allJobsData = [];
    let applicationsData = [];
    let analyticsData = null;
    let selectedDailyDays = 7;
    let activeJobIdModal = null;
    let activeAppIdModal = null;
    let currentPage = 1;
    const pageSize = 20;

    function exportToExcel() {
      window.location.href = '/api/export/applications.xlsx';
    }

    // Data Fetching
    async function loadDashboardData() {
      try {
        const [summaryRes, dashboardRes, allJobsRes, appsRes, reportRes] = await Promise.all([
          fetch('/api/summary'),
          fetch('/api/dashboard'),
          fetch('/api/jobs'),
          fetch('/api/applications'),
          fetch('/api/reports/latest')
        ]);

        const summary = await summaryRes.json();
        const dashboard = await dashboardRes.json();
        allJobsData = await allJobsRes.json();
        applicationsData = await appsRes.json();
        const report = await reportRes.json();

        // Update Summary Cards
        document.getElementById('stat-app-total').textContent = summary.total_applications || 0;
        document.getElementById('stat-app-week').textContent = summary.applications_this_week || 0;
        document.getElementById('stat-app-awaiting').textContent = summary.awaiting_response || 0;
        document.getElementById('stat-app-interviews').textContent = summary.interviews || 0;
        document.getElementById('stat-app-offers').textContent = summary.offers || 0;
        document.getElementById('stat-app-rejections').textContent = summary.rejections || 0;

        document.getElementById('badge-all-count').textContent = allJobsData.length || 0;
        document.getElementById('badge-apps-count').textContent = applicationsData.length || 0;

        // Render Dashboard Grids
        renderGrid('grid-apply-first', dashboard.apply_first || []);
        renderGrid('grid-fast-cash', dashboard.fastest_cash || []);
        renderGrid('grid-tech-match', dashboard.best_technical_match || []);
        renderGrid('grid-long-term', dashboard.best_long_term || []);
        renderGrid('grid-new-today', dashboard.new_today || []);

        // Render All Jobs Grid
        onFilterChange();

        // Render Applications Tracker Grid
        renderApplicationsView();

        // Render Report
        document.getElementById('reportContent').textContent = report.content || "No report available.";

        // Also refresh analytics if currently active tab
        if (document.getElementById('tab-analytics').classList.contains('active')) {
          loadAnalyticsData();
        }

      } catch (err) {
        console.error("Failed to load dashboard data:", err);
        showToast("⚠️ Unable to load dashboard data: " + err.message, "error");
        
        const retryHtml = `<div class="summary-subtext" style="color: var(--accent-red); margin-top: 0.5rem;">⚠️ Failed to load data: ${escapeHtml(err.message)}. <button class="btn btn-secondary" onclick="loadDashboardData()" style="margin-left: 0.5rem; padding: 0.2rem 0.6rem; font-size: 0.75rem;">🔄 Retry</button></div>`;
        
        ['grid-apply-first', 'grid-fast-cash', 'grid-tech-match', 'grid-long-term', 'grid-new-today', 'grid-all-jobs', 'grid-applications'].forEach(id => {
          const el = document.getElementById(id);
          if (el && (el.innerHTML.includes('Loading') || el.children.length === 0)) {
            el.innerHTML = retryHtml;
          }
        });
      }
    }

    // Analytics Data Fetching & Rendering
    async function loadAnalyticsData() {
      try {
        const res = await fetch('/api/analytics/all');
        if (!res.ok) return;
        analyticsData = await res.json();
        renderAnalyticsView();
      } catch (err) {
        console.error("Failed to load analytics data:", err);
      }
    }

    function setDailyRange(days) {
      selectedDailyDays = days;
      document.getElementById('btnDaily7').className = days === 7 ? 'btn btn-primary' : 'btn btn-secondary';
      document.getElementById('btnDaily30').className = days === 30 ? 'btn btn-primary' : 'btn btn-secondary';
      renderDailySection();
    }

    function renderAnalyticsView() {
      if (!analyticsData) return;

      const sum = analyticsData.summary || {};

      // 1. Top Metrics
      document.getElementById('an-total').textContent = sum.total_applications || 0;
      document.getElementById('an-today').textContent = sum.applications_today || 0;
      document.getElementById('an-yesterday').textContent = sum.applications_yesterday || 0;
      document.getElementById('an-7days').textContent = sum.applications_7_days || 0;
      document.getElementById('an-30days').textContent = sum.applications_30_days || 0;
      document.getElementById('an-awaiting').textContent = sum.awaiting_response || 0;

      // 2. Daily Timeline
      renderDailySection();

      // 3. Weekly Search Progress
      const wk = analyticsData.weekly_summary || {};
      const tw = wk.this_week || {};
      const pw = wk.previous_week || {};

      document.getElementById('wk-tw-apps').textContent = tw.applications || 0;
      document.getElementById('wk-tw-assess').textContent = tw.assessments || 0;
      document.getElementById('wk-tw-int').textContent = tw.interviews || 0;
      document.getElementById('wk-tw-offers').textContent = tw.offers || 0;
      document.getElementById('wk-tw-rej').textContent = tw.rejections || 0;

      document.getElementById('wk-pw-apps').textContent = pw.applications || 0;
      document.getElementById('wk-pw-assess').textContent = pw.assessments || 0;
      document.getElementById('wk-pw-int').textContent = pw.interviews || 0;
      document.getElementById('wk-pw-offers').textContent = pw.offers || 0;
      document.getElementById('wk-pw-rej').textContent = pw.rejections || 0;

      const volEl = document.getElementById('wk-volume-change');
      if (wk.volume_change_pct !== null && wk.volume_change_pct !== undefined) {
        const sign = wk.volume_change_pct >= 0 ? '+' : '';
        volEl.textContent = `${sign}${wk.volume_change_pct}%`;
        volEl.style.color = wk.volume_change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
      } else {
        volEl.textContent = 'Not enough historical data.';
        volEl.style.fontSize = '0.9rem';
        volEl.style.color = 'var(--text-muted)';
      }

      // 4. Status Breakdown
      const statusGrid = document.getElementById('statusBreakdownGrid');
      const statuses = [
        { label: 'APPLIED', val: sum.applied || 0, color: '#60a5fa' },
        { label: 'ASSESSMENT', val: sum.assessments || 0, color: '#c084fc' },
        { label: 'INTERVIEW', val: sum.interviews || 0, color: '#fbbf24' },
        { label: 'OFFER', val: sum.offers || 0, color: '#34d399' },
        { label: 'ACCEPTED', val: sum.accepted || 0, color: '#10b981' },
        { label: 'REJECTED', val: sum.rejections || 0, color: '#fca5a5' },
        { label: 'WITHDRAWN', val: sum.withdrawn || 0, color: '#94a3b8' },
      ];
      statusGrid.innerHTML = statuses.map(s => `
        <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem; text-align: center;">
          <div style="font-size: 0.725rem; color: var(--text-muted); text-transform: uppercase;">${s.label}</div>
          <div style="font-size: 1.35rem; font-weight: 700; color: ${s.color}; margin-top: 0.2rem;">${s.val}</div>
        </div>
      `).join('');

      // 5. Funnel & Conversion Rates
      const fn = analyticsData.funnel || {};
      const counts = fn.funnel_counts || {};
      const rates = fn.formatted_rates || {};

      const funnelContainer = document.getElementById('funnelContainer');
      funnelContainer.innerHTML = `
        <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.85rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
            <span>📥 APPLICATIONS: <strong>${counts.applications || 0}</strong></span>
            <span style="color: var(--accent-cyan); font-size: 0.8rem;">Conversion -> Assessment: ${rates.app_to_assessment || 'N/A'}</span>
          </div>
        </div>
        <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.85rem; margin-left: 0.75rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
            <span>🧪 ASSESSMENTS: <strong>${counts.assessments || 0}</strong></span>
            <span style="color: #c084fc; font-size: 0.8rem;">Conversion -> Interview: ${rates.app_to_interview || 'N/A'}</span>
          </div>
        </div>
        <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.85rem; margin-left: 1.5rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
            <span>🎙️ INTERVIEWS: <strong>${counts.interviews || 0}</strong></span>
            <span style="color: #fbbf24; font-size: 0.8rem;">Conversion -> Offer: ${rates.interview_to_offer || 'N/A'}</span>
          </div>
        </div>
        <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.85rem; margin-left: 2.25rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
            <span>🎉 OFFERS: <strong>${counts.offers || 0}</strong></span>
            <span style="color: var(--accent-green); font-size: 0.8rem;">Conversion -> Accepted: ${rates.offer_to_accepted || 'N/A'}</span>
          </div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 0.85rem; margin-left: 3rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 0.9rem; color: #34d399;">
            <span>🏆 ACCEPTED OFFERS: <strong>${counts.accepted || 0}</strong></span>
          </div>
        </div>
      `;

      // 6. Source Performance Table
      const sources = analyticsData.sources || [];
      const srcBody = document.getElementById('sourceTableBody');
      if (sources.length === 0) {
        srcBody.innerHTML = '<tr><td colspan="6" style="padding: 1rem; color: var(--text-muted);">No application source data recorded.</td></tr>';
      } else {
        srcBody.innerHTML = sources.map(s => `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 0.6rem; font-weight: 600; text-transform: uppercase;">${escapeHtml(s.source_name)}</td>
            <td style="padding: 0.6rem; text-align: center;">${s.applications}</td>
            <td style="padding: 0.6rem; text-align: center;">${s.interviews}</td>
            <td style="padding: 0.6rem; text-align: center; color: var(--accent-green);">${s.offers}</td>
            <td style="padding: 0.6rem; text-align: center; color: var(--accent-red);">${s.rejections}</td>
            <td style="padding: 0.6rem; text-align: right; font-weight: 600; color: var(--accent-cyan);">${s.interview_rate_pct}%</td>
          </tr>
        `).join('');
      }

      // 7. Category Performance Table
      const categories = analyticsData.categories || [];
      const catBody = document.getElementById('categoryTableBody');
      if (categories.length === 0) {
        catBody.innerHTML = '<tr><td colspan="6" style="padding: 1rem; color: var(--text-muted);">No application category data recorded.</td></tr>';
      } else {
        catBody.innerHTML = categories.map(c => `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 0.6rem; font-weight: 600;">${escapeHtml(c.category)}</td>
            <td style="padding: 0.6rem; text-align: center;">${c.applications}</td>
            <td style="padding: 0.6rem; text-align: center;">${c.assessments}</td>
            <td style="padding: 0.6rem; text-align: center;">${c.interviews}</td>
            <td style="padding: 0.6rem; text-align: center; color: var(--accent-green);">${c.offers}</td>
            <td style="padding: 0.6rem; text-align: right; color: var(--accent-red);">${c.rejections}</td>
          </tr>
        `).join('');
      }

      // 8. Next Actions
      const na = analyticsData.next_actions || {};
      renderNextActionsGroup('list-overdue', 'cnt-overdue', na.overdue || []);
      renderNextActionsGroup('list-due-today', 'cnt-due-today', na.due_today || []);
      renderNextActionsGroup('list-due-7days', 'cnt-due-7days', na.due_next_7_days || []);
    }

    function renderDailySection() {
      if (!analyticsData) return;
      const timeline = selectedDailyDays === 30 ? (analyticsData.daily_activity_30d || []) : (analyticsData.daily_activity_7d || []);

      const chart = document.getElementById('dailyChart');
      const maxCount = Math.max(1, ...timeline.map(t => t.count));

      chart.innerHTML = timeline.map(t => {
        const heightPct = Math.max(8, (t.count / maxCount) * 100);
        const dayLabel = t.date.substring(5); // MM-DD
        return `
          <div style="flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end;">
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.2rem;">${t.count > 0 ? t.count : ''}</div>
            <div style="width: 100%; max-width: 28px; height: ${heightPct}%; background: linear-gradient(180deg, #3b82f6, #1d4ed8); border-radius: 4px 4px 0 0;" title="${t.date}: ${t.count} apps"></div>
            <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 0.35rem; transform: rotate(-30deg); white-space: nowrap;">${dayLabel}</div>
          </div>
        `;
      }).join('');

      const tableBody = document.getElementById('dailyTableBody');
      tableBody.innerHTML = timeline.slice().reverse().map(t => `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
          <td style="padding: 0.4rem 0.5rem; font-weight: 500;">${t.date}</td>
          <td style="padding: 0.4rem 0.5rem; text-align: right; font-weight: 600; color: ${t.count > 0 ? '#60a5fa' : 'var(--text-muted)'};">${t.count}</td>
        </tr>
      `).join('');
    }

    function renderNextActionsGroup(listId, countId, items) {
      document.getElementById(countId).textContent = items.length;
      const listEl = document.getElementById(listId);

      if (items.length === 0) {
        listEl.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No items in this group.</div>';
        return;
      }

      listEl.innerHTML = items.map(item => `
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.65rem; font-size: 0.8rem; cursor: pointer;" onclick="openAppModal('${item.id}')">
          <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(item.job_title)}</div>
          <div style="color: #60a5fa; font-size: 0.75rem;">${escapeHtml(item.company_name)} | <span style="text-transform: uppercase;">${item.status}</span></div>
          <div style="margin-top: 0.35rem; color: #fcd34d;">📌 ${escapeHtml(item.next_action)} ${item.next_action_date ? `(${item.next_action_date})` : ''}</div>
        </div>
      `).join('');
    }

    function renderGrid(elementId, jobRecords) {
      const container = document.getElementById(elementId);
      if (!container) return;
      try {
        if (!jobRecords || jobRecords.length === 0) {
          container.innerHTML = '<div class="summary-subtext">No matching positions in this section.</div>';
          return;
        }
        container.innerHTML = jobRecords.map(rec => createJobCardHtml(rec)).join('');
      } catch (err) {
        console.error(`Failed rendering grid ${elementId}:`, err);
        container.innerHTML = `<div class="summary-subtext" style="color: var(--accent-red);">⚠️ Error rendering section: ${escapeHtml(err.message)}. <button class="btn btn-secondary" onclick="loadDashboardData()" style="margin-left: 0.5rem; padding: 0.2rem 0.6rem; font-size: 0.75rem;">🔄 Retry</button></div>`;
      }
    }

    function createJobCardHtml(rec) {
      const j = rec.job;
      const e = rec.explanation;

      let eligClass = 'pill-unknown';
      if (e.remote_eligibility === 'ELIGIBLE') eligClass = 'pill-eligible';
      else if (e.remote_eligibility === 'INELIGIBLE') eligClass = 'pill-ineligible';

      // History / Recency Badge
      let historyBadge = '👁️ PREVIOUSLY SEEN';
      if (j.status === 'CLOSED') historyBadge = '🔒 CLOSED';
      else if (e.freshness_factor >= 0.85) historyBadge = '✨ NEW TODAY';

      // Review state badge
      let reviewBadge = '';
      if (j.review_state === 'REVIEWING') reviewBadge = '<span class="pill pill-reviewing">👀 REVIEWING</span>';
      else if (j.review_state === 'DISMISSED') reviewBadge = '<span class="pill pill-dismissed">🚫 DISMISSED</span>';

      // Application status lookup
      const app = applicationsData.find(a => a.job_id === j.id);
      let appliedBadge = '';
      if (app) {
        const d = new Date(app.applied_at);
        appliedBadge = `<span class="pill pill-app-${app.status}">✓ ${app.status} (${d.toLocaleDateString()})</span>`;
      } else if (j.applied_at) {
        const d = new Date(j.applied_at);
        appliedBadge = `<span class="pill pill-applied">✓ APPLIED (${d.toLocaleDateString()})</span>`;
      }

      const urlEscaped = j.url ? j.url.replace(/"/g, '&quot;') : '#';
      const jobId = j.id;
      const isDismissed = j.review_state === 'DISMISSED';

      return `
        <div class="job-card ${isDismissed ? 'dismissed' : ''}">
          <div>
            <div class="job-header">
              <div>
                <div class="job-title">${escapeHtml(j.title)}</div>
                <div class="company-name">${escapeHtml(j.company_name)}</div>
              </div>
              <span class="source-tag">${escapeHtml(j.source_name)}</span>
            </div>

            <div class="meta-row" style="margin-top: 0.75rem;">
              <span class="pill ${eligClass}">
                🌐 ${e.remote_eligibility === 'ELIGIBLE' ? 'ELIGIBLE' : (e.remote_eligibility === 'UNKNOWN' ? 'UNCLEAR' : 'INELIGIBLE')}
              </span>
              <span class="pill pill-priority">Priority ${e.priority_score}</span>
              <span class="pill pill-tech">Tech ${e.technical_match_score}</span>
              <span class="pill pill-fresh">${historyBadge}</span>
              ${reviewBadge}
              ${appliedBadge}
            </div>

            <div style="font-size: 0.775rem; color: var(--text-muted); margin-top: 0.5rem;">
              💰 ${escapeHtml(e.compensation_text)} | 📍 ${escapeHtml(j.location_requirement || 'Remote')}
            </div>

            <div class="why-box" style="margin-top: 0.75rem;">
              ${escapeHtml(e.why_match)}
            </div>
          </div>

          <div class="card-actions">
            <a href="${urlEscaped}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
              Apply ↗
            </a>
            ${app ? 
              `<button class="btn btn-applied" onclick="openAppModal('${app.id}')">Status: ${app.status}</button>` : 
              (j.applied_at ? 
                '<span class="btn btn-applied">✓ Applied</span>' : 
                `<button class="btn btn-applied" onclick="markAppliedDirect('${jobId}')">Mark Applied</button>`
              )
            }
            <button class="btn btn-secondary" onclick="toggleReviewState('${jobId}')">
              ${j.review_state === 'REVIEWING' ? '👀 Reviewing' : (j.review_state === 'DISMISSED' ? '🚫 Dismissed' : 'Review')}
            </button>
            <button class="btn btn-secondary" onclick="openJobModal('${jobId}')">
              Details
            </button>
          </div>
        </div>
      `;
    }

    // Application Tracker Rendering
    function renderApplicationsView() {
      const container = document.getElementById('grid-applications');
      const filter = document.getElementById('appStatusFilter').value;

      const filtered = applicationsData.filter(app => {
        if (filter === 'ALL') return true;
        return app.status === filter;
      });

      if (filtered.length === 0) {
        container.innerHTML = '<div class="summary-subtext">No tracked applications in this status view.</div>';
        return;
      }

      container.innerHTML = filtered.map(app => {
        const j = app.job || { title: 'Unknown Job', company_name: 'Unknown Company', source_name: 'Direct' };
        const e = app.explanation || { priority_score: 0, technical_match_score: 0 };
        const dateStr = new Date(app.applied_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

        let nextActionBox = '';
        if (app.next_action) {
          nextActionBox = `
            <div class="action-box" style="margin-top: 0.6rem;">
              📅 Next: ${escapeHtml(app.next_action)} ${app.next_action_date ? `(${app.next_action_date})` : ''}
            </div>
          `;
        }

        let stageBadge = '';
        if (app.interview_stage && app.interview_stage !== 'NONE') {
          stageBadge = `<span class="pill pill-reviewing">🎙️ ${app.interview_stage}</span>`;
        }

        return `
          <div class="job-card">
            <div>
              <div class="job-header">
                <div>
                  <div class="job-title">${escapeHtml(j.title)}</div>
                  <div class="company-name">${escapeHtml(j.company_name)}</div>
                </div>
                <span class="source-tag">${escapeHtml(j.source_name)}</span>
              </div>

              <div class="meta-row" style="margin-top: 0.75rem;">
                <span class="pill pill-app-${app.status}">Status: ${app.status}</span>
                ${stageBadge}
                <span class="pill pill-priority">Priority ${e.priority_score}</span>
                <span class="pill pill-fresh">Applied ${dateStr}</span>
              </div>

              ${nextActionBox}

              ${app.notes ? `
                <div style="font-size: 0.8rem; color: #cbd5e1; margin-top: 0.6rem; font-style: italic; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 6px;">
                  "${escapeHtml(app.notes)}"
                </div>
              ` : ''}
            </div>

            <div class="card-actions">
              <button class="btn btn-primary" onclick="openAppModal('${app.id}')">
                Edit Status / Notes
              </button>
              <button class="btn btn-secondary" onclick="openJobModal('${app.job_id}')">
                Job Details
              </button>
              ${j.url ? `<a href="${j.url.replace(/"/g, '&quot;')}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">Original Link ↗</a>` : ''}
            </div>
          </div>
        `;
      }).join('');
    }

    // Filter, Sort, & Pagination Logic for All Jobs
    function onFilterChange() {
      currentPage = 1;
      renderAllJobsPage();
    }

    function getFilteredAndSortedJobs() {
      const q = document.getElementById('searchInput').value.toLowerCase().trim();
      const sort = document.getElementById('sortSelect').value;
      const elig = document.getElementById('eligibilityFilter').value;
      const review = document.getElementById('reviewFilter').value;
      const source = document.getElementById('sourceFilter').value;
      const tier = document.getElementById('tierFilter').value;
      const minTech = parseFloat(document.getElementById('techScoreFilter').value || "0");

      let filtered = allJobsData.filter(rec => {
        const j = rec.job;
        const e = rec.explanation;

        const matchQ = !q || j.title.toLowerCase().includes(q) || j.company_name.toLowerCase().includes(q) || (j.description_text || '').toLowerCase().includes(q) || j.source_name.toLowerCase().includes(q);
        const matchElig = (elig === 'ALL') || (e.remote_eligibility === elig);
        const matchReview = (review === 'ALL') || (review === 'APPLIED' ? !!j.applied_at : j.review_state === review);
        const matchSource = (source === 'ALL') || (j.source_name === source);
        const matchTier = (tier === 'ALL') || (e.match_tier === tier);
        const matchMinTech = e.technical_match_score >= minTech;

        return matchQ && matchElig && matchReview && matchSource && matchTier && matchMinTech;
      });

      // Sorting
      filtered.sort((a, b) => {
        if (sort === 'PRIORITY_DESC') return b.explanation.priority_score - a.explanation.priority_score;
        if (sort === 'TECH_DESC') return b.explanation.technical_match_score - a.explanation.technical_match_score;
        if (sort === 'NEWEST') return new Date(b.job.posted_at || b.job.first_seen_at) - new Date(a.job.posted_at || a.job.first_seen_at);
        if (sort === 'URGENCY_DESC') return b.explanation.income_urgency_score - a.explanation.income_urgency_score;
        if (sort === 'COMPANY_ASC') return a.job.company_name.localeCompare(b.job.company_name);
        if (sort === 'TITLE_ASC') return a.job.title.localeCompare(b.job.title);
        return 0;
      });

      return filtered;
    }

    function renderAllJobsPage() {
      const filtered = getFilteredAndSortedJobs();
      const total = filtered.length;
      const totalPages = Math.max(1, Math.ceil(total / pageSize));

      if (currentPage > totalPages) currentPage = totalPages;

      const startIdx = (currentPage - 1) * pageSize;
      const pageRecords = filtered.slice(startIdx, startIdx + pageSize);

      renderGrid('grid-all-jobs', pageRecords);

      // Pagination Controls
      document.getElementById('paginationSummary').textContent = total > 0 ? 
        `Showing ${startIdx + 1} - ${Math.min(startIdx + pageSize, total)} of ${total} jobs` : 
        `No jobs match the selected filters.`;

      document.getElementById('pageIndicator').textContent = `Page ${currentPage} of ${totalPages}`;
      document.getElementById('btnPrevPage').disabled = currentPage <= 1;
      document.getElementById('btnNextPage').disabled = currentPage >= totalPages;
    }

    function changePage(delta) {
      currentPage += delta;
      renderAllJobsPage();
    }

    // Toast Feedback Helper
    function showToast(message, type = 'success', duration = 3000) {
      const container = document.getElementById('toast-container');
      if (!container) return;
      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.innerHTML = `<span>${message}</span>`;
      container.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(0.5rem)';
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }

    // State Mutation APIs
    async function toggleReviewState(jobId) {
      const rec = allJobsData.find(r => r.job.id === jobId);
      if (!rec) return;

      let nextState = 'REVIEWING';
      if (rec.job.review_state === 'REVIEWING') nextState = 'DISMISSED';
      else if (rec.job.review_state === 'DISMISSED') nextState = 'UNREVIEWED';

      await setReviewState(jobId, nextState);
    }

    async function setReviewState(jobId, newState) {
      const rec = allJobsData.find(r => r.job.id === jobId);
      const title = rec ? rec.job.title : 'Job';

      try {
        const res = await fetch(`/api/jobs/${jobId}/review_state`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ review_state: newState })
        });
        if (res.ok) {
          if (rec) rec.job.review_state = newState;
          await loadDashboardData();
          if (newState === 'REVIEWING') {
            showToast(`👀 Marked "${title}" as Reviewing`, 'info');
          } else if (newState === 'DISMISSED') {
            showToast(`🚫 Dismissed "${title}" from recommendations`, 'info');
          } else {
            showToast(`Reset review state for "${title}"`, 'info');
          }
        } else {
          const errData = await res.json().catch(() => ({}));
          showToast(`❌ Failed to update review state: ${errData.error || res.statusText}`, 'error');
        }
      } catch (err) {
        console.error("Failed to set review state:", err);
        showToast(`❌ Connection error: ${err.message}`, 'error');
      }
    }

    async function markAppliedDirect(jobId) {
      const rec = allJobsData.find(r => r.job.id === jobId);
      const title = rec ? rec.job.title : 'Job';

      try {
        const res = await fetch(`/api/jobs/${jobId}/apply_intent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ applied: true })
        });
        if (res.ok) {
          await loadDashboardData();
          showToast(`✓ Marked "${title}" as Applied! Moved to Application Tracker.`, 'success');
        } else {
          const errData = await res.json().catch(() => ({}));
          showToast(`❌ Failed to mark as applied: ${errData.error || res.statusText}`, 'error');
        }
      } catch (err) {
        console.error("Failed to mark applied:", err);
        showToast(`❌ Connection error: ${err.message}`, 'error');
      }
    }

    // Modal Actions
    function openJobModal(jobId) {
      activeJobIdModal = jobId;
      const rec = allJobsData.find(r => r.job.id === jobId);
      if (!rec) return;

      const j = rec.job;
      const e = rec.explanation;

      document.getElementById('modalTitle').textContent = j.title;
      document.getElementById('modalCompany').textContent = j.company_name;
      document.getElementById('modalPriority').textContent = `${e.priority_score}/100`;
      document.getElementById('modalTech').textContent = `${e.technical_match_score}/100`;
      document.getElementById('modalUrgency').textContent = `${e.income_urgency_score}/100`;
      document.getElementById('modalFreshness').textContent = `${e.freshness_factor}x`;
      document.getElementById('modalEligibility').textContent = e.remote_eligibility;
      document.getElementById('modalComp').textContent = e.compensation_text;
      document.getElementById('modalEligibilityReason').textContent = e.eligibility_reason;
      document.getElementById('modalWhy').textContent = e.why_match;
      document.getElementById('modalGap').textContent = e.potential_gap;
      document.getElementById('modalSkills').textContent = `Matched: ${(e.matched_skills || []).join(', ') || 'None'} | Transferable: ${(e.transferable_skills || []).join(', ') || 'None'}`;
      document.getElementById('modalDesc').textContent = j.description_text || "No full description available.";
      document.getElementById('modalSourceMeta').textContent = `Source: ${j.source_name} | External ID: ${j.external_id}`;

      const applyBtn = document.getElementById('modalApplyBtn');
      applyBtn.href = j.url || '#';

      document.getElementById('jobModal').classList.add('active');
    }

    async function onModalSetReviewState(state) {
      if (!activeJobIdModal) return;
      const jId = activeJobIdModal;
      await setReviewState(jId, state);
      if (state === 'DISMISSED') {
        closeModal();
      } else {
        openJobModal(jId);
      }
    }

    async function onModalMarkApplied() {
      if (!activeJobIdModal) return;
      const jId = activeJobIdModal;
      await markAppliedDirect(jId);
      closeModal();
    }

    function closeModal() {
      document.getElementById('jobModal').classList.remove('active');
      activeJobIdModal = null;
    }

    function closeModalOnOverlay(e) {
      if (e.target.id === 'jobModal') closeModal();
    }

    // Application Modal Functions
    function openAppModal(appId) {
      activeAppIdModal = appId;
      const app = applicationsData.find(a => a.id === appId);
      if (!app) return;

      const j = app.job || { title: 'Job', company_name: 'Company' };
      document.getElementById('appModalTitle').textContent = j.title;
      document.getElementById('appModalCompany').textContent = j.company_name;
      document.getElementById('appModalAppliedAt').textContent = new Date(app.applied_at).toLocaleDateString();
      document.getElementById('appModalStatusVal').textContent = app.status;
      document.getElementById('appModalStageVal').textContent = app.interview_stage || 'NONE';
      document.getElementById('appModalUpdatedVal').textContent = new Date(app.updated_at || app.applied_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      document.getElementById('editAppStatus').value = app.status || 'APPLIED';
      document.getElementById('editAppStage').value = app.interview_stage || 'NONE';
      document.getElementById('editAppNextAction').value = app.next_action || '';
      document.getElementById('editAppNextDate').value = app.next_action_date || '';
      document.getElementById('editAppNotes').value = app.notes || '';

      document.getElementById('appEditModal').classList.add('active');
    }

    async function saveApplicationChanges() {
      if (!activeAppIdModal) return;

      const payload = {
        status: document.getElementById('editAppStatus').value,
        interview_stage: document.getElementById('editAppStage').value,
        next_action: document.getElementById('editAppNextAction').value,
        next_action_date: document.getElementById('editAppNextDate').value,
        notes: document.getElementById('editAppNotes').value
      };

      try {
        const res = await fetch(`/api/applications/${activeAppIdModal}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeAppModal();
          await loadDashboardData();
          showToast(`✓ Application details saved successfully.`, 'success');
        } else {
          const errData = await res.json().catch(() => ({}));
          showToast(`❌ Failed to save application changes: ${errData.error || res.statusText}`, 'error');
        }
      } catch (err) {
        console.error("Failed to save application changes:", err);
        showToast(`❌ Connection error: ${err.message}`, 'error');
      }
    }

    function openJobModalFromApp() {
      if (!activeAppIdModal) return;
      const app = applicationsData.find(a => a.id === activeAppIdModal);
      if (app && app.job_id) {
        closeAppModal();
        openJobModal(app.job_id);
      }
    }

    function closeAppModal() {
      document.getElementById('appEditModal').classList.remove('active');
      activeAppIdModal = null;
    }

    function closeAppModalOnOverlay(e) {
      if (e.target.id === 'appEditModal') closeAppModal();
    }

    // Tab Navigation
    function switchTab(tabId) {
      const tabs = ['dashboard', 'all-jobs', 'tracker', 'analytics', 'reports'];
      tabs.forEach(t => {
        document.getElementById(`tab-${t}`).classList.remove('active');
        document.getElementById(`view-${t}`).style.display = 'none';
      });

      document.getElementById(`tab-${tabId}`).classList.add('active');
      document.getElementById(`view-${tabId}`).style.display = 'block';

      if (tabId === 'analytics') {
        loadAnalyticsData();
      }
    }

    function getTimeOfDayGreeting(candidateName) {
      const name = candidateName || 'Candidate';
      const hour = new Date().getHours();
      let greetingPrefix = 'Good morning';
      if (hour >= 12 && hour < 17) {
        greetingPrefix = 'Good afternoon';
      } else if (hour >= 17) {
        greetingPrefix = 'Good evening';
      }
      return `${greetingPrefix}, ${name} 👋`;
    }

    let pipelineStatusInterval = null;
    let lastPipelineCompleted = false;

    async function checkPipelineStatus() {
      try {
        const res = await fetch('/api/pipeline/status');
        if (!res.ok) return;
        const data = await res.json();
        renderPipelineStatusBanner(data);
      } catch (err) {
        console.error("Failed to fetch pipeline status:", err);
      }
    }

    function renderPipelineStatusBanner(data) {
      const banner = document.getElementById('pipeline-status-banner');
      if (!banner || !data || data.state === 'IDLE') {
        if (banner) banner.style.display = 'none';
        return;
      }

      banner.style.display = 'block';

      const greeting = getTimeOfDayGreeting(data.candidate_name);
      document.getElementById('pipelineGreeting').textContent = greeting;

      const badge = document.getElementById('pipelineStateBadge');
      const subtext = document.getElementById('pipelineSubtext');
      const fill = document.getElementById('pipelineProgressFill');
      const sourcesGrid = document.getElementById('pipelineSourcesGrid');

      badge.className = 'pipeline-state-badge';

      const sourceKeys = Object.keys(data.sources || {});
      const totalSources = sourceKeys.length || 1;
      let completedCount = 0;
      let fetchingCount = 0;

      let chipsHtml = '';
      sourceKeys.forEach(key => {
        const info = data.sources[key] || {};
        let statusClass = '';
        let icon = '⏳';
        let detail = '';

        if (info.status === 'COMPLETED') {
          statusClass = 'completed';
          icon = '✓';
          completedCount++;
          if (info.fetched > 0) detail = ` (${info.fetched})`;
        } else if (info.status === 'FETCHING') {
          statusClass = 'fetching';
          icon = '⟳';
          fetchingCount++;
        } else if (info.status === 'FAILED') {
          statusClass = 'failed';
          icon = '✕';
          completedCount++;
        }

        chipsHtml += `<div class="source-chip ${statusClass}"><span>${icon}</span> <span>${key}${detail}</span></div>`;
      });

      sourcesGrid.innerHTML = chipsHtml;

      let percent = Math.min(100, Math.round((completedCount / totalSources) * 85));

      if (data.state === 'STARTING') {
        badge.textContent = 'Starting...';
        subtext.textContent = 'Profile loaded. Preparing your job search...';
        fill.style.width = '10%';
      } else if (data.state === 'INGESTING') {
        badge.textContent = `Fetching Jobs (${completedCount}/${totalSources})`;
        subtext.textContent = `Querying remote job boards for ${data.candidate_title || 'matches'}...`;
        fill.style.width = `${Math.max(15, percent)}%`;
      } else if (data.state === 'SCORING') {
        badge.textContent = 'Scoring & Ranking...';
        subtext.textContent = 'Evaluating compensation, remote eligibility, and preference scores...';
        fill.style.width = '92%';
      } else if (data.state === 'COMPLETE') {
        badge.textContent = 'Search Ready';
        badge.classList.add('complete');
        fill.style.width = '100%';

        const fetched = data.summary ? data.summary.total_fetched : 0;
        const newCount = data.summary ? data.summary.total_new : 0;
        const strong = data.summary ? data.summary.strong_matches : 0;

        subtext.textContent = `✓ Your job search is ready · ${newCount} new relevant job${newCount !== 1 ? 's' : ''} found · ${strong} strong match${strong !== 1 ? 'es' : ''}.`;

        if (!lastPipelineCompleted) {
          lastPipelineCompleted = true;
          loadDashboardData();
        }

        if (pipelineStatusInterval) {
          clearInterval(pipelineStatusInterval);
          pipelineStatusInterval = null;
        }
      } else if (data.state === 'ERROR') {
        badge.textContent = 'Notice';
        badge.classList.add('error');
        subtext.textContent = `⚠️ Discovery completed with errors: ${data.error || 'Unknown error'}. Showing cached matches below.`;
        fill.style.width = '100%';

        if (pipelineStatusInterval) {
          clearInterval(pipelineStatusInterval);
          pipelineStatusInterval = null;
        }
      }
    }

    // Initial Load & Status Polling
    loadDashboardData();
    checkPipelineStatus();
    pipelineStatusInterval = setInterval(checkPipelineStatus, 1000);
  </script>
</body>
</html>
"""
    return html_template.replace("__SECTION_3_DESC__", section_3_desc)


