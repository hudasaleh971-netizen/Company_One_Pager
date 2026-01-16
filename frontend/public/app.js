/**
 * Citation UI - Frontend Application
 * 
 * Tab 1: Annual Report Analysis with collapsible sections
 * Tab 2: Web Search (placeholder)
 * Tab 3: Company One Pager (placeholder)
 * 
 * Consumes AnnualReportResponse from API with:
 * - overview, products, leadership, stakeholders, metrics
 * - Each section has: section_name, clean_text, cited_text, citations, sources
 */

const API_BASE_URL = 'http://localhost:8000';

// ========== DOM Elements ==========
const form = document.getElementById('analysis-form');
const companyInput = document.getElementById('company-name');
const fileInput = document.getElementById('annual-report');
const fileName = document.getElementById('file-name');
const submitBtn = document.getElementById('submit-btn');
const btnText = submitBtn.querySelector('.btn-text');
const btnLoader = submitBtn.querySelector('.btn-loader');

const inputSection = document.getElementById('input-section');
const resultsSection = document.getElementById('results-section');
const resultsTitle = document.getElementById('results-title');
const sectionsContainer = document.getElementById('sections-container');
const sectionCountBadge = document.getElementById('section-count');
const backBtn = document.getElementById('back-btn');

const tooltip = document.getElementById('tooltip');
const tooltipPage = document.getElementById('tooltip-page');
const tooltipTitle = document.getElementById('tooltip-title');
const tooltipContent = document.getElementById('tooltip-content');

// Tab elements
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Store data from API (per section)
let sectionData = {};

// ========== Tab Navigation ==========
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        
        // Update active states
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(`tab-${tabId}`).classList.add('active');
        
        console.log(`📑 Switched to tab: ${tabId}`);
    });
});

// ========== Event Listeners ==========
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    fileName.textContent = file ? file.name : 'Choose PDF file';
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await runAnalysis();
});

backBtn.addEventListener('click', () => {
    resultsSection.style.display = 'none';
    inputSection.style.display = 'flex';
});

