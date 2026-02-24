/**
 * RevSignal SDK™ - JavaScript Tracking Library
 * Module 11: Visitor Identification & Buyer Intent Tracking
 *
 * Usage:
 *   <script src="https://api.revflow.ai/sdk/revsignal.js" data-site-id="YOUR_SITE_ID"></script>
 */

(function(window, document) {
    'use strict';

    // Configuration
    const CONFIG = {
        apiEndpoint: window.REVSIGNAL_API || 'https://api.revflow.ai',
        siteId: null,
        visitorId: null,
        sessionId: null,
        trackClicks: true,
        trackForms: true,
        trackScroll: true,
        sessionTimeout: 30, // minutes
        cookieDomain: null,
        debug: false
    };

    // Storage keys
    const VISITOR_KEY = '_rs_vid';
    const SESSION_KEY = '_rs_sid';
    const LAST_ACTIVITY_KEY = '_rs_la';

    // ─────────────────────────────────────────────────────────────────────────
    // Utility Functions
    // ─────────────────────────────────────────────────────────────────────────

    function log(...args) {
        if (CONFIG.debug) {
            console.log('[RevSignal]', ...args);
        }
    }

    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    function setCookie(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        const domain = CONFIG.cookieDomain ? '; domain=' + CONFIG.cookieDomain : '';
        document.cookie = name + '=' + (value || '') + expires + domain + '; path=/; SameSite=Lax';
    }

    function getCookie(name) {
        const nameEQ = name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    function getOrCreateVisitorId() {
        let visitorId = getCookie(VISITOR_KEY) || localStorage.getItem(VISITOR_KEY);
        if (!visitorId) {
            visitorId = generateUUID();
            setCookie(VISITOR_KEY, visitorId, 365);
            try {
                localStorage.setItem(VISITOR_KEY, visitorId);
            } catch (e) {}
        }
        return visitorId;
    }

    function getOrCreateSessionId() {
        const lastActivity = getCookie(LAST_ACTIVITY_KEY);
        const now = Date.now();

        // Check if session expired
        if (lastActivity && (now - parseInt(lastActivity)) > CONFIG.sessionTimeout * 60 * 1000) {
            // Session expired, create new one
            const sessionId = generateUUID();
            setCookie(SESSION_KEY, sessionId, null); // Session cookie
            setCookie(LAST_ACTIVITY_KEY, now.toString(), null);
            return sessionId;
        }

        let sessionId = getCookie(SESSION_KEY);
        if (!sessionId) {
            sessionId = generateUUID();
            setCookie(SESSION_KEY, sessionId, null);
        }

        // Update last activity
        setCookie(LAST_ACTIVITY_KEY, now.toString(), null);
        return sessionId;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Data Collection
    // ─────────────────────────────────────────────────────────────────────────

    function collectSignalData(eventType, eventData) {
        return {
            visitor_id: CONFIG.visitorId,
            session_id: CONFIG.sessionId,
            page_url: window.location.href,
            referrer: document.referrer || null,
            user_agent: navigator.userAgent,
            screen_resolution: window.screen.width + 'x' + window.screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            language: navigator.language,
            event_type: eventType,
            event_data: eventData || null,
            timestamp: new Date().toISOString()
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // API Communication
    // ─────────────────────────────────────────────────────────────────────────

    function sendSignal(signalData) {
        const url = CONFIG.apiEndpoint + '/sdk/v1/signal';

        // Use sendBeacon if available for reliability
        if (navigator.sendBeacon) {
            const blob = new Blob([JSON.stringify(signalData)], { type: 'application/json' });
            navigator.sendBeacon(url, blob);
            log('Signal sent via beacon:', signalData.event_type);
        } else {
            // Fallback to fetch
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(signalData),
                keepalive: true
            }).then(response => {
                if (response.ok) {
                    log('Signal sent:', signalData.event_type);
                }
            }).catch(err => {
                log('Signal error:', err);
            });
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Event Tracking
    // ─────────────────────────────────────────────────────────────────────────

    function trackPageview() {
        const signal = collectSignalData('pageview');
        sendSignal(signal);
    }

    function trackClick(event) {
        if (!CONFIG.trackClicks) return;

        const target = event.target;
        const signal = collectSignalData('click', {
            element: target.tagName,
            id: target.id || null,
            className: target.className || null,
            text: target.innerText ? target.innerText.substring(0, 100) : null,
            href: target.href || null
        });
        sendSignal(signal);
    }

    function trackFormSubmit(event) {
        if (!CONFIG.trackForms) return;

        const form = event.target;
        const signal = collectSignalData('form', {
            form_id: form.id || null,
            form_name: form.name || null,
            form_action: form.action || null
        });
        sendSignal(signal);
    }

    let scrollTimeout;
    let maxScroll = 0;

    function trackScroll() {
        if (!CONFIG.trackScroll) return;

        const scrollPercent = Math.round(
            (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
        );

        if (scrollPercent > maxScroll) {
            maxScroll = scrollPercent;
        }

        // Debounce scroll tracking
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            if (maxScroll >= 75) {
                const signal = collectSignalData('scroll', {
                    scroll_depth: maxScroll
                });
                sendSignal(signal);
            }
        }, 1000);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────────────────

    const RevSignal = {
        /**
         * Initialize the SDK
         * @param {Object} options Configuration options
         */
        init: function(options) {
            if (options.siteId) CONFIG.siteId = options.siteId;
            if (options.apiEndpoint) CONFIG.apiEndpoint = options.apiEndpoint;
            if (options.debug !== undefined) CONFIG.debug = options.debug;
            if (options.trackClicks !== undefined) CONFIG.trackClicks = options.trackClicks;
            if (options.trackForms !== undefined) CONFIG.trackForms = options.trackForms;
            if (options.trackScroll !== undefined) CONFIG.trackScroll = options.trackScroll;
            if (options.cookieDomain) CONFIG.cookieDomain = options.cookieDomain;

            CONFIG.visitorId = getOrCreateVisitorId();
            CONFIG.sessionId = getOrCreateSessionId();

            log('Initialized with visitor:', CONFIG.visitorId);

            // Bind event listeners
            this.bindEvents();

            // Track initial pageview
            trackPageview();
        },

        /**
         * Bind event listeners
         */
        bindEvents: function() {
            // Click tracking
            if (CONFIG.trackClicks) {
                document.addEventListener('click', trackClick, { passive: true });
            }

            // Form tracking
            if (CONFIG.trackForms) {
                document.addEventListener('submit', trackFormSubmit, { passive: true });
            }

            // Scroll tracking
            if (CONFIG.trackScroll) {
                document.addEventListener('scroll', trackScroll, { passive: true });
            }

            // Track pageviews on SPA navigation
            if (window.history && window.history.pushState) {
                const originalPushState = window.history.pushState;
                window.history.pushState = function() {
                    originalPushState.apply(this, arguments);
                    trackPageview();
                };
            }
        },

        /**
         * Track a custom event
         * @param {string} eventName Name of the event
         * @param {Object} eventData Additional event data
         */
        track: function(eventName, eventData) {
            const signal = collectSignalData('custom', {
                event_name: eventName,
                ...eventData
            });
            sendSignal(signal);
            log('Custom event tracked:', eventName);
        },

        /**
         * Identify a visitor with known data
         * @param {Object} userData User identification data
         */
        identify: function(userData) {
            const signal = collectSignalData('identify', userData);
            sendSignal(signal);
            log('Visitor identified:', userData);
        },

        /**
         * Get current visitor ID
         * @returns {string} Visitor ID
         */
        getVisitorId: function() {
            return CONFIG.visitorId;
        },

        /**
         * Get current session ID
         * @returns {string} Session ID
         */
        getSessionId: function() {
            return CONFIG.sessionId;
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    // Auto-initialization
    // ─────────────────────────────────────────────────────────────────────────

    // Check for script tag configuration
    const scripts = document.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
        const script = scripts[i];
        if (script.src && script.src.indexOf('revsignal') !== -1) {
            const siteId = script.getAttribute('data-site-id');
            const apiEndpoint = script.getAttribute('data-api');
            const debug = script.getAttribute('data-debug') === 'true';

            if (siteId) {
                RevSignal.init({
                    siteId: siteId,
                    apiEndpoint: apiEndpoint || CONFIG.apiEndpoint,
                    debug: debug
                });
            }
            break;
        }
    }

    // Expose to global scope
    window.RevSignal = RevSignal;

})(window, document);
