import sqlite3
import os
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger('discord-meeting-bot')

class Database:
    def __init__(self, db_path="data/meetings.db"):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    async def initialize(self):
        """Initialize the database and create tables if they don't exist"""
        await self._execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            meeting_name TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            transcript TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        logger.info("Database initialized")
    
    async def save_meeting(self, server_id, channel_id, meeting_name, start_time, end_time, transcript, notes):
        """
        Save meeting data to the database.
        
        Args:
            server_id: Discord server ID
            channel_id: Discord channel ID
            meeting_name: Name of the meeting
            start_time: Start time of the meeting
            end_time: End time of the meeting
            transcript: Transcribed text
            notes: Generated meeting notes
            
        Returns:
            meeting_id: ID of the saved meeting
        """
        query = '''
        INSERT INTO meetings 
        (server_id, channel_id, meeting_name, start_time, end_time, transcript, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        # Format datetime objects for SQLite
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = await self._execute(
            query, 
            (server_id, channel_id, meeting_name, start_time_str, end_time_str, transcript, notes)
        )
        
        meeting_id = cursor.lastrowid
        logger.info(f"Saved meeting {meeting_id} to database")
        
        return meeting_id
    
    async def get_meeting(self, meeting_id):
        """
        Get meeting data by ID.
        
        Args:
            meeting_id: ID of the meeting
            
        Returns:
            meeting: Meeting data as a dictionary
        """
        query = "SELECT * FROM meetings WHERE id = ?"
        cursor = await self._execute(query, (meeting_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row[0],
                'server_id': row[1],
                'channel_id': row[2],
                'meeting_name': row[3],
                'start_time': datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S'),
                'end_time': datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S'),
                'transcript': row[6],
                'notes': row[7],
                'created_at': datetime.strptime(row[8], '%Y-%m-%d %H:%M:%S')
            }
        
        return None
    
    async def get_recent_meetings(self, server_id, limit=5):
        """
        Get recent meetings for a server.
        
        Args:
            server_id: Discord server ID
            limit: Maximum number of meetings to return
            
        Returns:
            meetings: List of meeting data dictionaries
        """
        query = "SELECT * FROM meetings WHERE server_id = ? ORDER BY start_time DESC LIMIT ?"
        cursor = await self._execute(query, (server_id, limit))
        rows = cursor.fetchall()
        
        meetings = []
        for row in rows:
            meetings.append({
                'id': row[0],
                'server_id': row[1],
                'channel_id': row[2],
                'meeting_name': row[3],
                'start_time': datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S'),
                'end_time': datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S'),
                'transcript': row[6],
                'notes': row[7],
                'created_at': datetime.strptime(row[8], '%Y-%m-%d %H:%M:%S')
            })
        
        return meetings
    
    async def delete_old_meetings(self, days=30):
        """
        Delete meetings older than the specified number of days.
        
        Args:
            days: Number of days to keep meetings
            
        Returns:
            deleted_count: Number of deleted meetings
        """
        retention_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        query = "DELETE FROM meetings WHERE created_at < ?"
        cursor = await self._execute(query, (retention_date,))
        
        deleted_count = cursor.rowcount
        logger.info(f"Deleted {deleted_count} meetings older than {days} days")
        
        return deleted_count
    
    async def _execute(self, query, parameters=None):
        """Execute a database query asynchronously"""
        # Run in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, query, parameters)
    
    def _execute_sync(self, query, parameters=None):
        """Execute a database query synchronously (runs in thread pool)"""
        # Create connection if it doesn't exist
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self.conn.row_factory = sqlite3.Row
        
        # Execute query
        cursor = self.conn.cursor()
        if parameters:
            cursor.execute(query, parameters)
        else:
            cursor.execute(query)
        
        self.conn.commit()
        return cursor
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None 