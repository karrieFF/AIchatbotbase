"""
Example database implementation for chat data storage.
This is a working example you can use as a starting point.

For SQLite (simplest - no installation needed):
    db = Database("chat_data.db")

For PostgreSQL (production-ready):
    db = Database("postgresql://user:password@localhost:5432/chatbot_db")
"""

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Session(Base):
    __tablename__ = 'sessions'
    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_messages_session', 'session_id', 'user_id'),
        Index('idx_messages_user', 'user_id'),
        Index('idx_messages_created', 'created_at'),
    )


class Database:
    def __init__(self, db_path: str = "chat_data.db"):
        """
        Initialize database connection.
        
        For SQLite:
            db = Database("chat_data.db")
        
        For PostgreSQL:
            db = Database("postgresql://user:password@localhost:5432/chatbot_db")
        """
        # Detect if it's a PostgreSQL connection string
        if db_path.startswith("postgresql://"):
            self.engine = create_engine(db_path, echo=False)
        else:
            # SQLite
            self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        """Get a database session. Remember to close it after use."""
        return self.SessionLocal()
    
    def save_message(self, user_id: str, session_id: str, role: str, content: str):
        """
        Save a single message to the database.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
        """
        db = self.get_session()
        try:
            # Ensure user exists
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                user = User(user_id=user_id)
                db.add(user)
                db.commit()
            
            # Ensure session exists
            session = db.query(Session).filter(
                Session.session_id == session_id,
                Session.user_id == user_id
            ).first()
            if not session:
                session = Session(session_id=session_id, user_id=user_id)
                db.add(session)
                db.commit()
            else:
                session.last_accessed = datetime.utcnow()
                db.commit()
            
            # Save message
            message = Message(
                session_id=session_id,
                user_id=user_id,
                role=role,
                content=content
            )
            db.add(message)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error saving message: {e}")
            raise e
        finally:
            db.close()
    
    def get_session_messages(self, user_id: str, session_id: str):
        """
        Retrieve all messages for a session in chronological order.
        
        Returns:
            List of dicts with 'role' and 'content' keys
        """
        db = self.get_session()
        try:
            messages = db.query(Message).filter(
                Message.user_id == user_id,
                Message.session_id == session_id
            ).order_by(Message.created_at).all()
            
            return [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
        except Exception as e:
            print(f"Error retrieving messages: {e}")
            return []
        finally:
            db.close()
    
    def get_user_sessions(self, user_id: str):
        """
        Get all sessions for a user.
        
        Returns:
            List of session dictionaries with session_id, created_at, last_accessed
        """
        db = self.get_session()
        try:
            sessions = db.query(Session).filter(
                Session.user_id == user_id
            ).order_by(Session.last_accessed.desc()).all()
            
            return [
                {
                    "session_id": sess.session_id,
                    "created_at": sess.created_at.isoformat() if sess.created_at else None,
                    "last_accessed": sess.last_accessed.isoformat() if sess.last_accessed else None
                }
                for sess in sessions
            ]
        except Exception as e:
            print(f"Error retrieving user sessions: {e}")
            return []
        finally:
            db.close()
    
    def delete_session(self, user_id: str, session_id: str):
        """
        Delete a session and all its messages.
        
        Note: This will cascade delete all messages due to foreign key constraints.
        """
        db = self.get_session()
        try:
            session = db.query(Session).filter(
                Session.session_id == session_id,
                Session.user_id == user_id
            ).first()
            if session:
                db.delete(session)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error deleting session: {e}")
            raise e
        finally:
            db.close()
    
    def get_message_count(self, user_id: str = None, session_id: str = None):
        """
        Get count of messages, optionally filtered by user_id and/or session_id.
        
        Args:
            user_id: Optional user filter
            session_id: Optional session filter
            
        Returns:
            Integer count of messages
        """
        db = self.get_session()
        try:
            query = db.query(Message)
            if user_id:
                query = query.filter(Message.user_id == user_id)
            if session_id:
                query = query.filter(Message.session_id == session_id)
            return query.count()
        finally:
            db.close()


# Example usage
if __name__ == "__main__":
    # Initialize database (SQLite example)
    db = Database("test_chat.db")
    
    # Save some test messages
    print("Saving test messages...")
    db.save_message("user1", "session1", "user", "Hello!")
    db.save_message("user1", "session1", "assistant", "Hi there! How can I help?")
    db.save_message("user1", "session1", "user", "I need help with exercise")
    
    # Retrieve messages
    print("\nRetrieving messages...")
    messages = db.get_session_messages("user1", "session1")
    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    
    # Get user sessions
    print("\nUser sessions:")
    sessions = db.get_user_sessions("user1")
    for sess in sessions:
        print(f"Session: {sess['session_id']}, Created: {sess['created_at']}")
    
    # Get message count
    print(f"\nTotal messages in session: {db.get_message_count('user1', 'session1')}")

