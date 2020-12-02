from lark import Lark
import lark
from internals import *
# language grammar
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

# look up table mapping elements in the syntax to classes in the internal representation
# None means that it should use its child's type
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

# transform a string into an internal representation
def parse(expr):
	parsed = grammar.parse(expr)
	transformed = transform(parsed.children)
	return transformed[0]

# transform a lark parse tree into an internal representation
# takes a list of tree nodes/tokens and transforms them into a list of internal objects
def transform(items):
	result_items = []
	for item in items:
		# extract the item's "type" and it's "data"
		# these are at different members for lark Tree nodes and tokens
		if type(item) == lark.tree.Tree: # handle Tree nodes
			item_type = item.data
			item_value = transfrm(item.children) # transform the node's children, and use the result as the node's "data"
		else: # handle tokens
			item_type = item.type
			if item_type[0:6] == "__ANON": # ignore "anonymous" tokens created by the parser
				continue
			item_value = [item.value] # use the item's value as its type, since tokens don't have children
		ResultClass = resolve[item_type] # look up the corresponding class to the node's type
		if ResultClass: # it has a corresponding type
			result = ResultClass(*item_value)
		else: # collapse the item to it's child
			result, = item_value
		result_items.append(result)
	return result_items


