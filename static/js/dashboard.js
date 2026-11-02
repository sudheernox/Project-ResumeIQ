/**
 * Resume IQ — Dashboard & Features Logic
 * Fully persistent across all 6 core features:
 * 1. AI Resume Analysis
 * 2. Smart Job Match
 * 3. Skill Gap Detection
 * 4. Learning Roadmap
 * 5. ATS Optimization
 * 6. Multi-Job Profile Comparison
 */

// Safe accessor for ResumeIQ
function getResumeIQ() {
    if (typeof ResumeIQ !== 'undefined') return ResumeIQ;
    if (typeof window !== 'undefined' && window.ResumeIQ) return window.ResumeIQ;
    return null;
}

// -----------------------------------------------------------------------------
// 1. DASHBOARD PAGE
// -----------------------------------------------------------------------------
async function loadDashboard() {
    const rIQ = getResumeIQ();
    if (!rIQ) {
        setTimeout(loadDashboard, 50);
        return;
    }
    try {
        await rIQ.syncActiveResume();
        const resumeId = rIQ.currentResumeId;

        const url = resumeId ? `/api/dashboard?resume_id=${resumeId}` : '/api/dashboard';
        const data = await rIQ.apiCall(url);

        const emptyState = document.getElementById('emptyState');
        const dashboardData = document.getElementById('dashboardData');

        if (!data.has_data) {
            if (emptyState) emptyState.style.display = 'block';
            if (dashboardData) dashboardData.style.display = 'none';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        if (dashboardData) dashboardData.style.display = 'block';

        const summary = data.summary || {};
        const analysis = data.analysis;

        // Topbar score
        const topbarScore = document.getElementById('topbar-score-val');
        if (topbarScore) topbarScore.innerText = `${Math.round(summary.overall_score || 0)} / 100`;

        // Stat Cards
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        };

        setVal('sc-overall', Math.round(summary.overall_score || 0));
        setVal('sc-ats', Math.round(summary.ats_score || 0));
        setVal('sc-match', `${Math.round(summary.job_match || 0)}%`);
        setVal('sc-skills', summary.total_skills || 0);
        setVal('sc-missing', summary.missing_skills || 0);
        setVal('sc-progress', `${Math.round(summary.roadmap_progress || 0)}%`);

        // Render Charts
        if (analysis && analysis.scores) {
            Charts.renderOverviewChart('overviewChart', analysis.scores);
            Charts.renderBreakdownChart('breakdownChart', analysis.scores);

            // Technical & Soft Skills Tags
            renderSkillTags('techSkills', analysis.technical_skills || []);
            renderSkillTags('softSkills', analysis.soft_skills || []);

            // Strengths and Recommendations
            renderList('strengthsList', analysis.strengths || []);
            renderList('recsList', analysis.recommendations || []);
        }

        // AI Insights
        if (analysis) {
            const insights = analysis.ai_insights || {};
            const insSummary = document.querySelector('#ins-summary .ins-text');
            const insTop = document.querySelector('#ins-top .ins-text');
            const insStrength = document.querySelector('#ins-strength .ins-text');
            const insGap = document.querySelector('#ins-gap .ins-text');

            if (insSummary) {
                insSummary.innerText = insights.summary || 
                    `Candidate demonstrated competence with ${summary.total_skills || 0} cataloged skills. Profile shows ${summary.overall_score > 70 ? 'strong' : 'developing'} career momentum.`;
            }
            if (insTop) {
                insTop.innerText = insights.top_insight || 
                    (summary.ats_score < 60 ? 'Optimize section formatting and action verbs to pass initial ATS filtering.' : 'Focus on closing missing domain-specific technical skills.');
            }
            if (insStrength) {
                insStrength.innerText = insights.strengths_insight || 
                    ((analysis.strengths && analysis.strengths[0]) || 'Solid technical foundation.');
            }
            if (insGap) {
                insGap.innerText = insights.gap_insight || 
                    ((analysis.weaknesses && analysis.weaknesses[0]) || 'Continue expanding hands-on project depth.');
            }
        }

    } catch (err) {
        console.error("Dashboard loading error:", err);
        ResumeIQ.showToast("Could not load dashboard data", "error");
    }
}

