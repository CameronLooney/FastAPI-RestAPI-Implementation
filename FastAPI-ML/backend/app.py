import re
from typing import List, Tuple,cast,Mapping  # type annotations for the type hints
from databases import Database # Database is a class that defines a database connection
from fastapi import FastAPI, Query, Path, Body, Header, Depends, HTTPException, status

from database import get_database, sqlalchemy_engine # get_database is a function that returns a database connection
from models import  comments, metadata,posts,CommentCreate, CommentDB, PostDB, PostCreate,  PostPartialUpdate,PostPublic

app = FastAPI()

@app.on_event("startup") # on_event is a FastAPI decorator that allows us to perform an action when the application starts
async def startup():
    '''
    This function is called when the application starts.
    async means that this function is an asynchronous function.
    await means that this function will wait for the result of another function before it continues.
    create_all is a function that creates all the tables in the database (defined in the metadata object)
    # sqlalchemy_engine is a connection to the database
    '''
    await get_database().connect()
    metadata.create_all(sqlalchemy_engine)

@app.on_event("shutdown") # on_event is a FastAPI decorator that allows us to perform an action when the application stops
async def shutdown():
    '''
    close is a function that closes the database connection
    '''
    await get_database().disconnect()

# Pagination is a process that is used to divide a large data into smaller discrete pages
def pagination(skip: int = Query(0, ge=0) ,limit: int = Query(10, ge=0)) -> Tuple[int, int]:
    '''
    This function is used to paginate the results of a query.
    The function has two parameters, skip and limit.
    skip is the number of results to skip., its type int and it must be greater than or equal to 0. (default 0)
    limit is the number of results to return., its type int and it must be greater than or equal to 0. (default 10)
    capped_limit is the maximum number of results to return., its type int and it must be greater than or equal to 0. (default 100)
    return is a tuple with two elements, the first is the number of results to skip, the second is the number of results to return.
    '''
    capped_limit = min(100, limit)
    return (skip, capped_limit)
   


async def get_post_or_404(id: int, database: Database = Depends(get_database)) -> PostPublic:
    '''
    This function is used to get a post from the database.
    If the post is not found, raise a 404 error.
    takes two arguements, id and database.
    id is the id of the post to get.
    database is the database connection.
    Depends is a FastAPI decorator that allows us to inject a dependency. (we can inject a database connection)
    
    '''
    # select * from posts where id = id
    select_post_query = posts.select().where(posts.c.id == id)
    # raw posts is a list of dictionaries that represent the rows in the posts table
    raw_post = await database.fetch_one(select_post_query)

    # if the post is not found, raise a 404 error
    if raw_post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # select_comments_query is a query that selects all the comments for a post by matching the post id with the comment post id
    select_post_comments_query = comments.select().where(comments.c.post_id == id)
    # raw_comments is a list of dictionaries that represent the rows in the comments table
    raw_comments = await database.fetch_all(select_post_comments_query)
    # comments is a list of CommentDB objects that represent the rows in the comments table
    comments_list = [CommentDB(**comment) for comment in raw_comments]

    return PostPublic(**raw_post, comments=comments_list)
 
@app.get("/posts") # get is a FastAPI decorator that defines a GET request

# list_posts is a function that returns a list of posts, takes two arguments
async def list_posts(pagination: Tuple[int,int] = Depends(pagination),database: Database = Depends(get_database),) -> List[PostDB]:
    '''
    This function is used to get a list of posts from the database.
    takes two arguments, pagination and database.
    pagination is a tuple with two elements, the first is the number of results to skip, the second is the number of results to return.
    database is the database connection.
    List is a built-in Python type that is used to store a list of objects.
    PostDB is a class that defines a post.
    '''
    skip, limit = pagination # skip is the number of results to skip, limit is the number of results to return
    select_query = posts.select().offset(skip).limit(limit) # select_query is a sqlalchemy query that selects all the posts from the database
    rows = await database.fetch_all(select_query) # rows is a list of tuples that contains the results of the select_query
    # results is a list of PostDB objects that is defined in the models.py file
    results = []
    for row in rows: # for each row in rows
        results.append(PostDB(**row)) # append the row to the results list
    return results


