from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator
from tortoise.models import Model
from tortoise import fields

class CommentBase(BaseModel):
    post_id: int
    publication_date: datetime = Field(default_factory=datetime.now)
    content: str

    class Config:
        orm_mode = True


class CommentCreate(CommentBase):
    pass


class CommentDB(CommentBase):
    id: int


class PostBase(BaseModel):
    title: str
    content: str
    publication_date: datetime = Field(default_factory=datetime.now)

    class Config:
        orm_mode = True


class PostPartialUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class PostCreate(PostBase):
    pass


class PostDB(PostBase):
    id: int

class PostPublic(PostDB):
    comments: List[CommentDB]

    @validator("comments", pre=True)
    def fetch_comments(cls, v):
        return list(v)


# PostTortoise is the model that is used to interact with the database
'''
Create the Tortoise model for your entity. This is a Python class whose attributes represent the
columns of your table. This class will provide you static methods in which to perform queries, such as retrieving or creating data.
Moreover, the actual entities of your database will be instances of this class, 
giving you access to its data like any other object.
'''
class PostTortoise(Model):
    id = fields.IntField(pk=True, generated=True)
    publication_date = fields.DatetimeField(null=False)
    title = fields.CharField(max_length=255, null=False)
    content = fields.TextField(null=False)

    class Meta:
        table = "posts"


'''
post field is purposely defined as a foreign key. 
The first argument is the reference to the associated model.use the models prefix; 
this is the same one we defined in the Tortoise configuration. 
Additionally, we set the related_name. This is a typical and convenient feature of ORM.
By doing this, we'll be able to get all the comments of a given post simply by accessing its comments property.
The action of querying the related comments, therefore, becomes completely implicit.
'''
class CommentTortoise(Model):
    id = fields.IntField(pk=True, generated=True)
    post = fields.ForeignKeyField(
        "models.PostTortoise", related_name="comments", null=False
    )
    publication_date = fields.DatetimeField(null=False)
    content = fields.TextField(null=False)

    class Meta:
        table = "comments"