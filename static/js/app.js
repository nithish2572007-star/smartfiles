document.addEventListener('DOMContentLoaded', () => {
    // --- Scan Logic ---
    const startScanBtn = document.getElementById('start-scan-btn');
    const terminateScanBtn = document.getElementById('terminate-scan-btn');
    const scanPathInput = document.getElementById('scan-path');
    const scanStatus = document.getElementById('scan-status');
    const statsContainer = document.getElementById('stats-container');

    if (startScanBtn) {
        startScanBtn.addEventListener('click', async () => {
            const path = scanPathInput.value;
            if (!path) return alert('Please enter a folder path');

            scanStatus.textContent = 'Starting scan...';
            
            try {
                // Start the background scan
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: path })
                });
                
                const data = await response.json();
                if (data.scan_id) {
                    if (terminateScanBtn) terminateScanBtn.style.display = 'inline-block';
                    pollScanStatus(data.scan_id);
                } else {
                    scanStatus.textContent = 'Error starting scan.';
                }
            } catch (error) {
                scanStatus.textContent = 'Network error.';
            }
        });
    }

    if (terminateScanBtn) {
        terminateScanBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/scan/terminate', { method: 'POST' });
                const data = await res.json();
                alert(data.message);
            } catch (error) {
                alert('Error terminating scan');
            }
        });
    }

    // Poll for progress so the page does not freeze
    async function pollScanStatus(scanId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/scan/${scanId}/status`);
                const statusData = await res.json();

                if (statusData.status === 'in_progress') {
                    scanStatus.textContent = `Scanning... Files found: ${statusData.total_scanned}`;
                } else if (statusData.status === 'completed') {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    scanStatus.textContent = `Scan complete! Total files: ${statusData.total_scanned}`;
                    loadStats(scanId);
                } else if (statusData.status === 'cancelled') {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    scanStatus.textContent = 'Scan terminated by user.';
                } else {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    scanStatus.textContent = 'Scan failed.';
                }
            } catch (e) {
                clearInterval(interval);
                scanStatus.textContent = 'Network error while polling.';
            }
        }, 1000); // Poll every second
    }

    async function loadStats(scanId) {
        try {
            const res = await fetch(`/api/stats/${scanId}`);
            const stats = await res.json();
            
            const formatSize = (bytes) => (bytes / (1024 * 1024)).toFixed(2) + ' MB';

            document.getElementById('total-files').textContent = stats.total_files;
            document.getElementById('total-size').textContent = formatSize(stats.total_size);
            document.getElementById('duplicate-waste').textContent = formatSize(stats.duplicate_waste);
            
            const categoryList = document.getElementById('category-list');
            categoryList.innerHTML = '';
            
            for (const [category, data] of Object.entries(stats.categories)) {
                const li = document.createElement('li');
                li.textContent = `${category}: ${data.count} files (${formatSize(data.size)})`;
                categoryList.appendChild(li);
            }
            
            statsContainer.style.display = 'block';
        } catch (e) {
            console.error('Error loading stats:', e);
        }
    }

    // --- Search Logic ---
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const keyword = document.getElementById('search-keyword').value;
            const category = document.getElementById('search-category').value;
            
            const params = new URLSearchParams();
            if (keyword) params.append('keyword', keyword);
            if (category) params.append('category', category);
            
            try {
                const res = await fetch(`/api/search?${params.toString()}`);
                const results = await res.json();
                
                const tbody = document.getElementById('search-results-body');
                tbody.innerHTML = '';
                
                results.forEach(file => {
                    const tr = document.createElement('tr');
                    const sizeMB = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
                    tr.innerHTML = `
                        <td>${file.name}</td>
                        <td>${file.category}</td>
                        <td>${sizeMB}</td>
                        <td style="font-size: 0.8em; color: #666;">${file.path}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (error) {
                console.error('Search error:', error);
            }
        });
    }

    // --- Duplicates & Advisory Cleanup Logic ---
    const loadDupBtn = document.getElementById('load-duplicates-btn');
    if (loadDupBtn) {
        loadDupBtn.addEventListener('click', async () => {
            const scanId = document.getElementById('dup-scan-id').value;
            if (!scanId) return alert('Enter a scan ID');
            
            try {
                const res = await fetch(`/api/duplicates/${scanId}`);
                const groups = await res.json();
                
                const container = document.getElementById('duplicates-container');
                container.innerHTML = '<h3>Duplicate Groups</h3>';
                
                groups.forEach((group, index) => {
                    const groupDiv = document.createElement('div');
                    groupDiv.style.borderBottom = '1px solid #eee';
                    groupDiv.style.paddingBottom = '1rem';
                    groupDiv.style.marginBottom = '1rem';
                    
                    const wastedMB = (group.wasted_space / (1024 * 1024)).toFixed(2) + ' MB';
                    let html = `<h4>Group ${index + 1} - Wasted Space: ${wastedMB}</h4><ul>`;
                    
                    group.files.forEach(file => {
                        html += `
                            <li>
                                ${file.path} 
                                <button onclick="trashFile('${file.path}')" style="background: #e74c3c; padding: 0.2rem 0.5rem; margin-left: 10px; color: white; border: none; border-radius: 3px; cursor: pointer;">Trash</button>
                            </li>
                        `;
                    });
                    
                    html += '</ul>';
                    groupDiv.innerHTML = html;
                    container.appendChild(groupDiv);
                });
                
                container.style.display = 'block';
            } catch (error) {
                console.error('Duplicates error:', error);
            }
        });
    }
});

// Global function for the inline trash buttons
window.trashFile = async function(path) {
    if (confirm(`Move to recycle bin?\n${path}`)) {
        try {
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const data = await res.json();
            alert(data.message || data.error);
        } catch (error) {
            alert('Network error occurred');
        }
    }
};
