from lark import Lark
import lark
from internals import *
grammar = Lark('''start: value | variable_set
									variable_set: VAR " "* "=" " "* value
									value: sequence | numeric | variable
									variable: "$" VAR
									VAR: /[a-zA-Z]\w*/
									sequence: "[" sequence_items "]"
									sequence_items: value | value / *, */ sequence_items
									numeric: funcall | mathexpr | dicexpr | NUMBER | variable | "(" numeric ")"
									mathexpr: numeric " "* OPERATOR " "* numeric
									funcall: "[" FUNAME " " funcarglist "]"
									funcarglist: arglist | kwargsets | arglist " " kwargsets
									kwargsets: kwarglist | kwarglist " " kwargsets
									arglist: arg | arg " " arglist
									kwarglist: KEYWORD " " arglist
									KEYWORD: /[a-zA-Z]\w*/
									FUNAME: /[a-zA-Z]\w*/
									arg: value
									OPERATOR: /\+|\-|\*|\/|==|!=|<|>|<=|>=/
									dicexpr: numeric "d" numeric
									NUMBER: /\d+/
  						 ''')

resolve = {
	'dicexpr' : DiceExpression,
	'NUMBER' : IntegerLiteral,
	'OPERATOR' : Literal,
	'mathexpr' : MathExpression,
	'numeric' : None,
	'FUNAME' : Literal,
	'arglist' : ListConverter,
	'arg' : None,
	'funcall' : FunctionCall,
	'value' : None,
	'sequence' : None,
	'sequence_items' : ListConverter,
	'funcarglist' : ListConverter,
	'kwargsets' : ListConverter,
	'kwarglist' : ListConverter,
	'KEYWORD' : Literal,
	'variable_set' : VariableSetter,
	'variable' : VariableGetter,
	'VAR' : Literal,
}

def parse(expr):
	parsed = grammar.parse(expr)
	#print(parsed)
	transformed = transform(parsed.children)
	return transformed[0]


def transform(items):
	result_items = []
	for item in items:
		if type(item) == lark.tree.Tree:
			item_type = item.data
			item_value = transform(item.children)
		else:
			item_type = item.type
			if item_type[0:6] == "__ANON":
				continue
			item_value = [item.value]
		ResultClass = resolve[item_type]
		if ResultClass:
			#print(ResultClass, item_value)
			result = ResultClass(*item_value)
		else:
			result, = item_value
		result_items.append(result)
	return result_items


