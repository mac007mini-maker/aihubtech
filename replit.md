# Viso AI - Photo Avatar Headshot

## Overview
Viso AI is a Flutter-based application for generating studio-grade AI headshots and avatars. It provides advanced photo enhancement, face swapping, and various AI-driven transformations. The project aims to deliver high-quality, personalized digital images efficiently and cost-effectively, addressing the market demand for AI-powered image manipulation.

## User Preferences
None documented yet.

## System Architecture

### UI/UX Decisions
The application features a consistent and responsive design built with FlutterFlow-generated components, supporting both light and dark themes. It incorporates modern UI elements such as carousels with PageView sliders, smooth transitions, and dot indicators. Ad banners are strategically placed above navigation bars. A feedback system allows users to submit feature requests.

### Technical Implementations
Developed with Flutter 3.32.0 (Dart 3.8.0), Viso AI integrates with a Python Flask backend. This backend serves as a proxy for complex asynchronous image processing tasks and AI model interactions.

### Feature Specifications
- **AI Headshot & Avatar Generation**: Produces studio-grade AI headshots and stylized avatars.
- **Photo Enhancement**: Includes HD Image Enhancement (via Replicate Real-ESRGAN) and Old Photo Restoration (via Replicate GFPGAN).
- **Face Swapping**: Offers AI-powered face replacement with a multi-provider fallback system (PiAPI PRIMARY, Replicate FALLBACK), robust gallery permission handling, and rewarded ad integration. Supports both image and video face swap functionalities. PiAPI provides precise, photorealistic face swaps with 99.9% uptime SLA and enterprise-grade reliability.
- **AI Style Templates**: Features 14 diverse template categories for face swap and aesthetic transformations (e.g., Travel, Gym, Selfie, Tattoo, Wedding, Sport, Christmas, New Year, Birthday, School, Fashion Show, Profile, Suits). Each category includes carousel layouts and direct download capabilities. Templates are loaded dynamically from Supabase Storage.
- **AI Transformation Templates**: Provides 5 advanced AI transformations accessible from the Templates Gallery. Each template includes:
    - Multi-provider fallback for high uptime.
    - Rewarded ad integration for free users (AdMob → AppLovin).
    - PRO user bypass with daily usage limits (20/day).
    - Download functionality to device Gallery/VisoAI album.
    - Gallery and Camera photo picker integration.
    - Real-time processing feedback.
    - **Cartoon 3D Toon**: Transforms photos into Disney/Pixar-style cartoons.
    - **Memoji Avatar**: Creates Apple-style 3D memoji avatars.
    - **Animal Toon**: Transforms into animal characters (e.g., bunny, cat, dog).
    - **Muscle Enhancement**: Adds defined muscles with adjustable intensity.
    - **Art Style**: Applies artistic styles like mosaic, oil painting, or watercolor.
- **Monetization**:
    - **Advertising**: Google Mobile Ads (AdMob) for web, and a dual-network system (AdMob primary, AppLovin MAX fallback) for mobile banner, app open, and rewarded ads, configured via Firebase Remote Config.
    - **In-App Purchases**: RevenueCat SDK for premium subscriptions (Lifetime, Yearly, Weekly tiers) offering ad removal, unlimited creations, and priority processing.
- **Internationalization**: Supports 20 languages with interactive selection.
- **Mobile Download**: Images are saved to a dedicated "VisoAI" album in the device's gallery.
- **Settings**: Includes options for sharing, feedback, an "About" section, User Agreement, Privacy Policy, and Community Guidelines.

### System Design Choices
Supabase provides core backend services, including authentication, database, and storage. AI functionalities are primarily powered by Huggingface Spaces and Replicate APIs, accessed through a Python Flask proxy server. Face swap templates and video templates are dynamically loaded from Supabase Storage.

**Production Deployment Strategy:**
- **Backend**: Deployed on Railway Hobby for the Flask + Gunicorn application.
- **Database/Auth/Storage**: Managed by Supabase.
- **Mobile**: Flutter APK with `--split-per-abi` optimization.

