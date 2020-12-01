#!/Usr/bin/python
from random import randrange
import readline
from lark import Lark
import lark
from collections import defaultdict
from functools import reduce

def main():
	try:
		while(True):
			evalexpr(input())
	except EOFError:
		pass
def evalexpr(expr):
	parsedexpr = parse(expr)
	print(parsedexpr.eval())

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

def cartesian_product(lhs, rhs):
	result = {}
	for k1, p1 in lhs.items():
		for k2, p2 in rhs.items():
			result[(*k1, *k2)] = p1*p2
	return result

def fold(distr, func):
	result = defaultdict(lambda: 0.0)
	for k, p in distr.items():
		result[func(*k),] += p
	return result

class Expression():
	def eval(self):
		raise NotImplementedError
	def sequence(self):
		return [self.eval()]

class ValueExpression(Expression):
	def distribution(self):
		raise NotImplementedError

class Literal(ValueExpression):
	def __init__(self, value):
		self.value = value
	def eval(self):
		return self.value
	def distribution(self):
		return {(self.value,): 1.0}

class IntegerLiteral(Literal):
	def __init__(self, value):
		self.value = int(value)
	def __repr__(self):
		return "IntegerLiteral({})".format(self.value)

class MathExpression(ValueExpression):
	operators = {
		'+' : (lambda x, y: x + y),
		'-' : (lambda x, y: x - y),
		'*' : (lambda x, y: x * y),
		'/' : (lambda x, y: x / y),
		'==' : (lambda x, y: 1 if x == y else 0),
		'!=' : (lambda x, y: 1 if x == y else 0),
		'<' : (lambda x, y: 1 if x < y else 0),
		'>' : (lambda x, y: 1 if x > y else 0),
		'>=' : (lambda x, y: 1 if x >= y else 0),
		'<=' : (lambda x, y: 1 if x <= y else 0),
	}
	def __init__(self, lhs, operator, rhs):
		self.operator = MathExpression.operators[operator.eval()]
		self.lhs = lhs
		self.rhs = rhs
	def eval(self):
		return self.operator(self.lhs.eval(), self.rhs.eval())
	def distribution(self):
		product = cartesian_product(self.lhs.distribution(), self.rhs.distribution())
		return fold(product, self.operator)

class DiceExpression(ValueExpression):
	def __init__(self, number, sides):
		self.number, self.sides = number, sides
	def	eval(self):
		return sum(self.sequence())
	def sequence(self):
		sides = self.sides.eval()
		number = self.number.eval()
		return [randrange(1,sides+1) for _ in range(number)]
	def dice_pdf(sides):
		result = {}
		for i in range(1, sides+1):
			result[(i,)] = 1.0/sides
		return result
	def distribution(self):
		qual_pdf = cartesian_product(self.number.distribution(), self.sides.distribution())
		print(qual_pdf)
		result = defaultdict(lambda: 0.0)
		for k, p in qual_pdf.items():
			number, sides = k
			expanded = [DiceExpression.dice_pdf(sides) for _ in range(number)]
			def sum_pdf(lhs, rhs):
				return fold(cartesian_product(lhs, rhs), lambda x, y: x + y)
			total_pdf = reduce(sum_pdf, expanded)
			for k2, p2 in total_pdf.items():
				result[k2] += p * p2
		return result

def _builtins_distribution(item):
	return dict(item.distribution())

def _builtins_max(seq):
	s = seq.sequence()
	head, tail = s[0], s[1:]
	if len(s) == 1:
			return head
	tail_max = _builtins_max(tail)
	if head > tail_max:
		return tail_max
	else:
	
def _builtins_if(test, **kwargs):
	then, els = kwargs['then'], kwargs['else']
	#print(kwargs)
	if test.eval() != 0:
		return then[0].eval()
	else:
		return els[0].eval()

def Monad(Expression):
	def apply(self, function):
		raise NotImplementedError

def MonadLiteral(Monad):
	def __init__(self, wrapped):
		self.wrapped = wrapped
	def apply(self, function):
		return function(self)
	def eval(self):
		return self.wrapped.eval()
	def sequence(self):
		return self.wrapped.sequence()
	def distribution(self):
		return self.wrapped.distribution()

def SequenceMonad(Monad):
	def __init__(self, wrapped_vals):
		self.wrapped_vals = wrapped_vals
	def apply(self, function):
		return SequenceMonad(map(function, self.wrapped_vals))
	def eval(self):
		[wrapped_val.eval() for wrapped_val in self.wrapped_vals]
	def sequence(self):
		[wrapped_val.sequence() for wrapped_val in self.wrapped_vals]
	def distribution(self):
		[wrapped_val.sequence() for wrapped_val in self.wrapped_vals]

class FunctionCall(Expression):
	symbols = {
		('max', 1, ()) : _builtins_max,
		('if', 1, (('then', 1), ('else', 1))): _builtins_if,
		('distribution', 1, ()): _builtins_distribution,
	}
	def __init__(self, funame, args):
		args = args.sequence()
		self.args = args[0].sequence()
		self.kwargs = {s[0].eval(): s[1:] for s in [s.sequence() for s in args[1:]]}
		#print(self.kwargs)
		self.kwargsets = tuple([(kw, len(s)) for kw, s in self.kwargs.items()])
		self.funame = (funame.eval(), len(self.args), self.kwargsets)
		#print(self.funame)
	def eval(self):
		function = FunctionCall.symbols[self.funame]
		return function(*self.args, **self.kwargs)
	def distribution(self):
		self.kwargs['__distr'] = True
		result = self.eval()
		self.kwargs['__distr'] = False
		return result

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
	def __repr__(self):
		return "ListConverter({})".format(self.value)

context = {}

class VariableSetter(Expression):
	def __init__(self, varname, value):
		self.varname = varname.eval()
		self.value = value
	def eval(self):
		context[self.varname] = self.value.eval()

class VariableGetter(Expression):
	def __init__(self, varname):
		self.varname = varname
	def eval(self):
		return context[self.varname.eval()]

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

if __name__=='__main__':
	main()

