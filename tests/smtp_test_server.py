import asyncio
from aiosmtpd.controller import Controller
from threading import Thread
import time

class TestSMTPServer:
    def __init__(self, host='localhost', port=1025):
        self.host = host
        self.port = port
        self.controller = None
        self.messages = []
        
    class Handler:
        def __init__(self, messages_list):
            self.messages = messages_list
            
        async def handle_DATA(self, server, session, envelope):
            self.messages.append({
                'from_address': envelope.mail_from,
                'to_addresses': envelope.rcpt_tos,
                'data': envelope.content.decode('utf8', errors='replace')
            })
            return '250 Message accepted for delivery'
    
    def start(self):
        """Start the SMTP server in a separate thread"""
        self.controller = Controller(
            self.Handler(self.messages),
            hostname=self.host,
            port=self.port
        )
        self.controller.start()
        # Give the server a moment to start
        time.sleep(1)
        
    def stop(self):
        """Stop the SMTP server"""
        if self.controller:
            self.controller.stop()
            
    def clear_messages(self):
        """Clear the stored messages"""
        self.messages.clear()
        
    def get_messages(self):
        """Get all received messages"""
        return self.messages
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop() 