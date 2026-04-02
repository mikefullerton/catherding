// quick-ref.js — shared JS for /quick-ref generated pages
// Copy this entire file into a <script> tag at the end of <body>

const filterInput = document.getElementById('filter');
const findInput = document.getElementById('find');
const countEl = document.getElementById('count');
const findPosEl = document.getElementById('find-pos');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const skills = document.querySelectorAll('.skill');
const sections = document.querySelectorAll('h2, h3');
const total = skills.length;

// Build source (h2) and section (h3) lookups + auto-linkify unlinked titles
skills.forEach(s => {
  let h3Link = null;
  let el = s.previousElementSibling;
  while (el) {
    if (el.tagName === 'H3' && !s.dataset.section) {
      s.dataset.section = el.textContent.toLowerCase().trim();
      const a = el.querySelector('a[href]');
      if (a) h3Link = a.href;
    }
    if (el.tagName === 'H2') {
      s.dataset.source = el.textContent.toLowerCase().trim();
      break;
    }
    el = el.previousElementSibling;
  }
  if (h3Link) {
    const codeEl = s.querySelector('code');
    if (codeEl && !codeEl.parentElement.matches('a')) {
      const a = document.createElement('a');
      a.href = h3Link;
      a.target = '_blank';
      a.rel = 'noopener';
      a.tabIndex = -1;
      codeEl.parentNode.insertBefore(a, codeEl);
      a.appendChild(codeEl);
    }
  }
});

function parseQuery(raw) {
  const q = raw.toLowerCase().trim();
  const prefixes = ['source:', 'section:'];
  for (const p of prefixes) {
    if (q.startsWith(p)) {
      return { mode: p.slice(0, -1), term: q.slice(p.length).trim() };
    }
  }
  return { mode: 'title', term: q };
}

function matchSkill(s, mode, term) {
  if (!term) return true;
  if (mode === 'source') return (s.dataset.source || '').includes(term);
  if (mode === 'section') return (s.dataset.section || '').includes(term);
  return s.querySelector('code').textContent.toLowerCase().includes(term);
}

function updateHeaders() {
  sections.forEach(h => {
    let next = h.nextElementSibling;
    let hasVisible = false;
    while (next && next.tagName !== h.tagName && !(h.tagName === 'H3' && next.tagName === 'H2')) {
      if (next.classList.contains('skill') && !next.classList.contains('hidden')) hasVisible = true;
      if (next.tagName === 'H3' && h.tagName === 'H2') {
        let inner = next.nextElementSibling;
        while (inner && inner.tagName !== 'H2' && inner.tagName !== 'H3') {
          if (inner.classList.contains('skill') && !inner.classList.contains('hidden')) hasVisible = true;
          inner = inner.nextElementSibling;
        }
      }
      next = next.nextElementSibling;
    }
    h.classList.toggle('hidden', !hasVisible);
  });
}

