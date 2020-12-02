from builtin_functions import * 
from collections import defaultdict
from random import randrange
from util import cartesian_product, fold, scalar_product_accumulate
from functools import reduce

class Expression():
	def eval(self):
		raise NotImplementedError
	def sequence(self):
		return [self.eval()]

class ValueExpression(Expression):
	def distribution(self):
		raise NotImplementedError
	def distribution_sequence(self):
		return [self.distribution()]

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
		result = None
		for k, p in qual_pdf.items():
			number, sides = k
			expanded = [DiceExpression.dice_pdf(sides) for _ in range(number)]
			def sum_pdf(lhs, rhs):
				return fold(cartesian_product(lhs, rhs), lambda x, y: x + y)
			total_pdf = reduce(sum_pdf, expanded)
			result = scalar_product_accumulate(total_pdf, p, result)
		return result
	def distribution_sequence(self):
		number_distr = self.number.distribution()
		sides_distr = self.sides.distribution()
		max_dice, = max(number_distr.keys())
		dice = []
		for dn in range(1,int(max_dice)+1):
			dn_unit = {(dn,): 1.0}
			at_least_dn = fold(cartesian_product(number_distr, dn_unit), lambda x, y: y <= x)
			dn_exists_prob = at_least_dn[True,]
			dice_n = None
			for sides, sides_p in sides_distr.items():
				sides, = sides
				dice_n = scalar_product_accumulate(DiceExpression.dice_pdf(sides), sides_p*dn_exists_prob, dice_n)
			#todo: handle this better
			dice_n = scalar_product_accumulate({(0.0,) : 1.0}, 1-dn_exists_prob, dice_n)
			dice.append(dice_n)
		return dice			

class FunctionCall(Expression):
	symbols = {
		('max', 1, ()) : builtins_max,
		('if', 1, (('then', 1), ('else', 1))): builtins_if,
		('distribution', 1, ()): builtins_distribution,
	}
	distr_symbols = {
		('max', 1, ()) : builtins_max_distribution,
		('if', 1, (('then', 1), ('else', 1))): builtins_if_distribution,
		('distribution', 1, ()): builtins_distribution_distribution,
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
		function = FunctionCall.distr_symbols[self.funame]
		return function(*self.args, **self.kwargs)

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