// -----------------------------------------------------------------------------
// 2. RESUME ANALYSIS PAGE
// -----------------------------------------------------------------------------
async function initAnalysisPage() {
    const rIQ = getResumeIQ();
    if (!rIQ) {
        setTimeout(initAnalysisPage, 50);
        return;
    }

    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const toggleUploadBtn = document.getElementById('toggleUploadBtn');
    const bannerReanalyzeBtn = document.getElementById('bannerReanalyzeBtn');
    const bannerDeleteBtn = document.getElementById('bannerDeleteBtn');

    // Drag-and-drop events
    if (dropZone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length) handleFileUpload(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) handleFileUpload(e.target.files[0]);
        });
    }

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', runFullAnalysis);
    }

    if (bannerReanalyzeBtn) {
        bannerReanalyzeBtn.addEventListener('click', runFullAnalysis);
    }

    if (toggleUploadBtn) {
        toggleUploadBtn.addEventListener('click', () => {
            const uploadSection = document.getElementById('uploadSection');
            if (uploadSection) {
                uploadSection.style.display = (uploadSection.style.display === 'none') ? 'flex' : 'none';
                if (uploadSection.style.display === 'flex') {
                    uploadSection.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    }

    if (bannerDeleteBtn) {
        bannerDeleteBtn.addEventListener('click', () => {
            if (ResumeIQ.currentResumeId && ResumeIQ.currentFileName) {
                ResumeIQ.confirmDeleteResume(ResumeIQ.currentResumeId, ResumeIQ.currentFileName);
            }
        });
    }

    // Synchronize and auto-load active resume data from backend
    await ResumeIQ.syncActiveResume();
    await checkAndLoadActiveAnalysis();
}

async function checkAndLoadActiveAnalysis() {
    try {
        const data = await ResumeIQ.apiCall('/api/active-resume');
        const banner = document.getElementById('activeResumeBanner');
        const uploadSection = document.getElementById('uploadSection');
        const analyzeSection = document.getElementById('analyzeSection');

        if (!data.has_resume) {
            if (banner) banner.style.display = 'none';
            if (uploadSection) uploadSection.style.display = 'flex';
            if (analyzeSection) analyzeSection.style.display = 'none';
            document.getElementById('analysisResults').style.display = 'none';
            return;
        }

        const resume = data.resume;
        ResumeIQ.setResume(resume.id, resume.filename);

        // Update banner
        if (banner) {
            banner.style.display = 'flex';
            document.getElementById('bannerFileName').innerText = resume.filename;
            document.getElementById('bannerFileSize').innerText = `${Math.round(resume.file_size / 1024)} KB`;
            document.getElementById('bannerUploadTime').innerText = `Uploaded ${new Date(resume.upload_time).toLocaleDateString()}`;
            
            const badge = document.getElementById('bannerStatusBadge');
            if (badge) {
                badge.innerText = data.analysis ? 'Active & Analyzed' : 'Active (Pending Analysis)';
                badge.className = data.analysis ? 'badge bg-success' : 'badge bg-warning text-dark';
            }
        }

        if (data.analysis) {
            if (uploadSection) uploadSection.style.display = 'none';
            if (analyzeSection) analyzeSection.style.display = 'none';
            displayAnalysisResults(data.analysis, resume.filename);
        } else {
            // Resume uploaded but not yet analyzed
            if (uploadSection) uploadSection.style.display = 'flex';
            if (analyzeSection) analyzeSection.style.display = 'block';
            document.getElementById('analysisResults').style.display = 'none';
        }

    } catch (e) {
        console.warn("Could not check active analysis:", e);
    }
}

async function handleFileUpload(file) {
    const validExtensions = ['pdf', 'docx'];
    const ext = file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
        ResumeIQ.showToast("Please upload a PDF or DOCX file.", "warning");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const progressBar = document.getElementById('uploadBar');
    const progressPct = document.getElementById('uploadPct');
    const progressWrap = document.getElementById('uploadProgress');
    const successMsg = document.getElementById('uploadSuccess');
    const errorMsg = document.getElementById('uploadError');

    progressWrap.style.display = 'block';
    errorMsg.style.display = 'none';
    successMsg.style.display = 'none';

    progressBar.style.width = '45%';
    progressPct.innerText = '45%';

    try {
        const result = await ResumeIQ.apiCall('/api/upload-resume', 'POST', formData, true);

        progressBar.style.width = '100%';
        progressPct.innerText = '100%';

        ResumeIQ.setResume(result.resume_id, result.filename);

        setTimeout(async () => {
            progressWrap.style.display = 'none';
            successMsg.style.display = 'block';
            document.getElementById('uploadSuccessMsg').innerText = `Uploaded: ${result.filename} (${Math.round(result.file_size / 1024)} KB)`;
            document.getElementById('analyzeSection').style.display = 'block';
            ResumeIQ.showToast("Resume uploaded successfully! Running AI Analysis...", "success");

            // Automatically run analysis right after upload
            await runFullAnalysis();
        }, 500);

    } catch (err) {
        progressWrap.style.display = 'none';
        errorMsg.style.display = 'block';
        document.getElementById('uploadErrorMsg').innerText = err.message || "Upload failed.";
        ResumeIQ.showToast(err.message || "Failed to upload resume.", "error");
    }
}

async function runFullAnalysis() {
    const resumeId = ResumeIQ.currentResumeId;
    if (!resumeId) {
        ResumeIQ.showToast("Please upload a resume first.", "warning");
        return;
    }

    const loading = document.getElementById('analysisLoading');
    const results = document.getElementById('analysisResults');
    const analyzeSection = document.getElementById('analyzeSection');
    const uploadSection = document.getElementById('uploadSection');

    loading.style.display = 'block';
    results.style.display = 'none';
    if (analyzeSection) analyzeSection.style.display = 'none';

    try {
        const data = await ResumeIQ.apiCall('/api/analyze-resume', 'POST', { resume_id: resumeId });
        if (uploadSection) uploadSection.style.display = 'none';
        
        displayAnalysisResults(data, data.filename);
        ResumeIQ.showToast("Analysis complete!", "success");
        await ResumeIQ.refreshResumesList();
        
        // Update banner badge
        const badge = document.getElementById('bannerStatusBadge');
        if (badge) {
            badge.innerText = 'Active & Analyzed';
            badge.className = 'badge bg-success';
        }
    } catch (err) {
        console.error("Analysis failed:", err);
        ResumeIQ.showToast(err.message || "Analysis failed.", "error");
    } finally {
        loading.style.display = 'none';
    }
}

function displayAnalysisResults(data, filename = '') {
    const results = document.getElementById('analysisResults');
    if (!results) return;

    results.style.display = 'block';

    const ownerName = document.getElementById('resumeOwnerName');
    if (ownerName) {
        ownerName.innerText = filename ? `Analysis Results — ${filename}` : 'Analysis Results';
    }

    const scores = data.scores || {};
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
    };

    setVal('r-overall', Math.round(scores.overall || 0));
    setVal('r-skills', Math.round(scores.skills || 0));
    setVal('r-exp', Math.round(scores.experience || 0));
    setVal('r-kw', Math.round(scores.keywords || 0));
    setVal('r-ats', Math.round(scores.ats || 0));
    setVal('r-fmt', Math.round(scores.formatting || 0));

    // Radar Chart
    Charts.renderAnalysisRadar('analysisRadarChart', scores);

    // Skills
    renderSkillTags('aSkillsContainer', data.technical_skills || []);
    renderSkillTags('aSoftContainer', data.soft_skills || []);

    // Strengths, Weaknesses, Recs
    renderList('aStrengths', data.strengths || []);
    renderList('aWeaknesses', data.weaknesses || []);
    renderList('aRecs', data.recommendations || []);

    // Details: Education, Experience, Projects
    renderStructuredData('aEducation', data.education || []);
    renderStructuredData('aExperience', data.experience || []);
    renderStructuredData('aProjects', data.projects || []);

    // AI Insights
    const insights = data.ai_insights || {};
    setVal('ai-summary', insights.summary || 'Solid candidate foundation with core competencies.');
    setVal('ai-top', insights.top_insight || 'Target high-priority missing technical skills to boost match rates.');
    setVal('ai-strength', insights.strengths_insight || ((data.strengths && data.strengths[0]) || 'Strong technical base.'));
    setVal('ai-gap', insights.gap_insight || ((data.weaknesses && data.weaknesses[0]) || 'Add more quantifiable achievement metrics.'));
}

// -----------------------------------------------------------------------------
// 3. SMART JOB MATCH PAGE
// -----------------------------------------------------------------------------
async function initJobMatchPage() {
    const rIQ = getResumeIQ();
    if (!rIQ) {
        setTimeout(initJobMatchPage, 50);
        return;
    }

    const matchBtn = document.getElementById('matchBtn');
    if (!matchBtn) return;

    await rIQ.syncActiveResume();
    const resumeId = rIQ.currentResumeId;

    const noAlert = document.getElementById('noResumeAlert');
    const activeHeader = document.getElementById('jmActiveResumeHeader');

    if (!resumeId) {
        if (noAlert) noAlert.classList.remove('d-none');
        if (activeHeader) activeHeader.style.display = 'none';
        return;
    }

    if (noAlert) noAlert.classList.add('d-none');
    if (activeHeader) {
        activeHeader.style.display = 'flex';
        document.getElementById('jmResumeFileName').innerText = ResumeIQ.currentFileName || 'Active Resume';
    }

    // Auto-load existing saved job match from backend if exists
    try {
        const existing = await ResumeIQ.apiCall(`/api/job-match?resume_id=${resumeId}`);
        if (existing && existing.has_match) {
            if (existing.job_role) {
                const titleInput = document.getElementById('jobTitleInput');
                if (titleInput) titleInput.value = existing.job_role;
            }
            if (existing.job_description) {
                const descInput = document.getElementById('jobDescInput');
                if (descInput) descInput.value = existing.job_description;
            }
            displayJobMatchResults(existing);
        }
    } catch (e) {
        console.log("No previous job match found:", e);
    }

    matchBtn.addEventListener('click', async () => {
        const curResumeId = ResumeIQ.currentResumeId;
        if (!curResumeId) {
            ResumeIQ.showToast("Please upload a resume first.", "warning");
            return;
        }

        const jobTitle = (document.getElementById('jobTitleInput')?.value || '').trim();
        const jobRoleSelect = (document.getElementById('jobRoleSelect')?.value || '').trim();
        const jobDesc = (document.getElementById('jobDescInput')?.value || '').trim();

        const role = jobTitle || jobRoleSelect;

        if (!role && !jobDesc) {
            ResumeIQ.showToast("Please enter a job title or paste a job description.", "warning");
            return;
        }

        const loading = document.getElementById('matchLoading');
        const results = document.getElementById('matchResults');

        loading.style.display = 'block';
        results.style.display = 'none';

        try {
            const data = await ResumeIQ.apiCall('/api/job-match', 'POST', {
                resume_id: curResumeId,
                job_title: role,
                job_role: role,
                job_description: jobDesc
            });

            displayJobMatchResults(data);
            ResumeIQ.showToast("Job compatibility calculated and saved!", "success");
        } catch (err) {
            ResumeIQ.showToast(err.message || "Match calculation failed.", "error");
        } finally {
            loading.style.display = 'none';
        }
    });
}

function displayJobMatchResults(data) {
    const results = document.getElementById('matchResults');
    if (!results) return;
    results.style.display = 'block';

    const overall = Math.round(data.overall_match || 0);
    const scoreNum = document.getElementById('matchScoreNum');
    if (scoreNum) scoreNum.innerText = `${overall}%`;
    
    const roleLabel = document.getElementById('matchRoleLabel');
    if (roleLabel) roleLabel.innerText = data.job_role || 'Target Job Role';

    // Quality Badge
    const badge = document.getElementById('matchQuality');
    if (badge) {
        if (overall >= 75) {
            badge.innerText = 'High Compatibility';
            badge.className = 'big-score-badge bg-success text-white';
        } else if (overall >= 50) {
            badge.innerText = 'Moderate Match';
            badge.className = 'big-score-badge bg-warning text-dark';
        } else {
            badge.innerText = 'Skill Gap Detected';
            badge.className = 'big-score-badge bg-danger text-white';
        }
    }

    // Sub scores
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
    };

    setVal('ms-skills', `${Math.round(data.skills_match || 0)}%`);
    setVal('ms-kw', `${Math.round(data.keywords_match || 0)}%`);
    setVal('ms-req', data.match_breakdown ? data.match_breakdown.required_skills_match : '—');

    // SVG Circular Ring animation
    const circle = document.getElementById('matchRingCircle');
    if (circle) {
        const circumference = 2 * Math.PI * 52;
        const strokeVal = (overall / 100) * circumference;
        circle.style.strokeDasharray = `${strokeVal} ${circumference}`;
    }

    // Chart
    Charts.renderMatchBreakdownChart('matchBreakdownChart', data);

    // Skill Tag lists
    renderSkillTags('mr-matched', data.matched_skills || [], 'badge-success');
    renderSkillTags('mr-missing', data.missing_skills || [], 'badge-danger');
    renderSkillTags('mr-partial', data.partial_skills || [], 'badge-warning');

    // Recommendations
    renderList('mr-recs', data.recommendations || []);
}

// -----------------------------------------------------------------------------
// 4. SKILL GAP DETECTION PAGE
// -----------------------------------------------------------------------------
async function initSkillGapPage() {
    const rIQ = getResumeIQ();
    if (!rIQ) {
        setTimeout(initSkillGapPage, 50);
        return;
    }

    const analyzeBtn = document.getElementById('gapAnalyzeBtn');
    const roleSelect = document.getElementById('gapRoleSelect');
    if (!analyzeBtn) return;

    await rIQ.syncActiveResume();
    const resumeId = rIQ.currentResumeId;

    const noAlert = document.getElementById('noResumeAlert');
    const activeHeader = document.getElementById('gapActiveResumeHeader');

    if (!resumeId) {
        if (noAlert) noAlert.classList.remove('d-none');
        if (activeHeader) activeHeader.style.display = 'none';
        return;
    }

    if (noAlert) noAlert.classList.add('d-none');
    if (activeHeader) {
        activeHeader.style.display = 'flex';
        document.getElementById('gapResumeFileName').innerText = ResumeIQ.currentFileName || 'Active Resume';
    }

    // Load existing skill gap from backend
    const currentRole = roleSelect ? roleSelect.value : 'Software Developer';
    try {
        const existing = await ResumeIQ.apiCall(`/api/skill-gap?resume_id=${resumeId}&career_role=${encodeURIComponent(currentRole)}`);
        if (existing && existing.has_gap) {
            displaySkillGapResults(existing);
        } else {
            // First time load: automatically compute initial gap
            triggerSkillGapComputation(resumeId, currentRole);
        }
    } catch (e) {
        triggerSkillGapComputation(resumeId, currentRole);
    }

    analyzeBtn.addEventListener('click', async () => {
        const curResumeId = ResumeIQ.currentResumeId;
        if (!curResumeId) {
            ResumeIQ.showToast("Please upload a resume first.", "warning");
            return;
        }

        const role = roleSelect ? roleSelect.value : 'Software Developer';
        const customJd = (document.getElementById('gapCustomJd')?.value || '').trim();

        await triggerSkillGapComputation(curResumeId, role, customJd);
    });

    // When role changes, check if saved gap exists or re-analyze
    if (roleSelect) {
        roleSelect.addEventListener('change', async () => {
            const curResumeId = ResumeIQ.currentResumeId;
            if (!curResumeId) return;
            const role = roleSelect.value;
            try {
                const existing = await ResumeIQ.apiCall(`/api/skill-gap?resume_id=${curResumeId}&career_role=${encodeURIComponent(role)}`);
                if (existing && existing.has_gap) {
                    displaySkillGapResults(existing);
                } else {
                    await triggerSkillGapComputation(curResumeId, role);
                }
            } catch (e) {
                await triggerSkillGapComputation(curResumeId, role);
            }
        });
    }
}

async function triggerSkillGapComputation(resumeId, role, customJd = '') {
    const loading = document.getElementById('gapLoading');
    const results = document.getElementById('gapResults');

    if (loading) loading.style.display = 'block';
    if (results) results.style.display = 'none';

    try {
        const data = await ResumeIQ.apiCall('/api/skill-gap', 'POST', {
            resume_id: resumeId,
            career_role: role,
            custom_jd: customJd
        });

        displaySkillGapResults(data);
        ResumeIQ.showToast("Skill gap analysis updated and saved!", "success");
    } catch (err) {
        ResumeIQ.showToast(err.message || "Skill gap analysis failed.", "error");
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function displaySkillGapResults(data) {
    const results = document.getElementById('gapResults');
    if (!results) return;
    results.style.display = 'block';

    const coverage = Math.round(data.overall_coverage || 0);
    const scoreNum = document.getElementById('gapScoreNum');
    if (scoreNum) scoreNum.innerText = `${coverage}%`;
    
    const roleLabel = document.getElementById('gapRoleLabel');
    if (roleLabel) roleLabel.innerText = data.career_role;

    const missingCount = document.getElementById('gapMissingCount');
    if (missingCount) missingCount.innerText = data.total_missing || 0;

    // SVG Ring
    const circle = document.getElementById('gapRingCircle');
    if (circle) {
        const circumference = 2 * Math.PI * 52;
        const strokeVal = (coverage / 100) * circumference;
        circle.style.strokeDasharray = `${strokeVal} ${circumference}`;
    }

    // Radar Chart
    if (data.radar_data) {
        Charts.renderSkillGapRadar('skillGapRadar', data.radar_data);
    }

    // Category Breakdown progress bars
    const catContainer = document.getElementById('categoryBreakdown');
    if (catContainer) {
        catContainer.innerHTML = '';
        (data.category_analysis || []).forEach(cat => {
            const row = document.createElement('div');
            row.className = 'mb-3';
            row.innerHTML = `
                <div class="d-flex justify-content-between small mb-1">
                    <span class="text-white fw-600">${cat.category}</span>
                    <span class="text-cyan">${cat.score}% match</span>
                </div>
                <div class="progress" style="height: 6px; background: rgba(255,255,255,0.08);">
                    <div class="progress-bar" style="width: ${cat.score}%; background: linear-gradient(90deg, #6366f1, #22d3ee);"></div>
                </div>
            `;
            catContainer.appendChild(row);
        });
    }

    // Skill tags
    renderSkillTags('gap-missing-tech', data.missing_technical || [], 'badge-danger');
    renderSkillTags('gap-improve', data.skills_to_improve || [], 'badge-warning');
    renderSkillTags('gap-existing', data.existing_skills || [], 'badge-success');

    // Priority Skills
    const priorityContainer = document.getElementById('prioritySkills');
    if (priorityContainer) {
        priorityContainer.innerHTML = '';
        (data.priority_skills || []).forEach(skill => {
            const span = document.createElement('span');
            span.className = 'skill-tag badge-warning';
            span.innerHTML = `<i class="bi bi-star-fill text-warning me-1"></i>${skill}`;
            priorityContainer.appendChild(span);
        });
    }
}

// -----------------------------------------------------------------------------
// 5. PERSONALIZED LEARNING ROADMAP PAGE
// -----------------------------------------------------------------------------
async function initRoadmapPage() {
    const rIQ = getResumeIQ();
    if (!rIQ) {
        setTimeout(initRoadmapPage, 50);
        return;
    }

    const genBtn = document.getElementById('generateRoadmapBtn');
    const roleSelect = document.getElementById('roadmapRoleSelect');
    if (!genBtn) return;

    await rIQ.syncActiveResume();
    const resumeId = rIQ.currentResumeId;

    const noAlert = document.getElementById('noResumeAlert');
    const activeHeader = document.getElementById('roadmapActiveResumeHeader');

    if (!resumeId) {
        if (noAlert) noAlert.classList.remove('d-none');
        if (activeHeader) activeHeader.style.display = 'none';
        return;
    }

    if (noAlert) noAlert.classList.add('d-none');
    if (activeHeader) {
        activeHeader.style.display = 'flex';
        document.getElementById('roadmapResumeFileName').innerText = ResumeIQ.currentFileName || 'Active Resume';
    }

    const currentRole = roleSelect ? roleSelect.value : 'Software Developer';

    // FIRST: Check if an existing roadmap is already saved in SQLite!
    // NEVER overwrite existing progress on refresh!
    try {
        const existing = await ResumeIQ.apiCall(`/api/roadmap?resume_id=${resumeId}&career_role=${encodeURIComponent(currentRole)}`);
        if (existing && existing.has_roadmap) {
            displayRoadmapResults(existing);
        } else {
            // First time: generate automatically
            await triggerRoadmapGeneration(resumeId, currentRole);
        }
    } catch (e) {
        await triggerRoadmapGeneration(resumeId, currentRole);
    }

    genBtn.addEventListener('click', async () => {
        const curResumeId = ResumeIQ.currentResumeId;
        if (!curResumeId) {
            ResumeIQ.showToast("Please upload a resume first.", "warning");
            return;
        }

        const role = roleSelect ? roleSelect.value : 'Software Developer';
        await triggerRoadmapGeneration(curResumeId, role);
    });

    if (roleSelect) {
        roleSelect.addEventListener('change', async () => {
            const curResumeId = ResumeIQ.currentResumeId;
            if (!curResumeId) return;
            const role = roleSelect.value;
            try {
                const existing = await ResumeIQ.apiCall(`/api/roadmap?resume_id=${curResumeId}&career_role=${encodeURIComponent(role)}`);
                if (existing && existing.has_roadmap) {
                    displayRoadmapResults(existing);
                } else {
                    await triggerRoadmapGeneration(curResumeId, role);
                }
            } catch (e) {
                await triggerRoadmapGeneration(curResumeId, role);
            }
        });
    }
}

async function triggerRoadmapGeneration(resumeId, role) {
    const loading = document.getElementById('roadmapLoading');
    const container = document.getElementById('roadmapItems');

    if (loading) loading.style.display = 'block';
    if (container) container.innerHTML = '';

    try {
        const data = await ResumeIQ.apiCall('/api/generate-roadmap', 'POST', {
            resume_id: resumeId,
            career_role: role
        });

        displayRoadmapResults(data);
        ResumeIQ.showToast("Personalized learning roadmap generated and saved!", "success");
    } catch (err) {
        ResumeIQ.showToast(err.message || "Failed to generate roadmap.", "error");
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function displayRoadmapResults(data) {
    const phases = document.getElementById('roadmapPhases');
    const chartRow = document.getElementById('roadmapChartRow');
    if (phases) phases.style.display = 'flex';
    if (chartRow) chartRow.style.display = 'flex';

    const items = data.roadmap_items || [];
    const container = document.getElementById('roadmapItems');
    if (!container) return;
    container.innerHTML = '';

    // Update Progress Metrics
    updateRoadmapProgressMetrics(items);

    // Chart
    if (data.stage_summary) {
        Charts.renderRoadmapCharts('roadmapProgressChart', 'stageChart', data.stage_summary, items);
    }

    const roadmapId = data.roadmap_id || data.id;

    // Render Skill Roadmap Cards
    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = `roadmap-card ${item.completed ? 'completed' : ''}`;
        card.id = `skill-card-${index}`;

        const priorityBadge = item.priority === 'high' 
            ? '<span class="badge bg-danger">High Priority</span>' 
            : '<span class="badge bg-primary">Medium Priority</span>';

        const stages = item.stages || {};
        const learn = stages.learn || {};
        const practice = stages.practice || {};
        const build = stages.build || {};
        const apply = stages.apply || {};

        card.innerHTML = `
            <div class="roadmap-card-header">
                <div>
                    <h5 class="text-white mb-1"><i class="bi bi-code-slash text-cyan me-2"></i>${item.skill}</h5>
                    <div class="d-flex align-items-center gap-2 mt-1">
                        ${priorityBadge}
                        <span class="text-secondary small"><i class="bi bi-clock me-1"></i>${item.duration || '2-4 weeks'}</span>
                    </div>
                </div>
                <button class="btn btn-sm ${item.completed ? 'btn-success' : 'btn-outline-primary'}" onclick="toggleSkillCompletion(${roadmapId}, '${item.skill.replace(/'/g, "\\'")}', ${!item.completed}, ${index})">
                    <i class="bi ${item.completed ? 'bi-check-circle-fill' : 'bi-circle'} me-1"></i>${item.completed ? 'Completed' : 'Mark Complete'}
                </button>
            </div>

            <!-- 4 Stages Tabs -->
            <ul class="nav nav-pills gap-2 mb-3" id="pills-tab-${index}" role="tablist">
                <li class="nav-item">
                    <button class="stage-tab-btn active" data-bs-toggle="pill" data-bs-target="#learn-${index}">📚 Learn</button>
                </li>
                <li class="nav-item">
                    <button class="stage-tab-btn" data-bs-toggle="pill" data-bs-target="#practice-${index}">💪 Practice</button>
                </li>
                <li class="nav-item">
                    <button class="stage-tab-btn" data-bs-toggle="pill" data-bs-target="#build-${index}">🛠️ Build</button>
                </li>
                <li class="nav-item">
                    <button class="stage-tab-btn" data-bs-toggle="pill" data-bs-target="#apply-${index}">🚀 Apply</button>
                </li>
            </ul>

            <div class="tab-content" id="pills-tabContent-${index}">
                <!-- Learn Tab -->
                <div class="tab-pane fade show active" id="learn-${index}">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <h6 class="text-secondary small">Core Topics</h6>
                            <ul class="insight-list">
                                ${(learn.topics || []).map(t => `<li>${t}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-secondary small">Curated Free Resources</h6>
                            <div class="d-flex flex-column gap-2">
                                ${(learn.resources || []).map(r => `
                                    <a href="${r.url}" target="_blank" rel="noopener noreferrer" class="text-cyan small text-decoration-none">
                                        <i class="bi bi-box-arrow-up-right me-1"></i>${r.name} ${r.free ? '<span class="badge bg-success-subtle text-success ms-1">Free</span>' : ''}
                                    </a>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Practice Tab -->
                <div class="tab-pane fade" id="practice-${index}">
                    <h6 class="text-secondary small">Practice Exercises & Platforms</h6>
                    <ul class="insight-list">
                        ${(practice.exercises || []).map(e => `<li>${e}</li>`).join('')}
                    </ul>
                    ${(practice.platforms || []).length > 0 ? `
                        <div class="mt-2 text-secondary small">Recommended: ${(practice.platforms || []).join(', ')}</div>
                    ` : ''}
                </div>

                <!-- Build Tab -->
                <div class="tab-pane fade" id="build-${index}">
                    <h6 class="text-secondary small">Recommended Mini Projects</h6>
                    <ul class="insight-list">
                        ${(build.projects || []).map(p => `<li><strong>${p}</strong></li>`).join('')}
                    </ul>
                </div>

                <!-- Apply Tab -->
                <div class="tab-pane fade" id="apply-${index}">
                    <h6 class="text-secondary small">Job Application Steps</h6>
                    <ul class="insight-list">
                        ${(apply.actions || []).map(a => `<li>${a}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

async function toggleSkillCompletion(roadmapId, skillName, status, index) {
    try {
        const res = await ResumeIQ.apiCall('/api/roadmap-progress', 'POST', {
            roadmap_id: roadmapId,
            skill_name: skillName,
            completed: status
        });

        const bar = document.getElementById('overallProgressBar');
        if (bar) bar.style.width = `${res.progress_percentage}%`;

        const pctEl = document.getElementById('roadmapProgressPct');
        if (pctEl) pctEl.innerText = `${Math.round(res.progress_percentage)}%`;

        const textEl = document.getElementById('progressText');
        if (textEl) textEl.innerText = `${res.completed_items} / ${res.total_items} completed`;

        const card = document.getElementById(`skill-card-${index}`);
        if (card) {
            if (status) card.classList.add('completed');
            else card.classList.remove('completed');

            const btn = card.querySelector('button');
            btn.className = `btn btn-sm ${status ? 'btn-success' : 'btn-outline-primary'}`;
            btn.innerHTML = `<i class="bi ${status ? 'bi-check-circle-fill' : 'bi-circle'} me-1"></i>${status ? 'Completed' : 'Mark Complete'}`;
            btn.setAttribute('onclick', `toggleSkillCompletion(${roadmapId}, '${skillName.replace(/'/g, "\\'")}', ${!status}, ${index})`);
        }

        // Dynamically update progress charts
        try {
            const curRole = document.getElementById('roadmapRoleSelect')?.value || 'Software Developer';
            const curRoadmap = await ResumeIQ.apiCall(`/api/roadmap?resume_id=${ResumeIQ.currentResumeId}&career_role=${encodeURIComponent(curRole)}`);
            if (curRoadmap && curRoadmap.has_roadmap) {
                Charts.renderRoadmapCharts('roadmapProgressChart', 'stageChart', curRoadmap.stage_summary, curRoadmap.roadmap_items);
            }
        } catch (e) {}

        ResumeIQ.showToast(`${status ? 'Completed' : 'Unmarked'}: ${skillName}! Saved in database.`, "success");
    } catch (err) {
        ResumeIQ.showToast("Failed to update progress.", "error");
    }
}

function updateRoadmapProgressMetrics(items) {
    const total = items.length;
    const completed = items.filter(i => i.completed).length;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

    const bar = document.getElementById('overallProgressBar');
    if (bar) bar.style.width = `${pct}%`;

    const pctEl = document.getElementById('roadmapProgressPct');
    if (pctEl) pctEl.innerText = `${pct}%`;

    const textEl = document.getElementById('progressText');
    if (textEl) textEl.innerText = `${completed} / ${total} completed`;
}

// -----------------------------------------------------------------------------
// 6. MULTI-JOB PROFILE COMPARISON PAGE
// -----------------------------------------------------------------------------
async function initComparisonPage() {
    const rIQ = getResumeIQ();
    if (!rIQ) {
        setTimeout(initComparisonPage, 50);
        return;
    }

    const compBtn = document.getElementById('compareBtn');
    const addCustomBtn = document.getElementById('addCustomCompBtn');
    if (!compBtn) return;

    await rIQ.syncActiveResume();
    const resumeId = rIQ.currentResumeId;

    const noAlert = document.getElementById('noResumeAlert');
    const activeHeader = document.getElementById('compActiveResumeHeader');

    if (!resumeId) {
        if (noAlert) noAlert.classList.remove('d-none');
        if (activeHeader) activeHeader.style.display = 'none';
        return;
    }

    if (noAlert) noAlert.classList.add('d-none');
    if (activeHeader) {
        activeHeader.style.display = 'flex';
        document.getElementById('compResumeFileName').innerText = rIQ.currentFileName || 'Active Resume';
    }

    // Auto-load existing comparison if already computed
    try {
        const existing = await rIQ.apiCall(`/api/compare-jobs?resume_id=${resumeId}`);
        if (existing && existing.has_comparison) {
            displayComparisonResults(existing);
        } else {
            await triggerComparison(resumeId);
        }
    } catch (e) {
        await triggerComparison(resumeId);
    }

    compBtn.addEventListener('click', async () => {
        const curResumeId = rIQ.currentResumeId;
        if (!curResumeId) {
            rIQ.showToast("Please upload a resume first.", "warning");
            return;
        }
        await triggerComparison(curResumeId);
    });

    if (addCustomBtn) {
        addCustomBtn.addEventListener('click', async () => {
            const curResumeId = rIQ.currentResumeId;
            if (!curResumeId) return;

            const title = (document.getElementById('customCompTitle')?.value || '').trim();
            const desc = (document.getElementById('customCompDesc')?.value || '').trim();

            if (!title || !desc) {
                rIQ.showToast("Please enter both custom role title and requirements.", "warning");
                return;
            }

            const customRoles = [{ title, description: desc }];
            await triggerComparison(curResumeId, customRoles);
            rIQ.showToast(`Added and evaluated custom role: ${title}!`, "success");
        });
    }
}

async function triggerComparison(resumeId, customRoles = []) {
    const rIQ = getResumeIQ();
    const loading = document.getElementById('compLoading');
    const results = document.getElementById('compResults');

    if (loading) loading.style.display = 'block';
    if (results) results.style.display = 'none';

    try {
        const data = await rIQ.apiCall('/api/compare-jobs', 'POST', {
            resume_id: resumeId,
            custom_roles: customRoles
        });

        displayComparisonResults(data);
        rIQ.showToast("Comparison computed and saved!", "success");
    } catch (err) {
        if (rIQ) rIQ.showToast(err.message || "Comparison failed.", "error");
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function displayComparisonResults(data) {
    const results = document.getElementById('compResults');
    if (!results) return;
    results.style.display = 'block';

    const best = data.best_match;
    if (best) {
        const bmRole = document.getElementById('bm-role');
        if (bmRole) bmRole.innerText = best.role;

        const bmScore = document.getElementById('bm-score');
        if (bmScore) bmScore.innerText = `${Math.round(best.match_percentage)}% Match`;

        const bmMsg = document.getElementById('bm-msg');
        if (bmMsg) bmMsg.innerText = best.top_recommendation || 'Your current skills align closely with this career path.';
    }

    // Chart
    Charts.renderComparisonBarChart('compBarChart', data.comparisons || []);

    // Role Cards
    const container = document.getElementById('roleCards');
    if (!container) return;
    container.innerHTML = '';

    (data.comparisons || []).forEach(comp => {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4';

        const pct = Math.round(comp.match_percentage);
        const color = pct >= 75 ? 'success' : (pct >= 50 ? 'primary' : 'warning');
        const customBadge = comp.is_custom ? '<span class="badge bg-info-subtle text-cyan ms-1">Custom</span>' : '';

        col.innerHTML = `
            <div class="list-card h-100">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="text-white mb-0">${comp.role} ${customBadge}</h6>
                    <span class="badge bg-${color}">${pct}%</span>
                </div>
                <div class="progress mb-3" style="height: 5px;">
                    <div class="progress-bar bg-${color}" style="width: ${pct}%"></div>
                </div>
                <div class="mb-2">
                    <span class="text-secondary small">Matched Skills:</span>
                    <div class="skills-wrap mt-1">
                        ${(comp.matched_skills || []).map(s => `<span class="skill-tag badge-success">${s}</span>`).join('')}
                    </div>
                </div>
                <div>
                    <span class="text-secondary small">Missing Skills:</span>
                    <div class="skills-wrap mt-1">
                        ${(comp.missing_skills || []).map(s => `<span class="skill-tag badge-danger">${s}</span>`).join('')}
                    </div>
                </div>
            </div>
        `;
        container.appendChild(col);
    });
}

// -----------------------------------------------------------------------------
// HELPER UTILITIES
// -----------------------------------------------------------------------------
function renderSkillTags(containerId, skills, badgeClass = '') {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';
    if (!skills || skills.length === 0) {
        container.innerHTML = '<span class="text-secondary small">None identified</span>';
        return;
    }

    skills.forEach(skill => {
        const tag = document.createElement('span');
        tag.className = `skill-tag ${badgeClass}`;
        tag.innerText = skill;
        container.appendChild(tag);
    });
}

function renderList(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';
    if (!items || items.length === 0) {
        container.innerHTML = '<li class="text-secondary small">No items found</li>';
        return;
    }

    items.forEach(item => {
        const li = document.createElement('li');
        li.innerText = item;
        container.appendChild(li);
    });
}

function renderStructuredData(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = '<span class="text-secondary">None specified</span>';
        return;
    }

    let html = '';
    items.forEach(item => {
        if (typeof item === 'object') {
            const title = item.degree || item.title || item.name || item.raw || '';
            const sub = item.institution || item.company || (item.technologies ? item.technologies.join(', ') : '') || '';
            const year = item.year || item.duration || '';

            html += `
                <div class="mb-2 pb-2 border-bottom border-dark">
                    <div class="text-white fw-600">${title}</div>
                    ${sub ? `<div class="text-cyan small">${sub}</div>` : ''}
                    ${year ? `<div class="text-muted small">${year}</div>` : ''}
                </div>
            `;
        } else {
            html += `<div class="mb-1 text-white">${item}</div>`;
        }
    });

    container.innerHTML = html;
}
