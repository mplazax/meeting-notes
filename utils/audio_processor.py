import asyncio
import os
import wave
import logging
import uuid
import numpy as np
from datetime import datetime

logger = logging.getLogger('discord-meeting-bot')

class AudioProcessor:
    def __init__(self, sample_rate=16000, max_recording_seconds=3600):
        """
        Initialize the audio processor.
        
        Args:
            sample_rate: Sample rate for audio recording (default: 16000 Hz for Whisper)
            max_recording_seconds: Maximum recording time in seconds (default: 1 hour)
        """
        self.sample_rate = sample_rate
        self.max_recording_seconds = max_recording_seconds
        self.recordings = {}
        self.temp_dir = "temp_audio"
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    async def start_recording(self, voice_client, server_id, channel_id):
        """
        Start recording audio from a voice channel.
        
        Args:
            voice_client: Discord voice client
            server_id: Discord server ID
            channel_id: Discord channel ID
            
        Returns:
            session_id: Unique identifier for this recording session
        """
        session_id = str(uuid.uuid4())
        
        # Initialize recording data
        recording_data = {
            'audio_buffer': [],
            'voice_client': voice_client,
            'server_id': server_id,
            'channel_id': channel_id,
            'start_time': datetime.now(),
            'cancelled': False
        }
        
        # Store in active recordings
        self.recordings[server_id] = recording_data
        
        # Set up audio sink
        voice_client.listen(self._create_audio_sink(server_id))
        
        # Set up auto-stop after max duration
        recording_data['auto_stop_task'] = asyncio.create_task(
            self._auto_stop_recording(server_id, self.max_recording_seconds)
        )
        
        logger.info(f"Started recording in server {server_id}, channel {channel_id} with session ID {session_id}")
        return session_id
    
    async def stop_recording(self, server_id):
        """
        Stop recording and save the audio file.
        
        Args:
            server_id: Discord server ID
            
        Returns:
            file_path: Path to the saved audio file
        """
        if server_id not in self.recordings:
            raise ValueError(f"No active recording for server {server_id}")
        
        recording_data = self.recordings[server_id]
        
        # Stop listening
        if recording_data['voice_client'].is_listening():
            recording_data['voice_client'].stop_listening()
        
        # Cancel auto-stop task if it exists
        if 'auto_stop_task' in recording_data and not recording_data['auto_stop_task'].done():
            recording_data['auto_stop_task'].cancel()
        
        # Skip if recording was cancelled
        if recording_data['cancelled']:
            del self.recordings[server_id]
            raise ValueError(f"Recording for server {server_id} was cancelled")
        
        # Save the audio data to a WAV file
        file_path = os.path.join(self.temp_dir, f"recording_{server_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        await self._save_audio_file(recording_data['audio_buffer'], file_path)
        
        # Clean up
        del self.recordings[server_id]
        
        logger.info(f"Stopped recording in server {server_id}, saved to {file_path}")
        return file_path
    
    def _create_audio_sink(self, server_id):
        """Create an audio sink for recording"""
        
        def audio_sink(data, user, audio_packet):
            """Process incoming audio data"""
            # Only process if this server is being recorded
            if server_id in self.recordings and not self.recordings[server_id]['cancelled']:
                # Add audio data to buffer
                self.recordings[server_id]['audio_buffer'].append(data)
        
        return audio_sink
    
    async def _save_audio_file(self, audio_buffer, file_path):
        """Save the audio buffer to a WAV file"""
        # Convert the buffer to PCM data
        if not audio_buffer:
            raise ValueError("No audio data recorded")
        
        # Process in a thread to avoid blocking
        def process_audio():
            # Concatenate all audio data
            pcm_data = b''.join(audio_buffer)
            
            # Save as WAV file
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(2)  # Discord sends stereo
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm_data)
            
            return file_path
        
        # Run in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, process_audio)
        return result
    
    async def _auto_stop_recording(self, server_id, max_seconds):
        """Automatically stop recording after max_seconds"""
        try:
            await asyncio.sleep(max_seconds)
            logger.info(f"Auto-stopping recording for server {server_id} after {max_seconds} seconds")
            
            if server_id in self.recordings:
                # Mark as cancelled if max time reached
                self.recordings[server_id]['cancelled'] = True
                
                # Stop listening
                voice_client = self.recordings[server_id]['voice_client']
                if voice_client.is_listening():
                    voice_client.stop_listening()
                
                # Clean up
                del self.recordings[server_id]
        
        except asyncio.CancelledError:
            # Task was cancelled because recording was stopped manually
            pass 