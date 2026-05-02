function navigateTo(viewId, email = '') {
    localStorage.setItem('currentView', viewId);
    if (email) {
        localStorage.setItem('currentUserEmail', email);
    } else {
        email = localStorage.getItem('currentUserEmail') || '';
    }

    // Hide all views
    const views = document.querySelectorAll('.spa-view');
    views.forEach(view => {
        view.classList.remove('active-view');
    });

    // Show the target view
    const targetView = document.getElementById('view-' + viewId);
    if (targetView) {
        targetView.classList.add('active-view');
    }

    // Update active state in nav links
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('onclick') && link.getAttribute('onclick').includes("navigateTo('" + viewId + "')")) {
            link.classList.add('active');
        }
    });

    // Handle specific view logic
    if (viewId === 'profile' && email) {
        const nameDisplay = document.getElementById('user-name-display');
        const emailDisplay = document.getElementById('user-email-display');
        const initialDisplay = document.getElementById('user-initial-display');
        
        if (nameDisplay) nameDisplay.textContent = email.split('@')[0];
        if (emailDisplay) emailDisplay.textContent = email;
        if (initialDisplay) initialDisplay.textContent = email.charAt(0).toUpperCase();
        
        // Show logout, hide login
        const loginBtn = document.getElementById('login-nav-btn');
        const logoutBtn = document.getElementById('logout-nav-btn');
        const historyBtn = document.getElementById('history-nav-btn');
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-block';
        if (historyBtn) historyBtn.style.display = 'inline-block';

        // Fetch history
        const historyContainer = document.getElementById('translation-history-container');
        if (historyContainer) {
            historyContainer.innerHTML = '<p style="color: #5f6368; text-align: center; margin: 0;">Loading history...</p>';
            fetch('/api/history?user=' + encodeURIComponent(email))
                .then(res => res.json())
                .then(data => {
                    if (data.history && data.history.length > 0) {
                        let html = '<div style="display: flex; flex-direction: column; gap: 10px;">';
                        data.history.forEach(item => {
                            html += `
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #1a73e8; display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; color: #333;">"${item.text}"</span>
                                <span style="font-size: 0.85rem; color: #888;">${item.created_at}</span>
                            </div>`;
                        });
                        html += '</div>';
                        historyContainer.innerHTML = html;
                    } else {
                        historyContainer.innerHTML = '<p style="color: #5f6368; text-align: center; margin: 0;">No translations yet. Start translating to see your history!</p>';
                    }
                })
                .catch(err => {
                    console.error("Failed to load history", err);
                    historyContainer.innerHTML = '<p style="color: #ea4335; text-align: center; margin: 0;">Failed to load history.</p>';
                });
        }
    }

    // When navigating home, reset nav styling
    const nav = document.querySelector('nav');
    if (viewId === 'home') {
        nav.classList.add('transparent-nav');
    } else {
        nav.classList.remove('transparent-nav');
        nav.style.background = '#ffffff';
        nav.style.borderBottom = '1px solid var(--border-color)';
    }

    if (viewId === 'project') {
        // Camera must be started manually
    }
}

// Attach logout handler and restore state
document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logout-nav-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await fetch('/api/logout', { method: 'POST' });
            } catch (err) {
                console.error("Logout failed", err);
            }
            localStorage.removeItem('currentUserEmail');
            localStorage.setItem('currentView', 'home');
            const loginBtn = document.getElementById('login-nav-btn');
            const historyBtn = document.getElementById('history-nav-btn');
            if (loginBtn) loginBtn.style.display = 'inline-block';
            if (logoutBtn) logoutBtn.style.display = 'none';
            if (historyBtn) historyBtn.style.display = 'none';
            navigateTo('home');
        });
    }

    // Restore previous view
    const savedView = localStorage.getItem('currentView') || 'home';
    const savedEmail = localStorage.getItem('currentUserEmail') || '';
    
    // Check if user is theoretically logged in
    const loginBtn = document.getElementById('login-nav-btn');
    const historyBtn = document.getElementById('history-nav-btn');
    if (savedEmail && loginBtn) {
        loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-block';
        if (historyBtn) historyBtn.style.display = 'inline-block';
    }
    
    // Navigate to the saved view immediately
    navigateTo(savedView, savedEmail);
});

function openHistory() {
    const loginBtn = document.getElementById('login-nav-btn');
    if (loginBtn && loginBtn.style.display !== 'none') {
        alert("Please sign in to view your history.");
        const toggleAuthBtn = document.getElementById('toggle-auth');
        if (toggleAuthBtn && toggleAuthBtn.innerText.toLowerCase().includes('in')) {
            toggleAuthBtn.click();
        }
        navigateTo('login');
    } else {
        const emailDisplay = document.getElementById('user-email-display');
        const email = emailDisplay ? emailDisplay.textContent : '';
        navigateTo('profile', email);
        setTimeout(() => {
            const historyContainer = document.getElementById('translation-history-container');
            if (historyContainer) {
                historyContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 300);
    }
}

window.startCamera = function() {
    const emailDisplay = document.getElementById('user-email-display');
    const userEmail = emailDisplay ? emailDisplay.textContent : 'guest';
    const videoImg = document.getElementById('main-video-feed');
    const placeholder = document.getElementById('video-placeholder');
    const startBtn = document.getElementById('start-cam-btn');
    const stopBtn = document.getElementById('stop-cam-btn');
    const activeIndicator = document.getElementById('cam-active-indicator');

    if (videoImg) {
        videoImg.src = "/video_feed?user=" + encodeURIComponent(userEmail);
        videoImg.style.display = 'block';
        if (placeholder) placeholder.style.display = 'none';
    }
    if (startBtn) startBtn.style.display = 'none';
    if (stopBtn) stopBtn.style.display = 'flex';
    
    if (activeIndicator) {
        activeIndicator.style.background = '#34A853';
        activeIndicator.style.boxShadow = '0 0 8px #34A853';
        activeIndicator.style.animation = 'pulse 2s infinite';
    }
    const statusText = document.getElementById('cam-status-text');
    if (statusText) statusText.textContent = 'Camera Active';
};

window.stopCamera = function() {
    const videoImg = document.getElementById('main-video-feed');
    const placeholder = document.getElementById('video-placeholder');
    const startBtn = document.getElementById('start-cam-btn');
    const stopBtn = document.getElementById('stop-cam-btn');
    const activeIndicator = document.getElementById('cam-active-indicator');

    if (videoImg) {
        videoImg.src = "";
        videoImg.style.display = 'none';
        if (placeholder) placeholder.style.display = 'block';
    }
    if (startBtn) startBtn.style.display = 'flex';
    if (stopBtn) stopBtn.style.display = 'none';
    
    if (activeIndicator) {
        activeIndicator.style.background = '#ea4335';
        activeIndicator.style.boxShadow = '0 0 8px #ea4335';
        activeIndicator.style.animation = 'none';
    }
    const statusText = document.getElementById('cam-status-text');
    if (statusText) statusText.textContent = 'Camera Offline';
};