@app.get("posts/{id}", response_model=PostDB) # get is a FastAPI decorator that defines a GET request
# response_model is a FastAPI decorator that defines the response model for the request.
# get_post is a function that returns a post
async def get_posts(post: PostDB = Depends(get_post_or_404)) -> PostDB:
    return post


@app.post("/posts", response_model=PostDB, status_code = status.HTTP_201_CREATED) # post is a FastAPI decorator that defines a POST request
# create_post is a function that creates a post
async def create_post(post: PostCreate, database: Database = Depends(get_database)) -> PostDB:
    '''
    This function is used to create a post in the database.
    takes two arguments, post and database.
    post is the post to create.
    database is the database connection.
    PostDB is a class that defines a post.
    insert_query is a sqlalchemy query that inserts a post into the database.
    post_id is the id of the post that was inserted.
    post_db is the post that was inserted.
    return is the post that was inserted.'''
    insert_query = posts.insert().values(post.dict())
    post_id = await database.execute(insert_query)

    post_db = await get_post_or_404(post_id, database)

    return post_db


@app.patch("/posts/{id}", response_model=PostDB)
# update_post is a function that updates a post
async def update_post(post_update: PostPartialUpdate,post: PostDB = Depends(get_post_or_404),database: Database = Depends(get_database)) -> PostDB:
    '''
    This function is used to update a post in the database.
    takes three arguments, post_update, post and database.
    post_update is the post to update.
    post is the post to update.
    database is the database connection.
    PostDB is a class that defines a post.
    update_query is a sqlalchemy query that updates a post in the database.
    where_clause is a sqlalchemy where clause that filters the posts to update.
    c.id is the id of the post to update.'''
    update_query = (
        posts.update()
        .where(posts.c.id == post.id)
        .values(post_update.dict(exclude_unset=True))
    )
    await database.execute(update_query)

    post_db = await get_post_or_404(post.id, database)

    return post_db


# delete is a FastAPI decorator that defines a DELETE request
@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
# delete_post is a function that deletes a post
async def delete_post(post: PostDB = Depends(get_post_or_404), database: Database = Depends(get_database)):
    '''
    This function is used to delete a post from the database.
    takes two arguments, post and database.
    post is the post to delete.
    database is the database connection.
    delete_query is a sqlalchemy query that deletes a post from the database.
    where_clause is a sqlalchemy where clause that filters the posts to delete.
    '''
    delete_query = posts.delete().where(posts.c.id == post.id)
    await database.execute(delete_query)


# creates a comment using a post id
@app.post("/comments", response_model=CommentDB, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentCreate, database: Database = Depends(get_database)) -> CommentDB:
    '''
    This function is used to create a comment in the database.
    takes two arguments, comment and database.
    comment is the comment to create.
    database is the database connection.
    CommentDB is a class that defines a comment.
    select_post_query is a sqlalchemy query that selects a post from the database. by matching the post id with the comment post id.
    post is the post that was selected.
    '''
    select_post_query = posts.select().where(posts.c.id == comment.post_id)
    post = await database.fetch_one(select_post_query)

    # if the post is not found, raise a 404 error
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Post {id} does not exist"
        )

    # insert the comment into the database
    insert_query = comments.insert().values(comment.dict())
    # execute the insert_query
    comment_id = await database.execute(insert_query)
    # select the comment from the database
    select_query = comments.select().where(comments.c.id == comment_id)
    # fetch the comment from the database
    # cast the comment to a CommentDB object
    raw_comment = cast(Mapping, await database.fetch_one(select_query))
    return CommentDB(**raw_comment)