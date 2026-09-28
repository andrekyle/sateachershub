/**
 * South African Teachers Hub Runtime Helper
 * This script provides runtime fixes for common issues
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if Font Awesome is loaded properly
    const checkFontAwesome = () => {
        const testIcon = document.createElement('i');
        testIcon.className = 'fas fa-check';
        testIcon.style.display = 'none';
        document.body.appendChild(testIcon);
        
        const computedStyle = window.getComputedStyle(testIcon);
        const isFontAwesomeLoaded = computedStyle.fontFamily.includes('Font Awesome') || 
                                   !computedStyle.fontFamily.includes('sans-serif');
        
        document.body.removeChild(testIcon);
        
        if (!isFontAwesomeLoaded) {
            console.warn('Font Awesome not loaded properly. Attempting to reload...');
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
            document.head.appendChild(link);
        }
    };
    
    // Run checks
    setTimeout(checkFontAwesome, 500);
    
    // Fix for any broken images
    document.querySelectorAll('img').forEach(img => {
        img.onerror = function() {
            this.onerror = null;
            this.src = '/static/images/logo.png';
            this.style.opacity = '0.5';
        };
    });
});
