from pydantic import BaseModel, ConfigDict, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class PartialUpdateModel(APIModel):
    @model_validator(mode="after")
    def require_non_null_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        null_fields = [
            field_name
            for field_name in self.model_fields_set
            if getattr(self, field_name) is None
        ]
        if null_fields:
            fields = ", ".join(sorted(null_fields))
            raise ValueError(f"Fields cannot be null: {fields}.")

        return self


class ErrorResponse(APIModel):
    detail: str


class HealthResponse(APIModel):
    status: str


class Page[ItemT](APIModel):
    items: list[ItemT]
    total: int
    limit: int
    offset: int
