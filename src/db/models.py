
from sqlmodel import SQLModel, Field, Column,ForeignKey
from datetime import date, datetime
import uuid
import sqlalchemy.dialects.postgresql as pg
from typing import List, Optional


class usertable(SQLModel, table=True):
    __tablename__ = "usertable"
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    username: str
    email: str = Field(index=True)
    image: str = Field(default="")
    password: str = Field(default=None, nullable=True) 
    block_status: bool = Field(default=False)
    login_status: bool = Field(default=False)
    delete_status: bool = Field(default=False)
    role: str = Field(default="user", max_length=20,nullable=False)
    create_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow))
    update_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow))

    def __repr__(self):
        return f"<UserTable {self.username}>"

class OTPVerification(SQLModel, table=True):
    __tablename__ = "otp_verification"
    
    otp_verification_uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, nullable=False, default=uuid.uuid4)
    )
    email: str = Field(index=True)
    otp: str = Field(nullable=True)
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, nullable=False, default=datetime.utcnow)
    )

    def __repr__(self):
        return f"<OTPVerification {self.message}>"

class Comment(SQLModel):
    comment_uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    username: str
    user_photo: Optional[str] = Field(default=None)
    comment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BlogCreate(SQLModel, table=True):
    __tablename__ = "blogcreate"

    blog_uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("usertable.user_id"), nullable=False)
    )
    photo: Optional[str] = Field(default=None, nullable=True)
    description: Optional[str] = Field(default="", nullable=True)
    role: str = Field(default="user", max_length=20, nullable=True)
    delete_status: bool = Field(default=False)


    likes: List[uuid.UUID] = Field(
        default_factory=list,
        sa_column=Column(pg.ARRAY(pg.UUID(as_uuid=True)), nullable=False, default=[])
    )
    dislikes: List[uuid.UUID] = Field(
        default_factory=list,
        sa_column=Column(pg.ARRAY(pg.UUID(as_uuid=True)), nullable=False, default=[])
    )

    comments: List[Comment] = Field(
        default_factory=list,
        sa_column=Column(pg.JSONB, nullable=False, default=[])
    )

    create_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
    update_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )


    def __repr__(self):
        return f"<BlogCreate {self.blog_uid}>"