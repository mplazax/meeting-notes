import asyncio
import logging
import os
from llama_cpp import Llama

logger = logging.getLogger('discord-meeting-bot')

class NoteGenerator:
    def __init__(self, model_path, n_ctx=2048, n_gpu_layers=1, n_threads=8):
        """
        Initialize the note generator using a quantized LLM.
        
        Args:
            model_path: Path to the GGUF model file
            n_ctx: Context window size
            n_gpu_layers: Number of layers to offload to GPU (use 1 for Metal on Apple Silicon)
            n_threads: Number of CPU threads to use
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        
        # Ensure model directory exists
        model_dir = os.path.dirname(self.model_path)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            
        # Initialize the model on-demand to save memory
        self.llm = None
    
    def _initialize_model(self):
        """Initialize the LLM if not already loaded"""
        if self.llm is None:
            logger.info(f"Initializing LLM: {self.model_path}")
            
            try:
                # Initialize with Metal GPU acceleration on Apple Silicon
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=self.n_ctx,
                    n_gpu_layers=self.n_gpu_layers,
                    n_threads=self.n_threads
                )
                logger.info("LLM initialized with GPU acceleration")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM with GPU acceleration: {e}. Falling back to CPU-only.")
                # Fall back to CPU-only if GPU fails
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=self.n_ctx,
                    n_gpu_layers=0,
                    n_threads=self.n_threads
                )
    
    async def generate_notes(self, transcript):
        """
        Generate meeting notes from a transcript.
        
        Args:
            transcript: Transcribed text
            
        Returns:
            notes: Generated meeting notes
        """
        # Initialize model if needed
        if self.llm is None:
            self._initialize_model()
        
        # Run generation in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._process_transcript, transcript)
        return result
    
    def _process_transcript(self, transcript):
        """Process transcript to generate notes (runs in thread pool)"""
        logger.info("Generating meeting notes from transcript")
        
        # Prepare system prompt focused on meeting notes
        prompt = f"""[INST] <<SYS>>
You are an AI assistant specialized in summarizing meeting transcripts.
Your task is to analyze the provided meeting transcript and generate comprehensive meeting notes.
Focus on extracting:
1. Key decisions made during the meeting (in bullet points)
2. Action items with assignees and deadlines if mentioned (in bullet points)
3. Follow-up tasks or pending items that need attention
Be concise, clear, and organized. Ignore small talk and focus on substantive discussion.
<</SYS>>

Here is the meeting transcript:

{transcript}

Please generate structured meeting notes for this transcript including key decisions, action items, and follow-up tasks. [/INST]
"""
        
        try:
            # Generate completion with optimized parameters
            response = self.llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more factual output
                max_tokens=800,   # Limit output size
                top_p=0.9,        # Nucleus sampling
                top_k=40,         # Limit vocabulary diversity
                stop=["<|im_end|>", "</s>"]  # Stop tokens
            )
            
            # Extract response content
            if "choices" in response and len(response["choices"]) > 0:
                notes = response["choices"][0]["message"]["content"].strip()
                logger.info(f"Generated notes ({len(notes)} chars)")
                return notes
            else:
                logger.error("No response generated from LLM")
                return "Error: Failed to generate meeting notes."
                
        except Exception as e:
            logger.error(f"Error generating notes: {e}")
            return f"Error generating meeting notes: {str(e)}"
    
    def unload_model(self):
        """Unload the model to free up memory"""
        if self.llm is not None:
            logger.info("Unloading LLM to free memory")
            self.llm = None 