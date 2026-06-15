document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };

    // Load Stats & Charts
    try {
        const res = await fetch(`${API_BASE_URL}/v1/admin/stats`, { headers });
        if (res.status === 401 || res.status === 403) {
            window.location.href = 'dashboard.html';
            return;
        }
        
        if (!res.ok) {
            throw new Error(`HTTP Error ${res.status}`);
        }

        const data = await res.json();
        
        document.getElementById('total-users').textContent = data.total_users;
        document.getElementById('premium-users').textContent = data.premium_users;
        document.getElementById('predictions-today').textContent = data.predictions_today;
        document.getElementById('recommendations-today').textContent = data.recommendations_today;

        renderChart('usdChart', data.trends.usd, 'USD Price', '#10B981');
        renderChart('eurChart', data.trends.eur, 'EUR Price', '#3B82F6');
        
    } catch (error) {
        console.error("Admin API Error:", error);
        document.getElementById('total-users').textContent = 'Error loading data';
        document.getElementById('premium-users').textContent = 'Error loading data';
        document.getElementById('predictions-today').textContent = 'Error loading data';
        document.getElementById('recommendations-today').textContent = 'Error loading data';
    }

    // Load Users
    try {
        const res = await fetch(`${API_BASE_URL}/v1/admin/users`, { headers });
        const data = await res.json();
        const tbody = document.getElementById('user-table-body');
        
        if (data.status === 'success') {
            tbody.innerHTML = '';
            data.data.forEach(u => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${u.id}</td>
                    <td style="font-weight: 500;">${u.username}</td>
                    <td style="color: var(--text-muted);">${u.email}</td>
                    <td>
                        <select class="role-select" data-userid="${u.id}">
                            <option value="free" ${u.role==='free'?'selected':''}>Free</option>
                            <option value="premium" ${u.role==='premium'?'selected':''}>Premium</option>
                            <option value="admin" ${u.role==='admin'?'selected':''}>Admin</option>
                        </select>
                    </td>
                    <td style="display: flex; gap: 8px; border-bottom: none;">
                        <button class="btn btn-outline btn-sm update-role-btn" data-userid="${u.id}" style="padding: 6px 12px;">Save</button>
                        <button class="btn btn-outline btn-sm delete-user-btn" data-userid="${u.id}" style="padding: 6px 12px; color: #FF5252; border-color: rgba(255,82,82,0.3);">Drop</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Bind update buttons
            document.querySelectorAll('.update-role-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const userId = e.target.getAttribute('data-userid');
                    const select = document.querySelector(`.role-select[data-userid="${userId}"]`);
                    const newRole = select.value;
                    
                    const originalText = e.target.textContent;
                    e.target.textContent = 'Saving...';
                    try {
                        const updateRes = await fetch(`${API_BASE_URL}/v1/admin/users/${userId}/role`, {
                            method: 'PATCH',
                            headers,
                            body: JSON.stringify({ role: newRole })
                        });
                        if (updateRes.ok) {
                            e.target.textContent = 'Saved!';
                            e.target.style.borderColor = '#10B981';
                            e.target.style.color = '#10B981';
                            setTimeout(() => {
                                e.target.textContent = originalText;
                                e.target.style.borderColor = '';
                                e.target.style.color = '';
                            }, 2000);
                        } else {
                            const errData = await updateRes.json();
                            alert(errData.message || "Failed to update role.");
                            e.target.textContent = originalText;
                        }
                    } catch (err) {
                        console.error(err);
                        e.target.textContent = originalText;
                    }
                });
            });

            // Bind delete buttons
            document.querySelectorAll('.delete-user-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const userId = e.target.getAttribute('data-userid');
                    if (!confirm('Are you sure you want to drop this user? This action cannot be undone.')) {
                        return;
                    }
                    
                    const originalText = e.target.textContent;
                    e.target.textContent = 'Dropping...';
                    try {
                        const deleteRes = await fetch(`${API_BASE_URL}/v1/admin/users/${userId}`, {
                            method: 'DELETE',
                            headers
                        });
                        if (deleteRes.ok) {
                            e.target.closest('tr').remove();
                            const totalEl = document.getElementById('total-users');
                            if (totalEl && !isNaN(parseInt(totalEl.textContent))) {
                                totalEl.textContent = parseInt(totalEl.textContent) - 1;
                            }
                        } else {
                            const errData = await deleteRes.json();
                            alert(errData.message || "Failed to drop user.");
                            e.target.textContent = originalText;
                        }
                    } catch (err) {
                        console.error(err);
                        e.target.textContent = originalText;
                        alert("Connection error while dropping user.");
                    }
                });
            });
        }
    } catch (e) {
        console.error('Failed to load users', e);
    }

    function renderChart(canvasId, dataset, label, color) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        const labels = dataset.map(d => {
            const dateObj = new Date(d.date);
            return `${dateObj.getMonth()+1}/${dateObj.getDate()}`;
        });
        const prices = dataset.map(d => d.price);
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: prices,
                    borderColor: color,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: color
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1E293B',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { display: false } },
                    y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }
});
