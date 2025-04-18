/**
 * Micro-interactions and animations for Bybit Trading Bot
 * Enhances the user experience with subtle animations and interactions
 */

// Initialize micro-interactions when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add page transition effect
    addPageTransitionEffect();
    
    // Add hover effects to cards
    addCardHoverEffects();
    
    // Add button click effects
    addButtonClickEffects();
    
    // Add scroll animations
    addScrollAnimations();
    
    // Add input focus effects
    addInputFocusEffects();
    
    // Add navbar scroll effect
    addNavbarScrollEffect();
    
    // Add loading indicators
    enhanceLoadingIndicators();
    
    // Add smooth scrolling
    enableSmoothScrolling();
});

// Add page transition effect
function addPageTransitionEffect() {
    // Add a class to the body when page is loaded
    document.body.classList.add('page-loaded');
    
    // Add transition class to main content
    const mainContent = document.querySelector('main') || document.querySelector('.container-fluid');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    // Add transition to all links that lead to internal pages
    document.querySelectorAll('a').forEach(link => {
        // Only apply to internal links that are not # links or javascript: links
        if (link.href && 
            link.href.startsWith(window.location.origin) && 
            !link.href.includes('#') && 
            !link.href.includes('javascript:')) {
            
            link.addEventListener('click', function(e) {
                // Don't apply to links with target="_blank"
                if (this.target === '_blank') return;
                
                e.preventDefault();
                const href = this.href;
                
                // Add exit animation
                if (mainContent) {
                    mainContent.style.opacity = '0';
                    mainContent.style.transform = 'translateY(-20px)';
                }
                
                // Navigate after animation completes
                setTimeout(() => {
                    window.location.href = href;
                }, 300);
            });
        }
    });
}

// Add hover effects to cards
function addCardHoverEffects() {
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.05)';
        });
    });
    
    // Special effect for status cards
    document.querySelectorAll('.status-card').forEach(card => {
        const icon = card.querySelector('.status-icon');
        if (icon) {
            card.addEventListener('mouseenter', function() {
                icon.style.transform = 'scale(1.1)';
            });
            
            card.addEventListener('mouseleave', function() {
                icon.style.transform = 'scale(1)';
            });
        }
    });
}

// Add button click effects
function addButtonClickEffects() {
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('mousedown', function() {
            this.style.transform = 'scale(0.95)';
        });
        
        button.addEventListener('mouseup', function() {
            this.style.transform = '';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// Add scroll animations
function addScrollAnimations() {
    // Only apply if IntersectionObserver is supported
    if ('IntersectionObserver' in window) {
        const appearOptions = {
            threshold: 0.15,
            rootMargin: '0px 0px -100px 0px'
        };
        
        const appearOnScroll = new IntersectionObserver(function(entries, observer) {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                
                entry.target.classList.add('appear');
                observer.unobserve(entry.target);
            });
        }, appearOptions);
        
        // Apply to cards, rows, and other elements
        document.querySelectorAll('.card, .row > [class*="col-"], .chart-container, .log-container').forEach(element => {
            element.classList.add('fade-in-element');
            appearOnScroll.observe(element);
        });
    }
}

// Add input focus effects
function addInputFocusEffects() {
    document.querySelectorAll('.form-control, .form-select').forEach(input => {
        const formGroup = input.closest('.mb-3') || input.closest('.form-group');
        
        input.addEventListener('focus', function() {
            if (formGroup) {
                formGroup.classList.add('focused');
            }
        });
        
        input.addEventListener('blur', function() {
            if (formGroup) {
                formGroup.classList.remove('focused');
            }
        });
    });
}

// Add navbar scroll effect
function addNavbarScrollEffect() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 10) {
            navbar.classList.add('navbar-scrolled');
        } else {
            navbar.classList.remove('navbar-scrolled');
        }
    });
}

// Enhance loading indicators
function enhanceLoadingIndicators() {
    // Replace default loading spinner with a more elegant one
    const loadingSpinner = document.querySelector('.spinner-border');
    if (loadingSpinner) {
        loadingSpinner.classList.add('enhanced-spinner');
    }
    
    // Add loading state to buttons
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function() {
            // Only apply to buttons that trigger loading
            if (this.dataset.loading === 'true') {
                const originalText = this.innerHTML;
                this.setAttribute('data-original-text', originalText);
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Loading...';
                this.disabled = true;
                
                // Reset after timeout (in a real app, this would be after the action completes)
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }, 2000);
            }
        });
    });
}

// Enable smooth scrolling
function enableSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Add ripple effect to buttons
function addRippleEffect(element) {
    element.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
        ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
        
        element.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}

// Add pulse animation to important elements
function addPulseAnimation() {
    // Add pulse animation to elements that need attention
    document.querySelectorAll('[data-pulse="true"]').forEach(element => {
        element.classList.add('pulse');
    });
}

// Show toast notification with animation
function showAnimatedToast(message, type = 'info') {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        
        // Add animation to the latest toast
        setTimeout(() => {
            const toasts = document.querySelectorAll('.toast');
            if (toasts.length > 0) {
                const latestToast = toasts[toasts.length - 1];
                latestToast.classList.add('animated-toast');
            }
        }, 100);
    }
}

// Add shimmer effect to loading elements
function addShimmerEffect() {
    document.querySelectorAll('[data-loading="true"]').forEach(element => {
        element.classList.add('loading-shimmer');
        
        // Remove shimmer after loading is complete
        setTimeout(() => {
            element.classList.remove('loading-shimmer');
            element.removeAttribute('data-loading');
        }, 2000);
    });
}

// Enhance form validation feedback
function enhanceFormValidation() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
                
                // Add shake animation to invalid fields
                this.querySelectorAll(':invalid').forEach(field => {
                    field.classList.add('shake-animation');
                    
                    // Remove animation after it completes
                    setTimeout(() => {
                        field.classList.remove('shake-animation');
                    }, 600);
                });
            }
            
            form.classList.add('was-validated');
        });
    });
}

// Add these functions to the global scope
window.addRippleEffect = addRippleEffect;
window.showAnimatedToast = showAnimatedToast;
window.addShimmerEffect = addShimmerEffect;
window.enhanceFormValidation = enhanceFormValidation;
window.addPulseAnimation = addPulseAnimation;
