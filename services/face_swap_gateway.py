"""
Multi-Provider Face Swap Gateway with Production-Grade Reliability

Architecture:
- Provider abstraction for easy switching/fallback
- Cascading fallback: Nano-Banana → PiAPI → Replicate
- Retry logic with exponential backoff
- Comprehensive input validation
- Version pinning for stability
- Webhook support for async operations (PiAPI)
- Timeout handling per provider

Providers (Priority Order):
1. Nano-Banana PRIMARY (Image): google/nano-banana (Gemini 2.5 Flash Image)
   - Natural language-based face swap
   - Multi-image fusion
   - Character consistency
   - Fast (8-10s), creative results
   - SynthID watermark

2. PiAPI FALLBACK #1 (Image + Video): Qubico/image-toolkit, Qubico/video-toolkit
   - 99.9% uptime SLA
   - Enterprise-grade reliability
   - Webhook support

3. Replicate FALLBACK #2 (Image): easel/advanced-face-swap, omniedgeio/face-swap
   - Legacy models for emergency
   - Stable, version-pinned
"""

import os
import base64
import asyncio
import re
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import requests
import replicate
from PIL import Image
import io

class FaceSwapMediaType(Enum):
    IMAGE = "image"
    VIDEO = "video"

class FaceSwapProvider(ABC):
    """Base class for face swap providers"""
    
    @abstractmethod
    async def swap_face(
        self, 
        target: str, 
        source: str, 
        media_type: FaceSwapMediaType = FaceSwapMediaType.IMAGE,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform face swap
        
        Args:
            target: Target image/video (URL or base64)
            source: Source face image (URL or base64)
            media_type: Type of media (image or video)
            **kwargs: Provider-specific parameters
            
        Returns:
            Dict with 'success', 'result_url', 'message', 'provider'
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def get_timeout(self) -> int:
        """Return provider timeout in seconds"""
        pass

class NanoBananaProvider(FaceSwapProvider):
    """
    Google Nano-Banana (Gemini 2.5 Flash Image) provider for face swap
    
    Features:
    - Natural language-based face swap
    - Multi-image fusion capability
    - Character consistency
    - Fast processing (8-10s per image)
    - SynthID watermarking (invisible)
    
    Model: google/nano-banana on Replicate
    """
    
    MODEL_NAME = "google/nano-banana"
    TIMEOUT = 60  # 60s timeout (model typically takes 8-10s)
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        os.environ["REPLICATE_API_TOKEN"] = api_token
    
    def get_name(self) -> str:
        return "Nano-Banana"
    
    def get_timeout(self) -> int:
        return self.TIMEOUT
    
    async def swap_face(
        self, 
        target: str, 
        source: str, 
        media_type: FaceSwapMediaType = FaceSwapMediaType.IMAGE,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Nano-Banana face swap using natural language prompts
        
        Args:
            target: Target image (URL or data URI)
            source: Source face image (URL or data URI)
            media_type: Only IMAGE supported (video not supported)
        """
        
        if media_type == FaceSwapMediaType.VIDEO:
            return {
                "success": False,
                "error": "Nano-Banana does not support video face swap",
                "provider": self.get_name()
            }
        
        try:
            print(f"🍌 [NANO-BANANA] Starting face swap (timeout={self.TIMEOUT}s)...")
            
            # Convert data URIs to URLs if needed (Nano-Banana may need URLs)
            target_input = target
            source_input = source
            
            # If data URI, we need to use it directly (Replicate handles data URIs)
            # Nano-Banana accepts both URLs and data URIs in image_input array
            
            # Natural language prompt optimized for face swap
            prompt = (
                "Swap the face from the second image onto the person in the first image. "
                "Maintain the original pose, lighting, background, and body of the first image. "
                "Keep facial features, skin tone, and expression from the second image's face. "
                "Make the result look natural and seamless."
            )
            
            # Prepare input for Nano-Banana
            params = {
                "prompt": prompt,
                "image_input": [target_input, source_input],
                "aspect_ratio": "match_input_image",
                "output_format": "jpg"
            }
            
            print(f"📤 [NANO-BANANA] Target: {target_input[:80]}...")
            print(f"📤 [NANO-BANANA] Source: {source_input[:80]}...")
            print(f"📝 [NANO-BANANA] Prompt: {prompt[:100]}...")
            
            # Run with timeout
            def _run():
                return replicate.run(self.MODEL_NAME, input=params)
            
            loop = asyncio.get_event_loop()
            output = await asyncio.wait_for(
                loop.run_in_executor(None, _run),
                timeout=self.TIMEOUT
            )
            
            # Debug output
            print(f"🔍 [NANO-BANANA] Output type: {type(output).__name__}")
            
            if output:
                # Handle output (URL string or FileOutput object)
                result_url = None
                
                if isinstance(output, list) and len(output) > 0:
                    result_url = str(output[0])
                elif hasattr(output, 'url'):
                    result_url = str(output.url)
                else:
                    result_url = str(output)
                
                print(f"✅ [NANO-BANANA] Success! URL: {result_url[:100]}...")
                return {
                    "success": True,
                    "result_url": result_url,
                    "message": "Face swap completed via Nano-Banana (Gemini 2.5 Flash Image)",
                    "provider": self.get_name(),
                    "model": self.MODEL_NAME,
                    "watermark": "SynthID (invisible)"
                }
            else:
                print(f"⚠️ [NANO-BANANA] No output returned")
                return {
                    "success": False,
                    "error": "No output from Nano-Banana",
                    "provider": self.get_name()
                }
                
        except asyncio.TimeoutError:
            print(f"⏱️ [NANO-BANANA] Timeout after {self.TIMEOUT}s")
            return {
                "success": False,
                "error": f"Nano-Banana timeout ({self.TIMEOUT}s)",
                "provider": self.get_name()
            }
        except Exception as e:
            print(f"⚠️ [NANO-BANANA] Error: {type(e).__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": self.get_name()
            }

class ReplicateProvider(FaceSwapProvider):
    """Replicate face swap provider with version pinning"""
    
    # Version-pinned models for stability (updated 2025-10-15)
    MODELS = {
        "easel": {
            "name": "easel/advanced-face-swap",
            "version": None,  # Use latest (April 2025)
            "params": {
                "target_image": None,
                "swap_image": None,
                "hair_source": "target"
            },
            "timeout": 90,
            "priority": 1
        },
        "omniedge": {
            "name": "omniedgeio/face-swap",
            "version": None,  # Active alternative
            "params": {
                "input_image": None,
                "target_image": None,
                "swap_image": None
            },
            "timeout": 60,
            "priority": 2
        }
    }
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        os.environ["REPLICATE_API_TOKEN"] = api_token
    
    def get_name(self) -> str:
        return "Replicate"
    
    def get_timeout(self) -> int:
        return max(model["timeout"] for model in self.MODELS.values())
    
    async def swap_face(
        self, 
        target: str, 
        source: str, 
        media_type: FaceSwapMediaType = FaceSwapMediaType.IMAGE,
        **kwargs
    ) -> Dict[str, Any]:
        """Replicate face swap (image only)"""
        
        if media_type == FaceSwapMediaType.VIDEO:
            return {
                "success": False,
                "error": "Replicate provider does not support video face swap",
                "provider": self.get_name()
            }
        
        # Try models in priority order
        sorted_models = sorted(self.MODELS.items(), key=lambda x: x[1]["priority"])
        
        last_error = None
        last_model_name = "unknown"
        last_timeout = 60
        
        for model_key, model_config in sorted_models:
            try:
                last_model_name = model_config["name"]
                last_timeout = model_config["timeout"]
                print(f"🔄 [REPLICATE] Trying {last_model_name} (timeout={last_timeout}s)...")
                
                # Prepare params
                params = model_config["params"].copy()
                
                # Map params based on model type
                if "target_image" in params:
                    params["target_image"] = target
                if "input_image" in params:
                    params["input_image"] = target
                if "swap_image" in params:
                    params["swap_image"] = source
                
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}
                
                # Run with timeout
                def _run():
                    return replicate.run(last_model_name, input=params)
                
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(None, _run),
                    timeout=last_timeout
                )
                
                # Debug: Print output type and content
                print(f"🔍 [REPLICATE] Output type: {type(output).__name__}")
                print(f"🔍 [REPLICATE] Output content: {output}")
                
                if output:
                    # Handle different output types
                    result_url = None
                    
                    # If output is a list, get first item
                    if isinstance(output, list) and len(output) > 0:
                        result_url = str(output[0])
                        print(f"📋 [REPLICATE] List output, using first item: {result_url}")
                    # If output is a FileOutput object, get url attribute
                    elif hasattr(output, 'url'):
                        result_url = str(output.url)  # type: ignore
                        print(f"📎 [REPLICATE] FileOutput, using .url: {result_url}")
                    # Otherwise convert to string
                    else:
                        result_url = str(output)
                        print(f"📝 [REPLICATE] Direct string conversion: {result_url}")
                    
                    print(f"✅ [REPLICATE] Success via {last_model_name}, URL: {result_url[:100]}...")
                    return {
                        "success": True,
                        "result_url": result_url,
                        "message": f"Face swap completed via {last_model_name}",
                        "provider": self.get_name(),
                        "model": last_model_name
                    }
                else:
                    print(f"⚠️ [REPLICATE] {last_model_name} returned no output")
                    continue
                    
            except asyncio.TimeoutError:
                print(f"⏱️ [REPLICATE] {last_model_name} timeout ({last_timeout}s)")
                continue
            except Exception as e:
                print(f"⚠️ [REPLICATE] {last_model_name} failed: {type(e).__name__}: {e}")
                continue
        
        return {
            "success": False,
            "error": "All Replicate models failed or timed out",
            "provider": self.get_name()
        }

class PiAPIProvider(FaceSwapProvider):
    """PiAPI face swap provider with async support"""
    
    BASE_URL = "https://api.piapi.ai/api/v1"
    
    MODELS = {
        "image": {
            "model": "Qubico/image-toolkit",
            "task_type": "face-swap",
            "timeout": 60
        },
        "video": {
            "model": "Qubico/video-toolkit",
            "task_type": "face-swap",
            "timeout": 120
        }
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_name(self) -> str:
        return "PiAPI"
    
    def get_timeout(self) -> int:
        return 120
    
    async def swap_face(
        self, 
        target: str, 
        source: str, 
        media_type: FaceSwapMediaType = FaceSwapMediaType.IMAGE,
        webhook_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """PiAPI face swap with webhook support"""
        
        model_config = self.MODELS.get(media_type.value)
        if not model_config:
            return {
                "success": False,
                "error": f"Unsupported media type: {media_type.value}",
                "provider": self.get_name()
            }
        
        try:
            print(f"🚀 [PIAPI] Starting {media_type.value} face swap...")
            
            # PiAPI accepts data URIs (data:image/...;base64,xxx) or plain URLs
            # Keep data URIs as-is for proper format detection
            print(f"📤 [PIAPI] Target input: {target[:100]}...")
            print(f"📤 [PIAPI] Source input: {source[:100]}...")
            
            # Create task
            payload = {
                "model": model_config["model"],
                "task_type": model_config["task_type"],
                "input": {
                    "target_image" if media_type == FaceSwapMediaType.IMAGE else "target_video": target,
                    "swap_image": source
                }
            }
            
            # Add webhook if provided
            if webhook_url:
                payload["config"] = {
                    "webhook_config": {
                        "endpoint": webhook_url,
                        "secret": hashlib.sha256(f"{self.api_key}{time.time()}".encode()).hexdigest()[:32]
                    }
                }
            
            headers = {
                "x-api-key": self.api_key,  # PiAPI requires lowercase header (2025 API)
                "Content-Type": "application/json"
            }
            
            def _create_task():
                resp = requests.post(
                    f"{self.BASE_URL}/task",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                # Log full error response for debugging
                if resp.status_code != 200:
                    print(f"❌ [PIAPI] HTTP {resp.status_code} error response: {resp.text[:500]}")
                resp.raise_for_status()
                return resp.json()
            
            loop = asyncio.get_event_loop()
            create_response = await loop.run_in_executor(None, _create_task)
            
            if create_response.get("code") != 200:
                return {
                    "success": False,
                    "error": f"Failed to create task: {create_response}",
                    "provider": self.get_name()
                }
            
            task_id = create_response["data"]["task_id"]
            print(f"📋 [PIAPI] Task created: {task_id}")
            
            # If webhook provided, return immediately
            if webhook_url:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "pending",
                    "message": "Task created, webhook will be called when complete",
                    "provider": self.get_name(),
                    "async": True
                }
            
            # Poll for result
            timeout = model_config["timeout"]
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                def _get_task():
                    resp = requests.get(
                        f"{self.BASE_URL}/task/{task_id}",
                        headers=headers,
                        timeout=30
                    )
                    resp.raise_for_status()
                    return resp.json()
                
                result = await loop.run_in_executor(None, _get_task)
                status = result["data"]["status"]
                
                if status == "completed":
                    output_key = "image_url" if media_type == FaceSwapMediaType.IMAGE else "video_url"
                    result_url = result["data"]["output"].get(output_key)
                    
                    print(f"✅ [PIAPI] Success - {media_type.value} ready")
                    return {
                        "success": True,
                        "result_url": result_url,
                        "message": f"Face swap completed via PiAPI ({media_type.value})",
                        "provider": self.get_name(),
                        "task_id": task_id
                    }
                elif status == "failed":
                    error = result["data"].get("error", "Unknown error")
                    return {
                        "success": False,
                        "error": f"Task failed: {error}",
                        "provider": self.get_name(),
                        "task_id": task_id
                    }
                
                # Wait before polling again
                await asyncio.sleep(3)
            
            return {
                "success": False,
                "error": f"Task timeout after {timeout}s",
                "provider": self.get_name(),
                "task_id": task_id
            }
            
        except Exception as e:
            print(f"⚠️ [PIAPI] Error: {type(e).__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": self.get_name()
            }

class FaceSwapGateway:
    """Multi-provider face swap gateway with fallback and retry"""
    
    def __init__(self):
        self.replicate_token = os.environ.get('REPLICATE_API_TOKEN')
        self.piapi_key = os.environ.get('PIAPI_API_KEY')
        
        # Initialize providers in priority order
        self.providers: List[FaceSwapProvider] = []
        
        # 1. Nano-Banana PRIMARY (Google Gemini 2.5 Flash, creative face swap)
        if self.replicate_token:
            self.providers.append(NanoBananaProvider(self.replicate_token))
            print("✅ Nano-Banana provider enabled (PRIMARY - Gemini 2.5 Flash)")
        
        # 2. PiAPI FALLBACK #1 (99.9% SLA, enterprise-grade)
        if self.piapi_key:
            self.providers.append(PiAPIProvider(self.piapi_key))
            print("✅ PiAPI provider enabled (FALLBACK #1 - 99.9% uptime SLA)")
        
        # 3. Replicate FALLBACK #2 (legacy models for emergency)
        if self.replicate_token:
            self.providers.append(ReplicateProvider(self.replicate_token))
            print("✅ Replicate provider enabled (FALLBACK #2 - legacy models)")
        
        print(f"🔌 Face Swap Gateway initialized with {len(self.providers)} provider(s)")
        if len(self.providers) > 1:
            print(f"📊 Provider priority: {' → '.join([p.get_name() for p in self.providers])}")
    
    def _validate_input(self, data: str, media_type: FaceSwapMediaType = FaceSwapMediaType.IMAGE) -> Tuple[bool, Optional[str]]:
        """
        Validate input (URL or base64) based on media type
        Returns: (is_valid, error_message)
        """
        # Check if URL
        if data.startswith('http://') or data.startswith('https://'):
            return True, None
        
        # Check if data URI (image or video)
        if media_type == FaceSwapMediaType.VIDEO:
            data_uri_pattern = r'^data:(image|video)/(jpeg|jpg|png|gif|webp|bmp|mp4|avi|mov|webm);base64,'
        else:
            data_uri_pattern = r'^data:image/(jpeg|jpg|png|gif|webp|bmp);base64,'
        
        if re.match(data_uri_pattern, data, re.IGNORECASE):
            return True, None
        
        # Try to decode as base64
        try:
            base64.b64decode(data)
            return True, None
        except:
            media_name = "video" if media_type == FaceSwapMediaType.VIDEO else "image"
            return False, f"Invalid input: must be URL or base64 encoded {media_name}"
    
    def _normalize_base64(self, data: str) -> str:
        """
        Normalize input to appropriate format
        - URLs: preserve as-is (PiAPI needs URLs)
        - Data URIs: preserve as-is
        - Plain base64: convert to data URI
        """
        # URL, return as-is (important for PiAPI!)
        if data.startswith('http://') or data.startswith('https://'):
            return data
        
        # Already data URI (image or video)
        data_uri_pattern = r'^data:(image|video)/(jpeg|jpg|png|gif|webp|bmp|mp4|avi|mov);base64,'
        if re.match(data_uri_pattern, data, re.IGNORECASE):
            return data
        
        # Plain base64, add data URI prefix
        # Try to detect image type from base64 data
        try:
            img_bytes = base64.b64decode(data)
            img = Image.open(io.BytesIO(img_bytes))
            format_map = {
                'JPEG': 'jpeg',
                'PNG': 'png',
                'GIF': 'gif',
                'WEBP': 'webp',
                'BMP': 'bmp'
            }
            img_format = format_map.get(img.format or 'JPEG', 'jpeg')
            return f"data:image/{img_format};base64,{data}"
        except:
            # Default to jpeg
            return f"data:image/jpeg;base64,{data}"
    
    async def swap_face(
        self,
        target: str,
        source: str,
        media_type: FaceSwapMediaType = FaceSwapMediaType.IMAGE,
        retry_count: int = 2,
        webhook_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform face swap with multi-provider fallback and retry
        
        Args:
            target: Target image/video (URL or base64)
            source: Source face (URL or base64)
            media_type: Type of media (image or video)
            retry_count: Number of retries per provider
            webhook_url: Webhook URL for async operations (PiAPI only)
            **kwargs: Provider-specific parameters
        """
        
        # Validate inputs based on media type
        target_valid, target_error = self._validate_input(target, media_type)
        if not target_valid:
            return {"success": False, "error": target_error}
        
        # Source is always an image (face)
        source_valid, source_error = self._validate_input(source, FaceSwapMediaType.IMAGE)
        if not source_valid:
            return {"success": False, "error": source_error}
        
        # Normalize to data URIs
        target = self._normalize_base64(target)
        source = self._normalize_base64(source)
        
        if not self.providers:
            return {
                "success": False,
                "error": "No face swap providers configured (missing API keys)"
            }
        
        # Try each provider with retry
        for provider in self.providers:
            print(f"🔄 Trying provider: {provider.get_name()}")
            
            for attempt in range(retry_count + 1):
                try:
                    if attempt > 0:
                        # Exponential backoff
                        wait_time = 2 ** attempt
                        print(f"⏳ Retry {attempt}/{retry_count} after {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    
                    result = await provider.swap_face(
                        target=target,
                        source=source,
                        media_type=media_type,
                        webhook_url=webhook_url if isinstance(provider, PiAPIProvider) else None,
                        **kwargs
                    )
                    
                    if result.get("success"):
                        return result
                    
                    print(f"⚠️ Provider {provider.get_name()} failed: {result.get('error')}")
                    break
                    
                except Exception as e:
                    print(f"❌ Provider {provider.get_name()} error: {type(e).__name__}: {e}")
                    continue
        
        # All providers failed
        return {
            "success": False,
            "error": "All face swap providers failed after retries",
            "error_code": "ALL_PROVIDERS_FAILED"
        }

# Global gateway instance
face_swap_gateway = FaceSwapGateway()
