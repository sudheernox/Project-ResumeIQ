/**
 * ResumeIQ — Centralized i18n Localization Engine
 * Seamless bilingual support (English / Hindi) with persistent state across pages.
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'resumeiq_lang';
    let currentLang = localStorage.getItem(STORAGE_KEY) || 'en';

    function getTranslations(lang) {
        if (!window.RESUMEIQ_TRANSLATIONS) return {};
        return window.RESUMEIQ_TRANSLATIONS[lang] || window.RESUMEIQ_TRANSLATIONS['en'] || {};
    }

    function translateText(key, fallback = '') {
        const dict = getTranslations(currentLang);
        if (dict && dict[key] !== undefined) {
            return dict[key];
        }
        const enDict = getTranslations('en');
        if (enDict && enDict[key] !== undefined) {
            return enDict[key];
        }
        return fallback || key;
    }

    function applyTranslations() {
        const dict = getTranslations(currentLang);

        // Translate text content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (dict[key] !== undefined) {
                el.textContent = dict[key];
            }
        });

        // Translate innerHTML (for elements with icons or markup)
        document.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            if (dict[key] !== undefined) {
                el.innerHTML = dict[key];
            }
        });

        // Translate placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (dict[key] !== undefined) {
                el.setAttribute('placeholder', dict[key]);
            }
        });

        // Translate titles / tooltips
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (dict[key] !== undefined) {
                el.setAttribute('title', dict[key]);
            }
        });

        // Update active class & label on any language switcher buttons
        document.querySelectorAll('.lang-switcher-btn').forEach(btn => {
            const labelEl = btn.querySelector('.current-lang-label');
            if (labelEl) {
                labelEl.textContent = currentLang === 'hi' ? 'हिन्दी' : 'English';
            }
        });

        document.querySelectorAll('.lang-select-item').forEach(item => {
            const itemLang = item.getAttribute('data-lang');
            if (itemLang === currentLang) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Update html lang attribute
        document.documentElement.lang = currentLang;

        // Dispatch language change event for dynamic charts and scripts
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: currentLang } }));
    }

    function setLanguage(lang) {
        if (lang !== 'en' && lang !== 'hi') lang = 'en';
        currentLang = lang;
        localStorage.setItem(STORAGE_KEY, lang);
        document.cookie = `resumeiq_lang=${lang}; path=/; max-age=31536000; SameSite=Lax`;
        applyTranslations();
    }

    // Attach to global ResumeIQ namespace
    window.ResumeIQ = window.ResumeIQ || {};
    window.ResumeIQ.t = translateText;
    window.ResumeIQ.setLanguage = setLanguage;
    window.ResumeIQ.getLanguage = () => currentLang;

    // Initialize on DOM load
    document.addEventListener('DOMContentLoaded', () => {
        applyTranslations();

        // Delegate click events on language switch dropdown items
        document.body.addEventListener('click', (e) => {
            const item = e.target.closest('.lang-select-item');
            if (item) {
                e.preventDefault();
                const selected = item.getAttribute('data-lang');
                if (selected) {
                    setLanguage(selected);
                }
            }
        });
    });
})();
