/**
 * Citation UI - Frontend Application
 * 
 * Handles form submission, API calls, and citation hover tooltips.
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

// Store sources for tooltip display
let sourcesData = {};

// ========== Event Listeners ==========

// File input change
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        fileName.textContent = file.name;
    } else {
        fileName.textContent = 'Choose PDF file';
    }
});

// Form submit
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await runAnalysis();
});

// Back button
backBtn.addEventListener('click', () => {
    resultsSection.style.display = 'none';
    inputSection.style.display = 'flex';
});

// ========== Analysis Functions ==========

async function runAnalysis() {
    const companyName = companyInput.value.trim();
    if (!companyName) return;
    
    // Show loading state
    setLoading(true);
    
    try {
        // Build form data
        const formData = new FormData();
        formData.append('company_name', companyName);
        
        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
        }
        
        // Call API
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
        
        // Store sources for tooltips
        sourcesData = data.sources || {};
        
        // Display results
        displayResults(companyName, data.content, data.citation_count);
        
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

function displayResults(companyName, content, citationCount) {
    // Update header
    resultsTitle.textContent = `${companyName} - Stakeholder Analysis`;
    citationBadge.textContent = `${citationCount} citations`;
    
    // Process content - convert [[Src:XXX]] to clickable citations
    const processedContent = processCitations(content);
    
    // Render markdown-like formatting
    resultsContent.innerHTML = renderContent(processedContent);
    
    // Add hover listeners to citations
    addCitationListeners();
    
    // Show results section
    inputSection.style.display = 'none';
    resultsSection.style.display = 'block';
}

function processCitations(content) {
    // Replace [[Src:XXX]] with numbered citation spans
    let citationNumber = 1;
    const citationMap = {};
    
    return content.replace(/\[\[Src:(\d+)\]\]/g, (match, srcId) => {
        const fullId = `src_${srcId}`;
        if (!citationMap[fullId]) {
            citationMap[fullId] = citationNumber++;
        }
        return `<span class="citation" data-source-id="${fullId}">${citationMap[fullId]}</span>`;
    });
}

function renderContent(content) {
    // Basic markdown rendering
    let html = content;
    
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Lists
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // Paragraphs
    html = html.split('\n\n').map(p => {
        if (p.startsWith('<h') || p.startsWith('<ul')) return p;
        return `<p>${p}</p>`;
    }).join('\n');
    
    return html;
}

// ========== Tooltip Functions ==========

function addCitationListeners() {
    const citations = document.querySelectorAll('.citation');
    
    citations.forEach(citation => {
        citation.addEventListener('mouseenter', showTooltip);
        citation.addEventListener('mouseleave', hideTooltip);
        citation.addEventListener('mousemove', moveTooltip);
    });
}

function showTooltip(e) {
    const sourceId = e.target.dataset.sourceId;
    const source = sourcesData[sourceId];
    
    if (source) {
        tooltipPage.textContent = source.page_number || 'Source';
        tooltipTitle.textContent = source.title || 'Annual Report';
        tooltipContent.textContent = source.raw_text || 'No preview available';
        
        positionTooltip(e);
        tooltip.classList.add('visible');
    }
}

function hideTooltip() {
    tooltip.classList.remove('visible');
}

function moveTooltip(e) {
    positionTooltip(e);
}

function positionTooltip(e) {
    const padding = 16;
    const tooltipRect = tooltip.getBoundingClientRect();
    
    let x = e.clientX + padding;
    let y = e.clientY + padding;
    
    // Prevent overflow right
    if (x + tooltipRect.width > window.innerWidth - padding) {
        x = e.clientX - tooltipRect.width - padding;
    }
    
    // Prevent overflow bottom
    if (y + tooltipRect.height > window.innerHeight - padding) {
        y = e.clientY - tooltipRect.height - padding;
    }
    
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
}

// ========== Initialize ==========

// Focus company input on load
companyInput.focus();
