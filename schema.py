from pydantic import BaseModel ,Field
from typing import Literal

class RouteAnswer(BaseModel) :
    route : Literal["retrive","direct_answer"] = Field(description=("retrieve for the specified documents"
                                                                    "direct_answer for general conversation"))

class EvaluateAnswer(BaseModel):
    disicion : Literal["suffecient","unsuffecient"]

class FinalAnswer(BaseModel):
    Answer : str
    status : Literal["Answerd","not_answerd"]
    source : list[str]
