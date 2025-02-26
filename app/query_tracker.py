import difflib
import sys
from contextlib import contextmanager

# Recognized query methods to label.
RECOGNIZED_METHODS = {
    "filter",
    "order_by",
    "limit",
    "offset",
    "group_by",
    "join",
    "innerjoin"
    "outerjoin",
    "distinct",
}

# Conditional keywords to capture.
CONDITIONAL_KEYWORDS = ("if ", "elif ", "else", "case ", "switch ")


def make_unified_diff(old_sql, new_sql):
    """
    Produce a unified diff between old_sql and new_sql.
    If old_sql is empty, the diff shows the full new_sql as additions.
    """
    old_lines = old_sql.splitlines()
    new_lines = new_sql.splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
    return "\n".join(diff)


class ExecutionNode:
    """
    A node in the execution tree.
      call: A string describing the event (e.g. "Call: funcName()",
            "if ...", "q = q.filter(User.active == True)").
      diff: A unified diff string if the query changed.
      substeps: A list of child nodes.
      indent: For conditionals, the number of leading spaces.
    """

    def __init__(self, call, diff=None, indent=None):
        self.call = call
        self.diff = diff
        self.substeps = []
        self.indent = indent

    def add_substep(self, node):
        self.substeps.append(node)


class QueryTracer:
    """
    A sys.settrace–based tracer that:
      1. Only traces lines in a file whose name contains a specified indicator.
      2. At the first line of each function, pushes a "Call: funcName()" node and resets the conditional stack.
      3. For each line starting with one of the conditional keywords, uses its indentation to determine nesting:
         - Pops from the conditional stack until the current indent is greater.
         - Then, if that exact condition (same line text) hasn’t been added at that level, adds a new conditional node.
         - The conditional stack holds tuples (indent, node) so that nested conditionals are grouped.
      4. For lines containing a recognized query method (like ".filter(" or ".order_by("),
         creates a node with that line.
         - Such nodes (and any diff nodes) are added to the deepest active conditional node (if any),
           otherwise to the current function’s node.
      5. Then it checks all local variables for SQLAlchemy Query objects (those with “statement” and “session”):
         - For a new query, the baseline is "" (empty string) so the diff shows all new SQL.
         - If the new SQL differs from the baseline, a unified diff is computed and attached to the recognized node
           (or added as a new node), and the baseline is updated.
    """

    def __init__(self, compile_func, user_file_indicator):
        self.compile_func = compile_func
        self.user_file_indicator = user_file_indicator.lower()
        self.root = ExecutionNode("Query Execution")
        self.node_stack = [self.root]
        self.query_sql_before = {}  # Map: query object id -> last compiled SQL
        self.cond_stack = []  # Stack of (indent, node) for conditionals in current function

    def push_node(self, node):
        self.node_stack[-1].add_substep(node)
        self.node_stack.append(node)

    def pop_node(self):
        if len(self.node_stack) > 1:
            self.node_stack.pop()

    def current_node(self):
        return self.node_stack[-1]

    def global_trace(self, frame, event, arg):
        if event == 'call' and self._should_trace(frame):
            return self.local_trace
        return None

    def local_trace(self, frame, event, arg):
        if event == 'line':
            self._process_line(frame)
        elif event == 'return':
            self.cond_stack = []  # Reset conditional stack when function returns.
            self.pop_node()
        return self.local_trace

    def _should_trace(self, frame):
        filename = frame.f_code.co_filename.lower()
        return self.user_file_indicator in filename

    def _process_line(self, frame):
        code = frame.f_code
        # At the very first line of a function, push a "Call: funcName()" node and reset cond_stack.
        if frame.f_lineno == code.co_firstlineno:
            func_node = ExecutionNode(f"Call: {code.co_name}()")
            self.push_node(func_node)
            self.cond_stack = []
        filename = code.co_filename
        lineno = frame.f_lineno
        line = self._get_line(filename, lineno)
        if not line:
            return
        # Use the raw line (without trailing newline)
        stripped = line.rstrip("\n")
        trimmed = stripped.lstrip()
        indent = len(stripped) - len(trimmed)

        # (A) Conditional node: if the line starts with any of our conditional keywords.
        for kw in CONDITIONAL_KEYWORDS:
            if trimmed.startswith(kw):
                # Pop from cond_stack until top indent is less than current indent.
                while self.cond_stack and self.cond_stack[-1][0] >= indent:
                    self.cond_stack.pop()
                # If not already added at this indent and lineno, add it.
                cond_key = (lineno, trimmed)
                # Check if the current top of cond_stack has the same condition.
                if not self.cond_stack or self.cond_stack[-1][1].call != trimmed:
                    cond_node = ExecutionNode(trimmed, indent=indent)
                    # If there's an active conditional branch, add to its node; otherwise, add to current node.
                    if self.cond_stack:
                        self.cond_stack[-1][1].add_substep(cond_node)
                    else:
                        self.current_node().add_substep(cond_node)
                    self.cond_stack.append((indent, cond_node))
                break  # Only add one conditional node per line.

        # (B) Recognized query method call.
        recognized_call = None
        for method in RECOGNIZED_METHODS:
            if f".{method}(" in trimmed:
                recognized_call = trimmed
                break
        # If there is an active conditional branch, add recognized nodes to its last node.
        target = self.cond_stack[-1][1] if self.cond_stack else self.current_node()
        recognized_node = None
        if recognized_call:
            recognized_node = ExecutionNode(recognized_call)
            target.add_substep(recognized_node)

        # (C) Check for changes in local Query objects.
        self._check_for_query_changes(frame, line, recognized_node if recognized_node else target)

    def _check_for_query_changes(self, frame, line_text, target_node):
        for varname, val in frame.f_locals.items():
            if hasattr(val, "statement") and hasattr(val, "session"):
                q_id = id(val)
                new_sql = self.compile_func(val)
                # Use empty string as baseline for first encounter.
                old_sql = self.query_sql_before.get(q_id, "")
                if new_sql != old_sql:
                    diff_str = make_unified_diff(old_sql, new_sql)
                    self.query_sql_before[q_id] = new_sql
                    # Attach the diff to the target node.
                    if target_node.diff:
                        target_node.diff += "\n" + diff_str
                    else:
                        target_node.diff = diff_str

    def _get_line(self, filename, lineno):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if 1 <= lineno <= len(lines):
                return lines[lineno - 1]
        except Exception:
            return None

    def print(self):
        """
        Calls `print_query_log()` from query_printer.py.
        """
        from app.query_printer import print_query_log
        print_query_log(self.root)


@contextmanager
def sql_query_trace(compile_func, filename):
    old_trace = sys.gettrace()
    tracer = QueryTracer(compile_func, filename)

    def global_tracer(frame, event, arg):
        return tracer.global_trace(frame, event, arg)

    sys.settrace(global_tracer)
    try:
        yield tracer
    finally:
        sys.settrace(old_trace)
