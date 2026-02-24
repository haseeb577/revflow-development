from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import uuid
import json

class RevFlowLead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: Optional[str] = Field(None, alias="FIRST_NAME")
    last_name: Optional[str] = Field(None, alias="LAST_NAME")
    personal_emails: List[EmailStr] = Field(default_factory=list, alias="PERSONAL_EMAILS")
    deep_verified_emails: List[EmailStr] = Field(default_factory=list, alias="DEEP_VERIFIED_EMAILS")
    mobile_phone: Optional[str] = Field(None, alias="MOBILE_PHONE")
    mobile_phone_dnc: Optional[str] = Field("N", alias="MOBILE_PHONE_DNC")
    business_email: Optional[EmailStr] = Field(None, alias="BUSINESS_EMAIL")
    personal_city: Optional[str] = Field(None, alias="PERSONAL_CITY")
    personal_state: Optional[str] = Field(None, alias="PERSONAL_STATE")
    job_title: Optional[str] = Field(None, alias="JOB_TITLE")
    company_name: Optional[str] = Field(None, alias="COMPANY_NAME")
    company_industry: Optional[str] = Field(None, alias="COMPANY_INDUSTRY")
    source_id: str
    source_type: str = "Web"
    security_status: str = "Verified"
    customer_id: Optional[int] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
    
    @field_validator('source_id')
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        if not (v.startswith('Web-') or v.startswith('RevIntel-')):
            raise ValueError('source_id must start with "Web-" or "RevIntel-"')
        return v
    
    def to_db_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'personal_emails': json.dumps(self.personal_emails),
            'deep_verified_emails': json.dumps(self.deep_verified_emails),
            'mobile_phone': self.mobile_phone,
            'mobile_phone_dnc': self.mobile_phone_dnc == 'Y',
            'business_email': self.business_email,
            'personal_city': self.personal_city,
            'personal_state': self.personal_state,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'company_industry': self.company_industry,
            'source_id': self.source_id,
            'source_type': self.source_type,
            'security_status': self.security_status,
            'customer_id': self.customer_id,
            'ingested_at': self.ingested_at,
        }
