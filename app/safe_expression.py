# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import ast
import operator

__module_name__ = "Safe Expression Evaluator"
__version__ = "1.0.0"


class SafeExpressionError(ValueError):
    pass


class SafeExpressionEvaluator:
    _BINARY_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _UNARY_OPERATORS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
    }
    _COMPARISON_OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }
    _ALLOWED_CONSTANT_TYPES = (int, float, str, bool, type(None))

    def evaluate(self, expression, names=None, functions=None):
        try:
            parsed = ast.parse(str(expression or "").strip(), mode="eval")
        except SyntaxError as exc:
            raise SafeExpressionError(str(exc)) from exc
        return self._evaluate_node(
            parsed.body,
            names=names if isinstance(names, dict) else {},
            functions=functions if isinstance(functions, dict) else {},
        )

    def _evaluate_node(self, node, names, functions):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, self._ALLOWED_CONSTANT_TYPES):
                return node.value
            raise SafeExpressionError(f"Unsupported constant type: {type(node.value).__name__}")

        if isinstance(node, ast.Name):
            if node.id in names:
                return names[node.id]
            raise SafeExpressionError(f"Unknown name '{node.id}'")

        if isinstance(node, ast.BinOp):
            operator_fn = self._BINARY_OPERATORS.get(type(node.op))
            if operator_fn is None:
                raise SafeExpressionError(f"Unsupported binary operator: {type(node.op).__name__}")
            return operator_fn(
                self._evaluate_node(node.left, names, functions),
                self._evaluate_node(node.right, names, functions),
            )

        if isinstance(node, ast.UnaryOp):
            operator_fn = self._UNARY_OPERATORS.get(type(node.op))
            if operator_fn is None:
                raise SafeExpressionError(f"Unsupported unary operator: {type(node.op).__name__}")
            return operator_fn(self._evaluate_node(node.operand, names, functions))

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True
                for value_node in node.values:
                    result = self._evaluate_node(value_node, names, functions)
                    if not result:
                        return result
                return result
            if isinstance(node.op, ast.Or):
                result = False
                for value_node in node.values:
                    result = self._evaluate_node(value_node, names, functions)
                    if result:
                        return result
                return result
            raise SafeExpressionError(f"Unsupported boolean operator: {type(node.op).__name__}")

        if isinstance(node, ast.Compare):
            left_value = self._evaluate_node(node.left, names, functions)
            for operator_node, comparator_node in zip(node.ops, node.comparators):
                operator_fn = self._COMPARISON_OPERATORS.get(type(operator_node))
                if operator_fn is None:
                    raise SafeExpressionError(f"Unsupported comparison operator: {type(operator_node).__name__}")
                right_value = self._evaluate_node(comparator_node, names, functions)
                if not operator_fn(left_value, right_value):
                    return False
                left_value = right_value
            return True

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise SafeExpressionError("Only direct helper function calls are allowed")
            function = functions.get(node.func.id)
            if not callable(function):
                raise SafeExpressionError(f"Unknown function '{node.func.id}'")
            args = [self._evaluate_node(arg, names, functions) for arg in node.args]
            kwargs = {}
            for keyword in node.keywords:
                if keyword.arg is None:
                    raise SafeExpressionError("Starred keyword arguments are not allowed")
                kwargs[keyword.arg] = self._evaluate_node(keyword.value, names, functions)
            return function(*args, **kwargs)

        if isinstance(node, ast.Tuple):
            return tuple(self._evaluate_node(element, names, functions) for element in node.elts)

        if isinstance(node, ast.List):
            return [self._evaluate_node(element, names, functions) for element in node.elts]

        raise SafeExpressionError(f"Unsupported expression node: {type(node).__name__}")