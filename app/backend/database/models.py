from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from bson import ObjectId
from typing import Optional
from enum import Enum
from utils.general import strip_string


#- User

class UserRegister(BaseModel):
    name: str = Field(min_length=3, max_length=20)
    email: EmailStr
    mobile: str
    password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "mobile", "password", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        has_upper = False
        has_lower = False
        has_num = False
        has_special_char = False

        special_chars = set("!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~")

        for char in v:
            if char.islower():
                has_lower = True
            if char.isupper():
                has_upper = True
            if char.isnumeric():
                has_num = True
            if char in special_chars:
                has_special_char = True

        if not all([has_upper, has_lower, has_num, has_special_char]):
            raise ValueError(
                "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character."
            )
        return v

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v):
        v = str(v)
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Mobile number must be exactly 10 digits.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        return v.lower().strip()

    @field_validator("password", mode="before")
    @classmethod
    def strip_password(cls, v):
        return strip_string(v)


#- LLM

class LLMProvider(str, Enum):
    GROQ = "groq"
    GEMINI = "gemini"
    # HUGGINGFACE = "huggingface"


class LLMModel(str, Enum):

        
        LLAMA_3_1_8B = "llama-3.1-8b-instant"

        GEMINI_2_5_FLASH = "gemini-2.5-flash"
        


#- Tool

class AgentTool(str, Enum):
    WEB_SEARCH = "web_search"
    WEATHER    = "weather"
    DATETIME   = "datetime"
    WIKIPEDIA  = "wikipedia"



#- LLM Compatibility Map

compatibility_map: dict[LLMProvider, set[LLMModel]] = {
    LLMProvider.GROQ: {
        LLMModel.LLAMA_3_1_8B,
    },
    LLMProvider.GEMINI: {
        LLMModel.GEMINI_2_5_FLASH,
    }
}


#- Agent

class AgentCreation(BaseModel):
    name: str = Field(min_length=3, max_length=20)
    description: str
    role: str
    instruction: str
    llm_provider: LLMProvider
    llm_model: LLMModel
    temperature: float = Field(ge=0.0, le=1.0)
    knowledge_base: bool
    tools: list[AgentTool] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "description", "role", "instruction", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v)

    @model_validator(mode="after")
    def validate_provider_model_compatibility(self):
        allowed_models = compatibility_map.get(self.llm_provider, set())
        if self.llm_model not in allowed_models:
            raise ValueError(
                f"Model '{self.llm_model.value}' is not supported by provider '{self.llm_provider.value}'. "
                f"Allowed models: {sorted(m.value for m in allowed_models)}"
            )
        return self


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=20)
    description: Optional[str] = None
    role: Optional[str] = None
    instruction: Optional[str] = None
    llm_provider: Optional[LLMProvider] = None
    llm_model: Optional[LLMModel] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    knowledge_base: Optional[bool] = None
    tools: Optional[list[AgentTool]] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "description", "role", "instruction", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v) if v is not None else v

    @model_validator(mode="after")
    def validate_provider_model_compatibility(self):
        if self.llm_provider and self.llm_model:
            allowed_models = compatibility_map.get(self.llm_provider, set())
            if self.llm_model not in allowed_models:
                raise ValueError(
                    f"Model '{self.llm_model.value}' is not supported by "
                    f"provider '{self.llm_provider.value}'. "
                    f"Allowed models: {sorted(m.value for m in allowed_models)}"
                )
        return self
    
class AgentRunRequest(BaseModel):
    query: str
    thread_id: str | None = None


#DB

class URILink(BaseModel):
    connection_uri: str 