// youtube_analysis.js — robust + footer-hide + colors
try { window.__YT_ANALYSIS_JS_PRESENT__ = true; } catch (_) {}
let sentimentChart = null;
let hateChart = null;
let timelineChart = null;

// Helpers to control canvas sizing to avoid stretched charts
function _clearForcedCanvasSize(canvas) {
  if (!canvas) return;
  canvas.style.height = '';
  canvas.style.minHeight = '0px';
  canvas.style.maxHeight = 'none';
  canvas.style.width = '100%';
}
function _enforceSquareCanvas(canvas) {
  if (!canvas) return;
  const w = (canvas.parentElement && canvas.parentElement.clientWidth) ? canvas.parentElement.clientWidth : canvas.clientWidth || 300;
  canvas.removeAttribute('height');
  canvas.removeAttribute('width');
  canvas.width = w;
  canvas.height = w;
}
// Note: we intentionally avoid forcing heights. Chart.js will keep aspect ratio.

function getCSSVariable(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function hideFooter() {
  try {
    const f = document.querySelector('footer') || document.querySelector('.site-footer');
    if (f) {
      f.dataset._origDisplay = f.style.display || '';
      f.style.display = 'none';
    }
  } catch (e) { console.warn('hideFooter err', e); }
}
function showFooter() {
  try {
    const f = document.querySelector('footer') || document.querySelector('.site-footer');
    if (f) {
      f.style.display = f.dataset._origDisplay || '';
      delete f.dataset._origDisplay;
    }
  } catch (e) { console.warn('showFooter err', e); }
}

// Loader + form handling
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('youtube-analysis-form');
  const loader = document.getElementById('loading-animation');
  const button = form ? form.querySelector('button[type="submit"]') : null;

  if (form && loader) {
    form.addEventListener('submit', () => {
      // show loader + hide footer so footer doesn't overlap page
      loader.style.display = 'flex';
      hideFooter();
      if (button) {
        button.disabled = true;
        button.setAttribute('data-original-text', button.innerHTML);
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Analyzing...`;
      }
    });
  }

  // When page loads, if results present, init charts
  const el = document.getElementById('analysis-data');
  if (el) {
    try {
      // Read JSON as-is (backend already escapes where needed)
      let txt = (el.textContent || el.innerText || '').trim();
      // strip BOM if present
      if (txt.charCodeAt(0) === 0xFEFF) txt = txt.slice(1);
      const analysisData = JSON.parse(txt);
      initializeCharts(analysisData);
    } catch (e) {
      console.error('Failed to parse analysis data', e);
      // debug helper: show short preview of the text so we can inspect quickly
      try {
        const el2 = document.getElementById('analysis-data');
        console.log('analysis-data preview:', (el2 && el2.textContent) ? el2.textContent.slice(0,1000) : 'no data');
      } catch (e2) { /* ignore */ }
    } finally {
      // ensure footer visible (analysis finished if page already has results)
      showFooter();
      // restore analyze button if any
      const b = document.querySelector('#youtube-analysis-form button[type="submit"]');
      if (b && b.dataset && b.dataset.originalText) {
        b.innerHTML = b.dataset.originalText;
        b.disabled = false;
      }
    }
  }

  // "Show more comments"
  const showMoreBtn = document.getElementById('show-more-comments');
  if (showMoreBtn) {
    showMoreBtn.addEventListener('click', () => {
      const hidden = document.querySelectorAll('.hidden-comment');
      const batch = Array.from(hidden).slice(0, 10);
      batch.forEach(el => (el.style.display = 'block', el.classList.remove('hidden-comment')));
      if (document.querySelectorAll('.hidden-comment').length === 0) {
        showMoreBtn.style.display = 'none';
      }
    });
  }
});

// Public API used by the template after it injects data
function initializeCharts(data) {
  try {
    // Normalize incoming data. The server now sends the full `results` schema.
    // Build distributions from known keys or compute from analyzed_comments.
    let sentimentDist = {};
    let hateDist = {};
    let timelineObj = {};

    // 1) Try direct distributions
    if (data && data.sentiment_distribution && typeof data.sentiment_distribution === 'object') {
      sentimentDist = data.sentiment_distribution;
    }
    if (data && data.hate_distribution && typeof data.hate_distribution === 'object') {
      hateDist = data.hate_distribution;
    }

    // 2) Fallback: compute from analyzed_comments
    if ((!sentimentDist || Object.keys(sentimentDist).length === 0) && Array.isArray(data?.analyzed_comments)) {
      const counts = { Positive: 0, Neutral: 0, Negative: 0 };
      data.analyzed_comments.forEach(c => {
        const s = (c && c.sentiment) ? String(c.sentiment).toLowerCase() : 'neutral';
        if (s.startsWith('pos') || s.includes('positive')) counts.Positive++;
        else if (s.startsWith('neg') || s.includes('negative')) counts.Negative++;
        else counts.Neutral++;
      });
      sentimentDist = counts;
    }
    if ((!hateDist || Object.keys(hateDist).length === 0) && Array.isArray(data?.analyzed_comments)) {
      const counts = { 'Safe Content': 0, 'Hate Speech': 0 };
      data.analyzed_comments.forEach(c => {
        const h = (c && c.hate_speech) ? String(c.hate_speech).toLowerCase() : 'safe';
        if (h.startsWith('hate')) counts['Hate Speech']++; else counts['Safe Content']++;
      });
      hateDist = counts;
    }

    // 3) Timeline: prefer server-provided timeline_data
    if (data && data.timeline_data && typeof data.timeline_data === 'object') {
      timelineObj = data.timeline_data;
    } else if (Array.isArray(data?.analyzed_comments)) {
      const byDate = {};
      data.analyzed_comments.forEach(c => {
        const d = ((c && c.date) ? String(c.date) : '').split('T')[0] || new Date().toISOString().split('T')[0];
        if (!byDate[d]) byDate[d] = { Positive: 0, Neutral: 0, Negative: 0 };
        const s = (c && c.sentiment) ? String(c.sentiment).toLowerCase() : 'neutral';
        if (s.startsWith('pos') || s.includes('positive')) byDate[d].Positive++;
        else if (s.startsWith('neg') || s.includes('negative')) byDate[d].Negative++;
        else byDate[d].Neutral++;
      });
      const labels = Object.keys(byDate).sort();
      timelineObj = {
        labels,
        datasets: {
          positive: labels.map(l => byDate[l].Positive),
          neutral: labels.map(l => byDate[l].Neutral),
          negative: labels.map(l => byDate[l].Negative)
        }
      };
    }

    // Diagnostics to help identify empty charts
    try {
      console.log('[YouTubeAnalysis] parsed results:', {
        total: data?.total_comments,
        kpis: data?.kpis,
        sentiment_distribution: sentimentDist,
        hate_distribution: hateDist,
        timeline_labels: timelineObj?.labels?.length || 0
      });
    } catch (_) {}

    // Ensure non-empty values so Chart.js draws something
    const sum = obj => Object.values(obj || {}).reduce((a,b)=>a+(Number(b)||0),0);
    if (sum(sentimentDist) === 0 && (Array.isArray(data?.analyzed_comments) && data.analyzed_comments.length > 0)) {
      // default everyone to Neutral to visualize counts
      sentimentDist = { Positive: 0, Neutral: data.analyzed_comments.length, Negative: 0 };
    }
    if (sum(hateDist) === 0 && (Array.isArray(data?.analyzed_comments) && data.analyzed_comments.length > 0)) {
      hateDist = { 'Safe Content': data.analyzed_comments.length, 'Hate Speech': 0 };
    }
    if (!timelineObj || !Array.isArray(timelineObj.labels) || timelineObj.labels.length === 0) {
      // create single bucket based on distributions, if any
      timelineObj = {
        labels: ['All'],
        datasets: {
          positive: [sentimentDist.Positive || 0],
          neutral: [sentimentDist.Neutral || 0],
          negative: [sentimentDist.Negative || 0]
        }
      };
    }

    // Build line timeline (Total vs Hate) preferred style
    const makeLineFrom = () => {
      // Prefer explicit server format {labels, datasets:{total:[], hate:[]}}
      if (data && data.timeline_line && Array.isArray(data.timeline_line.labels)) {
        return data.timeline_line;
      }
      const labels = (timelineObj && Array.isArray(timelineObj.labels)) ? timelineObj.labels.slice() : [];
      const result = { labels: [], datasets: { total: [], hate: [] } };
      if (labels.length) {
        // If we have pos/neu/neg, make totals
        const pos = ((timelineObj.datasets||{}).positive||[]); 
        const neu = ((timelineObj.datasets||{}).neutral||[]);
        const neg = ((timelineObj.datasets||{}).negative||[]);
        result.labels = labels;
        for (let i=0;i<labels.length;i++) {
          const tot = (Number(pos[i]||0)+Number(neu[i]||0)+Number(neg[i]||0));
          result.datasets.total.push(tot);
          result.datasets.hate.push(0); // will improve from analyzed_comments below
        }
      }
      // If analyzed_comments available, compute hate/total per date precisely
      if (Array.isArray(data?.analyzed_comments) && data.analyzed_comments.length>0) {
        const byDate = {};
        data.analyzed_comments.forEach(c => {
          const d = ((c && c.date) ? String(c.date) : '').split('T')[0] || new Date().toISOString().split('T')[0];
          if (!byDate[d]) byDate[d] = { total: 0, hate: 0 };
          byDate[d].total++;
          const h = (c && c.hate_speech) ? String(c.hate_speech).toLowerCase() : 'safe';
          if (h.startsWith('hate')) byDate[d].hate++;
        });
        const keys = Object.keys(byDate).sort();
        result.labels = keys;
        result.datasets.total = keys.map(k => byDate[k].total);
        result.datasets.hate = keys.map(k => byDate[k].hate);
      }
      if (!Array.isArray(result.labels) || result.labels.length===0) {
        return { labels: ['All'], datasets: { total: [data?.total_comments||0], hate: [0] } };
      }
      return result;
    };

    const lineTimeline = makeLineFrom();

    // Finally draw charts
    createSentimentChart(sentimentDist);
    createHateChart(hateDist);
    createTimelineChart(lineTimeline);

    // mark as rendered to prevent duplicate drawing by inline scripts
    try { window.__YT_ANALYSIS_JS_RENDERED__ = true; } catch (_) {}
  } catch (e) {
    console.error('Chart initialization failed', e);
  } finally {
    // show footer always after chart init
    showFooter();
    // restore button
    const b = document.querySelector('#youtube-analysis-form button[type="submit"]');
    if (b && b.dataset && b.dataset.originalText) {
      b.innerHTML = b.dataset.originalText;
      b.disabled = false;
    }
    // hide loader
    const loader = document.getElementById('loading-animation');
    if (loader) loader.style.display = 'none';
  }
}

// ====== Chart builders ======
function createSentimentChart(dist) {
  const canvas = document.getElementById('sentimentChart');
  if (!canvas) return;
  if (sentimentChart && typeof sentimentChart.destroy === 'function') sentimentChart.destroy();
  // Ensure perfect circle: let Chart.js control sizing
  _clearForcedCanvasSize(canvas);
  _enforceSquareCanvas(canvas);
  const ctx = canvas.getContext ? canvas.getContext('2d') : null;
  if (!ctx) return;

  const labels = Object.keys(dist);
  const values = Object.values(dist);

  // ensure labels order: Positive, Neutral, Negative
  const order = ['Positive', 'Neutral', 'Negative'];
  const orderedValues = order.map(k => dist[k] || 0);
  const orderedLabels = order;

  sentimentChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: orderedLabels,
      datasets: [{
        data: orderedValues,
        backgroundColor: ['#2ecc71', '#95a5a6', '#e74c3c'],
        borderColor: 'rgba(0,0,0,0.3)',
        borderWidth: 1,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 1,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: getCSSVariable('--text-secondary') || '#fff' }
        },
        tooltip: { mode: 'index', intersect: false }
      },
      layout: { padding: { top: 10, right: 10, bottom: 10, left: 10 } }
      ,cutout: '65%'
    }
  });

  // Keep circle on container resize
  try {
    if (window.__SENTIMENT_RO && typeof window.__SENTIMENT_RO.disconnect === 'function') {
      window.__SENTIMENT_RO.disconnect();
    }
    if (window.ResizeObserver) {
      window.__SENTIMENT_RO = new ResizeObserver(() => {
        _enforceSquareCanvas(canvas);
        if (sentimentChart && typeof sentimentChart.resize === 'function') sentimentChart.resize();
      });
      window.__SENTIMENT_RO.observe(canvas.parentElement || canvas);
    }
  } catch (_) {}
}

function createHateChart(dist) {
  const canvas = document.getElementById('hateChart');
  if (!canvas) return;
  if (hateChart && typeof hateChart.destroy === 'function') hateChart.destroy();
  // Let Chart.js control height via aspectRatio
  _clearForcedCanvasSize(canvas);
  const ctx = canvas.getContext ? canvas.getContext('2d') : null;
  if (!ctx) return;

  // order Safe Content then Hate Speech
  const labels = ['Safe Content', 'Hate Speech'];
  const values = [dist['Safe Content'] || 0, dist['Hate Speech'] || 0];

  hateChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Count',
        data: values,
        backgroundColor: ['#2ecc71', '#e74c3c'],
        borderColor: ['#1e9f52', '#c0392b'],
        borderWidth: 0,
        borderRadius: 10,
        maxBarThickness: 56,
        barThickness: 'flex'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 1.7,
      plugins: {
        legend: { display: false },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: {
          ticks: { color: getCSSVariable('--text-secondary') || '#ccc' },
          grid: { display: false },
          stacked: false
        },
        y: {
          beginAtZero: true,
          ticks: { color: getCSSVariable('--text-secondary') || '#ccc' },
          grid: { color: 'rgba(255,255,255,0.06)' }
        }
      },
      categoryPercentage: 0.6,
      barPercentage: 0.9
    }
  });
}

function createTimelineChart(timeline) {
  const canvas = document.getElementById('timelineChart');
  if (!canvas) return;
  if (timelineChart && typeof timelineChart.destroy === 'function') timelineChart.destroy();
  const ctx = canvas.getContext ? canvas.getContext('2d') : null;
  if (!ctx) return;

  if (!timeline || !timeline.labels || !timeline.datasets) return;

  // Expect datasets: { total:[], hate:[] }
  const total = (timeline.datasets.total||[]);
  const hate = (timeline.datasets.hate||[]);

  timelineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: timeline.labels,
      datasets: [
        {
          label: 'Total Comments',
          data: total,
          borderColor: '#8a2be2',
          backgroundColor: 'rgba(138,43,226,0.15)',
          borderWidth: 3,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: '#8a2be2',
          pointBorderColor: '#fff',
          pointBorderWidth: 1,
          fill: false
        },
        {
          label: 'Hate Speech Comments',
          data: hate,
          borderColor: '#e74c3c',
          backgroundColor: 'rgba(231,76,60,0.15)',
          borderWidth: 3,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: '#e74c3c',
          pointBorderColor: '#fff',
          pointBorderWidth: 1,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { color: getCSSVariable('--text-secondary') || '#fff' } },
        tooltip: { mode: 'index', intersect: false }
      },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          ticks: { color: getCSSVariable('--text-secondary') || '#ccc', maxTicksLimit: 12 },
          grid: { color: 'rgba(255,255,255,0.06)' }
        },
        y: {
          beginAtZero: true,
          ticks: { color: getCSSVariable('--text-secondary') || '#ccc' },
          grid: { color: 'rgba(255,255,255,0.06)' }
        }
      }
    }
  });
}

// Export to template
window.initializeCharts = initializeCharts;
