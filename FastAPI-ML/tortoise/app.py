from typing import List, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query, status
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import DoesNotExist

from tortoise.models import ( CommentBase,CommentDB,CommentTortoise,PostCreate,PostDB,PostPartialUpdate,PostPublic,PostTortoise,
)

app = FastAPI()

# check baackend.app.py for comments
async def pagination(skip: int = Query(0, ge=0),limit: int = Query(10, ge=0)) -> Tuple[int, int]:
    capped_limit = min(100, limit)
    return (skip, capped_limit)


'''
The role of this dependency is to take the id in the path parameter and retrieve a single object from the database
that corresponds to this identifier. The get method is a convenient shortcut for this:
    - if no matching record is found, it raises the DoesNotExist exception. If there is more than one matching record
      it raises MultipleObjectsReturned.
'''
async def get_post_or_404(id: int) -> PostTortoise:
    # prefetch_related method on our query. By passing in the name of the related entities,
    #  it allows you to preload them upfront when getting the main object.
    try:
        return await PostTortoise.get(id=id).prefetch_related("comments")
    except DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

'''
first, we retrieve Tortoise objects using the query language. 
Notice that we use the all method, which gives us every object in the table. 
Additionally, we're able to apply our pagination parameters through offset and limit.

Then, we have to transform this list of PostTortoise objects into a list of PostDB objects.
'''
@app.get("/posts")
async def list_posts(pagination: Tuple[int, int] = Depends(pagination)) -> List[PostDB]:
    skip, limit = pagination
    posts = await PostTortoise.all().offset(skip).limit(limit)

    results = [PostDB.from_orm(post) for post in posts]

    return results



'''
This is a simple GET endpoint that expects the ID of the post in the path parameter.
We just have to transform our PostTortoise object into a PostDB.
Most of the logic is in the get_post_or_404 dependency.
'''
@app.get("/posts/{id}", response_model=PostDB)
async def get_post(post: PostTortoise = Depends(get_post_or_404)) -> PostDB:
    return PostDB.from_orm(post)

'''
Here, we have our POST endpoint, which accepts our PostCreate model. The core logic consists then of two operations.

First, we create the object in the database. We directly use the PostTortoise class and its static create method. 
Conveniently, it accepts a dictionary that maps fields to their values, so we just have to call dict on our input object. 

As a result, we get an instance of a PostTortoise object. This is why the second operation we need to perform is to transform it into a Pydantic model. 
To do this, we use the from_orm method, which is available because we enabled orm_mode. 
We get a proper PostDB instance, which we can return directly.
'''
@app.post("/posts", response_model=PostDB, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate) -> PostDB:
    post_tortoise = await PostTortoise.create(**post.dict())

    return PostDB.from_orm(post_tortoise)



'''
Operate directly on the post we want to modify. 
This is one of the key aspects when working with ORM: entities are objects that can be modified as you wish. 
When you are happy with the data, you can persist it in the database.
 This is exactly what we do here: we get a fresh representation of our post due to get_post_or_404 and 
 apply the update_from_dict utility method to change the fields that we want. 
 Then, we can persist the changes in the database using save.
'''
@app.patch("/posts/{id}", response_model=PostDB)
async def update_post(
    post_update: PostPartialUpdate, post: PostTortoise = Depends(get_post_or_404)
) -> PostDB:
    post.update_from_dict(post_update.dict(exclude_unset=True))
    await post.save()

    return PostDB.from_orm(post)


@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post: PostTortoise = Depends(get_post_or_404)):
    await post.delete()



'''
Most of the logic is very similar to the create post endpoint. The main difference is that we first check
for the existence of the post before proceeding with the comment creation.
 Indeed, we want to avoid the foreign key constraint error that could occur at the database level and
show a clear and helpful error message to the end user instead.
'''
@app.post("/comments", response_model=CommentDB, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentBase) -> CommentDB:
    try:
        await PostTortoise.get(id=comment.post_id)
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Post {id} does not exist"
        )

    comment_tortoise = await CommentTortoise.create(**comment.dict())

    return CommentDB.from_orm(comment_tortoise)
'''
Configure the Tortoise engine to set the database connection string and the location of our models. 
To do this, Tortoise comes with a utility function for FastAPI that does all the required tasks for you.
In particular, it automatically adds event handlers to open and close the connection at startup and shutdown
'''
TORTOISE_ORM = {
    "connections": {"default": "sqlite://tortoise_databse.db"},
    "apps": {
        "models": {
            "models": ["tortoise.models"],
            "default_connection": "default",
        },
    },
}
# register_tortoise is a function that registers the tortoise engine with the fastapi application
register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)

