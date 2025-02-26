# SQLAlchemy Query Tracker
[![Downloads](https://pepy.tech/badge/sqa_tracker)](https://pepy.tech/project/sqa_tracker)
SQLAlchemy Query Tracker is a Python package that lets you track modifications made to SQLAlchemy query objects in real time. Using Python’s `sys.settrace` along with the [Rich](https://github.com/Textualize/rich) library, it generates a detailed, nested execution tree showing function calls, conditional branches (if, elif, else, case, switch), and recognized query modifications—with unified diffs between query states.

## Features

- **Real-time Tracking:** Monitor SQLAlchemy query changes as they occur.
- **Rich Execution Tree:** Visualize function calls, conditionals, and query modifications as a nested tree.
- **Unified Diff Output:** Display differences between the SQL before and after each modification.
- **Easy Integration:** Wrap your session code with a simple context manager—no modifications to your existing queries are needed.

## Installation

Download or clone the repository:

```bash
git clone https://github.com/jiri-otoupal/sqa_tracker.git
cd sqa_tracker
```

Alternatively, download the ZIP archive from the repository page and extract it.

## Usage

Wrap your SQLAlchemy query code using the context manager provided by the package. For example:

```python
from sqlalchemy.orm import Session
from query_tracker import sql_query_trace
from query_printer import print_query_log

# Define your compile function (this example uses SQLAlchemy's compile)
def compile_sqlalchemy_query(query):
    return str(query.statement.compile(compile_kwargs={"literal_binds": True}))

# Within your session, wrap your code with sql_query_trace
with Session(engine) as session:
    with sql_query_trace(compile_sqlalchemy_query, Path(__file__).name) as tracer:
        q = session.query(User)
        # ... perform query modifications here ...
        q = q.filter(User.active == True)
        q = q.order_by(User.name.asc())
    print_query_log(tracer.root)
```

A complete example is provided in the `test_query_tracking.py` file.

Use print method on tracer to show current status without finish execution

```python
from sqlalchemy.orm import Session
from query_tracker import sql_query_trace


# Define your compile function (this example uses SQLAlchemy's compile)
def compile_sqlalchemy_query(query):
    return str(query.statement.compile(compile_kwargs={"literal_binds": True}))


# Within your session, wrap your code with sql_query_trace
with Session(engine) as session:
    with sql_query_trace(compile_sqlalchemy_query, Path(__file__).name) as tracer:
        q = session.query(User)
        # ... perform query modifications here ...
        q = q.filter(User.active == True)
        tracer.print()
        # other code ...
```

## Requirements

- Python 3.10+
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Rich](https://github.com/Textualize/rich)

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements or bug fixes.
