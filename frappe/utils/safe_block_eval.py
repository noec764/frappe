import ast

import frappe
from frappe.utils.safe_exec import is_safe_exec_enabled, safe_exec


def safe_block_eval(code: str, _globals=None, _locals=None, output_var=None, **kwargs):
	"""Evaluate a block of code and return the result.

	Allows `return` statements and `yield` expressions in the code to make it easier to write code that should return a value.

	Args:
	        code (str): The code to evaluate. Will be wrapped in a function.
	        _globals (dict, optional): Globals
	        _locals (dict, optional): Locals
	        output_var (str, optional): The name of the variable to store the result in. Randomly generated if not provided.
	        restrict_commit_rollback (bool, optional)

	Returns:
	        any: The result of the evaluation of the code.
	"""
	if not code:
		return

	if not isinstance(code, str):
		raise TypeError(f"Code must be a string, got: {code!r}")

	if not is_safe_exec_enabled():
		# If server scripts are disabled, just evaluate the expression normally.
		# Changing the value of "server_script_enabled" might break existing
		# multi-line conditions/virtual fields, but that's okay because it
		# is not a common use case.
		return frappe.safe_eval(code, _globals, _locals)

	output_var = output_var or "evaluated_code_output_" + frappe.generate_hash(length=5)
	_locals = _locals or {}
	code = _wrap_in_function(code, output_var=output_var, _locals=_locals)
	safe_exec(code, _globals, _locals, **kwargs)
	return _locals[output_var]


def _wrap_in_function(
	code: str,
	*,
	function_name: str = "evaluated_code_wrapper_function_",
	output_var: str = "evaluated_code_output_var_",
	_locals: dict[str, None] | None = None,
) -> str:
	"""Wrap code in a function so that it can contain `return` statements."""

	# Parse the code into an AST
	tree: ast.Module = ast.parse(code, filename="<safe_block_eval>", mode="exec")

	# Check if the code is a single expression
	if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
		# If it is, wrap it in a return statement
		tree.body[0] = ast.Return(tree.body[0].value)

	# Check if the code is empty
	if not tree.body:
		# If it is, pass
		tree.body = [ast.Pass()]

	# Create a function definition
	local_names = sorted(_locals.keys()) if _locals else []

	function_definition = ast.FunctionDef(
		name=function_name,
		# ast.arguments(arg* posonlyargs, arg* args, arg? vararg, arg* kwonlyargs, expr* kw_defaults, arg? kwarg, expr* defaults)
		args=ast.arguments(
			posonlyargs=[],
			args=[ast.arg(arg=name) for name in local_names],
			vararg=None,
			kwonlyargs=[],
			kw_defaults=[],
			kwarg=None,
			defaults=[],
		),
		body=tree.body,  # The body of the module becomes the body of the function
		decorator_list=[],
		returns=None,
		type_comment=None,
	)

	# Create a call to the function
	# ast.Call(func expr, expr* args, keyword* keywords)
	function_call = ast.Call(
		func=ast.Name(id=function_name, ctx=ast.Load()),
		args=[ast.Name(id=name, ctx=ast.Load()) for name in local_names],
		keywords=[],
	)

	# Create an assignment to store the result of the function call
	# ast.Assign(expr* targets, expr value, expr? type_comment)
	final_assignment = ast.Assign(
		targets=[ast.Name(id=output_var, ctx=ast.Store())],
		value=function_call,
		type_comment=None,
	)

	# Replace the body of the module with the function definition and assignment
	tree.body = [function_definition, final_assignment]

	# Convert the AST back into code
	ast.fix_missing_locations(tree)
	return ast.unparse(tree)


def validate(code: str | None, fieldname: str = ""):
	"""Validate a block of code by first wrapping it in a function and then compiling it."""
	if not code:
		return

	if not isinstance(code, (bytes, str)):
		raise TypeError(f"Code must be a string, got: {code!r}")

	try:
		code = _wrap_in_function(code)
		# Because the code is parsed into an AST, it is already checked for syntax errors
		# so we don't need to check again with:
		# >>> compile(code, f"<{fieldname}>", "exec")
		# Moreover, any subsequent error would come from the function-wrapping mechanism;
		# which is unlikely (and would be a bug in this code)
	except SyntaxError as se:
		msg = frappe._(fieldname or "") + ":" if fieldname else ""
		msg = frappe._("{} Invalid python code on line {}").format(msg, se.lineno)
		msg = msg.strip() + "<br>\n" + format_syntax_error(se)
		frappe.throw(msg, title=frappe._("Syntax Error"))


def format_syntax_error(se: SyntaxError):
	msg = f"<pre><code>{se.text}\n{'^'.rjust(se.offset + 1)}</code></pre><br>\n{se.msg}"
	return msg
