/**
 * Resume IQ — Core App JavaScript
 * Provides global state management, persistent active resume tracking,
 * topbar switcher, API request helpers, and UI notifications.
 */

const ResumeIQ = {
    currentResumeId: localStorage.getItem('resumeiq_current_resume_id') || null,
    currentFileName: localStorage.getItem('resumeiq_current_filename') || null,
    resumesList: [],

    setResume(id, filename) {
        this.currentResumeId = id;
        this.currentFileName = filename;
        if (id) localStorage.setItem('resumeiq_current_resume_id', id);
        else localStorage.removeItem('resumeiq_current_resume_id');
        if (filename) localStorage.setItem('resumeiq_current_filename', filename);
        else localStorage.removeItem('resumeiq_current_filename');
        this.updateActiveResumeUI();
    },

    clearResume() {
        this.currentResumeId = null;
        this.currentFileName = null;
        localStorage.removeItem('resumeiq_current_resume_id');
        localStorage.removeItem('resumeiq_current_filename');
        this.updateActiveResumeUI();
    },

    // Generic API caller
    async apiCall(endpoint, method = 'GET', data = null, isFormData = false) {
        const options = { method };

        if (data) {
            if (isFormData) {
                options.body = data;
            } else {
                options.headers = { 'Content-Type': 'application/json' };
                options.body = JSON.stringify(data);
            }
        }

        try {
            const response = await fetch(endpoint, options);

            // Handle unauthorized redirects cleanly
            if (response.status === 401 && !endpoint.includes('/api/auth/login') && !endpoint.includes('/api/auth/register')) {
                const currentPath = window.location.pathname;
                if (currentPath !== '/' && currentPath !== '/login' && currentPath !== '/register' && !currentPath.startsWith('/forgot-password') && !currentPath.startsWith('/reset-password')) {
                    window.location.href = `/login?next=${encodeURIComponent(currentPath)}`;
                    return null;
                }
            }

            const resData = await response.json();

            if (!response.ok) {
                throw new Error(resData.error || `Request failed with status ${response.status}`);
            }

            return resData;
        } catch (err) {
            console.error(`API Error on ${endpoint}:`, err);
            throw err;
        }
    },

    // Synchronize active resume between Flask backend and browser
    async syncActiveResume() {
        try {
            // First check backend active resume
            const activeRes = await this.apiCall('/api/active-resume');
            if (activeRes && activeRes.has_resume) {
                this.setResume(activeRes.resume.id, activeRes.resume.filename);
            } else if (this.currentResumeId) {
                // Try to set backend to local resume if exists
                try {
                    const setRes = await this.apiCall('/api/set-active-resume', 'POST', { resume_id: this.currentResumeId });
                    if (setRes.success) {
                        this.setResume(setRes.resume.id, setRes.resume.filename);
                    }
                } catch (e) {
                    this.clearResume();
                }
            } else {
                this.clearResume();
            }

            // Load list of all resumes for dropdown
            await this.refreshResumesList();
        } catch (e) {
            console.warn("Could not sync active resume:", e);
        }
    },

    async refreshResumesList() {
        try {
            const data = await this.apiCall('/api/resumes');
            this.resumesList = data.resumes || [];
            this.renderTopbarResumeWidget();
        } catch (e) {
            console.warn("Could not fetch resumes list:", e);
        }
    },

    // Dynamically insert or update active resume widget in topbar
    renderTopbarResumeWidget() {
        const topbar = document.querySelector('.topbar');
        if (!topbar) return;

        let widget = document.getElementById('topbar-active-resume-widget');
        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'topbar-active-resume-widget';
            widget.className = 'd-flex align-items-center gap-2';

            // Find right action container or append
            const rightContainer = topbar.querySelector('.d-flex.align-items-center:last-child');
            if (rightContainer && rightContainer !== topbar.firstElementChild) {
                rightContainer.prepend(widget);
            } else {
                topbar.appendChild(widget);
            }
        }

        if (!this.currentResumeId || !this.currentFileName) {
            widget.innerHTML = `
                <div class="active-resume-pill empty-pill">
                    <i class="bi bi-file-earmark-x text-muted me-1"></i>
                    <span class="text-secondary small">No Resume Active</span>
                </div>
            `;
            return;
        }

        // Build dropdown menu items
        let menuItemsHtml = '';
        if (this.resumesList.length > 0) {
            menuItemsHtml = this.resumesList.map(r => {
                const isActive = (r.id === Number(this.currentResumeId));
                const scoreText = r.overall_score !== null ? `<span class="badge bg-primary-soft text-cyan ms-auto">${r.overall_score}</span>` : '';
                return `
                    <li>
                        <a class="dropdown-item d-flex align-items-center gap-2 py-2 ${isActive ? 'active-dropdown-item' : ''}" 
                           href="javascript:void(0)" onclick="ResumeIQ.switchActiveResume(${r.id})">
                            <i class="bi ${isActive ? 'bi-check-circle-fill text-success' : 'bi-file-earmark-text text-secondary'}"></i>
                            <span class="text-truncate" style="max-width: 170px;">${r.filename}</span>
                            ${scoreText}
                        </a>
                    </li>
                `;
            }).join('');
        }

        widget.innerHTML = `
            <div class="dropdown">
                <button class="active-resume-btn dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-file-earmark-person-fill text-cyan"></i>
                    <span class="active-resume-name text-truncate" style="max-width: 180px;">${this.currentFileName}</span>
                </button>
                <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow-lg" style="min-width: 260px;">
                    <li class="dropdown-header text-uppercase small text-muted">Uploaded Resumes</li>
                    ${menuItemsHtml}
                    <li><hr class="dropdown-divider border-secondary"></li>
                    <li>
                        <a class="dropdown-item py-2 text-primary d-flex align-items-center gap-2" href="/analysis">
                            <i class="bi bi-cloud-upload"></i> Upload Another Resume
                        </a>
                    </li>
                    <li>
                        <a class="dropdown-item py-2 text-danger d-flex align-items-center gap-2" href="javascript:void(0)" onclick="ResumeIQ.confirmDeleteResume(${this.currentResumeId}, '${this.currentFileName.replace(/'/g, "\\'")}')">
                            <i class="bi bi-trash"></i> Delete Active Resume
                        </a>
                    </li>
                </ul>
            </div>
        `;
    },

    updateActiveResumeUI() {
        this.renderTopbarResumeWidget();

        // Update any on-page filename indicators
        const nameBadges = document.querySelectorAll('.js-active-filename');
        nameBadges.forEach(el => {
            el.innerText = this.currentFileName || 'No resume selected';
        });

        // Hide/show alerts for empty state
        const noResumeAlerts = document.querySelectorAll('#noResumeAlert, .js-no-resume-alert');
        noResumeAlerts.forEach(el => {
            if (this.currentResumeId) {
                el.classList.add('d-none');
            } else {
                el.classList.remove('d-none');
            }
        });
    },

    async switchActiveResume(resumeId) {
        try {
            const res = await this.apiCall('/api/set-active-resume', 'POST', { resume_id: resumeId });
            if (res.success) {
                this.setResume(res.resume.id, res.resume.filename);
                this.showToast(`Switched active resume to ${res.resume.filename}`, "success");
                // Reload current page to reflect new active resume
                setTimeout(() => {
                    window.location.reload();
                }, 400);
            }
        } catch (e) {
            this.showToast("Failed to switch resume.", "error");
        }
    },

    async confirmDeleteResume(resumeId, filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"? All associated analyses, matches, and roadmaps will be removed.`)) {
            return;
        }

        try {
            const res = await this.apiCall(`/api/delete-resume/${resumeId}`, 'DELETE');
            if (res.success) {
                this.showToast(res.message || "Resume deleted successfully.", "success");
                if (res.has_resumes && res.active_resume) {
                    this.setResume(res.active_resume.id, res.active_resume.filename);
                } else {
                    this.clearResume();
                }
                setTimeout(() => {
                    window.location.href = '/analysis';
                }, 500);
            }
        } catch (e) {
            this.showToast(e.message || "Failed to delete resume.", "error");
        }
    },

    // Toast Notification Banner
    showToast(message, type = 'info') {
        let toastContainer = document.getElementById('resumeiq-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'resumeiq-toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                bottom: 25px;
                right: 25px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        const colorMap = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#6366f1'
        };

        toast.style.cssText = `
            background: rgba(15, 23, 42, 0.95);
            border-left: 4px solid ${colorMap[type] || colorMap.info};
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 10px;
            backdrop-filter: blur(10px);
            animation: slideIn 0.3s ease forwards;
        `;

        toast.innerHTML = `<span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    // Render user profile menu in topbar
    async renderUserMenu() {
        const topbar = document.querySelector('.topbar');
        if (!topbar) return;

        let userWidget = document.getElementById('topbar-user-menu-widget');
        if (!userWidget) {
            userWidget = document.createElement('div');
            userWidget.id = 'topbar-user-menu-widget';
            userWidget.className = 'd-flex align-items-center ms-2';

            const rightContainer = topbar.querySelector('.d-flex.align-items-center:last-child');
            if (rightContainer && rightContainer !== topbar.firstElementChild) {
                rightContainer.appendChild(userWidget);
            } else {
                topbar.appendChild(userWidget);
            }
        }

        try {
            const auth = await this.apiCall('/api/auth/me');
            if (auth && auth.authenticated && auth.user) {
                const u = auth.user;
                const initials = (u.full_name || 'User')
                    .trim()
                    .split(/\s+/)
                    .map(n => n[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase();

                const firstName = u.full_name.trim().split(/\s+/)[0];

                userWidget.innerHTML = `
                    <div class="dropdown">
                        <button class="user-menu-btn dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" title="User Menu">
                            <div class="user-avatar">${initials}</div>
                            <span class="text-white small fw-600 d-none d-md-inline pe-1">${firstName}</span>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow-lg" style="min-width: 220px;">
                            <li class="px-3 py-2 border-bottom border-secondary border-opacity-25">
                                <div class="fw-600 text-white">${u.full_name}</div>
                                <div class="small text-muted text-truncate">${u.email}</div>
                            </li>
                            <li>
                                <a class="dropdown-item py-2 d-flex align-items-center gap-2 mt-1" href="/profile">
                                    <i class="bi bi-person-circle text-primary"></i> Profile & Settings
                                </a>
                            </li>
                            <li>
                                <a class="dropdown-item py-2 d-flex align-items-center gap-2" href="/dashboard">
                                    <i class="bi bi-grid-1x2 text-cyan"></i> Dashboard
                                </a>
                            </li>
                            <li><hr class="dropdown-divider border-secondary border-opacity-25"></li>
                            <li>
                                <a class="dropdown-item py-2 text-danger d-flex align-items-center gap-2" href="/logout">
                                    <i class="bi bi-box-arrow-right"></i> Sign Out
                                </a>
                            </li>
                        </ul>
                    </div>
                `;
            }
        } catch (e) {
            console.warn("Could not render user menu:", e);
        }
    }
};

// Expose globally on window
if (typeof window !== 'undefined') {
    window.ResumeIQ = ResumeIQ;
}

// Initialize active resume sync and user menu on document ready
document.addEventListener('DOMContentLoaded', () => {
    ResumeIQ.syncActiveResume();
    ResumeIQ.renderUserMenu();
});
