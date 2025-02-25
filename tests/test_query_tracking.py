from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import Session, declarative_base

from app.query_printer import print_query_log
from app.query_tracker import sql_query_trace

engine = create_engine("sqlite:///:memory:", echo=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    active = Column(Boolean)

Base.metadata.create_all(engine)

def compile_sqlalchemy_query(query):
    return str(query.statement.compile(engine, compile_kwargs={"literal_binds": True}))

def add_query(q):
    # user code if statements
    if "add_query":
        q = q.filter(User.age < 50)
    return q

def modify_query(q):
    # nested if statements
    if "somea":
        q = q.filter(User.id == 5)
        if True:
            q = q.filter(User.active == True)
            if "addx":
                q = q.filter(User.age > 30)
                q = add_query(q)
    return q

def main():
    with Session(engine) as session:
        # Start the trace context
        with sql_query_trace(compile_sqlalchemy_query) as tracer:
            # Inside this block, user code is traced
            q = session.query(User)
            q = modify_query(q)
            q = q.order_by(User.name.asc())

        # Print the final execution tree
        print_query_log(tracer.root)

        print("🔹 Final Query Execution:")
        print(q.statement.compile(engine, compile_kwargs={"literal_binds": True}))

if __name__ == "__main__":
    # If you want all if statements to pass:
    # random.uniform = lambda *args, **kwargs: 1.0
    main()
