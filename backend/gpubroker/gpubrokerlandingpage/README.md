# GPUBROKER Landing Page

Public marketing website for GPUBROKER at `gpubroker.live`.

## Overview

Static landing page built with HTML5, CSS3, and vanilla JavaScript. Dark theme with green accents, fully responsive, optimized for conversion.

## Structure

```
gpubrokerlandingpage/
├── index.html          # Main HTML file
├── css/
│   └── styles.css      # All styles (mobile-first)
├── js/
│   └── main.js         # Interactivity & analytics
├── images/             # Images (to be added)
│   ├── favicon.ico
│   ├── logo.svg
│   └── og-image.png
└── README.md           # This file
```

## Local Development

1. Open `index.html` directly in a browser, or
2. Use a local server:

```bash
# Python 3
python -m http.server 8000

# Node.js (npx)
npx serve .

# PHP
php -S localhost:8000
```

Then visit `http://localhost:8000`

## Deployment to AWS S3 + CloudFront

### Prerequisites

- AWS CLI configured with appropriate credentials
- S3 bucket created for hosting
- CloudFront distribution (optional but recommended)

### Step 1: Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://gpubroker-landing --region us-east-1

# Enable static website hosting
aws s3 website s3://gpubroker-landing \
    --index-document index.html \
    --error-document index.html
```

### Step 2: Configure Bucket Policy

Create `bucket-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::gpubroker-landing/*"
        }
    ]
}
```

Apply policy:

```bash
aws s3api put-bucket-policy \
    --bucket gpubroker-landing \
    --policy file://bucket-policy.json
```

### Step 3: Upload Files

```bash
# Sync all files
aws s3 sync . s3://gpubroker-landing \
    --exclude ".git/*" \
    --exclude "README.md" \
    --exclude "*.md"

# Set cache headers for static assets
aws s3 cp s3://gpubroker-landing/css/ s3://gpubroker-landing/css/ \
    --recursive \
    --metadata-directive REPLACE \
    --cache-control "max-age=31536000"

aws s3 cp s3://gpubroker-landing/js/ s3://gpubroker-landing/js/ \
    --recursive \
    --metadata-directive REPLACE \
    --cache-control "max-age=31536000"

# Set shorter cache for HTML
aws s3 cp s3://gpubroker-landing/index.html s3://gpubroker-landing/index.html \
    --metadata-directive REPLACE \
    --cache-control "max-age=3600"
```

### Step 4: Create CloudFront Distribution

```bash
aws cloudfront create-distribution \
    --origin-domain-name gpubroker-landing.s3.amazonaws.com \
    --default-root-object index.html
```

### Step 5: Configure Custom Domain

1. Request SSL certificate in ACM (us-east-1 for CloudFront)
2. Add CNAME record: `gpubroker.live` → CloudFront distribution
3. Update CloudFront with custom domain and certificate

## Configuration

### Google Analytics

Replace `G-XXXXXXXXXX` in `index.html` with your actual GA4 Measurement ID:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-YOUR-ID"></script>
<script>
    gtag('config', 'G-YOUR-ID');
</script>
```

### Checkout URL

The landing page redirects to checkout at:
```
https://admin.gpubroker.live/checkout?plan={plan}
```

Plans: `trial`, `basic`, `pro`, `corp`, `enterprise`

## Images Required

Create/add these images to the `images/` folder:

- `favicon.ico` - 32x32 favicon
- `apple-touch-icon.png` - 180x180 iOS icon
- `logo.svg` - GPUBROKER logo (currently inline SVG)
- `og-image.png` - 1200x630 Open Graph image for social sharing

## Performance Checklist

- [x] Mobile-first CSS
- [x] Minimal JavaScript (vanilla, no frameworks)
- [x] CSS variables for theming
- [x] Semantic HTML structure
- [x] Lazy loading ready
- [ ] Image optimization (WebP with fallbacks)
- [ ] Critical CSS inlining (optional)
- [ ] Service worker (optional)

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+
- Mobile browsers (iOS Safari, Chrome Android)

## License

Copyright © 2025 GPUBROKER / SOMATECH DEV. All rights reserved.
