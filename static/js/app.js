document.addEventListener('DOMContentLoaded', () => {
    const formatSize = (bytes) => {
        if (!bytes || bytes === 0) return '0 B';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    };

    // --- Scan Logic ---
    const startScanBtn = document.getElementById('start-scan-btn');
    const terminateScanBtn = document.getElementById('terminate-scan-btn');
    const scanPathInput = document.getElementById('scan-path');
    const scanStatus = document.getElementById('scan-status');
    const statsContainer = document.getElementById('stats-container');
    const skippedSection = document.getElementById('skipped-section');
    const skippedList = document.getElementById('skipped-list');

    if (startScanBtn) {
        startScanBtn.addEventListener('click', async () => {
            const rawInput = scanPathInput.value.trim();
            if (!rawInput) return alert('Please enter one or more folder paths (comma-separated).');

            const paths = rawInput.split(',').map(p => p.trim()).filter(Boolean);
            if (paths.length === 0) return alert('Please enter valid folder paths.');

            scanStatus.textContent = 'Starting scan...';
            if (skippedSection) skippedSection.style.display = 'none';
            if (skippedList) skippedList.innerHTML = '';
            
            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ paths: paths })
                });
                
                const data = await response.json();
                if (data.scan_id) {
                    if (terminateScanBtn) terminateScanBtn.style.display = 'inline-block';
                    pollScanStatus(data.scan_id);
                } else {
                    scanStatus.textContent = data.error || 'Error starting scan.';
                }
            } catch (error) {
                scanStatus.textContent = 'Network error starting scan.';
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
                    scanStatus.textContent = `Scanning... Files indexed: ${statusData.total_scanned}`;
                } else if (statusData.status === 'completed') {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    scanStatus.textContent = `Scan complete! Total files indexed: ${statusData.total_scanned}`;
                    renderSkipped(statusData.skipped_items);
                    loadStats(scanId);
                } else if (statusData.status === 'cancelled') {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    scanStatus.textContent = `Scan terminated by user. Total files indexed: ${statusData.total_scanned}`;
                    renderSkipped(statusData.skipped_items);
                    loadStats(scanId);
                } else {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    scanStatus.textContent = 'Scan failed.';
                    renderSkipped(statusData.skipped_items);
                }
            } catch (e) {
                clearInterval(interval);
                scanStatus.textContent = 'Network error while polling.';
            }
        }, 1000);
    }

    function renderSkipped(items) {
        if (!skippedSection || !skippedList) return;
        if (items && items.length > 0) {
            skippedList.innerHTML = '';
            items.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${item.path}</strong>: <em>${item.reason}</em>`;
                skippedList.appendChild(li);
            });
            skippedSection.style.display = 'block';
        } else {
            skippedSection.style.display = 'none';
        }
    }

    async function loadStats(scanId) {
        try {
            const res = await fetch(`/api/stats/${scanId}`);
            const stats = await res.json();

            document.getElementById('total-files').textContent = stats.total_files.toLocaleString();
            document.getElementById('total-size').textContent = formatSize(stats.total_size);
            document.getElementById('duplicate-waste').textContent = formatSize(stats.duplicate_waste);
            
            // Category Breakdown
            const categoryList = document.getElementById('category-list');
            categoryList.innerHTML = '';
            for (const [category, data] of Object.entries(stats.categories)) {
                const li = document.createElement('li');
                li.textContent = `${category}: ${data.count.toLocaleString()} files (${formatSize(data.size)})`;
                categoryList.appendChild(li);
            }
            
            // Largest Files Table
            const largestTbody = document.getElementById('largest-files-body');
            if (largestTbody) {
                largestTbody.innerHTML = '';
                if (stats.largest_files && stats.largest_files.length > 0) {
                    stats.largest_files.forEach(file => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td><strong>${file.name}</strong></td>
                            <td>${file.category}</td>
                            <td>${formatSize(file.size)}</td>
                            <td style="font-size: 0.85em; color: #555; word-break: break-all;">${file.path}</td>
                        `;
                        largestTbody.appendChild(tr);
                    });
                } else {
                    largestTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #888;">No files found.</td></tr>';
                }
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
            const keyword = document.getElementById('search-keyword').value.trim();
            const category = document.getElementById('search-category').value;
            const minSizeKb = document.getElementById('search-min-size') ? document.getElementById('search-min-size').value : '';
            const maxSizeKb = document.getElementById('search-max-size') ? document.getElementById('search-max-size').value : '';
            const startDateVal = document.getElementById('search-start-date') ? document.getElementById('search-start-date').value : '';
            const endDateVal = document.getElementById('search-end-date') ? document.getElementById('search-end-date').value : '';
            
            const params = new URLSearchParams();
            if (keyword) params.append('keyword', keyword);
            if (category) params.append('category', category);
            if (minSizeKb) params.append('min_size', Math.round(parseFloat(minSizeKb) * 1024));
            if (maxSizeKb) params.append('max_size', Math.round(parseFloat(maxSizeKb) * 1024));
            if (startDateVal) {
                const startTimestamp = new Date(startDateVal).getTime() / 1000;
                params.append('start_date', startTimestamp);
            }
            if (endDateVal) {
                // End of selected day (23:59:59)
                const endTimestamp = (new Date(endDateVal).getTime() / 1000) + 86399;
                params.append('end_date', endTimestamp);
            }
            
            try {
                const res = await fetch(`/api/search?${params.toString()}`);
                const results = await res.json();
                
                const tbody = document.getElementById('search-results-body');
                tbody.innerHTML = '';
                
                if (results.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #888;">No matching files found.</td></tr>';
                    return;
                }

                results.forEach(file => {
                    const tr = document.createElement('tr');
                    tr.id = `file-row-${file.id}`;
                    tr.innerHTML = `
                        <td><strong>${file.name}</strong></td>
                        <td>${file.category}</td>
                        <td>${formatSize(file.size)}</td>
                        <td style="font-size: 0.8em; color: #666; word-break: break-all;">${file.path}</td>
                        <td>
                            <button onclick="moveFilePrompt('${file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')" style="background: #27ae60; padding: 0.25rem 0.5rem; font-size: 0.8em; margin-right: 5px; color: white; border: none; border-radius: 3px; cursor: pointer;">Move</button>
                            <button onclick="trashFile('${file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')" style="background: #e74c3c; padding: 0.25rem 0.5rem; font-size: 0.8em; color: white; border: none; border-radius: 3px; cursor: pointer;">Trash</button>
                        </td>
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
                
                if (groups.length === 0) {
                    container.innerHTML += '<p style="color: #666;">No duplicates found in this scan.</p>';
                    container.style.display = 'block';
                    return;
                }

                groups.forEach((group, index) => {
                    const groupDiv = document.createElement('div');
                    groupDiv.style.borderBottom = '1px solid #eee';
                    groupDiv.style.paddingBottom = '1rem';
                    groupDiv.style.marginBottom = '1rem';
                    
                    let html = `<h4>Group ${index + 1} (${group.count} files) - Verified Wasted Space: ${formatSize(group.wasted_space)}</h4><ul style="line-height: 1.8;">`;
                    
                    group.files.forEach(file => {
                        const escapedPath = file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                        html += `
                            <li>
                                <code>${file.path}</code> 
                                <button onclick="moveFilePrompt('${escapedPath}')" style="background: #27ae60; padding: 0.2rem 0.5rem; margin-left: 10px; color: white; border: none; border-radius: 3px; cursor: pointer;">Move</button>
                                <button onclick="trashFile('${escapedPath}')" style="background: #e74c3c; padding: 0.2rem 0.5rem; margin-left: 5px; color: white; border: none; border-radius: 3px; cursor: pointer;">Trash</button>
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

// Global function for trashing files
window.trashFile = async function(path) {
    if (confirm(`Move file to recycle bin?\n\n${path}`)) {
        try {
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const data = await res.json();
            alert(data.message || data.error);
            // Refresh search results or duplicate view if possible
            const searchForm = document.getElementById('search-form');
            if (searchForm) {
                searchForm.dispatchEvent(new Event('submit'));
            }
            const loadDupBtn = document.getElementById('load-duplicates-btn');
            if (loadDupBtn && document.getElementById('dup-scan-id').value) {
                loadDupBtn.click();
            }
        } catch (error) {
            alert('Network error occurred during delete');
        }
    }
};

// Global function for moving / transferring files
window.moveFilePrompt = async function(path) {
    const destination = prompt(`Move or transfer file to new folder or path:\n\nSource: ${path}\nEnter target folder or new path:`);
    if (!destination) return;

    try {
        const res = await fetch('/api/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: path, destination: destination.trim() })
        });
        const data = await res.json();
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            alert(data.message);
            // Refresh search results or duplicate view if possible
            const searchForm = document.getElementById('search-form');
            if (searchForm) {
                searchForm.dispatchEvent(new Event('submit'));
            }
            const loadDupBtn = document.getElementById('load-duplicates-btn');
            if (loadDupBtn && document.getElementById('dup-scan-id').value) {
                loadDupBtn.click();
            }
        }
    } catch (error) {
        alert('Network error occurred during move');
    }
};
