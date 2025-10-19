#!/usr/bin/env python3
"""
Viso AI Backend API for Vercel
Converted from BaseHTTPRequestHandler to Flask for serverless deployment
"""
import os
import sys
import json
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.image_ai_service import image_ai_service
from services.face_swap_gateway import face_swap_gateway, FaceSwapMediaType
from services.hd_image_gateway import hd_image_gateway
from services.cartoon_gateway import cartoon_gateway
from services.memoji_gateway import memoji_gateway
from services.animal_toon_gateway import animal_toon_gateway
from services.muscle_gateway import muscle_gateway
from services.art_style_gateway import art_style_gateway
from services.video_swap_gateway import video_swap_gateway

app = Flask(__name__)
CORS(app)

# Environment variables
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'Viso AI Backend',
        'version': '1.0.0',
        'endpoints': [
            '/api/huggingface/text-generation',
            '/api/huggingface/text-to-image',
            '/api/ai/hd-image',
            '/api/ai/fix-old-photo',
            '/api/ai/cartoonify',
            '/api/ai/face-swap',
            '/api/ai/face-swap-v2',
            '/api/ai/video-swap',
            '/api/ai/video-swap/download',
            '/api/ai/video-templates',
            '/api/ai/photo-templates/swapface',
            '/api/ai/photo-templates/story',
            '/api/ai/cartoon',
            '/api/ai/memoji',
            '/api/ai/animal-toon',
            '/api/ai/muscle',
            '/api/ai/art-style'
        ]
    })

