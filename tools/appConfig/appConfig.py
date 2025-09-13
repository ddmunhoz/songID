import pydantic
import json
from typing import Annotated, Optional, List
from pathlib import Path
import json
import re
import os
os.environ['PYDANTIC_ERRORS_INCLUDE_URL'] = '0'

SCRIPT_DIR = Path(__file__).parent.parent.parent

class appConfig(pydantic.BaseModel):
    monitored_paths: list[str]
    notifySignal: bool = False
    logLevel: Annotated[str, pydantic.Field(pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')] = "INFO"
    checkInterval: Annotated[int, pydantic.Field(gt=0)] = 300  
    signalSender: str
    signalGroup: str
    signalEndpoint: pydantic.HttpUrl

    @pydantic.field_validator('logLevel', mode='before')
    @classmethod
    def uppercase_log_level(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v
    
    @pydantic.field_validator('signalSender')
    @classmethod
    def signal_sender_must_be_valid(cls, v: str) -> str:
        base64_pattern = r'^\+[0-9]+$'

        if not re.match(base64_pattern, v):
            raise ValueError('signalSender must be a valid phone number in the format: +1234567890')

        return v

    @pydantic.field_validator('signalGroup')
    @classmethod
    def signal_group_must_be_valid(cls, v: str) -> str:
        base64_pattern = r'^group\.[a-zA-Z0-9+/=]+$'
        
        if not re.match(base64_pattern, v):
            raise ValueError('signalGroup must start with "group." and be followed by chars and numbers like: group.Vadf87098xjdf0-8E1EL28vUjl0987809867dkjLKJHljhfsd=')
            
        return v
    
    def get_data(self) -> dict:
        full_config = self.model_dump()
        return full_config
    

