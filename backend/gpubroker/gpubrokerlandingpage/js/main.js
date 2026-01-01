/**
 * GPUBROKER Landing Page - Main JavaScript
 * Handles navigation, smooth scrolling, animations, enrollment modal, and analytics
 */

// ============================================
// API Configuration
// ============================================
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:28080'
    : 'https://admin.gpubroker.site';

// ============================================
// Plan Configuration
// ============================================
const PLAN_CONFIG = {
    trial: { name: 'Prueba Gratuita', price: '$0 USD', priceNum: 0, tokens: '1,000' },
    basic: { name: 'Básico', price: '$20 USD/mes', priceNum: 20, tokens: '5,000' },
    pro: { name: 'Profesional', price: '$40 USD/mes', priceNum: 40, tokens: '10,000' },
    corp: { name: 'Corporativo', price: '$99 USD/mes', priceNum: 99, tokens: '50,000' },
    enterprise: { name: 'Enterprise', price: '$299 USD/mes', priceNum: 299, tokens: '200,000' }
};

// ============================================
// Enrollment Modal State
// ============================================
let enrollmentState = {
    plan: 'pro',
    geoConfig: null,
    requiresTaxId: false,
    detectedCountry: 'US',
    validatedIdentifier: null,
    identifierType: null,
    apiKey: null,
    podId: null,
    podUrl: null,
    userEmail: null,
    userName: null
};

// PayPal buttons rendered flag
let paypalButtonsRendered = false;

// ============================================
// Global Modal Functions (accessible from onclick)
// ============================================
function openEnrollmentModal(plan) {
    enrollmentState.plan = plan || 'pro';
    const modal = document.getElementById('enrollmentModal');
    if (modal) {
        modal.classList.add('enrollment-modal--open');
        document.body.classList.add('modal-open');
        initEnrollmentFlow();
    }
}

function closeEnrollmentModal() {
    const modal = document.getElementById('enrollmentModal');
    if (modal) {
        modal.classList.remove('enrollment-modal--open');
        document.body.classList.remove('modal-open');
        resetEnrollmentState();
    }
}

function resetEnrollmentState() {
    enrollmentState = {
        plan: 'pro',
        geoConfig: null,
        requiresTaxId: false,
        detectedCountry: 'US',
        validatedIdentifier: null,
        identifierType: null,
        apiKey: null,
        podId: null,
        podUrl: null,
        userEmail: null,
        userName: null
    };
    // Reset PayPal buttons flag
    paypalButtonsRendered = false;
    // Clear PayPal container
    const paypalContainer = document.getElementById('paypal-button-container');
    if (paypalContainer) {
        paypalContainer.innerHTML = '';
    }
    // Reset all steps visibility
    showModalStep('stepGeo');
}

