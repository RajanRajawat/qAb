from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from bson import ObjectId
from typing import Optional, Literal
from enum import Enum
from utils.general import strip_string


#- User

class UserRegister(BaseModel):
    name: str = Field(min_length=3, max_length=20)
    email: EmailStr
    password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "password", mode="before")
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
    GMAIL      = "gmail"
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

class CreateKnowledgeBase(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    db_id: Optional[str] = None
    embedding_model: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def strip_kb_name(cls, v):
        return strip_string(v)

    @field_validator("embedding_model", mode="before")
    @classmethod
    def strip_embedding_model(cls, v):
        return strip_string(v)


#- KB 

class UpdateKnowledgeBase(BaseModel):
    name: str = Field(min_length=3, max_length=50)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def strip_kb_name(cls, v):
        return strip_string(v)


class KnowledgeBaseVectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=3, ge=1, le=10)

    model_config = ConfigDict(extra="forbid")

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, v):
        return strip_string(v)
    

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
    knowledge_base_id: Optional[str] = None
    data_query: bool = False
    data_query_id: Optional[str] = None
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
        if self.knowledge_base and not self.knowledge_base_id:
            raise ValueError("knowledge_base_id is required when knowledge_base is true.")
        if not self.knowledge_base and self.knowledge_base_id:
            raise ValueError("knowledge_base_id should be empty when knowledge_base is false.")
        if self.data_query and not self.data_query_id:
            raise ValueError("data_query_id is required when data_query is true.")
        if not self.data_query and self.data_query_id:
            raise ValueError("data_query_id should be empty when data_query is false.")
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
    knowledge_base_id: Optional[str] = None
    data_query: Optional[bool] = None
    data_query_id: Optional[str] = None
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
    
class AgentSessionMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, v):
        return strip_string(v)


class AgentRunRequest(BaseModel):
    query: str
    history: list[AgentSessionMessage] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, v):
        return strip_string(v)


#- DB  connecction

class ListDB(str, Enum):
    MongoDB = "mongo"
    Postgres    = "postgres"

class AddDB(BaseModel):
    name : str = Field(min_length=3, max_length=20)
    db : ListDB
    connection_uri: str 
    #need to add validations!

    @field_validator("name", "connection_uri", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v)


class UpdateDB(BaseModel):
    name: str = Field(min_length=3, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v):
        return strip_string(v)


#- Data Query   

class DataQueryColumnConfig(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    data_type: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "data_type", "description", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v) if v is not None else v


class DataQuerySourceConfig(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_type: Literal["table", "collection"]
    description: Optional[str] = None
    columns: list[DataQueryColumnConfig] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v) if v is not None else v


class CreateDataQuery(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    db_id: str
    sources: list[DataQuerySourceConfig] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "db_id", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v)


class UpdateDataQuery(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    sources: list[DataQuerySourceConfig] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v)

