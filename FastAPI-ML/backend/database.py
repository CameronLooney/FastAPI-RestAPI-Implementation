import sqlalchemy # sqlalchemy is a package that allows us to connect to a database and execute queries
from databases import Database 
# Database is a class that defines a database connection

# Generally URL consists of the database engine, followed by authentication information and the hostname of the database server
DATABASE_URL = "sqlite:///backend.db" 
# This is the connection layer provided by databases that will allow us to perform asynchronous queries.
database = Database(DATABASE_URL)
sqlalchemy_engine = sqlalchemy.create_engine(DATABASE_URL)


def get_database() -> Database:
    return database