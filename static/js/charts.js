/**
 * Resume IQ — Chart.js Visualizations
 * Handles chart creation, responsive themes, radar charts, and dynamic updates.
 */

const Charts = {
    instances: {},

    // Dark theme default colors
    colors: {
        primary: '#6366f1',
        primarySoft: 'rgba(99, 102, 241, 0.25)',
        purple: '#8b5cf6',
        purpleSoft: 'rgba(139, 92, 246, 0.25)',
        cyan: '#22d3ee',
        cyanSoft: 'rgba(34, 211, 238, 0.25)',
        success: '#10b981',
        successSoft: 'rgba(16, 185, 129, 0.25)',
        warning: '#f59e0b',
        danger: '#ef4444',
        text: '#94a3b8',
        grid: 'rgba(255, 255, 255, 0.06)'
    },

    // Destroy existing instance to prevent canvas re-use bugs
    destroy(id) {
        if (this.instances[id]) {
            this.instances[id].destroy();
            delete this.instances[id];
        }
    },

    // 1. Dashboard Overview Doughnut Chart
    renderOverviewChart(canvasId, scores) {
        this.destroy(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.instances[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Skills', 'Experience', 'Keywords', 'ATS', 'Formatting'],
                datasets: [{
                    data: [
                        scores.skills || 0,
                        scores.experience || 0,
                        scores.keywords || 0,
                        scores.ats || 0,
                        scores.formatting || 0
                    ],
                    backgroundColor: [
                        '#6366f1',
                        '#8b5cf6',
                        '#22d3ee',
                        '#10b981',
                        '#f59e0b'
                    ],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: this.colors.text, boxWidth: 12, padding: 15 }
                    }
                },
                cutout: '72%'
            }
        });
    },

    // 2. Score Breakdown Bar Chart
    renderBreakdownChart(canvasId, scores) {
        this.destroy(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.instances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Overall', 'Skills', 'Experience', 'Keywords', 'ATS', 'Formatting'],
                datasets: [{
                    label: 'Score / 100',
                    data: [
                        scores.overall || 0,
                        scores.skills || 0,
                        scores.experience || 0,
                        scores.keywords || 0,
                        scores.ats || 0,
                        scores.formatting || 0
                    ],
                    backgroundColor: [
                        '#6366f1',
                        '#818cf8',
                        '#8b5cf6',
                        '#22d3ee',
                        '#10b981',
                        '#f59e0b'
                    ],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: this.colors.grid },
                        ticks: { color: this.colors.text }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: this.colors.text }
                    }
                }
            }
        });
    },

    // 3. Analysis Radar Chart
    renderAnalysisRadar(canvasId, scores) {
        this.destroy(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.instances[canvasId] = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Skills', 'Experience', 'Education', 'Keywords', 'ATS', 'Formatting'],
                datasets: [{
                    label: 'Resume Rating',
                    data: [
                        scores.skills || 0,
                        scores.experience || 0,
                        scores.education || 0,
                        scores.keywords || 0,
                        scores.ats || 0,
                        scores.formatting || 0
                    ],
                    backgroundColor: 'rgba(99, 102, 241, 0.25)',
                    borderColor: '#6366f1',
                    pointBackgroundColor: '#22d3ee',
                    pointBorderColor: '#ffffff',
                    pointHoverBackgroundColor: '#ffffff',
                    pointHoverBorderColor: '#6366f1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: this.colors.grid },
                        grid: { color: this.colors.grid },
                        pointLabels: { color: this.colors.text, font: { size: 11 } },
                        suggestedMin: 0,
                        suggestedMax: 100,
                        ticks: { display: false }
                    }
                },
                plugins: { legend: { display: false } }
            }
        });
    },

    // 4. Job Match Breakdown Bar Chart
    renderMatchBreakdownChart(canvasId, matchData) {
        this.destroy(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.instances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Overall Match', 'Skills Match', 'Keywords Match', 'Exp / Qualifications'],
                datasets: [{
                    label: 'Match %',
                    data: [
                        matchData.overall_match || 0,
                        matchData.skills_match || 0,
                        matchData.keywords_match || 0,
                        matchData.experience_match || 0
                    ],
                    backgroundColor: ['#6366f1', '#22d3ee', '#8b5cf6', '#10b981'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: this.colors.grid },
                        ticks: { color: this.colors.text }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: this.colors.text }
                    }
                }
            }
        });
    },

    // 5. Skill Gap Radar Chart
    renderSkillGapRadar(canvasId, radarData) {
        this.destroy(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.instances[canvasId] = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: radarData.labels || [],
                datasets: [
                    {
                        label: 'My Skills',
                        data: radarData.current || [],
                        backgroundColor: 'rgba(34, 211, 238, 0.25)',
                        borderColor: '#22d3ee',
                        pointBackgroundColor: '#22d3ee',
                        pointBorderColor: '#ffffff'
                    },
                    {
                        label: 'Required Skills',
                        data: radarData.required || [],
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderColor: '#ef4444',
                        borderDash: [5, 5],
                        pointBackgroundColor: '#ef4444'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: this.colors.grid },
                        grid: { color: this.colors.grid },
                        pointLabels: { color: this.colors.text, font: { size: 12, weight: 'bold' } },
                        suggestedMin: 0,
                        suggestedMax: 100,
                        ticks: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: this.colors.text, boxWidth: 12 }
                    }
                }
            }
        });
    },

    // 6. Multi-Job Comparison Horizontal/Vertical Bar Chart
    renderComparisonBarChart(canvasId, comparisons) {
        this.destroy(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const labels = comparisons.map(c => c.role);
        const data = comparisons.map(c => c.match_percentage);

        this.instances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Compatibility %',
                    data: data,
                    backgroundColor: data.map(val => {
                        if (val >= 75) return '#10b981';
                        if (val >= 55) return '#6366f1';
                        if (val >= 40) return '#f59e0b';
                        return '#ef4444';
                    }),
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: this.colors.grid },
                        ticks: { color: this.colors.text }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: this.colors.text }
                    }
                }
            }
        });
    },

    // 7. Roadmap Stage Progress Chart
    renderRoadmapCharts(progressCanvasId, stageCanvasId, stageSummary, items = []) {
        this.destroy(progressCanvasId);
        const ctxProg = document.getElementById(progressCanvasId);
        if (ctxProg) {
            const completedCount = items.filter(i => i.completed).length;
            const pendingCount = items.length - completedCount;
            this.instances[progressCanvasId] = new Chart(ctxProg, {
                type: 'doughnut',
                data: {
                    labels: ['Completed Tasks', 'Pending Tasks'],
                    datasets: [{
                        data: [completedCount, Math.max(pendingCount, 0)],
                        backgroundColor: ['#10b981', 'rgba(99, 102, 241, 0.4)'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { position: 'bottom', labels: { color: this.colors.text } }
                    }
                }
            });
        }

        this.destroy(stageCanvasId);
        const ctxStage = document.getElementById(stageCanvasId);
        if (ctxStage) {
            this.instances[stageCanvasId] = new Chart(ctxStage, {
                type: 'polarArea',
                data: {
                    labels: ['Learn', 'Practice', 'Build', 'Apply'],
                    datasets: [{
                        data: [
                            stageSummary.learn || 0,
                            stageSummary.practice || 0,
                            stageSummary.build || 0,
                            stageSummary.apply || 0
                        ],
                        backgroundColor: [
                            'rgba(99, 102, 241, 0.7)',
                            'rgba(139, 92, 246, 0.7)',
                            'rgba(34, 211, 238, 0.7)',
                            'rgba(16, 185, 129, 0.7)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: this.colors.text } }
                    },
                    scales: {
                        r: {
                            grid: { color: this.colors.grid },
                            ticks: { display: false }
                        }
                    }
                }
            });
        }
    }
};

// Expose globally on window
if (typeof window !== 'undefined') {
    window.Charts = Charts;
}
