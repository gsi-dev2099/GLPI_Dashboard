from sqlalchemy import Column, Integer, String, DateTime, SmallInteger
from database import Base

class Ticket(Base):
    __tablename__ = "glpi_tickets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    status = Column(Integer)
    is_deleted = Column(SmallInteger, default=0)
    date = Column(DateTime)
    # Add other fields if necessary for future expansions