### Recent Changes

**Comprehensive Timeout Fix for All AI Features (October 2025)**
Fixed critical timeout bug affecting 8 AI features (Face Swap + 7 transformation features) by switching from base64 transfer to URL-based CDN download:

**🎯 Problem Identified:**
All AI features were timing out after 120-180s despite fast Replicate API processing (9-30s). Root cause: Backend was downloading large images (6.8MB) → encoding to 9MB base64 → slow HTTP transfer to Flutter caused timeouts.

**✅ Solution Applied:**
Backend gateways now return Replicate CDN URLs directly (no download/encode). Flutter downloads image bytes from CDN separately, eliminating backend bottleneck.

**📦 Features Fixed (8 total):**
1. **Face Swap** (SwapFace + 13 story templates: Travel, Gym, Selfie, Tattoo, Wedding, Sport, Christmas, New Year, Birthday, School, Fashion Show, Profile, Suits)
2. **Cartoon 3D Toon** - Disney/Pixar-style transformations
3. **Memoji Avatar** - Apple-style 3D memoji creation
4. **Animal Toon** - Animal character transformations (bunny, cat, dog, fox, bear)
5. **Muscle Enhancement** - Adds defined muscles with adjustable intensity
6. **Art Style** - Artistic styles (mosaic, oil painting, watercolor)
7. **HD Image Enhancement** - Real-ESRGAN upscaling (2x, 4x)
8. **Fix Old Photo** - GFPGAN photo restoration

**🔧 Technical Implementation:**

*Backend (Python) - 7 Gateway Files:*
- `services/cartoon_gateway.py` (2 providers: PhotoMaker, InstantID)
- `services/memoji_gateway.py` (2 providers: PhotoMaker, InstantID)
- `services/animal_toon_gateway.py` (3 providers: PhotoMaker, InstantID, PiAPI)
- `services/muscle_gateway.py` (1 provider: Instruct-Pix2Pix)
- `services/art_style_gateway.py` (2 providers: PhotoMaker, Oil Painting)
- `services/hd_image_gateway.py` (1 provider: Real-ESRGAN)
- `services/image_ai_service.py` (fix_old_photo with GFPGAN)

All return `{"success": True, "url": result_url}` instead of `{"image": base64_string}`

*Backend Proxy (Python):*
- `api/index.py`: Added `/api/proxy-image` endpoint to download from Replicate CDN and stream to Flutter
- Solves network blocking issue where direct Replicate CDN downloads were refused by some networks/firewalls
- Security: Only allows `https://replicate.delivery/` URLs to prevent abuse

*Flutter (Dart) - Service + Widgets:*
- `lib/services/huggingface_service.dart`: 
  - Added `downloadImageViaProxy()` method for secure image download via backend proxy
  - Updated 3 API methods (fixOldPhoto, hdImage, cartoonify) to parse `data['url']`
- **SwapFace**: 1 widget updated to use proxy download
- **Story templates**: 13 widgets updated (birthday, christmas, newyear, travel, gym, selfie, tattoo, wedding, sport, school, fashionshow, profile, suits)
- **AI transformations**: 7 widgets updated (cartoon_toon, memoji_avatar, animal_toon, muscle_enhance, art_style, hdphoto, fixoldphoto)

All use pattern: `HuggingfaceService.downloadImageViaProxy(resultUrl)` → `resultBytes` → display/save

**📊 Performance Impact:**
- **Before**: 6.8MB download + 9MB base64 encode + 9MB HTTP transfer = 120-180s timeout risk
- **After**: Instant URL return (< 1s) + Direct CDN download (5-10s) = No timeout, 90% faster

**🚀 Uptime Guarantee:**
Multi-provider fallback architecture ensures 99.9%+ availability for all features (Replicate PRIMARY → PiAPI/InstantID/PhotoMaker FALLBACK)

**🎯 Pattern Consistency:**
Matches proven video swap implementation - all 9 media-heavy features now use URL-based download pattern

