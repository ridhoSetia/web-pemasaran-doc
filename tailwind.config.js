/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './store/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        "primary":                   "#154212",
        "on-primary":                "#FFFFFF",
        "primary-container":         "#2D5A27",
        "on-primary-container":      "#9DD090",
        "secondary":                 "#D4A017",
        "on-secondary":              "#3B2900",
        "secondary-container":       "#FEF3C7",
        "on-secondary-container":    "#7C5A00",
        "background":                "#FAF7F0",
        "on-background":             "#161A14",
        "surface":                   "#F5F1E8",
        "on-surface":                "#161A14",
        "surface-variant":           "#EDE8DD",
        "on-surface-variant":        "#3D4B3A",
        "surface-container-lowest":  "#FFFFFF",
        "outline":                   "#6B7A68",
        "outline-variant":           "#C8BFB0",
        "error":                     "#BA1A1A",
        "on-error":                  "#FFFFFF",
        "error-container":           "#FFDAD6",
        "on-error-container":        "#93000A",
      },
      borderRadius: { 
        DEFAULT: '0.25rem', lg: '0.5rem', xl: '0.75rem', '2xl': '1rem', full: '9999px' 
      },
      spacing: { 
        xl: '40px', gutter: '20px', unit: '4px', md: '16px', sm: '8px', 
        xs: '4px', 'container-margin': '32px', lg: '24px', 
        'container-max': '1280px', xxl: '48px' 
      },
      fontFamily: {
        'label-sm': ['Open Sans', 'sans-serif'],
        h1: ['Open Sans', 'sans-serif'],
        h2: ['Open Sans', 'sans-serif'],
        h3: ['Open Sans', 'sans-serif'],
        'body-lg': ['Open Sans', 'sans-serif'],
        'body-md': ['Open Sans', 'sans-serif']
      },
      fontSize: {
        // H1 lebih proporsional untuk dashboard, tidak terlalu agresif
        h1: ['32px', { lineHeight: '1.25', letterSpacing: '-0.01em', fontWeight: '700' }],
        // H2 terasa lebih elegan dan tidak "tabrakan" dengan H1
        h2: ['24px', { lineHeight: '1.3', fontWeight: '600' }],
        // H3 lebih pas untuk sub-heading menu atau section
        h3: ['18px', { lineHeight: '1.4', fontWeight: '600' }],
        // 16px adalah standar industri untuk body text yang nyaman dibaca
        'body-lg': ['16px', { lineHeight: '1.6', fontWeight: '400' }],
        // 14px untuk metadata atau info pendukung agar tidak terlalu mencolok
        'body-md': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        // Label dengan letter-spacing sedikit lebih rapat
        'label-sm': ['12px', { lineHeight: '1.2', letterSpacing: '0.02em', fontWeight: '600' }],
        // Caption yang tetap terbaca (12px)
        caption: ['12px', { lineHeight: '1.4', fontWeight: '400' }]
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ],
}