function clearFilterMarks() {
  document.querySelectorAll('mark.filter-mark').forEach(m => {
    const parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
}

function highlightFilterInNode(node, query) {
  if (node.nodeType === Node.TEXT_NODE) {
    const idx = node.textContent.toLowerCase().indexOf(query);
    if (idx === -1) return;
    const before = node.textContent.slice(0, idx);
    const match = node.textContent.slice(idx, idx + query.length);
    const after = node.textContent.slice(idx + query.length);
    const mark = document.createElement('mark');
    mark.className = 'filter-mark';
    mark.textContent = match;
    const parent = node.parentNode;
    if (before) parent.insertBefore(document.createTextNode(before), node);
    parent.insertBefore(mark, node);
    if (after) parent.insertBefore(document.createTextNode(after), node);
    parent.removeChild(node);
  } else if (node.nodeType === Node.ELEMENT_NODE && !node.classList.contains('find-badge')) {
    [...node.childNodes].forEach(child => highlightFilterInNode(child, query));
  }
}

function updateFilter() {
  clearFilterMarks();
  const { mode, term } = parseQuery(filterInput.value);
  let visible = 0;
  skills.forEach(s => {
    const match = matchSkill(s, mode, term);
    s.classList.toggle('hidden', !match);
    if (match) visible++;
  });
  updateHeaders();
  if (term && mode === 'title') {
    [...skills].filter(s => !s.classList.contains('hidden')).forEach(s => {
      const codeEl = s.querySelector('code');
      if (codeEl) highlightFilterInNode(codeEl, term);
    });
  }
  const label = term
    ? `Showing ${visible} of ${total} items` + (mode !== 'title' ? ` (filtering by ${mode})` : '')
    : `${total} items`;
  countEl.textContent = label;
  updateFind();
}

// ── Find ──
let findMatches = [];
let findIndex = -1;
let lastFindQuery = '';
const allFindable = [...document.querySelectorAll('h2, h3, .skill')];

function clearHighlight() {
  allFindable.forEach(el => {
    el.classList.remove('find-highlight');
    const badge = el.querySelector('.find-badge');
    if (badge) badge.textContent = '';
  });
  document.querySelectorAll('mark.find-mark').forEach(m => {
    const parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
}

function getVisibleFindable() {
  return allFindable.filter(el => !el.classList.contains('hidden'));
}

function findableText(el) {
  if (el.classList.contains('skill')) {
    const title = el.querySelector('code').textContent.toLowerCase();
    const desc = el.querySelector('p').textContent.toLowerCase();
    const source = (el.dataset.source || '').toLowerCase();
    const section = (el.dataset.section || '').toLowerCase();
    return title + ' ' + desc + ' ' + source + ' ' + section;
  }
  return el.textContent.toLowerCase();
}

function highlightTextInNode(node, query) {
  if (node.nodeType === Node.TEXT_NODE) {
    const idx = node.textContent.toLowerCase().indexOf(query);
    if (idx === -1) return;
    const before = node.textContent.slice(0, idx);
    const match = node.textContent.slice(idx, idx + query.length);
    const after = node.textContent.slice(idx + query.length);
    const mark = document.createElement('mark');
    mark.className = 'find-mark';
    mark.textContent = match;
    const parent = node.parentNode;
    if (before) parent.insertBefore(document.createTextNode(before), node);
    parent.insertBefore(mark, node);
    if (after) parent.insertBefore(document.createTextNode(after), node);
    parent.removeChild(node);
  } else if (node.nodeType === Node.ELEMENT_NODE && !node.classList.contains('find-badge')) {
    [...node.childNodes].forEach(child => highlightTextInNode(child, query));
  }
}

function updateFind() {
  clearHighlight();
  const q = findInput.value.toLowerCase().trim();
  lastFindQuery = q;
  if (!q) {
    findMatches = [];
    findIndex = -1;
    findPosEl.textContent = '';
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    return;
  }
  findMatches = getVisibleFindable().filter(el => findableText(el).includes(q));
  findMatches.forEach(el => highlightTextInNode(el, q));
  prevBtn.disabled = findMatches.length === 0;
  nextBtn.disabled = findMatches.length === 0;
  if (findMatches.length > 0) {
    findIndex = 0;
    highlightCurrent();
  } else {
    findIndex = -1;
    findPosEl.textContent = '0 / 0';
  }
}

function highlightCurrent() {
  allFindable.forEach(el => {
    el.classList.remove('find-highlight');
    const badge = el.querySelector('.find-badge');
    if (badge) badge.textContent = '';
  });
  if (findIndex < 0 || findMatches.length === 0) return;
  const el = findMatches[findIndex];
  el.classList.add('find-highlight');
  const badge = el.querySelector('.find-badge');
  if (badge) badge.textContent = `${findIndex + 1}/${findMatches.length}`;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  findPosEl.textContent = `${findIndex + 1} / ${findMatches.length}`;
}

function findNext() {
  if (findMatches.length === 0) return;
  findIndex = (findIndex + 1) % findMatches.length;
  highlightCurrent();
}

function findPrev() {
  if (findMatches.length === 0) return;
  findIndex = (findIndex - 1 + findMatches.length) % findMatches.length;
  highlightCurrent();
}

// ── Autocomplete history ──
const HISTORY_KEY = 'quick-ref-search-history';

function loadHistory(key) {
  try { return JSON.parse(localStorage.getItem(key)) || []; } catch { return []; }
}
function saveHistory(key, list) {
  localStorage.setItem(key, JSON.stringify(list.slice(0, 50)));
}
function addToHistory(key, value) {
  const v = value.trim();
  if (!v) return;
  const list = loadHistory(key).filter(x => x !== v);
  list.unshift(v);
  saveHistory(key, list);
}
function replaceInHistory(key, oldVal, newVal) {
  const list = loadHistory(key);
  const nv = newVal.trim();
  if (!nv) return;
  const cleaned = list.filter(x => x !== nv);
  const idx = cleaned.indexOf(oldVal);
  if (idx !== -1) {
    cleaned[idx] = nv;
  } else {
    cleaned.unshift(nv);
  }
  saveHistory(key, cleaned);
}

function setupAutocomplete(input, listEl, historyKey, onCommit) {
  let acIndex = -1;
  let autocommitEntry = null;
  let autocommitTimer = null;

  function showAC() {
    const q = input.value.toLowerCase().trim();
    const history = loadHistory(historyKey);
    const filtered = q ? history.filter(h => h.toLowerCase().includes(q)) : history;
    while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
    acIndex = -1;
    if (filtered.length === 0) { listEl.classList.remove('open'); return; }
    filtered.forEach(item => {
      const d = document.createElement('div');
      d.textContent = item;
      d.addEventListener('mousedown', e => {
        e.preventDefault();
        input.value = item;
        listEl.classList.remove('open');
        endSession();
        onCommit();
      });
      listEl.appendChild(d);
    });
    listEl.classList.add('open');
  }

  function hideAC() { listEl.classList.remove('open'); acIndex = -1; }

  function navAC(dir) {
    const items = listEl.querySelectorAll('div');
    if (items.length === 0) return false;
    if (!listEl.classList.contains('open')) { showAC(); return true; }
    items.forEach(d => d.classList.remove('ac-active'));
    acIndex += dir;
    if (acIndex >= items.length) acIndex = 0;
    if (acIndex < 0) acIndex = items.length - 1;
    items[acIndex].classList.add('ac-active');
    items[acIndex].scrollIntoView({ block: 'nearest' });
    return true;
  }

  function selectAC() {
    const items = listEl.querySelectorAll('div');
    if (acIndex >= 0 && acIndex < items.length) {
      input.value = items[acIndex].textContent;
      hideAC();
      endSession();
      onCommit();
      return true;
    }
    return false;
  }

  function scheduleAutocommit() {
    if (autocommitTimer) clearTimeout(autocommitTimer);
    autocommitTimer = setTimeout(() => {
      const v = input.value.trim();
      if (!v) return;
      if (autocommitEntry) {
        replaceInHistory(historyKey, autocommitEntry, v);
      } else {
        addToHistory(historyKey, v);
      }
      autocommitEntry = v;
    }, 1000);
  }

  function endSession() {
    if (autocommitTimer) clearTimeout(autocommitTimer);
    const v = input.value.trim();
    if (v) {
      if (autocommitEntry) {
        replaceInHistory(historyKey, autocommitEntry, v);
      } else {
        addToHistory(historyKey, v);
      }
    }
    autocommitEntry = null;
  }

  input.addEventListener('focus', () => {
    autocommitEntry = null;
    showAC();
  });
  input.addEventListener('input', () => {
    showAC();
    scheduleAutocommit();
    onCommit();
  });
  input.addEventListener('blur', () => {
    endSession();
    setTimeout(hideAC, 150);
  });

  return { hideAC, navAC, selectAC, showAC, endSession };
}

const findAC = setupAutocomplete(findInput, document.getElementById('find-ac'), HISTORY_KEY, updateFind);
const filterAC = setupAutocomplete(filterInput, document.getElementById('filter-ac'), HISTORY_KEY, updateFilter);

function commitFind() {
  findAC.endSession();
  findAC.hideAC();
}
function commitFilter() {
  filterAC.endSession();
  filterAC.hideAC();
}

function handleEscape(input, clearFn, acHelper) {
  acHelper.hideAC();
  if (input.value) {
    input.value = '';
    clearFn();
  } else {
    input.blur();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

// ── Clear buttons ──
const findWrap = document.getElementById('find-wrap');
const filterWrap = document.getElementById('filter-wrap');
const findClear = document.getElementById('find-clear');
const filterClear = document.getElementById('filter-clear');

function syncClearBtn(input, wrap) {
  wrap.classList.toggle('has-value', input.value.length > 0);
}

// ── Focus switching between Find/Filter resets page ──
findInput.addEventListener('focus', () => {
  if (filterInput.value) {
    filterInput.value = '';
    clearFilterMarks();
    skills.forEach(s => s.classList.remove('hidden'));
    sections.forEach(h => h.classList.remove('hidden'));
    countEl.textContent = `${total} items`;
    updateFind();
    syncClearBtn(filterInput, filterWrap);
  }
});
filterInput.addEventListener('focus', () => {
  if (findInput.value) {
    findInput.value = '';
    clearHighlight();
    findMatches = [];
    findIndex = -1;
    findPosEl.textContent = '';
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    syncClearBtn(findInput, findWrap);
  }
});

// ── Key handlers ──
findInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') { handleEscape(findInput, updateFind, findAC); syncClearBtn(findInput, findWrap); e.preventDefault(); return; }
  const acOpen = document.getElementById('find-ac').classList.contains('open');
  if (e.key === 'ArrowDown' && acOpen) { findAC.navAC(1); e.preventDefault(); return; }
  if (e.key === 'ArrowUp' && acOpen) { findAC.navAC(-1); e.preventDefault(); return; }
  if ((e.key === 'Enter' || e.key === 'Tab') && acOpen && findAC.selectAC()) { e.preventDefault(); return; }
  if (e.key === 'Enter') { commitFind(); e.shiftKey ? findPrev() : findNext(); e.preventDefault(); return; }
  if (e.key === 'Tab') { commitFind(); return; }
  if (e.key === 'ArrowDown') { findNext(); e.preventDefault(); return; }
  if (e.key === 'ArrowUp') { findPrev(); e.preventDefault(); return; }
});

filterInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') { handleEscape(filterInput, () => { updateFilter(); updateFind(); }, filterAC); syncClearBtn(filterInput, filterWrap); e.preventDefault(); return; }
  const acOpen = document.getElementById('filter-ac').classList.contains('open');
  if (e.key === 'ArrowDown' && acOpen) { filterAC.navAC(1); e.preventDefault(); return; }
  if (e.key === 'ArrowUp' && acOpen) { filterAC.navAC(-1); e.preventDefault(); return; }
  if ((e.key === 'Enter' || e.key === 'Tab') && acOpen && filterAC.selectAC()) { if (e.key !== 'Tab') e.preventDefault(); return; }
  if (e.key === 'Enter') { commitFilter(); e.preventDefault(); return; }
  if (e.key === 'Tab') { commitFilter(); return; }
});

nextBtn.addEventListener('click', findNext);
prevBtn.addEventListener('click', findPrev);

findInput.addEventListener('input', () => syncClearBtn(findInput, findWrap));
filterInput.addEventListener('input', () => syncClearBtn(filterInput, filterWrap));

findClear.addEventListener('mousedown', e => {
  e.preventDefault();
  handleEscape(findInput, updateFind, findAC);
  syncClearBtn(findInput, findWrap);
  findInput.focus();
});
filterClear.addEventListener('mousedown', e => {
  e.preventDefault();
  handleEscape(filterInput, () => { updateFilter(); updateFind(); }, filterAC);
  syncClearBtn(filterInput, filterWrap);
  filterInput.focus();
});

// Remove all other elements from tab order
document.querySelectorAll('a, button:not(.clear-btn):not(.nav-btn)').forEach(el => {
  el.setAttribute('tabindex', '-1');
});

updateFilter();
syncClearBtn(findInput, findWrap);
syncClearBtn(filterInput, filterWrap);
