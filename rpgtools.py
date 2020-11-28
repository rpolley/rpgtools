#!/usr/bin/python
from random import randrange
import readline
from lark import Lark
import lark

def main():
	try:
		while(True):
			evalexpr(input())
	except EOFError:
		pass
def evalexpr(expr):
	parsedexpr = parse(expr)
	print(parsedexpr.eval())

grammar = Lark('''start: value
									value: sequence | numeric
									sequence: "[" sequence_items "]"
									sequence_items: value | value / *, */ sequence_items
									numeric: funcall | mathexpr | dicexpr | NUMBER | "(" numeric ")"
									mathexpr: numeric " "* OPERATOR " "* numeric
									funcall: "[" FUNAME " " arglist "]"
									arglist: arg | arg arglist
									FUNAME: /[a-zA-Z]\w*/
									arg: value
									OPERATOR: /\+|\-|\*|\//
									dicexpr: numeric "d" numeric
									NUMBER: /\d+/
  						 ''')

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

class Expression():
	def eval(self):
		raise NotImplementedError
	def sequence(self):
		return [self.eval()]

class Literal(Expression):
	def __init__(self, value):
		self.value = value
	def eval(self):
		return self.value

class IntegerLiteral(Literal):
	def __init__(self, value):
		self.value = int(value)
class MathExpression(Expression):
	operators = {
		'+' : (lambda x, y: x + y),
		'-' : (lambda x, y: x - y),
		'*' : (lambda x, y: x * y),
		'/' : (lambda x, y: x / y),
	}
	def __init__(self, lhs, operator, rhs):
		self.operator = MathExpression.operators[operator.eval()]
		self.lhs = lhs
		self.rhs = rhs
	def eval(self):
		return self.operator(self.lhs.eval(), self.rhs.eval())

class DiceExpression(Expression):
	def __init__(self, number, sides):
		self.number, self.sides = number, sides
	def	eval(self):
		return sum(self.sequence())
	def sequence(self):
		sides = self.sides.eval()
		number = self.number.eval()
		return [randrange(1,sides+1) for _ in range(number)]

def _builtins_max(seq):
	return max([_builtins_eval(item) for item in seq.sequence()])

def _builtins_eval(item):
	if isinstance(item, Expression):
		return item.eval()
	else:
		return item

class FunctionCall(Expression):
	symbols = {
		'max' : _builtins_max,
		'eval' : _builtins_eval,
	}
	def __init__(self, funame, args):
		self.funame = funame.eval()
		self.args = args.sequence()
	def eval(self):
		function = FunctionCall.symbols[self.funame]
		return function(*self.args)

class ListConverter(Expression):
	def __init__(self, head, tail=None):
		if tail:
			self.value = [head] + tail.sequence()
		else:
			self.value = [head]
	def sequence(self):
		return self.value
	def eval(self):
		return [item.eval() for item in self.value]

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
}

if __name__=='__main__':
	main()

