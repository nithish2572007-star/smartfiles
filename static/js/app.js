document.addEventListener('DOMContentLoaded', () => {
    // --- Utility: Format File Sizes ---
    const formatSize = (bytes) => {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    // --- Toast Notifications ---
    const toastContainer = document.getElementById('toast-container');
    window.showToast = (message, type = 'info') => {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let iconSvg = '';
        if (type === 'success') {
            iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="#10b981"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
        } else if (type === 'error') {
            iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="#ef4444"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>';
        } else {
            iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="#3b82f6"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>';
        }

        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                ${iconSvg}
                <span>${message}</span>
            </div>
            <button style="background: none; border: none; color: #94a3b8; cursor: pointer; padding: 0 4px; font-size: 1rem;" onclick="this.parentElement.remove()">&times;</button>
        `;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(10px)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    };

    // --- Accessible Custom Modal Dialog (<dialog>) ---
    const modal = document.getElementById('app-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const modalCloseX = document.getElementById('modal-close-x');
    const modalBtnCancel = document.getElementById('modal-btn-cancel');
    const modalBtnConfirm = document.getElementById('modal-btn-confirm');

    window.showConfirmModal = (title, message, confirmText = 'Confirm', isDanger = false) => {
        return new Promise((resolve) => {
            if (!modal) return resolve(confirm(message));

            modalTitle.textContent = title;
            modalBody.innerHTML = `<p style="margin: 0; color: var(--text-main); font-size: 0.95rem;">${message}</p>`;
            modalBtnConfirm.textContent = confirmText;
            modalBtnConfirm.className = isDanger ? 'btn btn-danger' : 'btn btn-primary';

            const onConfirm = () => { cleanup(); resolve(true); modal.close(); };
            const onCancel = () => { cleanup(); resolve(false); modal.close(); };
            const cleanup = () => {
                modalBtnConfirm.removeEventListener('click', onConfirm);
                modalBtnCancel.removeEventListener('click', onCancel);
                if (modalCloseX) modalCloseX.removeEventListener('click', onCancel);
            };

            modalBtnConfirm.addEventListener('click', onConfirm);
            modalBtnCancel.addEventListener('click', onCancel);
            if (modalCloseX) modalCloseX.addEventListener('click', onCancel);

            modal.showModal();
        });
    };

    window.showPromptModal = (title, message, defaultValue = '', confirmText = 'Submit') => {
        return new Promise((resolve) => {
            if (!modal) return resolve(prompt(message, defaultValue));

            modalTitle.textContent = title;
            modalBody.innerHTML = `
                <p style="margin: 0 0 0.75rem; color: var(--text-main); font-size: 0.95rem;">${message}</p>
                <input type="text" id="modal-prompt-input" value="${defaultValue}" style="width: 100%; box-sizing: border-box;">
            `;
            modalBtnConfirm.textContent = confirmText;
            modalBtnConfirm.className = 'btn btn-primary';

            const inputElem = document.getElementById('modal-prompt-input');

            const onConfirm = () => {
                const val = inputElem ? inputElem.value : '';
                cleanup();
                resolve(val);
                modal.close();
            };
            const onCancel = () => { cleanup(); resolve(null); modal.close(); };
            const cleanup = () => {
                modalBtnConfirm.removeEventListener('click', onConfirm);
                modalBtnCancel.removeEventListener('click', onCancel);
                if (modalCloseX) modalCloseX.removeEventListener('click', onCancel);
            };

            modalBtnConfirm.addEventListener('click', onConfirm);
            modalBtnCancel.addEventListener('click', onCancel);
            if (modalCloseX) modalCloseX.addEventListener('click', onCancel);

            modal.showModal();
            if (inputElem) {
                inputElem.focus();
                inputElem.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') { e.preventDefault(); onConfirm(); }
                });
            }
        });
    };

    // --- Clipboard Helper ---
    window.copyPath = (text) => {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Path copied to clipboard', 'info');
        }).catch(() => {
            showToast('Failed to copy path', 'error');
        });
    };

    // ==========================================
    // 1. Dashboard & Scanner Logic
    // ==========================================
    const startScanBtn = document.getElementById('start-scan-btn');
    const terminateScanBtn = document.getElementById('terminate-scan-btn');
    const scanPathInput = document.getElementById('scan-path');
    const scanStatus = document.getElementById('scan-status');
    const scanProgress = document.getElementById('scan-progress-container');
    const statsContainer = document.getElementById('stats-container');
    const skippedSection = document.getElementById('skipped-section');
    const skippedList = document.getElementById('skipped-list');
    const skippedCount = document.getElementById('skipped-count');

    // Preset pills click handler
    document.querySelectorAll('.preset-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const path = chip.getAttribute('data-path');
            if (scanPathInput) {
                scanPathInput.value = path;
                scanPathInput.focus();
            }
        });
    });

    if (startScanBtn) {
        startScanBtn.addEventListener('click', async () => {
            const rawInput = scanPathInput.value.trim();
            if (!rawInput) {
                showToast('Please enter one or more folder paths.', 'error');
                return;
            }

            const paths = rawInput.split(',').map(p => p.trim()).filter(Boolean);
            if (paths.length === 0) return;

            scanStatus.textContent = 'Submitting scan request to worker pool...';
            if (scanProgress) scanProgress.style.display = 'block';
            if (skippedSection) skippedSection.style.display = 'none';
            if (skippedList) skippedList.innerHTML = '';
            startScanBtn.disabled = true;

            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ paths: paths })
                });

                const data = await response.json();
                if (data.scan_id) {
                    showToast(data.message || 'Scan registered', 'info');
                    if (terminateScanBtn) terminateScanBtn.style.display = 'inline-flex';
                    pollScanStatus(data.scan_id);
                } else {
                    scanStatus.textContent = data.error || 'Error starting scan.';
                    if (scanProgress) scanProgress.style.display = 'none';
                    startScanBtn.disabled = false;
                }
            } catch (error) {
                scanStatus.textContent = 'Network error starting scan.';
                if (scanProgress) scanProgress.style.display = 'none';
                startScanBtn.disabled = false;
            }
        });
    }

    if (terminateScanBtn) {
        terminateScanBtn.addEventListener('click', async () => {
            const confirmed = await showConfirmModal(
                'Terminate Active Scan',
                'Are you sure you want to cancel the currently running scan? Files indexed so far will be preserved.',
                'Terminate',
                true
            );
            if (!confirmed) return;

            try {
                const res = await fetch('/api/scan/terminate', { method: 'POST' });
                const data = await res.json();
                showToast(data.message, 'warning');
            } catch (error) {
                showToast('Error sending termination signal', 'error');
            }
        });
    }

    async function pollScanStatus(scanId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/scan/${scanId}/status`);
                const statusData = await res.json();

                if (statusData.status === 'in_progress') {
                    scanStatus.innerHTML = `Scanning in progress... <strong>${statusData.total_scanned.toLocaleString()}</strong> files indexed`;
                } else if (statusData.status === 'completed') {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    if (startScanBtn) startScanBtn.disabled = false;
                    if (scanProgress) scanProgress.style.display = 'none';
                    scanStatus.innerHTML = `<span style="color: var(--success); font-weight: 600;">✓ Scan complete!</span> Total files indexed: <strong>${statusData.total_scanned.toLocaleString()}</strong>`;
                    showToast(`Scan complete (${statusData.total_scanned.toLocaleString()} files)`, 'success');
                    renderSkipped(statusData.skipped_items);
                    loadStats(scanId);
                } else if (statusData.status === 'cancelled') {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    if (startScanBtn) startScanBtn.disabled = false;
                    if (scanProgress) scanProgress.style.display = 'none';
                    scanStatus.innerHTML = `<span style="color: var(--warning); font-weight: 600;">Scan cancelled by user.</span> Indexed: <strong>${statusData.total_scanned.toLocaleString()}</strong>`;
                    showToast('Scan terminated', 'warning');
                    renderSkipped(statusData.skipped_items);
                    loadStats(scanId);
                } else {
                    clearInterval(interval);
                    if (terminateScanBtn) terminateScanBtn.style.display = 'none';
                    if (startScanBtn) startScanBtn.disabled = false;
                    if (scanProgress) scanProgress.style.display = 'none';
                    scanStatus.innerHTML = `<span style="color: var(--danger); font-weight: 600;">Scan failed:</span> ${statusData.error_log || 'Unknown error'}`;
                    showToast('Scan encountered an error', 'error');
                    renderSkipped(statusData.skipped_items);
                }
            } catch (e) {
                clearInterval(interval);
                if (startScanBtn) startScanBtn.disabled = false;
                if (scanProgress) scanProgress.style.display = 'none';
                scanStatus.textContent = 'Connection interrupted while polling.';
            }
        }, 1000);
    }

    function renderSkipped(items) {
        if (!skippedSection || !skippedList) return;
        if (items && items.length > 0) {
            skippedList.innerHTML = '';
            if (skippedCount) skippedCount.textContent = items.length;
            items.forEach(item => {
                const li = document.createElement('li');
                li.style.marginBottom = '4px';
                li.innerHTML = `<code class="path-code">${item.path}</code> &mdash; <span style="color: var(--warning-text); font-style: italic;">${item.reason}</span>`;
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

            const totalFilesEl = document.getElementById('total-files');
            const totalSizeEl = document.getElementById('total-size');
            const dupWasteEl = document.getElementById('duplicate-waste');

            if (totalFilesEl) totalFilesEl.textContent = stats.total_files.toLocaleString();
            if (totalSizeEl) totalSizeEl.textContent = formatSize(stats.total_size);
            if (dupWasteEl) dupWasteEl.textContent = formatSize(stats.duplicate_waste);

            // Render visual category distribution bar & legend
            renderCategoryDistribution(stats.categories, stats.total_size);

            // Render largest files table
            const largestTbody = document.getElementById('largest-files-body');
            if (largestTbody) {
                largestTbody.innerHTML = '';
                if (stats.largest_files && stats.largest_files.length > 0) {
                    stats.largest_files.forEach(file => {
                        const tr = document.createElement('tr');
                        const escapedPath = file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                        tr.innerHTML = `
                            <td>
                                <div class="file-name">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="#64748b"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                                    ${file.name}
                                </div>
                            </td>
                            <td><span class="badge badge-${file.category}">${file.category}</span></td>
                            <td><strong>${formatSize(file.size)}</strong></td>
                            <td>
                                <span class="path-code">${file.path}</span>
                                <button type="button" class="copy-btn" title="Copy Path" onclick="copyPath('${escapedPath}')">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                                </button>
                            </td>
                        `;
                        largestTbody.appendChild(tr);
                    });
                } else {
                    largestTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No files found.</td></tr>';
                }
            }

            if (statsContainer) statsContainer.style.display = 'block';
        } catch (e) {
            console.error('Error loading stats:', e);
        }
    }

    function renderCategoryDistribution(categories, totalSize) {
        const barContainer = document.getElementById('category-distribution-bar');
        const legendContainer = document.getElementById('category-legend');
        if (!barContainer || !legendContainer) return;

        barContainer.innerHTML = '';
        legendContainer.innerHTML = '';

        const catColors = {
            'Documents': '#2563eb',
            'Images': '#7c3aed',
            'Video': '#db2777',
            'Audio': '#ea580c',
            'Code': '#059669',
            'Archives': '#0891b2',
            'Others': '#64748b'
        };

        const total = totalSize || 1;

        for (const [cat, data] of Object.entries(categories)) {
            const pct = Math.max(0.5, ((data.size || 0) / total) * 100);
            const color = catColors[cat] || '#64748b';

            // Segment in distribution bar
            const segment = document.createElement('div');
            segment.className = 'distribution-segment';
            segment.style.width = `${pct}%`;
            segment.style.backgroundColor = color;
            segment.title = `${cat}: ${formatSize(data.size)} (${pct.toFixed(1)}%)`;
            barContainer.appendChild(segment);

            // Legend item
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';
            legendItem.innerHTML = `
                <span class="legend-dot" style="background-color: ${color};"></span>
                <strong>${cat}:</strong> ${data.count.toLocaleString()} files <span style="color: var(--text-muted);">(${formatSize(data.size)})</span>
            `;
            legendContainer.appendChild(legendItem);
        }
    }

    // Auto-load latest stats on dashboard if available
    if (document.getElementById('total-files')) {
        fetch('/api/scans').then(r => r.json()).then(scans => {
            if (scans && scans.length > 0 && scans[0].id) {
                loadStats(scans[0].id);
            }
        }).catch(() => {});
    }

    // ==========================================
    // 2. Search Page Logic
    // ==========================================
    const searchForm = document.getElementById('search-form');
    const searchResetBtn = document.getElementById('search-reset-btn');
    const resultsCountEl = document.getElementById('results-count');

    if (searchResetBtn && searchForm) {
        searchResetBtn.addEventListener('click', () => {
            searchForm.reset();
            const tbody = document.getElementById('search-results-body');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">Filters reset. Enter search criteria above.</td></tr>';
            }
            if (resultsCountEl) resultsCountEl.textContent = '0';
        });
    }

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
                params.append('start_date', new Date(startDateVal).getTime() / 1000);
            }
            if (endDateVal) {
                params.append('end_date', (new Date(endDateVal).getTime() / 1000) + 86399);
            }

            try {
                const res = await fetch(`/api/search?${params.toString()}`);
                const results = await res.json();

                const tbody = document.getElementById('search-results-body');
                tbody.innerHTML = '';
                if (resultsCountEl) resultsCountEl.textContent = results.length;

                if (results.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No matching files found. Try adjusting your query or filter ranges.</td></tr>';
                    return;
                }

                results.forEach(file => {
                    const tr = document.createElement('tr');
                    tr.id = `file-row-${file.id}`;
                    const escapedPath = file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                    tr.innerHTML = `
                        <td>
                            <div class="file-name">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="#64748b"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                                <strong>${file.name}</strong>
                            </div>
                        </td>
                        <td><span class="badge badge-${file.category}">${file.category}</span></td>
                        <td><strong>${formatSize(file.size)}</strong></td>
                        <td>
                            <span class="path-code">${file.path}</span>
                            <button type="button" class="copy-btn" title="Copy Path" onclick="copyPath('${escapedPath}')">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                            </button>
                        </td>
                        <td>
                            <div style="display: flex; gap: 6px;">
                                <button type="button" class="btn btn-secondary btn-sm" onclick="moveFilePrompt('${escapedPath}')">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M10 9h4V6h3l-5-5-5 5h3v3zm-1 1H6V7l-5 5 5 5v-3h3v-4zm14 2l-5-5v3h-3v4h3v3l5-5zm-9 3h-4v3H7l5 5 5-5h-3v-3z"/></svg>
                                    Move
                                </button>
                                <button type="button" class="btn btn-danger btn-sm" onclick="trashFile('${escapedPath}')">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-3.5l-1-1zM18 7H6v12c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7z"/></svg>
                                    Trash
                                </button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (error) {
                showToast('Failed to perform search query', 'error');
            }
        });
    }

    // ==========================================
    // 3. Duplicates Page Logic
    // ==========================================
    const dupScanSelect = document.getElementById('dup-scan-select');
    const dupScanIdInput = document.getElementById('dup-scan-id');
    const loadDupBtn = document.getElementById('load-duplicates-btn');
    const dupSummaryBanner = document.getElementById('duplicate-summary-banner');
    const dupTotalWasteEl = document.getElementById('dup-total-waste');
    const dupGroupsCountEl = document.getElementById('dup-groups-count');

    // Populate recent scans dropdown
    if (dupScanSelect) {
        fetch('/api/scans').then(r => r.json()).then(scans => {
            dupScanSelect.innerHTML = '';
            if (!scans || scans.length === 0) {
                dupScanSelect.innerHTML = '<option value="">No scans found. Run a scan from Dashboard first.</option>';
                return;
            }
            scans.forEach((s, idx) => {
                const opt = document.createElement('option');
                opt.value = s.id;
                const dateStr = s.started_at ? new Date(s.started_at).toLocaleString() : '';
                opt.textContent = `Scan #${s.id} - ${s.root_path} (${s.total_scanned} files) [${s.status}]`;
                if (idx === 0) opt.selected = true;
                dupScanSelect.appendChild(opt);
            });
            if (dupScanIdInput && scans[0]) {
                dupScanIdInput.value = scans[0].id;
            }
        }).catch(() => {
            dupScanSelect.innerHTML = '<option value="">Failed to load scans</option>';
        });

        dupScanSelect.addEventListener('change', () => {
            if (dupScanIdInput) dupScanIdInput.value = dupScanSelect.value;
        });
    }

    if (loadDupBtn) {
        loadDupBtn.addEventListener('click', async () => {
            const scanId = dupScanIdInput ? dupScanIdInput.value : (dupScanSelect ? dupScanSelect.value : '');
            if (!scanId) {
                showToast('Please select or enter a valid Scan ID', 'error');
                return;
            }

            loadDupBtn.disabled = true;
            loadDupBtn.innerHTML = 'Analyzing...';

            try {
                const res = await fetch(`/api/duplicates/${scanId}`);
                const groups = await res.json();

                const container = document.getElementById('duplicates-container');
                container.innerHTML = '';

                if (!groups || groups.length === 0) {
                    if (dupSummaryBanner) dupSummaryBanner.style.display = 'none';
                    container.innerHTML = `
                        <div class="card" style="text-align: center; padding: 3rem 1.5rem;">
                            <div style="width: 56px; height: 56px; margin: 0 auto 1rem; border-radius: var(--radius-full); background: var(--success-light); display: flex; align-items: center; justify-content: center;">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="#059669"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                            </div>
                            <h3 style="margin: 0 0 0.5rem; color: var(--text-main);">Zero Duplicates Found</h3>
                            <p style="margin: 0; color: var(--text-muted);">All scanned files in this run have distinct content verified byte-by-byte.</p>
                        </div>
                    `;
                    loadDupBtn.disabled = false;
                    loadDupBtn.innerHTML = 'Find Duplicates';
                    return;
                }

                let totalWaste = 0;
                groups.forEach(g => { totalWaste += (g.wasted_space || 0); });

                if (dupSummaryBanner) {
                    dupSummaryBanner.style.display = 'flex';
                    if (dupTotalWasteEl) dupTotalWasteEl.textContent = formatSize(totalWaste);
                    if (dupGroupsCountEl) dupGroupsCountEl.textContent = `${groups.length} Duplicate Group${groups.length > 1 ? 's' : ''}`;
                }

                groups.forEach((group, index) => {
                    const groupCard = document.createElement('div');
                    groupCard.className = 'duplicate-group-card';

                    let itemsHtml = '';
                    group.files.forEach((file, fileIdx) => {
                        const escapedPath = file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                        const isOriginal = (fileIdx === 0);

                        itemsHtml += `
                            <div class="duplicate-item">
                                <div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden;">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#64748b" style="flex-shrink: 0;"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                                    <span class="path-code">${file.path}</span>
                                    <button type="button" class="copy-btn" title="Copy Path" onclick="copyPath('${escapedPath}')">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                                    </button>
                                    ${isOriginal ? '<span class="original-tag">Original (Keep)</span>' : '<span style="font-size: 0.72rem; color: var(--text-muted); margin-left: 6px;">Duplicate Copy</span>'}
                                </div>
                                <div style="display: flex; gap: 6px; flex-shrink: 0;">
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="moveFilePrompt('${escapedPath}')">Move</button>
                                    <button type="button" class="btn btn-danger btn-sm" onclick="trashFile('${escapedPath}')">Trash</button>
                                </div>
                            </div>
                        `;
                    });

                    groupCard.innerHTML = `
                        <div class="group-header">
                            <h4>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="#ef4444"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
                                Group ${index + 1} (${group.count} copies &bull; ${formatSize(group.size)} each)
                            </h4>
                            <span class="group-waste-badge">Recoverable: ${formatSize(group.wasted_space)}</span>
                        </div>
                        <div>${itemsHtml}</div>
                    `;
                    container.appendChild(groupCard);
                });

                showToast(`Found ${groups.length} duplicate group(s)`, 'info');
            } catch (error) {
                showToast('Failed to retrieve duplicate files', 'error');
            } finally {
                loadDupBtn.disabled = false;
                loadDupBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 14z"/></svg>
                    Find Duplicates
                `;
            }
        });
    }

    // ==========================================
    // 4. File Actions: Move & Trash
    // ==========================================
    window.trashFile = async function(path) {
        const confirmed = await showConfirmModal(
            'Move to Recycle Bin',
            `Are you sure you want to move this file to the system trash bin?<br><br><code class="path-code">${path}</code>`,
            'Move to Trash',
            true
        );
        if (!confirmed) return;

        try {
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const data = await res.json();
            if (data.error) {
                showToast(data.error, 'error');
            } else {
                showToast(data.message || 'File sent to recycle bin', 'success');
                // Auto refresh active search or duplicate view
                if (searchForm) {
                    searchForm.dispatchEvent(new Event('submit'));
                }
                if (loadDupBtn && dupScanIdInput && dupScanIdInput.value) {
                    loadDupBtn.click();
                }
            }
        } catch (error) {
            showToast('Network error while deleting file', 'error');
        }
    };

    window.moveFilePrompt = async function(path) {
        const destination = await showPromptModal(
            'Move / Transfer File',
            `Specify the target directory or new path for:<br><code class="path-code">${path}</code>`,
            '',
            'Move File'
        );
        if (!destination || !destination.trim()) return;

        try {
            const res = await fetch('/api/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: path, destination: destination.trim() })
            });
            const data = await res.json();
            if (data.error) {
                showToast(data.error, 'error');
            } else {
                showToast(data.message || 'File moved successfully', 'success');
                if (searchForm) {
                    searchForm.dispatchEvent(new Event('submit'));
                }
                if (loadDupBtn && dupScanIdInput && dupScanIdInput.value) {
                    loadDupBtn.click();
                }
            }
        } catch (error) {
            showToast('Network error while moving file', 'error');
        }
    };
});