// ========== Analysis Functions ==========
async function runAnalysis() {
    const companyName = companyInput.value.trim();
    if (!companyName) return;

    setLoading(true);
    console.log(`🚀 Starting analysis for: ${companyName}`);

    try {
        const formData = new FormData();
        formData.append('company_name', companyName);

        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
            console.log(`📁 Uploading file: ${fileInput.files[0].name}`);
        }

        // Use the sequential endpoint (rate-limit safe, runs one section at a time)
        // Alternative: /api/analyze-report for parallel extraction (faster but may hit rate limits)
        const response = await fetch(`${API_BASE_URL}/api/analyze-report-sequential`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        console.log('📥 API Response:', data);

        if (data.error) {
            throw new Error(data.error);
        }

        // Store section data
        sectionData = {
            overview: data.overview,
            products: data.products,
            leadership: data.leadership,
            stakeholders: data.stakeholders,
            metrics: data.metrics
        };

        // Display results
        displayResults(companyName, sectionData);

    } catch (error) {
        console.error('❌ Analysis failed:', error);
        alert(`Analysis failed: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    btnText.style.display = isLoading ? 'none' : 'inline';
    btnLoader.style.display = isLoading ? 'flex' : 'none';
}

// ========== Display Functions ==========
function displayResults(companyName, sections) {
    resultsTitle.textContent = `${companyName} - Annual Report Analysis`;
    
    // Count valid sections
    const validSections = Object.values(sections).filter(s => s !== null);
    sectionCountBadge.textContent = `${validSections.length} sections`;
    
    // Clear previous content
    sectionsContainer.innerHTML = '';
    
    // Section order and display names
    const sectionOrder = [
        { key: 'overview', title: 'Company Overview', icon: '🏢' },
        { key: 'products', title: 'Products & Services', icon: '📦' },
        { key: 'leadership', title: 'Leadership Team', icon: '👥' },
        { key: 'stakeholders', title: 'Stakeholders', icon: '📊' },
        { key: 'metrics', title: 'Key Metrics', icon: '📈' }
    ];
    
    sectionOrder.forEach(({ key, title, icon }) => {
        const section = sections[key];
        if (section) {
            const sectionEl = createCollapsibleSection(key, title, icon, section);
            sectionsContainer.appendChild(sectionEl);
        }
    });
    
    // Add citation listeners to all rendered sections
    addCitationListeners();
    
    // Show results
    inputSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    console.log(`✅ Displayed ${validSections.length} sections`);
}

function createCollapsibleSection(key, title, icon, section) {
    const container = document.createElement('div');
    container.className = 'collapsible-section';
    container.dataset.section = key;
    
    // Count citations for this section
    const citationCount = section.citations?.length || 0;
    
    // Header
    const header = document.createElement('div');
    header.className = 'section-header';
    header.innerHTML = `
        <div class="section-title">
            <span class="section-icon">${icon}</span>
            <span class="section-name">${title}</span>
            <span class="citation-badge">${citationCount} citations</span>
        </div>
        <button class="collapse-btn" aria-expanded="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6,9 12,15 18,9"/>
            </svg>
        </button>
    `;
    
    // Content
    const content = document.createElement('div');
    content.className = 'section-content expanded';
    
    // Process cited text for display
    const processedContent = processCitationTags(section.cited_text || '', section.sources || {}, key);
    content.innerHTML = `<div class="section-body">${renderMarkdown(processedContent)}</div>`;
    
    container.appendChild(header);
    container.appendChild(content);
    
    // Toggle collapse
    header.addEventListener('click', () => {
        const isExpanded = content.classList.contains('expanded');
        content.classList.toggle('expanded');
        header.querySelector('.collapse-btn').setAttribute('aria-expanded', !isExpanded);
    });
    
    return container;
}

function processCitationTags(content, sources, sectionKey) {
    // Map source IDs to display numbers (per section)
    let citationNumber = 1;
    const citationMap = {};

    return content.replace(/\[\[Src:(\d+)\]\]/g, (match, srcNum) => {
        const sourceId = `src_${srcNum}`;

        if (!citationMap[sourceId]) {
            citationMap[sourceId] = citationNumber++;
        }

        const displayNum = citationMap[sourceId];
        return `<span class="citation" data-source-id="${sourceId}" data-section="${sectionKey}" data-num="${displayNum}">${displayNum}</span>`;
    });
}

function renderMarkdown(content) {
    let html = content;

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Lists (bullet)
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Lists (numbered)
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Tables - basic support
    const tableRegex = /\|(.+)\|\n\|[-: |]+\|\n((?:\|.+\|\n?)+)/g;
    html = html.replace(tableRegex, (match, headerRow, bodyRows) => {
        const headers = headerRow.split('|').filter(h => h.trim());
        const rows = bodyRows.trim().split('\n').map(row => 
            row.split('|').filter(c => c.trim())
        );
        
        let table = '<table><thead><tr>';
        headers.forEach(h => table += `<th>${h.trim()}</th>`);
        table += '</tr></thead><tbody>';
        rows.forEach(row => {
            table += '<tr>';
            row.forEach(cell => table += `<td>${cell.trim()}</td>`);
            table += '</tr>';
        });
        table += '</tbody></table>';
        return table;
    });

    // Paragraphs
    html = html.split('\n\n').map(p => {
        p = p.trim();
        if (!p) return '';
        if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || 
            p.startsWith('<li') || p.startsWith('<table')) {
            return p;
        }
        return `<p>${p}</p>`;
    }).join('\n');

    return html;
}

// ========== Tooltip Functions ==========
let hideTimeout = null;
let currentSourceId = null;
let currentSectionKey = null;

function addCitationListeners() {
    const citations = document.querySelectorAll('.citation');

    citations.forEach(citation => {
        citation.addEventListener('mouseenter', showTooltip);
        citation.addEventListener('mouseleave', startHideTimer);
        citation.addEventListener('click', pinTooltip);
    });

    // Keep tooltip visible when hovering over it
    tooltip.addEventListener('mouseenter', cancelHideTimer);
    tooltip.addEventListener('mouseleave', startHideTimer);
}

function showTooltip(e) {
    cancelHideTimer();

    const sourceId = e.target.dataset.sourceId;
    const sectionKey = e.target.dataset.section;
    currentSourceId = sourceId;
    currentSectionKey = sectionKey;
    
    // Get source from the specific section's data
    const section = sectionData[sectionKey];
    const source = section?.sources?.[sourceId];

    if (source) {
        // Display page number or fallback
        const pageText = source.page_number || 'Source';
        tooltipPage.textContent = pageText;

        // Display title
        tooltipTitle.textContent = source.title || 'Annual Report';

        // Display FULL raw text (scrollable in tooltip)
        const rawText = source.raw_text || 'No preview available';
        tooltipContent.textContent = rawText;  // Show full text, tooltip is scrollable

        positionTooltipNear(e.target);
        tooltip.classList.add('visible');
        
        console.log(`📖 Showing tooltip for ${sourceId} in ${sectionKey}`);
    } else {
        console.warn(`⚠️ Source not found: ${sourceId} in section ${sectionKey}`);
    }
}

function pinTooltip(e) {
    // Click to keep the tooltip visible
    cancelHideTimer();
    tooltip.classList.add('pinned');
}

function startHideTimer() {
    // Don't hide if pinned
    if (tooltip.classList.contains('pinned')) return;

    // Delay before hiding to allow moving to tooltip
    hideTimeout = setTimeout(() => {
        tooltip.classList.remove('visible');
        currentSourceId = null;
        currentSectionKey = null;
    }, 300);
}

function cancelHideTimer() {
    if (hideTimeout) {
        clearTimeout(hideTimeout);
        hideTimeout = null;
    }
}

function hideTooltip() {
    tooltip.classList.remove('visible', 'pinned');
    currentSourceId = null;
    currentSectionKey = null;
}

function positionTooltipNear(element) {
    const rect = element.getBoundingClientRect();
    const padding = 12;

    let x = rect.right + padding;
    let y = rect.top;

    // Get tooltip size (need to make visible first to measure)
    tooltip.style.visibility = 'hidden';
    tooltip.style.display = 'block';
    const tooltipRect = tooltip.getBoundingClientRect();
    tooltip.style.visibility = '';
    tooltip.style.display = '';

    // Prevent overflow right
    if (x + tooltipRect.width > window.innerWidth - padding) {
        x = rect.left - tooltipRect.width - padding;
    }

    // Prevent overflow bottom
    if (y + tooltipRect.height > window.innerHeight - padding) {
        y = window.innerHeight - tooltipRect.height - padding;
    }

    // Prevent negative values
    x = Math.max(padding, x);
    y = Math.max(padding, y);

    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
}

// Close tooltip when clicking outside
document.addEventListener('click', (e) => {
    if (!tooltip.contains(e.target) && !e.target.classList.contains('citation')) {
        hideTooltip();
    }
});

// ========== Initialize ==========
companyInput.focus();
console.log('🚀 Company Analysis UI initialized');