// Make functions globally accessible
window.openEnrollmentModal = openEnrollmentModal;
window.closeEnrollmentModal = closeEnrollmentModal;

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
    const cookieBanner = document.getElementById('cookieBanner');
    const acceptCookiesBtn = document.getElementById('acceptCookies');
    const cookieSettingsBtn = document.getElementById('cookieSettings');

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
        link.href = 'https://admin.gpubroker.site/checkout';
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

    // ============================================
    // Cookie Consent Management
    // ============================================
    const COOKIE_CONSENT_KEY = 'gpubroker_cookie_consent';
    const COOKIE_CONSENT_EXPIRY = 365; // days

    function getCookieConsent() {
        try {
            return localStorage.getItem(COOKIE_CONSENT_KEY);
        } catch (e) {
            return null;
        }
    }

    function setCookieConsent(value) {
        try {
            localStorage.setItem(COOKIE_CONSENT_KEY, value);
        } catch (e) {
            console.warn('Could not save cookie consent to localStorage');
        }
    }

    function showCookieBanner() {
        if (cookieBanner) {
            setTimeout(function() {
                cookieBanner.classList.add('cookie-banner--visible');
            }, 1000); // Show after 1 second
        }
    }

    function hideCookieBanner() {
        if (cookieBanner) {
            cookieBanner.classList.remove('cookie-banner--visible');
        }
    }

    function acceptAllCookies() {
        setCookieConsent('accepted');
        hideCookieBanner();
        trackEvent('consent', 'cookie_consent', 'accepted');
        enableAnalytics();
    }

    function openCookieSettings() {
        // Redirect to cookie policy page
        window.location.href = 'legal/cookie-policy.html';
    }

    function enableAnalytics() {
        // Enable Google Analytics if consent given
        if (typeof gtag === 'function') {
            gtag('consent', 'update', {
                'analytics_storage': 'granted'
            });
        }
    }

    // Initialize cookie consent
    function initCookieConsent() {
        const consent = getCookieConsent();
        
        if (!consent) {
            showCookieBanner();
        } else if (consent === 'accepted') {
            enableAnalytics();
        }
    }

    // Event listeners for cookie banner
    if (acceptCookiesBtn) {
        acceptCookiesBtn.addEventListener('click', acceptAllCookies);
    }

    if (cookieSettingsBtn) {
        cookieSettingsBtn.addEventListener('click', openCookieSettings);
    }

    // Initialize cookie consent on page load
    initCookieConsent();

    // ============================================
    // Enrollment Modal Logic
    // ============================================
    const enrollmentModal = document.getElementById('enrollmentModal');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const modalClose = document.getElementById('modalClose');

    // Close modal on backdrop click
    if (modalBackdrop) {
        modalBackdrop.addEventListener('click', closeEnrollmentModal);
    }

    // Close modal on X button click
    if (modalClose) {
        modalClose.addEventListener('click', closeEnrollmentModal);
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && enrollmentModal && enrollmentModal.classList.contains('enrollment-modal--open')) {
            closeEnrollmentModal();
        }
    });

    // Tax ID Validation Button
    const modalValidateBtn = document.getElementById('modalValidateBtn');
    if (modalValidateBtn) {
        modalValidateBtn.addEventListener('click', validateModalIdentity);
    }

    // Identifier input - numbers only
    const modalIdentifier = document.getElementById('modalIdentifier');
    if (modalIdentifier) {
        modalIdentifier.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }

    // Retry button
    const modalRetryBtn = document.getElementById('modalRetryBtn');
    if (modalRetryBtn) {
        modalRetryBtn.addEventListener('click', function() {
            showModalStep('stepGeo');
            initEnrollmentFlow();
        });
    }

})();

// ============================================
// Modal Step Management
// ============================================
function showModalStep(stepId) {
    const steps = ['stepGeo', 'stepTaxId', 'stepPayment', 'stepProcessing', 'stepProvisioning', 'stepReady', 'stepError'];
    steps.forEach(function(id) {
        const el = document.getElementById(id);
        if (el) {
            el.style.display = id === stepId ? 'block' : 'none';
        }
    });
}

// ============================================
// Enrollment Flow Initialization
// ============================================
async function initEnrollmentFlow() {
    showModalStep('stepGeo');
    
    // Update plan info in modal
    const config = PLAN_CONFIG[enrollmentState.plan] || PLAN_CONFIG.pro;
    const planNameEl = document.getElementById('modalPlanName');
    const planPriceEl = document.getElementById('modalPlanPrice');
    const planTokensEl = document.getElementById('modalPlanTokens');
    
    if (planNameEl) planNameEl.textContent = config.name;
    if (planPriceEl) planPriceEl.textContent = config.price;
    if (planTokensEl) planTokensEl.textContent = config.tokens + ' tokens mensuales';

    // Detect country
    try {
        const response = await fetch(API_BASE + '/api/v2/admin/public/geo/detect');
        enrollmentState.geoConfig = await response.json();
        
        enrollmentState.detectedCountry = enrollmentState.geoConfig.geo?.country_code || 'US';
        enrollmentState.requiresTaxId = enrollmentState.geoConfig.show_tax_id || false;
        
        const countryName = enrollmentState.geoConfig.geo?.country_name || 'Unknown';
        const countryInfoEl = document.getElementById('modalCountryInfo');
        if (countryInfoEl) {
            countryInfoEl.textContent = 'Registrando desde: ' + countryName + ' (' + enrollmentState.detectedCountry + ')';
        }
        
        // Short delay for UX
        await new Promise(resolve => setTimeout(resolve, 800));
        
        if (enrollmentState.requiresTaxId) {
            // Ecuador - show tax ID validation
            const taxIdLabel = enrollmentState.geoConfig.tax_id_label || 'RUC/Cédula';
            const labelEl = document.getElementById('modalTaxIdLabel');
            const subtitleEl = document.getElementById('taxIdSubtitle');
            if (labelEl) labelEl.textContent = taxIdLabel;
            if (subtitleEl) subtitleEl.textContent = 'Ingresa tu ' + taxIdLabel + ' para continuar';
            showModalStep('stepTaxId');
        } else {
            // Other countries - go directly to payment
            showModalStep('stepPayment');
            initPayPalButtons();
        }
    } catch (err) {
        console.error('Geo detection failed:', err);
        // On error, skip to payment
        showModalStep('stepPayment');
        initPayPalButtons();
    }
}

