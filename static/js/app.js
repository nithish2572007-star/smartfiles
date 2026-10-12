document.addEventListener('DOMContentLoaded', () => {
    const startScanBtn = document.getElementById('start-scan-btn');
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
                    pollScanStatus(data.scan_id);
                } else {
                    scanStatus.textContent = 'Error starting scan.';
                }
            } catch (error) {
                scanStatus.textContent = 'Network error.';
            }
        });
    }

    // Poll for progress so the page does not freeze
    async function pollScanStatus(scanId) {
        const interval = setInterval(async () => {
            const res = await fetch(`/api/scan/${scanId}/status`);
            const statusData = await res.json();

            if (statusData.status === 'in_progress') {
                scanStatus.textContent = `Scanning... Files found: ${statusData.total_scanned}`;
            } else if (statusData.status === 'completed') {
                clearInterval(interval);
                scanStatus.textContent = `Scan complete! Total files: ${statusData.total_scanned}`;
                loadStats(scanId);
            } else {
                clearInterval(interval);
                scanStatus.textContent = 'Scan failed.';
            }
        }, 1000); // Poll every second
    }

    async function loadStats(scanId) {
        const res = await fetch(`/api/stats/${scanId}`);
        const stats = await res.json();
        
        document.getElementById('total-files').textContent = stats.total_files;
        document.getElementById('total-size').textContent = stats.total_size;
        document.getElementById('duplicate-waste').textContent = stats.duplicate_waste;
        
        const categoryList = document.getElementById('category-list');
        categoryList.innerHTML = '';
        
        for (const [category, data] of Object.entries(stats.categories)) {
            const li = document.createElement('li');
            li.textContent = `${category}: ${data.count} files (${data.size} bytes)`;
            categoryList.appendChild(li);
        }
        
        statsContainer.style.display = 'block';
    }
});