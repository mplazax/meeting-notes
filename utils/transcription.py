import asyncio
import logging
import os
from faster_whisper import WhisperModel

logger = logging.getLogger('discord-meeting-bot')

class Transcriber:
    def __init__(self, model_size="small", compute_type="int8", device="cpu", 
                 chunk_size=30, language="en", models_dir="models"):
        """
        Initialize the transcriber using faster-whisper.
        
        Args:
            model_size: Size of the Whisper model ('tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3')
            compute_type: Compute type ('float16', 'int8', 'int4')
            device: Device to use ('cpu', 'cuda', 'mlx')
            chunk_size: Size of audio chunks in seconds
            language: Language code
            models_dir: Directory to store models
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.chunk_size = chunk_size
        self.language = language
        self.models_dir = models_dir
        
        # Create models directory if it doesn't exist
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
        
        # Initialize the model on demand to save memory
        self.model = None
    
    def _initialize_model(self):
        """Initialize the Whisper model if not already loaded"""
        if self.model is None:
            logger.info(f"Initializing Whisper model: {self.model_size} on {self.device}")
            
            # For Apple Silicon, prefer MLX or CPU
            if self.device == "mlx":
                logger.info("Using MLX for acceleration")
                # MLX specific loading if applicable
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type, download_root=self.models_dir)
            else:
                # Standard CPU loading, optimized for Apple Silicon
                self.model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type, download_root=self.models_dir)
            
            logger.info("Whisper model initialized")
    
    async def transcribe(self, audio_file):
        """
        Transcribe an audio file using faster-whisper.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            transcript: Transcribed text
        """
        # Initialize model if needed
        if self.model is None:
            self._initialize_model()
        
        # Run transcription in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._transcribe_audio, audio_file)
        return result
    
    def _transcribe_audio(self, audio_file):
        """Process audio transcription with Whisper (runs in thread pool)"""
        logger.info(f"Transcribing audio file: {audio_file}")
        
        try:
            # Transcribe with specified parameters optimized for meetings
            segments, info = self.model.transcribe(
                audio_file,
                language=self.language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"threshold": 0.5},  # More sensitive to detect speech
                word_timestamps=True  # Enable word-level timestamps
            )
            
            # Process segments into a formatted transcript with timestamps
            transcript_parts = []
            for segment in segments:
                start_time = self._format_timestamp(segment.start)
                transcript_parts.append(f"[{start_time}] {segment.text}")
            
            full_transcript = "\n".join(transcript_parts)
            logger.info(f"Transcription complete: {len(transcript_parts)} segments")
            
            return full_transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    def _format_timestamp(self, seconds):
        """Format seconds into a timestamp string (MM:SS)"""
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def unload_model(self):
        """Unload the model to free up memory"""
        if self.model is not None:
            logger.info("Unloading Whisper model to free memory")
            self.model = None 