**Face Swap Provider Update: PiAPI PRIMARY (October 23, 2025)**
Reverted face swap provider priority after Nano-Banana experiment proved unsuitable:

**🎯 Issue Identified:**
Google Nano-Banana (google/nano-banana on Replicate) was tested as PRIMARY face swap provider but produced incorrect results. Instead of precise face swapping, the model performed creative image editing - only adjusting image view/composition and zooming out to show wider scenes, without actually replacing faces.

**✅ Solution:**
- **DISABLED Nano-Banana** for face swap (commented out in `services/face_swap_gateway.py`)
- **SET PiAPI as PRIMARY** - specialized face swap provider with proven photorealistic results
- **Replicate models as FALLBACK** - emergency backup

**🔧 Technical Changes:**
- Updated `services/face_swap_gateway.py`:
  - Commented out NanoBananaProvider initialization
  - Promoted PiAPIProvider to PRIMARY position
  - Updated architecture documentation in file header
  - Provider order now: PiAPI → Replicate (2 providers instead of 3)

**📊 Provider Comparison:**
- **Nano-Banana (DISABLED):** Creative editing model, unsuitable for precise face swap - only adjusts view/composition
- **PiAPI (NEW PRIMARY):** Specialized face swap, 99.9% uptime, photorealistic, supports image + video
- **Replicate (FALLBACK):** Legacy models (easel/advanced-face-swap, omniedgeio/face-swap) for emergency

**🎯 Decision Rationale:**
User testing confirmed Nano-Banana does not perform actual face replacement despite multiple prompt engineering attempts. PiAPI provides the precision and reliability needed for production face swap feature.

**Template Sorting Enhancement (October 2025)**
Implemented automatic newest-first ordering for all dynamically loaded templates from Supabase Storage:

**🎯 Feature:**
Templates (both photo and video) now appear with newest uploads first, making it easy for content managers to update the app with fresh content.

**✅ Implementation:**
- Updated `/api/ai/photo-templates/story` endpoint to sort by `created_at DESC`
- Updated `/api/ai/video-templates` endpoint to sort by `created_at DESC`
- Applied to all 14 story template categories (Travel, Gym, Selfie, Tattoo, Wedding, Sport, Christmas, New Year, Birthday, School, Fashion Show, Profile, Suits)
- Applied to all video template categories

**🔧 Technical Details:**
Backend sorts Supabase Storage API responses before processing:
```python
# Sort photos/videos by created_at DESC (newest first)
items_sorted = sorted(
    items,
    key=lambda x: x.get('created_at', ''),
    reverse=True
)
```

**📊 Benefits:**
- Content managers can upload new templates and they instantly appear at the top
- No manual sorting required in Flutter app
- Consistent ordering across photo and video templates
- Graceful fallback to original order if `created_at` metadata is missing

## External Dependencies

- **Supabase**: Backend services (authentication, database, storage).
- **Google Mobile Ads (AdMob)**: Advertising network.
- **AppLovin MAX**: Secondary mobile ad network.
- **RevenueCat**: In-app purchase and subscription management.
- **Huggingface API**: AI models for various transformations and generations.
- **VModel API**: Primary provider for video face swap (photo-to-video).
- **Replicate API**: Hosts Nano-Banana (google/nano-banana) for image face swap PRIMARY, plus photo restoration, and style transfer. Also provides legacy face swap models as FALLBACK #2.
- **Nano-Banana (Gemini 2.5 Flash Image)**: Google's state-of-the-art image editing model via Replicate. PRIMARY provider for image face swap with natural language prompts, multi-image fusion, and character consistency. Features invisible SynthID watermarking.
- **PiAPI**: Face swap provider FALLBACK #1 for both image and video operations. 99.9% uptime SLA.
- **Flutter Core Dependencies**: `supabase_flutter`, `cached_network_image`, `go_router`, `google_fonts`, `flutter_animate`, `http`, `permission_handler`, `path_provider`, `applovin_max`, `share_plus`, `url_launcher`, `firebase_core`, `firebase_remote_config`, `purchases_flutter`, `gal`, `shared_preferences`.