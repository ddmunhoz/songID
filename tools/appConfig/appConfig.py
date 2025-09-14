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
    @classmethod
    def load_and_validate(cls, config_path: Path) -> 'appConfig':
        """Loads and validates the JSON config file before creating the model."""
        try:
            with open(config_path) as f:
                try:
                    config_data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"❌ Invalid JSON format in config file: {str(e)}")
                
                # Now try to create and validate the model
                return cls(**config_data)
        except FileNotFoundError:
            raise ValueError(f"❌ Config file not found at: {config_path}")

    logLevel: Annotated[str, pydantic.Field(pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')] = "INFO"
    monitored_paths: list[str]
    maxQueueSize: Annotated[int, pydantic.Field(gt=0)] = 50
    checkInterval: Annotated[int, pydantic.Field(gt=0)] = 300
    renameAndMoveOnly: bool = False  
    notifySignal: bool = False
    notifyEachSong: bool = False
    notifySummary: Annotated[int, pydantic.Field(ge=0)] = 5
    signalSender: str
    signalGroup: str
    signalEndpoint: pydantic.HttpUrl

    @pydantic.field_validator('logLevel', mode='before')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.upper()
            if v not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                raise ValueError(f'🔍 logLevel must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL not {v}')
            return v
    
    @pydantic.field_validator('monitored_paths')
    @classmethod
    def validate_monitored_paths(cls, v: list) -> list:
        if not isinstance(v, list):
            raise ValueError(f'📁 monitored_paths must be a list ["path/to/your/songs"] not {v}')
        if not v:
            raise ValueError(f'📁 At least one monitored path is required in ["path/to/your/songs"] not {v}')
        for path in v:
            if not isinstance(path, str):
                raise ValueError(f'📁 All paths must be strings, found {type(path).__name__} in monitored_paths')
            if not os.path.exists(path):
                raise ValueError(f'📁 Path not found: {path}')
        return v
    @pydantic.field_validator('maxQueueSize')
    @classmethod
    def validate_max_queue_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('📈 maxQueueSize must be greater than 0')
        return v

    @pydantic.field_validator('checkInterval')
    @classmethod
    def validate_check_interval(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('⏱️ checkInterval must be greater than 0')
        return v
    
    @pydantic.field_validator('notifySignal')
    @classmethod
    def validate_notify_signal(cls, v: bool) -> bool:
        if not isinstance(v, bool):
            raise ValueError('🔔 notifySignal must be true or false')
        return v

    @pydantic.field_validator('notifyEachSong')
    @classmethod
    def validate_notify_each_song(cls, v: bool) -> bool:
        if not isinstance(v, bool):
            raise ValueError('🎵 notifyEachSong must be true or false')
        return v

    @pydantic.field_validator('notifySummary')
    @classmethod 
    def validate_notify_summary(cls, v: int, info: pydantic.ValidationInfo) -> int:
        max_queue = info.data.get('maxQueueSize')
        if v > max_queue:
            raise ValueError(f'📊 notifySummary({v}) must be less than or equal to maxQueueSize ({max_queue})')
        return v

    @pydantic.field_validator('signalSender')
    @classmethod
    def signal_sender_must_be_valid(cls, v: str) -> str:
        base64_pattern = r'^\+[0-9]+$'

        if not re.match(base64_pattern, v):
            raise ValueError('📱 signalSender must be a valid phone number in the format: +1234567890')

        return v

    @pydantic.field_validator('signalGroup')
    @classmethod
    def signal_group_must_be_valid(cls, v: str) -> str:
        base64_pattern = r'^group\.[a-zA-Z0-9+/=]+$'
        
        if not re.match(base64_pattern, v):
            raise ValueError('🔑 signalGroup must start with "group." and be followed by chars and numbers like: group.Vadf87098xjdf0-8E1EL28vUjl0987809867dkjLKJHljhfsd=')
            
        return v
    
    def get_data(self) -> dict:
        full_config = self.model_dump()
        return full_config
    