// ============================================
// Tax ID Validation
// ============================================
async function validateModalIdentity() {
    const identifier = document.getElementById('modalIdentifier').value.trim();
    const statusEl = document.getElementById('modalValidationStatus');
    const validateBtn = document.getElementById('modalValidateBtn');

    if (!identifier) {
        statusEl.innerHTML = '<span class="error">Ingresa tu identificación</span>';
        return;
    }

    validateBtn.disabled = true;
    validateBtn.textContent = 'Verificando...';
    statusEl.innerHTML = '<span class="loading">Validando...</span>';

    try {
        const response = await fetch(API_BASE + '/api/v2/admin/public/validate/identity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier: identifier })
        });
        const result = await response.json();

        if (result.valid) {
            enrollmentState.validatedIdentifier = identifier;
            enrollmentState.identifierType = result.type;
            statusEl.innerHTML = '<span class="success">' + result.message + '</span>';
            
            // Short delay then proceed
            await new Promise(resolve => setTimeout(resolve, 500));
            showModalStep('stepPayment');
            initPayPalButtons();
        } else {
            statusEl.innerHTML = '<span class="error">' + result.message + '</span>';
            validateBtn.disabled = false;
            validateBtn.textContent = 'Verificar Identidad';
        }
    } catch (err) {
        statusEl.innerHTML = '<span class="error">Error de conexión. Intenta de nuevo.</span>';
        validateBtn.disabled = false;
        validateBtn.textContent = 'Verificar Identidad';
    }
}

// ============================================
// PayPal Button Initialization
// ============================================
function initPayPalButtons() {
    // Prevent double rendering
    if (paypalButtonsRendered) return;
    
    const container = document.getElementById('paypal-button-container');
    if (!container) return;
    
    // Check if PayPal SDK is loaded
    if (typeof paypal === 'undefined') {
        console.error('PayPal SDK not loaded');
        showPayPalError('PayPal no está disponible. Recarga la página.');
        return;
    }
    
    const config = PLAN_CONFIG[enrollmentState.plan] || PLAN_CONFIG.pro;
    
    paypal.Buttons({
        style: {
            layout: 'vertical',
            color: 'gold',
            shape: 'rect',
            label: 'paypal',
            height: 45
        },
        
        // Validate form before creating order
        onClick: function(data, actions) {
            const email = document.getElementById('modalEmail').value.trim();
            const name = document.getElementById('modalName').value.trim();
            const terms = document.getElementById('modalTerms').checked;
            
            if (!email || !name) {
                showPayPalError('Por favor completa tu email y nombre');
                return actions.reject();
            }
            
            if (!terms) {
                showPayPalError('Debes aceptar los Términos de Servicio');
                return actions.reject();
            }
            
            if (enrollmentState.requiresTaxId && !enrollmentState.validatedIdentifier) {
                showPayPalError('Primero debes verificar tu identificación fiscal');
                return actions.reject();
            }
            
            hidePayPalError();
            return actions.resolve();
        },
        
        // Create PayPal order via our backend
        createOrder: async function(data, actions) {
            const email = document.getElementById('modalEmail').value.trim();
            const name = document.getElementById('modalName').value.trim();
            
            try {
                const response = await fetch(API_BASE + '/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: email,
                        plan: enrollmentState.plan,
                        amount: config.priceNum,
                        name: name,
                        ruc: enrollmentState.validatedIdentifier || ''
                    })
                });
                
                const result = await response.json();
                
                if (result.success && result.order_id) {
                    // Store user info for later
                    enrollmentState.userEmail = email;
                    enrollmentState.userName = name;
                    return result.order_id;
                } else {
                    throw new Error(result.error || 'No se pudo crear la orden de PayPal');
                }
            } catch (err) {
                console.error('PayPal createOrder error:', err);
                showPayPalError(err.message || 'Error al crear la orden de pago');
                throw err;
            }
        },
        
        // Capture payment after user approves
        onApprove: async function(data, actions) {
            showModalStep('stepProcessing');
            
            try {
                // Capture the payment via our backend
                const captureResponse = await fetch(API_BASE + '/api/v2/admin/public/payment/paypal/capture/' + data.orderID, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const captureResult = await captureResponse.json();
                
                if (captureResult.success && captureResult.status === 'COMPLETED') {
                    // Payment successful - now create subscription
                    const subscriptionResponse = await fetch(API_BASE + '/api/v2/admin/public/subscription/create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            email: enrollmentState.userEmail,
                            name: enrollmentState.userName,
                            plan: enrollmentState.plan,
                            amount: config.priceNum,
                            ruc: enrollmentState.validatedIdentifier || '',
                            payment_provider: 'paypal',
                            paypal_order_id: data.orderID,
                            paypal_transaction_id: captureResult.transaction_id,
                            country_code: enrollmentState.detectedCountry
                        })
                    });
                    
                    const subscriptionResult = await subscriptionResponse.json();
                    
                    if (subscriptionResult.success) {
                        enrollmentState.apiKey = subscriptionResult.api_key;
                        enrollmentState.podId = subscriptionResult.pod_id;
                        
                        // Start provisioning animation
                        await startProvisioningAnimation(subscriptionResult);
                    } else {
                        showModalError(subscriptionResult.error || 'Error al crear la suscripción');
                    }
                } else {
                    showModalError(captureResult.error || 'El pago no se completó correctamente');
                }
            } catch (err) {
                console.error('PayPal onApprove error:', err);
                showModalError('Error al procesar el pago: ' + (err.message || 'Error desconocido'));
            }
        },
        
        onCancel: function(data) {
            console.log('PayPal payment cancelled:', data);
            showPayPalError('Pago cancelado. Puedes intentar de nuevo.');
        },
        
        onError: function(err) {
            console.error('PayPal error:', err);
            showPayPalError('Error de PayPal. Por favor intenta de nuevo.');
        }
    }).render('#paypal-button-container');
    
    paypalButtonsRendered = true;
}

