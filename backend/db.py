# db.py
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class TrafficData(Base):
    __tablename__ = 'traffic_data'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    location_type = Column(String)  # 'indoor' or 'road'
    value = Column(Integer)

class Forecast(Base):
    __tablename__ = 'forecast'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    location_type = Column(String)  # 'indoor' or 'road'
    predicted_value = Column(Float)

class CleaningTask(Base):
    __tablename__ = 'cleaning_tasks'
    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    task = Column(String)
    priority = Column(String)
    location_type = Column(String)

engine = create_engine('sqlite:///cleansweep.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)