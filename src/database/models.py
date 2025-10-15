"""Database models."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, JSON
from sqlalchemy.sql import func
from config.database import Base

class Company(Base):
    """Company data model."""
    
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cin = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(500))
    company_roc_code = Column(String(100))
    company_category = Column(String(200))
    company_sub_category = Column(String(200))
    company_class = Column(String(100))
    authorized_capital = Column(Float)
    paidup_capital = Column(Float)
    registration_date = Column(Date)
    registered_office_address = Column(Text)
    listing_status = Column(String(50))
    company_status = Column(String(50))
    company_state_code = Column(String(50))
    company_type = Column(String(100))  # Indian/Foreign
    nic_code = Column(String(20))
    industrial_classification = Column(String(500))
    snapshot_date = Column(Date)
    snapshot_timestamp = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'cin': self.cin,
            'company_name': self.company_name,
            'company_roc_code': self.company_roc_code,
            'company_category': self.company_category,
            'company_sub_category': self.company_sub_category,
            'company_class': self.company_class,
            'authorized_capital': self.authorized_capital,
            'paidup_capital': self.paidup_capital,
            'registration_date': str(self.registration_date) if self.registration_date else None,
            'registered_office_address': self.registered_office_address,
            'listing_status': self.listing_status,
            'company_status': self.company_status,
            'company_state_code': self.company_state_code,
            'company_type': self.company_type,
            'nic_code': self.nic_code,
            'industrial_classification': self.industrial_classification,
            'snapshot_date': str(self.snapshot_date) if self.snapshot_date else None,
            'snapshot_timestamp': str(self.snapshot_timestamp) if self.snapshot_timestamp else None
        }

class Snapshot(Base):
    """Snapshot metadata model."""
    
    __tablename__ = 'snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, unique=True, nullable=False, index=True)
    file_path = Column(String(500))
    total_records = Column(Integer)
    status = Column(String(50))  # SUCCESS, FAILED, IN_PROGRESS
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    error_message = Column(Text)

class ChangeLog(Base):
    """Change log model."""
    
    __tablename__ = 'change_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cin = Column(String(50), nullable=False, index=True)
    company_name = Column(String(500))
    change_type = Column(String(50))  # NEW, MODIFIED, DELETED
    change_date = Column(Date, nullable=False, index=True)
    changed_fields = Column(JSON)  # Store field-level changes
    old_values = Column(JSON)
    new_values = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'cin': self.cin,
            'company_name': self.company_name,
            'change_type': self.change_type,
            'change_date': str(self.change_date) if self.change_date else None,
            'changed_fields': self.changed_fields,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'created_at': str(self.created_at) if self.created_at else None
        }