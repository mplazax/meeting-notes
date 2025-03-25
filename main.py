import discord
import os
import logging
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
from utils.audio_processor import AudioProcessor
from utils.transcription import Transcriber
from utils.note_generator import NoteGenerator
from database.storage import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord-meeting-bot')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize components
audio_processor = AudioProcessor()
transcriber = Transcriber(model_size="small")  # Use 'small' for faster performance, 'medium' for better accuracy
note_generator = NoteGenerator(model_path=os.getenv('LLM_MODEL_PATH', 'models/llama-2-7b.Q4_K_M.gguf'))
db = Database()

# Store active recording sessions
active_recordings = {}

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    await db.initialize()

@bot.command(name='join')
async def join(ctx):
    """Join the voice channel the user is in"""
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel for me to join.")
        return

    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    
    await ctx.send(f"Joined {channel.name}!")

@bot.command(name='startmeeting')
async def start_meeting(ctx, meeting_name=None):
    """Start recording a meeting"""
    if ctx.voice_client is None:
        await ctx.send("I need to be in a voice channel first. Use !join")
        return
    
    if ctx.guild.id in active_recordings:
        await ctx.send("A meeting is already being recorded in this server.")
        return
    
    if not meeting_name:
        meeting_name = f"Meeting-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    channel_id = ctx.author.voice.channel.id
    server_id = ctx.guild.id
    
    # Initialize recording
    session_id = await audio_processor.start_recording(ctx.voice_client, server_id, channel_id)
    
    active_recordings[server_id] = {
        'session_id': session_id,
        'meeting_name': meeting_name,
        'start_time': datetime.now(),
        'channel_id': channel_id,
        'user_id': ctx.author.id
    }
    
    await ctx.send(f"📝 Started recording meeting: **{meeting_name}**")
    await ctx.send("Use `!stopmeeting` when you're done, or the recording will automatically stop after 1 hour.")

@bot.command(name='stopmeeting')
async def stop_meeting(ctx):
    """Stop recording the current meeting and generate notes"""
    if ctx.guild.id not in active_recordings:
        await ctx.send("No active meeting recording in this server.")
        return
    
    server_id = ctx.guild.id
    session = active_recordings[server_id]
    
    await ctx.send("📊 Processing meeting recording... This might take a few minutes.")
    
    # Stop recording and get audio file
    audio_file = await audio_processor.stop_recording(server_id)
    
    # Process the recording
    try:
        # Transcribe the audio
        await ctx.send("🔊 Transcribing audio...")
        transcription = await transcriber.transcribe(audio_file)
        
        # Generate meeting notes
        await ctx.send("📝 Generating meeting notes...")
        notes = await note_generator.generate_notes(transcription)
        
        # Save to database
        meeting_id = await db.save_meeting(
            server_id=server_id,
            channel_id=session['channel_id'],
            meeting_name=session['meeting_name'],
            start_time=session['start_time'],
            end_time=datetime.now(),
            transcript=transcription,
            notes=notes
        )
        
        # Cleanup temporary audio file
        os.remove(audio_file)
        
        # Format and send notes
        formatted_notes = f"# Meeting Notes: {session['meeting_name']}\n\n{notes}"
        
        # Send notes in chunks if they exceed Discord's message limit
        if len(formatted_notes) <= 2000:
            await ctx.send(formatted_notes)
        else:
            # Create a temporary file for the notes
            notes_file = f"notes_{meeting_id}.md"
            with open(notes_file, 'w') as f:
                f.write(formatted_notes)
            
            await ctx.send(file=discord.File(notes_file))
            os.remove(notes_file)
        
        await ctx.send(f"Meeting recording processed! Use `!getnotes {meeting_id}` to retrieve these notes again.")
        
    except Exception as e:
        logger.error(f"Error processing meeting: {e}")
        await ctx.send(f"❌ Error processing meeting: {str(e)}")
    
    # Clean up
    del active_recordings[server_id]

@bot.command(name='getnotes')
async def get_notes(ctx, meeting_id=None):
    """Retrieve notes from a previous meeting"""
    if meeting_id is None:
        # List recent meetings
        meetings = await db.get_recent_meetings(ctx.guild.id, limit=5)
        if not meetings:
            await ctx.send("No recent meetings found.")
            return
        
        meeting_list = "Recent meetings:\n" + "\n".join([
            f"- ID: {m['id']} | {m['meeting_name']} | {m['start_time'].strftime('%Y-%m-%d %H:%M')}"
            for m in meetings
        ])
        await ctx.send(meeting_list)
        return
    
    try:
        meeting = await db.get_meeting(meeting_id)
        if not meeting:
            await ctx.send(f"Meeting with ID {meeting_id} not found.")
            return
        
        formatted_notes = f"# Meeting Notes: {meeting['meeting_name']}\n\n{meeting['notes']}"
        
        if len(formatted_notes) <= 2000:
            await ctx.send(formatted_notes)
        else:
            notes_file = f"notes_{meeting_id}.md"
            with open(notes_file, 'w') as f:
                f.write(formatted_notes)
            
            await ctx.send(file=discord.File(notes_file))
            os.remove(notes_file)
            
    except Exception as e:
        logger.error(f"Error retrieving notes: {e}")
        await ctx.send(f"❌ Error retrieving notes: {str(e)}")

@bot.command(name='help')
async def help_command(ctx):
    """Show available commands"""
    help_text = """
**Discord Meeting Notes Bot Commands:**
- `!join` - Join your current voice channel
- `!startmeeting [name]` - Start recording a meeting (name is optional)
- `!stopmeeting` - Stop recording and generate meeting notes
- `!getnotes [meeting_id]` - Get notes from a recent meeting
- `!help` - Show this help message
    """
    await ctx.send(help_text)

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle bot disconnection from voice channel"""
    if member.id == bot.user.id and before.channel is not None and after.channel is None:
        # Bot was disconnected from voice channel
        server_id = before.channel.guild.id
        if server_id in active_recordings:
            # Stop any active recordings
            await audio_processor.stop_recording(server_id)
            del active_recordings[server_id]
            logger.info(f"Recording stopped due to bot disconnection in server {server_id}")

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN) 