@app.route('/api/huggingface/text-generation', methods=['POST'])
def text_generation():
    """Text generation using Huggingface models"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        model = data.get('model', 'mistralai/Mistral-7B-Instruct-v0.2')
        
        if not HUGGINGFACE_TOKEN:
            return jsonify({'error': 'HUGGINGFACE_TOKEN not configured'}), 500
        
        import requests as http_requests
        hf_url = f'https://api-inference.huggingface.co/models/{model}'
        payload = {
            'inputs': prompt,
            'parameters': {
                'max_new_tokens': data.get('max_tokens', 250),
                'temperature': data.get('temperature', 0.7),
                'top_p': data.get('top_p', 0.9),
            }
        }
        
        response = http_requests.post(
            hf_url,
            headers={'Authorization': f'Bearer {HUGGINGFACE_TOKEN}'},
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'result': response.json()})
        else:
            return jsonify({'error': f'Huggingface API error: {response.text}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/huggingface/text-to-image', methods=['POST'])
def text_to_image():
    """Text to image generation using Huggingface models"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        model = data.get('model', 'stabilityai/stable-diffusion-2-1')
        
        if not HUGGINGFACE_TOKEN:
            return jsonify({'error': 'HUGGINGFACE_TOKEN not configured'}), 500
        
        import requests as http_requests
        import base64
        
        hf_url = f'https://api-inference.huggingface.co/models/{model}'
        payload = {'inputs': prompt}
        
        response = http_requests.post(
            hf_url,
            headers={'Authorization': f'Bearer {HUGGINGFACE_TOKEN}'},
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            image_bytes = response.content
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            return jsonify({
                'success': True,
                'image': f'data:image/png;base64,{image_base64}'
            })
        else:
            return jsonify({'error': f'Huggingface API error: {response.text}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/hd-image', methods=['POST'])
def hd_image():
    """HD Image Enhancement using Multi-Provider Gateway (Replicate PRIMARY → PiAPI FALLBACK)"""
    try:
        data = request.get_json()
        image_base64 = data.get('image', '')
        scale = data.get('scale', 4)
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        # Use HD Image Gateway (Replicate PRIMARY, skips slow Huggingface)
        result = asyncio.run(hd_image_gateway.enhance_image(image_base64, scale))
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/fix-old-photo', methods=['POST'])
def fix_old_photo():
    """Fix Old Photo using GFPGAN"""
    try:
        data = request.get_json()
        image_base64 = data.get('image', '')
        version = data.get('version', 'v1.3')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        result = asyncio.run(image_ai_service.fix_old_photo(image_base64, version))
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/cartoonify', methods=['POST'])
def cartoonify():
    """Cartoonify image using VToonify"""
    try:
        data = request.get_json()
        image_base64 = data.get('image', '')
        style = data.get('style', 'cartoon')
        style_degree = data.get('style_degree', 0.5)
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        result = asyncio.run(image_ai_service.cartoonify(image_base64, style, style_degree))
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/face-swap', methods=['POST'])
def face_swap_legacy():
    """Face Swap (Legacy endpoint) - redirects to v2"""
    return face_swap_v2()

@app.route('/api/ai/face-swap-v2', methods=['POST'])
def face_swap_v2():
    """Face Swap using Multi-Provider Gateway (Replicate → PiAPI)"""
    try:
        print("📥 [FACE_SWAP] Received request")
        data = request.get_json()
        
        target_image = data.get('target_image', '')
        source_face = data.get('source_face', '')
        
        print(f"🖼️  [FACE_SWAP] Target: {target_image[:50]}...")
        print(f"👤 [FACE_SWAP] Source: {source_face[:50]}...")
        
        if not target_image or not source_face:
            return jsonify({'error': 'Both target_image and source_face required'}), 400
        
        print("🚀 [FACE_SWAP] Calling gateway...")
        result = asyncio.run(face_swap_gateway.swap_face(
            target=target_image,
            source=source_face,
            media_type=FaceSwapMediaType.IMAGE
        ))
        
        print(f"📤 [FACE_SWAP] Result: success={result.get('success')}")
        
        if result.get('success'):
            # Return URL directly (Flutter will download) - fixes timeout issue
            result_url = result.get('result_url')
            if result_url:
                print(f"✅ [FACE_SWAP] Returning URL: {result_url[:80]}...")
                return jsonify({
                    'success': True,
                    'url': result_url,
                    'provider': result.get('provider', 'unknown')
                })
            else:
                return jsonify({'success': False, 'error': 'No result URL in response'}), 500
        else:
            error_msg = result.get('error', 'Unknown error')
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except Exception as e:
        print(f"❌ [FACE_SWAP] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/video-swap', methods=['POST'])
def video_swap():
    """Video Face Swap using Multi-Provider Gateway (PiAPI → Replicate → VModel)"""
    try:
        print("📥 [VIDEO_SWAP] Received request")
        data = request.get_json()
        
        user_image = data.get('user_image', '')
        template_video_url = data.get('template_video_url', '')
        
        if not user_image or not template_video_url:
            return jsonify({'error': 'Both user_image and template_video_url required'}), 400
        
        print(f"🚀 [VIDEO_SWAP] Starting swap - Template: {template_video_url}")
        result = asyncio.run(video_swap_gateway.swap_video(user_image, template_video_url))
        
        print(f"📤 [VIDEO_SWAP] Result: success={result.get('success')}, provider={result.get('provider')}")
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ [VIDEO_SWAP] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/video-swap/download', methods=['POST'])
def download_video():
    """Proxy video download from CDN to avoid client-side connection issues"""
    try:
        print("📥 [VIDEO_DOWNLOAD] Received download request")
        data = request.get_json()
        
        video_url = data.get('video_url', '')
        if not video_url:
            return jsonify({'error': 'video_url required'}), 400
        
        # SECURITY: Validate URL is from trusted CDN providers only (prevent SSRF)
        from urllib.parse import urlparse
        parsed_url = urlparse(video_url)
        
        # Enforce HTTPS only
        if parsed_url.scheme != 'https':
            print(f"⚠️ [VIDEO_DOWNLOAD] Blocked non-HTTPS scheme: {parsed_url.scheme}")
            return jsonify({'error': 'Only HTTPS URLs are allowed'}), 403
        
        # Reject URLs with credentials (userinfo) to prevent bypass attacks
        if parsed_url.username or parsed_url.password:
            print(f"⚠️ [VIDEO_DOWNLOAD] Blocked URL with credentials")
            return jsonify({'error': 'URLs with credentials are not allowed'}), 403
        
        # Use .hostname to properly extract host (ignores credentials and port)
        hostname = parsed_url.hostname
        if not hostname:
            print(f"⚠️ [VIDEO_DOWNLOAD] Invalid URL: no hostname")
            return jsonify({'error': 'Invalid URL'}), 400
        
        hostname = hostname.lower()  # Normalize to lowercase
        
        allowed_domains = [
            'replicate.delivery',      # Replicate CDN
            'cdn.vmimgs.com',           # VModel CDN
            'pbxt.replicate.delivery',  # Replicate alternative CDN
        ]
        
        # Check if hostname exactly matches OR is a subdomain of allowed domains
        is_allowed = False
        for domain in allowed_domains:
            if hostname == domain or hostname.endswith('.' + domain):
                is_allowed = True
                break
        
        if not is_allowed:
            print(f"⚠️ [VIDEO_DOWNLOAD] Blocked untrusted domain: {hostname}")
            return jsonify({'error': 'Video URL must be from trusted provider CDN'}), 403
        
        print(f"⬇️ [VIDEO_DOWNLOAD] Downloading from: {video_url[:100]}...")
        
        import requests as http_requests
        from flask import Response
        
        # Download video from CDN with streaming
        video_response = http_requests.get(video_url, stream=True, timeout=300)
        video_response.raise_for_status()
        
        print(f"✅ [VIDEO_DOWNLOAD] Downloaded successfully, streaming to client")
        
        # Stream video bytes to client
        return Response(
            video_response.iter_content(chunk_size=8192),
            content_type='video/mp4',
            headers={
                'Content-Disposition': 'attachment; filename="viso_ai_video.mp4"'
            }
        )
        
    except Exception as e:
        print(f"❌ [VIDEO_DOWNLOAD] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/video-templates', methods=['GET'])
def get_video_templates():
    """Load video templates from Supabase Storage dynamically - 100% DYNAMIC!"""
    try:
        print("📥 [VIDEO_TEMPLATES] Fetching from Supabase...")
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        import requests as http_requests
        
        bucket_name = 'video-swap-templates'
        storage_url = f"{supabase_url}/storage/v1/object/list/{bucket_name}"
        
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}'
        }
        
        # Step 1: List root folder to get all categories (folders)
        response = http_requests.post(
            storage_url,
            headers=headers,
            json={'prefix': '', 'limit': 1000},
            timeout=10
        )
        response.raise_for_status()
        folders = response.json()
        
        # Step 2: For each category, list all videos inside
        templates = {}
        for folder_item in folders:
            category = folder_item.get('name')
            if not category:
                continue
            
            # List videos in this category folder
            folder_response = http_requests.post(
                storage_url,
                headers=headers,
                json={'prefix': f'{category}/', 'limit': 1000},
                timeout=10
            )
            folder_response.raise_for_status()
            videos = folder_response.json()
            
            # Sort videos by created_at DESC (newest first)
            videos_sorted = sorted(
                videos,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # Process each video in this category
            for video_item in videos_sorted:
                filename = video_item.get('name')
                if not filename or not filename.endswith('.mp4'):
                    continue
                
                if category not in templates:
                    templates[category] = []
                
                video_path = f"{category}/{filename}"
                video_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{video_path}"
                
                templates[category].append({
                    'id': video_path.replace('/', '_').replace('.mp4', ''),
                    'title': filename.replace('.mp4', '').replace('_', ' ').title(),
                    'video_url': video_url,
                    'thumbnail_url': video_url,
                    'category': category,
                    'filename': filename
                })
        
        total_videos = sum(len(v) for v in templates.values())
        print(f"✅ [VIDEO_TEMPLATES] Found {total_videos} videos in {len(templates)} categories (DYNAMIC)")
        
        # Fallback to REAL videos from Supabase if Storage List API fails
        if total_videos == 0:
            print("⚠️  [VIDEO_TEMPLATES] Storage List API failed, using direct video URLs")
            base_url = f"{supabase_url}/storage/v1/object/public/video-swap-templates"
            templates = {
                'fashion': [
                    {'id': 'fashion_fashion', 'title': 'Fashion', 'video_url': f'{base_url}/fashion/fashion.mp4', 'thumbnail_url': f'{base_url}/fashion/fashion.mp4', 'category': 'fashion'},
                    {'id': 'fashion_nicegirl', 'title': 'Nice Girl', 'video_url': f'{base_url}/fashion/nicegirl.mp4', 'thumbnail_url': f'{base_url}/fashion/nicegirl.mp4', 'category': 'fashion'},
                ],
                'fitness': [
                    {'id': 'fitness_gym', 'title': 'Gym', 'video_url': f'{base_url}/fitness/gym.mp4', 'thumbnail_url': f'{base_url}/fitness/gym.mp4', 'category': 'fitness'},
                    {'id': 'fitness_yoga', 'title': 'Yoga', 'video_url': f'{base_url}/fitness/yoga.mp4', 'thumbnail_url': f'{base_url}/fitness/yoga.mp4', 'category': 'fitness'},
                ],
                'people': [
                    {'id': 'people_foodman', 'title': 'Food Man', 'video_url': f'{base_url}/people/foodman.mp4', 'thumbnail_url': f'{base_url}/people/foodman.mp4', 'category': 'people'},
                    {'id': 'people_people', 'title': 'People', 'video_url': f'{base_url}/people/people.mp4', 'thumbnail_url': f'{base_url}/people/people.mp4', 'category': 'people'},
                    {'id': 'people_woman', 'title': 'Woman', 'video_url': f'{base_url}/people/woman.mp4', 'thumbnail_url': f'{base_url}/people/woman.mp4', 'category': 'people'},
                ],
                'professional': [
                    {'id': 'professional_aman', 'title': 'A Man', 'video_url': f'{base_url}/professional/aman.mp4', 'thumbnail_url': f'{base_url}/professional/aman.mp4', 'category': 'professional'},
                    {'id': 'professional_theman', 'title': 'The Man', 'video_url': f'{base_url}/professional/theman.mp4', 'thumbnail_url': f'{base_url}/professional/theman.mp4', 'category': 'professional'},
                ],
                'travel': [
                    {'id': 'travel_sport', 'title': 'Sport', 'video_url': f'{base_url}/travel/sport.mp4', 'thumbnail_url': f'{base_url}/travel/sport.mp4', 'category': 'travel'},
                ],
            }
            total_videos = sum(len(v) for v in templates.values())
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total_videos': total_videos,
            'categories': list(templates.keys())
        })
        
    except Exception as e:
        print(f"❌ [VIDEO_TEMPLATES] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/photo-templates/swapface', methods=['GET'])
def get_swapface_photo_templates():
    """Load SwapFace photo templates from Supabase Storage dynamically"""
    try:
        print("📥 [PHOTO_TEMPLATES_SWAPFACE] Fetching from Supabase...")
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        import requests as http_requests
        
        bucket_name = 'face-swap-templates'
        storage_url = f"{supabase_url}/storage/v1/object/list/{bucket_name}"
        
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}'
        }
        
        # Step 1: List root folder to get all categories (female, male, mixed)
        response = http_requests.post(
            storage_url,
            headers=headers,
            json={'prefix': '', 'limit': 1000},
            timeout=10
        )
        response.raise_for_status()
        folders = response.json()
        
        # Step 2: For each category, list all photos inside
        templates = {}
        for folder_item in folders:
            category = folder_item.get('name')
            if not category:
                continue
            
            # List photos in this category folder
            folder_response = http_requests.post(
                storage_url,
                headers=headers,
                json={'prefix': f'{category}/', 'limit': 1000},
                timeout=10
            )
            folder_response.raise_for_status()
            photos = folder_response.json()
            
            # Process each photo in this category
            for photo_item in photos:
                filename = photo_item.get('name')
                # Support common image formats
                if not filename or not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    continue
                
                if category not in templates:
                    templates[category] = []
                
                photo_path = f"{category}/{filename}"
                photo_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{photo_path}"
                
                templates[category].append({
                    'id': photo_path.replace('/', '_').replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('.webp', ''),
                    'name': filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title(),
                    'imagePath': photo_url,
                    'category': category,
                    'filename': filename
                })
        
        total_photos = sum(len(v) for v in templates.values())
        print(f"✅ [PHOTO_TEMPLATES_SWAPFACE] Found {total_photos} photos in {len(templates)} categories (DYNAMIC)")
        
        # Fallback to current hardcoded templates if Storage List API fails
        if total_photos == 0:
            print("⚠️  [PHOTO_TEMPLATES_SWAPFACE] Storage List API failed, using hardcoded fallback")
            base_url = f"{supabase_url}/storage/v1/object/public/face-swap-templates"
            templates = {
                'female': [
                    {'id': 'female_beautiful_girl', 'name': 'Beautiful Girl', 'imagePath': f'{base_url}/female/beautiful-girl.jpg', 'category': 'female'},
                    {'id': 'female_kate_upton', 'name': 'Kate Upton', 'imagePath': f'{base_url}/female/kate-upton.jpg', 'category': 'female'},
                    {'id': 'female_nice_girl', 'name': 'Nice Girl', 'imagePath': f'{base_url}/female/nice-girl.jpg', 'category': 'female'},
                    {'id': 'female_usa_girl', 'name': 'USA Girl', 'imagePath': f'{base_url}/female/usa-girl.jpg', 'category': 'female'},
                    {'id': 'female_wedding_face', 'name': 'Wedding Face', 'imagePath': f'{base_url}/female/wedding-face.jpeg', 'category': 'female'},
                ],
                'male': [
                    {'id': 'male_aquaman', 'name': 'Aquaman', 'imagePath': f'{base_url}/male/aquaman.jpg', 'category': 'male'},
                    {'id': 'male_handsome', 'name': 'Handsome', 'imagePath': f'{base_url}/male/handsome.jpg', 'category': 'male'},
                    {'id': 'male_superman', 'name': 'Superman', 'imagePath': f'{base_url}/male/superman.jpg', 'category': 'male'},
                    {'id': 'male_themen', 'name': 'Themen', 'imagePath': f'{base_url}/male/themen.jpg', 'category': 'male'},
                ],
                'mixed': [
                    {'id': 'mixed_beckham', 'name': 'Beckham', 'imagePath': f'{base_url}/mixed/beckham.jpg', 'category': 'mixed'},
                    {'id': 'mixed_parka_clothing', 'name': 'Parka Clothing', 'imagePath': f'{base_url}/mixed/parka-clothing.jpg', 'category': 'mixed'},
                ],
            }
            total_photos = sum(len(v) for v in templates.values())
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total_photos': total_photos,
            'categories': list(templates.keys())
        })
        
    except Exception as e:
        print(f"❌ [PHOTO_TEMPLATES_SWAPFACE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/photo-templates/story', methods=['GET'])
def get_story_photo_templates():
    """Load Story photo templates from Supabase Storage dynamically"""
    try:
        print("📥 [PHOTO_TEMPLATES_STORY] Fetching from Supabase...")
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        import requests as http_requests
        
        bucket_name = 'story-templates'
        storage_url = f"{supabase_url}/storage/v1/object/list/{bucket_name}"
        
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}'
        }
        
        # Step 1: List root folder to get all categories (travel, gym, selfie, etc.)
        response = http_requests.post(
            storage_url,
            headers=headers,
            json={'prefix': '', 'limit': 1000},
            timeout=10
        )
        response.raise_for_status()
        folders = response.json()
        
        # Step 2: For each category, list all photos inside
        templates = {}
        for folder_item in folders:
            category = folder_item.get('name')
            if not category:
                continue
            
            # List photos in this category folder
            folder_response = http_requests.post(
                storage_url,
                headers=headers,
                json={'prefix': f'{category}/', 'limit': 1000},
                timeout=10
            )
            folder_response.raise_for_status()
            photos = folder_response.json()
            
            # Sort photos by created_at DESC (newest first)
            photos_sorted = sorted(
                photos,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # Process each photo in this category
            for photo_item in photos_sorted:
                filename = photo_item.get('name')
                # Support common image formats
                if not filename or not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    continue
                
                if category not in templates:
                    templates[category] = []
                
                photo_path = f"{category}/{filename}"
                photo_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{photo_path}"
                
                templates[category].append({
                    'id': photo_path.replace('/', '_').replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('.webp', ''),
                    'name': filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title(),
                    'imagePath': photo_url,
                    'category': category,
                    'filename': filename
                })
        
        total_photos = sum(len(v) for v in templates.values())
        print(f"✅ [PHOTO_TEMPLATES_STORY] Found {total_photos} photos in {len(templates)} categories (DYNAMIC)")
        
        # Fallback to empty if Storage List API fails (user needs to upload photos to Supabase)
        if total_photos == 0:
            print("⚠️  [PHOTO_TEMPLATES_STORY] No photos found in Supabase Storage. Please upload photos to 'story-templates' bucket.")
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total_photos': total_photos,
            'categories': list(templates.keys())
        })
        
    except Exception as e:
        print(f"❌ [PHOTO_TEMPLATES_STORY] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/cartoon', methods=['POST'])
def cartoon():
    """Cartoon/3D Toon transformation using Multi-Provider Gateway"""
    try:
        print("📥 [CARTOON] Received request")
        data = request.get_json()
        image_base64 = data.get('image', '')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        print("🚀 [CARTOON] Calling cartoon gateway...")
        result = asyncio.run(cartoon_gateway.transform(image_base64))
        
        print(f"📤 [CARTOON] Result: success={result.get('success')}, provider={result.get('provider')}")
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ [CARTOON] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/memoji', methods=['POST'])
def memoji():
    """Memoji/Face-Emoji transformation using Multi-Provider Gateway"""
    try:
        print("📥 [MEMOJI] Received request")
        data = request.get_json()
        image_base64 = data.get('image', '')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        print("🚀 [MEMOJI] Calling memoji gateway...")
        result = asyncio.run(memoji_gateway.transform(image_base64))
        
        print(f"📤 [MEMOJI] Result: success={result.get('success')}, provider={result.get('provider')}")
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ [MEMOJI] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/animal-toon', methods=['POST'])
def animal_toon():
    """Animal-Toon transformation using Multi-Provider Gateway"""
    try:
        print("📥 [ANIMAL_TOON] Received request")
        data = request.get_json()
        image_base64 = data.get('image', '')
        animal_type = data.get('animal_type', 'bunny')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        print(f"🚀 [ANIMAL_TOON] Calling animal-toon gateway (animal={animal_type})...")
        result = asyncio.run(animal_toon_gateway.transform(image_base64, animal_type))
        
        print(f"📤 [ANIMAL_TOON] Result: success={result.get('success')}, provider={result.get('provider')}")
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ [ANIMAL_TOON] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/muscle', methods=['POST'])
def muscle():
    """Muscle Enhancement transformation using Multi-Provider Gateway"""
    try:
        print("📥 [MUSCLE] Received request")
        data = request.get_json()
        image_base64 = data.get('image', '')
        intensity = data.get('intensity', 'moderate')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        print(f"🚀 [MUSCLE] Calling muscle gateway (intensity={intensity})...")
        result = asyncio.run(muscle_gateway.transform(image_base64, intensity))
        
        print(f"📤 [MUSCLE] Result: success={result.get('success')}, provider={result.get('provider')}")
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ [MUSCLE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/art-style', methods=['POST'])
def art_style():
    """Art Style transformation using Multi-Provider Gateway"""
    try:
        print("📥 [ART_STYLE] Received request")
        data = request.get_json()
        image_base64 = data.get('image', '')
        style = data.get('style', 'mosaic')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        print(f"🚀 [ART_STYLE] Calling art-style gateway (style={style})...")
        result = asyncio.run(art_style_gateway.transform(image_base64, style))
        
        print(f"📤 [ART_STYLE] Result: success={result.get('success')}, provider={result.get('provider')}")
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ [ART_STYLE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy-image', methods=['GET'])
def proxy_image():
    """Proxy image download from Replicate CDN to solve network blocking issues"""
    try:
        image_url = request.args.get('url', '')
        
        if not image_url:
            return jsonify({'error': 'No URL provided'}), 400
        
        if not image_url.startswith('https://replicate.delivery/'):
            return jsonify({'error': 'Invalid URL - only Replicate CDN allowed'}), 400
        
        print(f"🔗 [PROXY] Downloading from: {image_url[:80]}...")
        
        import requests as http_requests
        response = http_requests.get(image_url, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ [PROXY] Failed: HTTP {response.status_code}")
            return jsonify({'error': f'Download failed: HTTP {response.status_code}'}), response.status_code
        
        content_type = response.headers.get('Content-Type', 'image/png')
        print(f"✅ [PROXY] Success, {len(response.content)} bytes, type: {content_type}")
        
        from flask import send_file
        import io
        return send_file(
            io.BytesIO(response.content),
            mimetype=content_type,
            as_attachment=False,
            download_name='result.png'
        )
        
    except Exception as e:
        print(f"❌ [PROXY] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For local testing
    app.run(host='0.0.0.0', port=5000, debug=True)