function showPayPalError(message) {
    const errorEl = document.getElementById('paypalError');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }
}

function hidePayPalError() {
    const errorEl = document.getElementById('paypalError');
    if (errorEl) {
        errorEl.style.display = 'none';
    }
}

// ============================================
// Provisioning Animation
// ============================================
async function startProvisioningAnimation(result) {
    showModalStep('stepProvisioning');
    
    const steps = [
        { id: 'provStep1', delay: 0 },
        { id: 'provStep2', delay: 1000 },
        { id: 'provStep3', delay: 2500 },
        { id: 'provStep4', delay: 4000 }
    ];
    
    // Animate through steps
    for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, steps[i].delay > 0 ? steps[i].delay - (steps[i-1]?.delay || 0) : 0));
        
        // Mark previous as completed
        if (i > 0) {
            const prevStep = document.getElementById(steps[i-1].id);
            if (prevStep) {
                prevStep.classList.remove('active');
                prevStep.classList.add('completed');
                prevStep.querySelector('.provisioning-step__icon').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
            }
        }
        
        // Mark current as active
        const currentStep = document.getElementById(steps[i].id);
        if (currentStep) {
            currentStep.classList.add('active');
            if (i < steps.length - 1) {
                currentStep.querySelector('.provisioning-step__icon').innerHTML = '<div class="mini-spinner"></div>';
            }
        }
    }
    
    // Final step completion
    await new Promise(resolve => setTimeout(resolve, 1500));
    const lastStep = document.getElementById('provStep4');
    if (lastStep) {
        lastStep.classList.remove('active');
        lastStep.classList.add('completed');
        lastStep.querySelector('.provisioning-step__icon').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
    }
    
    // Show ready screen
    await new Promise(resolve => setTimeout(resolve, 500));
    showReadyScreen(result);
}

// ============================================
// Ready Screen
// ============================================
function showReadyScreen(result) {
    showModalStep('stepReady');
    
    const config = PLAN_CONFIG[enrollmentState.plan] || PLAN_CONFIG.pro;
    
    const apiKeyEl = document.getElementById('modalApiKey');
    const podUrlEl = document.getElementById('modalPodUrl');
    const finalPlanEl = document.getElementById('modalFinalPlan');
    const dashboardBtn = document.getElementById('modalGoToDashboard');
    
    if (apiKeyEl) apiKeyEl.textContent = result.api_key || 'gpb_' + Math.random().toString(36).substr(2, 12);
    if (podUrlEl) podUrlEl.textContent = result.pod_url || 'https://pod-' + (result.pod_id || 'xxx') + '.gpubroker.site';
    if (finalPlanEl) finalPlanEl.textContent = config.name;
    
    if (dashboardBtn) {
        dashboardBtn.href = API_BASE + '/admin/?key=' + (result.api_key || '');
    }
}

// ============================================
// Error Handling
// ============================================
function showModalError(message) {
    showModalStep('stepError');
    const errorMsgEl = document.getElementById('modalErrorMessage');
    if (errorMsgEl) {
        errorMsgEl.textContent = message;
    }
}
