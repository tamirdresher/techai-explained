# AdSense Setup Instructions

## Step 1: Register for Google AdSense
1. Visit [https://adsense.google.com](https://adsense.google.com)
2. Sign in with your Google account
3. Enter your website URL
4. Select your country, agree to Terms of Service
5. Click **Start using AdSense**

## Step 2: Add Verification Code
Google will provide a verification snippet. Add it to your site's `<head>` section.

## Step 3: Wait for Approval
- Approval typically takes 1-14 days
- Your site needs original content and a privacy policy
- Traffic helps but isn't strictly required

## Step 4: Create Ad Units
Create these ad units in your AdSense dashboard:

1. **Header Banner** (728x90 Leaderboard)
2. **Sidebar** (300x250 Medium Rectangle) 
3. **In-Article** (Fluid/Responsive)

## Step 5: Replace Placeholder Code
1. Find all `ca-pub-XXXXXXXXXXXXXXXX` in your layout templates
2. Replace with your actual AdSense publisher ID
3. Replace `data-ad-slot="XXXXXXXXXX"` with your ad unit slot IDs
4. Uncomment the `<ins class="adsbygoogle">` tags
5. Remove the placeholder `<div>` elements
6. Uncomment the AdSense script tag in `<head>`

## Step 6: Add AdSense Script to Head
Uncomment this in your base layout:
```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script>
```

## Revenue Expectations
- Blog/tutorial sites typically earn $2-8 RPM
- Focus on growing traffic through SEO and social media
- Higher-value topics (cloud, AI, DevOps) command higher CPMs
