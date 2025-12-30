/**
 * GPUBROKER Landing Page - Main JavaScript
 * Handles navigation, smooth scrolling, animations, and analytics
 */

(function() {
    'use strict';

    // ============================================
    // DOM Elements
    // ============================================
    const nav = document.getElementById('nav');
    const navToggle = document.getElementById('navToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    const navLinks = document.querySelectorAll('.nav__link, .mobile-menu__link');
    const planButtons = document.querySelectorAll('[data-plan]');
    const currentYearEl = document.getElementById('currentYear');

    // ============================================
    // Navigation - Scroll Effect
    // ============================================
    function handleNavScroll() {
        if (window.scrollY > 50) {
            nav.classList.add('nav--scrolled');
        } else {
            nav.classList.remove('nav--scrolled');
        }
    }

    window.addEventListener('scroll', handleNavScroll, { passive: true });
    handleNavScroll(); // Initial check

    // ============================================
    // Mobile Menu Toggle
    // ============================================
    function toggleMobileMenu() {
        const isOpen = mobileMenu.classList.contains('mobile-menu--open');
        
        if (isOpen) {
            mobileMenu.classList.remove('mobile-menu--open');
            navToggle.classList.remove('nav__toggle--active');
            document.body.style.overflow = '';
        } else {
            mobileMenu.classList.add('mobile-menu--open');
            navToggle.classList.add('nav__toggle--active');
            document.body.style.overflow = 'hidden';
        }
    }

    if (navToggle) {
        navToggle.addEventListener('click', toggleMobileMenu);
    }

    // Close mobile menu when clicking a link
    navLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            if (mobileMenu.classList.contains('mobile-menu--open')) {
                toggleMobileMenu();
            }
        });
    });

    // ============================================
    // Smooth Scrolling
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                e.preventDefault();
                
                const navHeight = nav.offsetHeight;
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // ============================================
    // Scroll Reveal Animation
    // ============================================
    function initScrollReveal() {
        const revealElements = document.querySelectorAll('.feature-card, .pricing-card, .step');
        
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('reveal--visible');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        revealElements.forEach(function(el) {
            el.classList.add('reveal');
            observer.observe(el);
        });
    }

    // Initialize scroll reveal if IntersectionObserver is supported
    if ('IntersectionObserver' in window) {
        initScrollReveal();
    }

    // ============================================
    // Analytics Tracking
    // ============================================
    function trackEvent(category, action, label, value) {
        // Google Analytics 4
        if (typeof gtag === 'function') {
            gtag('event', action, {
                'event_category': category,
                'event_label': label,
                'value': value
            });
        }
        
        // Console log for debugging (remove in production)
        console.log('Analytics Event:', { category: category, action: action, label: label, value: value });
    }

    // Track CTA button clicks
    document.querySelectorAll('.btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const plan = this.getAttribute('data-plan');
            const href = this.getAttribute('href');
            
            if (plan) {
                trackEvent('conversion', 'select_plan', plan, getPlanValue(plan));
            } else if (href && href.includes('checkout')) {
                trackEvent('engagement', 'cta_click', 'checkout_redirect');
            } else if (href && href.includes('#')) {
                trackEvent('engagement', 'cta_click', href);
            }
        });
    });

    // Get plan value for analytics
    function getPlanValue(plan) {
        var values = {
            'trial': 0,
            'basic': 20,
            'pro': 40,
            'corp': 99,
            'enterprise': 299
        };
        return values[plan] || 0;
    }

    // Track scroll depth
    var scrollDepthTracked = {
        25: false,
        50: false,
        75: false,
        100: false
    };

    function trackScrollDepth() {
        var scrollPercent = Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100);
        
        [25, 50, 75, 100].forEach(function(depth) {
            if (scrollPercent >= depth && !scrollDepthTracked[depth]) {
                scrollDepthTracked[depth] = true;
                trackEvent('engagement', 'scroll_depth', depth + '%');
            }
        });
    }

    window.addEventListener('scroll', debounce(trackScrollDepth, 250), { passive: true });

    // ============================================
    // Utility Functions
    // ============================================
    function debounce(func, wait) {
        var timeout;
        return function() {
            var context = this;
            var args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    }

    // ============================================
    // Update Current Year
    // ============================================
    if (currentYearEl) {
        currentYearEl.textContent = new Date().getFullYear();
    }

    // ============================================
    // Keyboard Navigation
    // ============================================
    document.addEventListener('keydown', function(e) {
        // Close mobile menu on Escape
        if (e.key === 'Escape' && mobileMenu.classList.contains('mobile-menu--open')) {
            toggleMobileMenu();
        }
    });

    // ============================================
    // Preload Critical Resources
    // ============================================
    function preloadResources() {
        // Preload checkout page for faster navigation
        var link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = 'https://admin.gpubroker.live/checkout';
        document.head.appendChild(link);
    }

    // Preload after page load
    window.addEventListener('load', preloadResources);

    // ============================================
    // Error Handling
    // ============================================
    window.addEventListener('error', function(e) {
        console.error('JavaScript Error:', e.message, e.filename, e.lineno);
    });

    // ============================================
    // Initialize
    // ============================================
    console.log('GPUBROKER Landing Page initialized');

})();
