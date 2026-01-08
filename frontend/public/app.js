/**
 * Citation UI - Frontend Application
 * 
 * Consumes FinalResponse from API with:
 * - clean_text: Text without tags
 * - cited_text: Text with [[Src:xxx]] tags
 * - citations: List of {start_index, end_index, source_id}
 * - sources: Dict of {source_id: {title, page_number, raw_text}}
 */

const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
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
const resultsContent = document.getElementById('results-content');
const citationBadge = document.getElementById('citation-badge');
const backBtn = document.getElementById('back-btn');

const tooltip = document.getElementById('tooltip');
const tooltipPage = document.getElementById('tooltip-page');
const tooltipTitle = document.getElementById('tooltip-title');
const tooltipContent = document.getElementById('tooltip-content');

// Store data from API
let sourcesData = {};
let citationsData = [];

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

    try {
        const formData = new FormData();
        formData.append('company_name', companyName);

        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
        }

        const response = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Store data from FinalResponse
        sourcesData = data.sources || {};
        citationsData = data.citations || [];

        // Use cited_text from new API format (contains [[Src:xxx]] tags)
        // Falls back to content for old API format, or empty string
        const citedText = data.cited_text || data.content || '';

        if (!citedText) {
            throw new Error('No content received from analysis');
        }

        // Display results using cited_text (has tags for processing)
        displayResults(companyName, citedText, citationsData.length);

    } catch (error) {
        console.error('Analysis failed:', error);
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

function displayResults(companyName, citedText, citationCount) {
    resultsTitle.textContent = `${companyName} - Stakeholder Analysis`;
    citationBadge.textContent = `${citationCount} citations`;

    // Convert [[Src:XXX]] tags to numbered citation spans
    const processedContent = processCitationTags(citedText);

    // Render with basic markdown
    resultsContent.innerHTML = renderMarkdown(processedContent);

    // Add hover listeners
    addCitationListeners();

    // Show results
    inputSection.style.display = 'none';
    resultsSection.style.display = 'block';
}

function processCitationTags(content) {
    // Map source IDs to display numbers
    let citationNumber = 1;
    const citationMap = {};

    return content.replace(/\[\[Src:(\d+)\]\]/g, (match, srcNum) => {
        const sourceId = `src_${srcNum}`;

        if (!citationMap[sourceId]) {
            citationMap[sourceId] = citationNumber++;
        }

        const displayNum = citationMap[sourceId];
        return `<span class="citation" data-source-id="${sourceId}" data-num="${displayNum}">${displayNum}</span>`;
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

    // Paragraphs (for lines that aren't already wrapped)
    html = html.split('\n\n').map(p => {
        p = p.trim();
        if (!p) return '';
        if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<li')) {
            return p;
        }
        return `<p>${p}</p>`;
    }).join('\n');

    return html;
}

// ========== Tooltip Functions ==========

let hideTimeout = null;
let currentSourceId = null;

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
    currentSourceId = sourceId;
    const source = sourcesData[sourceId];

    if (source) {
        // Display page number or fallback
        const pageText = source.page_number || 'Source';
        tooltipPage.textContent = pageText;

        // Display title
        tooltipTitle.textContent = source.title || 'Annual Report';

        // Display raw text (source excerpt)
        const rawText = source.raw_text || 'No preview available';
        tooltipContent.textContent = rawText.length > 400
            ? rawText.substring(0, 400) + '...'
            : rawText;

        positionTooltipNear(e.target);
        tooltip.classList.add('visible');
    } else {
        console.warn(`Source not found: ${sourceId}`);
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

